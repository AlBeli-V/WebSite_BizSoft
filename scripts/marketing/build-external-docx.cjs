/**
 * Сборка Word-версии внешних публикаций для ревью.
 *
 * Источник — markdown-файлы docs/marketing/external/week1/*.md: правки текстов
 * вносятся там, .docx пересобирается. Обратной конвертации нет.
 *
 * Запуск: node scripts/marketing/build-external-docx.cjs [week1|dzen1]
 * Расширение .cjs обязательно: проект в ESM-режиме ("type": "module").
 */
const fs = require('fs');
const path = require('path');
// Требуется пакет docx: pnpm add -D docx (в CI не участвует).
const D = require('docx');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, PageBreak,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, LevelFormat,
  ExternalHyperlink, TableOfContents,
} = D;

const ROOT = path.resolve(__dirname, '..', '..');

/**
 * Пакеты документов. По умолчанию — week1.
 */
const PACKS = {
  week1: {
    files: ['docs/marketing/external/week1/01-vc-oplata-po.md',
            'docs/marketing/external/week1/02-dzen-oplata-poshagovo.md',
            'docs/marketing/external/week1/03-spark-oshibki-buhgalteria.md',
            'docs/marketing/external/week1/04-tenchat-karta-sotrudnika.md',
            'docs/marketing/external/week1/05-dzen-ai-dlya-kompanii.md',
            'docs/marketing/external/week1/06-tenchat-minimum-mest.md',
            'docs/marketing/external/week1/07-dzen-ai-dlya-razrabotki.md',
            'docs/marketing/external/week1/08-spark-byudzhet-ai-razrabotka.md'],
    out: 'exports/marketing/bizsoft-external-week1.docx',
    kicker: 'BIZSoft · Внешние публикации',
    title: 'Неделя 1: восемь материалов',
    subtitle: 'Пакет на внешнее экспертное ревью',
    platforms: 'VC.ru · Дзен · Spark.ru · TenChat',
    map: true,
    intro: 'docs/marketing/external/_intro-week1.md',
  },
  dzen1: {
    files: ['docs/marketing/external/dzen-requirements.md',
            'docs/marketing/external/dzen/01-karta-sotrudnika.md'],
    out: 'exports/marketing/bizsoft-dzen-01-karta-sotrudnika.docx',
    kicker: 'BIZSoft · Дзен',
    title: 'Регламент площадки и первый материал',
    subtitle: 'На ревью внешнего маркетолога',
    platforms: 'Дзен · канал BIZSoft',
    map: false,
    fullHead: true, // служебная шапка выводится целиком, а не тремя полями
    intro: 'docs/marketing/external/_intro-dzen1.md',
  },
  // Мастер-версия с расчётной моделью — на аудит юриста и налогового консультанта.
  'master-audit': {
    files: ['docs/marketing/content-library/objects/karta-sotrudnika/source.md'],
    out: 'exports/marketing/karta-sotrudnika-master-audit.docx',
    bare: true,
  },
  // Пакет для публикации: только текст статьи, без титула, вводной и карточки.
  // Копируется из Word прямо в редактор Дзена — форматирование переносится.
  'dzen1-publish': {
    files: ['docs/marketing/external/dzen/01-karta-sotrudnika.md'],
    out: 'exports/marketing/dzen-01-publish.docx',
    bare: true,
  },
};

const PACK = PACKS[process.argv[2] || 'week1'];
if (!PACK) { console.error('Неизвестный пакет:', process.argv[2]); process.exit(1); }
const OUT = path.join(ROOT, PACK.out);

/** Инлайновая разметка: **жирный**, *курсив*, [текст](url), `код`. */
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\)|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const tok = m[0];
    if (tok.startsWith('**')) {
      out.push(new TextRun({ text: tok.slice(2, -2), bold: true, ...base }));
    } else if (tok.startsWith('`')) {
      out.push(new TextRun({ text: tok.slice(1, -1), font: 'Consolas', size: 20, ...base }));
    } else if (tok.startsWith('[')) {
      const mm = tok.match(/\[([^\]]+)\]\(([^)]+)\)/);
      out.push(new ExternalHyperlink({
        link: mm[2],
        children: [new TextRun({ text: mm[1], style: 'Hyperlink', ...base })],
      }));
      out.push(new TextRun({ text: ` (${mm[2]})`, size: 18, color: '767676', ...base }));
    } else {
      out.push(new TextRun({ text: tok.slice(1, -1), italics: true, ...base }));
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out.length ? out : [new TextRun({ text: '', ...base })];
}

