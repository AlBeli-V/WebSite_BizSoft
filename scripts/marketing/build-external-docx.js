/**
 * Сборка Word-версии внешних публикаций для ревью.
 *
 * Источник — markdown-файлы docs/marketing/external/week1/*.md: правки текстов
 * вносятся там, .docx пересобирается. Обратной конвертации нет.
 *
 * Запуск: node scripts/marketing/build-external-docx.js
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
const SRC = path.join(ROOT, 'docs/marketing/external/week1');
const OUT = path.join(ROOT, 'exports/marketing/bizsoft-external-week1.docx');

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

/** Абзацы markdown → элементы docx. Заголовки статьи сдвинуты на уровень вниз. */
function mdToParagraphs(md, { shift = 1 } = {}) {
  const els = [];
  const lines = md.split('\n');
  let buf = [];
  const flush = () => {
    if (!buf.length) return;
    els.push(new Paragraph({ children: runs(buf.join(' ')), spacing: { after: 160, line: 300 } }));
    buf = [];
  };
  const H = [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3,
             HeadingLevel.HEADING_4, HeadingLevel.HEADING_5];
  for (const raw of lines) {
    const line = raw.trimEnd();
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
    const ul = line.match(/^[-*]\s+(.*)$/);
    if (ul) {
      flush();
      els.push(new Paragraph({ children: runs(ul[1]), bullet: { level: 0 }, spacing: { after: 80, line: 300 } }));
      continue;
    }
    const ol = line.match(/^(\d+)\.\s+(.*)$/);
    if (ol) {
      flush();
      els.push(new Paragraph({
        children: runs(ol[2]),
        numbering: { reference: 'ordered', level: 0 },
        spacing: { after: 80, line: 300 },
      }));
      continue;
    }
    const cont = line.match(/^\s{2,}(\S.*)$/);
    if (cont && els.length && !buf.length) {
      // продолжение пункта списка — дописываем в последний абзац
      const prev = els[els.length - 1];
      if (prev instanceof Paragraph) { buf.push(line.trim()); continue; }
    }
    buf.push(line.trim());
  }
  flush();
  return els;
}

/** Служебная шапка файла (до первого «---») и тело статьи. */
function splitArticle(md) {
  const i = md.indexOf('\n---\n');
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

const cellBorders = {
  top: { style: BorderStyle.SINGLE, size: 4, color: 'D9D9D9' },
  bottom: { style: BorderStyle.SINGLE, size: 4, color: 'D9D9D9' },
  left: { style: BorderStyle.SINGLE, size: 4, color: 'D9D9D9' },
  right: { style: BorderStyle.SINGLE, size: 4, color: 'D9D9D9' },
};

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

const files = fs.readdirSync(SRC).filter((f) => f.endsWith('.md')).sort();
const articles = files.map((f) => {
  const { head, body } = splitArticle(fs.readFileSync(path.join(SRC, f), 'utf8'));
  return { file: f, ...meta(head), body };
});

const children = [];

// ── Титул ──
children.push(
  new Paragraph({ text: '', spacing: { after: 1400 } }),
  new Paragraph({
    children: [new TextRun({ text: 'BIZSoft · Внешние публикации', size: 24, color: '767676', characterSpacing: 30 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 200 },
  }),
  new Paragraph({
    children: [new TextRun({ text: 'Неделя 1: восемь материалов', bold: true, size: 44 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
  }),
  new Paragraph({
    children: [new TextRun({ text: 'Пакет на внешнее экспертное ревью', size: 28, color: '404040' })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 600 },
  }),
  new Paragraph({
    children: [new TextRun({ text: 'VC.ru · Дзен · Spark.ru · TenChat', size: 22, color: '767676' })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
  }),
  new Paragraph({
    children: [new TextRun({ text: 'Публикация от лица BIZSoft как эксперта. 01.09.2026', size: 20, color: '767676' })],
    alignment: AlignmentType.CENTER,
  }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ── Что мы просим у эксперта ──
children.push(
  new Paragraph({ text: 'О чём мы просим эксперта', heading: HeadingLevel.HEADING_1, spacing: { after: 200 } }),
  ...mdToParagraphs(`
Восемь текстов ниже — первая неделя программы внешних публикаций BIZSoft. Задача недели не в
ссылках как таковых, а в замере: какие площадки и какие темы дают индексацию, показы и переходы.
Платные размещения покупаются позже и только по темам, доказавшим спрос.

Все материалы написаны от лица BIZSoft как отраслевого эксперта, с открытым раскрытием аффилиации:
мы прямо говорим, что мы поставщик. Это осознанный выбор — скрытая реклама снимается площадками
и хуже читается аудиторией.

**Что важно проверить в первую очередь**

1. **Юридические и бухгалтерские формулировки.** Тексты касаются оплаты зарубежного ПО, закрывающих
документов и лицензирования. Мы намеренно избегали ссылок на конкретные нормы, но утверждения
о том, что принимает бухгалтерия и на кого оформляется лицензия, требуют проверки специалистом.
2. **Фактура по продуктам.** В материалах названы пороги мест (ChatGPT Business — от 2, Claude Team —
от 5), наличие SSO только на Enterprise, IP-индемнификация у GitHub Copilot Business. Эти данные
взяты из каталога сайта и должны быть сверены с текущими условиями вендоров на дату публикации.
3. **Тональность для площадки.** VC.ru и Spark.ru плохо принимают материалы, читающиеся как реклама.
Просим оценить, где текст сваливается в продажу.
4. **Раскрытие аффилиации.** Достаточно ли явно и достаточно ли уместно оно сделано.
5. **Ссылочная нагрузка.** В каждом материале 2–3 ссылки на сайт. Просим сказать, где это выглядит
избыточным для конкретной площадки.
6. **Что мы упустили** — возражения аудитории, на которые текст не отвечает.

**Чего в текстах сознательно нет**

Цен. На сайте цены ориентировочные и зависят от курса и состава, поэтому в статьях названы принципы
ценообразования, а не цифры. Если эксперт считает, что без порядка цен материал теряет ценность,
это отдельное решение.
`.trim(), { shift: 1 }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ── Карта публикаций ──
children.push(
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
);

// ── Статьи ──
articles.forEach((a, i) => {
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
