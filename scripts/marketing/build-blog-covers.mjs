#!/usr/bin/env node
/**
 * Генератор обложек статей блога.
 *
 * Одна дизайн-система на все статьи: светлый песочный фон, белые карточки с
 * иконками вокруг центрального объекта, оранжевые связи, рамка-уголок слева и
 * логотип внизу — как на эталонной обложке, утверждённой руководителем.
 * Отличается только иконография: она собирается из темы конкретной статьи.
 *
 * Почему генерация, а не готовые файлы: обложек девять, они должны быть
 * единообразны, а при смене фирменного цвета — перерисованы одной командой.
 *
 * Запуск: node scripts/marketing/build-blog-covers.mjs [slug ...]
 * Без аргументов рисует все. Результат — public/blog/covers/<slug>.png.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Resvg } from '@resvg/resvg-js';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const OUT_DIR = resolve(ROOT, 'public/blog/covers');
const W = 1664;
const H = 936;

/** Фирменные цвета — из src/styles/global.css, чтобы обложки не разъезжались с сайтом. */
const C = {
  accent: '#f2591d',
  accentSoft: '#fff2ec',
  ink: '#1d1d1f',
  inkSoft: '#3f3f46',
  card: '#ffffff',
  bgFrom: '#fbf8f5',
  bgTo: '#f1e7de',
};

/**
 * Иконки — пути в системе координат 24×24 (как у большинства icon-set).
 * Рисуются обводкой: одна толщина, одинаковые скругления, узнаваемый силуэт.
 */
const ICONS = {
  card: 'M2 7h20v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7zm0 3h20M5 15h4',
  doc: 'M6 2h8l4 4v16H6V2zm8 0v4h4M9 12h6M9 16h6',
  stamp: 'M12 3a3 3 0 0 1 3 3c0 2-2 3-2 5h-2c0-2-2-3-2-5a3 3 0 0 1 3-3zM5 16h14v4H5z',
  shield: 'M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5l8-3zM9 12l2 2 4-4',
  lock: 'M6 10h12v10H6V10zm3 0V7a3 3 0 0 1 6 0v3M12 14v2',
  brain: 'M7 7h10v10H7V7zm3 3h4v4h-4v-4zM10 4v3M14 4v3M10 17v3M14 17v3M4 10h3M4 14h3M17 10h3M17 14h3',
  code: 'M8 6l-5 6 5 6M16 6l5 6-5 6M14 4l-4 16',
  users: 'M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm8 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM2 20c0-3 2.5-5 6-5s6 2 6 5M15 15c3 0 7 1.5 7 5',
  cloud: 'M7 18a4 4 0 0 1 0-8 5 5 0 0 1 9.6-1.4A4 4 0 0 1 18 18H7z',
  ruble: 'M9 20V4h4a4 4 0 0 1 0 8H9m-2 4h8',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm0 4v5l3 2',
  chart: 'M4 20V10m5 10V4m5 16v-7m5 7V8',
  folder: 'M3 6h6l2 3h10v11H3V6z',
  refresh: 'M20 8a8 8 0 1 0 1 6M20 3v6h-6',
  image: 'M3 5h18v14H3V5zm3 10l4-4 3 3 3-3 5 5',
  route: 'M6 20a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm12-10a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 14V9a4 4 0 0 1 4-4h5M18 10v5a4 4 0 0 1-4 4H9',
  scale: 'M12 3v18M5 7h14M7 7l-3 6h6l-3-6zm10 0l-3 6h6l-3-6z',
  warn: 'M12 4l9 16H3l9-16zm0 6v4m0 3v.5',
};

