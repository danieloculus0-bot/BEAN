"use strict";
// Display only. The numerical engine is bean.engineering.jobsite on the server.
const el = id => document.getElementById(id);
let profileInstalled = false;
function switchTo(which) {
  const wall = which === "wall";
  el("wall").hidden = !wall; el("beam").hidden = wall;
  el("tab-wall").classList.toggle("active", wall);
  el("tab-beam").classList.toggle("active", !wall);
  el("tab-wall").setAttribute("aria-pressed",String(wall));
  el("tab-beam").setAttribute("aria-pressed",String(!wall));
  el("output").textContent = "Enter the details above and tap the green button.";
}
el("tab-wall").addEventListener("click",()=>switchTo("wall"));
el("tab-beam").addEventListener("click",()=>switchTo("beam"));
function n(id){return Number(el(id).value)}
function line(text,className="") {
  const div=document.createElement("div");
  div.textContent=text; if(className)div.className=className;
  el("output").appendChild(div);
}
async function submit(body) {
  el("output").textContent="Calculating…";
  try {
    const r=await fetch("/api/calculate",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify(body)
    });
    const result=await r.json();
    el("output").textContent="";
    if(!r.ok){line("Check the inputs: "+(result.error || "Unable to calculate"),"warning");return}
    if(result.schema==="bean.jobsite_studs.v1"){
      line(result.base_full_height_studs+" full-height studs","headline");
      line("Straight wall only. Add corners, plates, openings, bracing and waste separately.");
      line("Material count, not structural approval.","warning");
    }else if(result.schema==="bean.jobsite_beam_screen.v1"){
      const m=result.members[0], fail=m.worst_utilization>1;
      line((fail?"REVIEW: ":"SCREEN: ")+m.id,"headline");
      line("Main issue: "+m.governing+" ("+(m.worst_utilization*100).toFixed(1)+"% of supplied limit)");
      line("Bending: "+(m.utilization.bending*100).toFixed(1)+"% | Shear: "+(m.utilization.shear*100).toFixed(1)+"% | Deflection: "+(m.utilization.deflection*100).toFixed(1)+"%");
      if(fail) {
        line("Possible ways to improve:","warning");
        for(const fix of result.mitigations)line("• "+fix.option+". "+fix.needs_check);
      }
      line("This is a simplified beam check. Get structural review before building or changing supports.","warning");
    }else{line("Unexpected answer from BEAN","warning")}
  }catch(e){el("output").textContent="Could not reach the local BEAN engine. Check that the server is running."}
}
el("wall-form").addEventListener("submit",event=>{
  event.preventDefault();
  submit({schema:"bean.jobsite_request.v1",operation:"wall_studs",
          length_ft:n("wall-length"),spacing_in:n("wall-spacing")});
});
el("beam-form").addEventListener("submit",event=>{
  event.preventDefault();
  const beam={
    id:el("beam-name").value.trim(),
    width_in:n("beam-width"),depth_in:n("beam-depth"),
    span_ft:n("beam-span"),load_plf:n("beam-load")
  };
  if(!profileInstalled)Object.assign(beam,{
    modulus_psi:n("beam-e"),allowable_bending_psi:n("beam-fb"),
    allowable_shear_psi:n("beam-fv"),deflection_limit_ratio:n("beam-ratio")
  });
  submit({schema:"bean.jobsite_request.v1",operation:"beam_check",members:[beam]});
});
fetch("/api/profile").then(r=>r.json()).then(profile=>{
  profileInstalled=Boolean(profile.profile_installed);
  el("limits-fields").hidden=profileInstalled;
  el("profile-info").textContent=profileInstalled?
    "Project limits loaded: "+profile.name+". Source: "+profile.limits_source:
    "No saved project profile. Enter material limits below for each beam.";
}).catch(()=>{
  el("profile-info").textContent="No project profile available. Enter verified limits below.";
});
