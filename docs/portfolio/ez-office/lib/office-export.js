/* Tiny dependency-free ZIP writer and basic OOXML exporters.
   Stored ZIP entries; no runtime decompressor or package-manager dependency. */
(function(){
"use strict";
const enc=new TextEncoder();
function bytes(value){if(value instanceof Uint8Array)return value;return enc.encode(String(value));}
const table=Array.from({length:256},(_,i)=>{let c=i;for(let j=0;j<8;j++)c=c&1?(c>>>1)^0xedb88320:c>>>1;return c>>>0;});
function crc32(data){let c=0xffffffff;for(const b of data)c=(c>>>8)^table[(c^b)&255];return (c^0xffffffff)>>>0;}
function u16(data,n,p){data[p]=n&255;data[p+1]=(n>>>8)&255;}
function u32(data,n,p){u16(data,n&65535,p);u16(data,(n>>>16)&65535,p+2);}
function concat(parts){const out=new Uint8Array(parts.reduce((n,x)=>n+x.length,0));let offset=0;for(const part of parts){out.set(part,offset);offset+=part.length;}return out;}
function zip(entries){
  const local=[],central=[];let offset=0;
  for(const [filename,data] of entries){
    if(!/^[\w\-./\[\]]+$/.test(filename)||filename.includes(".."))throw Error("Invalid ZIP member");
    const name=bytes(filename),content=bytes(data),crc=crc32(content);
    const h=new Uint8Array(30+name.length);
    u32(h,0x04034b50,0);u16(h,20,4);u16(h,2048,6);u16(h,0,8);u32(h,crc,14);u32(h,content.length,18);u32(h,content.length,22);u16(h,name.length,26);h.set(name,30);
    local.push(h,content);
    const d=new Uint8Array(46+name.length);
    u32(d,0x02014b50,0);u16(d,20,4);u16(d,20,6);u16(d,2048,8);u16(d,0,10);u32(d,crc,16);u32(d,content.length,20);u32(d,content.length,24);u16(d,name.length,28);u32(d,offset,42);d.set(name,46);
    central.push(d);
    offset+=h.length+content.length;
  }
  const dir=concat(central);
  const end=new Uint8Array(22);u32(end,0x06054b50,0);u16(end,entries.length,8);u16(end,entries.length,10);u32(end,dir.length,12);u32(end,offset,16);
  return new Blob([...local,dir,end],{type:"application/zip"});
}
function xml(value){return String(value??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&apos;").replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g,"");}
const declaration='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
function rel(type,target,id="rId1"){return '<Relationship Id="'+id+'" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'+type+'" Target="'+target+'"/>';}
function rels(body){return declaration+'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+body+'</Relationships>';}
const ROOT=rels(rel("officeDocument","word/document.xml"));
function docx(editor){
  const paragraphs=[];
  function runs(parent,state){
    let out="";
    for(const node of parent.childNodes){
      if(node.nodeType===3){
        if(!node.textContent)continue;
        const p=state.bold||state.italic||state.underline||state.strike||state.color;
        let props="";
        if(state.bold)props+="<w:b/>";if(state.italic)props+="<w:i/>";if(state.underline)props+='<w:u w:val="single"/>';
        if(state.strike)props+="<w:strike/>";if(state.color)props+='<w:color w:val="'+xml(state.color)+'"/>';
        out+='<w:r>'+(p?'<w:rPr>'+props+'</w:rPr>':"")+'<w:t xml:space="preserve">'+xml(node.textContent)+'</w:t></w:r>';
      }else if(node.nodeType===1){
        const tag=node.tagName,style={...state};
        if(["B","STRONG"].includes(tag))style.bold=true;
        if(["I","EM"].includes(tag))style.italic=true;
        if(tag==="U")style.underline=true;
        if(tag==="S")style.strike=true;
        if(node.style?.color){const c=node.style.color;const m=/^#([0-9a-f]{6})$/i.exec(c);if(m)style.color=m[1].toUpperCase();}
        if(tag==="BR")out+="<w:r><w:br/></w:r>";
        else out+=runs(node,style);
      }
    }
    return out;
  }
  function paragraph(node,tag="P",list=null){
    const heading=/^H[123]$/.test(tag)?Number(tag.slice(1)):0;
    const align=node.style?.textAlign||"";
    let props="";
    if(heading)props+='<w:pStyle w:val="Heading'+heading+'"/>';
    if(["left","right","center","justify"].includes(align))props+='<w:jc w:val="'+(align==="justify"?"both":align)+'"/>';
    if(list)props+='<w:ind w:left="480"/>';
    let text=runs(node,{bold:!!heading,italic:false,underline:false,strike:false,color:""});
    if(list)text='<w:r><w:t xml:space="preserve">'+(list==="OL"?"1. ":"• ")+'</w:t></w:r>'+text;
    paragraphs.push('<w:p>'+(props?'<w:pPr>'+props+'</w:pPr>':"")+text+'</w:p>');
  }
  function walk(parent){
    for(const node of parent.childNodes){
      if(node.nodeType!==1){if(node.nodeType===3&&node.textContent.trim())paragraph({childNodes:[node],style:{}});continue;}
      const tag=node.tagName;
      if(tag==="UL"||tag==="OL"){for(const child of node.children){if(child.tagName==="LI")paragraph(child,"LI",tag);}continue;}
      if(["P","DIV","H1","H2","H3","BLOCKQUOTE","LI"].includes(tag)){paragraph(node,tag);continue;}
      walk(node);
    }
  }
  walk(editor);if(!paragraphs.length)paragraph({childNodes:[],style:{}});
  const document=declaration+'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+paragraphs.join("")+'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1000" w:right="1000" w:bottom="1000" w:left="1000"/></w:sectPr></w:body></w:document>';
  const styles=declaration+'<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'+
    [1,2,3].map(n=>'<w:style w:type="paragraph" w:styleId="Heading'+n+'"><w:name w:val="heading '+n+'"/><w:pPr><w:outlineLvl w:val="'+(n-1)+'"/></w:pPr><w:rPr><w:b/><w:sz w:val="'+(40-n*6)+'"/></w:rPr></w:style>').join("")+'</w:styles>';
  return zip([
    ["[Content_Types].xml",declaration+'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'],
    ["_rels/.rels",ROOT],
    ["word/document.xml",document],
    ["word/_rels/document.xml.rels",rels(rel("styles","styles.xml"))],
    ["word/styles.xml",styles]
  ]);
}
function xlsx(rows,evaluate){
  let cells="";
  for(let r=0;r<rows.length;r++){
    let line="";
    for(let c=0;c<rows[r].length;c++){
      const raw=String(rows[r][c]??"");if(!raw)continue;
      let label="",n=c+1;while(n){n--;label=String.fromCharCode(65+n%26)+label;n=Math.floor(n/26);}
      const ref=label+(r+1);
      if(raw.startsWith("=")){
        let value="",error="";
        try{const v=evaluate(r,c);if(typeof v!=="number"||!Number.isFinite(v))throw Error("#VALUE!");value=String(v);}
        catch(e){error=String(e.message||"#ERROR!");if(!error.startsWith("#"))error="#VALUE!";}
        line+='<c r="'+ref+'"'+(error?' t="e"':"")+'><f>'+xml(raw.slice(1))+'</f><v>'+xml(error||value)+'</v></c>';
      }else if(/^-?(?:\d+\.?\d*|\.\d+)$/.test(raw)&&!(raw.length>1&&raw[0]==="0"&&raw[1]!==".")){
        line+='<c r="'+ref+'"><v>'+xml(raw)+'</v></c>';
      }else{
        line+='<c r="'+ref+'" t="inlineStr"><is><t xml:space="preserve">'+xml(raw)+'</t></is></c>';
      }
    }
    cells+='<row r="'+(r+1)+'">'+line+'</row>';
  }
  const sheet=declaration+'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"/></sheetViews><sheetFormatPr defaultRowHeight="15"/><sheetData>'+cells+'</sheetData></worksheet>';
  const workbook=declaration+'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets><calcPr calcId="191029" calcMode="auto" fullCalcOnLoad="1"/></workbook>';
  return zip([
    ["[Content_Types].xml",declaration+'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'],
    ["_rels/.rels",rels(rel("officeDocument","xl/workbook.xml"))],
    ["xl/workbook.xml",workbook],
    ["xl/_rels/workbook.xml.rels",rels(rel("worksheet","worksheets/sheet1.xml"))],
    ["xl/worksheets/sheet1.xml",sheet]
  ]);
}
function pptx(slides){
  const entries=[],overrides=[],slideRels=[],masterRels=[];
  const prs=(x,y,w,h)=>'<a:xfrm><a:off x="'+x+'" y="'+y+'"/><a:ext cx="'+w+'" cy="'+h+'"/></a:xfrm>';
  const ptx=(id,text,x,y,w,h,font=2400,color="FFFFFF",alignment="center")=>{
    const direction={left:"l",center:"ctr",right:"r"}[alignment]||"ctr";
    const content=String(text??"").replace(/\r\n?/g,"\n").split("\n").map(line=>
      '<a:p><a:pPr algn="'+direction+'"/><a:r><a:rPr lang="en-US" sz="'+font+'"><a:solidFill><a:srgbClr val="'+color+'"/></a:solidFill></a:rPr><a:t xml:space="preserve">'+xml(line)+'</a:t></a:r><a:endParaRPr lang="en-US"/></a:p>'
    ).join("");
    return '<p:sp><p:nvSpPr><p:cNvPr id="'+id+'" name="Text '+id+'"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr>'+prs(x,y,w,h)+'</p:spPr><p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>'+content+'</p:txBody></p:sp>';
  };
  const bg={night:"182A40",lime:"A3EF69",paper:"FCFAF3",sunset:"953F67"};
  const fg={night:"FFFFFF",lime:"152A13",paper:"18232C",sunset:"FFFFFF"};
  const slideSizeX=12192000,slideSizeY=6858000;
  for(let i=0;i<slides.length;i++){
    const s=slides[i],index=i+1;
    let relset=rel("slideLayout","../slideLayouts/slideLayout1.xml");
    let pic="",note="";
    if(s.media){
      note=s.media.name||"Embedded media";
      const match=/^data:([-\w/.+]+);base64,([A-Za-z0-9+/=]+)$/.exec(s.media.data);
      if(match){
        const ext=({["image/png"]:"png",["image/jpeg"]:"jpg",["image/webp"]:"webp",["image/gif"]:"gif",["audio/mpeg"]:"mp3",["audio/mp4"]:"m4a",["audio/wav"]:"wav",["audio/ogg"]:"ogg",["audio/webm"]:"webm",["video/mp4"]:"mp4",["video/webm"]:"webm",["video/ogg"]:"ogv"})[match[1]];
        if(ext){
          const mediaPath="ppt/media/media"+index+"."+ext;
          const raw=atob(match[2]),bin=new Uint8Array(raw.length);for(let j=0;j<raw.length;j++)bin[j]=raw.charCodeAt(j);
          entries.push([mediaPath,bin]);
          if(match[1].startsWith("image/")){
            relset+=rel("image","../media/media"+index+"."+ext,"rId2");
            pic='<p:pic><p:nvPicPr><p:cNvPr id="4" name="'+xml(note)+'"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="rId2"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr>'+prs(3600000,3300000,4900000,3000000)+'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>';
          }else{
            relset+=rel(match[1].startsWith("video/")?"video":"audio","../media/media"+index+"."+ext,"rId2");
            note=note+" (embedded "+(match[1].startsWith("video/")?"video":"audio")+" media; playback support varies by PowerPoint version)";
          }
        }
      }
    }
    const shade=bg[s.theme]||bg.night,ink=fg[s.theme]||fg.night;
    const title=ptx(2,s.title||"",500000,450000,11200000,1800000,3600,ink);
    const body=ptx(3,s.body||"",800000,2450000,10500000,pic?1100000:3100000,2100,ink,s.align);
    const more=note&&!pic?ptx(5,"Media: "+note,900000,5700000,10200000,450000,1300,ink):"";
    const slide=declaration+'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="'+shade+'"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'+title+body+pic+more+'</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>';
    entries.push(["ppt/slides/slide"+index+".xml",slide]);
    entries.push(["ppt/slides/_rels/slide"+index+".xml.rels",rels(relset)]);
    overrides.push('<Override PartName="/ppt/slides/slide'+index+'.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>');
    slideRels.push(rel("slide","slides/slide"+index+".xml","rId"+(index+1)));
  }
  const pres=declaration+'<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>'+slides.map((_,i)=>'<p:sldId id="'+(256+i)+'" r:id="rId'+(i+2)+'"/>').join("")+'</p:sldIdLst><p:sldSz cx="'+slideSizeX+'" cy="'+slideSizeY+'" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>';
  const master=declaration+'<p:sldMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>';
  const layout=declaration+'<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>';
  const theme=declaration+'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="EZ Office"><a:themeElements><a:clrScheme name="EZ"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1><a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'+["dk2","lt2","accent1","accent2","accent3","accent4","accent5","accent6","hlink","folHlink"].map(t=>'<a:'+t+'><a:srgbClr val="628A65"/></a:'+t+'>').join("")+'</a:clrScheme><a:fontScheme name="EZ"><a:majorFont><a:latin typeface="Aptos Display"/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/></a:minorFont></a:fontScheme><a:fmtScheme name="EZ"><a:fillStyleLst><a:solidFill><a:schemeClr val="accent1"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="accent1"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="lt1"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>';
  const other=entries.filter(([name])=>name.startsWith("ppt/media/"));
  const extensions=[...new Set(other.map(([name])=>name.split(".").pop()))];
  const typeMap={jpg:"image/jpeg",png:"image/png",gif:"image/gif",webp:"image/webp",mp3:"audio/mpeg",m4a:"audio/mp4",wav:"audio/wav",ogg:"audio/ogg",webm:"video/webm",mp4:"video/mp4",ogv:"video/ogg"};
  const types=declaration+'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'+extensions.map(t=>'<Default Extension="'+t+'" ContentType="'+typeMap[t]+'"/>').join("")+
    '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/><Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'+overrides.join("")+'</Types>';
  entries.push(["[Content_Types].xml",types],["_rels/.rels",rels(rel("officeDocument","ppt/presentation.xml"))],
    ["ppt/presentation.xml",pres],["ppt/_rels/presentation.xml.rels",rels(rel("slideMaster","slideMasters/slideMaster1.xml","rId1")+slideRels.join(""))],
    ["ppt/slideMasters/slideMaster1.xml",master],["ppt/slideMasters/_rels/slideMaster1.xml.rels",rels(rel("slideLayout","../slideLayouts/slideLayout1.xml")+rel("theme","../theme/theme1.xml","rId2"))],
    ["ppt/slideLayouts/slideLayout1.xml",layout],["ppt/slideLayouts/_rels/slideLayout1.xml.rels",rels(rel("slideMaster","../slideMasters/slideMaster1.xml"))],
    ["ppt/theme/theme1.xml",theme]);
  return zip(entries);
}
window.EZOfficeExport={docx,xlsx,pptx,zip,xml};
})();