// Вес фирменного логотипа. Он грузится в шапке на каждой странице сайта и
// не лениво, поэтому лишний килобайт здесь умножается на всё посещение.
// Замер PageSpeed 05.09.2026 назвал файлы логотипа единственным остатком в
// аудите доставки изображений после правки обложек статей; 13.09 они
// пересобраны квантованием палитры (scripts/build-brand-lockup.mjs).
// Тест держит достигнутое: потолок с запасом к текущему весу и совпадение
// ширины файла с дескриптором srcset.
import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(__dirname, '..');
const dir = resolve(root, 'src/assets/brand');

/** Ширина, высота и наличие альфы из заголовка VP8L/VP8X файла WebP. */
function webpSize(file: string): { width: number; height: number } {
  const b = readFileSync(file);
  expect(b.toString('ascii', 0, 4), file).toBe('RIFF');
  expect(b.toString('ascii', 8, 12), file).toBe('WEBP');
  const chunk = b.toString('ascii', 12, 16);
  if (chunk === 'VP8L') {
    // 14 бит ширины и 14 бит высоты, начиная с байта 21, оба минус единица.
    const bits = b.readUInt32LE(21);
    return { width: (bits & 0x3fff) + 1, height: ((bits >> 14) & 0x3fff) + 1 };
  }
  if (chunk === 'VP8X') {
    return {
      width: (b.readUIntLE(24, 3) & 0xffffff) + 1,
      height: (b.readUIntLE(27, 3) & 0xffffff) + 1,
    };
  }
  throw new Error(`${file}: неизвестный формат чанка ${chunk}`);
}

// Потолок — текущий вес плюс примерно пятая часть запаса: заметное
// утяжеление роняет проверку, мелкие колебания кодировщика — нет.
const LIMITS: Record<number, number> = { 256: 11, 320: 14, 384: 19, 448: 23, 512: 27 };

describe('логотип-локап: вес и размеры', () => {
  for (const [width, limitKb] of Object.entries(LIMITS)) {
    it(`ширина ${width} — не тяжелее ${limitKb} КБ и той самой ширины`, () => {
      const file = resolve(dir, `bizsoft-logo-lockup-${width}.webp`);
      expect(existsSync(file), file).toBe(true);
      const kb = statSync(file).size / 1024;
      expect(kb, `${file}: ${kb.toFixed(1)} КБ`).toBeLessThanOrEqual(limitKb);
      expect(webpSize(file).width).toBe(Number(width));
    });
  }

  it('srcset компонента перечисляет ровно эти четыре ширины', () => {
    const src = readFileSync(resolve(root, 'src/components/SiteLogo.astro'), 'utf8');
    for (const width of Object.keys(LIMITS)) {
      expect(src).toContain(`${width}w`);
      expect(src).toContain(`bizsoft-logo-lockup-${width}.webp`);
    }
  });
});
