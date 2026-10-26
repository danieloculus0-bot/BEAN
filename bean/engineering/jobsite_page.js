"use strict";
// Display-only field controls; every numerical answer comes from BEAN's Python service.
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
function valueIn(row, className){return Number(row.querySelector("." + className).value)}
function line(text,className="") {
  const div=document.createElement("div");
  div.textContent=text; if(className)div.className=className;
  el("output").appendChild(div);
}
function showResult(result) {
  if(result.schema === "bean.jobsite_studs.v1") {
    line(result.base_full_height_studs + " baseline full-height studs","headline");
    line("No openings. Add plates, corners, openings, bracing and waste separately.");
    line("Material takeoff only; no structural load check.","warning");
  }else if(result.schema === "bean.jobsite_wall_layout.v1"){
    line(result.minimum_specified_2x4_pieces_before_other_framing + " specified framing segments","headline");
    line(result.baseline_full_height_studs_remaining + " remaining full-length grid studs");
    line(result.studs_removed_inside_rough_openings + " baseline grid studs replaced by rough openings");
    line(result.extra_full_height_king_studs_specified + " extra full-length kings and " +
         result.short_jack_studs_specified + " short jack pieces explicitly specified");
    line("This is NOT a count of full-length boards to buy. Add headers, cripples, plates, corners, waste and bracing; verify all opening framing.","warning");
  }else if(result.schema === "bean.jobsite_beam_screen.v1"){
    const ranked=result.ranking.map(id=>result.members.find(m=>m.id===id));
    const worst=ranked[0], over=worst.worst_utilization > 1;
    line((over?"OVER LIMIT: ":"HIGHEST LOAD RATIO: ") + worst.id,"headline");
    line("Governing: "+worst.governing+" at "+(worst.worst_utilization*100).toFixed(1)+"% of supplied limit");
    line("Member ranking (highest first):","member-results");
    for(const m of ranked){
      line((m.worst_utilization>1?"⚠ ":"") + m.id+": "+
        (m.worst_utilization*100).toFixed(1)+"% ("+m.governing+")");
    }
    if(over){
      line("Options for engineering review:","warning");
      for(const fix of result.mitigations)line("• "+fix.option+". "+fix.needs_check);
    }
    line("Only a simplified 1D beam comparison. Not a construction or code approval.","warning");
  }else line("Unexpected answer from BEAN","warning");
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
    showResult(result);
  }catch(e){
    el("output").textContent="Could not reach the local BEAN engine. Check that the server is running.";
  }
}
function openings(){
  return Array.from(el("opening-list").querySelectorAll(".opening-entry")).map(row=>({
    start_in:valueIn(row,"open-start"),
    width_in:valueIn(row,"open-width"),
    extra_king_studs_per_side:valueIn(row,"open-kings"),
    jack_studs_per_side:valueIn(row,"open-jacks")
  }));
}
el("add-opening").addEventListener("click",()=>{
  if(el("opening-list").children.length>=20){line("For larger layouts, use a drawing and reviewed CSV/JSON.","warning");return}
  const row=el("opening-template").content.firstElementChild.cloneNode(true);
  row.querySelector(".entry-title").textContent="Opening "+(el("opening-list").children.length+1);
  row.querySelector(".remove-opening").addEventListener("click",()=>row.remove());
  el("opening-list").appendChild(row);
});
el("wall-form").addEventListener("submit",event=>{
  event.preventDefault();
  const list=openings();
  const base={schema:"bean.jobsite_request.v1",
              length_ft:n("wall-length"),spacing_in:n("wall-spacing")};
  submit(list.length ? {...base,operation:"wall_layout",openings:list}
                     : {...base,operation:"wall_studs"});
});
el("add-beam").addEventListener("click",()=>{
  const container=el("beam-members");
  if(container.children.length>=20)return;
  const row=el("beam-template").content.firstElementChild.cloneNode(true);
  row.querySelector(".beam-name").value="Beam "+(container.children.length+1);
  row.querySelector(".remove-beam").addEventListener("click",()=>row.remove());
  container.appendChild(row);
});
el("beam-form").addEventListener("submit",event=>{
  event.preventDefault();
  const members=Array.from(el("beam-members").querySelectorAll(".beam-member")).map(row=>({
    id:row.querySelector(".beam-name").value.trim(),
    width_in:valueIn(row,"beam-width"),depth_in:valueIn(row,"beam-depth"),
    span_ft:valueIn(row,"beam-span"),load_plf:valueIn(row,"beam-load")
  }));
  const payload={schema:"bean.jobsite_request.v1",operation:"beam_check",members};
  if(!profileInstalled){
    payload.project_defaults={
      modulus_psi:n("beam-e"),allowable_bending_psi:n("beam-fb"),
      allowable_shear_psi:n("beam-fv"),deflection_limit_ratio:n("beam-ratio")
    };
  }
  submit(payload);
});
fetch("/api/profile").then(r=>r.json()).then(profile=>{
  profileInstalled=Boolean(profile.profile_installed);
  el("limits-fields").hidden=profileInstalled;
  for(const id of ["beam-e","beam-fb","beam-fv","beam-ratio"]){
    el(id).required=!profileInstalled;
  }
  el("profile-info").textContent=profileInstalled?
    "Project limits loaded: "+profile.name+". Source: "+profile.limits_source:
    "No saved project profile. Enter reviewed material limits below once for all beams.";
}).catch(()=>{
  el("profile-info").textContent="No project profile available. Enter reviewed limits below.";
});
