(function(){
"use strict";
function parseCSV(text){
  const rows=[],row=[];let value="",quoted=false,atStart=true;
  for(let i=0;i<text.length;i++){
    const ch=text[i];
    if(quoted){
      if(ch==='"'&&text[i+1]==='"'){value+='"';i++;}
      else if(ch==='"')quoted=false;
      else value+=ch;
    }else if(ch==='"'&&atStart){quoted=true;atStart=false;}
    else if(ch===","){row.push(value);value="";atStart=true;}
    else if(ch==="\r"||ch==="\n"){
      if(ch==="\r"&&text[i+1]==="\n")i++;
      row.push(value);rows.push(row.slice());row.length=0;value="";atStart=true;
    }else {value+=ch;atStart=false;}
  }
  if(quoted)throw Error("Unclosed quoted CSV cell");
  if(value!==""||row.length||text.length&&!/[\r\n]$/.test(text)){row.push(value);rows.push(row);}
  return rows;
}
function csvText(rows){return rows.map(row=>row.map(val=>{
  const v=String(val==null?"":val);
  return /[",\r\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v;
}).join(",")).join("\r\n")+"\r\n";}
function columnLabel(index){
  let s="",n=index+1;
  while(n>0){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}
  return s;
}
EZOffice.register("sheets",function(ctx){
  const {elem,button,root,toolbar,choose,download,message,info,markDirty}=ctx;
  const MAX_ROWS=5000,MAX_COLS=40,PAGE_SIZE=45;
  let rows=Array.from({length:12},()=>Array(6).fill("")),cols=6,page=0;
  const bar=toolbar();
  const filename=elem("input",{type:"text",value:"Table.csv","aria-label":"CSV filename"},bar);
  const summary=elem("small",{},bar);
  button(bar,"Open CSV",()=>choose(".csv,text/csv,text/plain",async file=>{
    if(file.size>2*1024*1024)throw Error("CSV file over 2 MB; use a larger spreadsheet application");
    const incoming=parseCSV(await file.text());
    if(!ctx.isActive())return;
    const width=Math.max(1,...incoming.map(row=>row.length));
    if(width>MAX_COLS||incoming.length>MAX_ROWS)throw Error("This tool supports at most 40 columns and 5,000 rows");
    rows=incoming.length?incoming:[[""]];
    cols=width;rows.forEach(row=>{while(row.length<cols)row.push("");});
    filename.value=file.name;page=0;markDirty(false);render();
    message("Loaded "+file.name+" ("+rows.length+" rows, "+cols+" columns)");
  }));
  button(bar,"Save CSV",()=>{download(filename.value.trim()||"Table.csv",csvText(rows),"text/csv;charset=utf-8");markDirty(false);},true);
  button(bar,"Add row",()=>{if(rows.length>=MAX_ROWS){message("Maximum rows reached");return;}rows.push(Array(cols).fill(""));page=Math.floor((rows.length-1)/PAGE_SIZE);markDirty(true);render();});
  button(bar,"Add column",()=>{if(cols>=MAX_COLS){message("Maximum columns reached");return;}cols++;rows.forEach(r=>r.push(""));markDirty(true);render();});
  const host=elem("div",{className:"grid-wrap"},root);
  const controls=toolbar();
  const previous=button(controls,"← Previous",()=>{page--;render();});
  const next=button(controls,"Next →",()=>{page++;render();});
  const note=elem("small",{},controls);
  function render(){
    host.replaceChildren();
    const table=elem("table",{className:"sheet"},host);
    const head=elem("thead",{},table),hrow=elem("tr",{},head);
    elem("th",{className:"row-head",text:"#"},hrow);
    for(let c=0;c<cols;c++)elem("th",{text:columnLabel(c)},hrow);
    const body=elem("tbody",{},table);
    for(let i=page*PAGE_SIZE;i<Math.min(rows.length,(page+1)*PAGE_SIZE);i++){
      const tr=elem("tr",{},body);
      elem("th",{className:"row-head",text:String(i+1)},tr);
      for(let c=0;c<cols;c++){
        const td=elem("td",{},tr);
        const input=elem("input",{type:"text",value:rows[i][c],"aria-label":columnLabel(c)+(i+1)},td);
        input.addEventListener("input",()=>{rows[i][c]=input.value;markDirty(true);});
      }
    }
    summary.textContent=rows.length+" rows × "+cols+" columns";
    note.textContent="Page "+(page+1)+" of "+Math.ceil(rows.length/PAGE_SIZE);
    previous.disabled=page<=0;next.disabled=(page+1)*PAGE_SIZE>=rows.length;
  }
  render();
  info("Handles quoted CSV cells, commas, and multiline values. Stores cell text verbatim, including leading zeros. Formulas, XLSX formatting and recalculation are not implemented. Only 45 rows are rendered per page to limit memory.");
  return ()=>{rows.length=0;host.replaceChildren();};
});
})();
