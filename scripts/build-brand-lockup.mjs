#!/usr/bin/env node
/**
 * Пересборка файлов логотипа-локапа из мастер-PNG.
 *
 * Зачем скрипт, а не разовая перекодировка: файлов четыре, они должны
 * готовиться одинаково, и при любой правке мастера их надо пересобрать одной
 * командой — иначе ширины разъедутся по качеству, как это уже случилось
 * (05.09.2026 замер PageSpeed показал разное отклонение у соседних ширин).
 *
 * Почему палитра. В локапе 68 % пикселей прозрачны, и вес файла держит не
 * разрешение, а альфа-канал: обычное сжатие WebP с потерями его почти не
 * трогает и даёт файл не легче нынешнего. Квантование палитры сжимает и цвет,
 * и альфу разом. Замер 13.09.2026 по четырём ширинам: файл становится на
 * 26–49 % легче и при этом ближе к мастеру, чем лежавший в репозитории.
 *
 * Палитра 256, а не 32: вариант с 32 цветами весит ещё впятеро меньше, но по
 * попиксельному отклонению от мастера уступает нынешнему файлу, а это
 * фирменный знак. Решение руководителя 13.09.2026 — брать тот вариант,
 * который лучше нынешнего по обоим показателям сразу.
 *
 * Запуск: node scripts/build-brand-lockup.mjs
 * Результат: src/assets/brand/bizsoft-logo-lockup-<ширина>.webp
 */
import sharp from 'sharp';
import { writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const MASTER = resolve(ROOT, 'src/assets/brand/bizsoft-logo-lockup.png');
const OUT_DIR = resolve(ROOT, 'src/assets/brand');

/** Ширины из srcset компонента SiteLogo: 1x, шаг под телефон, 1.5x, 2x. */
export const WIDTHS = [256, 320, 384, 512];
/** Цветов в палитре: больше не нужно, меньше — хуже нынешнего файла. */
export const COLOURS = 256;

/** Среднее отклонение канала от мастера той же ширины, поверх белого. */
export async function deviation(buf, width) {
  const ref = await sharp(MASTER).resize({ width, kernel: 'lanczos3' })
    .flatten({ background: '#ffffff' }).raw().toBuffer();
  const got = await sharp(buf).flatten({ background: '#ffffff' }).raw().toBuffer();
  let sum = 0;
  for (let i = 0; i < ref.length; i += 1) sum += Math.abs(ref[i] - got[i]);
  return sum / ref.length;
}

export async function build(width) {
  // Порядок важен: сначала уменьшение (lanczos даёт чистые края текста),
  // затем палитра, затем WebP без потерь — потери поверх палитры только
  // добавили бы вес, размыв ровные заливки.
  const resized = await sharp(MASTER).resize({ width, kernel: 'lanczos3' }).png().toBuffer();
  const quantised = await sharp(resized)
    .png({ palette: true, colours: COLOURS, dither: 0.5, effort: 10 }).toBuffer();
  return sharp(quantised).webp({ lossless: true, effort: 6 }).toBuffer();
}

if (import.meta.url === `file://${process.argv[1]}`) {
  for (const width of WIDTHS) {
    const buf = await build(width);
    const file = resolve(OUT_DIR, `bizsoft-logo-lockup-${width}.webp`);
    // Готовый буфер пишется как есть: пропуск его через sharp.toFile()
    // перекодировал бы WebP настройками по умолчанию и прибавил треть веса.
    writeFileSync(file, buf);
    console.log(`${width}: ${(buf.length / 1024).toFixed(1)} КБ, ` +
                `отклонение от мастера ${(await deviation(buf, width)).toFixed(2)}`);
  }
}
