/* EZ Sheets: bounded CSV worksheet with a real, sandboxed recursive-descent formula evaluator. */
(function(){
"use strict";
function parseCSV(text){
  const rows=[],row=[];let value="",quoted=false,first=true;
  for(let i=0;i<text.length;i++){
    const ch=text[i];
    if(quoted){
      if(ch==='"'&&text[i+1]==='"'){value+='"';i++;}
      else if(ch==='"')quoted=false;
      else value+=ch;
    }else if(ch==='"'&&first){quoted=true;first=false;}
    else if(ch===","){row.push(value);value="";first=true;}
    else if(ch==="\r"||ch==="\n"){
      if(ch==="\r"&&text[i+1]==="\n")i++;
      row.push(value);rows.push(row.slice());row.length=0;value="";first=true;
    }else{value+=ch;first=false;}
  }
  if(quoted)throw Error("Unclosed quoted CSV cell");
  if(value!==""||row.length||(text.length&&!/[\r\n]$/.test(text))){row.push(value);rows.push(row);}
  return rows;
}
function csvText(rows){return rows.map(row=>row.map(v=>{
  const text=String(v??"");return /[",\r\n]/.test(text)?'"'+text.replace(/"/g,'""')+'"':text;
}).join(",")).join("\r\n")+"\r\n";}
function colLabel(i){let s="";for(let n=i+1;n>0;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
function cellCoords(ref){
  const m=/^([A-Z]+)([1-9]\d*)$/.exec(ref);
  if(!m)throw Error("#REF!");
  let col=0;for(const ch of m[1])col=col*26+ch.charCodeAt(0)-64;
  return [Number(m[2])-1,col-1];
}
function calculate(rows,r,c,cache=new Map(),visiting=new Set()){
  const key=r+":"+c;if(cache.has(key))return cache.get(key);
  if(visiting.has(key))throw Error("#CYCLE!");
  if(r<0||r>=rows.length||c<0||c>=(rows[0]||[]).length)throw Error("#REF!");
  visiting.add(key);
  try{
    const raw=String(rows[r][c]??"");
    let result=raw;
    if(raw.startsWith("=")){
      const source=raw.slice(1).toUpperCase();
      const tokens=[];const re=/\s*([A-Z]+[1-9]\d*|\d+(?:\.\d+)?|[A-Z_]+|[()+\-*/^,:])\s*/gy;
      let pos=0;while(pos<source.length){
        re.lastIndex=pos;const m=re.exec(source);
        if(!m)throw Error("#PARSE!");
        tokens.push(m[1]);pos=re.lastIndex;
        if(tokens.length>1000)throw Error("#LIMIT!");
      }
      let at=0;
      function peek(){return tokens[at];}
      function eat(tok){if(peek()===tok){at++;return true;}return false;}
      function expect(tok){if(!eat(tok))throw Error("#PARSE!");}
      function number(v){
        if(Array.isArray(v))throw Error("#VALUE!");
        if(typeof v==="string"&&v.startsWith("#"))throw Error(v);
        if(v===""||v==null)return 0;
        const n=Number(v);if(!Number.isFinite(n))throw Error("#VALUE!");
        return n;
      }
      function factor(){
        if(eat("+"))return number(factor());
        if(eat("-"))return -number(factor());
        if(eat("(")){const v=expression();expect(")");return v;}
        const tok=tokens[at++];if(!tok)throw Error("#PARSE!");
        if(/^\d/.test(tok))return Number(tok);
        if(/^[A-Z]+[1-9]\d*$/.test(tok)){
          const [rr,cc]=cellCoords(tok);
          if(eat(":")){
            const end=tokens[at++];
            const [r2,c2]=cellCoords(end||"");
            if(rr>r2||cc>c2||(r2-rr+1)*(c2-cc+1)>5000)throw Error("#LIMIT!");
            const values=[];
            for(let y=rr;y<=r2;y++)for(let x=cc;x<=c2;x++)values.push(calculate(rows,y,x,cache,visiting));
            return values;
          }
          return calculate(rows,rr,cc,cache,visiting);
        }
        if(/^[A-Z_]+$/.test(tok)){
          expect("(");const args=[];
          if(!eat(")")){do{args.push(expression());}while(eat(","));expect(")");}
          const vals=args.flatMap(x=>Array.isArray(x)?x:[x]);
          const nums=vals.filter(x=>x!==""&&x!=null).map(number);
          if(tok==="SUM")return nums.reduce((a,b)=>a+b,0);
          if(tok==="AVERAGE"||tok==="AVG")return nums.length?nums.reduce((a,b)=>a+b,0)/nums.length:0;
          if(tok==="MIN")return nums.length?Math.min(...nums):0;
          if(tok==="MAX")return nums.length?Math.max(...nums):0;
          if(tok==="COUNT")return nums.length;
          if(tok==="IF"){if(args.length!==3)throw Error("#ARGS!");return number(args[0])?args[1]:args[2];}
          throw Error("#NAME?");
        }
        throw Error("#PARSE!");
      }
      function power(){const v=factor();return eat("^")?Math.pow(number(v),number(power())):v;}
      function term(){let v=power();while(peek()==="*"||peek()==="/"){const op=tokens[at++],b=number(power()),a=number(v);if(op==="/"&&b===0)throw Error("#DIV/0!");v=op==="*"?a*b:a/b;}return v;}
      function expression(){let v=term();while(peek()==="+"||peek()==="-"){const op=tokens[at++],b=number(term()),a=number(v);v=op==="+"?a+b:a-b;}return v;}
      result=expression();if(at!==tokens.length)throw Error("#PARSE!");
      if(Array.isArray(result))throw Error("#VALUE!");
      if(typeof result==="number"&&!Number.isFinite(result))throw Error("#NUM!");
    }
    cache.set(key,result);return result;
  }finally{visiting.delete(key);}
}
EZOffice.register("sheets",function(ctx){
  const {elem,button,root,toolbar,choose,download,message,info,markDirty,onDispose}=ctx;
  const MAX_ROWS=5000,MAX_COLS=40,PAGE_SIZE=35,CELL_WIDTH=144,ROW_HEIGHT=76;
  let rows=Array.from({length:15},()=>Array(8).fill("")),cols=8,page=0,frame=0;
  rows[0].splice(0,4,"Item","Qty","Price","Total");
  rows[1].splice(0,4,"Sheet metal",2,125,"=B2*C2");
  rows[2].splice(0,4,"Fasteners",10,4.5,"=B3*C3");
  rows[3].splice(0,4,"Grand total","","","=SUM(D2:D3)");
  const bar=toolbar(),filename=elem("input",{type:"text",value:"Estimate.csv","aria-label":"Sheet filename"},bar);
  const summary=elem("small",{},bar);
  // Fixed coordinate headers live OUTSIDE the scrolling cell viewport.
  // No sticky table cells, no frozen data cells, no overlapping scroll layers.
  const sheetFrame=elem("div",{className:"sheet-frame"},root);
  sheetFrame.style.setProperty("--sheet-cell-width",CELL_WIDTH+"px");
  sheetFrame.style.setProperty("--sheet-row-height",ROW_HEIGHT+"px");
  elem("div",{className:"sheet-corner",text:"#","aria-label":"Row and column corner"},sheetFrame);
  const topHeader=elem("div",{className:"sheet-x-header","aria-label":"Column labels"},sheetFrame);
  const columnStrip=elem("div",{className:"sheet-x-strip"},topHeader);
  const sideHeader=elem("div",{className:"sheet-y-header","aria-label":"Row numbers"},sheetFrame);
  const rowStrip=elem("div",{className:"sheet-y-strip"},sideHeader);
  const host=elem("div",{className:"grid-wrap",tabindex:"0","aria-label":"Scrollable spreadsheet cells"},sheetFrame);
  const controls=toolbar();
  const jumpField=elem("input",{type:"text",placeholder:"A1","aria-label":"Go to cell reference"},controls);
  button(controls,"Go to cell",()=>{
    try{
      const [r,c]=cellCoords(jumpField.value.trim().toUpperCase());
      if(r<0||r>=rows.length||c<0||c>=cols)throw Error("Cell outside current sheet");
      page=Math.floor(r/PAGE_SIZE);render();
      host.scrollLeft=c*CELL_WIDTH;
      host.scrollTop=(r-page*PAGE_SIZE)*ROW_HEIGHT;
      syncHeaders();
      const target=host.querySelector('[aria-label="'+colLabel(c)+(r+1)+'"]');
      if(target)target.focus({preventScroll:true});
      message("Selected "+colLabel(c)+(r+1));
    }catch(e){message("Go to cell failed: "+e.message);}
  });
  function syncHeaders(){
    columnStrip.style.transform="translate3d("+(-host.scrollLeft)+"px,0,0)";
    rowStrip.style.transform="translate3d(0,"+(-host.scrollTop)+"px,0)";
  }
  host.addEventListener("scroll",syncHeaders,{passive:true});
  const back=button(controls,"← Previous",()=>{page--;render();});
  const next=button(controls,"Next →",()=>{page++;render();});
  const counter=elem("small",{},controls);
  function values(){return rows.map(r=>Array.from({length:cols},(_,i)=>String(r[i]??"")));}
  function refresh(){
    const cache=new Map();
    host.querySelectorAll("[data-result]").forEach(node=>{
      const [r,c]=node.dataset.result.split(":").map(Number);
      try{const v=calculate(rows,r,c,cache);node.textContent=String(v);node.title="Calculated value";node.classList.remove("formula-error");}
      catch(e){node.textContent=e.message.startsWith("#")?e.message:"#ERROR!";node.classList.add("formula-error");}
    });
  }
  function schedule(){if(frame)cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{frame=0;refresh();});}
  function render(){
    const x=host.scrollLeft,y=host.scrollTop;
    host.replaceChildren();columnStrip.replaceChildren();rowStrip.replaceChildren();
    for(let c=0;c<cols;c++)elem("div",{className:"sheet-axis-cell",text:colLabel(c)},columnStrip);
    const table=elem("table",{className:"sheet","aria-label":"Spreadsheet data"},host);
    table.style.width=(cols*CELL_WIDTH)+"px";
    const cg=elem("colgroup",{},table);
    for(let c=0;c<cols;c++)elem("col",{width:String(CELL_WIDTH)},cg);
    const body=elem("tbody",{},table);
    for(let r=page*PAGE_SIZE;r<Math.min(rows.length,(page+1)*PAGE_SIZE);r++){
      elem("div",{className:"sheet-index-cell",text:String(r+1)},rowStrip);
      const tr=elem("tr",{},body);
      for(let c=0;c<cols;c++){
        const td=elem("td",{},tr);
        const raw=String(rows[r][c]??"");
        const input=elem("input",{type:"text",value:raw,"aria-label":colLabel(c)+(r+1)},td);
        const output=elem("output",{"data-result":r+":"+c,className:"formula-result"},td);
        if(!raw.startsWith("="))output.hidden=true;
        input.addEventListener("input",()=>{rows[r][c]=input.value;output.hidden=!input.value.startsWith("=");markDirty(true);schedule();});
        input.addEventListener("paste",event=>{
          const pasted=event.clipboardData?.getData("text/plain");
          if(!pasted||!/[\t\r\n]/.test(pasted))return;
          const lines=pasted.replace(/\r\n/g,"\n").replace(/\r/g,"\n").replace(/\n$/,"").split("\n");
          const cells=lines.map(line=>line.split("\t"));
          const width=Math.max(0,...cells.map(line=>line.length));
          if(r+cells.length>MAX_ROWS||c+width>MAX_COLS){
            event.preventDefault();message("Paste exceeds sheet size limits (5,000 rows / 40 columns)");return;
          }
          event.preventDefault();
          cols=Math.max(cols,c+width);
          while(rows.length<r+cells.length)rows.push(Array(cols).fill(""));
          for(const row of rows)while(row.length<cols)row.push("");
          for(let y=0;y<cells.length;y++)for(let x=0;x<cells[y].length;x++)rows[r+y][c+x]=cells[y][x];
          markDirty(true);render();message("Pasted "+cells.length+" row(s) × "+width+" column(s) into "+colLabel(c)+(r+1));
        });
      }
    }
    summary.textContent=rows.length+" rows × "+cols+" columns";
    counter.textContent="Page "+(page+1)+" / "+Math.ceil(rows.length/PAGE_SIZE);
    back.disabled=page===0;next.disabled=(page+1)*PAGE_SIZE>=rows.length;
    refresh();
    host.scrollLeft=x;host.scrollTop=y;
    syncHeaders();
  }
  function setRows(input,name){
    if(!Array.isArray(input)||input.length>MAX_ROWS||input.some(r=>!Array.isArray(r)||r.length>MAX_COLS))throw Error("Grid exceeds 5,000 rows or 40 columns");
    cols=Math.max(1,...input.map(r=>r.length));rows=(input.length?input:[[""]]).map(r=>Array.from({length:cols},(_,i)=>String(r[i]??"")));
    filename.value=name;page=0;markDirty(false);render();message("Opened "+name);
  }
  button(bar,"Open CSV",()=>choose(".csv,text/csv,text/plain",async file=>{
    if(file.size>2*1024*1024)throw Error("CSV larger than 2 MB");
    const parsed=parseCSV(await file.text());if(ctx.isActive())setRows(parsed,file.name);
  }));
  button(bar,"Open workbook",()=>choose(".ezsheet,.json,application/json",async file=>{
    if(file.size>2*1024*1024)throw Error("Workbook larger than 2 MB");
    const data=JSON.parse(await file.text());if(data.format!=="EZSheet-1")throw Error("Unsupported workbook format");
    if(ctx.isActive())setRows(data.rows,file.name);
  }));
  button(bar,"Save XLSX",()=>{
    const filenameX=(filename.value.replace(/.(csv|json|ezsheet|xlsx)$/i,"")||"Workbook")+".xlsx";
    const blob=EZOfficeExport.xlsx(values(),(r,c)=>calculate(rows,r,c));
    download(filenameX,blob,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
    markDirty(false);
  },true);
  button(bar,"Print / PDF",()=>window.print());
  button(bar,"Save CSV",()=>{download((filename.value||"Sheet.csv").replace(/\.(ezsheet|json)$/i,".csv"),csvText(values()),"text/csv;charset=utf-8");markDirty(false);},true);
  button(bar,"Save workbook",()=>{download("Workbook.ezsheet",JSON.stringify({format:"EZSheet-1",rows:values()}),"application/json");markDirty(false);});
  button(bar,"Add row",()=>{if(rows.length>=MAX_ROWS){message("Row limit reached");return;}rows.push(Array(cols).fill(""));page=Math.floor((rows.length-1)/PAGE_SIZE);markDirty(true);render();});
  button(bar,"Add column",()=>{if(cols>=MAX_COLS){message("Column limit reached");return;}cols++;rows.forEach(r=>r.push(""));markDirty(true);render();});
  onDispose(()=>{if(frame)cancelAnimationFrame(frame);rows.length=0;});
  render();
  info("Export real .xlsx for Excel/LibreOffice, CSV, .ezsheet with formulas, or Print / Save PDF. Paste tabular ranges from a spreadsheet and jump directly to a cell. Functional formulas: =A1*B1, =SUM(A1:A9), AVERAGE, MIN, MAX, COUNT, IF, arithmetic, powers and references. Circular references and division by zero report errors. CSV preserves formula text; .ezsheet preserves editable formulas. XLSX import remains unsupported.");
});
})();