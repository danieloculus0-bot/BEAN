/* Offline bounded ZIP/OOXML readers. No network, eval, or script injection.
 * Supports ordinary ZIP stored and DEFLATE members, including common Office files.
 */
(function(){
"use strict";
const WORD="http://schemas.openxmlformats.org/wordprocessingml/2006/main";
const SS="http://schemas.openxmlformats.org/spreadsheetml/2006/main";
const REL="http://schemas.openxmlformats.org/officeDocument/2006/relationships";
const MAX_ARCHIVE=10*1024*1024,MAX_ENTRY=16*1024*1024,MAX_TOTAL=40*1024*1024;
const utf8=new TextDecoder("utf-8",{fatal:true});
function fail(detail){throw Error("Office import: "+detail);}
function little16(a,p){return a[p]|a[p+1]<<8;}
function little32(a,p){return (a[p]|a[p+1]<<8|a[p+2]<<16|a[p+3]*16777216)>>>0;}
const crcTable=Array.from({length:256},(_,i)=>{let c=i;for(let j=0;j<8;j++)c=(c>>>1)^((c&1)?0xedb88320:0);return c>>>0;});
function crc32(bytes){let c=0xffffffff;for(const b of bytes)c=(c>>>8)^crcTable[(c^b)&255];return (c^0xffffffff)>>>0;}
function inflate(data,size){
  if(size>MAX_ENTRY)fail("unpacked part exceeds 16 MB");
  const out=new Uint8Array(size);
  let p=0,buf=0,n=0,used=0;
  function read(bits){
    while(n<bits){if(p>=data.length)fail("truncated compressed stream");buf|=data[p++]<<n;n+=8;}
    const value=buf&((1<<bits)-1);buf>>>=bits;n-=bits;return value;
  }
  function makeTree(lengths){
    const count=new Uint16Array(16),next=new Uint16Array(16),lookup=Array.from({length:16},()=>new Map());
    for(const len of lengths){if(len>15)fail("invalid Huffman width");if(len)count[len]++;}
    let code=0;
    for(let len=1;len<=15;len++){code=(code+count[len-1])*2;next[len]=code;if(code+count[len]>(1<<len))fail("invalid Huffman codes");}
    let max=0;
    lengths.forEach((len,symbol)=>{if(len){lookup[len].set(next[len]++,symbol);max=Math.max(max,len);}});
    if(!max)fail("missing Huffman codes");
    return ()=>{let bits=0;for(let len=1;len<=max;len++){bits=(bits<<1)|read(1);if(lookup[len].has(bits))return lookup[len].get(bits);}fail("invalid Huffman sequence");};
  }
  const order=[16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15];
  const lb=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258];
  const le=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0];
  const db=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577];
  const de=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13];
  function add(value){if(used>=out.length)fail("unpacked part larger than declared");out[used++]=value;}
  let last=false;
  while(!last){
    last=read(1)===1;const type=read(2);
    if(type===0){
      if(n)read(n%8);
      const length=read(16),check=read(16);
      if((length^check)!==65535)fail("stored-block checksum mismatch");
      for(let i=0;i<length;i++)add(read(8));
      continue;
    }
    if(type===3)fail("unsupported compression block");
    let lit,dist;
    if(type===1){
      lit=makeTree(Array.from({length:288},(_,i)=>i<=143?8:i<=255?9:i<=279?7:8));
      dist=makeTree(Array(32).fill(5));
    }else{
      const numLit=read(5)+257,numDist=read(5)+1,numLen=read(4)+4;
      const codeLens=Array(19).fill(0);
      for(let i=0;i<numLen;i++)codeLens[order[i]]=read(3);
      const lengthDecoder=makeTree(codeLens),lens=[];
      while(lens.length<numLit+numDist){
        const symbol=lengthDecoder();
        if(symbol<=15)lens.push(symbol);
        else{
          const howMany=symbol===16?read(2)+3:symbol===17?read(3)+3:symbol===18?read(7)+11:0;
          if(!howMany||(symbol===16&&!lens.length))fail("invalid Huffman repeat");
          const value=symbol===16?lens[lens.length-1]:0;
          for(let i=0;i<howMany;i++)lens.push(value);
        }
        if(lens.length>numLit+numDist)fail("Huffman repeat beyond table");
      }
      lit=makeTree(lens.slice(0,numLit));
      const distLengths=lens.slice(numLit);
      dist=distLengths.some(Boolean)?makeTree(distLengths):null;
    }
    while(true){
      const symbol=lit();
      if(symbol<256){add(symbol);continue;}
      if(symbol===256)break;
      if(symbol>285||!dist)fail("invalid length/distance symbol");
      const li=symbol-257,length=lb[li]+read(le[li]);
      const di=dist();
      if(di>=30)fail("invalid distance code");
      const distance=db[di]+read(de[di]);
      if(distance>used)fail("back-reference before output");
      for(let i=0;i<length;i++)add(out[used-distance]);
    }
  }
  if(used!==size)fail("unpacked length mismatch");
  return out;
}
function openZip(arrayBuffer){
  const a=new Uint8Array(arrayBuffer);
  if(a.length>MAX_ARCHIVE)fail("file is larger than 10 MB");
  if(a.length<22)fail("truncated ZIP file");
  let end=-1;
  for(let p=a.length-22;p>=Math.max(0,a.length-65557);p--){if(little32(a,p)===0x06054b50){end=p;break;}}
  if(end<0)fail("ZIP central directory missing");
  const items=little16(a,end+10),start=little32(a,end+16),dirSize=little32(a,end+12);
  if(items>2000||start+dirSize>a.length)fail("invalid or oversized ZIP directory");
  let at=start,total=0;
  const entries=new Map();
  for(let i=0;i<items;i++){
    if(at+46>a.length||little32(a,at)!==0x02014b50)fail("invalid central-directory member");
    const flags=little16(a,at+8),method=little16(a,at+10),crc=little32(a,at+16);
    const packed=little32(a,at+20),size=little32(a,at+24),nameLen=little16(a,at+28);
    const extra=little16(a,at+30),comment=little16(a,at+32),local=little32(a,at+42);
    if(at+46+nameLen+extra+comment>a.length)fail("truncated central-directory name");
    const name=utf8.decode(a.subarray(at+46,at+46+nameLen));
    at+=46+nameLen+extra+comment;
    if(flags&1)fail("encrypted Office files are unsupported");
    if((flags&0x40)||size===0xffffffff||packed===0xffffffff)fail("ZIP64/strong encryption is unsupported");
    if(method!==0&&method!==8)fail("unsupported ZIP compression method");
    if(size>MAX_ENTRY||packed>MAX_ARCHIVE||(total+=size)>MAX_TOTAL)fail("ZIP decompression budget exceeded");
    if(local+30>a.length||little32(a,local)!==0x04034b50)fail("invalid ZIP local header");
    const dataAt=local+30+little16(a,local+26)+little16(a,local+28);
    if(dataAt+packed>a.length)fail("truncated ZIP member");
    if(entries.has(name))fail("duplicate ZIP member");
    entries.set(name,{dataAt,packed,size,method,crc});
  }
  function get(name,optional=false){
    const e=entries.get(name);
    if(!e){if(optional)return null;fail("required part missing: "+name);}
    const compressed=a.subarray(e.dataAt,e.dataAt+e.packed);
    const result=e.method===0?compressed:inflate(compressed,e.size);
    if(result.length!==e.size||crc32(result)!==e.crc)fail("corrupt ZIP member: "+name);
    return result;
  }
  return {get,has:name=>entries.has(name),list:()=>[...entries.keys()]};
}
function xmlDocument(bytes){
  const source=utf8.decode(bytes);
  if(/<!\s*(?:DOCTYPE|ENTITY)\b/i.test(source))fail("DTD/entity declarations are forbidden");
  const doc=new DOMParser().parseFromString(source,"application/xml");
  if(doc.querySelector("parsererror"))fail("invalid XML document");
  return doc;
}
function nodes(element,ns,name){return Array.from(element.getElementsByTagNameNS(ns,name));}
function child(element,ns,name){return Array.from(element.children).find(c=>c.namespaceURI===ns&&c.localName===name)||null;}
function attribute(element,ns,name){return element?.getAttributeNS(ns,name)||element?.getAttribute(name)||"";}
function readDOCX(buffer){
  const zip=openZip(buffer);
  const doc=xmlDocument(zip.get("word/document.xml"));
  const body=nodes(doc,WORD,"body")[0];if(!body)fail("Word body missing");
  const container=document.createElement("div");
  const direct=Array.from(body.children);
  if(direct.length>10000)fail("document has too many blocks");
  for(const block of direct){
    if(block.localName!=="p"&&block.localName!=="tbl")continue;
    const paragraphs=block.localName==="p"?[block]:nodes(block,WORD,"p");
    for(const p of paragraphs){
      const pp=child(p,WORD,"pPr"),style=attribute(child(pp||p,WORD,"pStyle"),WORD,"val");
      const tag=/^(?:Heading\s*1|heading1|Title)$/i.test(style)?"h1":/^(?:Heading\s*2|heading2)$/i.test(style)?"h2":/^(?:Heading\s*3|heading3)$/i.test(style)?"h3":"p";
      const el=document.createElement(tag);
      const justify=attribute(child(pp||p,WORD,"jc"),WORD,"val");
      if(["left","center","right","both"].includes(justify))el.style.textAlign=justify==="both"?"justify":justify;
      if(child(pp||p,WORD,"numPr"))el.append(document.createTextNode("• "));
      for(const run of nodes(p,WORD,"r")){
        const rp=child(run,WORD,"rPr");
        let holder=el;
        for(const [key,tagName] of [["b","strong"],["i","em"],["u","u"],["strike","s"]]){
          const prop=child(rp||run,WORD,key);
          if(prop&&attribute(prop,WORD,"val")!=="0"){
            const wrap=document.createElement(tagName);holder.append(wrap);holder=wrap;
          }
        }
        for(const item of run.children){
          if(item.namespaceURI!==WORD)continue;
          if(item.localName==="t"||item.localName==="instrText") {
            if(item.localName==="t")holder.append(document.createTextNode(item.textContent||""));
          }else if(item.localName==="tab")holder.append(document.createTextNode("\t"));
          else if(item.localName==="br")holder.append(document.createElement("br"));
        }
      }
      container.append(el);
      if(container.textContent.length>1024*1024)fail("Word text exceeds 1 MB");
    }
  }
  return {html:container.innerHTML,blocks:container.childElementCount};
}
function colCoords(ref){
  const match=/^([A-Z]+)([1-9]\d*)$/.exec(ref);
  if(!match)fail("invalid spreadsheet cell reference");
  let col=0;
  for(const ch of match[1])col=col*26+ch.charCodeAt(0)-64;
  const row=Number(match[2])-1;col--;
  if(col>=40||row>=5000)fail("sheet exceeds 40 columns or 5,000 rows");
  return [row,col];
}
function sheetPath(zip){
  const workbook=zip.get("xl/workbook.xml",true);
  const rels=zip.get("xl/_rels/workbook.xml.rels",true);
  if(workbook&&rels){
    const d=xmlDocument(workbook),first=nodes(d,SS,"sheet")[0];
    const id=first?.getAttributeNS(REL,"id");
    if(id){
      const paths=nodes(xmlDocument(rels),"http://schemas.openxmlformats.org/package/2006/relationships","Relationship");
      const hit=paths.find(p=>p.getAttribute("Id")===id&&p.getAttribute("Type")?.endsWith("/worksheet"));
      if(hit){
        const target=hit.getAttribute("Target")||"";
        if(target.includes("://")||target.startsWith("//")||target.includes("\\"))fail("invalid worksheet target");
        const segments=(target.startsWith("/")?target.slice(1):"xl/"+target).split("/");
        const clean=[];
        for(const part of segments){if(part===".." ){if(!clean.length)fail("worksheet outside archive");clean.pop();}else if(part&&part!==".")clean.push(part);}
        return clean.join("/");
      }
    }
  }
  return "xl/worksheets/sheet1.xml";
}
function readXLSX(buffer){
  const zip=openZip(buffer);
  const shared=[];
  if(zip.has("xl/sharedStrings.xml")){
    const d=xmlDocument(zip.get("xl/sharedStrings.xml"));
    for(const si of nodes(d,SS,"si")){
      shared.push(nodes(si,SS,"t").map(e=>e.textContent||"").join(""));
      if(shared.length>200000)fail("shared string count exceeds limit");
    }
  }
  const doc=xmlDocument(zip.get(sheetPath(zip))),rows=[];
  const data=nodes(doc,SS,"sheetData")[0];if(!data)fail("worksheet data missing");
  let widest=0,nonempty=0;
  for(const row of nodes(data,SS,"row")){
    for(const cell of Array.from(row.children).filter(e=>e.namespaceURI===SS&&e.localName==="c")){
      const [r,c]=colCoords(cell.getAttribute("r")||"");
      if(!rows[r])rows[r]=[];
      const type=cell.getAttribute("t");
      const formula=child(cell,SS,"f");
      const value=child(cell,SS,"v");
      let content="";
      if(formula&&formula.textContent)content="="+formula.textContent;
      else if(type==="s"){
        const index=Number(value?.textContent);
        if(!Number.isInteger(index)||index<0||index>=shared.length)fail("invalid shared string index");
        content=shared[index];
      }else if(type==="inlineStr"){
        content=nodes(cell,SS,"t").map(e=>e.textContent||"").join("");
      }else if(type==="b")content=value?.textContent==="1"?"TRUE":"FALSE";
      else if(value)content=value.textContent||"";
      rows[r][c]=content;widest=Math.max(widest,c+1);nonempty++;
      if(nonempty>200000)fail("too many populated cells");
    }
  }
  if(!rows.length)rows.push([""]);
  const width=Math.max(1,widest);
  return {rows:Array.from({length:rows.length},(_,r)=>Array.from({length:width},(_,c)=>rows[r]?.[c]??"")),columns:width};
}
window.EZOfficeImport={readDOCX,readXLSX};
})();