const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
class Element {constructor(){this.hidden=false;this.dataset={};this.textContent='';this.disabled=false;this.value=0;}removeAttribute(name){delete this[name];} }
const nodes=new Map(),el=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
const controls=[new Element(),new Element()];let response,offline=false;
const sandbox={URL,AbortSignal,console,Date,Number,Set,Promise,location:{origin:'http://192.168.191.89'},localStorage:{getItem:()=> 'test-token'},window:{OFFICE_CONNECTION:{service:'http://192.168.191.89:8769/',mail:'http://192.168.191.89:2000/'},addEventListener(){}},document:{getElementById:el,querySelectorAll:()=>controls},setTimeout:()=>1,clearTimeout(){},fetch:async()=>{if(offline)throw new TypeError('Disconnected');return {ok:true,status:200,json:async()=>response};}};
vm.createContext(sandbox);
const html=fs.readFileSync('cdn_office_suite/updates.html','utf8');const script=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n').replace('if(service)initialize();','if(service){}');vm.runInContext(script,sandbox);
(async()=>{
const base={installed:'v0.5.0',latest:'v0.6.0',available:true,notes:null,previous:null,jobId:'approved-job',version:'v0.6.0'};
response={apps:{deckcraft:{...base,phase:'installing',step:'download',progress:40,downloadedBytes:400,totalBytes:1000,attempt:1,updatedAt:10,message:'Downloading'}}};
await vm.runInContext('refresh()',sandbox);assert.equal(el('deckcraft-progress').value,40);assert.equal(el('deckcraft-job').hidden,false);
offline=true;await vm.runInContext('refresh()',sandbox);assert.equal(el('connectionStatus').hidden,false);assert.equal(el('deckcraft-progress').value,40);assert(controls.every(b=>b.disabled));
offline=false;response={apps:{deckcraft:{...base,phase:'retrying',step:'waiting',progress:40,attempt:2,updatedAt:11,nextRetryAt:Date.now()/1000+60,message:'Waiting for internet'}}};
await vm.runInContext('refresh()',sandbox);assert.equal(el('connectionStatus').hidden,true);assert.equal(el('deckcraft-step').textContent,'Download paused');assert.match(el('deckcraft-detail').textContent,/Attempt 2/);assert(controls.every(b=>b.disabled));
response={apps:{deckcraft:{...base,installed:'v0.6.0',phase:'complete',step:'done',progress:100,updatedAt:12,message:'Installed'}}};await vm.runInContext('refresh()',sandbox);assert.equal(el('deckcraft-progress').value,100);assert(controls.every(b=>!b.disabled));
response={apps:{deckcraft:{...base,phase:'installing',step:'download',progress:30,updatedAt:9}}};await vm.runInContext('refresh()',sandbox);assert.equal(el('deckcraft-progress').value,100);
console.log('Update UI tests passed: disconnect retains progress; reconnect restores retry and completion; stale responses cannot rewind progress.');
})().catch(e=>{console.error(e);process.exitCode=1;});
