const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const code=fs.readFileSync('cdn_office_suite/connection.js','utf8');
function connection(config,origin='http://server:4444'){const ctx={window:{OFFICE_CONFIG:config},location:{origin,hostname:new URL(origin).hostname},URL,Number,Set,Object};vm.createContext(ctx);vm.runInContext(code,ctx);return ctx.window.OFFICE_CONNECTION;}
const ports={port:8877,oc4dPort:3333,mailPort:2222};
const c=connection(ports);assert.equal(c.service,'http://server:8877/');assert.equal(c.mail,'http://server:2222/');ports.port=4444;assert.equal(c.ports.port,8877);assert(Object.isFrozen(c.ports));
for(const config of [undefined,{}, {port:8877,oc4dPort:3333}, {port:'8877',oc4dPort:3333,mailPort:2222},{port:8877,oc4dPort:8877,mailPort:2222}]){const c=connection(config);assert(c.error);assert.equal(c.service,undefined);assert.equal(c.mail,undefined);}
console.log('Port tests passed: custom office/mail endpoints stay explicit; missing, invalid or colliding configuration fails closed.');

function scripts(file){return [...fs.readFileSync(file,'utf8').matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');}
for(const page of ['index','updates']){
 const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',href:'#',setAttribute(){},removeAttribute(k){delete this[k];}});return nodes.get(id);};
 const links=Array.from({length:8},()=>({href:'#',setAttribute(){},removeAttribute(k){delete this[k];}})),statuses=Array.from({length:8},()=>({textContent:''}));
 let requests=0;
 const ctx={window:{OFFICE_CONNECTION:{error:'Invalid saved ports'},addEventListener(){}},document:{getElementById:node,querySelectorAll:s=>s.includes('Link')?links:statuses},location:{origin:'http://server:4444',hostname:'server'},URL,Set,Number,fetch:()=>{requests++;throw new Error('Should not request another port');},setInterval:()=>{throw new Error('Should not poll without ports');}};
 vm.createContext(ctx);vm.runInContext(scripts('cdn_office_suite/'+page+'.html'),ctx);
 assert.equal(requests,0,page+' must not guess an endpoint');
 if(page==='index'){assert(links.every(a=>a.href===undefined));assert.equal(node('serverName').textContent,'Invalid saved ports');}
 else assert.equal(node('accessMessage').textContent,'Invalid saved ports');
}
console.log('Actual launcher and Updates scripts issue no requests with invalid port settings.');

const suffix='.52.47.49.176.nip.io';
for(const origin of ['http://192x168x191x243-3000'+suffix,'https://192x168x191x243-3000'+suffix,'http://192x168x191x243'+suffix]){
 const c=connection({port:8769,oc4dPort:3000,mailPort:2000},origin);
 assert.equal(c.gateway,true);
 assert.equal(new URL(c.service).hostname,'192x168x191x243-8769'+suffix);
 assert.equal(new URL(c.mail).hostname,'192x168x191x243-2000'+suffix);
 assert.equal(new URL(c.service).port,'');
 assert.equal(new URL(c.service).protocol,new URL(origin).protocol);
}
const customGateway=connection({port:8877,oc4dPort:3333,mailPort:2222},'https://192x168x191x243-3333'+suffix+':8443');
assert.equal(customGateway.service,'https://192x168x191x243-8877'+suffix+':8443/');
assert.equal(customGateway.mail,'https://192x168x191x243-2222'+suffix+':8443/');
console.log('Gateway links retain the public origin port and encode the private app/mail port in the hostname.');
