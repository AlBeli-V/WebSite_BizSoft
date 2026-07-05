# Реорганизация раздела AI-каталога (`/catalog/ai`)

Стратегия и техническая архитектура переработки AI-раздела biz-soft.pro под цели:
**SEO-трафик · GEO / AI Search видимость · B2B-конверсия · продажа только официальных
годовых корпоративных лицензий и подписок.**

> Роли автора документа: Senior UX Architect · Senior SEO Architect · GEO SEO Specialist ·
> Enterprise B2B Product Manager.

Документ описывает целевое состояние и содержит готовые к внедрению артефакты:
- `scripts/ai-catalog-cards.json` — импортируемые карточки новых B2B-продуктов (формат `build-vendor-cards.mjs`);
- обновлённый `scripts/build-vendor-cards.mjs` — тексты/аудитории/ключевики для новых AI-подкатегорий.

Каталог управляется данными из **Directus** (страница `/catalog/[segment]` рендерит товары
категории; карточка — `product/[slug].astro`). Поэтому «построить каталог» = завести категории
и товары в Directus + внести правки в шаблоны/перелинковку. Всё, что требует записи в БД,
собрано в разделе **«Чек-лист внедрения»**.

---

## Метод и источники (важно для Этапа 1)

Проверка лицензирования проведена **только по официальным сайтам производителей** (pricing/
enterprise/help-центры) по состоянию на 2026 г. Ключевой вывод:

> **Ни один из рассмотренных сервисов не продаётся «только помесячно».** У всех есть годовой или
> законтрактованный вариант. Поэтому формальное правило «нет года → удалить» отсекает не
> вендоров, а **отдельные потребительские тарифы** внутри карточек (индивидуальные месячные
> подписки и usage-based биллинг), которые не являются корпоративной годовой лицензией.

Правило удаления в этом документе применяется так: **из B2B-каталога убираются тарифы, которые
(а) индивидуальные и помесячные, либо (б) usage-based без годового обязательства.** Корпоративные
Team/Business/Enterprise-тарифы остаются.

## Ценообразование (единая формула)

> **Рублёвая цена на сайте = годовая цена у вендора × 1.9 × официальный курс (ЦБ РФ).**

Это ровно то, что вычисляет `computePegRub` в `src/lib/pricing.ts`
(`base × rate × markup_coeff`), где `markup_coeff = 1.9`, `rate` — текущий официальный курс
валюты, а `base` — **годовая** цена вендора за место/пользователя. Поэтому в
`scripts/ai-catalog-cards.json` поле `base_price` хранит **годовую** цену (USD/год за место), а
`billing_note_ru` — «за место/пользователя в год». Тарифы с индивидуальным годовым контрактом
(Enterprise/custom) идут как `price_on_request` — цена подтверждается в счёте. Итоговая цена —
ориентировочная, окончательная фиксируется в счёте по курсу ЦБ на дату выставления.

---

# ЭТАП 1. Аудит текущего каталога

Текущий `/catalog/ai` (Directus, `category = ai`) — 7 вендоров, 31 карточка.
Матрица официального лицензирования (Y = есть, — = нет, custom = по запросу):

