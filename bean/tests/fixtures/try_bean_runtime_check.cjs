/* Executable BEAN browser-memory contract test. Offline Node.js, fake storage.
 * Proves REAL SHA-256 append/reload/retrieval/corruption detection. No network.
 */
"use strict";
const assert=require("node:assert/strict");
const path=require("node:path");
const {webcrypto}=require("node:crypto");
if(!globalThis.crypto?.subtle) Object.defineProperty(globalThis,"crypto",{value:webcrypto,configurable:true});
const script=path.resolve(__dirname,"../../../docs/try-bean-memory.js");
const saved=new Map();
const storage={
  getItem(key){return saved.has(key)?saved.get(key):null;},
  setItem(key,val){saved.set(key,String(val));},
  removeItem(key){saved.delete(key);}
};
async function run() {
  require(script);
  let bean=globalThis.BEANBrowserMemory;
  const empty=await bean.verify(storage);
  assert.equal(empty.records.length,0);
  await bean.add(storage,{subject:"Project color",statement:"The sample project uses orange.",source:"human-entered"});
  const one=await bean.verify(storage);
  assert.equal(one.records.length,1);
  assert.match(one.tip,/^[a-f0-9]{64}$/);
  assert.equal(one.records[0].evidence,"UNVERIFIED");
  // Browser reload re-runs JavaScript with existing localStorage.
  delete require.cache[require.resolve(script)];
  delete globalThis.BEANBrowserMemory;
  require(script);
  bean=globalThis.BEANBrowserMemory;
  const reopened=await bean.verify(storage);
  assert.deepEqual(reopened,one);
  assert.equal(bean.recall(reopened.records,"What color is the project?").length,1);
  assert.equal(bean.recall(reopened.records,"unknown bicycle").length,0);
  assert.match(bean.context(reopened.records,"project"),/UNVERIFIED/);
  assert.match(bean.context(reopened.records,"project"),/not BEAN Core/);
  await bean.add(storage,{subject:"Project color",statement:"The sample project uses blue.",source:"pasted-ai-text"});
  const two=await bean.verify(storage);
  assert.equal(two.records.length,2);
  assert.notEqual(two.records[0].hash,two.records[1].hash);
  assert.equal(bean.recall(two.records,"project color").length,2);
  assert.equal(two.records[1].prevHash,two.records[0].hash);
  const original=saved.get(bean.KEY);
  // Rewriting a stored claim without recomputing its hash must fail closed.
  const changed=JSON.parse(original);changed[0].statement="Fabricated replacement claim";
  saved.set(bean.KEY,JSON.stringify(changed));
  await assert.rejects(()=>bean.verify(storage),/SHA-256/);
  await assert.rejects(()=>bean.add(storage,{subject:"foo",statement:"bar",source:"human-entered"}),/SHA-256/);
  saved.set(bean.KEY,original);
  await assert.rejects(()=>bean.add(storage,{subject:"foo",statement:"bar",source:"unknown"}),/Select a recognized source/);
  bean.clear(storage);
  assert.equal((await bean.verify(storage)).records.length,0);
  process.stdout.write("Browser memory proof: PASS (SHA-256, session restart, recall, contradictions, tamper, abstention, clear)\n");
}
run().catch(err=>{console.error(err);process.exitCode=1;});
