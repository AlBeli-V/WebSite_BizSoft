/**
 * Сверка живой карточки товара с композицией, утверждённой 12.09.2026.
 *
 * Отчёт печатается текстом в лог прогона: артефакты прогона из сессии не
 * скачиваются (блоб-хранилище закрыто прокси), а разбирать расхождение по
 * HTML вслепую дороже, чем прочитать список блоков с их содержимым.
 *
 * Скрипт ничего не меняет: только читает публичные страницы.
 */
import { chromium } from 'playwright';
import { existsSync, readFileSync } from 'node:fs';

const SITE = (process.env.SITE || 'https://biz-soft.pro').replace(/\/$/, '');
let raw = process.env.PATHS || '';
if (!raw.trim() && process.env.PATHS_FILE && existsSync(process.env.PATHS_FILE)) {
  raw = readFileSync(process.env.PATHS_FILE, 'utf8');
}
const paths = raw.split(/[,\n]/).map((s) => s.trim()).filter((s) => s && !s.startsWith('#'));
if (paths.length === 0) throw new Error('список адресов пуст');

const browser = await chromium.launch(process.env.PLAYWRIGHT_EXEC ? { executablePath: process.env.PLAYWRIGHT_EXEC } : {});
for (const p of paths) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const res = await page.goto(`${SITE}${p}`, { waitUntil: 'networkidle', timeout: 60000 });
  // .reveal прячет секции ниже первого экрана до прокрутки — без неё отчёт
  // сказал бы «блока нет» там, где он есть.
  await page.evaluate(async () => {
    const step = window.innerHeight * 0.7;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 120));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(400);

  const a = await page.evaluate(() => {
    const t = (el) => (el?.textContent || '').replace(/\s+/g, ' ').trim();
    const all = (sel) => Array.from(document.querySelectorAll(sel));
    return {
      title: document.title,
      h1: t(document.querySelector('h1')),
      chips: all('.col-hero .chip').map(t),
      vendorline: t(document.querySelector('.vendorline')),
      subtitle: t(document.querySelector('.subtitle')),
      crumbs: all('.breadcrumbs li').map(t).join(' '),
      lede: t(document.querySelector('.lede')),
      facts: all('.hero-facts div').map((d) => `${t(d.querySelector('dt'))} = ${t(d.querySelector('dd'))}`),
      price: t(document.querySelector('.pz-sum b')),
      priceNotes: all('.pz-sum span').map(t),
      priceWhat: all('.pz-what li').map(t),
      qtyLabel: t(document.querySelector('.qty-label')),
      presets: all('.presets button').map(t),
      qtyValue: document.querySelector('[data-qty]')?.value ?? null,
      qtyMin: document.querySelector('[data-qty]')?.getAttribute('min') ?? null,
      totalLabel: t(document.querySelector('.bt-lbl')),
      total: t(document.querySelector('[data-total]')),
      rate: t(document.querySelector('.rate-note')),
      cta: t(document.querySelector('.buy-cta .btn-primary')),
      collLabel: t(document.querySelector('[data-coll-label]')),
      trust: all('.buy-trust li').map(t),
      headings: all('.col-rest h2').map(t),
      params: all('.prow').map((r) => `${t(r.querySelector('.k'))} ${t(r.querySelector('.v')) || '⟨ПУСТО⟩'}`),
      incl: all('.col-rest .incl li').map((li) => t(li).slice(0, 70)),
      dealGroups: all('.deal-row').map((r) => `${t(r.querySelector('.num'))} ${t(r.querySelector('h3'))} (${r.querySelectorAll('li').length})`),
      assist: t(document.querySelector('.assist h3')),
      faqCount: all('.faq-item').length,
      faqCols: getComputedStyle(document.querySelector('.faq-list') || document.body).gridTemplateColumns,
      tailCta: t(document.querySelector('main ~ section h2, .cta-section h2')) || t(all('h2').pop()),
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      composition: document.querySelector('.product-layout')?.dataset.composition ?? null,
    };
  });

  console.log(`\n================ ${p} (HTTP ${res?.status()}) ================`);
  console.log(`вид позиции: ${a.composition}   прокрутка вбок: ${a.overflow}px`);
  console.log(`крошки: ${a.crumbs || '⟨нет⟩'}`);
  console.log(`H1: ${a.h1}`);
  console.log(`маркеры: ${a.chips.join(' | ')}`);
  console.log(`производитель: ${a.vendorline}`);
  console.log(`подзаголовок: ${a.subtitle || '⟨нет⟩'}`);
  console.log(`описание: ${a.lede || '⟨нет⟩'}`);
  console.log(`факты: ${a.facts.join(' | ') || '⟨нет⟩'}`);
  console.log(`цена: ${a.price || '⟨нет⟩'}  подписи: ${a.priceNotes.join(' / ')}`);
  console.log(`за что: ${a.priceWhat.join(' | ') || '⟨нет⟩'}`);
  console.log(`количество: «${a.qtyLabel}» min=${a.qtyMin} value=${a.qtyValue} ступени: ${a.presets.join(',')}`);
  console.log(`итого: «${a.totalLabel}» ${a.total}   курс: ${a.rate || '⟨нет⟩'}`);
  console.log(`призыв: ${a.cta}`);
  console.log(`подборка: ${a.collLabel || '⟨нет⟩'}`);
  console.log(`доверие (${a.trust.length}): ${a.trust.join(' · ')}`);
  console.log(`разделы: ${a.headings.join(' → ')}`);
  console.log(`параметры (${a.params.length}):`);
  for (const r of a.params) console.log(`   ${r}`);
  console.log(`что входит (${a.incl.length}):`);
  for (const r of a.incl) console.log(`   ${r}`);
  console.log(`взаимодействие: ${a.dealGroups.join(' | ')}`);
  console.log(`помощь с выбором: ${a.assist || '⟨нет⟩'}`);
  console.log(`вопросы: ${a.faqCount}, колонки: ${a.faqCols}`);
  console.log(`хвостовой призыв: ${a.tailCta || '⟨нет⟩'}`);
  await page.close();
}
await browser.close();
