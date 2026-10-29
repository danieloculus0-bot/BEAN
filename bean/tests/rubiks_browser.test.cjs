/* Independent 3x3 contract against the unmodified vendored cubejs reference. */
const assert=require('node:assert/strict');
const Cube=require('../../docs/vendor/cubejs/cube.js');
require('../../docs/vendor/cubejs/solve.js');
const ours=require('../../docs/rubiks-cube.js');
assert.equal(ours.MOVES.length,18);
assert.equal(ours.toCubeJS(ours.SOLVED),[...'URFDLB'].map(f=>f.repeat(9)).join(''));
for(const m of ours.MOVES){
 const state=ours.turn(ours.SOLVED,m);
 assert.equal(ours.apply(state,ours.invert([m])),ours.SOLVED,'inverse '+m);
 const reference=new Cube();reference.move(m);
 assert.equal(ours.toCubeJS(state),reference.asString(),'independent turn '+m);
}
for(const moves of [
 ['R','U',"R'","U'"],['F','L','B','D','U2','R2'],
 ours.scramble(42,20),ours.scramble(5,50)]){
 const state=ours.apply(ours.SOLVED,moves);
 const reference=new Cube();reference.move(moves.join(' '));
 assert.equal(ours.toCubeJS(state),reference.asString(),'sticker geometry');
}
const short=ours.apply(ours.SOLVED,['R','L',"R'"]);
const probe=ours.shortProbe(short);
assert.ok(probe.complete);
assert.equal(probe.moves.length,1);
assert.equal(ours.apply(short,probe.moves),ours.SOLVED);
const start=Date.now(); Cube.initSolver();
for(const seed of [0,1,2,13,21,42,81]){
 const state=ours.apply(ours.SOLVED,ours.scramble(seed,40));
 const cube=Cube.fromString(ours.toCubeJS(state));
 assert.equal(cube.asString(),ours.toCubeJS(state));
 const raw=cube.solve();
 assert.equal(typeof raw,'string');
 const solution=raw.trim()?raw.trim().split(/\s+/):[];
 assert.equal(ours.apply(state,solution),ours.SOLVED,'full scramble seed '+seed);
 assert.ok(solution.length<=22,'documented cubejs reachability bound');
 console.log(JSON.stringify({seed,recipe_length:40,solution_length:solution.length,solved:true}));
}
console.log('Independent cubejs reference tests PASSED; runtime '+(Date.now()-start)+'ms');
