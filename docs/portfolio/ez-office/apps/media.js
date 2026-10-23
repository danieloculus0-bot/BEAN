/* EZ Media: local native audio/video decoding; no plugin, codec bundle or network. */
(function(){
"use strict";
const EXT={
  mp3:["audio","audio/mpeg"],wav:["audio","audio/wav"],wave:["audio","audio/wav"],
  m4a:["audio","audio/mp4"],aac:["audio","audio/aac"],ogg:["audio","audio/ogg"],
  oga:["audio","audio/ogg"],opus:["audio","audio/ogg; codecs=opus"],
  flac:["audio","audio/flac"],mp4:["video","video/mp4"],m4v:["video","video/mp4"],
  webm:["video","video/webm"],ogv:["video","video/ogg"],
  mov:["video","video/quicktime"],mkv:["video","video/x-matroska"],
  png:["img","image/png"],jpg:["img","image/jpeg"],jpeg:["img","image/jpeg"],
  gif:["img","image/gif"],webp:["img","image/webp"],bmp:["img","image/bmp"],
  svg:["img","image/svg+xml"],avif:["img","image/avif"]
};
const recommended="Try MP4 (H.264/AAC), WebM (VP8/VP9 + Opus), MP3 or WAV. Playback depends on the browser/OS's built-in decoders; EZ-Office never installs plugins.";
function formatTime(time){
  if(!Number.isFinite(time)||time<0)return "?:??";
  const seconds=Math.floor(time),minutes=Math.floor(seconds/60);
  return minutes+":"+String(seconds%60).padStart(2,"0");
}
EZOffice.register("media",function(ctx){
  const {elem,button,root,toolbar,choose,message,info,onDispose,download}=ctx;
  const bar=toolbar(),controls=toolbar();
  const stage=elem("div",{className:"media-stage"},root);
  const playbackState=elem("p",{className:"hint media-playback-state",role:"status","aria-live":"polite",text:"Open a file to check and play it locally."},root);
  const details=elem("p",{className:"hint media-details",text:"No media selected."},root);
  const matrix=elem("div",{className:"media-capabilities",role:"region","aria-label":"Native format support"},root);
  let sourceUrl=null,player=null,currentFile=null,kind=null,serial=0,ready=false;

  const rate=elem("select",{"aria-label":"Playback speed"},bar);
  for(const [value,label] of [["0.5","0.5×"],["1","1× Normal"],["1.5","1.5×"],["2","2×"]])elem("option",{value,text:label},rate);
  rate.value="1";
  const loopLabel=elem("label",{className:"media-loop-label"},bar);
  const loop=elem("input",{type:"checkbox","aria-label":"Loop playback"},loopLabel);
  elem("span",{text:"Loop"},loopLabel);

  function state(text){playbackState.textContent=text;}
  function options(){if(player&&kind!=="img"){player.playbackRate=Number(rate.value);player.loop=loop.checked;}}
  rate.addEventListener("change",options);loop.addEventListener("change",options);
  const playButton=button(controls,"Play / Pause",async()=>{
    if(!player||kind==="img")return;
    if(!player.paused){player.pause();return;}
    try{await player.play();}
    catch(e){if(player)state("Playback could not start ("+(e.name||"browser error")+"). "+recommended);}
  });
  const back=button(controls,"← 10s",()=>seek(-10));
  const ahead=button(controls,"10s →",()=>seek(10));
  function seek(offset){
    if(!player||kind==="img"||player.readyState<1||!Number.isFinite(player.duration))return;
    player.currentTime=Math.max(0,Math.min(player.duration,player.currentTime+offset));
  }
  function enableControls(){
    const active=!!player&&kind!=="img";
    playButton.disabled=!active;back.disabled=!active;ahead.disabled=!active;rate.disabled=!active;loop.disabled=!active;
  }
  function release(){
    ++serial;ready=false;
    const old=player,oldUrl=sourceUrl;
    player=null;sourceUrl=null;kind=null;
    if(old){
      if(typeof old.pause==="function")old.pause();
      old.removeAttribute("src");
      if(typeof old.load==="function")old.load();
      old.remove();
    }
    if(oldUrl)URL.revokeObjectURL(oldUrl);
    enableControls();
  }
  function showFormats(){
    matrix.replaceChildren();
    const checks=[
      ["MP4 (H.264/AAC)","video","video/mp4; codecs=\"avc1.42E01E, mp4a.40.2\""],
      ["WebM (VP8/Opus)","video","video/webm; codecs=\"vp8, opus\""],
      ["MP3","audio","audio/mpeg"],
      ["WAV (PCM)","audio","audio/wav"],
      ["Ogg (Vorbis)","audio","audio/ogg; codecs=vorbis"]
    ];
    elem("strong",{text:"Formats this browser reports it can decode"},matrix);
    for(const [label,tag,mime] of checks){
      const claim=document.createElement(tag).canPlayType(mime);
      elem("p",{text:label+": "+(claim==="probably"?"Likely":claim==="maybe"?"Possibly":"Not advertised")},matrix);
    }
    elem("p",{className:"hint",text:"This is only a capability estimate. Actual playback of a selected file is the final test; container support does not guarantee its internal codec."},matrix);
  }
  function open(file){
    const ext=(file.name.split(".").pop()||"").toLowerCase();
    const type=(file.type||"").toLowerCase();
    const found=EXT[ext];
    const inferred=type.startsWith("image/")?"img":type.startsWith("audio/")?"audio":type.startsWith("video/")?"video":null;
    const target=found?.[0]||inferred;
    if(!target){state("This file type is not recognized. "+recommended);message("Unrecognized media file: "+file.name);return;}
    release();currentFile=file;kind=target;stage.replaceChildren();matrix.replaceChildren();
    sourceUrl=URL.createObjectURL(file);
    const ticket=serial;
    const active=()=>ticket===serial&&player!==null;
    player=elem(target,{src:sourceUrl,"aria-label":file.name},stage);
    const element=player,selectedKind=target;
    if(selectedKind==="img"){
      element.alt=file.name;
      element.addEventListener("load",()=>{
        if(!active())return;
        ready=true;details.textContent=file.name+" · "+element.naturalWidth+" × "+element.naturalHeight+" pixels";
        state("Image loaded. Save the original or export as PNG.");
      });
      element.addEventListener("error",()=>{if(active())state("Cannot display this image in the current browser.");});
    }else{
      element.controls=true;element.preload="metadata";element.playsInline=true;
      element.setAttribute("playsinline","");
      element.setAttribute("webkit-playsinline","");
      options();
      const codecMime=found?.[1]||type;
      const advertised=codecMime?element.canPlayType(codecMime):"";
      details.textContent=file.name+" · "+(file.size/(1024*1024)).toFixed(2)+" MiB"+
        " · "+(advertised==="probably"?"Native format likely supported":advertised==="maybe"?"Native format support possible":"Native format support unknown");
      state("Loading media metadata…");
      element.addEventListener("loadedmetadata",()=>{
        if(!active())return;
        details.textContent=file.name+" · "+formatTime(element.duration)+
          (selectedKind==="video"?" · "+element.videoWidth+" × "+element.videoHeight:"")+
          " · "+(file.size/(1024*1024)).toFixed(2)+" MiB";
        state("Metadata loaded. Press Play to verify decoding.");
      });
      element.addEventListener("canplay",()=>{
        if(!active())return;
        ready=true;
        if(element.paused)state("Ready — press Play. This file can be decoded by the browser.");
      });
      element.addEventListener("playing",()=>{if(active())state("Playing "+formatTime(element.currentTime)+" / "+formatTime(element.duration));});
      element.addEventListener("timeupdate",()=>{
        if(active()&&!element.paused)state("Playing "+formatTime(element.currentTime)+" / "+formatTime(element.duration));
      });
      element.addEventListener("pause",()=>{
        if(active()&&!element.ended&&ready)state("Paused at "+formatTime(element.currentTime));
      });
      element.addEventListener("ended",()=>{if(active())state("Playback complete.");});
      element.addEventListener("waiting",()=>{if(active()&&!element.paused)state("Waiting for local media to decode…");});
      element.addEventListener("error",()=>{
        if(!active())return;
        const code=element.error?.code;
        state((code===3?"Decoding failed":code===4?"Format/codec unsupported":"Could not play media")+
          " — "+file.name+". "+recommended);
        message("Unable to decode "+file.name+" with built-in browser media support.");
      });
      // Metadata is explicitly requested; playback itself is user initiated,
      // because mobile browsers reject unprompted autoplay.
      element.load();
    }
    enableControls();
    message("Opened local "+selectedKind+": "+file.name+". No plugin or upload used.");
  }
  button(bar,"Open media",()=>choose("image/*,audio/*,video/*,.mkv,.mov,.m4v,.mp3,.flac,.opus,.ogv,.webm,.svg",open),true);
  button(bar,"Check formats",showFormats);
  button(bar,"Save original",()=>{
    if(!currentFile){message("Open a file first");return;}
    download(currentFile.name,currentFile,currentFile.type||"application/octet-stream");
  });
  button(bar,"Export still PNG",()=>{
    if(!player||![ "IMG","VIDEO" ].includes(player.tagName)){message("Open an image or playable video first");return;}
    if(player.tagName==="VIDEO"&&player.readyState<2){message("Play the video until a frame has decoded, then try again");return;}
    const canvas=document.createElement("canvas");
    canvas.width=player.tagName==="IMG"?player.naturalWidth:player.videoWidth;
    canvas.height=player.tagName==="IMG"?player.naturalHeight:player.videoHeight;
    if(!canvas.width||!canvas.height||canvas.width*canvas.height>24000000){message("Frame unavailable or larger than 24 MP");return;}
    canvas.getContext("2d").drawImage(player,0,0);
    canvas.toBlob(blob=>{
      if(blob)download("EZ-Media-frame.png",blob,"image/png");
      else message("This browser cannot export the frame");
    },"image/png");
  });
  button(bar,"Print / PDF",()=>window.print());
  button(bar,"Close media",()=>{
    release();currentFile=null;stage.replaceChildren();
    details.textContent="No media selected.";state("Media released.");
    elem("p",{className:"hint",text:"No media loaded."},stage);
    message("Media released and playback resources cleaned up.");
  });
  elem("p",{className:"hint",text:"Open a local MP4, WebM, MP3 or WAV. Native browser controls provide play, volume and timeline scrubbing."},stage);
  enableControls();
  info("Built-in HTML audio/video decoding, no plugins, extra players, downloads or uploads. Common MP4 (H.264/AAC), WebM (VP8/VP9/Opus), MP3 and WAV work only when the current browser and operating system supply the decoder. Click Check formats to see support estimates, then open a file and press Play. MOV, MKV, FLAC and unusual codec combinations are not universally supported. Files are streamed via object URLs and released on close/switch.");
  onDispose(()=>{release();currentFile=null;stage.replaceChildren();});
});
})();