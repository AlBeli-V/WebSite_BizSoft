/**
 * PDF коммерческого предложения — драйвер поверх общей раскладки.
 *
 * Сам макет живёт в quote-layout.ts, здесь только рисование примитивов
 * средствами pdfkit. Кириллица — встроенный DejaVu Sans из node_modules,
 * headless-браузер не нужен.
 *
 * PDF — рабочий документ: его отправляет руководитель лично. Клиент со
 * страницы получает JPG (см. jpg-quote.ts), чтобы документ нельзя было
 * отредактировать и выдать за наш.
 */
import PDFDocument from 'pdfkit';
import { createRequire } from 'node:module';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildQuoteLayout, PAGE, type QuoteData, type Measure, type Primitive } from './quote-layout';

export type { QuoteData };
export { buildQuoteNo, formatDateRu, addDays } from './quote-layout';

const require = createRequire(import.meta.url);

/**
 * Шрифт документов — тот же Raleway, что на сайте (решение руководителя
 * 15.09.2026). Вариативный woff2 витрины ни pdfkit, ни resvg не читают,
 * поэтому в `public/brand/fonts` лежат статические начертания, полученные
 * из него же (`scripts/brand/build-doc-fonts.mjs`); они попадают в образ
 * вместе с dist/client.
 *
 * Если файлов на месте не оказалось — документ всё равно собирается на
 * DejaVu Sans из node_modules: расхождение в шрифте хуже, чем ненабранное
 * КП, но неотправленное предложение хуже и того.
 */
const DOC_FONT_FAMILY = 'Raleway';
const DEJAVU_FAMILY = 'DejaVu Sans';

function loadFont(brand: string, fallback: string): { buffer: Buffer; brand: boolean } {
  try {
    return { buffer: readFileSync(resolveAsset(`public/brand/fonts/${brand}`)), brand: true };
  } catch (e) {
    console.error(`шрифт документа ${brand} не найден, берём DejaVu`, e);
    return { buffer: readFileSync(require.resolve(`dejavu-fonts-ttf/ttf/${fallback}`)), brand: false };
  }
}

/** Путь к запасному шрифту DejaVu (используется драйвером картинки). */
export function fontPath(file: string): string {
  return require.resolve(`dejavu-fonts-ttf/ttf/${file}`);
}

const REGULAR = loadFont('Raleway-Regular.ttf', 'DejaVuSans.ttf');
const BOLD = loadFont('Raleway-Bold.ttf', 'DejaVuSans-Bold.ttf');
const FONT_REGULAR = REGULAR.buffer;
const FONT_BOLD = BOLD.buffer;

/** Начертания документа для драйвера картинки: те же файлы и то же имя. */
export function docFonts(): { family: string; files: string[] } {
  const brand = REGULAR.brand && BOLD.brand;
  return brand
    ? { family: DOC_FONT_FAMILY,
        files: [resolveAsset('public/brand/fonts/Raleway-Regular.ttf'),
                resolveAsset('public/brand/fonts/Raleway-Bold.ttf')] }
    : { family: DEJAVU_FAMILY,
        files: [fontPath('DejaVuSans.ttf'), fontPath('DejaVuSans-Bold.ttf')] };
}

/**
 * Путь к файлу из public/ — и в исходниках, и в собранном приложении.
 *
 * Прежний расчёт «два уровня вверх от модуля» верен только для src/lib.
 * В рантайм-образ копируется один каталог dist, исходников и public/ там
 * нет вовсе, а сам модуль оказывается в dist/server/pages/api — два уровня
 * вверх дают dist/, где никакого public/ не лежит. Логотип в проде не
 * читался, генерация падала, и КП не уходило: сервер отвечал «не удалось
 * сформировать документ».
 *
 * Поэтому путь ищется, а не вычисляется: от каталога модуля и от рабочего
 * каталога вверх по дереву, в каждом — три места, где файл реально бывает.
 * Так работают и запуск из исходников, и тесты, и контейнер, независимо от
 * глубины, на которую сборщик уложил чанк.
 */
