/* EZ Mail: local draft editor, real Gmail OAuth and Microsoft 365 OAuth PKCE adapters.
   No client secret/password collection. Tokens stay in memory; MS authorization uses short-lived session PKCE. */
(function(){
"use strict";
const GH="https://www.googleapis.com/gmail/v1/users/me";
const GRAPH="https://graph.microsoft.com/v1.0/me";
const MS_AUTH="https://login.microsoftonline.com/common/oauth2/v2.0";
const MS_SCOPE="openid profile User.Read Mail.Read Mail.Send";
const KEY="ezoffice-ms-auth";
function base64url(bytes){
  let binary="";for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.slice(i,i+32768));
  return btoa(binary).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
}
function utf8base64(text){return base64url(new TextEncoder().encode(text));}
function mimeBase64(text){const raw=utf8base64(text).replace(/-/g,"+").replace(/_/g,"/");const padded=raw+"=".repeat((4-raw.length%4)%4);return padded.match(/.{1,76}/g)?.join("\r\n")||"";}
function header(s){return String(s||"").replace(/[\r\n\0]+/g," ").trim();}
function addresses(text){
  return String(text||"").split(",").map(s=>s.trim()).filter(Boolean).map(s=>{
    if(!/^[^\s@,<>]+@[^\s@,<>]+\.[^\s@,<>]+$/.test(s))throw Error("Invalid address: "+s);
    return s;
  });
}
function gmailRaw(to,cc,subject,body){
  const toList=addresses(to);
  if(!toList.length)throw Error("Enter a recipient before sending");
  const ccs=addresses(cc);
  const lines=["MIME-Version: 1.0","To: "+toList.join(", "),...(ccs.length?["Cc: "+ccs.join(", ")]:[]),
    "Subject: =?UTF-8?B?"+mimeBase64(header(subject)).replace(/\r\n/g,"")+"?=",
    "Content-Type: text/plain; charset=UTF-8","Content-Transfer-Encoding: base64","",
    mimeBase64(body),""];
  return utf8base64(lines.join("\r\n"));
}
function loadGoogleScript(){
  if(window.google?.accounts?.oauth2)return Promise.resolve();
  return new Promise((resolve,reject)=>{
    const script=document.createElement("script");
    script.src="https://accounts.google.com/gsi/client";
    script.async=true;
    script.onload=()=>window.google?.accounts?.oauth2?resolve():reject(Error("Google Identity Services unavailable"));
    script.onerror=()=>reject(Error("Could not load Google's OAuth sign-in library"));
    document.head.append(script);
  });
}
async function api(url,token,options={}){
  const response=await fetch(url,{...options,headers:{"Authorization":"Bearer "+token,...(options.headers||{})},cache:"no-store"});
  if(!response.ok){
    let details="";try{const j=await response.json();details=j.error?.message||j.error_description||"";}catch(e){}
    throw Error("Provider HTTP "+response.status+(details?": "+details:""));
  }
  if(response.status===204)return {};
  return response.json();
}
function randomValue(){return base64url(crypto.getRandomValues(new Uint8Array(32)));}
async function sha256(s){return base64url(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(s))));}
function callbackURL(){return location.origin+location.pathname;}
EZOffice.register("mail",function(ctx){
  const {elem,button,root,toolbar,download,message,info,markDirty,onDispose}=ctx;
  let activeToken="",provider="",busy=false;
  const card=elem("div",{className:"card"},root),fields=elem("div",{className:"form-grid"},card);
  function field(label,type="text"){
    elem("label",{text:label},fields);
    return elem("input",{type,"aria-label":label},fields);
  }
  const to=field("To"),cc=field("Cc"),subject=field("Subject");
  elem("label",{text:"Message"},card);
  const body=elem("textarea",{className:"mail-body","aria-label":"Email body",placeholder:"Type your message. Only Send via Gmail/Outlook actually transmits it."},card);
  const bar=toolbar();
  function eml(){
    const b=body.value.replace(/\r?\n/g,"\r\n");
    return ["MIME-Version: 1.0","Content-Type: text/plain; charset=UTF-8",
      "To: "+header(to.value),"Cc: "+header(cc.value),"Subject: "+header(subject.value),"",b,""].join("\r\n");
  }
  button(bar,"Print / PDF",()=>window.print());
  button(bar,"Download .eml",()=>{download("EZ-Office-draft.eml",eml(),"message/rfc822;charset=utf-8");markDirty(false);},true);
  button(bar,"Open in mail app",()=>{
    if((to.value+cc.value+subject.value+body.value).length>1600){message("Draft too large for mailto; export .eml instead");return;}
    location.href="mailto:"+encodeURIComponent(to.value.trim())+"?cc="+encodeURIComponent(cc.value)+"&subject="+encodeURIComponent(subject.value)+"&body="+encodeURIComponent(body.value);
  });
  for(const e of [to,cc,subject,body])e.addEventListener("input",()=>markDirty(true));
  const connect=elem("section",{className:"mail-connect"},root);
  elem("h2",{text:"Connected email"},connect);
  elem("p",{className:"hint",text:"Connect Gmail or Outlook with delegated OAuth permissions. Requires your own registered OAuth public client ID and HTTPS hosting. The client ID is public configuration, not an account password. Nothing syncs until you connect."},connect);
  const config=elem("div",{className:"form-grid"},connect);
  elem("label",{text:"Google OAuth client ID"},config);
  const googleID=elem("input",{type:"text","aria-label":"Google OAuth client ID",placeholder:"Registered Google web application client ID"},config);
  elem("label",{text:"Microsoft app client ID"},config);
  const microsoftID=elem("input",{type:"text","aria-label":"Microsoft app client ID",placeholder:"Registered Microsoft SPA application client ID"},config);
  const controls=elem("div",{className:"toolbar"},connect);
  const state=elem("p",{className:"hint",text:"Disconnected. Files and drafts remain local."},connect);
  const inbox=elem("div",{className:"inbox-list",role:"region","aria-label":"Inbox messages"},connect);
  const send=button(controls,"Send via connected account",async()=>{
    if(!activeToken){message("Connect an email account first");return;}
    if(busy)return;
    try{
      addresses(to.value);addresses(cc.value);if(!addresses(to.value).length)throw Error("Recipient required");
      if(!confirm("Send this message through "+provider+" to "+to.value+"?"))return;
      busy=true;send.disabled=true;
      if(provider==="Gmail"){
        await api(GH+"/messages/send",activeToken,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({raw:gmailRaw(to.value,cc.value,subject.value,body.value)})});
      }else{
        const recipients=list=>addresses(list).map(address=>({emailAddress:{address}}));
        await api(GRAPH+"/sendMail",activeToken,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:{subject:header(subject.value),body:{contentType:"Text",content:body.value},toRecipients:recipients(to.value),ccRecipients:recipients(cc.value)},saveToSentItems:true})});
      }
      message("Provider accepted message for sending through "+provider+".");markDirty(false);
    }catch(e){message("Send failed: "+e.message);}
    finally{busy=false;send.disabled=!activeToken;}
  },true);
  send.disabled=true;
  button(controls,"Refresh inbox",()=>refresh());
  button(controls,"Disconnect",()=>{activeToken="";provider="";send.disabled=true;inbox.replaceChildren();state.textContent="Disconnected";message("Disconnected; token forgotten from memory.");});
  async function refresh(){
    if(!activeToken){message("Connect first");return;}
    inbox.replaceChildren();elem("p",{className:"hint",text:"Loading messages..."},inbox);
    try{
      let records=[];
      if(provider==="Gmail"){
        const list=await api(GH+"/messages?maxResults=12&labelIds=INBOX",activeToken);
        const items=(list.messages||[]).slice(0,12);
        records=await Promise.all(items.map(async item=>{
          const d=await api(GH+"/messages/"+encodeURIComponent(item.id)+"?format=metadata&metadataHeaders=Subject&metadataHeaders=From",activeToken);
          const h=Object.fromEntries((d.payload?.headers||[]).map(h=>[h.name.toLowerCase(),h.value]));
          return {from:h.from||"Unknown",subject:h.subject||"(No subject)",snippet:d.snippet||""};
        }));
      }else{
        const list=await api(GRAPH+"/mailFolders/inbox/messages?$top=12&$select=from,subject,bodyPreview,receivedDateTime&$orderby=receivedDateTime%20desc",activeToken);
        records=(list.value||[]).map(m=>({from:m.from?.emailAddress?.address||"Unknown",subject:m.subject||"(No subject)",snippet:m.bodyPreview||""}));
      }
      if(!ctx.isActive())return;
      inbox.replaceChildren();
      for(const record of records){
        const item=elem("article",{className:"message-preview"},inbox);
        elem("strong",{text:record.subject},item);
        elem("small",{text:record.from},item);
        elem("p",{text:record.snippet},item);
      }
      if(!records.length)elem("p",{className:"hint",text:"No inbox messages returned."},inbox);
      state.textContent="Connected to "+provider+" · "+records.length+" message previews";
    }catch(e){inbox.replaceChildren();message("Inbox fetch failed: "+e.message);}
  }
  function ready(which,token){
    if(!ctx.isActive())return;
    provider=which;activeToken=token;send.disabled=false;state.textContent="Connected to "+which+". OAuth token is held only in memory.";
    message("Connected to "+which+". Refresh inbox or send your own draft.");
    refresh();
  }
  button(controls,"Connect Gmail",async()=>{
    const client=googleID.value.trim();
    if(!client){message("Enter a Google web OAuth client ID first");return;}
    if(location.protocol!=="https:"&&location.hostname!=="localhost"){message("Gmail OAuth requires a supported HTTPS origin");return;}
    try{
      await loadGoogleScript();
      if(!ctx.isActive())return;
      const tokenClient=google.accounts.oauth2.initTokenClient({
        client_id:client,scope:"https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send",
        callback:resp=>resp.error?message("Google OAuth failed: "+resp.error):ready("Gmail",resp.access_token),
        error_callback:e=>message("Google sign-in failed: "+(e.type||"unknown"))
      });
      tokenClient.requestAccessToken({prompt:"consent"});
    }catch(e){message("Gmail connection failed: "+e.message);}
  });
  button(controls,"Connect Outlook",async()=>{
    const client=microsoftID.value.trim();
    if(!/^[0-9a-f-]{36}$/i.test(client)){message("Enter a registered Microsoft application ID");return;}
    if(location.protocol!=="https:"&&location.hostname!=="localhost"){message("Microsoft OAuth requires a supported HTTPS origin");return;}
    try{
      const verifier=randomValue(),stateCode=randomValue(),challenge=await sha256(verifier);
      sessionStorage.setItem(KEY,JSON.stringify({client,verifier,state:stateCode,redirect:callbackURL(),time:Date.now()}));
      const query=new URLSearchParams({client_id:client,response_type:"code",redirect_uri:callbackURL(),response_mode:"query",scope:MS_SCOPE,state:stateCode,code_challenge:challenge,code_challenge_method:"S256"});
      location.assign(MS_AUTH+"/authorize?"+query);
    }catch(e){message("Outlook authorization failed: "+e.message);}
  });
  async function finishMicrosoftRedirect(){
    const params=new URLSearchParams(location.search);
    if(!params.has("code")&&!params.has("error"))return;
    history.replaceState(null,"",location.pathname+location.hash);
    let data;try{data=JSON.parse(sessionStorage.getItem(KEY)||"null");}catch(e){}
    sessionStorage.removeItem(KEY);
    if(params.has("error")){message("Microsoft OAuth error: "+params.get("error"));return;}
    if(!data||data.state!==params.get("state")||Date.now()-data.time>10*60*1000){message("OAuth state expired or mismatched; reconnect");return;}
    try{
      const payload=new URLSearchParams({client_id:data.client,grant_type:"authorization_code",code:params.get("code"),redirect_uri:data.redirect,code_verifier:data.verifier,scope:MS_SCOPE});
      const resp=await fetch(MS_AUTH+"/token",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:payload,cache:"no-store"});
      const json=await resp.json();
      if(!resp.ok||!json.access_token)throw Error(json.error_description||"Token exchange failed");
      ready("Outlook",json.access_token);
    }catch(e){message("Microsoft token exchange failed: "+e.message);}
  }
  finishMicrosoftRedirect();
  onDispose(()=>{activeToken="";provider="";inbox.replaceChildren();});
  info("Gmail: Google Identity Services OAuth with Gmail readonly/send scopes; Outlook: Microsoft identity authorization-code PKCE with Graph Mail.Read/Mail.Send. Both are real API requests after authorization, not sample inbox data. Register your own OAuth application and authorize this exact hosted URL; admin policy/consent may be required. No passwords, client secrets, refresh tokens or messages are saved locally. Not supported from file://.");
});
})();