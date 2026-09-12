/**
 * Проверка вёрстки на узких экранах: страница не должна прокручиваться вбок.
 *
 * Зачем отдельная проверка. Горизонтальная прокрутка на телефоне выглядит не
 * как прокрутка, а как поломка: Safari отдаёт странице всю ширину документа,
 * и содержимое съезжает к левому краю с пустой полосой справа. Поймать это
 * можно только в браузере и только на узком экране — ни один из прежних
 * сторожей (тесты, смоук, проверки артефакта) ширину layout'а не измеряет.
 *
 * Что считается поломкой: documentElement.scrollWidth больше clientWidth
 * более чем на 1 px. Виновники ищутся обходом DOM — печатается путь до
 * элемента, его ширина и края.
 *
 * Чего проверка НЕ считает поломкой:
 *   - элементы за левым краем (ссылка «к содержимому» уезжает на -9999px);
 *   - position: fixed (шапка и модальные окна не расширяют документ);
 *   - содержимое внутри собственного горизонтального скроллера — таблица,
 *     лента фильтров и блок кода прокручиваются внутри себя сознательно
 *     (правило docs/rules/kpi-kit.md).
 *
 * Два режима:
 *   node scripts/ci/mobile-layout.mjs
 *       — поднимает стаб Directus и собранный сайт, как смоук, и меряет стенд;
 *   node scripts/ci/mobile-layout.mjs --base=https://biz-soft.pro
 *       — меряет живой сайт (так его запускает ops-mobile-layout).
 *
 * Список адресов берётся из карты сайта: статические страницы целиком плюс
 * несколько представителей каждого слоя (--per-group). Так проверка не
 * отстаёт от сайта — новый раздел попадает в неё сам.
 */
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { chromium } from 'playwright';

const args = Object.fromEntries(process.argv.slice(2)
  .filter((a) => a.startsWith('--'))
  .map((a) => {
    const [k, ...v] = a.slice(2).split('=');
    return [k, v.join('=') || 'true'];
  }));

const STUB_PORT = Number(args['stub-port'] || 8096);
const APP_PORT = Number(args['app-port'] || 4396);
/** Ширины: iPhone Pro Max, Pro, mini и самый узкий поддерживаемый экран. */
const WIDTHS = (args.widths || '440,393,375,320').split(',').map(Number);
const PER_GROUP = Number(args['per-group'] || 3);
const MAX_PAGES = Number(args['max-pages'] || 48);
const TOLERANCE = 1;

const procs = [];
function start(cmd, cmdArgs, env, label) {
  const p = spawn(cmd, cmdArgs, { env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
  p.stderr.on('data', (d) => process.env.LAYOUT_VERBOSE && console.error(`[${label}] ${d}`));
  procs.push(p);
  return p;
}
async function waitFor(url, tries = 80) {
  for (let i = 0; i < tries; i++) {
    try { const r = await fetch(url); if (r.ok) return true; } catch { /* ещё не поднялся */ }
    await sleep(250);
  }
  return false;
}

/**
 * Адреса для проверки: карта сайта, сгруппированная по первому сегменту.
 *
 * Целиком её обходить незачем — тысяча карточек товара сверстана одним
 * шаблоном. Но и одной страницы на слой мало: поломку часто даёт конкретное
 * содержимое (длинный артикул, широкая таблица), поэтому от каждого слоя
 * берётся несколько представителей.
 */
async function collectPaths(base) {
  if (args.paths) return args.paths.split(',').map((s) => s.trim()).filter(Boolean);
  let xml = '';
  try {
    const res = await fetch(`${base}/sitemap.xml`);
    if (res.ok) xml = await res.text();
  } catch { /* карта недоступна — ниже фолбэк */ }
  const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  const paths = locs.map((u) => { try { return new URL(u).pathname; } catch { return ''; } }).filter(Boolean);
  if (paths.length === 0) {
    return ['/', '/catalog', '/vendors', '/pricing', '/contacts', '/blog', '/faq'];
  }
  const groups = new Map();
  for (const p of paths) {
    const key = p === '/' ? '/' : `/${p.split('/')[1]}`;
    const list = groups.get(key) ?? [];
    // Корневые страницы раздела («/vendors») берутся всегда, вложенные — с лимитом.
    if (p === key || list.length < PER_GROUP) list.push(p);
    groups.set(key, list);
  }
  const picked = [...groups.values()].flat();
  // Корень и ключевые разделы — первыми, чтобы при обрезке остались они.
  picked.sort((a, b) => a.split('/').length - b.split('/').length || a.localeCompare(b));
  return [...new Set(picked)].slice(0, MAX_PAGES);
}

/** Замер одной страницы: ширина документа и виновники выхода за край. */
const MEASURE = () => {
  const doc = document.documentElement;
  const over = doc.scrollWidth - doc.clientWidth;
  const result = { over, clientWidth: doc.clientWidth, scrollWidth: doc.scrollWidth, offenders: [] };
  if (over <= 1) return result;

  const path = (el) => {
    const parts = [];
    for (let n = el; n && n.nodeType === 1 && parts.length < 4; n = n.parentElement) {
      const cls = String(n.className || '').trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
      parts.unshift(n.tagName.toLowerCase() + (cls ? `.${cls}` : ''));
    }
    return parts.join(' > ');
  };
  /** Внутри собственного горизонтального скроллера ширина — не поломка. */
  const inScroller = (el) => {
    for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
      const ox = getComputedStyle(n).overflowX;
      if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') return true;
    }
    return false;
  };

  const seen = new Set();
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.right <= doc.clientWidth + 1) continue;
    if (r.right <= 0) continue;
    if (getComputedStyle(el).position === 'fixed') continue;
    if (inScroller(el)) continue;
    const key = path(el);
    if (seen.has(key)) continue;
    seen.add(key);
    result.offenders.push({
      path: key,
      left: Math.round(r.left),
      right: Math.round(r.right),
      width: Math.round(r.width),
      text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 48),
    });
  }
  // Самый широкий виновник нагляднее первого попавшегося.
  result.offenders.sort((a, b) => b.right - a.right);
  result.offenders = result.offenders.slice(0, 5);
  return result;
};