const cellBorders = {
  top: { style: BorderStyle.SINGLE, size: 4, color: 'D9D9D9' },
  bottom: { style: BorderStyle.SINGLE, size: 4, color: 'D9D9D9' },
  left: { style: BorderStyle.SINGLE, size: 4, color: 'D9D9D9' },
  right: { style: BorderStyle.SINGLE, size: 4, color: 'D9D9D9' },
};

/** Строки-продолжения (отступ ≥2 пробелов) приклеиваются к своему пункту. */
function joinWrapped(md) {
  const out = [];
  for (const raw of md.split('\n')) {
    const isCont = /^\s{2,}\S/.test(raw) && out.length && out[out.length - 1].trim() !== '';
    if (isCont && !/^\s*[-*]\s/.test(raw) && !/^\s*\d+\.\s/.test(raw) && !/^\s*\|/.test(raw)) {
      out[out.length - 1] += ' ' + raw.trim();
    } else {
      out.push(raw);
    }
  }
  return out;
}

/** Markdown-таблица → docx Table. Ширины колонок пропорциональны заголовкам. */
function mdTable(rows) {
  const cells = rows.map((r) => r.replace(/^\||\|$/g, '').split('|').map((c) => c.trim()));
  const cols = cells[0].length;
  const weights = cells[0].map((_, i) =>
    Math.max(...cells.map((r) => (r[i] || '').length), 6));
  const sum = weights.reduce((a, b) => a + b, 0);
  const TOTALW = 9000;
  const widths = weights.map((w) => Math.round((w / sum) * TOTALW));
  widths[cols - 1] = TOTALW - widths.slice(0, -1).reduce((a, b) => a + b, 0);
  const body = cells.slice(1).filter((r) => !/^-{2,}$/.test((r[0] || '').replace(/:/g, '')));
  const mk = (r, header) => new TableRow({
    tableHeader: header,
    children: r.slice(0, cols).map((txt, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      borders: cellBorders,
      shading: header ? { type: ShadingType.CLEAR, fill: 'F2F2F2', color: 'auto' } : undefined,
      margins: { top: 60, bottom: 60, left: 90, right: 90 },
      children: [new Paragraph({
        children: runs(txt, { size: 19, bold: header || undefined }),
        spacing: { after: 0, line: 260 },
      })],
    })),
  });
  return new Table({
    columnWidths: widths,
    width: { size: TOTALW, type: WidthType.DXA },
    rows: [mk(cells[0], true), ...body.map((r) => mk(r, false))],
  });
}

/** Абзацы markdown → элементы docx. Заголовки статьи сдвинуты на уровень вниз. */
function mdToParagraphs(md, { shift = 1 } = {}) {
  const els = [];
  const lines = joinWrapped(md);
  let buf = [];
  let table = [];
  const flush = () => {
    if (!buf.length) return;
    els.push(new Paragraph({ children: runs(buf.join(' ')), spacing: { after: 160, line: 300 } }));
    buf = [];
  };
  const flushTable = () => {
    if (table.length < 2) { table.forEach((r) => buf.push(r)); table = []; flush(); return; }
    els.push(mdTable(table));
    els.push(new Paragraph({ text: '', spacing: { after: 160 } }));
    table = [];
  };
  const H = [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3,
             HeadingLevel.HEADING_4, HeadingLevel.HEADING_5];
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (/^\s*\|.*\|\s*$/.test(line)) { flush(); table.push(line.trim()); continue; }
    if (table.length) flushTable();
    if (/^\s*$/.test(line)) { flush(); continue; }
    if (/^---+$/.test(line)) { flush(); continue; }
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      flush();
      const lvl = Math.min(h[1].length - 1 + shift, 4);
      els.push(new Paragraph({
        children: runs(h[2]),
        heading: H[lvl],
        spacing: { before: 280, after: 140 },
        keepNext: true,
      }));
      continue;
    }
    const ul = line.match(/^\s*[-*]\s+(.*)$/);
    if (ul) {
      flush();
      els.push(new Paragraph({ children: runs(ul[1]), bullet: { level: 0 }, spacing: { after: 80, line: 300 } }));
      continue;
    }
    const ol = line.match(/^\s*(\d+)\.\s+(.*)$/);
    if (ol) {
      flush();
      els.push(new Paragraph({
        children: runs(ol[2]),
        numbering: { reference: 'ordered', level: 0 },
        spacing: { after: 80, line: 300 },
      }));
      continue;
    }
    buf.push(line.trim());
  }
  if (table.length) flushTable();
  flush();
  return els;
}

