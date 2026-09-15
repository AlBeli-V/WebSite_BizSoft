#!/usr/bin/env node
/**
 * Шапка письма с коммерческим предложением — две картинки из одной сборки.
 *
 * Почему картинкой, а не вёрсткой: фирменный Raleway почтовые клиенты не
 * подгружают (Gmail и Outlook вырезают `@font-face`), а подложку с плитками
 * вендоров таблицами не собрать. Внутри картинки шрифт и композиция
 * одинаковы у всех получателей.
 *
 * Почему две, а не одна: на телефоне общая картинка ужимается вдвое, и
 * слоган лок-апа падает до 5 px, а заголовок — до 13 px. Поэтому под телефон
 * своя раскладка: текст на белом поле сверху, подложка полосой снизу.
 * Подменяются медиазапросом в письме (`quote-customer.ts`).
 *
 * Почему JPEG: прозрачности в баннере нет, а тот же кадр в PNG весит 692 и
 * 493 КБ против 116 и 97 КБ — письмо вышло бы за бюджет Gmail, и он обрезал
 * бы конец с подписью менеджера. Качество 92 без прореживания цвета: на
 * 4:2:0 оранжевый в знаке идёт лесенкой.
 *
 * Холст задан в почтовых пикселях (640 и 360), а рендер идёт вдвое крупнее —
 * так кегли считаются в тех величинах, в которых их увидит получатель, а на
 * экранах с двойной плотностью картинка не мылит.
 *
 * Здесь же собираются значки контактов подписи: в письме нельзя svg (Gmail
 * и Outlook его вырезают), а юникодные ✉ и ☎ каждый клиент рисует своим
 * шрифтом — от чёрного глифа до цветного эмодзи. Отрисованный png одинаков
 * у всех.
 *
 * Запуск: node scripts/brand/build-email-banner.mjs
 * Исходники: public/email/banner-bg.png, public/email/bizsoft-logo-lockup.png
 * Результат: public/email/banner-desk.jpg, public/email/banner-mob.jpg,
 *            public/email/g-mail.png, g-phone.png, g-tg.png, g-wa.png
 */
import { Resvg } from '@resvg/resvg-js';
import sharp from 'sharp';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const FONTS = [
  resolve(ROOT, 'public/brand/fonts/Raleway-Regular.ttf'),
  resolve(ROOT, 'public/brand/fonts/Raleway-Bold.ttf'),
];

/** Подложка: изометрические плитки вендоров, пустая левая часть под текст. */
export const BG = { file: 'public/email/banner-bg.png', w: 1844, h: 853 };
/** Лок-ап целиком: знак, BIZSoft, BUSINESS INTEGRATION ZONE и слоган. */
export const LOCKUP = { file: 'public/email/bizsoft-logo-lockup.png', w: 1962, h: 648 };

const ORANGE = '#FF763C';
const DEEP = '#16202C';
const MUTED = '#78828F';

const HEADLINE = 'ОТ ИДЕЙ К РЕЗУЛЬТАТАМ';
const LEAD_DESK = ['AI-сервисы, облачные решения', 'и лицензионное ПО для задач', 'любого масштаба.'];
const LEAD_MOB = ['AI-сервисы, облачные решения и лицензионное', 'ПО для задач любого масштаба.'];

const b64 = (rel) => readFileSync(resolve(ROOT, rel)).toString('base64');

function logo(x, y, w) {
  return `<image x="${x}" y="${y}" width="${w}" height="${w * (LOCKUP.h / LOCKUP.w)}"
    href="data:image/png;base64,${b64(LOCKUP.file)}"/>`;
}

/**
 * Подложка «по обрезке» в заданное окно — то же, что `object-fit: cover`.
 * Прижим к правому краю (`focusX = 1`) оставляет плитки целиком: обрезается
 * пустая левая часть, на которой всё равно лежит текст.
 */
function bgIn(x0, y0, w, h, id) {
  const k = Math.max(w / BG.w, h / BG.h);
  const dw = BG.w * k, dh = BG.h * k;
  return `<clipPath id="${id}"><rect x="${x0}" y="${y0}" width="${w}" height="${h}"/></clipPath>
  <g clip-path="url(#${id})"><image x="${x0 + w - dw}" y="${y0 + (h - dh) / 2}"
    width="${dw}" height="${dh}" href="data:image/png;base64,${b64(BG.file)}"/></g>`;
}

/** Растушёвки: текст ложится на чистое поле, стык с подложкой не читается. */
const DEFS = `<defs>
  <linearGradient id="fadeL" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#FFFFFF" stop-opacity=".97"/>
    <stop offset=".5" stop-color="#FFFFFF" stop-opacity=".9"/>
    <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>
  <linearGradient id="fadeT" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FFFFFF" stop-opacity=".96"/>
    <stop offset=".55" stop-color="#FFFFFF" stop-opacity=".7"/>
    <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>
</defs>`;

const lead = (x, y0, lines, step) => lines
  .map((t, i) => `<text x="${x}" y="${y0 + i * step}" font-family="Raleway" font-size="12"
    fill="${MUTED}">${t}</text>`).join('');

