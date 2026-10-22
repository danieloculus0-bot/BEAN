(function(){
"use strict";
EZOffice.register("writer",function(ctx){
  const {elem,button,root,toolbar,message,download,choose,info,markDirty,onDispose}=ctx;
  let filename="Untitled.txt",dirty=false;
  const actions=toolbar();
  const name=elem("input",{type:"text",value:filename,"aria-label":"Document filename"},actions);
  const stats=elem("small",{text:"0 words · 0 characters"},actions);
  const textarea=elem("textarea",{className:"document",spellcheck:"true","aria-label":"Document editor",placeholder:"Write here. Open a .txt or .md file, or start a new document."},root);
  function mark(value){dirty=value;markDirty(value);}
  function tally(){
    const t=textarea.value.trim();
    const words=t?t.split(/\s+/u).length:0;
    stats.textContent=words.toLocaleString()+" words · "+textarea.value.length.toLocaleString()+" characters";
  }
  function save(){
    const file=(name.value.trim()||"Untitled.txt").replace(/[\\/]/g,"_");
    download(file,textarea.value,"text/plain;charset=utf-8");
    filename=file;mark(false);
  }
  button(actions,"Open",()=>choose(".txt,.md,.markdown,.log,.json,.csv,text/plain",async file=>{
    if(file.size>5*1024*1024)throw Error("Text file exceeds this editor's 5 MB limit");
    if(dirty&&!window.confirm("Discard unsaved changes and open another file?"))return;
    const contents=await file.text();
    if(!ctx.isActive())return;
    textarea.value=contents;name.value=file.name;filename=file.name;mark(false);tally();
    message("Opened "+file.name+" ("+file.size.toLocaleString()+" bytes)");
  }));
  button(actions,"Save copy",save,true);
  button(actions,"New",()=>{
    if(dirty&&!window.confirm("Discard unsaved changes?"))return;
    textarea.value="";name.value="Untitled.txt";mark(false);tally();
  });
  function keydown(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="s"){e.preventDefault();save();}}
  document.addEventListener("keydown",keydown);
  onDispose(()=>document.removeEventListener("keydown",keydown));
  textarea.addEventListener("input",()=>{mark(true);tally();});
  info("Plain text and Markdown. Ctrl/Cmd+S exports a new local file; it does not silently overwrite the original. The browser's native text undo and spell-check remain available.");
  return ()=>{textarea.value="";};
});
})();