async function main() {
  let base = args.base;
  if (!base) {
    start('node', ['scripts/ci/stub-directus.mjs', String(STUB_PORT)], {}, 'stub');
    if (!(await waitFor(`http://127.0.0.1:${STUB_PORT}/__stub/health`))) throw new Error('стаб Directus не поднялся');
    start('node', ['./dist/server/entry.mjs'], {
      HOST: '127.0.0.1', PORT: String(APP_PORT),
      DIRECTUS_URL: `http://127.0.0.1:${STUB_PORT}`, DIRECTUS_TOKEN: 'stub-token',
      SMTP_HOST: '', NODE_ENV: 'production',
    }, 'app');
    base = `http://127.0.0.1:${APP_PORT}`;
    if (!(await waitFor(`${base}/`))) throw new Error('приложение не поднялось');
  }
  base = base.replace(/\/$/, '');

  const paths = await collectPaths(base);
  console.log(`Проверка вёрстки: ${base}`);
  console.log(`Страниц: ${paths.length}, ширины: ${WIDTHS.join(', ')} px\n`);

  const browser = await chromium.launch(
    process.env.LAYOUT_CHROMIUM ? { executablePath: process.env.LAYOUT_CHROMIUM } : {},
  );
  const failures = [];
  let checked = 0;
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({
      viewport: { width, height: 900 },
      isMobile: true,
      hasTouch: true,
      deviceScaleFactor: 3,
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
        + '(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    });
    const page = await ctx.newPage();
    for (const path of paths) {
      let res = null;
      try {
        res = await page.goto(base + path, { waitUntil: 'domcontentloaded', timeout: 30000 });
      } catch (e) {
        console.log(`  ⚠️  ${width}px ${path} — не открылась: ${e.message.split('\n')[0]}`);
        continue;
      }
      if (!res || res.status() >= 400) {
        console.log(`  ⚠️  ${width}px ${path} — код ${res ? res.status() : 'нет ответа'}`);
        continue;
      }
      // Шрифты и ленивые картинки успевают доехать: без паузы замер видит
      // страницу до подстановки веб-шрифта и врёт в обе стороны.
      await page.waitForTimeout(400);
      const info = await page.evaluate(MEASURE);
      checked++;
      if (info.over > TOLERANCE) {
        failures.push({ width, path, ...info });
        console.log(`  ❌ ${width}px ${path} — вбок на ${info.over}px (документ ${info.scrollWidth}, экран ${info.clientWidth})`);
        for (const o of info.offenders) {
          console.log(`       ${o.path} — ширина ${o.width}px, край ${o.right}px${o.text ? ` · «${o.text}»` : ''}`);
        }
      }
    }
    await ctx.close();
  }
  await browser.close();

  console.log(`\nПроверено замеров: ${checked}. Страниц с прокруткой вбок: ${failures.length}.`);
  if (failures.length > 0) {
    const pages = [...new Set(failures.map((f) => f.path))];
    console.log(`Адреса: ${pages.join(', ')}`);
  }
  return failures.length === 0 ? 0 : 1;
}

let code = 1;
try {
  code = await main();
} catch (e) {
  console.error(`Проверка вёрстки не запустилась: ${e.message}`);
  code = 1;
} finally {
  for (const p of procs) p.kill('SIGKILL');
}
process.exit(code);