/** Компьютер: текст слева, плитки справа. */
export function desktopSvg() {
  const W = 640, H = 300, L = 30;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    ${DEFS}
    ${bgIn(0, 0, W, H, 'cutD')}
    <rect x="0" y="0" width="${W * 0.56}" height="${H}" fill="url(#fadeL)"/>
    ${logo(L, 28, 252)}
    <rect x="${L}" y="146" width="30" height="3" rx="1.5" fill="${ORANGE}"/>
    <text x="${L}" y="188" font-family="Raleway" font-weight="700" font-size="23" letter-spacing=".5"
          fill="${DEEP}">${HEADLINE}</text>
    ${lead(L, 222, LEAD_DESK, 18)}
  </svg>`;
}

/** Телефон: белое поле с текстом сверху, подложка полосой снизу. */
export function mobileSvg() {
  const W = 360, H = 440, L = 24, bandY = 186;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    ${DEFS}
    <rect width="${W}" height="${H}" fill="#FFFFFF"/>
    ${bgIn(0, bandY, W, H - bandY, 'cutM')}
    <rect x="0" y="${bandY}" width="${W}" height="64" fill="url(#fadeT)"/>
    ${logo(L, 26, 236)}
    <rect x="${L}" y="120" width="30" height="3" rx="1.5" fill="${ORANGE}"/>
    <text x="${L}" y="158" font-family="Raleway" font-weight="700" font-size="21" letter-spacing=".4"
          fill="${DEEP}">${HEADLINE}</text>
    ${lead(L, 186, LEAD_MOB, 18)}
  </svg>`;
}

/**
 * Значки контактов: тонкая линия в цвет подписи, без подложки и кружка.
 * Рендер в 2× от экранных 17 px.
 */
export const GLYPHS = {
  'g-mail': ['<rect x="3" y="8" width="30" height="21" rx="3"/><path d="M4 10 18 21 32 10"/>', 2.4],
  'g-phone': ['<path d="M12.2 5.6 15.8 9.4a2 2 0 0 1 .1 2.7l-1.6 1.9a1.6 1.6 0 0 0-.1 1.8 17.5 17.5 0 0 0 6.5 6.5c.6.3 1.3.3 1.8-.1l1.9-1.6a2 2 0 0 1 2.7.1l3.8 3.6a2 2 0 0 1 0 2.9l-1.5 1.5c-1.5 1.5-3.8 1.9-5.7 1A32 32 0 0 1 7.5 13.7c-.9-1.9-.5-4.2 1-5.7l1.5-1.5a2 2 0 0 1 2.2-.9z"/>', 2.4],
  'g-tg': ['<path d="M3.8 17.2 32 6.2l-4.6 23.6-9.2-6.6-4.2 4.5-.6-7.6z"/><path d="M14 20.1 27.6 9.4"/>', 2.4],
  'g-wa': ['<path d="M18 4.5a13.5 13.5 0 0 0-11.7 20.2L4.7 31.3l6.8-1.5A13.5 13.5 0 1 0 18 4.5z"/><path d="M13.4 12.8c.4-.8 1-.9 1.5-.9.5 0 .9.2 1.2.8l.9 1.9c.2.5.1.9-.2 1.2l-.7.8c-.2.3-.3.6-.1.9a7.6 7.6 0 0 0 3.4 3.4c.3.2.6.1.9-.1l.8-.7c.3-.3.7-.4 1.2-.2l1.9.9c.6.3.8.7.8 1.2 0 .5-.1 1.1-.9 1.5-1 .5-2.5.6-4.1-.1a12.4 12.4 0 0 1-6.6-6.6c-.7-1.6-.5-3.1-.1-4z"/>', 2],
};

export function glyphSvg(path, strokeWidth) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="34" height="34" viewBox="0 0 36 36">
    <g fill="none" stroke="${MUTED}" stroke-width="${strokeWidth}" stroke-linecap="round"
       stroke-linejoin="round">${path}</g></svg>`;
}

export async function render(svg, width) {
  const png = new Resvg(svg, {
    fitTo: { mode: 'width', value: width },
    font: { fontFiles: FONTS, loadSystemFonts: false, defaultFontFamily: 'Raleway' },
  }).render().asPng();
  return sharp(png).flatten({ background: '#ffffff' })
    .jpeg({ quality: 92, chromaSubsampling: '4:4:4', mozjpeg: true }).toBuffer();
}

if (import.meta.url === `file://${process.argv[1]}`) {
  for (const [svg, width, out] of [
    [desktopSvg(), 1280, 'public/email/banner-desk.jpg'],
    [mobileSvg(), 720, 'public/email/banner-mob.jpg'],
  ]) {
    const buf = await render(svg, width);
    writeFileSync(resolve(ROOT, out), buf);
    console.log(`${out} — ${Math.round(buf.length / 1024)} КБ`);
  }
  // Значки остаются png с прозрачностью: они ложатся на белое поле подписи,
  // и залитый фон выдал бы прямоугольник.
  for (const [name, [path, sw]] of Object.entries(GLYPHS)) {
    const png = new Resvg(glyphSvg(path, sw), { fitTo: { mode: 'width', value: 34 } }).render().asPng();
    writeFileSync(resolve(ROOT, `public/email/${name}.png`), png);
    console.log(`public/email/${name}.png — ${png.length} Б`);
  }
}
