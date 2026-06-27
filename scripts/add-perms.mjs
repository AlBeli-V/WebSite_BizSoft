// Доп. права сервисной политике: products create/delete (для пакетной заливки).
import { readFileSync } from 'node:fs';
function le(p){const o={};try{for(const l of readFileSync(p,'utf8').split(/\r?\n/)){const t=l.trim();if(!t||t.startsWith('#'))continue;const i=t.indexOf('=');if(i<0)continue;o[t.slice(0,i).trim()]=t.slice(i+1).trim();}}catch{}return o;}
const env={...(process.env.ENV_FILE?le(process.env.ENV_FILE):{}),...process.env};
const URL=(env.DIRECTUS_URL||'http://directus:8055').replace(/\/$/,'');
let token='';
async function api(m,p,b){const r=await fetch(URL+p,{method:m,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},body:b?JSON.stringify(b):undefined});const t=await r.text();let j;try{j=t?JSON.parse(t):{}}catch{j={raw:t}}if(!r.ok)throw new Error(`${m} ${p} ${r.status} ${j?.errors?.[0]?.message||t.slice(0,120)}`);return j.data;}
const r=await fetch(URL+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:env.ADMIN_EMAIL,password:env.ADMIN_PASSWORD})});
token=(await r.json()).data.access_token;
const pol=await api('GET','/policies?filter[name][_eq]=Site Service Policy&limit=1');
if(!pol.length)throw new Error('policy not found');
const pid=pol[0].id;
const perms=await api('GET',`/permissions?filter[policy][_eq]=${pid}&limit=-1`);
const have=new Set(perms.map(p=>`${p.collection}:${p.action}`));
for(const [c,a] of [['products','create'],['products','delete']]){
  if(have.has(`${c}:${a}`)){console.log('= '+c+':'+a);continue;}
  await api('POST','/permissions',{policy:pid,collection:c,action:a,fields:['*'],permissions:{},validation:{}});
  console.log('✓ added '+c+':'+a);
}
console.log('done');
