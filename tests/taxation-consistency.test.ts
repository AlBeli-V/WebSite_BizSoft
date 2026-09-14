/**
 * Согласованность текстов о налоге.
 *
 * С 01.01.2026 порог освобождения от НДС на УСН снижен до 20 млн ₽ дохода за
 * предыдущий год (ст. 145 НК РФ), оборот его превысил, и продавец применяет
 * пониженную ставку 5% (п. 8 ст. 164 НК РФ).
 *
 * До этой правки на сайте одновременно жили «в т.ч. НДС 5%» на карточке товара
 * и «если применяется спецрежим, счёт-фактура обычно не выставляется» в блоге.
 * Клиент читал второе и делал вывод, что вычета не будет, — то есть текст
 * сайта работал против собственного предложения. Проверка нужна потому, что
 * FAQ вендоров генерируется из JSON: одна правка шаблона вернёт всё назад.
 */
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { taxation } from '../src/config/site';
import { cardParams } from '../src/lib/card-params';

const ROOT = resolve(__dirname, '..');

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, name.name);
    if (name.isDirectory()) walk(full, out);
    else if (/\.(ts|astro|md|json)$/.test(name.name)) out.push(full);
  }
  return out;
}

/** Тексты, которые видит клиент: страницы, данные карточек, статьи, FAQ. */
const contentFiles = [
  ...walk(resolve(ROOT, 'src/data')),
  ...walk(resolve(ROOT, 'src/components')),
  ...walk(resolve(ROOT, 'src/content')),
  ...walk(resolve(ROOT, 'scripts/content')),
];

describe('налоговый режим в текстах сайта', () => {
  it('ставка задана одним источником', () => {
    expect(taxation.vatPercent).toBe(5);
    expect(taxation.since).toBe('2026-01-01');
  });

  it('нигде не сказано, что мы не платим НДС', () => {
    // Формулировка была верна до 2026 года и стала прямой дезинформацией:
    // она отговаривает покупателя от сделки, обещая отсутствие вычета.
    const guilty = contentFiles.filter((f) => {
      const src = readFileSync(f, 'utf8');
      return /не является плательщиком НДС|при спецрежиме.{0,40}не выставля|НДС не облагается|применяется спецрежим.{0,60}не выставля/i.test(src);
    });
    expect(guilty.map((f) => f.replace(ROOT, ''))).toEqual([]);
  });

  it('статья о закрывающих документах говорит про вычет', () => {
    const src = readFileSync(
      resolve(ROOT, 'src/content/blog/zakryvayushchie-dokumenty-na-po.md'), 'utf8');
    expect(src).toMatch(/принимает\w*(\s+\S+){0,3}\s+к вычету/);
    expect(src).toContain('УПД');
    expect(src).toContain('5%');
  });

  it('ответ про документы для бухгалтерии называет выделенный НДС', () => {
    // Человек, задавший этот вопрос, как раз и решает, подходим ли мы его
    // бухгалтерии. Умолчать о налоге здесь — потерять сделку молча.
    const files = walk(resolve(ROOT, 'scripts/content'));
    const answers: string[] = [];
    for (const f of files) {
      const data = JSON.parse(readFileSync(f, 'utf8'));
      for (const item of data.faq || []) {
        if (/документ/i.test(item.q) && /бухгалтери/i.test(item.q)) answers.push(item.a);
      }
    }
    expect(answers.length).toBeGreaterThan(10);
    const silent = answers.filter((a) => !/НДС/.test(a));
    expect(silent).toEqual([]);
  });

  it('карточка товара называет налог включённым в цену, а не добавленным сверху', () => {
    // Постановка руководителя 14.09.2026: отдельного пояснения под строкой
    // НДС в параметрах нет — таблица параметров говорит значениями. Смысл
    // «налог уже в цене» при этом обязан звучать, иначе покупатель снова
    // прочтёт одну цифру и решит, что платит сверху (разбор 12.09.2026).
    // Развёрнутый ответ про вычет остался там, куда за ним и идут: в статье о
    // закрывающих документах и в ответах «какие документы для бухгалтерии» —
    // обе проверки выше в этом же файле.
    const src = readFileSync(resolve(ROOT, 'src/pages/product/[slug].astro'), 'utf8');
    const row = cardParams({
      vendorLegal: 'OpenAI, Inc.', category: 'Текстовые AI', planShort: 'Командный',
      term: '1 год', sku: 'OPAI-LIC-CHATGPTBUS-TEAM-1Y-USER', qtyLabel: 'Рабочих мест',
      minQty: 2, vat: taxation.vatPercent,
    }).find((r) => r.key === 'НДС');
    expect(row?.value).toBe(`${taxation.vatPercent}% (включено в стоимость)`);
    // И в блоке цены: «в том числе», а не «плюс».
    expect(src).toContain('в том числе НДС {vat}%');
    expect(src).not.toMatch(/НДС\s*сверху|плюс\s*НДС/i);
  });
});