| Продукт (тариф) | Годовой тариф | Корп. покупка | B2B | Enterprise-лиц. | Team-лиц. | Вердикт Этапа 1 |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **ChatGPT Plus** (OpenAI, $20/мес, individual) | — (помесячно) | — | — | — | — | **Удалить** — потребительский месячный тариф |
| **ChatGPT Pro** (OpenAI, $200/мес, individual) | — (помесячно) | — | — | — | — | **Удалить** — потребительский месячный тариф |
| **ChatGPT Business** (ex-Team, $20/польз./год) | Y ($240/год) | Y | Y | — | Y (от 2 мест) | **Оставить** |
| **ChatGPT Enterprise** | Y (контракт) | Y | Y | Y | Y | **Оставить** |
| **OpenAI API** (оплата по использованию) | — (usage-based) | Y | Y | — | — | **Удалить из каталога** — нет годовой лицензии (вынести в сноску/лид-форму) |
| **Midjourney** Basic | Y (−20% год) | частично (50+) | частично | — | — | **Удалить** — минимальный индивидуальный тариф |
| **Midjourney** Standard / Pro / Mega | Y (−20% год) | 50+ по счёту | частично | — | — | **Оставить** (Pro/Mega — Stealth, коммерч. использование) |
| **Recraft** Basic | Y | Y | — | — | — | **Объединить** — свернуть в Advanced |
| **Recraft** Advanced / Pro / Team / Enterprise | Y | Y | Y | Y | Y (Team, от 3 мест) | **Оставить** |
| **Runway** Standard / Pro / Max / Enterprise | Y | Y | Y | Y | Y (за место) | **Оставить** |
| **ElevenLabs** Starter / Creator | Y | Y | — | — | — | **Объединить** — свести к Creator как входному |
| **ElevenLabs** Pro / Scale / Business / Enterprise | Y (~2 мес бесплатно) | Y | Y | Y | Y (Scale 3, Business 10 мест) | **Оставить** |
| **Descript** Hobbyist | Y | Y | — | — | — | **Удалить** — индивидуальный входной |
| **Descript** Creator / Business / Enterprise | Y | Y | Y | Y | Y (за место) | **Оставить** |
| **HeyGen** Creator | Y | Y | — | — | — | **Объединить** — свернуть в Pro |
| **HeyGen** Pro / Business / Enterprise | Y | Y | Y | Y | Y (Business + места) | **Оставить** |

**Итог аудита:** вендоры остаются все 7, но каталог «худеет» на потребительских хвостах
(ChatGPT Plus/Pro, OpenAI API, Midjourney Basic, Descript Hobbyist) и консолидирует входные тарифы.
Главная проблема текущего раздела — **не переизбыток тарифов, а отсутствие флагманских
B2B-сервисов**, которые формируют спрос и SEO/GEO-видимость (Claude, Copilot, Gemini, Perplexity,
Cursor и др.). Их добавление — предмет Этапа 2–3.

---

# ЭТАП 2. Новый каталог

## 2.1. Информационная архитектура: хаб + функциональные подкатегории

`/catalog/ai` превращается из плоского списка в **хаб-страницу**:
1. **Верхний блок — «Популярные мировые AI-сервисы»**: витрина флагманов в порядке приоритета
   (ChatGPT Business → Claude Team/Enterprise → Microsoft Copilot → GitHub Copilot Business →
   Gemini Workspace → Perplexity Enterprise → Cursor Business → Midjourney → Adobe Firefly →
   Canva AI → Runway → ElevenLabs → Notion AI → Grammarly Business → Jasper → Gamma).
2. **Плитки функциональных подкатегорий** (каждая — отдельный URL и SEO-кластер).
3. **Кросс-коллекция «Корпоративные AI»** — витрина Enterprise-тарифов (не отдельная таксономия,
   а курируемая подборка; товары уже лежат в функциональных подкатегориях).

### Подкатегории (Directus category · slug · URL)

| Категория | slug | URL | Основные продукты |
|---|---|---|---|
| Текстовые AI | `ai-text` | `/catalog/ai/text` | ChatGPT Business/Enterprise, Claude Team/Enterprise, Perplexity Enterprise |
| Программирование | `ai-code` | `/catalog/ai/code` | GitHub Copilot Business/Enterprise, Cursor Business/Enterprise |
| Изображения | `ai-image` | `/catalog/ai/image` | Midjourney, Adobe Firefly, Recraft |
| Видео | `ai-video` | `/catalog/ai/video` | Runway, HeyGen, Descript |
| Аудио | `ai-audio` | `/catalog/ai/audio` | ElevenLabs |
| Офисная продуктивность | `ai-office` | `/catalog/ai/office` | Microsoft 365 Copilot, Gemini for Workspace, Notion AI, Gamma |
| Маркетинг | `ai-marketing` | `/catalog/ai/marketing` | Jasper, Grammarly Business, Canva AI |
| Корпоративные AI | `ai-enterprise` | `/catalog/ai/enterprise` | *(кросс-коллекция Enterprise-тарифов)* |