/** Обложки: центральный объект и иконки-спутники по смыслу статьи. */
const COVERS = {
  'stoimost-vladeniya-podpiskoy': {
    hero: 'card',
    icons: ['cloud', 'brain', 'folder', 'refresh', 'lock', 'users', 'chart', 'warn'],
    alt: 'Банковская карта в центре схемы из иконок сервисов, часть связей прерывается предупреждающими знаками',
  },
  'kak-kupit-zarubezhnoe-po-dlya-yurlica': {
    hero: 'doc',
    icons: ['stamp', 'ruble', 'cloud', 'folder', 'clock', 'users'],
    alt: 'Договор в центре схемы: печать, оплата в рублях, доступ к сервисам и документы',
  },
  'zakryvayushchie-dokumenty-na-po': {
    hero: 'folder',
    icons: ['doc', 'stamp', 'ruble', 'refresh', 'clock', 'chart'],
    alt: 'Комплект закрывающих документов: договор, счёт, УПД и обмен через электронный документооборот',
  },
  'bezopasnost-dannyh-v-korporativnyh-ai': {
    hero: 'shield',
    icons: ['brain', 'lock', 'cloud', 'users', 'folder', 'warn'],
    alt: 'Щит в центре схемы из иконок AI-сервисов, доступов и хранения данных',
  },
  'kak-vybrat-ai-assistenta-dlya-komandy-razrabotki': {
    hero: 'code',
    icons: ['brain', 'users', 'cloud', 'lock', 'refresh', 'chart'],
    alt: 'Символ кода в центре схемы: AI-ассистент, команда разработки, доступы и интеграции',
  },
  'enterprise-vs-team-korporativnye-tarify-ai': {
    hero: 'users',
    icons: ['lock', 'brain', 'chart', 'folder', 'shield', 'refresh'],
    alt: 'Схема корпоративных тарифов: места в команде, единый вход, аудит и управление доступом',
  },
  'kak-oformit-korporativnuyu-ai-podpisku-na-yurlico': {
    hero: 'brain',
    icons: ['doc', 'ruble', 'stamp', 'users', 'lock', 'clock'],
    alt: 'AI-сервис в центре схемы оформления подписки на юридическое лицо: договор, счёт, доступы',
  },
  'kak-oplatit-depositphotos-dlya-yurlica': {
    hero: 'image',
    icons: ['ruble', 'doc', 'folder', 'cloud', 'stamp', 'clock'],
    alt: 'Сток-изображения в центре схемы оплаты подписки для юридического лица',
  },
  'kak-kupit-perplexity-dlya-yurlica': {
    hero: 'brain',
    icons: ['doc', 'folder', 'lock', 'users', 'ruble', 'stamp'],
    alt: 'AI-поиск в центре схемы: источники ответов, внутренние файлы компании, единый вход и оплата по счёту',
  },
  'kak-oplatit-framer-dlya-yurlica': {
    hero: 'cloud',
    icons: ['code', 'image', 'folder', 'users', 'ruble', 'chart'],
    alt: 'Сайт на хостинге в центре схемы: визуальный редактор, CMS-коллекции, команда редакторов и оплата подписки',
  },
  'kak-kupit-github-copilot-dlya-yurlica': {
    hero: 'code',
    icons: ['brain', 'users', 'shield', 'lock', 'doc', 'ruble'],
    alt: 'Код в центре схемы: AI-помощник разработчика, команда, политики организации и оформление на юрлицо',
  },
  'tarify-runway-oplata-dlya-yurlica': {
    hero: 'image',
    icons: ['brain', 'cloud', 'chart', 'ruble', 'users', 'clock'],
    alt: 'Кадр видео в центре схемы: генеративные модели, кредиты, рабочие места и оплата тарифа',
  },
  'kak-oplatit-envato-elements-dlya-yurlica': {
    hero: 'folder',
    icons: ['image', 'brain', 'ruble', 'users', 'doc', 'clock'],
    alt: 'Библиотека ассетов в центре схемы: изображения и шаблоны, места в команде, лицензия и оплата по счёту',
  },
  'kak-oplatit-postman-dlya-yurlica': {
    hero: 'cloud',
    icons: ['code', 'refresh', 'users', 'lock', 'doc', 'chart'],
    alt: 'API в центре схемы: коллекции запросов, тесты по расписанию, роли участников и оформление подписки',
  },
  'podpiska-napryamuyu-ili-cherez-postavshchika': {
    hero: 'route',
    icons: ['card', 'doc', 'ruble', 'warn', 'stamp', 'scale'],
    alt: 'Развилка двух путей покупки подписки: напрямую и через российского поставщика',
  },
  // Партия CONTENT-003: вторая волна тиража приёма на десять кластеров.
  'kak-kupit-windsurf-iz-rossii-dlya-yurlica': {
    hero: 'code',
    icons: ['brain', 'users', 'lock', 'chart', 'doc', 'ruble'],
    alt: 'Код в центре схемы: AI-агент в редакторе, рабочие места команды, политика хранения данных и оплата подписки по счёту',
  },
  'gitlab-godovaya-podpiska-iz-rossii-dlya-yurlica': {
    hero: 'folder',
    icons: ['code', 'refresh', 'users', 'clock', 'doc', 'ruble'],
    alt: 'Репозиторий в центре схемы: конвейер CI/CD, ревью кода, места команды, годовой срок и оплата по счёту',
  },
  'oplata-descript-yuridicheskim-licom': {
    hero: 'image',
    icons: ['doc', 'brain', 'users', 'clock', 'ruble', 'stamp'],
    alt: 'Видеодорожка в центре схемы: расшифровка в текст, ИИ-инструменты, команда монтажёров и оформление подписки по счёту',
  },
  'kak-poluchit-schet-i-zakryvayushchie-ot-atlassian': {
    hero: 'chart',
    icons: ['folder', 'users', 'doc', 'ruble', 'stamp', 'card'],
    alt: 'Доска задач в центре схемы: база знаний, места команды, договор и счёт, закрывающие документы через ЭДО',
  },
  'kak-oplatit-box-business-iz-rossii': {
    hero: 'folder',
    icons: ['lock', 'doc', 'users', 'shield', 'ruble', 'stamp'],
    alt: 'Папка с документами в центре схемы: права доступа, журнал действий, внешние участники и оплата подписки по счёту',
  },
  'korporativnye-plany-cloudflare-dlya-kompanij-iz-rf': {
    hero: 'shield',
    icons: ['cloud', 'lock', 'chart', 'route', 'ruble', 'doc'],
    alt: 'Щит в центре схемы: защита сайта от атак, сеть доставки контента, сертификат, домены компании и оплата тарифа по счёту',
  },
  'oplata-dropbox-dlya-yurlica-iz-rossii': {
    hero: 'cloud',
    icons: ['folder', 'users', 'refresh', 'lock', 'ruble', 'doc'],
    alt: 'Облачное хранилище в центре схемы: общие папки команды, восстановление версий, передача больших файлов и оплата подписки по счёту',
  },
  'kupit-leonardo-ai-yuridicheskim-licom': {
    hero: 'image',
    icons: ['brain', 'chart', 'code', 'users', 'ruble', 'doc'],
    alt: 'Сгенерированное изображение в центре схемы: собственная модель, запас токенов, конвейер через API и оплата подписки по счёту',
  },
  'spine-2d-kupit-licenziyu-dlya-yurlica': {
    hero: 'route',
    icons: ['stamp', 'users', 'code', 'image', 'ruble', 'doc'],
    alt: 'Скелет анимированного персонажа в центре схемы: бессрочная лицензия, рабочие места аниматоров, экспорт в игровой движок и оплата по счёту',
  },
  'elevenlabs-tarify-oplata-dlya-yurlica': {
    hero: 'chart',
    icons: ['brain', 'users', 'code', 'clock', 'ruble', 'doc'],
    alt: 'Звуковая волна в центре схемы: клонирование голоса, кредиты на синтез, интеграция через API и оплата подписки по счёту',
  },
};

