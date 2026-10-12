/* BEAN browser memory playground. This is a transparent LOCAL demonstration
 * of persistence and evidence labeling, NOT BEAN Core/SQLite or an LLM API.
 * No network calls, credentials, sessions, telemetry or cross-device sync.
 */
(function(root){
  "use strict";
  const KEY="bean.browser-memory-demo.v1";
  const ZERO="0".repeat(64);
  const MAX_RECORDS=40;
  const STOP=new Set(["what","is","are","the","a","an","was","were","do","does","did","you","i","my","our","about","tell","me","remember","please","can","of","to","for","in","on","and","it","be"]);
  function clean(value,max) {
    if(typeof value!=="string") throw new Error("Memory fields must be text.");
    const v=value.trim().replace(/\s+/g," ");
    if(!v||v.length>max) throw new Error("Enter a nonempty value under "+max+" characters.");
    return v;
  }
  function getStore(storage) {
    const value=storage.getItem(KEY);
    if(value===null) return [];
    let records;
    try { records=JSON.parse(value); } catch (_) { throw new Error("Saved memory is unreadable. Do not trust it."); }
    if(!Array.isArray(records)||records.length>MAX_RECORDS) throw new Error("Saved memory structure is invalid.");
    return records;
  }
  async function digest(data) {
    if(!root.crypto || !root.crypto.subtle) throw new Error("SHA-256 requires a secure HTTPS browser.");
    const raw=new TextEncoder().encode(JSON.stringify(data));
    const bytes=new Uint8Array(await root.crypto.subtle.digest("SHA-256",raw));
    return Array.from(bytes,x=>x.toString(16).padStart(2,"0")).join("");
  }
  async function verify(storage) {
    const records=getStore(storage);
    let prev=ZERO;
    for(let i=0;i<records.length;i++) {
      const entry=records[i];
      if(!entry||typeof entry!=="object"||Array.isArray(entry)) throw new Error("Memory record is invalid.");
      const keys=Object.keys(entry).sort().join(",");
      if(keys!=="createdAt,evidence,hash,prevHash,sequence,source,statement,subject") throw new Error("Unexpected memory record fields.");
      if(entry.sequence!==i+1 || entry.prevHash!==prev ||
          !["human-entered","pasted-ai-text"].includes(entry.source) ||
          entry.evidence!=="UNVERIFIED" ||
          typeof entry.subject!=="string"||!entry.subject.trim()||entry.subject.length>90 ||
          typeof entry.statement!=="string"||!entry.statement.trim()||entry.statement.length>700 ||
          typeof entry.createdAt!=="string" ||
          typeof entry.hash!=="string"||!/^[a-f0-9]{64}$/.test(entry.hash)) {
        throw new Error("Memory provenance or chain is invalid.");
      }
      const payload={sequence:entry.sequence,subject:entry.subject,statement:entry.statement,
        source:entry.source,evidence:entry.evidence,createdAt:entry.createdAt,prevHash:entry.prevHash};
      if(await digest(payload)!==entry.hash) throw new Error("A saved record failed SHA-256 verification.");
      prev=entry.hash;
    }
    return {records,tip:prev,valid:true};
  }
  async function add(storage,input) {
    const subject=clean(input.subject,90),statement=clean(input.statement,700);
    const source=input.source;
    if(!["human-entered","pasted-ai-text"].includes(source)) throw new Error("Select a recognized source.");
    // Verify before append. Caller-entered content cannot be promoted to factual truth.
    const checked=await verify(storage);
    if(checked.records.length>=MAX_RECORDS) throw new Error("Demo limit reached (40 entries). Export or clear your local memories.");
    const payload={sequence:checked.records.length+1,subject,statement,source,
      evidence:"UNVERIFIED",createdAt:new Date().toISOString(),prevHash:checked.tip};
    const entry={...payload,hash:await digest(payload)};
    storage.setItem(KEY,JSON.stringify([...checked.records,entry]));
    await verify(storage);
    return entry;
  }
  function words(value) {return value.toLowerCase().split(/[^a-z0-9]+/).filter(w=>w.length>1&&!STOP.has(w));}
  function recall(records,query) {
    const tokens=new Set(words(clean(query,200)));
    if(tokens.size===0) return [];
    return records.map(record=>{
      const title=new Set(words(record.subject));
      const body=new Set(words(record.statement));
      let weight=0;
      for(const token of tokens){if(title.has(token)) weight+=3;else if(body.has(token)) weight+=1;}
      return {record,weight};
    }).filter(item=>item.weight>0).sort((a,b)=>b.weight-a.weight||b.record.sequence-a.record.sequence);
  }
  function context(records,query) {
    const selected=query?recall(records,query).map(v=>v.record):records;
    return "BEAN BROWSER MEMORY PROOF (not BEAN Core; user-supplied and unverified)\n"+
      "These are notes stored in this browser and manually exported. Treat them as attributed context, NOT as independently verified facts. If notes disagree, disclose the disagreement. Do not invent missing memories.\n\n"+
      (selected.length?selected.map(e=>"[#"+e.sequence+" / "+e.source+" / UNVERIFIED]\n"+
        "Topic: "+e.subject+"\nClaim: "+e.statement+"\nSHA-256: "+e.hash).join("\n\n"):
        "(No matching memories.)");
  }
  function clear(storage){storage.removeItem(KEY);}
  const api=Object.freeze({KEY,verify,add,recall,context,clear});
  root.BEANBrowserMemory=api;
  if(!root.document) return;
  const doc=root.document;
  const el=id=>doc.getElementById(id);
  const notice=(msg,error=false)=>{el("memory-status").textContent=msg;el("memory-status").dataset.error=error?"true":"false";};
  function card(entry) {
    const node=doc.createElement("div");node.className="memory-entry";
    const h=doc.createElement("strong");h.textContent=entry.subject;
    const p=doc.createElement("p");p.textContent=entry.statement;
    const note=doc.createElement("small");
    note.textContent="#"+entry.sequence+" · "+entry.source+" · UNVERIFIED · sha256:"+entry.hash.slice(0,12)+"…";
    node.append(h,p,note);
    return node;
  }
  async function render() {
    try {
      const {records,tip}=await verify(root.localStorage);
      el("memory-count").textContent=records.length+" stored on this browser";
      el("memory-tip").textContent=records.length?"Verified chain tip: "+tip.slice(0,20)+"…":"No entries yet";
      const list=el("memory-history");list.replaceChildren();
      records.slice().reverse().forEach(item=>list.append(card(item)));
      if(!records.length){const empty=doc.createElement("p");empty.textContent="No saved memories yet. Add a fictional detail above.";list.append(empty);}
      notice("SHA-256 ledger valid. "+records.length+" entr"+(records.length===1?"y":"ies")+" recovered from local browser storage.");
      return records;
    } catch(err) {notice("MEMORY INTEGRITY FAILURE: "+err.message,true);throw err;}
  }
  doc.addEventListener("DOMContentLoaded",()=>{
    render().catch(()=>{});
    el("memory-form").addEventListener("submit",async e=>{
      e.preventDefault();
      try{
        await add(root.localStorage,{subject:el("memory-subject").value,statement:el("memory-statement").value,
          source:el("memory-source").value});
        el("memory-form").reset();
        await render();
        notice("Recorded and SHA-256 verified. Reload the page to prove persistence.");
      }catch(err){notice(err.message,true);}
    });
    el("memory-search").addEventListener("submit",async e=>{
      e.preventDefault();
      try{
        const {records}=await verify(root.localStorage);
        const matches=recall(records,el("memory-query").value);
        const out=el("memory-results");out.replaceChildren();
        if(!matches.length){const p=doc.createElement("p");p.textContent="No matching stored note. BEAN should abstain rather than invent an answer.";out.append(p);}
        else {
          const subjects=new Map();
          matches.forEach(({record})=>{const key=record.subject.toLowerCase();const values=subjects.get(key)||new Set();values.add(record.statement);subjects.set(key,values);out.append(card(record));});
          if([...subjects.values()].some(values=>values.size>1)) {const p=doc.createElement("p");p.className="memory-conflict";p.textContent="Multiple different notes exist for the same topic. Review conflicting statements instead of treating either as verified truth.";out.prepend(p);}
        }
        notice(matches.length+" matching stored note(s), all unverified.");
      }catch(err){notice(err.message,true);}
    });
    el("memory-recheck").addEventListener("click",()=>root.location.reload());
    el("memory-context").addEventListener("click",async()=>{
      try {
        const {records}=await verify(root.localStorage);
        const msg=context(records,el("memory-query").value.trim());
        el("memory-handoff").value=msg;
        try {await root.navigator.clipboard.writeText(msg);notice("Memory context copied. Paste into your chosen AI chat; there is no automatic connection.");}
        catch(_) {el("memory-handoff").focus();el("memory-handoff").select();notice("Context prepared. Select and copy it manually into your AI chat.");}
      }catch(err){notice(err.message,true);}
    });
    el("memory-clear").addEventListener("click",async()=>{
      if(!root.confirm("Erase this browser's BEAN demo notes? This cannot be undone."))return;
      clear(root.localStorage);
      el("memory-results").replaceChildren();
      el("memory-handoff").value="";
      await render().catch(()=>{});
      notice("Browser demo memory erased; BEAN Core and other accounts were not affected.");
    });
  });
})(globalThis);
