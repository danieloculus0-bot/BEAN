(function(){
"use strict";
EZOffice.register("mail",function(ctx){
  const {elem,button,root,toolbar,download,message,info,markDirty}=ctx;
  const form=elem("div",{className:"card"},root);
  const fields=elem("div",{className:"form-grid"},form);
  function input(label,type){
    elem("label",{text:label},fields);
    return elem("input",{type,"aria-label":label},fields);
  }
  const to=input("To","text"),cc=input("Cc","text"),subject=input("Subject","text");
  elem("label",{text:"Message"},form);
  const body=elem("textarea",{className:"mail-body","aria-label":"Email body",placeholder:"Write a message. Mail sync and sending are handled by your email client."},form);
  const bar=toolbar();
  function singleLine(s){return s.replace(/[\r\n]/g," ").trim();}
  function addr(s){return singleLine(s).replace(/[\x00-\x1f\x7f]/g,"");}
  function eml(){
    const headers=["MIME-Version: 1.0","Content-Type: text/plain; charset=UTF-8","Content-Transfer-Encoding: 8bit"];
    if(to.value.trim())headers.push("To: "+addr(to.value));
    if(cc.value.trim())headers.push("Cc: "+addr(cc.value));
    headers.push("Subject: "+singleLine(subject.value||"(No subject)"));
    return headers.join("\r\n")+"\r\n\r\n"+body.value.replace(/\r?\n/g,"\r\n")+"\r\n";
  }
  button(bar,"Download .eml",()=>{
    download("EZ-Office-draft.eml",eml(),"message/rfc822;charset=utf-8");markDirty(false);
  },true);
  button(bar,"Open in mail app",()=>{
    const total=(to.value+cc.value+subject.value+body.value).length;
    if(total>1600){message("Draft exceeds reliable mailto URL length. Download an .eml file instead.");return;}
    const url="mailto:"+encodeURIComponent(addr(to.value))+"?subject="+encodeURIComponent(singleLine(subject.value))+"&cc="+encodeURIComponent(addr(cc.value))+"&body="+encodeURIComponent(body.value);
    window.location.href=url;
    message("Requested the operating system's mail handler. EZ-Office does not send or sync mail.");
  });
  for(const element of [to,cc,subject,body])element.addEventListener("input",()=>markDirty(true));
  info("Real local draft editing and RFC 822-style .eml export. Open in mail app delegates to the system's configured handler. There is no fake inbox, SMTP send, OAuth, or background polling.");
});
})();