const logo = readFileSync(resolve(ROOT, 'public/brand/bizsoft-logo-primary-transparent.png'))
  .toString('base64');

/** Белая карточка со скруглением, мягкой тенью и иконкой внутри. */
function iconCard(x, y, size, icon, accent) {
  const s = size / 24 * 0.52;
  const pad = size * 0.24;
  return `
  <g>
    <rect x="${x}" y="${y}" width="${size}" height="${size}" rx="${size * 0.26}"
          fill="${C.card}" filter="url(#soft)"/>
    <g transform="translate(${x + pad} ${y + pad}) scale(${s})"
       fill="none" stroke="${accent ? C.accent : C.ink}" stroke-width="1.7"
       stroke-linecap="round" stroke-linejoin="round">
      <path d="${ICONS[icon]}"/>
    </g>
  </g>`;
}

function buildSvg({ hero, icons }) {
  const cx = W * 0.46;
  const cy = H * 0.5;
  const R = 300;
  const card = 118;

  // Спутники по окружности: начинаем сверху и идём по кругу, пропуская сектор
  // справа снизу — там в композиции воздух.
  const nodes = icons.map((icon, i) => {
    const a = (-Math.PI / 2) + (i / icons.length) * Math.PI * 2;
    return {
      icon,
      x: cx + Math.cos(a) * R * 1.32 - card / 2,
      y: cy + Math.sin(a) * R * 0.92 - card / 2,
      cxp: cx + Math.cos(a) * R * 1.32,
      cyp: cy + Math.sin(a) * R * 0.92,
      accent: i % 3 === 0,
    };
  });

  const links = nodes.map((n, i) => `
    <line x1="${cx}" y1="${cy}" x2="${n.cxp}" y2="${n.cyp}"
          stroke="${C.accent}" stroke-width="${i % 3 === 0 ? 2 : 1.4}"
          stroke-opacity="${i % 3 === 0 ? 0.5 : 0.28}"
          ${i % 4 === 3 ? 'stroke-dasharray="7 9"' : ''}/>`).join('');

  const dots = Array.from({ length: 36 }, (_, i) => {
    const col = i % 6, row = Math.floor(i / 6);
    return `<circle cx="${248 + col * 17}" cy="${330 + row * 17}" r="2.4"
             fill="${C.accent}" fill-opacity="0.22"/>`;
  }).join('');

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="${C.bgFrom}"/>
      <stop offset="1" stop-color="${C.bgTo}"/>
    </linearGradient>
    <radialGradient id="glow" cx="46%" cy="50%" r="42%">
      <stop offset="0" stop-color="${C.accent}" stop-opacity="0.16"/>
      <stop offset="1" stop-color="${C.accent}" stop-opacity="0"/>
    </radialGradient>
    <filter id="soft" x="-40%" y="-40%" width="180%" height="180%">
      <feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#7a5240" flood-opacity="0.13"/>
    </filter>
    <filter id="heroShadow" x="-40%" y="-40%" width="180%" height="180%">
      <feDropShadow dx="0" dy="16" stdDeviation="22" flood-color="#5a3a2a" flood-opacity="0.2"/>
    </filter>
  </defs>

  <rect width="${W}" height="${H}" fill="url(#bg)"/>
  <rect width="${W}" height="${H}" fill="url(#glow)"/>

  <!-- Рамка-уголок слева: тонкая линия, уходящая вниз от верхнего угла -->
  <path d="M92 30 H40 a10 10 0 0 0-10 10 V${H - 40}"
        fill="none" stroke="${C.accent}" stroke-width="2.4" stroke-opacity="0.75"/>

  ${dots}

  <!-- Концентрические круги вокруг центра -->
  <circle cx="${cx}" cy="${cy}" r="${R * 0.78}" fill="none" stroke="${C.accent}" stroke-opacity="0.12" stroke-width="1.5"/>
  <circle cx="${cx}" cy="${cy}" r="${R * 1.06}" fill="none" stroke="${C.accent}" stroke-opacity="0.08" stroke-width="1.5"/>

  ${links}

  <!-- Центральный объект -->
  <g filter="url(#heroShadow)">
    <rect x="${cx - 190}" y="${cy - 128}" width="380" height="256" rx="30" fill="${C.ink}"/>
    <rect x="${cx - 190}" y="${cy - 128}" width="380" height="256" rx="30" fill="none"
          stroke="${C.accent}" stroke-opacity="0.5" stroke-width="2"/>
    <g transform="translate(${cx - 62} ${cy - 62}) scale(5.2)" fill="none" stroke="${C.accentSoft}"
       stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="${ICONS[hero]}"/>
    </g>
  </g>

  ${nodes.map((n) => iconCard(n.x, n.y, card, n.icon, n.accent)).join('')}

  <!-- Логотип -->
  <image href="data:image/png;base64,${logo}" x="86" y="${H - 132}" width="248" height="76"
         preserveAspectRatio="xMinYMid meet"/>
</svg>`;
}

const want = process.argv.slice(2);
const list = want.length ? want : Object.keys(COVERS);
mkdirSync(OUT_DIR, { recursive: true });

for (const slug of list) {
  const cfg = COVERS[slug];
  if (!cfg) { console.error(`нет конфигурации обложки: ${slug}`); process.exitCode = 1; continue; }
  const svg = buildSvg(cfg);
  const png = new Resvg(svg, { fitTo: { mode: 'width', value: W } }).render().asPng();
  const out = resolve(OUT_DIR, `${slug}.png`);
  writeFileSync(out, png);
  console.log(`${slug}.png — ${(png.length / 1024).toFixed(0)} КБ`);
}
