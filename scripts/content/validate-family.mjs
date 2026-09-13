#!/usr/bin/env node
// Валидатор семейства content_modules. Запуск: node validate-family.mjs <family.json> [--published slugs.txt]
// Выход: список ошибок (ERROR — блокирует), предупреждений (WARN) и сводка. Код возврата 1 при ERROR.
import fs from 'node:fs';

const file = process.argv[2];
if (!file) { console.error('usage: validate-family.mjs <family.json> [--published slugs.txt]'); process.exit(2); }
const pubIdx = process.argv.indexOf('--published');
const published = pubIdx > 0 ? new Set(fs.readFileSync(process.argv[pubIdx + 1], 'utf8').split(/\r?\n/).map((s) => s.trim().replace(/^.*\/product\//, '')).filter(Boolean)) : null;

const fam = JSON.parse(fs.readFileSync(file, 'utf8'));
const errors = [], warns = [];
const E = (s, m) => errors.push(`${s}: ${m}`);
const W = (s, m) => warns.push(`${s}: ${m}`);

const LIB = new Set(['CAPABILITIES','INCLUDED','ADDON_SCOPE','CREDIT_USAGE','PERPETUAL_RULES','RENEWAL_RULES','TEAM_MODEL','INDIVIDUAL_MODEL','PLAN_COMPARE','FIT','TRADEOFFS','DEPENDENCIES','CONFIGURATION','SUPPORT_MAINTENANCE','BEFORE_ORDER','ALTERNATIVES']);

// Матрица класс → обязательные / запрещённые (README п. 3.2)
const RULES = [
  { when: (c) => c.nature === 'mono', req: ['CAPABILITIES', 'FIT'], forb: ['INCLUDED'] },
  { when: (c) => c.nature === 'suite', req: ['INCLUDED', 'FIT|INDIVIDUAL_MODEL'], forb: [] },
  // team: у дополнения (addon) командная модель принадлежит базовому продукту — достаточно TRADEOFFS со ссылкой
  { when: (c) => c.ownership === 'team' && c.nature !== 'addon', req: ['TEAM_MODEL', 'TRADEOFFS'], forb: [] },
  { when: (c) => c.ownership === 'team' && c.nature === 'addon', req: ['TRADEOFFS'], forb: [] },
  { when: (c) => c.ownership === 'individual', req: ['INDIVIDUAL_MODEL'], forb: [] },
  { when: (c) => c.nature === 'addon', req: ['ADDON_SCOPE', 'DEPENDENCIES', 'FIT'], forb: ['INCLUDED', 'TEAM_MODEL'] },
  { when: (c) => c.nature === 'credit', req: ['CREDIT_USAGE', 'PLAN_COMPARE', 'FIT', 'BEFORE_ORDER'], forb: ['INCLUDED', 'TEAM_MODEL'] },
  { when: (c) => /perpetual/.test(c.term), req: ['PERPETUAL_RULES', 'PLAN_COMPARE'], forb: [] },
  { when: (c) => c.nature === 'service', req: ['RENEWAL_RULES', 'SUPPORT_MAINTENANCE', 'BEFORE_ORDER'], forb: ['CAPABILITIES'] },
  { when: (c) => c.packaging === 'edition_tier', req: ['PLAN_COMPARE'], forb: [] },
  // volume_tier: выбор объёма — в PLAN_COMPARE, а если на витрине один объём — в BEFORE_ORDER
  { when: (c) => c.packaging === 'volume_tier', req: ['PLAN_COMPARE|BEFORE_ORDER'], forb: [] },
  { when: (c) => c.packaging === 'configuration' || c.packaging === 'composite', req: ['CONFIGURATION'], forb: ['INCLUDED'] },
];

const BANNED = ['мощное решение','идеальный выбор','широкий спектр','в современном мире','выводит на новый уровень','раскрывает потенциал','инновационн','передов','незаменим','уникальн','лучшее решение','высокое качество'];
const TEMPLATE_OPENERS = ['Кому подходит:','Типичный сценарий','Оформим на вашу компанию','Что входит:'];

const textOf = (m) => [m.body || '', ...(m.items || []).map((i) => `${i.t}. ${i.d}`), ...(m.rows || []).map((r) => `${r.label}: ${Object.values(r.values || {}).join(' / ')}`)].join('\n');
const norm = (s) => s.toLowerCase().replace(/[«»"()\[\],.;:!?—–-]/g, ' ').replace(/\s+/g, ' ').trim();
const shingles = (s, n = 8) => { const w = norm(s).split(' ').filter(Boolean); const out = new Set(); for (let i = 0; i + n <= w.length; i++) out.add(w.slice(i, i + n).join(' ')); return out; };
const inter = (a, b) => [...a].filter((x) => b.has(x));

const slugs = Object.keys(fam.products || {});
if (!fam.family_key) E('family', 'нет family_key');
if (!slugs.includes(fam.carrier_slug)) E('family', `carrier_slug ${fam.carrier_slug} не в семействе`);

const pageShingles = {};
for (const slug of slugs) {
  const p = fam.products[slug];
  const c = p.classification || {};
  for (const k of ['nature', 'ownership', 'term', 'metric', 'packaging']) if (!c[k]) E(slug, `classification.${k} пуст`);
  if (!p.unit_label) E(slug, 'unit_label пуст');
  if (c.nature === 'addon' && !p.base_product_sku) E(slug, 'addon без base_product_sku');

  // hero
  const sd = p.short_description || '';
  const lede = sd.split(/\n{2,}/)[0];
  if (!sd) E(slug, 'short_description пуст');
  if (lede.length > 360) E(slug, `первый абзац hero ${lede.length} > 360`);
  if (/^\s*что входит:/i.test(lede)) E(slug, 'hero начинается с «Что входит:»');
  if (c.ownership === 'team' && !/командн(ая|ый) (подписк|план)/i.test(lede)) E(slug, 'в первом абзаце нет фразы «командная подписка/командный план» (читает плашка)');
  if (c.ownership === 'individual' && !/индивидуальн(ая|ый) (подписк|план)/i.test(lede)) E(slug, 'в первом абзаце нет фразы «индивидуальная подписка/индивидуальный план»');
  if (/\d[\d\s]*\s?(₽|руб|\$|€)/.test(sd)) E(slug, 'сумма с валютой в hero');

  // modules
  const mods = p.content_modules || [];
  const codes = mods.map((m) => m.code);
  if (mods.length < 4 || mods.length > 7) E(slug, `модулей ${mods.length}, нужно 4–7`);
  for (const m of mods) {
    if (!LIB.has(m.code)) E(slug, `модуль ${m.code} не из библиотеки`);
    if (!m.title) E(slug, `${m.code}: нет заголовка`);
    if (!['prose', 'items', 'compare'].includes(m.kind)) E(slug, `${m.code}: kind ${m.kind}`);
    const t = textOf(m);
    if (t.length < 140 || t.length > 1600) W(slug, `${m.code}: объём ${t.length} (ориентир 140–1600)`);
    if (m.kind === 'items' && (!m.items || m.items.length < 2 || m.items.length > 8)) E(slug, `${m.code}: items ${m.items?.length}`);
    if (m.kind === 'compare' && (!m.rows || m.rows.length < 3 || m.rows.length > 8)) E(slug, `${m.code}: rows ${m.rows?.length}`);
    for (const l of [...(m.links || []), ...((m.items || []).map((i) => i.link).filter(Boolean))]) {
      if (!slugs.includes(l) && published && !published.has(l)) E(slug, `${m.code}: ссылка на неопубликованный slug ${l}`);
    }
    if (/\d[\d\s]*\s?(₽|руб\.)/.test(t)) E(slug, `${m.code}: сумма в рублях в тексте`);
  }
  const has = (x) => x.split('|').some((k) => codes.includes(k));
  for (const r of RULES) if (r.when(c)) {
    for (const q of r.req) if (!has(q)) E(slug, `обязательный модуль ${q} отсутствует (класс ${JSON.stringify(c)})`);
    for (const f of r.forb) if (codes.includes(f)) E(slug, `запрещённый модуль ${f} для класса`);
  }
  if (c.nature === 'credit' && /рабоч\w+ мест/i.test(textOf({ body: sd }) + mods.map(textOf).join(' '))) E(slug, 'credit: упоминание рабочих мест');
  if (/perpetual/.test(c.term) && /срок действия (плана )?подписки/i.test(sd + mods.map(textOf).join(' '))) E(slug, 'perpetual: подписочная формулировка срока');

  // faq
  const faq = p.faq || [];
  if (faq.length > 5) E(slug, `FAQ ${faq.length} > 5`);
  for (const f of faq) if (/оплат|счёт|счет|эдо|закрывающ|документ|регистрир|учётн\w+ запис|доступ (передаётся|предоставляется)/i.test(f.q)) E(slug, `FAQ о механике сделки: «${f.q}»`);

  // banned & template
  const all = sd + '\n' + mods.map(textOf).join('\n') + '\n' + faq.map((f) => f.q + ' ' + f.a).join('\n');
  for (const b of BANNED) if (all.toLowerCase().includes(b)) E(slug, `запрещённая фраза «${b}»`);
  for (const t of TEMPLATE_OPENERS) if (all.includes(t)) W(slug, `шаблонная конструкция «${t}»`);

  // meta
  if (!p.meta_title || p.meta_title.length > 60) E(slug, `meta_title ${p.meta_title?.length ?? 0} (≤60)`);
  if (!p.meta_description || p.meta_description.length > 160) E(slug, `meta_description ${p.meta_description?.length ?? 0} (≤160)`);
  for (const r of p.related_products || []) if (!slugs.includes(r) && published && !published.has(r)) E(slug, `related_products: ${r} не опубликован`);

  // module_log
  const logged = new Set((p.module_log || []).map((l) => l.module));
  for (const m of mods) if (!logged.has(m.code)) E(slug, `${m.code}: нет записи в module_log`);

  // intra-page overlap
  const perMod = mods.map((m) => ({ code: m.code, sh: shingles(textOf(m)) }));
  perMod.push({ code: 'HERO', sh: shingles(sd) });
  for (let i = 0; i < perMod.length; i++) for (let j = i + 1; j < perMod.length; j++) {
    const x = inter(perMod[i].sh, perMod[j].sh);
    if (x.length) E(slug, `повтор ≥8 слов между ${perMod[i].code} и ${perMod[j].code}: «${x[0]}»`);
  }
  pageShingles[slug] = shingles(all);
}
// cross-sibling overlap
for (let i = 0; i < slugs.length; i++) for (let j = i + 1; j < slugs.length; j++) {
  const x = inter(pageShingles[slugs[i]], pageShingles[slugs[j]]);
  if (x.length > 2) E(`${slugs[i]}↔${slugs[j]}`, `${x.length} общих фрагментов ≥8 слов: ${x.slice(0, 3).map((s) => '«' + s + '»').join('; ')}${x.length > 3 ? ' …' : ''}`);
  else if (x.length) W(`${slugs[i]}↔${slugs[j]}`, `общий фрагмент: «${x[0]}»`);
}
// meta uniqueness
const mt = slugs.map((s) => fam.products[s].meta_title); if (new Set(mt).size !== mt.length) E('family', 'meta_title не уникальны');

for (const w of warns) console.log('WARN ', w);
for (const e of errors) console.log('ERROR', e);
console.log(`\n${slugs.length} позиций · ${errors.length} ошибок · ${warns.length} предупреждений`);
process.exit(errors.length ? 1 : 0);
