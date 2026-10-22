(function(){
"use strict";
EZOffice.register("media",function(ctx){
  const {elem,button,root,toolbar,choose,message,info,onDispose}=ctx;
  const bar=toolbar();
  const stage=elem("div",{className:"media-stage"},root);
  let url=null,player=null;
  function release(){
    if(player){
      if(player.pause)player.pause();
      player.removeAttribute("src");
      if(player.load)player.load();
      player.remove();player=null;
    }
    if(url){URL.revokeObjectURL(url);url=null;}
  }
  function open(file){
    const mime=file.type||"";
    const extension=(file.name.split(".").pop()||"").toLowerCase();
    const kind=mime.startsWith("image/")||/^(png|jpe?g|gif|webp|svg|bmp|avif)$/.test(extension)?"img":
      mime.startsWith("audio/")||/^(mp3|wav|ogg|m4a|flac|aac|opus)$/.test(extension)?"audio":
      mime.startsWith("video/")||/^(mp4|webm|ogv|mov|m4v|mkv)$/.test(extension)?"video":null;
    if(!kind){message("Unsupported media type. Choose a browser-supported image, audio, or video file.");return;}
    release();stage.replaceChildren();
    url=URL.createObjectURL(file);
    player=elem(kind,{src:url,"aria-label":file.name},stage);
    if(kind!=="img"){player.controls=true;player.preload="metadata";}else player.alt=file.name;
    player.addEventListener("error",()=>message("Browser could not decode "+file.name+". Codec support varies by platform."));
    message("Opened local "+kind+": "+file.name+" ("+(file.size/1024/1024).toFixed(2)+" MiB).");
  }
  button(bar,"Open media",()=>choose("image/*,audio/*,video/*,.mkv,.flac,.svg",open),true);
  button(bar,"Close media",()=>{release();stage.replaceChildren();elem("p",{className:"hint",text:"No media loaded."},stage);message("Media released");});
  elem("p",{className:"hint",text:"Open a file to play audio or video or view an image."},stage);
  info("Uses a local object URL to stream directly from your selected file. Does not read an entire movie into JavaScript memory. Pauses, unloads, and revokes its URL when closed or when you switch applications.");
  onDispose(()=>{release();stage.replaceChildren();});
});
})();
