/**
 * Фирменный каркас HTML-писем BIZSoft.
 *
 * Правила вёрстки почты (Outlook, Gmail, Яндекс, мобильные клиенты):
 * - только таблицы и inline-CSS, никаких внешних стилей и скриптов;
 * - никаких внешних картинок: «логотип» набран текстом — письмо выглядит
 *   фирменным и с выключенной загрузкой изображений;
 * - ширина 600px, на узких экранах таблица сжимается сама.
 *
 * Каждое письмо обязано отправляться с text-fallback: html и text — два
 * представления одного содержимого, собираются рядом в одном шаблоне.
 */
import { seller, site } from '../../config/site';
import type { AttributionFields } from '../quote-lead';
import { explainSource, ruDay, type SourceEnrichment, type SourceStep } from '../traffic-source';

/** Экранирование пользовательских данных в HTML-письме. */
export function escapeHtml(v: string): string {
  return v.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export const EMAIL_COLOR = {
  accent: '#FF763C',
  dark: '#14161A',
  body: '#374151',
  muted: '#6B7280',
  rule: '#E5E7EB',
  bg: '#F4F5F7',
  card: '#FFFFFF',
  noteBg: '#FFF4EF',
  ok: '#166534',
  warn: '#B42318',
  /** Бордовый — критические предупреждения в тексте письма (решение 28.08). */
  maroon: '#7E1428',
} as const;

// Брендовый шрифт сайта — Raleway. Почтовые клиенты с поддержкой @font-face
// (Apple Mail, iOS, часть остальных) возьмут его из блока в emailShell;
// Gmail и Outlook веб-шрифты не грузят и упадут на системный из стека.
const F = "font-family:'Raleway','Segoe UI',Roboto,Helvetica,Arial,sans-serif;";

/**
 * @font-face на файлы с нашего домена (public/fonts/). Это не «внешний
 * ресурс» в смысле трекинга: без него письмо полностью читаемо, клиенты без
 * поддержки просто не сделают запрос.
 */
const FONT_FACES = ['400', '700'].map((w) =>
  ['cyrillic', 'latin'].map((subset) =>
    `@font-face{font-family:'Raleway';font-style:normal;font-weight:${w};`
    + `src:url(${site.url}/fonts/raleway-${subset}-${w}-normal.woff2) format('woff2');`
    + `font-display:swap;}`).join('')).join('');

/** Строка «ключ — значение» для карточки-таблицы. */
export function kvRow(key: string, value: string, bold = false): string {
  return `<tr>`
    + `<td style="${F}font-size:13px;color:${EMAIL_COLOR.muted};padding:6px 12px 6px 0;white-space:nowrap;">${key}</td>`
    + `<td style="${F}font-size:13px;color:${EMAIL_COLOR.dark};padding:6px 0;${bold ? 'font-weight:bold;' : ''}">${value}</td>`
    + `</tr>`;
}

/** Обёртка карточки с рамкой. */
export function card(innerHtml: string): string {
  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" `
    + `style="border:1px solid ${EMAIL_COLOR.rule};border-radius:8px;margin:14px 0;">`
    + `<tr><td style="padding:14px 18px;">${innerHtml}</td></tr></table>`;
}

/** Акцентная плашка (оговорка, предупреждение). */
export function note(html: string, tone: 'accent' | 'warn' = 'accent'): string {
  const border = tone === 'warn' ? EMAIL_COLOR.warn : EMAIL_COLOR.accent;
  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:14px 0;">`
    + `<tr><td style="${F}font-size:13px;line-height:1.5;color:${EMAIL_COLOR.dark};`
    + `background:${EMAIL_COLOR.noteBg};border-left:3px solid ${border};padding:12px 16px;">${html}</td></tr>`
    + `</table>`;
}

export function paragraph(html: string, opts: { muted?: boolean; small?: boolean } = {}): string {
  return `<p style="${F}font-size:${opts.small ? 12 : 14}px;line-height:1.55;margin:0 0 12px;`
    + `color:${opts.muted ? EMAIL_COLOR.muted : EMAIL_COLOR.body};">${html}</p>`;
}

export function heading(text: string): string {
  return `<h1 style="${F}font-size:20px;line-height:1.3;margin:0 0 14px;color:${EMAIL_COLOR.dark};">${text}</h1>`;
}

/**
 * Полное письмо: шапка с маркой, тело, подвал с контактами.
 * preheader — первая строка в списке писем почтовика, невидимая в теле.
 */
export function emailShell(bodyHtml: string, preheader = ''): string {
  return `<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">`
    + `<meta name="viewport" content="width=device-width,initial-scale=1">`
    + `<style>${FONT_FACES}</style></head>`
    + `<body style="margin:0;padding:0;background:${EMAIL_COLOR.bg};">`
    + (preheader
      ? `<div style="display:none;max-height:0;overflow:hidden;">${escapeHtml(preheader)}</div>`
      : '')
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${EMAIL_COLOR.bg};">`
    + `<tr><td align="center" style="padding:24px 12px;">`
    + `<table role="presentation" width="600" cellpadding="0" cellspacing="0" `
    + `style="max-width:600px;width:100%;background:${EMAIL_COLOR.card};border-radius:10px;overflow:hidden;">`
    // Шапка: марка текстом, без картинок.
    + `<tr><td style="padding:20px 28px;border-bottom:3px solid ${EMAIL_COLOR.accent};">`
    + `<span style="${F}font-size:24px;font-weight:bold;color:${EMAIL_COLOR.dark};">BIZ`
    + `<span style="color:${EMAIL_COLOR.accent};">Soft</span></span>`
    + `<div style="${F}font-size:11px;color:${EMAIL_COLOR.muted};margin-top:2px;">${site.tagline}</div>`
    + `</td></tr>`
    + `<tr><td style="padding:24px 28px;">${bodyHtml}</td></tr>`
    // Подвал.
    + `<tr><td style="padding:16px 28px;border-top:1px solid ${EMAIL_COLOR.rule};">`
    + `<div style="${F}font-size:11px;line-height:1.6;color:${EMAIL_COLOR.muted};">`
    + `${seller.shortName} · ${seller.phone} · <a href="${site.url}" style="color:${EMAIL_COLOR.accent};text-decoration:none;">${site.domain}</a><br>`
    + `${seller.legalName} · ИНН ${seller.inn} · ОГРНИП ${seller.ogrnip}`
    + `</div></td></tr>`
    + `</table></td></tr></table></body></html>`;
}

/** Один шаг пути посетителя строкой. */
function stepLine(s: SourceStep): string {
  const head = [ruDay(s.when), s.source, s.engine, s.phrase ? `«${s.phrase}»` : '']
    .filter(Boolean).join(' · ');
  const tail = s.visits && s.visits > 1 ? ` (визитов: ${s.visits})` : '';
  return s.page ? `${head} → ${s.page}${tail}` : `${head}${tail}`;
}

const rubShort = (n: number) => `${n.toLocaleString('ru-RU', { maximumFractionDigits: 2 })} ₽`;

/**
 * Строки источника перехода — общий вид для писем о заявке и о КП.
 *
 * Первой строкой стоит вердикт «органика / реклама / внешняя площадка», а не
 * сырая метка канала: письмо должно отвечать на вопрос руководителя сразу, не
 * заставляя его расшифровывать «yandex.ru / referral». Второй строкой —
 * чем вердикт подтверждается, чтобы разбор можно было проверить.
 */
export function attributionRows(a: AttributionFields, enrichment?: SourceEnrichment | null): string {
  const v = explainSource(a, enrichment);
  const rows: string[] = [
    kvRow('Тип трафика', `${escapeHtml(v.kindLabel)}${
      v.system ? ` · ${escapeHtml(v.system)}` : ''}`, true),
  ];
  if (v.evidence) {
    rows.push(kvRow('Как определено',
      `<span style="color:${EMAIL_COLOR.muted};">${escapeHtml(v.evidence)}</span>`));
  }
  // Сырая метка канала остаётся в письме мелким шрифтом: по ней заявка
  // сходится с витриной аналитики, где канал хранится именно в этом виде.
  if (a.last_touch_source) {
    rows.push(kvRow('Метка канала',
      `<span style="color:${EMAIL_COLOR.muted};">${escapeHtml(a.last_touch_source)}</span>`));
  }
  if (v.query) {
    rows.push(kvRow('Запрос', `<b>${escapeHtml(v.query)}</b>${
      v.queryNote ? ` <span style="color:${EMAIL_COLOR.muted};">· ${escapeHtml(v.queryNote)}</span>` : ''}`));
  } else if (v.queryNote) {
    rows.push(kvRow('Запрос',
      `<span style="color:${EMAIL_COLOR.muted};">${escapeHtml(v.queryNote)}</span>`));
  }
  if (v.campaign || v.group || v.ad) {
    rows.push(kvRow('Кампания', [
      v.campaign ? `<b>${escapeHtml(v.campaign)}</b>` : '',
      v.group ? `группа ${escapeHtml(v.group)}` : '',
      v.ad ? `объявление ${escapeHtml(v.ad)}` : '',
    ].filter(Boolean).join(' <span style="color:' + EMAIL_COLOR.muted + ';">·</span> ')));
  }
  if (typeof v.cpcRub === 'number') {
    rows.push(kvRow('Цена клика', `<b>${escapeHtml(rubShort(v.cpcRub))}</b>${
      v.cpcNote ? ` <span style="color:${EMAIL_COLOR.muted};">· ${escapeHtml(v.cpcNote)}</span>` : ''}`));
  } else if (v.cpcNote) {
    rows.push(kvRow('Цена клика',
      `<span style="color:${EMAIL_COLOR.muted};">${escapeHtml(v.cpcNote)}</span>`));
  }
  if (a.first_touch_source && a.first_touch_source !== a.last_touch_source) {
    rows.push(kvRow('Первое касание', escapeHtml(a.first_touch_source)
      + (a.first_touch_ts ? ` <span style="color:${EMAIL_COLOR.muted};">· ${escapeHtml(a.first_touch_ts.slice(0, 10))}</span>` : '')));
  }
  if (a.landing_path) rows.push(kvRow('Вход на сайт', escapeHtml(a.landing_path)));
  if (v.steps.length) {
    rows.push(kvRow('Путь клиента',
      v.steps.map((s) => escapeHtml(stepLine(s))).join('<br>')
      + (v.stepsOrigin ? `<br><span style="color:${EMAIL_COLOR.muted};">${escapeHtml(v.stepsOrigin)}</span>` : '')));
  }
  for (const note of v.pending) {
    rows.push(kvRow('Ожидается',
      `<span style="color:${EMAIL_COLOR.muted};">${escapeHtml(note)}</span>`));
  }
  return rows.join('');
}

/** Те же строки источника для text-версии. */
export function attributionLines(a: AttributionFields, enrichment?: SourceEnrichment | null): string[] {
  const v = explainSource(a, enrichment);
  return [
    `Тип трафика: ${v.kindLabel}${v.system ? ` · ${v.system}` : ''}`,
    ...(v.evidence ? [`Как определено: ${v.evidence}`] : []),
    ...(a.last_touch_source ? [`Метка канала: ${a.last_touch_source}`] : []),
    ...(v.query ? [`Запрос: ${v.query}${v.queryNote ? ` (${v.queryNote})` : ''}`]
      : v.queryNote ? [`Запрос: ${v.queryNote}`] : []),
    ...(v.campaign || v.group || v.ad ? [`Кампания: ${[
      v.campaign, v.group ? `группа ${v.group}` : '', v.ad ? `объявление ${v.ad}` : '',
    ].filter(Boolean).join(' · ')}`] : []),
    ...(typeof v.cpcRub === 'number'
      ? [`Цена клика: ${rubShort(v.cpcRub)}${v.cpcNote ? ` (${v.cpcNote})` : ''}`]
      : v.cpcNote ? [`Цена клика: ${v.cpcNote}`] : []),
    ...(a.first_touch_source && a.first_touch_source !== a.last_touch_source
      ? [`Первое касание: ${a.first_touch_source}`] : []),
    ...(a.landing_path ? [`Вход на сайт: ${a.landing_path}`] : []),
    ...(v.steps.length
      ? ['Путь клиента:', ...v.steps.map((s) => `  ${stepLine(s)}`),
        ...(v.stepsOrigin ? [`  (${v.stepsOrigin})`] : [])]
      : []),
    ...v.pending.map((n) => `Ожидается: ${n}`),
  ];
}
