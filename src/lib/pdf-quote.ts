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

/**
 * Начертание водяного знака с диска. Кэш: полос на листе две, файл один.
 * Файла нет — возвращаем null, и знак набирается жирным шрифтом документа.
 */
const bandCache = new Map<string, Buffer | null>();
export function bandFontBuffer(file: string): Buffer | null {
  if (!bandCache.has(file)) {
    try {
      bandCache.set(file, readFileSync(resolveAsset(`public/brand/fonts/${file}`)));
    } catch (e) {
      console.error(`шрифт водяного знака ${file} не найден, берём шрифт документа`, e);
      bandCache.set(file, null);
    }
  }
  return bandCache.get(file) ?? null;
}

/** Файл начертания знака для драйвера картинки; null — файла нет. */
export function bandFontPath(file: string): string | null {
  return bandFontBuffer(file) ? resolveAsset(`public/brand/fonts/${file}`) : null;
}

/** Измеритель на pdfkit: оба формата считают раскладку им, поэтому не расходятся. */
export function pdfMeasure(): Measure {
  // Поле у пробного документа роли не играет: раскладка рисует по
  // абсолютным координатам, пробник нужен только для метрик шрифта.
  const probe = new PDFDocument({ size: 'A4', margin: PAGE.margin.left });
  probe.registerFont('r', FONT_REGULAR);
  probe.registerFont('b', FONT_BOLD);
  const registered = new Set<string>();
  const pick = (size: number, bold?: boolean, fontFile?: string) => {
    let name = bold ? 'b' : 'r';
    if (fontFile) {
      const buf = bandFontBuffer(fontFile);
      if (buf) {
        name = `f:${fontFile}`;
        if (!registered.has(name)) { probe.registerFont(name, buf); registered.add(name); }
      }
    }
    return probe.font(name).fontSize(size);
  };
  return {
    height: (text, size, width, bold) => { pick(size, bold); return probe.heightOfString(text, { width }); },
    width: (text, size, bold, fontFile) => { pick(size, bold, fontFile); return probe.widthOfString(text); },
  };
}

/** Какие начертания знака уже зарегистрированы в документе. */
const bandFonts = new WeakMap<PDFKit.PDFDocument, Set<string>>();

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

    // Слой 2 — градиентное ядро: узкая светящаяся жила вдоль середины
    // полосы, гаснет к верхнему и нижнему краю листа.
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

    // Слой 3 — замки: путь приходит из раскладки, скважина вырезается
    // правилом even-odd.
    doc.fillOpacity(p.lockOpacity);
    for (const d of p.locks) doc.path(d).fill(p.color, 'even-odd');
    doc.fillOpacity(1);

    // Слой 4 — надпись снизу вверх, прижатая к своему замку. Разрядка
    // задаётся characterSpacing: она делает строку ритмичной, не увеличивая
    // кегль, и одинаково считается в обоих форматах.
    // Надпись набирается своим шрифтом; регистрируем его один раз на документ.
    const bandBuf = bandFontBuffer(p.fontFile);
    const bandName = `w:${p.fontFile}`;
    if (bandBuf && !bandFonts.has(doc)) bandFonts.set(doc, new Set());
    const reg = bandFonts.get(doc);
    if (bandBuf && reg && !reg.has(bandName)) { doc.registerFont(bandName, bandBuf); reg.add(bandName); }
    doc.font(bandBuf ? bandName : 'b').fontSize(p.size).fillColor(p.color).fillOpacity(p.textOpacity);
    doc.save();
    doc.rotate(-90, { origin: [p.cx, p.textCy] });
    const tw = doc.widthOfString(p.text, { characterSpacing: p.spacing });
    doc.text(p.text, p.cx - tw / 2, p.textCy - p.size * 0.62,
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
