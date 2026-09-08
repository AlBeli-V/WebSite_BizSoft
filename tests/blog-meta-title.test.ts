// Отдельный заголовок статьи для выдачи (MONEY-002, 08.09.2026).
//
// До этой правки `title` статьи рендерился сразу в трёх местах: <title>, <h1>
// и хлебные крошки. Значит, на 45 статьях блога сниппет-эксперимент был
// невозможен в принципе: правка заголовка под запрос меняла саму страницу, и
// вывод о тексте в выдаче нельзя было отделить от вывода об изменении
// страницы. Партия MONEY-A2 из-за этого ограничилась правкой description.
//
// Тест держит разделение: <title> берёт metaTitle, всё остальное — title.
// Он же ловит обратную ошибку — если кто-то подставит metaTitle в <h1> или в
// разметку, разделение исчезнет молча.
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(__dirname, '..');
const template = readFileSync(resolve(root, 'src/pages/blog/[slug].astro'), 'utf8');
const schema = readFileSync(resolve(root, 'src/content.config.ts'), 'utf8');
const postsDir = resolve(root, 'src/content/blog');

describe('мета-заголовок статьи отделён от заголовка страницы', () => {
  it('поле metaTitle есть в схеме и необязательно', () => {
    expect(schema).toMatch(/metaTitle:\s*z\.string\(\)\.optional\(\)/);
  });

  it('<title> берёт metaTitle, если он задан', () => {
    expect(template).toMatch(/title=\{d\.metaTitle \|\| d\.title\}/);
  });

  it('H1, хлебные крошки и разметка продолжают брать title статьи', () => {
    expect(template).toMatch(/<h1>\{d\.title\}<\/h1>/);
    expect(template).toMatch(/name: d\.title, url: `\/blog\/\$\{post\.id\}`/);
    expect(template).toMatch(/headline: d\.title,/);
    // metaTitle нигде, кроме <title>: иначе разделение исчезает.
    expect(template.match(/d\.metaTitle/g) ?? []).toHaveLength(1);
  });

  it('поле пока не задано ни одной статье — выкат ничего не сдвигает', () => {
    // Партии MONEY-A1/A2 и snippets-10-expand считаются до 06.10 и 30.09.
    // Первое использование поля обязано быть отдельным экспериментом со своей
    // датой, а не побочным следствием этой правки.
    const used = readdirSync(postsDir)
      .filter((f) => f.endsWith('.md'))
      .filter((f) => /^metaTitle:/m.test(readFileSync(resolve(postsDir, f), 'utf8')));
    expect(used).toEqual([]);
  });
});
