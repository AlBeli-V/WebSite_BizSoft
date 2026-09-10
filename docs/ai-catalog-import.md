# Runbook: импорт нового AI-каталога в Directus

Пошагово доводит раздел `/catalog/ai` до целевого состояния из
[`ai-catalog-redesign.md`](./ai-catalog-redesign.md). Требует доступа к Directus
(переменные `SITE_URL`, `ADMIN_TOOLS_TOKEN`, `DIRECTUS_URL`, `DIRECTUS_TOKEN` в `.env`).

## Шаг 1. Создать подкатегории (Directus → Collections → categories)

Создать 8 категорий со статусом `published`. Slug — обязателен (по нему работают
роут `/catalog/ai/[sub]` и импорт товаров).

| name | slug | Что положить в intro/meta |
|---|---|---|
| Текстовые AI | `ai-text` | «Корпоративные текстовые AI: ChatGPT Business, Claude Team/Enterprise, Perplexity…» |
| Программирование (AI) | `ai-code` | «AI для команд разработки: GitHub Copilot, Cursor Business…» |
| Изображения (AI) | `ai-image` | «Генеративный AI для изображений: Midjourney, Adobe Firefly, Recraft…» |
| Видео (AI) | `ai-video` | «AI для видео: Runway, HeyGen, Descript…» |
| Аудио (AI) | `ai-audio` | «AI для аудио: ElevenLabs — синтез и клонирование голоса…» |
| Офисная продуктивность (AI) | `ai-office` | «AI для офиса: Microsoft 365 Copilot, Gemini for Workspace, Notion AI, Gamma…» |
| Маркетинг (AI) | `ai-marketing` | «AI для маркетинга: Jasper, Grammarly Business, Canva AI…» |
| Корпоративные AI | `ai-enterprise` | «Enterprise-тарифы с SSO/SCIM/SOC 2…» |

Тексты intro/meta можно взять из `src/data/ai-hub.ts` (`aiSubcategories`).

## Шаг 2. Собрать xlsx и импортировать товары

```bash
pnpm ai:cards           # → out/ai-cards.xlsx (23 карточки из scripts/ai-catalog-cards.json)
pnpm ai:import          # DRY-RUN: покажет create/update и рублёвые цены, ничего не пишет
pnpm ai:import -- --apply   # применить импорт
```

Цена считается автоматически: **годовая цена вендора × 1.9 × курс ЦБ** (`markup_coeff=1.9`,
`base_price` — годовая цена, см. `computePegRub`). Enterprise/custom идут как «Цена по запросу».

## Шаг 3. Перенести действующие AI-карточки в подкатегории

Сменить `category` у существующих товаров:
- ChatGPT Business/Enterprise → `ai-text` (Enterprise дополнительно показать в `ai-enterprise`);
- Midjourney (Standard/Pro/Mega), Recraft (Advanced/Pro/Team/Enterprise) → `ai-image`;
- Runway, HeyGen, Descript → `ai-video`;
- ElevenLabs (Pro/Scale/Business/Enterprise) → `ai-audio`.

## Шаг 4. Снять с публикации потребительские хвосты

Перевести в `draft`/снять `published` и настроить 301 через `old_slugs`:
ChatGPT Plus, ChatGPT Pro, OpenAI API, Midjourney Basic, Descript Hobbyist.

## Шаг 5. Проставить перелинковку товаров

Заполнить `related_products` (≥4 slug) по матрице Этапа 5. Блоки «Сравнения / База знаний /
Категория» на карточке подтягиваются автоматически из `src/data/ai-interlinks.ts` по вендору.

## Шаг 6. Включить витрину флагманов на хабе (опционально)

После импорта карточки существуют по предсказуемым slug (`sku.toLowerCase()`), поэтому можно
вывести `aiFlagships` из `src/data/ai-hub.ts` на `/catalog/ai` без риска 404.

## Проверка

- `/catalog/ai` — плитки подкатегорий, сравнения, сценарии (уже задеплоено).
- `/catalog/ai/text` … `/catalog/ai/marketing` — списки товаров (после шагов 1–3).
- Rich Results Test: Product / FAQPage / BreadcrumbList на карточках и сравнениях.
- `sitemap.xml` — присутствуют `/compare/*`, `/solutions/ai-*`, новые категории и товары.

## Заведение отдельной карточки AI-каталога (после миграции)

Миграция выше — одноразовая. Дальше карточки раздела заводятся и правятся
партиями по одной-двум позициям, без категорий и переносов:

1. **Запись в реестре** `scripts/ai-catalog-cards.json`. Обязательное:
   `name`, `license_type`, `short_desc_ru`, `features_ru`, `billing_note_ru`,
   `base_price` + `currency` (USD или EUR) либо `price_on_request: true`.
   Необязательное: `sku` — готовый SKU вместо `prefix-key` (для карточки,
   которая уже живёт в Directus под «интеграционным» sku: upsert идёт по нему,
   слаг карточки не меняется), `markup_coeff` — свой коэффициент вместо
   общего 1.9, `sort` — своё место в списке раздела (без него позиция получает
   сквозной номер и сдвигает соседей).
2. **Сборка и проверка**: `node scripts/build-vendor-cards.mjs
   scripts/ai-catalog-cards.json out/ai-cards.xlsx --only SKU1,SKU2` — в xlsx
   уедут только перечисленные SKU.
3. **Импорт** — воркфлоу `ops-import-ai-cards` (только с `main`): вход
   `skus` — те же SKU через запятую, `apply=false` для dry-run, затем
   `apply=true`. Вход `relink=true` дозаполняет `related_products` новым
   карточкам по матрице `scripts/ai-catalog-data.py` (у карточек с уже
   заполненным полем ничего не меняется). Отчёт — в issue #22.
4. **SEO-тексты** — `data/seo/product-descriptions.json` + `ops-apply-descriptions`
   (`apply=false`, потом `apply=true`). Запускать ПОСЛЕ импорта: импорт
   кладёт в описание шаблонный текст генератора, партия описаний его
   перекрывает.
5. **Индексация** — проверить карточку в `/sitemap.xml` и заказать переобход
   (`ops-yandex-recrawl`), см. `docs/rules/sitemap-indexing.md`.

### Пара «Standard seat + Premium seat»

У ChatGPT Business, Claude Team и Cursor Business продаются два типа мест с
одинаковыми возможностями рабочего пространства и разными лимитами. Такая пара
— главный источник каннибализации: описания совпадают по построению. Правила:

- **две карточки, не одна**: тип места — различитель в `name` через запятую,
  одинаково у всех вендоров (`Claude Team, Standard seat` и `Claude Team,
  Premium seat`; `ChatGPT Business, Standard seat` и `ChatGPT Business,
  Premium seat`), а не строка в описании;
- **разные тексты** в `data/seo/product-descriptions.json`: у карточки
  Standard seat раздел «когда брать это место», у Premium seat — «кому нужно»
  и чем оно отличается; `meta_title`, `meta_description` и `short_description` уникальны
  (барьер — `tests/catalog-uniqueness.test.ts`);
- **связка вместо конкуренции**: карточки ссылаются друг на друга через
  `related_products`, на лендинге вендора стоят соседними столбцами сравнения,
  а в FAQ есть вопрос «чем место Premium отличается от базового»;
- **слаг действующей карточки не трогаем**: он уже в индексе и в перелинковке,
  переименование названия его не меняет.