> **URL-решение.** Текущий роут — плоский `/catalog/[segment]`. Для вложенности `/catalog/ai/<sub>`
> нужен роут `/catalog/ai/[sub].astro` (или подкатегории как самостоятельные сегменты
> `/catalog/ai-text` без вложенности — быстрее внедрить, но слабее семантически). Рекомендуется
> вложенный вариант с хабом `/catalog/ai` и хлебными крошками `Каталог → AI → <подкатегория>`.
> Обоснование в Этапе 8.

## 2.2. Порядок вывода (приоритет флагманов)

Витрина верхнего блока хаба сортируется полем `sort` (см. `sortBase` в seed-файлах). Задаём
`sort` так, чтобы порядок совпал с приоритетом из брифа. В `scripts/ai-catalog-cards.json`
использован `sortBase: 1400` (ниже действующего OpenAI `sortBase: 1500` — флагманы поднимаются выше).

---

# ЭТАП 3. Решения по каждому продукту (оставить / объединить / удалить / создать)

## 3.1. Действующие продукты

| Продукт | Решение | Обоснование |
|---|---|---|
| ChatGPT Business / Enterprise | **Оставить**, перенести в `ai-text`, Enterprise дублировать в `ai-enterprise` | Ядро спроса, годовые B2B-тарифы |
| ChatGPT Plus / Pro | **Удалить** | Индивидуальные месячные, не B2B-годовые |
| OpenAI API | **Удалить из каталога** | Usage-based, нет годовой лицензии; оставить как lead-форму «Доступ к OpenAI API по счёту» |
| Midjourney Basic | **Удалить** | Минимальный индивидуальный тариф |
| Midjourney Standard/Pro/Mega | **Оставить**, перенести в `ai-image` | Годовой (−20%), Stealth/коммерческое использование |
| Recraft Basic | **Объединить** в Advanced | Убрать шум входного тарифа |
| Recraft Advanced/Pro/Team/Enterprise | **Оставить** → `ai-image` | Есть Team (от 3) и Enterprise |
| Runway (все платные) | **Оставить** → `ai-video` | Годовые, Enterprise annual-only |
| ElevenLabs Starter/Creator | **Объединить** — Creator как входной | Убрать индивидуальный хвост |
| ElevenLabs Pro/Scale/Business/Enterprise | **Оставить** → `ai-audio` | Scale/Business/Enterprise — места, SSO |
| Descript Hobbyist | **Удалить** | Индивидуальный входной |
| Descript Creator/Business/Enterprise | **Оставить** → `ai-video` | Business/Enterprise — пул мест |
| HeyGen Creator | **Объединить** в Pro | Убрать индивидуальный хвост |
| HeyGen Pro/Business/Enterprise | **Оставить** → `ai-video` | Business + места, Enterprise SSO/SCIM |

## 3.2. Новые продукты — **создать** (в `scripts/ai-catalog-cards.json`)