export function resolveAsset(file: string): string {
  // Внутри dist/client файлы лежат без префикса public/: Astro копирует
  // содержимое каталога, а не сам каталог.
  const rel = file.replace(/^public\//, '');
  const starts = [fileURLToPath(new URL('.', import.meta.url)), process.cwd()];
  const tried: string[] = [];
  for (const start of starts) {
    let dir = start;
    for (let up = 0; up < 8; up += 1) {
      for (const candidate of [
        join(dir, file),                    // корень проекта
        join(dir, 'dist', 'client', rel),   // рядом с собранным приложением
        join(dir, 'client', rel),           // изнутри dist
      ]) {
        if (existsSync(candidate)) return candidate;
        tried.push(candidate);
      }
      const parent = dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }
  }
  throw new Error(`файл ${file} не найден; проверены пути: ${tried.join(', ')}`);
}

const logoCache = new Map<string, Buffer>();
/** Файл логотипа с диска. Кэш: страниц бывает несколько, файл один. */
export function logoBuffer(file: string): Buffer {
  let buf = logoCache.get(file);
  if (!buf) {
    buf = readFileSync(resolveAsset(file));
    logoCache.set(file, buf);
  }
  return buf;
}

/** Измеритель на pdfkit: оба формата считают раскладку им, поэтому не расходятся. */
export function pdfMeasure(): Measure {
  // Поле у пробного документа роли не играет: раскладка рисует по
  // абсолютным координатам, пробник нужен только для метрик шрифта.
  const probe = new PDFDocument({ size: 'A4', margin: PAGE.margin.left });
  probe.registerFont('r', FONT_REGULAR);
  probe.registerFont('b', FONT_BOLD);
  const pick = (size: number, bold?: boolean) => probe.font(bold ? 'b' : 'r').fontSize(size);
  return {
    height: (text, size, width, bold) => { pick(size, bold); return probe.heightOfString(text, { width }); },
    width: (text, size, bold) => { pick(size, bold); return probe.widthOfString(text); },
  };
}

/**
 * Замок на скруглённой плашке — как на референсе: плашка подложкой, над
 * ней дужка линией и корпус заливкой.
 */
function lock(doc: PDFKit.PDFDocument, cx: number, cy: number,
              size: number, color: string, opacity: number): void {
  const bodyW = size / 2;
  const bodyH = size * 0.39;
  const bodyY = cy - size * 0.05;
  doc.save();
  // Плашка: та же заливка, что у полосы, только плотнее — замок читается
  // как значок, а не как пятно.
  doc.fillOpacity(opacity * 0.28);
  doc.roundedRect(cx - size / 2, cy - size / 2, size, size, size * 0.25).fill(color);
  doc.fillOpacity(opacity);
  doc.strokeOpacity(opacity);
  doc.strokeColor(color).lineWidth(size * 0.073);
  const arm = size * 0.164;
  doc.moveTo(cx - arm, bodyY)
    .lineTo(cx - arm, bodyY - size * 0.19)
    .bezierCurveTo(cx - arm, cy - size * 0.42, cx + arm, cy - size * 0.42, cx + arm, bodyY - size * 0.19)
    .lineTo(cx + arm, bodyY)
    .stroke();
  doc.roundedRect(cx - bodyW / 2, bodyY, bodyW, bodyH, size * 0.09).fill(color);
  doc.restore();
  doc.fillOpacity(1).strokeOpacity(1);
}

function draw(doc: PDFKit.PDFDocument, p: Primitive): void {
  if (p.kind === 'image') {
    // Логотип читается с диска один раз и кэшируется: страниц может быть
    // несколько, а файл один и тот же.
    // align не указываем: для изображений pdfkit принимает только 'center'
    // и 'right', а выравнивание по левому краю и так подразумевается.
    doc.image(logoBuffer(p.file), p.x, p.y, { fit: [p.w, p.h] });
    return;
  }
  if (p.kind === 'bullet') {
    doc.circle(p.x, p.y, p.size).fill(p.color);
    return;
  }
  if (p.kind === 'rect') {
    doc.rect(p.x, p.y, p.w, p.h).fill(p.fill);
    return;
  }
  if (p.kind === 'line') {
    doc.moveTo(p.x1, p.y1).lineTo(p.x2, p.y2)
      .strokeColor(p.color).lineWidth(p.lineWidth).stroke();
    return;
  }
  if (p.kind === 'band') {
    doc.save();

    // Слой 1 — подложка во всю высоту листа.
    doc.fillOpacity(p.fillOpacity);
    doc.rect(p.x, p.y, p.w, p.h).fill(p.color);
    doc.fillOpacity(1);

    // Слой 2 — градиентное ядро: свечение вдоль середины полосы, гаснет к
    // верхнему и нижнему краю листа.
    const core = doc.linearGradient(p.x, p.y, p.x, p.y + p.h);
    core.stop(0, p.color, 0)
      .stop(0.16, p.color, p.coreOpacity)
      .stop(0.84, p.color, p.coreOpacity)
      .stop(1, p.color, 0);
    doc.rect(p.x + p.coreInset, p.y, p.w - p.coreInset * 2, p.h).fill(core);

    // Тонкие линии по краям: край полосы виден и на чёрно-белой печати.
    doc.strokeOpacity(p.edgeOpacity).strokeColor(p.color).lineWidth(0.8);
    for (const x of [p.x, p.x + p.w]) {
      doc.moveTo(x, p.y).lineTo(x, p.y + p.h).stroke();
    }
    doc.strokeOpacity(1);

    // Слой 3 — замки на концах полосы.
    const cx = p.cx;
    lock(doc, cx, p.y + p.lockInset, p.lock, p.color, p.textOpacity);
    lock(doc, cx, p.y + p.h - p.lockInset, p.lock, p.color, p.textOpacity);

    // Слой 4 — надпись снизу вверх по середине полосы. Разрядка задаётся
    // characterSpacing: она делает длинную строку ритмичной, не увеличивая
    // кегль, и одинаково считается в обоих форматах.
    const cy = p.y + p.h / 2;
    doc.font('b').fontSize(p.size).fillColor(p.color).fillOpacity(p.textOpacity);
    doc.save();
    doc.rotate(-90, { origin: [cx, cy] });
    const tw = doc.widthOfString(p.text, { characterSpacing: p.spacing });
    doc.text(p.text, cx - tw / 2, cy - p.size * 0.62,
             { lineBreak: false, characterSpacing: p.spacing });
    doc.restore();
    doc.fillOpacity(1);

    doc.restore();
    return;
  }
  doc.font(p.bold ? 'b' : 'r').fontSize(p.size).fillColor(p.color);
  // lineBreak: false обязателен и при заданной ширине. Раскладка уже разбила
  // текст на строки и знает координату каждой; если оставить перенос на
  // pdfkit, он у нижнего поля молча заводит новую страницу — так колонтитул
  // порождал два пустых листа, которых нет ни в раскладке, ни в JPG.
  doc.text(p.text, p.x, p.y,
    p.width ? { width: p.width, align: p.align || 'left', lineBreak: false }
            : { lineBreak: false });
}

export function generateQuotePdf(data: QuoteData): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    try {
      const pages = buildQuoteLayout(data, pdfMeasure());
      // Поля документа обнулены намеренно: раскладка позиционирует каждый
      // примитив абсолютно и сама решает, где кончается страница. С полями
      // pdfkit считает нижнюю границу своей и заводит продолжение страницы
      // всякий раз, когда текст оказывается ниже неё, — колонтитул порождал
      // два пустых листа, которых нет ни в раскладке, ни в JPG.
      const doc = new PDFDocument({ size: 'A4', margin: 0, autoFirstPage: false });
      doc.registerFont('r', FONT_REGULAR);
      doc.registerFont('b', FONT_BOLD);

      const chunks: Buffer[] = [];
      doc.on('data', (c: Buffer) => chunks.push(c));
      doc.on('end', () => resolve(Buffer.concat(chunks)));
      doc.on('error', reject);

      for (const page of pages) {
        doc.addPage({ size: 'A4', margin: 0 });
        for (const p of page.items) draw(doc, p);
      }
      doc.end();
    } catch (e) {
      reject(e);
    }
  });
}
