/**
 * Переход к покупке из статьи: ссылка-абзац становится блоком, ссылка внутри
 * предложения — нет.
 *
 * Правило — `.claude/skills/bizsoft-content/SKILL.md`, раздел 4б.
 */
import { describe, expect, it } from 'vitest';
import remarkProductCards from '../scripts/marketing/remark-product-cards.mjs';

type Node = { type: string; url?: string; value?: string; children?: Node[] };

function paragraphWithLink(url: string, text: string): Node {
  return { type: 'paragraph', children: [{ type: 'link', url, children: [{ type: 'text', value: text }] }] };
}

function run(children: Node[]): Node {
  const tree: Node = { type: 'root', children };
  (remarkProductCards() as (t: Node) => void)(tree);
  return tree;
}

describe('блок перехода к покупке', () => {
  it('ссылка-абзац на карточку превращается в блок с названием', () => {
    const tree = run([paragraphWithLink('/product/recraft-business', 'Recraft для юрлиц')]);
    const node = tree.children![0];
    expect(node.type).toBe('html');
    expect(node.value).toContain('class="product-cta"');
    expect(node.value).toContain('href="/product/recraft-business"');
    expect(node.value).toContain('Recraft для юрлиц');
    expect(node.value).toContain('Карточка товара');
  });

  it('ссылка на раздел производителя подписана иначе', () => {
    const tree = run([paragraphWithLink('/vendors/adobe', 'Adobe')]);
    expect(tree.children![0].value).toContain('Раздел производителя');
  });

  it('цены в блоке нет: статья собирается заранее, цена считается по курсу', () => {
    const tree = run([paragraphWithLink('/product/recraft-business', 'Recraft')]);
    expect(tree.children![0].value).not.toMatch(/[₽]|руб/);
  });

  it('ссылка внутри предложения остаётся ссылкой', () => {
    const tree = run([{
      type: 'paragraph',
      children: [
        { type: 'text', value: 'подробности — ' },
        { type: 'link', url: '/product/recraft-business', children: [{ type: 'text', value: 'в карточке' }] },
      ],
    }]);
    expect(tree.children![0].type).toBe('paragraph');
  });

  it('чужие и внутренние ссылки других разделов не трогаются', () => {
    const tree = run([
      paragraphWithLink('/blog/kak-kupit-zarubezhnoe-po-dlya-yurlica', 'статья'),
      paragraphWithLink('https://example.com', 'внешняя'),
    ]);
    expect(tree.children!.every((n) => n.type === 'paragraph')).toBe(true);
  });

  it('ссылка без подписи блоком не становится', () => {
    const tree = run([{ type: 'paragraph', children: [{ type: 'link', url: '/product/x', children: [] }] }]);
    expect(tree.children![0].type).toBe('paragraph');
  });

  it('название экранируется: разметка из каталога не ломает страницу', () => {
    const tree = run([paragraphWithLink('/product/x', 'Тариф "Pro" <b>для команд</b>')]);
    expect(tree.children![0].value).toContain('&quot;Pro&quot;');
    expect(tree.children![0].value).toContain('&lt;b&gt;');
  });

  it('блок собирается и внутри вложенных узлов', () => {
    const tree = run([{
      type: 'blockquote',
      children: [paragraphWithLink('/product/recraft-business', 'Recraft')],
    }]);
    expect(tree.children![0].children![0].type).toBe('html');
  });
});