| Продукт | Категория | Тариф(ы) | Годовой / корп. лицензирование (официально) |
|---|---|---|---|
| **Claude Team** (Anthropic) | ai-text | Team, Team Premium | $20/$80 за место/мес при годовой; от 5 мест; данные не обучают |
| **Claude Enterprise** (Anthropic) | ai-text / ai-enterprise | Enterprise | Годовой контракт (custom); SSO, SCIM/JIT, RBAC, audit, HIPAA/BAA; от 20 мест |
| **Perplexity Enterprise Pro** | ai-text | Enterprise Pro | $40/место/мес или $400/место/год; SSO, SOC 2, SCIM (50+), retention |
| **Microsoft 365 Copilot** | ai-office / ai-enterprise | Enterprise add-on | $30/польз./мес при годовой оплате (annual-only); требует базовую лицензию M365 |
| **GitHub Copilot Business** | ai-code | Business | $19/польз./мес; org-политики, SSO, audit, IP-indemnity |
| **GitHub Copilot Enterprise** | ai-code / ai-enterprise | Enterprise | $39/польз./мес; индексация кодовой базы, кастом-модели |
| **Google Gemini for Workspace** | ai-office | Business Standard, Enterprise | Gemini включён в тарифы Workspace; годовой fixed-term; enterprise custom |
| **Cursor Business** | ai-code | Teams (Standard/Premium) | $32/$96 за место/мес при годовой; SSO SAML/OIDC, privacy enforcement, Bugbot |
| **Cursor Enterprise** | ai-code / ai-enterprise | Enterprise | custom (счёт/wire), enterprise-контроль |
| **Adobe Firefly for teams / enterprise** | ai-image | Teams / Enterprise | Годовой; enterprise — индемнификация по IP (custom) |
| **Notion AI** | ai-office | Business / Enterprise | AI включён в Business ($20/польз./год); Enterprise custom (SSO/SCIM/SOC 2) |
| **Grammarly Business** | ai-marketing | Pro / Enterprise | ~$20/чел./мес при годовой; Enterprise custom (SAML SSO, SCIM, SOC 2/ISO) |
| **Jasper** | ai-marketing | Pro / Business | Pro $59/мес при годовой; Business custom (12 мес, SSO, API, Agent Builder) |
| **Gamma** | ai-office | Pro / Business | Годовой (−28%); Business — SSO/SAML, админ-контроль |

## 3.3. **Объединить / кросс-листинг** (без дублирования SKU)

- **Canva AI** — карточки Canva Business/Enterprise уже существуют в каталоге дизайна.
  **Не создавать дубли SKU:** отобразить их в `ai-marketing` через кросс-листинг (доп. категория/
  тег или блок «также в AI-каталоге») + сделать посадочную «Canva AI (Magic Studio) для бизнеса».
- **ChatGPT Enterprise, Claude Enterprise, M365 Copilot, GitHub Copilot Enterprise, Gemini
  Enterprise, Perplexity Enterprise** — основной товар лежит в функциональной подкатегории, а в
  `ai-enterprise` попадает через кросс-коллекцию.

---

# ЭТАП 4. SEO-посадочная страница продукта (обязательная структура)

Шаблон `product/[slug].astro` уже рендерит H1, короткое описание, `features`, `use_cases`, `faq`,
`related_products`, `related_solutions` и Product JSON-LD. Дозаполняем **контент-модель товара в
Directus** по единому каркасу:

| Блок | Источник в Directus / шаблоне | Комментарий |
|---|---|---|
| **H1** | `name` | `<Продукт> — купить для юрлица по счёту` шаблоном на странице |
| **Краткое описание** | `short_description` | 1–2 предложения, вхождение бренда + «для юрлица/по счёту» |
| **Кому подходит** | `for_whom` | список ролей/типов команд |
| **Основные возможности** | `features` | 5–8 пунктов |
| **Преимущества** | `description` (абзац) | акцент на годовой лицензии, закрывающих, ЭДО |
| **Сравнение тарифов** | таблица (новое поле `comparison` или блок в `description`) | как в `scripts/content/*.json → comparison` |
| **Почему через Biz-Soft** | общий партиал | договор, счёт в ₽, ЭДО, курс ЦБ, сопровождение |
| **Сценарии использования** | `use_cases` | 3–4 сценария |
| **FAQ** | `faq` | 5–7 Q/A, каждый — цель для AI Search |
| **Похожие продукты** | `related_products` | ≥4 slug (см. Этап 5) |
| **CTA** | партиал `CTASection` + `QuestionForm` | «Получить КП», «Запросить счёт» |

## 4.1. Обязательная разметка JSON-LD

Все билдеры уже есть в `src/lib/seo.ts` — переиспользуем:

- **Product** — `productSchema(p, {images})` (name, sku, brand, offers, priceCurrency, availability,
  политика возврата/доставки).
- **FAQPage** — `faqSchema(product.faq)` (для AI Search / rich-результатов).
- **BreadcrumbList** — `breadcrumbSchema([...])` (`Каталог → AI → <подкатегория> → <продукт>`).
- **Organization / WebSite** — `organizationSchema()` / `websiteSchema()` (site-wide, в layout).

