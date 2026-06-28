#!/usr/bin/env node
/** Миграция v4: поля масштабирования (SEO-архитектура) для товаров и категорий. */
import { readFileSync } from 'node:fs';
function le(p){const o={};try{for(const l of readFileSync(p,'utf8').split(/\r?\n/)){const t=l.trim();if(!t||t.startsWith('#'))continue;const i=t.indexOf('=');if(i<0)continue;o[t.slice(0,i).trim()]=t.slice(i+1).trim();}}catch{}return o;}
const env={...(process.env.ENV_FILE?le(process.env.ENV_FILE):{}),...process.env};
const URL=(env.DIRECTUS_URL||'http://directus:8055').replace(/\/$/,'');
let token='';
async function api(m,p,b){const r=await fetch(URL+p,{method:m,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},body:b?JSON.stringify(b):undefined});const t=await r.text();let j;try{j=t?JSON.parse(t):{}}catch{j={raw:t}}if(!r.ok)throw new Error(`${m} ${p} ${r.status} ${j?.errors?.[0]?.message||t.slice(0,140)}`);return j.data;}
async function fields(c){return new Set((await api('GET',`/fields/${c}`)).map(f=>f.field));}
async function ensureField(c,f,def){const have=await fields(c);if(have.has(f)){console.log('= '+c+'.'+f);return;}await api('POST',`/fields/${c}`,{field:f,...def});console.log('✓ '+c+'.'+f);}
const listField=(note)=>({type:'json',meta:{interface:'list',options:{fields:[{field:'value',type:'string',meta:{interface:'input'}}]},note}});
const qaField=(note)=>({type:'json',meta:{interface:'list',options:{fields:[{field:'q',type:'string',meta:{interface:'input'}},{field:'a',type:'string',meta:{interface:'input-multiline'}}]},note}});

const r=await fetch(URL+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:env.ADMIN_EMAIL,password:env.ADMIN_PASSWORD})});
token=(await r.json()).data.access_token;
console.log('✓ login');

// ── products ──
await ensureField('products','noindex',{type:'boolean',meta:{interface:'boolean',width:'half',note:'Исключить из индексации (не попадёт в sitemap)'},schema:{default_value:false}});
await ensureField('products','date_updated',{type:'timestamp',meta:{interface:'datetime',width:'half',readonly:true,special:['date-updated'],note:'Дата обновления (для lastmod)'}});
await ensureField('products','for_whom',{type:'text',meta:{interface:'input-multiline',note:'Для кого подходит'}});
await ensureField('products','use_cases',{...listField('Какие задачи закрывает (список)')});
await ensureField('products','former_names',{...listField('Прежние названия (для редиректов/синонимов)')});
await ensureField('products','old_slugs',{...listField('Старые slug (301-редирект на текущий)')});
await ensureField('products','related_products',{...listField('Связанные товары (slug)')});
await ensureField('products','related_solutions',{...listField('Связанные решения (slug)')});
await ensureField('products','price_from',{type:'boolean',meta:{interface:'boolean',width:'half',note:'Показывать цену как «от»'},schema:{default_value:false}});

// ── categories ──
await ensureField('categories','intro',{type:'text',meta:{interface:'input-multiline',note:'Краткий ответ/intro вверху раздела'}});
await ensureField('categories','faqs',{...qaField('FAQ раздела')});
await ensureField('categories','noindex',{type:'boolean',meta:{interface:'boolean',width:'half'},schema:{default_value:false}});
await ensureField('categories','related_products',{...listField('Связанные товары (slug)')});
await ensureField('categories','related_articles',{...listField('Связанные статьи (slug)')});

console.log('\n✅ MIGRATION v4 COMPLETE');
