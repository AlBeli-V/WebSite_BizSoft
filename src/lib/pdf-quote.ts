/**
 * Генерация PDF коммерческого предложения (КП) на pdfkit.
 * Кириллица — через встроенный DejaVu Sans (грузим из node_modules).
 * Возвращает Buffer. Без headless-браузера.
 */
import PDFDocument from 'pdfkit';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { seller, site } from '../config/site';
import { formatRub } from './pricing';
import type { QuoteItem } from './types';

const require = createRequire(import.meta.url);
function fontPath(file: string): string {
  return require.resolve(`dejavu-fonts-ttf/ttf/${file}`);
}
const FONT_REGULAR = readFileSync(fontPath('DejaVuSans.ttf'));
const FONT_BOLD = readFileSync(fontPath('DejaVuSans-Bold.ttf'));

const ACCENT = '#FF763C';
const DARK = '#14161A';
const MUTED = '#6B7280';

export interface QuoteData {
  quoteNo: string;
  date: string; // dd.mm.yyyy
  validUntil: string; // dd.mm.yyyy
  buyerCompany: string;
  buyerInn: string;
  contactName: string;
  email: string;
  phone?: string;
  items: QuoteItem[];
  total: number;
}

export function generateQuotePdf(data: QuoteData): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    try {
      const doc = new PDFDocument({ size: 'A4', margin: 48 });
      doc.registerFont('r', FONT_REGULAR);
      doc.registerFont('b', FONT_BOLD);
      doc.font('r');

      const chunks: Buffer[] = [];
      doc.on('data', (c: Buffer) => chunks.push(c));
      doc.on('end', () => resolve(Buffer.concat(chunks)));
      doc.on('error', reject);

      const left = doc.page.margins.left;
      const right = doc.page.width - doc.page.margins.right;
      const width = right - left;

      // ── Шапка ──
      doc.font('b').fontSize(22).fillColor(DARK).text('Biz', left, 48, { continued: true });
      doc.fillColor(ACCENT).text('Soft');
      doc.font('r').fontSize(9).fillColor(MUTED).text(site.tagline, left, 74);

      doc.font('b').fontSize(16).fillColor(DARK).text('Коммерческое предложение', left, 48, { width, align: 'right' });
      doc.font('r').fontSize(10).fillColor(MUTED)
        .text(`№ ${data.quoteNo}`, left, 72, { width, align: 'right' })
        .text(`от ${data.date}`, { width, align: 'right' })
        .text(`Действует до ${data.validUntil}`, { width, align: 'right' });

      doc.moveTo(left, 108).lineTo(right, 108).strokeColor('#E5E7EB').lineWidth(1).stroke();

      // ── Продавец / Покупатель ──
      let y = 124;
      doc.font('b').fontSize(10).fillColor(DARK).text('Продавец', left, y);
      doc.font('b').fontSize(10).fillColor(DARK).text('Покупатель', left + width / 2 + 10, y);
      y += 16;
      doc.font('r').fontSize(9).fillColor('#374151');

      const sellerLines = [
        seller.legalName,
        seller.address,
        `ИНН ${seller.inn}, ОГРНИП ${seller.ogrnip}`,
        `Тел.: ${seller.phone}`,
        `E-mail: ${seller.email}`,
      ];
      const buyerLines = [
        data.buyerCompany || '—',
        data.buyerInn ? `ИНН ${data.buyerInn}` : '',
        data.contactName ? `Контакт: ${data.contactName}` : '',
        data.email ? `E-mail: ${data.email}` : '',
        data.phone ? `Тел.: ${data.phone}` : '',
      ].filter(Boolean);

      // Сдвигаем Y по реально измеренной высоте каждой строки (учёт переносов длинных строк).
      const colW = width / 2 - 10;
      let yL = y;
      let yR = y;
      for (const l of sellerLines) { doc.text(l, left, yL, { width: colW }); yL += doc.heightOfString(l, { width: colW }) + 2; }
      for (const l of buyerLines) { doc.text(l, left + width / 2 + 10, yR, { width: colW }); yR += doc.heightOfString(l, { width: colW }) + 2; }
      y = Math.max(yL, yR) + 14;

      // ── Таблица позиций ──
      const cols = {
        n: left,
        name: left + 26,
        sku: left + width - 230,
        qty: left + width - 150,
        price: left + width - 110,
        sum: left + width - 60,
      };
      doc.rect(left, y, width, 22).fill('#F3F4F6');
      doc.font('b').fontSize(9).fillColor(DARK);
      doc.text('№', cols.n + 4, y + 7);
      doc.text('Наименование', cols.name, y + 7);
      doc.text('Артикул', cols.sku, y + 7, { width: 76 });
      doc.text('Кол-во', cols.qty, y + 7, { width: 38, align: 'right' });
      doc.text('Цена', cols.price, y + 7, { width: 46, align: 'right' });
      doc.text('Сумма', cols.sum, y + 7, { width: 56, align: 'right' });
      y += 22;

      doc.font('r').fontSize(9).fillColor('#374151');
      data.items.forEach((it, i) => {
        const nameH = doc.heightOfString(it.name, { width: cols.sku - cols.name - 8 });
        const rowH = Math.max(20, nameH + 8);
        if (y + rowH > doc.page.height - 120) {
          doc.addPage();
          y = 48;
        }
        doc.fillColor('#374151');
        doc.text(String(i + 1), cols.n + 4, y + 4, { width: 20 });
        doc.text(it.name, cols.name, y + 4, { width: cols.sku - cols.name - 8 });
        doc.text(it.sku, cols.sku, y + 4, { width: 76 });
        doc.text(String(it.qty), cols.qty, y + 4, { width: 38, align: 'right' });
        doc.text(formatRub(it.price), cols.price, y + 4, { width: 46, align: 'right' });
        doc.text(formatRub(it.sum), cols.sum, y + 4, { width: 56, align: 'right' });
        doc.moveTo(left, y + rowH).lineTo(right, y + rowH).strokeColor('#E5E7EB').lineWidth(0.5).stroke();
        y += rowH;
      });

      // ── Итог ──
      y += 10;
      doc.font('b').fontSize(12).fillColor(DARK)
        .text(`Итого: ${formatRub(data.total)}`, left, y, { width, align: 'right' });
      doc.font('r').fontSize(8).fillColor(MUTED)
        .text('НДС не облагается (применяется специальный налоговый режим).', left, y + 18, { width, align: 'right' });

      // ── Реквизиты для оплаты ──
      y += 44;
      doc.font('b').fontSize(10).fillColor(DARK).text('Реквизиты для оплаты по счёту', left, y);
      y += 16;
      doc.font('r').fontSize(9).fillColor('#374151');
      const bank = [
        `Получатель: ${seller.legalName}`,
        `ИНН ${seller.inn}`,
        `Банк: ${seller.bank.bankName}`,
        `Р/с ${seller.bank.account}`,
        `К/с ${seller.bank.corrAccount}`,
        `БИК ${seller.bank.bik}`,
      ];
      bank.forEach((l, i) => doc.text(l, left, y + i * 12));

      // ── Подвал (две короткие строки, чтобы не уехать на новую страницу) ──
      doc.font('r').fontSize(8).fillColor(MUTED)
        .text(`${seller.shortName} · ${site.url} · ${seller.phone}`, left, doc.page.height - 82, { width, align: 'center', lineBreak: false })
        .text('Работаем по договору, оплата по счёту, закрывающие документы через ЭДО.', left, doc.page.height - 70, { width, align: 'center', lineBreak: false });

      doc.end();
    } catch (e) {
      reject(e);
    }
  });
}

/** Номер КП вида BZ-YYYYMMDD-XXXX (XXXX — из времени/случайности вызывающего). */
export function buildQuoteNo(now: Date, suffix: string): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `BZ-${y}${m}${d}-${suffix}`;
}

/** dd.mm.yyyy */
export function formatDateRu(d: Date): string {
  return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.${d.getFullYear()}`;
}

export function addDays(d: Date, days: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + days);
  return r;
}
