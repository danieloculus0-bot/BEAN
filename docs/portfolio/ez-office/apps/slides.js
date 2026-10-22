/* EZ Slides: offline, media-capable presentation editor using a bounded JSON deck format. */
(function(){
"use strict";
const MIME=/^data:(image\/(?:png|jpeg|webp|gif)|audio\/(?:mpeg|wav|ogg|mp4|webm)|video\/(?:mp4|webm|ogg));base64,[a-z0-9+/=]+$/i;
const THEMES=["night","lime","paper","sunset"];
const sample=()=>({title:"New slide",body:"Write your key message here.",notes:"",theme:"night",align:"center",media:null});
function valid(data){
  if(!data||data.format!=="EZSlides-2"||!Array.isArray(data.slides)||!data.slides.length||data.slides.length>100)throw Error("Unsupported deck: expected EZSlides-2, 1–100 slides");
  return data.slides.map(item=>{
    if(!item||typeof item!=="object")throw Error("Invalid slide");
    const slide={
      title:String(item.title??"").slice(0,250),body:String(item.body??"").slice(0,8000),
      notes:String(item.notes??"").slice(0,4000),theme:THEMES.includes(item.theme)?item.theme:"night",
      align:["left","center","right"].includes(item.align)?item.align:"center",media:null
    };
    if(item.media){
      if(typeof item.media.data!=="string"||item.media.data.length>11*1024*1024||!MIME.test(item.media.data))throw Error("Invalid or oversized embedded media");
      const kind=item.media.data.startsWith("data:image/")?"image":item.media.data.startsWith("data:audio/")?"audio":"video";
      slide.media={kind,name:String(item.media.name||"Media").slice(0,150),data:item.media.data};
    }
    return slide;
  });
}
EZOffice.register("slides",function(ctx){
  const {elem,button,root,toolbar,choose,download,message,info,markDirty,onDispose}=ctx;
  let deck=[{title:"Welcome to EZ Slides",body:"Build rich slides with images, audio and video.\nUse the controls to edit or present.",notes:"Presenter notes go here",theme:"night",align:"center",media:null},sample()],at=0;
  const bar=toolbar(),name=elem("input",{type:"text",value:"Presentation.ezslides","aria-label":"Deck filename"},bar);
  const deckTools=toolbar();
  const sidebar=elem("div",{className:"slide-editor-layout"},root);
  const panel=elem("div",{className:"slide-controls"},sidebar);
  elem("label",{text:"Title"},panel);
  const title=elem("input",{type:"text","aria-label":"Slide title"},panel);
  elem("label",{text:"Body text"},panel);
  const body=elem("textarea",{"aria-label":"Slide body",rows:"6"},panel);
  elem("label",{text:"Presenter notes"},panel);
  const notes=elem("textarea",{"aria-label":"Slide notes",rows:"3"},panel);
  elem("label",{text:"Theme"},panel);
  const theme=elem("select",{"aria-label":"Slide theme"},panel);
  for(const t of THEMES)elem("option",{value:t,text:t[0].toUpperCase()+t.slice(1)},theme);
  elem("label",{text:"Text alignment"},panel);
  const align=elem("select",{"aria-label":"Text alignment"},panel);
  for(const value of ["left","center","right"])elem("option",{value,text:value},align);
  const attach=elem("div",{className:"toolbar"},panel);
  const stage=elem("div",{className:"slide-preview",tabindex:"0","aria-label":"Current slide"},sidebar);
  const pages=elem("small",{},deckTools);
  function loadFields(){
    const s=deck[at];title.value=s.title;body.value=s.body;notes.value=s.notes;theme.value=s.theme;align.value=s.align;
  }
  function repaint(){
    const s=deck[at];
    stage.className="slide-preview slide-theme-"+s.theme;
    stage.style.textAlign=s.align;
    stage.replaceChildren();
    const wrap=elem("div",{className:"slide-inner"},stage);
    elem("h2",{className:"slide-heading",text:s.title},wrap);
    elem("p",{className:"slide-copy",text:s.body},wrap);
    if(s.media){
      const tag={image:"img",audio:"audio",video:"video"}[s.media.kind];
      const media=elem(tag,{src:s.media.data,"aria-label":s.media.name,className:"slide-media"},wrap);
      if(tag==="img")media.alt=s.media.name;
      else{media.controls=true;media.preload="metadata";media.playsInline=true;}
    }
    pages.textContent="Slide "+(at+1)+" / "+deck.length;
  }
  function changeSlide(next){
    if(next<0||next>=deck.length)return;
    stage.querySelectorAll("video,audio").forEach(e=>e.pause());
    at=next;loadFields();repaint();
  }
  function changed(){const s=deck[at];s.title=title.value;s.body=body.value;s.notes=notes.value;s.theme=theme.value;s.align=align.value;markDirty(true);repaint();}
  for(const field of [title,body,notes,theme,align])field.addEventListener(field.tagName==="SELECT"?"change":"input",changed);
  button(bar,"Open deck",()=>choose(".ezslides,.json,.txt",async file=>{
    if(file.size>23*1024*1024)throw Error("Deck larger than 23 MB");
    if(file.name.toLowerCase().endsWith(".txt")){
      const slides=(await file.text()).split(/^\s*---\s*$/m).map(t=>({title:t.trim().split("\n")[0]||"Untitled",body:t.trim().split("\n").slice(1).join("\n"),notes:"",theme:"night",align:"center",media:null}));
      if(ctx.isActive()){deck=slides.slice(0,100);at=0;name.value="Presentation.ezslides";loadFields();repaint();markDirty(true);}
    }else{
      const data=JSON.parse(await file.text());
      const parsed=valid(data);
      if(ctx.isActive()){deck=parsed;at=0;name.value=file.name;loadFields();repaint();markDirty(false);}
    }
    message("Deck opened");
  }));
  button(bar,"Save PowerPoint",()=>{
    download((name.value.replace(/.(ezslides|pptx|txt|json)$/i,"")||"Presentation")+".pptx",
      EZOfficeExport.pptx(deck),"application/vnd.openxmlformats-officedocument.presentationml.presentation");
    markDirty(false);
  },true);
  button(bar,"Save deck",()=>{
    download(name.value||"Presentation.ezslides",JSON.stringify({format:"EZSlides-2",slides:deck}),"application/json");
    markDirty(false);
  },true);
  // Print the ENTIRE slide deck, not just the currently previewed slide.
  function printDeck(){
    const printable=elem("div",{className:"slides-print-pages"},root);
    for(const s of deck){
      const page=elem("section",{className:"print-slide slide-theme-"+s.theme},printable);
      page.style.textAlign=s.align;
      elem("h1",{text:s.title},page);
      elem("p",{text:s.body},page);
      if(s.media){
        if(s.media.kind==="image"){const img=elem("img",{src:s.media.data,alt:s.media.name},page);img.className="slide-print-image";}
        else elem("p",{text:"Embedded "+s.media.kind+": "+s.media.name+" (available in the editable deck)"},page);
      }
    }
    const cleanup=()=>{printable.remove();window.removeEventListener("afterprint",cleanup);};
    window.addEventListener("afterprint",cleanup,{once:true});
    window.print();
  }
  button(bar,"Print / PDF",printDeck);
  button(deckTools,"← Previous",()=>changeSlide(at-1));
  button(deckTools,"Next →",()=>changeSlide(at+1));
  button(deckTools,"New slide",()=>{
    if(deck.length>=100){message("100-slide limit");return;}
    deck.splice(at+1,0,sample());markDirty(true);changeSlide(at+1);
  });
  button(deckTools,"Duplicate",()=>{
    if(deck.length>=100){message("100-slide limit");return;}
    deck.splice(at+1,0,structuredClone(deck[at]));markDirty(true);changeSlide(at+1);
  });
  button(deckTools,"Delete",()=>{
    if(deck.length===1){deck[0]=sample();changeSlide(0);}
    else{deck.splice(at,1);changeSlide(Math.min(at,deck.length-1));}
    markDirty(true);
  });
  button(deckTools,"Move earlier",()=>{if(at<1)return;[deck[at-1],deck[at]]=[deck[at],deck[at-1]];at--;markDirty(true);changeSlide(at);});
  button(deckTools,"Move later",()=>{if(at>=deck.length-1)return;[deck[at+1],deck[at]]=[deck[at],deck[at+1]];at++;markDirty(true);changeSlide(at);});
  button(deckTools,"Present fullscreen",()=>{
    if(!stage.requestFullscreen){message("Fullscreen unavailable");return;}
    stage.requestFullscreen().catch(e=>message("Fullscreen unavailable: "+e.message));
  });
  button(attach,"Insert image / audio / video",()=>choose("image/png,image/jpeg,image/webp,image/gif,audio/mpeg,audio/wav,audio/ogg,audio/mp4,audio/webm,video/mp4,video/webm,video/ogg",async file=>{
    const mime=file.type;
    if(file.size>8*1024*1024)throw Error("Embedded media limit is 8 MB per asset");
    if(!/^(image\/(png|jpeg|webp|gif)|audio\/(mpeg|wav|ogg|mp4|webm)|video\/(mp4|webm|ogg))$/.test(mime))throw Error("Unsupported media type");
    // FileReader generates a self-contained data URL for offline presentation saving.
    const data=await new Promise((resolve,reject)=>{
      const reader=new FileReader();reader.onerror=()=>reject(Error("Could not read media"));reader.onload=()=>resolve(reader.result);reader.readAsDataURL(file);
    });
    if(!ctx.isActive())return;
    const otherBytes=JSON.stringify({format:"EZSlides-2",slides:deck}).length-(deck[at].media?.data.length||0);
    if(otherBytes+data.length>22*1024*1024)throw Error("Deck would exceed the 22 MB media budget");
    deck[at].media={kind:mime.split("/")[0],name:file.name,data};
    markDirty(true);repaint();message("Embedded "+file.name+" in this slide");
  }));
  button(attach,"Remove media",()=>{deck[at].media=null;markDirty(true);repaint();});
  function keydown(e){
    if(["INPUT","TEXTAREA","SELECT"].includes(e.target.tagName))return;
    if(["ArrowRight","PageDown"].includes(e.key)){changeSlide(at+1);}
    if(["ArrowLeft","PageUp"].includes(e.key)){changeSlide(at-1);}
  }
  document.addEventListener("keydown",keydown);
  onDispose(()=>{
    document.removeEventListener("keydown",keydown);
    stage.querySelectorAll("video,audio").forEach(e=>e.pause());
    if(document.fullscreenElement===stage)document.exitFullscreen().catch(()=>{});
    deck.length=0;stage.replaceChildren();
  });
  loadFields();repaint();
  info("Export real .pptx for PowerPoint/LibreOffice with slide text, themes and image media; embedded audio/video remains in .ezslides and is stored as media in PPTX with playback subject to app support. Print / Save as PDF is available. Edit titles, layouts and themes; rearrange, duplicate or delete slides; embed actual image, audio and video files that survive .ezslides save/reopen. Present fullscreen or print. File sizes are bounded. Advanced native PowerPoint editing and animations are not supported.");
});
})();