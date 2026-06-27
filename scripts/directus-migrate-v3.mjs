#!/usr/bin/env node
/** Миграция v3: мультивалютная привязка (USD/EUR) + коэффициент наценки + фиксация цены. */
import { readFileSync } from 'node:fs';
function le(p){const o={};try{for(const l of readFileSync(p,'utf8').split(/\r?\n/)){const t=l.trim();if(!t||t.startsWith('#'))continue;const i=t.indexOf('=');if(i<0)continue;o[t.slice(0,i).trim()]=t.slice(i+1).trim();}}catch{}return o;}
const env={...(process.env.ENV_FILE?le(process.env.ENV_FILE):{}),...process.env};
const URL=(env.DIRECTUS_URL||'http://directus:8055').replace(/\/$/,'');
let token='';
async function api(m,p,b){const r=await fetch(URL+p,{method:m,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},body:b?JSON.stringify(b):undefined});const t=await r.text();let j;try{j=t?JSON.parse(t):{}}catch{j={raw:t}}if(!r.ok)throw new Error(`${m} ${p} ${r.status} ${j?.errors?.[0]?.message||t.slice(0,140)}`);return j.data;}
async function fields(c){return new Set((await api('GET',`/fields/${c}`)).map(f=>f.field));}
async function ensureField(c,f,def){const have=await fields(c);if(have.has(f)){console.log('= '+c+'.'+f);return;}await api('POST',`/fields/${c}`,{field:f,...def});console.log('✓ '+c+'.'+f);}

const r=await fetch(URL+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:env.ADMIN_EMAIL,password:env.ADMIN_PASSWORD})});
token=(await r.json()).data.access_token;
console.log('✓ login');

await ensureField('products','base_price_eur',{type:'float',meta:{interface:'input',width:'half',note:'Закупочная цена в EUR (себестоимость с сайта производителя)'}});
await ensureField('products','peg_currency',{type:'string',meta:{interface:'select-dropdown',width:'half',note:'Валюта закупки (для пересчёта в рубли по курсу ЦБ)',options:{choices:[{text:'Доллар США (USD)',value:'USD'},{text:'Евро (EUR)',value:'EUR'}]}},schema:{default_value:'USD'}});
await ensureField('products','markup_coeff',{type:'float',meta:{interface:'input',width:'half',note:'Коэффициент наценки (рубл.цена = себестоимость × курс × коэф). База 1.85'},schema:{default_value:1.85}});
await ensureField('products','price_locked',{type:'boolean',meta:{interface:'boolean',width:'half',note:'Цена зафиксирована вручную — массовые переоценки её НЕ меняют'},schema:{default_value:false}});
await ensureField('currency_rate','eur_rate',{type:'float',meta:{interface:'input',note:'Рублей за 1 EUR'}});

// проставим значения по умолчанию существующим привязанным товарам
const pegged=await api('GET','/items/products?filter[peg_to_usd][_eq]=true&fields=id,peg_currency,markup_coeff&limit=-1');
let fixed=0;
for(const p of pegged){
  const upd={};
  if(!p.peg_currency) upd.peg_currency='USD';
  if(p.markup_coeff==null) upd.markup_coeff=1.85;
  if(Object.keys(upd).length){ await api('PATCH',`/items/products/${p.id}`,upd); fixed++; }
}
console.log('✓ defaults set on '+fixed+' pegged products');
console.log('\n✅ MIGRATION v3 COMPLETE');
