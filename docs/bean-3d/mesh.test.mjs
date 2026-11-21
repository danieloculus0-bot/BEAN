import test from "node:test";
import assert from "node:assert/strict";
import {wovenCoaster,ring,fromPrompt,bounds,binarySTL,obj,decodeSTL} from "./mesh.mjs";

function checkClosedManifold(mesh) {
  const counts=new Map(),f=mesh.triangles;
  for(let i=0;i<f.length;i+=3) {
    for(const [a,b] of [[f[i],f[i+1]],[f[i+1],f[i+2]],[f[i+2],f[i]]]){
      const edge=Math.min(a,b)+":"+Math.max(a,b);
      counts.set(edge,(counts.get(edge)||0)+1);
    }
  }
  for(const count of counts.values()) assert.equal(count,2);
}

test("coaster is one closed, printable-height mesh with STL geometry",async()=>{
  const mesh=wovenCoaster({diameter:96,thickness:2.4,relief:.7,radialSteps:24,angularSteps:72});
  const b=bounds(mesh);
  assert.ok(Math.abs(b.size[0]-96)<.1 && Math.abs(b.size[1]-96)<.1);
  assert.ok(b.size[2]>=2.4 && b.size[2]<3.4);
  checkClosedManifold(mesh);
  const blob=binarySTL(mesh),buffer=await blob.arrayBuffer();
  assert.equal(buffer.byteLength,84+mesh.triangles.length/3*50);
  const restored=decodeSTL(buffer);
  assert.equal(restored.triangles.length,mesh.triangles.length);
  assert.ok((await obj(mesh).text()).includes("\nf "));
});
test("ring mesh is manifold and correctly sized",()=>{
  const mesh=ring({diameter:80,thickness:4,wall:5,angularSteps:64});
  checkClosedManifold(mesh);
  const b=bounds(mesh);
  assert.ok(Math.abs(b.size[0]-80)<1e-4);
  assert.equal(b.size[2],4);
});
test("prompt parser is deliberately constrained",()=>{
  assert.equal(fromPrompt("washer").kind,"ring");
  assert.equal(fromPrompt("rope coaster").kind,"woven-coaster");
});
test("bad binary STL rejected",()=>{
  assert.throws(()=>decodeSTL(new ArrayBuffer(5)));
});
