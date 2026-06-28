#!/usr/bin/env node
/** Переименование ChatGPT Team → ChatGPT Business (name, slug, former_names, old_slugs). */
import { readFileSync } from 'node:fs';
function le(p){const o={};try{for(const l of readFileSync(p,'utf8').split(/\r?\n/)){const t=l.trim();if(!t||t.startsWith('#'))continue;const i=t.indexOf('=');if(i<0)continue;o[t.slice(0,i).trim()]=t.slice(i+1).trim();}}catch{}return o;}
const env={...(process.env.ENV_FILE?le(process.env.ENV_FILE):{}),...process.env};
const URL=(env.DIRECTUS_URL||'http://directus:8055').replace(/\/$/,'');
let token='';
async function api(m,p,b){const r=await fetch(URL+p,{method:m,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},body:b?JSON.stringify(b):undefined});const t=await r.text();let j;try{j=t?JSON.parse(t):{}}catch{j={raw:t}}if(!r.ok)throw new Error(`${m} ${p} ${r.status} ${j?.errors?.[0]?.message||t.slice(0,160)}`);return j.data;}
const r=await fetch(URL+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:env.ADMIN_EMAIL,password:env.ADMIN_PASSWORD})});
token=(await r.json()).data.access_token;
console.log('✓ login');

// найти продукт по старому slug или sku
let rows=await api('GET','/items/products?filter[slug][_eq]=int-ai-chatgpt&fields=id,slug,name&limit=1');
if(!rows.length) rows=await api('GET','/items/products?filter[sku][_eq]=INT-AI-CHATGPT&fields=id,slug,name&limit=1');
if(!rows.length){ console.log('! продукт ChatGPT не найден (возможно уже переименован)');
  const cur=await api('GET','/items/products?filter[slug][_eq]=chatgpt-business&fields=id,name,slug&limit=1');
  console.log(cur.length?`= уже: ${cur[0].name} /${cur[0].slug}`:'?? не найден ни старый, ни новый'); process.exit(0);
}
const p=rows[0];
await api('PATCH',`/items/products/${p.id}`,{
  name:'ChatGPT Business',
  slug:'chatgpt-business',
  former_names:[{value:'ChatGPT Team'}],
  old_slugs:[{value:'int-ai-chatgpt'}],
});
console.log(`✓ ${p.name} (/${p.slug}) → ChatGPT Business (/chatgpt-business)`);
console.log('\n✅ RENAME COMPLETE');
