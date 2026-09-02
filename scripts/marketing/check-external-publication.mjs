#!/usr/bin/env node
/**
 * Проверка внешней публикации: как её видит посетитель и поисковый робот.
 *
 * Зачем на раннере, а не из сессии: у сессии ассистента нет доступа к
 * площадкам (dzen.ru, vc.ru и прочие закрыты egress-политикой), а страницы
 * рисует JavaScript — статический curl отдаёт пустой каркас.
 *
 * Что снимает:
 *  - заголовок, описание и canonical — то, что увидит поиск;
 *  - meta robots: индексируется ли материал вообще;
 *  - все ссылки на biz-soft.pro с атрибутом rel — передают ли они вес или
 *    закрыты nofollow (для ссылочного профиля это решающий факт);
 *  - объём видимого текста — доехал ли материал целиком;
 *  - число заголовков — собралось ли оглавление.
 *
 * Запуск: URL=https://... node scripts/marketing/check-external-publication.mjs
 */
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const URL_TO_CHECK = process.env.URL;
if (!URL_TO_CHECK) {
  console.error('Не задан URL');
  process.exit(2);
}

const browser = await chromium.launch();
const page = await browser.newPage({
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    + '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
});

const report = { url: URL_TO_CHECK, checkedAt: new Date().toISOString() };

try {
  const resp = await page.goto(URL_TO_CHECK, { waitUntil: 'domcontentloaded', timeout: 60000 });
  report.httpStatus = resp?.status() ?? null;
  // Лента подгружает текст по мере прокрутки — иначе снимем только первый экран.
  for (let i = 0; i < 6; i++) {
    await page.mouse.wheel(0, 2500);
    await page.waitForTimeout(700);
  }

  Object.assign(report, await page.evaluate(() => {
    const meta = (sel, attr = 'content') => document.querySelector(sel)?.getAttribute(attr) || null;
    const links = [...document.querySelectorAll('a[href]')]
      .map((a) => ({ href: a.href, text: (a.textContent || '').trim().slice(0, 80), rel: a.rel || '' }))
      .filter((l) => l.href.includes('biz-soft.pro'));
    return {
      title: document.title || null,
      h1: document.querySelector('h1')?.textContent?.trim() || null,
      description: meta('meta[name="description"]'),
      ogTitle: meta('meta[property="og:title"]'),
      ogImage: meta('meta[property="og:image"]'),
      robots: meta('meta[name="robots"]'),
      canonical: meta('link[rel="canonical"]', 'href'),
      textLength: (document.body.innerText || '').length,
      headings: document.querySelectorAll('article h2, article h3').length,
      ownLinks: links,
    };
  }));
} catch (e) {
  report.error = String(e).slice(0, 500);
} finally {
  await browser.close();
}

writeFileSync('external-check.json', JSON.stringify(report, null, 2));

const L = [];
L.push(`## Проверка публикации`);
L.push('');
L.push(`URL: ${report.url}`);
L.push(`HTTP: ${report.httpStatus ?? '—'} · снято ${report.checkedAt}`);
if (report.error) L.push(`\n**Ошибка:** ${report.error}`);
L.push('');
L.push('| Параметр | Значение |');
L.push('|---|---|');
L.push(`| Заголовок страницы | ${report.title || '—'} |`);
L.push(`| H1 в материале | ${report.h1 || '—'} |`);
L.push(`| Описание | ${(report.description || '—').slice(0, 160)} |`);
L.push(`| meta robots | ${report.robots || 'не задан (индексируется)'} |`);
L.push(`| canonical | ${report.canonical || '—'} |`);
L.push(`| og:image | ${report.ogImage ? 'есть' : 'нет'} |`);
L.push(`| Видимого текста | ${report.textLength ?? '—'} знаков |`);
L.push(`| Заголовков в статье | ${report.headings ?? '—'} |`);
L.push('');

const own = report.ownLinks || [];
L.push(`### Ссылки на biz-soft.pro: ${own.length}`);
L.push('');
if (own.length) {
  L.push('| Адрес | Анкор | rel |');
  L.push('|---|---|---|');
  for (const l of own) {
    L.push(`| ${l.href} | ${l.text || '—'} | ${l.rel || '(пусто — ссылка открытая)'} |`);
  }
  const nofollow = own.filter((l) => /nofollow/i.test(l.rel)).length;
  L.push('');
  L.push(nofollow === own.length && own.length > 0
    ? '**Все ссылки закрыты nofollow** — вес не передаётся, ценность только в переходах и упоминании бренда.'
    : nofollow > 0
      ? `**Часть ссылок (${nofollow} из ${own.length}) закрыта nofollow.**`
      : '**Ссылки открыты** — атрибута nofollow нет.');
} else {
  L.push('Ссылок на biz-soft.pro в разметке не найдено. Возможные причины: они '
    + 'подгружаются скриптом, отданы редиректом площадки или не сохранились при вставке.');
}

writeFileSync('external-check.md', L.join('\n'));
console.log(L.join('\n'));
