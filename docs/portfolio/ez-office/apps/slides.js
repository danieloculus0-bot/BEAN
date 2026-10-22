(function(){
"use strict";
EZOffice.register("slides",function(ctx){
  const {elem,button,root,toolbar,choose,download,message,info,markDirty,onDispose}=ctx;
  let slide=0;
  const bar=toolbar();
  const name=elem("input",{type:"text",value:"Presentation.txt","aria-label":"Deck filename"},bar);
  const source=elem("textarea",{className:"document","aria-label":"Slide deck text"},root);
  source.style.minHeight="170px";
  source.value="My Presentation\nA small slide deck\n\n---\n\nSecond Slide\nAdd your content here";
  const controls=toolbar();
  const status=elem("small",{},controls);
  const stage=elem("div",{className:"slide-preview",tabindex:"0","aria-label":"Current slide"},root);
  function pages(){return source.value.split(/^\s*---\s*$/m).map(s=>s.trim());}
  function render(){const list=pages();slide=Math.max(0,Math.min(slide,list.length-1));stage.textContent=list[slide]||"Empty slide";status.textContent="Slide "+(slide+1)+" / "+list.length;}
  button(bar,"Open deck",()=>choose(".txt,.md,text/plain",async file=>{
    if(file.size>1024*1024)throw Error("Text deck exceeds 1 MB");
    const text=await file.text();
    if(!ctx.isActive())return;
    source.value=text;name.value=file.name;slide=0;render();markDirty(false);
    message("Opened "+file.name);
  }));
  button(bar,"Save copy",()=>{download(name.value.trim()||"Presentation.txt",source.value);markDirty(false);},true);
  button(controls,"← Previous",()=>{slide--;render();});
  button(controls,"Next →",()=>{slide++;render();});
  button(controls,"Present fullscreen",()=>{
    if(!stage.requestFullscreen){message("Fullscreen is unavailable in this browser");return;}
    stage.requestFullscreen().catch(e=>message("Fullscreen unavailable: "+e.message));
  });
  source.addEventListener("input",()=>{markDirty(true);slide=0;render();});
  function keydown(e){
    if(e.target===source||e.target===name)return;
    if(e.key==="ArrowRight"||e.key==="PageDown"){slide++;render();}
    else if(e.key==="ArrowLeft"||e.key==="PageUp"){slide--;render();}
  }
  document.addEventListener("keydown",keydown);
  onDispose(()=>{document.removeEventListener("keydown",keydown);if(document.fullscreenElement===stage)document.exitFullscreen().catch(()=>{});});
  render();
  info("Separate slides with a line containing ---. Type and preview instantly, navigate with arrow keys, present fullscreen, and save an editable text deck. PowerPoint import/export is not supported.");
  return ()=>{source.value="";};
});
})();
