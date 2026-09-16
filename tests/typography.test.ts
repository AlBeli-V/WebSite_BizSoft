/**
 * Типографика сайта — фиксированный набор директив, а не настройка скорости.
 *
 * Шрифт «слетал» дважды, и оба раза причиной была правка @font-face ради
 * баллов PageSpeed, сделанная без сторожа:
 *   04.09.2026 — единый size-adjust 104 % на всех весах запасного семейства:
 *                фолбэк шире реального Raleway, шапка переверстывалась после
 *                свопа, CLS 0,51;
 *   тогда же    — переход на font-display: optional: при пустом кэше браузер
 *                применяет запасной Arial на весь визит, фирменный Raleway и
 *                Prosto One появляются только со второго перехода. Замер
 *                собранного сайта 15.09.2026 (Chromium, холодный кэш,
 *                задержка сети 0/150/400 мс) — Liberation Sans во всех трёх
 *                прогонах.
 *
 * Отсюда правило (docs/rules/typography.md): фирменное начертание видно на
 * каждом визите, включая первый. Тест стережёт именно директивы — состав
 * @font-face, метрики запасных семейств, стеки токенов и отсутствие
 * сторонних шрифтов в компонентах. Любая их правка должна быть осознанной:
 * тест придётся менять вместе с кодом, и в правило пойдёт строка о том,
 * почему.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

const ROOT = resolve(__dirname, '..');
const CSS = readFileSync(resolve(ROOT, 'src/styles/global.css'), 'utf8');

/** Блок @font-face по семейству и (для фолбэков) диапазону весов. */
function faces(family: string): string[] {
  return [...CSS.matchAll(/@font-face\s*\{([^}]*)\}/g)]
    .map((m) => m[1])
    .filter((body) => new RegExp(`font-family:\\s*'${family}'`).test(body));
}