/** Служебная шапка файла (до первого «---») и тело статьи. */
function splitArticle(md) {
  const i = md.indexOf('\n---\n');
  // Документ без служебной шапки (например регламент) идёт телом целиком:
  // первая строка «# Заголовок» становится названием раздела.
  if (i === -1) {
    const nl = md.indexOf('\n');
    return { head: md.slice(0, nl).trim(), body: md.slice(nl).trim() };
  }
  return { head: md.slice(0, i).trim(), body: md.slice(i + 5).trim() };
}

function meta(head) {
  const title = head.split('\n')[0].replace(/^#\s*/, '');
  const get = (k) => {
    const m = head.match(new RegExp(`\\*\\*${k}:\\*\\*\\s*(.+)`));
    return m ? m[1].trim() : '';
  };
  return {
    title,
    platform: get('Площадка'),
    volume: get('Объём'),
    keys: get('Ключевые фразы'),
    links: get('Целевые ссылки'),
  };
}


const WIDTHS = [700, 2200, 4300, 1000, 1200];
const TOTAL = WIDTHS.reduce((a, b) => a + b, 0);

function cell(text, w, opts = {}) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: cellBorders,
    shading: opts.header ? { type: ShadingType.CLEAR, fill: 'F2F2F2', color: 'auto' } : undefined,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    children: [new Paragraph({
      children: [new TextRun({ text, bold: !!opts.header, size: 19 })],
      spacing: { after: 0, line: 260 },
    })],
  });
}

const articles = PACK.files.map((rel) => {
  const { head, body } = splitArticle(fs.readFileSync(path.join(ROOT, rel), 'utf8'));
  return { file: rel, head, ...meta(head), body };
});

const children = [];

