/* EZ-Office: classic scripts deliberately work from local file:// URLs.
   Exactly one tool UI is mounted at a time. No network or framework needed. */
(function(){
  "use strict";
  const root=document.getElementById("tool-root");
  const heading=document.getElementById("tool-title");
  const subtitle=document.getElementById("tool-subtitle");
  const status=document.getElementById("status");
  const buttons=[...document.querySelectorAll("[data-tool]")];
  const titles={home:["EZ-Office","Local tools, loaded only when used"],writer:["EZ Writer","Formatted documents, HTML export and print"],sheets:["EZ Sheets","Recalculating formulas and CSV workbooks"],slides:["EZ Slides","Multimedia decks with images, audio and video"],media:["EZ Media","Open local video, audio, and images"],mail:["EZ Mail","Gmail, Outlook and local email drafts"]};
  const factories=new Map(),loading=new Map();
  let current="home",destroy=null,epoch=0,dirty=false;
  function elem(tag,props,parent){
    const e=document.createElement(tag);
    Object.entries(props||{}).forEach(([k,v])=>{
      if(k==="text")e.textContent=v;
      else if(k==="className")e.className=v;
      else if(k==="value")e.value=v;
      else if(k==="onClick")e.addEventListener("click",v);
      else e.setAttribute(k,String(v));
    });
    if(parent)parent.appendChild(e);
    return e;
  }
  function button(parent,text,fn,primary){
    return elem("button",{type:"button",text,className:primary?"primary":"",onClick:fn},parent);
  }
  function message(text){status.textContent=text;}
  function download(filename,contents,mime="text/plain;charset=utf-8"){
    const blob=new Blob([contents],{type:mime});
    const url=URL.createObjectURL(blob);
    const a=elem("a",{href:url,download:filename},document.body);
    a.click();a.remove();
    window.setTimeout(()=>URL.revokeObjectURL(url),12000);
    message("Download requested: "+filename+". Original local file was not overwritten.");
  }
  function choose(accept,callback){
    const input=elem("input",{type:"file",accept},document.body);
    input.hidden=true;
    let done=false;
    function cleanup(){if(!done){done=true;input.remove();}}
    input.addEventListener("cancel",cleanup,{once:true});
    input.addEventListener("change",()=>{
      const file=input.files&&input.files[0];
      cleanup();
      if(file)Promise.resolve(callback(file)).catch(e=>message("Open failed: "+e.message));
    },{once:true});
    input.click();
    return cleanup;
  }
  function context(id){
    let alive=true;
    const disposers=[];
    return {
      root,elem,button,message,download,
      choose:(accept,callback)=>{const cancel=choose(accept,async file=>{if(alive)await callback(file);});disposers.push(cancel);},
      toolbar:()=>elem("div",{className:"toolbar"},root),
      info:text=>elem("p",{className:"info",text},root),
      onDispose:fn=>disposers.push(fn),
      isActive:()=>alive,
      markDirty:value=>{if(alive)dirty=!!value;},
      destroy:()=>{alive=false;disposers.reverse().forEach(fn=>{try{fn();}catch(e){console.error(e);}});}
    };
  }
  function load(id){
    if(factories.has(id))return Promise.resolve();
    if(loading.has(id))return loading.get(id);
    // File loading only occurs on first activation of each tool.
    const p=new Promise((resolve,reject)=>{
      const script=document.createElement("script");
      script.src="apps/"+id+".js?v=buildout-02";
      script.async=true;
      script.onload=()=>factories.has(id)?resolve():reject(Error("Tool did not register: "+id));
      script.onerror=()=>reject(Error("Cannot load "+id+".js from local application files"));
      document.head.append(script);
    });
    loading.set(id,p);
    return p;
  }
  function home(ctx){
    elem("h2",{text:"Everything you need. Nothing you don't."},root);
    elem("p",{className:"hint",text:"One shared HTML window. Tools load on demand, and their working documents and media are released when you switch. Save a copy before switching."},root);
    const tiles=elem("div",{className:"tiles"},root);
    [
      ["writer","▤","Writer","Rich text, colors, headings and printable HTML"],
      ["sheets","▦","Sheets","Real formulas, ranges and CSV workbooks"],
      ["slides","▣","Slides","Embed images, audio and video, present fullscreen"],
      ["media","▶","Media","Play local audio and video, view photos"],
      ["mail","✉","Mail","OAuth Gmail/Outlook, inbox and .eml drafts"]
    ].forEach(([id,glyph,name,desc])=>{
      const tile=button(tiles,"",()=>switchTool(id));
      tile.className="tile";
      elem("span",{text:glyph},tile);
      elem("strong",{text:name},tile);
      elem("small",{text:desc},tile);
    });
    ctx.info("Functional lightweight productivity tools. DOCX/XLSX/PPTX import is not included. Gmail/Outlook require explicit OAuth setup; no files are uploaded by default.");
  }
  function switchTool(id){
    if(!Object.hasOwn(titles,id))id="home";
    if(id===current&&root.children.length)return;
    if(dirty&&!window.confirm("This tool has unsaved edits. Close it and discard them?"))return;
    epoch++;
    const ticket=epoch;
    if(destroy){destroy();destroy=null;}
    root.replaceChildren();dirty=false;current=id;
    buttons.forEach(b=>{
      const selected=b.dataset.tool===id;
      b.classList.toggle("active",selected);
      if(selected)b.setAttribute("aria-current","page");else b.removeAttribute("aria-current");
    });
    heading.textContent=titles[id][0];subtitle.textContent=titles[id][1];
    const ctx=context(id);
    destroy=()=>ctx.destroy();
    if(id==="home"){home(ctx);message("Ready. No document or media engine is active.");return;}
    elem("p",{className:"hint",text:"Opening "+titles[id][0]+"..."},root);
    load(id).then(()=>{
      if(ticket!==epoch)return;
      root.replaceChildren();
      const cleanup=factories.get(id)(ctx);
      if(typeof cleanup==="function")ctx.onDispose(cleanup);
      message(titles[id][0]+" is ready. Only one tool is mounted.");
    }).catch(e=>{if(ticket===epoch){root.replaceChildren();elem("p",{text:e.message},root);message("Tool unavailable: "+e.message);}});
  }
  window.EZOffice={
    register(id,factory){if(!Object.hasOwn(titles,id)||id==="home"||typeof factory!=="function")throw Error("Invalid tool registration");factories.set(id,factory);},
    open:switchTool,
    // Test-only: count registered scripts and mounted controls, not heap estimates.
    inspect:()=>({current,registered:[...factories.keys()],mounted:root.querySelectorAll("*").length,dirty})
  };
  window.addEventListener("beforeunload",event=>{
    // Native browser prompt only for edits that were not saved/exported.
    if(dirty){event.preventDefault();event.returnValue="";}
  });
  buttons.forEach(b=>b.addEventListener("click",()=>switchTool(b.dataset.tool)));
  home(context("home"));
  // Resume an Outlook authorization-code redirect in the actual mail tool.
  if(new URLSearchParams(location.search).has("code")||new URLSearchParams(location.search).has("error"))switchTool("mail");
})();
