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
} as const;

const F = "font-family:Arial,Helvetica,sans-serif;";

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
    + `<meta name="viewport" content="width=device-width,initial-scale=1"></head>`
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