// ── Титул и вводная: только для ревью-пакетов ──
if (!PACK.bare) children.push(
  new Paragraph({ text: '', spacing: { after: 1400 } }),
  new Paragraph({
    children: [new TextRun({ text: PACK.kicker, size: 24, color: '767676', characterSpacing: 30 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 200 },
  }),
  new Paragraph({
    children: [new TextRun({ text: PACK.title, bold: true, size: 44 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
  }),
  new Paragraph({
    children: [new TextRun({ text: PACK.subtitle, size: 28, color: '404040' })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 600 },
  }),
  new Paragraph({
    children: [new TextRun({ text: PACK.platforms, size: 22, color: '767676' })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
  }),
  new Paragraph({
    children: [new TextRun({ text: 'Публикация от лица BIZSoft как эксперта. 01.09.2026', size: 20, color: '767676' })],
    alignment: AlignmentType.CENTER,
  }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ── Вводная для рецензента ──
if (!PACK.bare) children.push(
  ...mdToParagraphs(fs.readFileSync(path.join(ROOT, PACK.intro), 'utf8').trim(), { shift: 0 }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ── Карта публикаций ──
if (PACK.map && !PACK.bare) { children.push(
  new Paragraph({ text: 'Карта публикаций недели', heading: HeadingLevel.HEADING_1, spacing: { after: 200 } }),
  new Table({
    columnWidths: WIDTHS,
    width: { size: TOTAL, type: WidthType.DXA },
    rows: [
      new TableRow({
        tableHeader: true,
        children: [
          cell('№', WIDTHS[0], { header: true }),
          cell('Площадка', WIDTHS[1], { header: true }),
          cell('Заголовок', WIDTHS[2], { header: true }),
          cell('Слов', WIDTHS[3], { header: true }),
          cell('Ссылок', WIDTHS[4], { header: true }),
        ],
      }),
      ...articles.map((a, i) => {
        const h1 = a.body.match(/^##\s+(.*)$/m);
        const nlinks = (a.body.match(/\]\(https:\/\/biz-soft\.pro/g) || []).length;
        return new TableRow({
          children: [
            cell(String(i + 1), WIDTHS[0]),
            cell(a.platform.split(',')[0], WIDTHS[1]),
            cell(h1 ? h1[1] : a.title, WIDTHS[2]),
            cell(a.volume.replace(' (факт)', '').replace(' слов', ''), WIDTHS[3]),
            cell(String(nlinks), WIDTHS[4]),
          ],
        });
      }),
    ],
  }),
  new Paragraph({
    children: [new TextRun({
      text: 'Все ссылки ведут на страницы, присутствующие в /sitemap.xml. Точный коммерческий анкор — не более одного на материал.',
      size: 19, color: '767676',
    })],
    spacing: { before: 200 },
  }),
  new Paragraph({ children: [new PageBreak()] }),
); }

// ── Статьи ──
articles.forEach((a, i) => {
  if (PACK.bare) {
    children.push(...mdToParagraphs(a.body, { shift: 0 }));
    return;
  }
  children.push(
    new Paragraph({
      children: [new TextRun({ text: `Материал ${i + 1} · ${a.platform}`, size: 20, color: '767676', characterSpacing: 20 })],
      spacing: { after: 100 },
    }),
    new Paragraph({
      text: a.title.replace(/^[A-Z]-\S+\s+—\s+/, ''),
      heading: HeadingLevel.HEADING_1,
      spacing: { after: 160 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: 'D9D9D9', space: 6 } },
    }),
  );
  if (PACK.fullHead) {
    // Шапка целиком: в ней таблицы и решения, которые нужны рецензенту.
    const rest = a.head.split('\n').slice(1).join('\n').trim();
    if (rest) children.push(...mdToParagraphs(rest, { shift: 1 }));
  } else {
    const info = [
      ['Объём', a.volume],
      ['Ключевые фразы', a.keys],
      ['Целевые ссылки', a.links],
    ];
    info.forEach(([k, v]) => {
      if (!v) return;
      children.push(new Paragraph({
        children: [
          new TextRun({ text: `${k}: `, bold: true, size: 19, color: '404040' }),
          ...runs(v, { size: 19, color: '404040' }),
        ],
        spacing: { after: 60, line: 260 },
      }));
    });
  }
  children.push(new Paragraph({ text: '', spacing: { after: 200 } }));
  children.push(...mdToParagraphs(a.body, { shift: 1 }));
  if (i < articles.length - 1) children.push(new Paragraph({ children: [new PageBreak()] }));
});

const doc = new Document({
  creator: 'BIZSoft',
  title: 'BIZSoft — внешние публикации, неделя 1',
  description: 'Восемь материалов для VC.ru, Дзена, Spark.ru и TenChat на внешнее экспертное ревью',
  styles: {
    default: {
      document: { run: { font: 'Calibri', size: 22, color: '1A1A1A' }, paragraph: { spacing: { line: 300 } } },
      heading1: { run: { font: 'Calibri', size: 32, bold: true, color: '111111' } },
      heading2: { run: { font: 'Calibri', size: 26, bold: true, color: '111111' } },
      heading3: { run: { font: 'Calibri', size: 23, bold: true, color: '333333' } },
      heading4: { run: { font: 'Calibri', size: 22, bold: true, color: '404040' } },
    },
  },
  numbering: {
    config: [{
      reference: 'ordered',
      levels: [{
        level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.START,
        style: { paragraph: { indent: { left: 460, hanging: 260 } } },
      }],
    }],
  },
  sections: [{
    properties: { page: { margin: { top: 1100, bottom: 1100, left: 1200, right: 1200 } } },
    children,
  }],
});

fs.mkdirSync(path.dirname(OUT), { recursive: true });
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log('OK', OUT, b.length, 'байт'); });
