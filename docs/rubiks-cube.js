/* BEAN Cognitive Gauntlet 3x3.
 * Reference: unmodified cubejs two-phase MIT solver in a Web Worker.
 * Candidate: short-path BFS and persisted case-based route reuse.
 * The candidate is a browser experiment, NOT the BEAN Python Core learner.
 */
'use strict';
(function(){
const FACES='UDFBRL', ORDER='URFDLB';
const SOLVED=[...FACES].map(f=>f.repeat(9)).join('');
const MOVES=[...FACES].flatMap(f=>[f,f+"'",f+'2']);
const NORMAL={U:[0,1,0],D:[0,-1,0],F:[0,0,1],B:[0,0,-1],R:[1,0,0],L:[-1,0,0]};
const RIGHT={U:[1,0,0],D:[1,0,0],F:[1,0,0],B:[-1,0,0],R:[0,0,-1],L:[0,0,1]};
const DOWN={U:[0,0,1],D:[0,0,-1],F:[0,-1,0],B:[0,-1,0],R:[0,-1,0],L:[0,-1,0]};
const add=(...vs)=>[0,1,2].map(i=>vs.reduce((a,v)=>a+v[i],0));
const mul=(v,k)=>v.map(x=>x*k);
const spin=(v,axis,sign)=>{
 const [x,y,z]=v;return axis===0?[x,-sign*z,sign*y]:
 axis===1?[sign*z,y,-sign*x]:[-sign*y,sign*x,z];
};
const stickers=[];
for(const f of FACES)for(let row=0;row<3;row++)for(let col=0;col<3;col++)
 stickers.push([add(NORMAL[f],mul(RIGHT[f],col-1),mul(DOWN[f],row-1)),NORMAL[f]]);
const index=new Map(stickers.map((pair,i)=>[JSON.stringify(pair),i]));
if(index.size!==54)throw Error('Broken cube geometry');
const compose=(a,b)=>a.map(i=>b[i]), perms={};
for(const f of FACES){
 const norm=NORMAL[f],axis=norm.findIndex(x=>x!==0),sign=-norm[axis];
 const quarter=stickers.map(([p,n])=>index.get(JSON.stringify(
 p[axis]===norm[axis]?[spin(p,axis,sign),spin(n,axis,sign)]:[p,n])));
 if(quarter.some(i=>i===undefined))throw Error('Invalid move permutation');
 perms[f]=quarter;perms[f+'2']=compose(quarter,quarter);
 perms[f+"'"]=compose(perms[f+'2'],quarter);
}
function turn(state,move){
 if(state.length!==54||!perms[move])throw Error('Invalid move or cube');
 const out=Array(54),perm=perms[move];
 for(let i=0;i<54;i++)out[perm[i]]=state[i];
 return out.join('');
}
function apply(state,moves){for(const m of moves)state=turn(state,m);return state;}
function invert(ms){return [...ms].reverse().map(m=>m.endsWith('2')?m:m.endsWith("'")?m.slice(0,-1):m+"'");}
function toCubeJS(state){return [...ORDER].map(f=>state.slice(FACES.indexOf(f)*9,FACES.indexOf(f)*9+9)).join('');}
function scramble(seed,length){
 if(length<0||length>10000||!Number.isInteger(length))throw Error('Bad scramble length');
 let x=(seed>>>0)||0x9e3779b9;const result=[];
 for(let i=0;i<length;i++){
  x^=x<<13;x^=x>>>17;x^=x<<5;x>>>=0;
  const opts=MOVES.filter(m=>!result.length||m[0]!==result[result.length-1][0]);
  result.push(opts[x%opts.length]);
 }
 return result;
}
// Bounded OPTIMALITY IMPROVEMENT only; never a cap on a valid cube's solution.
function shortProbe(state,maxDepth=6,nodeCap=75000){
 if(state===SOLVED)return {moves:[],complete:true,nodes:1};
 function bfs(start,depth){
  const seen=new Map([[start,[]]]);let frontier=[start];
  for(let d=0;d<depth;d++){
   const next=[];
   for(const s of frontier){
    const prev=seen.get(s);
    for(const m of MOVES){
     if(prev.length&&m[0]===prev[prev.length-1][0])continue;
     const candidate=turn(s,m);
     if(!seen.has(candidate)){
      if(seen.size>=nodeCap)return {seen,complete:false};
      seen.set(candidate,prev.concat(m));next.push(candidate);
     }
    }
   }frontier=next;
  }return {seen,complete:true};
 }
 const a=bfs(state,Math.floor(maxDepth/2)),b=bfs(SOLVED,Math.ceil(maxDepth/2));
 let moves=null;
 for(const [key,p] of a.seen){
  const q=b.seen.get(key);
  if(q&&(!moves||p.length+q.length<moves.length))moves=p.concat(invert(q));
 }
 if(moves&&apply(state,moves)!==SOLVED)throw Error('Independent probe replay failed');
 return {moves,complete:a.complete&&b.complete,nodes:a.seen.size+b.seen.size};
}
function normalize(moves){ // merge consecutive same-face turns; preserves cube action
 const stack=[];const power=m=>m.endsWith('2')?2:m.endsWith("'")?3:1;
 for(const m of moves){
  if(stack.length&&stack[stack.length-1][0]===m[0]){
   const x=(power(stack.pop())+power(m))%4;
   if(x)stack.push(m[0]+(x===1?'':x===2?'2':"'"));
  }else stack.push(m);
 }return stack;
}
const engine={FACES,SOLVED,MOVES,turn,apply,invert,toCubeJS,scramble,shortProbe,normalize};
if(typeof module!=='undefined'&&module.exports)module.exports=engine;
if(typeof document==='undefined')return;
const $=id=>document.getElementById(id),faceBoxes={},net=$('cube-net');
const palette={U:'#f4f5ed',D:'#f3d542',F:'#52bc62',B:'#4f87de',R:'#e44b4b',L:'#fa9a37'};
for(const f of ['U','L','F','R','B','D']){
 const box=document.createElement('section');box.className='face face-'+f;
 const name=document.createElement('div');name.className='face-name';name.textContent=f;
 const cells=document.createElement('div');cells.className='face-cells';
 for(let i=0;i<9;i++){const tile=document.createElement('span');tile.className='tile';cells.append(tile);}
 box.append(name,cells);net.append(box);faceBoxes[f]=[...cells.children];
}
let state=SOLVED,origin=SOLVED,recipe=[],manual=false,answer=null,answerStep=0;
let pending=0,receipts=[];
const KEY='bean.rubiks3.case_routes.v1';
let learned={};try{learned=JSON.parse(localStorage.getItem(KEY)||'{}');}catch(e){learned={};}
function render(){
 for(let i=0;i<FACES.length;i++)for(let j=0;j<9;j++)
  faceBoxes[FACES[i]][j].style.background=palette[state[i*9+j]];
 $('current-state').textContent=state===SOLVED?'Solved':'Scrambled';
}
function say(txt){$('message').textContent=txt;}
function saveRoutes(start,moves){
 let pos=start,added=0,updated=0;
 for(let i=0;i<=moves.length;i++){
  const tail=moves.slice(i),prior=learned[pos];
  if(!prior||tail.length<prior.length){
   learned[pos]=tail;updated++;if(!prior)added++;
  }
  if(i<moves.length)pos=turn(pos,moves[i]);
 }
 const entries=Object.keys(learned);
 if(entries.length>1800)for(const key of entries.slice(0,entries.length-1800))delete learned[key];
 try{localStorage.setItem(KEY,JSON.stringify(learned));}catch(e){/* Still retain session memory. */}
 return {added,updated,stored:Object.keys(learned).length};
}
function recallRoutes(start,maxSteps=1){
 let best=learned[start]||null,used=best!==null;
 if(maxSteps>0){
  for(const m of MOVES){
   const tail=learned[turn(start,m)];
   if(tail&&(!best||1+tail.length<best.length)){best=[m,...tail];used=true;}
  }
 }
 return {moves:best,used};
}
const worker=new Worker('./rubiks-cube-worker.js');
let working=false,job=0;
worker.onerror=event=>{working=false;$('solve').disabled=false;say('Reference worker failed: '+event.message);};
worker.onmessage=function(event){
 const {id,algorithm,error}=event.data;
 if(id!==job)return;
 working=false;$('solve').disabled=false;
 const snapshot=origin;
 const receipt={id:++pending,seed:Number($('seed').value)>>>0,
  scramble_length:manual?null:recipe.length,
  scramble_trace:manual?null:[...recipe],starting_state:snapshot,
  reference:'cubejs unmodified Kociemba two-phase',engine_revision:'cubejs upstream lib',
  solution_length_limit:'none imposed by the experiment; cubejs default complete 3x3 solver',
  candidate:'case-memory reuse + six-move optimality probe',
  error:error||null};
 if(error){answer=null;say('Reference solver error: '+error);receipt.solved=false;
 }else{
  const raw=algorithm.trim()?algorithm.trim().split(/\s+/):[];
  const baseline=normalize(raw);
  if(apply(snapshot,baseline)!==SOLVED){say('Reference solution FAILED independent facelet replay.');
   receipt.error='Reference solution failed independent replay';receipt.solved=false;answer=null;
  }else{
   const memo=recallRoutes(snapshot),probe=shortProbe(snapshot);
   let choice={name:'two_phase_reference',moves:baseline};
   if(memo.moves&&memo.moves.length<choice.moves.length&&apply(snapshot,memo.moves)===SOLVED)
    choice={name:'learned_route_reuse',moves:memo.moves};
   if(probe.moves&&probe.moves.length<choice.moves.length)
    choice={name:'short_proof',moves:probe.moves};
   answer=choice.moves;answerStep=0;
   const learnedChange=saveRoutes(snapshot,answer);
   receipt.reference_moves=baseline;receipt.candidate_moves=answer;
   receipt.probe_complete=probe.complete;receipt.probe_nodes=probe.nodes;
   receipt.solved=true;receipt.selected=choice.name;receipt.learned=learnedChange;
   receipt.improvement_moves=baseline.length-answer.length;
   receipt.shorter_than_scramble=!manual&&answer.length<recipe.length;
   say('Solved in '+answer.length+' moves. Reference: '+baseline.length+
      '. Improvement: '+receipt.improvement_moves+' move(s). Method: '+choice.name+'.');
   $('summary').textContent='Solution: '+(answer.join(' ')||'(already solved)')+
     '. Saved '+learnedChange.stored+' reusable route states locally.';
  }
 }
 receipts.push(receipt);showReceipts();
};
function showReceipts(){
 const log=$('history');log.textContent='';
 for(const row of receipts.slice(-8).reverse()){
  const item=document.createElement('li');
  item.textContent='#'+row.id+': '+(row.solved?row.candidate_moves.length+'-move solution (reference '+row.reference_moves.length+')':'FAILED')+
    ', '+(row.selected||row.error||'unknown');
  log.append(item);
 }
}
$('scramble').onclick=()=>{
 if(working){say('The current attempt is still running.');return;}
 const seed=Number($('seed').value)>>>0,len=Number($('length').value);
 recipe=scramble(seed,len);state=apply(SOLVED,recipe);origin=state;manual=false;answer=null;answerStep=0;
 $('summary').textContent='Challenge generated from seed '+seed+', '+len+' face turns.';
 say('Scrambled. Solver gets only the 54 face stickers.');render();
};
$('shortcut').onclick=()=>{
 if(working)return;
 recipe=['R','L',"R'"];state=apply(SOLVED,recipe);origin=state;manual=false;answer=null;answerStep=0;
 $('summary').textContent="3-turn shortcut challenge, R L R'.";say('Can the search discover the one-turn solution?');render();
};
$('reset').onclick=()=>{
 if(working)return;state=SOLVED;origin=state;recipe=[];answer=null;answerStep=0;manual=false;
 $('summary').textContent='Cube reset.';say('Ready for a challenge.');render();
};
for(const m of MOVES){
 const btn=document.createElement('button');btn.className='move';btn.textContent=m;
 btn.onclick=()=>{
  if(working)return;
  state=turn(state,m);origin=state;manual=true;answer=null;answerStep=0;
  say('Manual turn '+m+' recorded. This state has no scramble-length comparator.');render();
 };$('moves').append(btn);
}
$('solve').onclick=()=>{
 if(working)return;working=true;answer=null;answerStep=0;job++;origin=state;
 $('solve').disabled=true;
 say('Reference solver calculating in a worker. Prior routes can improve the returned move count.');
 $('summary').textContent='Exploring legal cube states, not applying the inverse scramble.';
 worker.postMessage({id:job,facelets:toCubeJS(origin)});
};
$('play').onclick=()=>{
 if(!answer){say('Solve the current position first.');return;}
 if(answerStep===0)state=origin;
 if(answerStep<answer.length){
  state=turn(state,answer[answerStep++]);render();
  say('Move '+answerStep+' / '+answer.length+'. '+(state===SOLVED?'Solved!':''));
 }else say('Solution fully played.');
};
$('export').onclick=()=>{
 const payload={schema:'bean.rubiks3.browser.v2',scope:'local browser only',
  provenance:'two-phase cubejs reference plus case-based route reuse; not BEAN Python Core',
  source:'https://github.com/danieloculus0-bot/BEAN/pull/199',
  memory_states:Object.keys(learned).length,receipts};
 const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'}));
 const a=document.createElement('a');a.href=url;a.download='bean-rubiks-cube-receipts.json';a.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
};
render();
})();