> **GEO / AI Search.** Для видимости в ответах ИИ-поисковиков (ChatGPT Search, Perplexity, Gemini,
> AI Overviews) ключевые сигналы: (1) **FAQ Schema** с прямыми Q→A формулировками; (2) чёткие
> факты в первом экране (тип лицензии, годовой тариф, «для юрлица по счёту, закрывающие через ЭДО»);
> (3) сравнительные таблицы; (4) внутренняя перелинковка (Этап 5). Формулировки в `short_description`
> и первом Q FAQ пишем как самодостаточные ответы — их цитируют модели.

## 4.2. Пример JSON-LD FAQ (для страницы продукта)

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Можно ли оформить Claude Team на российское юрлицо по счёту?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Да. Biz-Soft оформляет подписку на организацию с оплатой по счёту в рублях и закрывающими документами через ЭДО. Тариф считается за место в год."
      }
    }
  ]
}
```

---

# ЭТАП 5. Карта внутренней перелинковки

Норматив на каждую карточку: **≥4 похожих продукта · 2 статьи базы знаний · 2 сравнения ·
1 категория.**

## 5.1. База знаний (существующая + предлагаемая)

Существуют: `/blog/kak-kupit-zarubezhnoe-po-dlya-yurlica`,
`/blog/zakryvayushchie-dokumenty-na-po`, `/blog/podpiska-napryamuyu-ili-cherez-postavshchika`.

Предложить (AI-специфичные): «Как оформить корпоративную AI-подписку на юрлицо»,
«Enterprise vs Team: чем отличаются корпоративные тарифы AI», «Безопасность данных в корпоративных
AI (SOC 2, обучение на данных, SSO)», «Как выбрать AI-ассистента для команды разработки».

## 5.2. Матрица перелинковки флагманов

| Продукт | 4 похожих | 2 статьи БЗ | 2 сравнения | Категория |
|---|---|---|---|---|
| **ChatGPT Business** | Claude Team, Gemini Workspace, Perplexity Enterprise, Microsoft 365 Copilot | «как оформить AI на юрлицо», «Enterprise vs Team» | ChatGPT vs Claude, ChatGPT vs Gemini | Текстовые AI |
| **Claude Team** | ChatGPT Business, Perplexity Enterprise, Gemini Workspace, Cursor Business | «Enterprise vs Team», «безопасность данных в AI» | Claude vs ChatGPT, Claude vs Gemini | Текстовые AI |
| **Claude Enterprise** | ChatGPT Enterprise, M365 Copilot, Gemini Enterprise, GitHub Copilot Enterprise | «Enterprise vs Team», «безопасность данных в AI» | ChatGPT vs Claude, Copilot vs Gemini | Корпоративные AI |
| **Microsoft 365 Copilot** | Gemini Workspace, ChatGPT Enterprise, Notion AI, Grammarly Business | «AI для бизнеса», «безопасность данных в AI» | Copilot vs Gemini, ChatGPT vs Gemini | Офисная продуктивность |
| **GitHub Copilot Business** | Cursor Business, GitHub Copilot Enterprise, Claude Team, ChatGPT Business | «AI для разработчиков», «Enterprise vs Team» | Cursor vs Copilot, ChatGPT vs Claude | Программирование |
| **Cursor Business** | GitHub Copilot Business, GitHub Copilot Enterprise, Claude Team, ChatGPT Business | «AI для разработчиков», «как оформить AI на юрлицо» | Cursor vs Copilot, ChatGPT vs Claude | Программирование |
| **Gemini for Workspace** | Microsoft 365 Copilot, ChatGPT Business, Notion AI, Perplexity Enterprise | «AI для бизнеса», «безопасность данных в AI» | Copilot vs Gemini, Claude vs Gemini | Офисная продуктивность |
| **Perplexity Enterprise** | ChatGPT Business, Claude Team, Gemini Workspace, Notion AI | «AI для аналитиков», «безопасность данных в AI» | Perplexity vs ChatGPT, ChatGPT vs Claude | Текстовые AI |
| **Midjourney** | Adobe Firefly, Recraft, Runway, Canva AI | «AI для дизайнеров», «как оформить AI на юрлицо» | Midjourney vs Firefly, Midjourney vs Recraft | Изображения |
| **Adobe Firefly** | Midjourney, Recraft, Canva AI, Runway | «AI для дизайнеров», «безопасность/лицензии на контент» | Midjourney vs Firefly, Firefly vs Canva | Изображения |
| **Runway** | HeyGen, Descript, Midjourney, ElevenLabs | «AI для видеопродакшна», «как оформить AI на юрлицо» | Runway vs HeyGen, Midjourney vs Firefly | Видео |
| **ElevenLabs** | Descript, Runway, HeyGen, Notion AI | «AI для контента», «как оформить AI на юрлицо» | ElevenLabs vs Descript, Runway vs HeyGen | Аудио |
| **Notion AI** | Gamma, Microsoft 365 Copilot, Grammarly Business, ChatGPT Business | «AI для бизнеса», «AI для продуктивности» | Notion vs ChatGPT, Copilot vs Gemini | Офисная продуктивность |
| **Grammarly Business** | Jasper, Notion AI, ChatGPT Business, Canva AI | «AI для маркетинга», «AI для продаж» | Grammarly vs Jasper, ChatGPT vs Claude | Маркетинг |
| **Jasper** | Grammarly Business, Canva AI, Notion AI, ChatGPT Business | «AI для маркетинга», «AI для продаж» | Grammarly vs Jasper, Jasper vs ChatGPT | Маркетинг |
| **Gamma** | Notion AI, Canva AI, Microsoft 365 Copilot, Grammarly Business | «AI для бизнеса», «AI для маркетинга» | Gamma vs Canva, Notion vs ChatGPT | Офисная продуктивность |

Реализация: поле `related_products` карточки (slug-и) уже поддержано шаблоном; статьи/сравнения/
категория — фиксированные блоки на странице продукта (партиалы), заполняются по этой матрице.

---

# ЭТАП 6. Страницы сравнения (новый раздел `/compare/`)

Отдельный SEO/GEO-кластер: сравнения — высокочастотные транзакционно-исследовательские запросы и
любимый источник цитирования у AI-поисковиков. Структура страницы: H1 «X vs Y: что выбрать для
бизнеса», TL;DR-вывод (для AI Search), таблица параметров (тарифы, годовая цена, SSO/SOC 2, места,
данные/обучение), «кому X / кому Y», FAQ + **FAQPage/Breadcrumb JSON-LD**, CTA, перелинковка на обе
карточки и категорию.

Приоритетные страницы (v1):

1. `/compare/chatgpt-vs-claude`
2. `/compare/claude-vs-gemini`
3. `/compare/cursor-vs-copilot`
4. `/compare/midjourney-vs-firefly`
5. `/compare/perplexity-vs-chatgpt`
6. `/compare/copilot-vs-gemini`
7. `/compare/chatgpt-vs-gemini`
8. `/compare/runway-vs-heygen`
9. `/compare/grammarly-vs-jasper`
10. `/compare/elevenlabs-vs-descript`
11. `/compare/midjourney-vs-recraft`
12. `/compare/notion-vs-chatgpt`
13. `/compare/gamma-vs-canva`
14. `/compare/firefly-vs-canva`

Реализация: датафайл `src/data/comparisons.ts` (по образцу `src/data/solutions.ts`) +
роут `src/pages/compare/[slug].astro`.

---

# ЭТАП 7. Страницы по сценариям использования (расширение `/solutions/`)

Раздел `/solutions/[industry]` уже существует (`src/data/solutions.ts`). Добавляем сценарные
посадочные под роли/задачи (H1, боли, оффер, подборка AI-продуктов, FAQ + JSON-LD, CTA):

| Сценарий | slug | Ключевые AI-продукты |
|---|---|---|
| AI для разработчиков | `ai-dlya-razrabotchikov` | GitHub Copilot Business/Enterprise, Cursor Business, Claude Team |
| AI для бизнеса | `ai-dlya-biznesa` | ChatGPT Business, Microsoft 365 Copilot, Gemini Workspace, Notion AI |
| AI для маркетинга | `ai-dlya-marketinga` | Jasper, Grammarly Business, Canva AI, Midjourney |
| AI для продаж | `ai-dlya-prodazh` | ChatGPT Business, Grammarly Business, Gamma, Perplexity Enterprise |
| AI для образования | `ai-dlya-obrazovaniya` | ChatGPT Business, Gamma, Claude Team, ElevenLabs |
| AI для дизайнеров | `ai-dlya-dizainerov` | Midjourney, Adobe Firefly, Recraft, Canva AI |
| AI для аналитиков | `ai-dlya-analitikov` | Perplexity Enterprise, ChatGPT Business, Claude Team, Gemini Workspace |
| AI для юристов | `ai-dlya-yuristov` | Claude Enterprise, ChatGPT Enterprise, Perplexity Enterprise |
| AI для бухгалтерии | `ai-dlya-buhgalterii` | Microsoft 365 Copilot, ChatGPT Business, Notion AI |

Каждая сценарная страница ссылается на профильную подкатегорию AI и на 3–4 карточки; карточки, в
свою очередь, ссылаются на сценарии через `related_solutions`.

---

# ЭТАП 8. Итоговая архитектура AI-раздела

## 8.1. Иерархия URL

```
/catalog/ai                         ← ХАБ: витрина флагманов + плитки подкатегорий
├── /catalog/ai/text                ← Текстовые AI
│   ├── /product/chatgpt-business
│   ├── /product/chatgpt-enterprise
│   ├── /product/claude-team
│   ├── /product/claude-enterprise
│   └── /product/perplexity-enterprise
├── /catalog/ai/code                ← Программирование
│   ├── /product/github-copilot-business
│   ├── /product/github-copilot-enterprise
│   ├── /product/cursor-business
│   └── /product/cursor-enterprise
├── /catalog/ai/image               ← Изображения
│   ├── /product/midjourney-*        (Standard/Pro/Mega)
│   ├── /product/adobe-firefly-*     (teams/enterprise)
│   └── /product/recraft-*           (Advanced/Pro/Team/Enterprise)
├── /catalog/ai/video               ← Видео
│   ├── /product/runway-*            /product/heygen-*   /product/descript-*
├── /catalog/ai/audio               ← Аудио
│   └── /product/elevenlabs-*        (Pro/Scale/Business/Enterprise)
├── /catalog/ai/office              ← Офисная продуктивность
│   ├── /product/microsoft-365-copilot
│   ├── /product/gemini-for-workspace-*  /product/notion-ai-*  /product/gamma-*
├── /catalog/ai/marketing           ← Маркетинг
│   ├── /product/jasper-*  /product/grammarly-business  (+ кросс-листинг Canva)
└── /catalog/ai/enterprise          ← Корпоративные AI (кросс-коллекция Enterprise-тарифов)

