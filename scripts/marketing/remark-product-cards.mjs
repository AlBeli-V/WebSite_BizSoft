/**
 * Переход к покупке из статьи: ссылка-абзац превращается в оформленный блок.
 *
 * Зачем. Читатель, дочитавший до места, где ему понятно, что покупать, должен
 * попасть на карточку отсюда, а не из подвала статьи. Компонент в текст
 * markdown вставить нельзя — MDX в проекте нет и заводить его ради одного
 * блока незачем, — поэтому блок собирается из того, что автор уже пишет:
 * обычной ссылки, стоящей отдельным абзацем.
 *
 *     [Recraft для юридических лиц](/product/recraft-business)
 *
 * Ссылка внутри предложения остаётся ссылкой: блок посреди фразы разорвал бы
 * чтение. Преобразуется только абзац, который целиком состоит из одной ссылки
 * на карточку товара или на раздел производителя.
 *
 * Цены в блоке нет намеренно. Страница статьи собирается заранее, а цена
 * считается по курсу ЦБ на момент запроса: любое число, вшитое в сборку,
 * устареет молча и тем вернее, чем лучше работает статья.
 */

const KINDS = [
  { prefix: '/product/', label: 'Карточка товара', go: 'Состав, срок и расчёт количества' },
  { prefix: '/vendors/', label: 'Раздел производителя', go: 'Тарифы и порядок поставки' },
];

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Текст ссылки: у автора это название товара, оно же заголовок блока. */
function linkText(node) {
  return (node.children || [])
    .map((child) => (child.type === 'text' ? child.value
      : child.children ? linkText(child) : ''))
    .join('')
    .trim();
}

function cardHtml(url, name, kind) {
  return [
    `<a class="product-cta" href="${escapeHtml(url)}" data-kind="${kind.prefix.replace(/\//g, '')}">`,
    `<span class="product-cta__label">${kind.label}</span>`,
    `<span class="product-cta__name">${escapeHtml(name)}</span>`,
    `<span class="product-cta__go">${kind.go}</span>`,
    '</a>',
  ].join('');
}

export default function remarkProductCards() {
  return (tree) => {
    const walk = (node) => {
      if (!node || !Array.isArray(node.children)) return;
      node.children.forEach((child, index) => {
        if (child.type === 'paragraph'
            && child.children?.length === 1
            && child.children[0].type === 'link') {
          const link = child.children[0];
          const kind = KINDS.find((k) => String(link.url || '').startsWith(k.prefix));
          const name = linkText(link);
          // Ссылка без подписи блоком не становится: заголовок брать неоткуда,
          // и «тут» на месте названия товара выглядит хуже обычной ссылки.
          if (kind && name) {
            node.children[index] = { type: 'html', value: cardHtml(link.url, name, kind) };
            return;
          }
        }
        walk(child);
      });
    };
    walk(tree);
  };
}
