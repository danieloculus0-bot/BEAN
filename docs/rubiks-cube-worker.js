/* BEAN browser cube reference: original cubejs two-phase solver, MIT. */
'use strict';
importScripts('./vendor/cubejs/cube.js','./vendor/cubejs/solve.js');
let ready=false;
self.onmessage=function(event){
  const {id,facelets}=event.data||{};
  try{
    if(!ready){Cube.initSolver();ready=true;}
    if(typeof facelets!=='string'||facelets.length!==54)throw Error('Expected 54 facelets');
    const parsed=Cube.fromString(facelets);
    if(parsed.asString()!==facelets)throw Error('Unreachable cube configuration');
    const raw=parsed.solve();
    if(typeof raw!=='string')throw Error('Two-phase reference returned no solution');
    self.postMessage({id,algorithm:raw,engine:'cubejs two-phase reference'});
  }catch(error){self.postMessage({id,error:String(error.message||error)});}
};