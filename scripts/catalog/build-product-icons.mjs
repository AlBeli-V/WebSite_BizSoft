/**
 * Нормализация выбранных знаков продуктов в формат пакета
 * (правило docs/rules/product-logos.md):
 *
 *   src/assets/product-icons/catalog/color/<id>.svg   512×512, прозрачный фон
 *   src/assets/product-icons/catalog/mono/<id>.svg    то же в монохроме
 *   src/data/product-icon-map.json                    слаг → id
 *   docs/catalog-product-icons-manifest.json          источник и права
 *
 * Вход — data/catalog/logo-choices.json: [{ id, pick }] — номер кандидата
 * из assets/incoming/logos/<id>/candidates.json (1..N) либо путь к файлу.
 * Векторный кандидат кладётся в обёртку 512 как есть; растровый —
 * вписывается в 512×512 с полями 6% и встраивается PNG в SVG (так же
 * устроены 106 знаков действующего пакета). Монохром: вектор — заливка
 * одним цветом, растр — обесцвечивание.
 *
 *   node scripts/catalog/build-product-icons.mjs [--choices data/catalog/logo-choices.json]
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import sharp from 'sharp';

const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => a.startsWith('--') ? [a.slice(2), all[i + 1]] : []).filter(Boolean));
const CHOICES = args.choices || 'data/catalog/logo-choices.json';
const INCOMING = 'assets/incoming/logos';
const REQUESTS = 'data/catalog/logo-requests.json';
const PACK = 'src/assets/product-icons/catalog';
const MAP = 'src/data/product-icon-map.json';
const MANIFEST = 'docs/catalog-product-icons-manifest.json';
const SIZE = 512; const PAD = Math.round(SIZE * 0.06);

const choices = JSON.parse(readFileSync(CHOICES, 'utf8'));
const requests = new Map(JSON.parse(readFileSync(REQUESTS, 'utf8')).map((r) => [r.id, r]));
const map = JSON.parse(readFileSync(MAP, 'utf8'));
const manifest = JSON.parse(readFileSync(MANIFEST, 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');

function wrapSvg(id, title, desc, inner) {
  return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${SIZE}" height="${SIZE}" viewBox="0 0 ${SIZE} ${SIZE}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title><desc>${esc(desc)}</desc>${inner}</svg>`;
}

async function rasterToPngs(buf) {
  const inner = SIZE - PAD * 2;
  const base = sharp(buf, { density: 300 }).resize(inner, inner, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .extend({ top: PAD, bottom: PAD, left: PAD, right: PAD, background: { r: 0, g: 0, b: 0, alpha: 0 } });
  const color = await base.clone().png().toBuffer();
  const mono = await base.clone().grayscale().png().toBuffer();
  return { color, mono };
}

let done = 0;
for (const ch of choices) {
  const req = requests.get(ch.id);
  if (!req) { console.error(`${ch.id}: заявки нет`); continue; }
  const dir = join(INCOMING, ch.id);
  const cands = JSON.parse(readFileSync(join(dir, 'candidates.json'), 'utf8'));
  const item = typeof ch.pick === 'number' ? cands.items[ch.pick - 1] : null;
  const file = item ? join(dir, item.file) : ch.pick;
  if (!file || !existsSync(file)) { console.error(`${ch.id}: файл кандидата не найден`); continue; }
  const buf = readFileSync(file);
  const isSvg = file.endsWith('.svg');
  const title = req.family; const desc = `Знак продукта ${req.family} (${req.vendor}); источник: ${item?.source || file}`;
  let colorSvg, monoSvg;
  if (isSvg) {
    // Вектор: содержимое кладём в группу, вписанную в холст через вложенный svg.
    const src = buf.toString('utf8').replace(/<\?xml[^>]*>/, '').replace(/<!DOCTYPE[^>]*>/i, '').trim();
    // У корневого <svg> снимаем свои x/y/width/height (иначе атрибут задаётся
    // дважды и XML не разбирается — иконки Marketplace несут width/height);
    // без viewBox выводим его из исходных размеров, чтобы знак вписался в холст.
    const nested = src.replace(/<svg\b([^>]*)>/, (_m, attrs) => {
      const w = /\bwidth="([\d.]+)(?:px)?"/.exec(attrs)?.[1];
      const h = /\bheight="([\d.]+)(?:px)?"/.exec(attrs)?.[1];
      let rest = attrs.replace(/\s(?:x|y|width|height|preserveAspectRatio)="[^"]*"/g, '');
      // Инлайновый style корня (width: 1em; height: 1em у иконок Marketplace)
      // перекрывает атрибуты размера — объявления размера из него снимаем.
      rest = rest.replace(/\sstyle="([^"]*)"/, (_s, css) => {
        const kept = css.split(';').map((d) => d.trim()).filter((d) => d && !/^(width|height|min-width|min-height|max-width|max-height)\s*:/i.test(d));
        return kept.length ? ` style="${kept.join('; ')}"` : '';
      });
      if (!/\bviewBox=/.test(rest) && w && h) rest += ` viewBox="0 0 ${w} ${h}"`;
      return `<svg x="${PAD}" y="${PAD}" width="${SIZE - PAD * 2}" height="${SIZE - PAD * 2}" preserveAspectRatio="xMidYMid meet"${rest}>`;
    });
    colorSvg = wrapSvg(ch.id, title, desc, nested);
    // Монохром векторного знака — растеризация и обесцвечивание: перекрашивать
    // заливки внутри чужого SVG ненадёжно (градиенты, маски, стили).
    const { mono } = await rasterToPngs(await sharp(Buffer.from(colorSvg), { density: 300 }).png().toBuffer());
    monoSvg = wrapSvg(ch.id, title, desc, `<image x="0" y="0" width="${SIZE}" height="${SIZE}" href="data:image/png;base64,${mono.toString('base64')}"/>`);
  } else {
    const { color, mono } = await rasterToPngs(buf);
    colorSvg = wrapSvg(ch.id, title, desc, `<image x="0" y="0" width="${SIZE}" height="${SIZE}" href="data:image/png;base64,${color.toString('base64')}"/>`);
    monoSvg = wrapSvg(ch.id, title, desc, `<image x="0" y="0" width="${SIZE}" height="${SIZE}" href="data:image/png;base64,${mono.toString('base64')}"/>`);
  }
  writeFileSync(join(PACK, 'color', `${ch.id}.svg`), colorSvg);
  writeFileSync(join(PACK, 'mono', `${ch.id}.svg`), monoSvg);
  for (const slug of req.slugs) map[slug] = ch.id;
  const entry = {
    icon_id: ch.id, title: req.family, used_by_count: req.slugs.length, vendors: req.vendor,
    sample_products: req.skus.slice(0, 3).join('; '),
    source_url: item?.source || file, source_kind: item?.kind === 'jetbrains-marketplace' ? 'JetBrains Marketplace publisher-provided plugin icon'
      : item?.kind === 'official' ? 'Official product mark from vendor site' : 'Product mark picked from image search (Google CSE), owner site preferred',
    source_owner: req.vendor, source_format: isSvg ? 'svg' : 'raster embedded in svg',
    rights_note: 'Trademark and copyright remain with the vendor; used to identify the product in the catalog.',
    picked_on: new Date().toISOString().slice(0, 10), picked_by: 'session',
    svg_color: `svg/color/${ch.id}__color.svg`, svg_mono: `svg/mono/${ch.id}__mono.svg`,
  };
  const i = manifest.findIndex((e) => e.icon_id === ch.id);
  if (i >= 0) manifest[i] = entry; else manifest.push(entry);
  done++;
  console.log(`${ch.id}: ${isSvg ? 'вектор' : 'растр'} ← ${item?.source || file} (${req.slugs.length} поз.)`);
}
writeFileSync(MAP, JSON.stringify(Object.fromEntries(Object.entries(map).sort()), null, 1) + '\n');
writeFileSync(MANIFEST, JSON.stringify(manifest, null, 2) + '\n');
console.log(`готово: ${done} знаков; карта ${Object.keys(map).length} позиций`);