/compare/<x>-vs-<y>                  ← 14 сравнений (Этап 6)
/solutions/<scenario>               ← 9 сценарных посадочных (Этап 7)
/blog/<ai-kb-articles>              ← база знаний AI (Этап 5)
```

## 8.2. Структура категорий (Directus)
Родитель `ai` (хаб) + 8 подкатегорий (`ai-text`, `ai-code`, `ai-image`, `ai-video`, `ai-audio`,
`ai-office`, `ai-marketing`, `ai-enterprise`), каждая с `meta_title`, `meta_description`, `intro`,
`faqs`. `ai-enterprise` наполняется кросс-листингом.

## 8.3. Структура карточки — см. Этап 4 (каркас + JSON-LD).

## 8.4. Структура перелинковки — см. Этап 5 (норматив 4/2/2/1).

## 8.5. Что создать / удалить / объединить (сводка)

**Создать (товары):** Claude Team, Claude Enterprise, Perplexity Enterprise, Microsoft 365 Copilot,
GitHub Copilot Business, GitHub Copilot Enterprise, Gemini for Workspace (Business/Enterprise),
Cursor Business, Cursor Enterprise, Adobe Firefly (teams/enterprise), Notion AI (Business/Enterprise),
Grammarly Business, Jasper (Pro/Business), Gamma (Pro/Business). → `scripts/ai-catalog-cards.json`.

**Создать (страницы):** хаб `/catalog/ai` + 8 подкатегорий; 14 `/compare/*`; 9 `/solutions/*`;
4 KB-статьи.

**Удалить (карточки):** ChatGPT Plus, ChatGPT Pro, OpenAI API, Midjourney Basic, Descript Hobbyist.

**Объединить:** Recraft Basic→Advanced; ElevenLabs Starter→Creator; HeyGen Creator→Pro;
Canva — кросс-листинг вместо дублей; Enterprise-тарифы — кросс-коллекция `ai-enterprise`.

**Переместить:** все действующие AI-карточки из плоской `ai` в функциональные подкатегории.

---

# Чек-лист внедрения

### A. Данные (Directus — требует доступа к БД)
- [ ] Создать 8 категорий-подразделов (slug/meta/intro/faqs из Этапа 2/8).
- [ ] Собрать xlsx: `node scripts/build-vendor-cards.mjs scripts/ai-catalog-cards.json out/ai-cards.xlsx`.
- [ ] Импорт (dry-run → apply): `node scripts/import-cards.mjs out/ai-cards.xlsx` / `--apply`.
- [ ] Перенести действующие AI-карточки в новые категории; проставить `related_products`/`related_solutions` по Этапу 5.
- [ ] Снять с публикации: ChatGPT Plus/Pro, OpenAI API, Midjourney Basic, Descript Hobbyist (с 301 на подкатегорию/аналог через `old_slugs`).

### B. Шаблоны/страницы (код)
- [x] **Ценообразование** — формула «год × 1.9 × курс» заложена в `scripts/ai-catalog-cards.json` (годовые цены) и совпадает с `computePegRub`.
- [x] **`src/data/comparisons.ts` + `src/pages/compare/[slug].astro`** — 14 страниц сравнения с FAQ/Breadcrumb JSON-LD (собрано, `dist/.../compare/*`).
- [x] **Расширен `src/data/solutions.ts`** — 9 сценарных посадочных (Этап 7).
- [x] **3 KB-статьи** в `src/content/blog/` (оформление AI на юрлицо, Enterprise vs Team, безопасность данных).
- [x] **`sitemap.xml.ts`** — добавлены `/compare/*`; solutions и блог подхватываются автоматически.
- [x] **Плитки подкатегорий + сравнения + сценарии** на `/catalog/ai` — блок в `catalog/[segment].astro` (для `segment==='ai'`), данные — `src/data/ai-hub.ts`.
- [x] **Вложенный роут `/catalog/ai/[sub].astro`** — рендерит товары категории `ai-<sub>` из Directus; пока категории нет — «в подготовке» (noindex) с перелинковкой на сравнения.
- [ ] Полная витрина флагманов на хабе (`aiFlagships` в `ai-hub.ts` готов) — включить после импорта товаров, чтобы ссылки на карточки не вели на 404.
- [ ] Блоки карточки: «Сравнение тарифов», «Похожие/Статьи/Сравнения/Категория» — в шаблоне `product/[slug].astro`.
- [ ] Внутреннее меню/футер — ссылки на подкатегории.

> **Порядок деплоя.** Страницы `/compare/*` и сценарии ссылаются на карточки товаров
> (`/product/<sku>`) и подкатегории (`/catalog/ai/<sub>`), которые появляются после импорта
> (раздел A). Поэтому сначала выполняется раздел A (категории + импорт), затем деплой раздела B —
> иначе часть ссылок временно ведёт на 404.

### C. SEO/GEO
- [ ] Проверить Product/FAQ/Breadcrumb/Organization JSON-LD на каждой странице (Rich Results Test).
- [ ] `short_description` и первый Q FAQ — как самодостаточные ответы (цитируемость в AI Search).
- [ ] Канонические URL без хвостового слеша; фильтрованные выдачи — `noindex` (уже так).
