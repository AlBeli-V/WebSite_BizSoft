/**
 * Документ КП для клиента: один PDF из листов-картинок и его имя.
 *
 * Раньше клиенту уходило по файлу на лист (`KP_…_лист1.jpg`, `_лист2.jpg`):
 * распечатать такое можно, а работать с трёхлистовым предложением — нет.
 * Решение руководителя 15.09.2026: листы остаются картинками (их нельзя
 * открыть в редакторе, подменить сумму и выдать за наш документ), но в
 * письмо уходит один PDF, где каждая картинка — отдельная страница А4.
 *
 * Пересжатия нет: JPEG-данные кладутся в PDF как есть, `doc.image` их не
 * перекодирует. Поэтому текст в PDF ровно той же чёткости, что на листе,
 * а вес файла — сумма весов листов.
 */
import PDFDocument from 'pdfkit';
import { PAGE } from './quote-layout';

/** Латиница для имени файла: имя заказчика не должно ломать почту и диск. */
const TRANSLIT: Record<string, string> = {
  а: 'A', б: 'B', в: 'V', г: 'G', д: 'D', е: 'E', ё: 'E', ж: 'ZH', з: 'Z',
  и: 'I', й: 'I', к: 'K', л: 'L', м: 'M', н: 'N', о: 'O', п: 'P', р: 'R',
  с: 'S', т: 'T', у: 'U', ф: 'F', х: 'H', ц: 'TS', ч: 'CH', ш: 'SH',
  щ: 'SCH', ъ: '', ы: 'Y', ь: '', э: 'E', ю: 'YU', я: 'YA',
};

/**
 * Организационно-правовые формы в имя файла не идут: они одинаковы у
 * половины заказчиков и съедают место, по которому файл узнают.
 * «ООО «ИТ МАТРИЦА»» → `IT-MATRITSA`.
 */
// Граница слова здесь — просмотр вперёд, а не \b: кириллица в JS-регулярках
// без флага u словом не считается, и \b после «ООО» не срабатывает вовсе.
const LEGAL_FORMS = /^(ООО|ОАО|ЗАО|ПАО|АО|НАО|ИП|НКО|ФГУП|ГУП|МУП|АНО|ТСЖ|LLC|LTD|INC|GMBH)(?=\s|$)/i;

/** Имя заказчика латиницей: без кавычек, кириллицы и сдвоенных дефисов. */
export function latinName(raw: string): string {
  const cleaned = String(raw || '')
    .replace(/[«»"'`„“”]/g, ' ')
    .trim()
    .replace(LEGAL_FORMS, ' ')
    .trim();
  const translit = [...cleaned].map((ch) => {
    const lower = ch.toLowerCase();
    const mapped = TRANSLIT[lower];
    if (mapped !== undefined) return mapped;
    if (/[A-Za-z0-9]/.test(ch)) return ch.toUpperCase();
    return '-';
  }).join('');
  const name = translit
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '');
  // Пустая строка сломала бы имя файла двумя подчёркиваниями подряд.
  return name || 'CLIENT';
}

/**
 * Имя файла КП: `КП_BIZSoft_<номер>_<ЗАКАЗЧИК>_<дата>.pdf`.
 *
 * Кириллица в имени оставлена намеренно: файл открывает человек, и
 * «КП_BIZSoft_…» в списке вложений он узнаёт с одного взгляда. Латиницей
 * приводится только название заказчика — оно приходит из формы и может
 * содержать что угодно.
 */
export function quotePdfFileName(quoteNo: string, buyerCompany: string, dateRu: string): string {
  return `КП_BIZSoft_${quoteNo}_${latinName(buyerCompany)}_${dateRu}.pdf`;
}

/**
 * Собрать листы-картинки в один PDF: одна картинка — одна страница А4.
 *
 * Картинка рисуется во весь лист без полей: она и есть лист, поля уже
 * заложены в раскладку документа (`quote-layout.ts`).
 */
export function pdfFromJpegPages(pages: Buffer[]): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    if (pages.length === 0) { reject(new Error('нет листов для сборки PDF')); return; }
    try {
      const doc = new PDFDocument({ size: 'A4', margin: 0, autoFirstPage: false });
      const chunks: Buffer[] = [];
      doc.on('data', (c: Buffer) => chunks.push(c));
      doc.on('end', () => resolve(Buffer.concat(chunks)));
      doc.on('error', reject);
      for (const page of pages) {
        doc.addPage({ size: 'A4', margin: 0 });
        doc.image(page, 0, 0, { width: PAGE.width, height: PAGE.height });
      }
      doc.end();
    } catch (e) {
      reject(e);
    }
  });
}

/** Размер файла для письма: «1,1 МБ». Человеку, а не в байтах. */
export function fileSizeRu(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} МБ`;
}