describe('фирменные шрифты', () => {
  it('Raleway и Prosto One подключены двумя self-hosted woff2', () => {
    const raleway = faces('Raleway');
    const prosto = faces('Prosto One');
    expect(raleway).toHaveLength(1);
    expect(prosto).toHaveLength(1);
    expect(raleway[0]).toContain("url('../assets/fonts/raleway-var.woff2') format('woff2')");
    expect(prosto[0]).toContain("url('../assets/fonts/prosto-one.woff2') format('woff2')");
    // Вариативная ось закрывает все начертания сайта одним файлом.
    expect(raleway[0]).toMatch(/font-weight:\s*100 900/);
    for (const file of ['src/assets/fonts/raleway-var.woff2', 'src/assets/fonts/prosto-one.woff2']) {
      expect(existsSync(resolve(ROOT, file)), `нет файла ${file}`).toBe(true);
    }
  });

  it('оба файла отдаются с font-display: swap', () => {
    // optional = фирменный шрифт только при попадании в кэш, то есть «слетает»
    // на каждом первом визите; block = невидимый текст. Правило требует swap.
    for (const [name, body] of [['Raleway', faces('Raleway')[0]], ['Prosto One', faces('Prosto One')[0]]] as const) {
      expect(body, `${name}: директива font-display изменена`).toMatch(/font-display:\s*swap/);
    }
    expect(CSS).not.toMatch(/font-display:\s*(optional|block|fallback|auto)/);
  });

  it('шрифты не подгружаются со стороннего CDN', () => {
    expect(CSS).not.toMatch(/fonts\.googleapis\.com|fonts\.gstatic\.com|@import\s+url\(/);
  });
});

describe('метрические фолбэки', () => {
  // Метрики woff2 (fontkit, em 1000): Raleway ascent 940, descent 234;
  // Prosto One ascent 940, descent 295. Переопределения считаются как
  // метрика / size-adjust — именно поэтому своп не двигает раскладку.
  const RALEWAY_FALLBACK = [
    { weight: '100 449', size: '102.7%', ascent: '91.5%', descent: '22.8%' },
    { weight: '450 549', size: '103.7%', ascent: '90.6%', descent: '22.6%' },
    { weight: '550 649', size: '98.9%', ascent: '95%', descent: '23.7%' },
    { weight: '650 749', size: '100.2%', ascent: '93.8%', descent: '23.4%' },
    { weight: '750 950', size: '93.7%', ascent: '100.3%', descent: '25%' },
  ];

  it('Raleway-fallback объявлен по диапазонам весов со своим size-adjust', () => {
    const bodies = faces('Raleway-fallback');
    expect(bodies).toHaveLength(RALEWAY_FALLBACK.length);
    for (const m of RALEWAY_FALLBACK) {
      const body = bodies.find((b) => new RegExp(`font-weight:\\s*${m.weight}`).test(b));
      expect(body, `нет фолбэка для весов ${m.weight}`).toBeTruthy();
      expect(body, `size-adjust для весов ${m.weight}`).toContain(`size-adjust: ${m.size}`);
      expect(body, `ascent-override для весов ${m.weight}`).toContain(`ascent-override: ${m.ascent}`);
      expect(body, `descent-override для весов ${m.weight}`).toContain(`descent-override: ${m.descent}`);
      expect(body).toContain('line-gap-override: 0%');
    }
  });

  it('Prosto-One-fallback подогнан под дисплейный шрифт', () => {
    const body = faces('Prosto-One-fallback')[0];
    expect(body).toBeTruthy();
    expect(body).toContain('size-adjust: 124%');
    expect(body).toContain('ascent-override: 75.8%');
    expect(body).toContain('descent-override: 23.8%');
  });

  it('оба фолбэка берут локальный системный шрифт, а не файл', () => {
    for (const body of [...faces('Raleway-fallback'), ...faces('Prosto-One-fallback')]) {
      expect(body).toContain("local('Arial')");
      expect(body).not.toContain('url(');
    }
  });
});

describe('токены типографики', () => {
  const token = (name: string) => CSS.match(new RegExp(`--font-${name}:\\s*([^;]+);`))?.[1].trim();

  it('--font-sans начинается с Raleway и его метрического фолбэка', () => {
    const v = token('sans');
    expect(v).toBeTruthy();
    expect(v!.startsWith("'Raleway', 'Raleway-fallback'"), `--font-sans: ${v}`).toBe(true);
  });

  it('--font-display начинается с Prosto One и его метрического фолбэка', () => {
    const v = token('display');
    expect(v).toBeTruthy();
    expect(v!.startsWith("'Prosto One', 'Prosto-One-fallback'"), `--font-display: ${v}`).toBe(true);
  });

  it('текст страницы идёт --font-sans, заголовки — --font-display', () => {
    expect(CSS).toMatch(/html\s*\{[^}]*font-family:\s*var\(--font-sans\)/s);
    expect(CSS).toMatch(/h1,\s*\n?\s*h2,\s*\n?\s*h3,\s*\n?\s*h4\s*\{[^}]*font-family:\s*var\(--font-display\)/s);
  });
});

describe('страницы не заводят своих шрифтов', () => {
  function walk(dir: string, out: string[] = []): string[] {
    for (const name of readdirSync(dir)) {
      const full = join(dir, name);
      if (statSync(full).isDirectory()) walk(full, out);
      else if (full.endsWith('.astro')) out.push(full);
    }
    return out;
  }

  // Исключения — по одному, с причиной:
  //   ui-monospace в шапке — надписи-рубрики выпадающих меню (моноширинный
  //     набор прописными, решение по композиции шапки);
  //   qa-audit-* — внутренние страницы приёмки графики, вне витрины.
  const ALLOWED = new Set(['src/components/Header.astro', 'src/pages/qa-audit-cards.astro', 'src/pages/qa-audit-icons.astro']);

  it('font-family в разметке — только через токены', () => {
    const bad: string[] = [];
    for (const file of walk(resolve(ROOT, 'src'))) {
      const rel = file.slice(ROOT.length + 1);
      if (ALLOWED.has(rel)) continue;
      readFileSync(file, 'utf8').split('\n').forEach((line, i) => {
        const m = line.match(/font-family:\s*([^;}"']+)/);
        if (m && !m[1].includes('var(--font-')) bad.push(`${rel}:${i + 1} — font-family: ${m[1].trim()}`);
      });
    }
    expect(bad, `свой шрифт мимо токенов:\n${bad.join('\n')}`).toEqual([]);
  });
});

describe('шрифты писем', () => {
  it('файлы, на которые ссылается вёрстка письма, лежат в public/fonts', () => {
    const layout = readFileSync(resolve(ROOT, 'src/lib/email/layout.ts'), 'utf8');
    expect(layout).toContain('/fonts/raleway-${subset}-${w}-normal.woff2');
    for (const w of ['400', '700']) {
      for (const subset of ['cyrillic', 'latin']) {
        const file = `public/fonts/raleway-${subset}-${w}-normal.woff2`;
        expect(existsSync(resolve(ROOT, file)), `нет файла ${file}`).toBe(true);
      }
    }
  });
});
