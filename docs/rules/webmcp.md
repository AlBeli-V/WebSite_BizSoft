# Регулярное правило: новые вендоры/товары/страницы → WebMCP

Внедрено 30.08.2026. На сайте есть WebMCP-слой для AI-агентов
(`src/webmcp/`, эндпоинт `/api/agent/*`, рубильник `PUBLIC_WEBMCP=0`;
архитектура — `docs/webmcp/architecture.md`). Правила:

- Новые товары и вендоры в Directus видны generic-инструментам
  (`search_products`, `get_product`, `get_vendor`, `list_vendor_products`,
  `list_vendors`) автоматически — WebMCP-код под них НЕ пишется.
  Приёмка — чеклист в `docs/vendors-expansion-prompt.md` (раздел 11а).
- Запрещены product-specific инструменты (get_claude и т.п.) и любая
  параллельная база товаров/цен для агентов: единственный источник —
  Directus → `effectivePrice()` → адаптеры `src/webmcp/adapters.ts`.
- Write-инструменты (заявки, КП, заказы) через WebMCP ЗАПРЕЩЕНЫ без
  отдельной команды руководителя и регламента `docs/webmcp/security.md`.
- Информационные и служебные страницы инструментов не получают;
  для новых форм Declarative WebMCP пока не применяется.
- Вызовы инструментов не должны отправлять цели Метрики/GA4 и создавать
  pageviews; `/api/agent/*` — noindex и вне sitemap (смоук стережёт).
- Изменил слой — прогнать `pnpm verify` и `pnpm test:webmcp-browser`.
