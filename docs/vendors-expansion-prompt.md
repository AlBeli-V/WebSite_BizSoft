# Промт: добавление новых производителей и товаров на biz-soft.pro

Переработанная версия под реальную архитектуру проекта (проверено по коду
2026-08-19). Исходный промт оперировал абстракциями («CMS/fixtures», поля
`vendor_slug`/`fx_source`, статусы CHECK/CONDITIONAL), которых в проекте нет —
здесь всё сведено к штатным механизмам.

## 0. Контуры исполнения — кто что может

| Контур | Что делается | Ограничения |
|---|---|---|
| Репозиторий (сессия Claude / локально) | `src/data/vendors.ts`, `scripts/content/<slug>.json`, логотипы, тесты, xlsx-прайс | из облачной сессии НЕТ egress к сайтам вендоров, biz-soft.pro и Directus |
| Directus (прод) | карточки товаров, цены, категории | только с ноутбука оператора: `node scripts/import-cards.mjs <file.xlsx>` (dry-run) → `--apply`; нужны `SITE_URL` и `ADMIN_TOOLS_TOKEN` в `.env` |
| Проверка официальных источников | подтверждение self-service checkout, цен, способов оплаты | вручную оператором, либо воркфлоу `ops-probe` (GitHub runner имеет полный egress: URL + grep-шаблон → результат в issue #22) |

## 1. PREFLIGHT (до изменений)

1. Архитектура: Astro SSR + Directus (товары/категории ЖИВЫЕ из БД, не в репо).
   Прочитать: `docs/OPERATIONS.md`, `src/lib/types.ts` (схема Product),
   `src/lib/pricing.ts` (ценовая логика), `src/lib/bulk-import.ts` (импорт).
2. Эталоны переиспользования:
   - вендорская страница: `/vendors/[slug].astro` → `VendorGenericLanding.astro`
     (базовый) или `VendorLanding.astro` (если для slug есть контент в
     `src/data/vendor-content.ts`). Страницы `vendors/jetbrains.astro`,
     `zoom.astro`, `figma.astro`, `openai.astro` — bespoke, руками написанные:
     их НЕ копировать, новые вендоры идут через шаблонный маршрут;
   - карточка товара: `/product/[slug].astro` — рендерит запись Directus
     (эталон наполнения — товар `jb-all-pack-org`).
3. Источник данных вендора: запись в `VENDORS` (`src/data/vendors.ts`) +
   опционально `scripts/content/<slug>.json` (summary, comparison, decision,
   scenarios, faq) → `node scripts/build-vendor-content.mjs`. Товары
   подтягиваются из Directus по точному совпадению поля `vendor`.
   Контент в компоненты не хардкодить.
4. Штатный ценовой калькулятор — `computePegRub()` (`src/lib/pricing.ts`):
   `base_price_usd|eur × курс ЦБ × markup_coeff` (по умолчанию 1.85),
   округление `roundPrice`. Проверить воспроизводимость на 5 опубликованных
   иностранных SKU (значения смотреть в Directus/на витрине). Если формула
   не воспроизводится — цены не угадывать: карточки без цены («Цена по
   запросу» — штатный режим при пустой `price`) + `reports/vendors/pricing-audit.md`.
5. `git status` чистый; несвязанные файлы не трогать. Не коммитить и не
   деплоить без отдельной команды.

## 2. Допуск SKU

Публиковать цену только если в день выполнения на официальном сайте
подтверждены: self-service checkout, оплата банковской картой, фиксированная
публичная цена/конфигуратор, edition, метрика лицензирования, страна
биллинга и способ оформить аккаунт/tenant/лицензию на клиента.

Полей `source_url`/`checked_at` в схеме Directus нет — фиксация аудита ведётся
в репо: `reports/vendors/pricing-audit.md`, по строке на SKU:
`sku | official_name | source_url | checkout_url | цена и валюта | метрика |
период | мин. кол-во | дата проверки | кто проверил`.

Contact sales / Request quote / Enterprise / Dedicated / MSP/MSSP / Premium
Support / usage-based без фиксированного SKU → `reports/vendors/rejected-products.md`
с причиной. Такие тарифы не заводить вовсе (даже как «по запросу»), если весь
вендор quote-only — вендора не создавать.

## 3. Создать вендоров (VENDORS + content JSON + логотип + товары в Directus)

Для каждого: запись в `VENDORS` (slug, vendor, legalName, brandColor, site,
catSeg/catLabel — существующая категория каталога, domain, tagline, about),
официальный SVG-логотип в `public/brand-logos/<slug>-logo.svg` (не
перерисовывать, не base64), при необходимости регистрация в `src/data/logos.ts`
по образцу соседей; `scripts/content/<slug>.json` со сравнением тарифов,
decision-матрицей, сценариями и FAQ → пересборка `vendor-content.ts`.

| Вендор | SKU (slug = sku в нижнем регистре) | Исключить |
|---|---|---|
| AnyDesk | anydesk-solo, anydesk-standard, anydesk-advanced | — |
| Docker | docker-pro, docker-team, docker-business | Business только если есть Buy now; без Premium Support/TAM |
| GitLab | gitlab-premium-saas, gitlab-premium-self-managed | Ultimate, Dedicated |
| Parallels | parallels-desktop-standard-sub, parallels-desktop-standard-perpetual, parallels-desktop-pro, parallels-desktop-business | Enterprise, RAS, DaaS |
| Acronis | acronis-cyber-protect-standard-ws, -standard-server, -advanced-ws, -advanced-server, acronis-cloud-storage | только online-store SMB; без Cloud/MSP/DR custom |
| 1Password | 1password-teams-starter, 1password-business | Enterprise |
| Slack | slack-pro, slack-business-plus | Enterprise+ |
| Dropbox | dropbox-standard, dropbox-advanced | Enterprise |
| SketchUp | sketchup-go, sketchup-pro, sketchup-studio | enterprise solutions |
| Bitdefender | bitdefender-gravityzone-business, bitdefender-gravityzone-premium | online checkout 1–100 устройств; без Enterprise/XDR/MDR/MSSP |
| Cloudflare | cloudflare-pro, cloudflare-business | цена за домен; без Enterprise/Workers/R2/usage-based |
| Microsoft | см. §5 | E3/E5, Windows Server/SQL/CAL/LTSC, Azure |

Категории: сопоставлять с существующими в Directus (каталог `/catalog/<segment>`);
новую категорию создавать только если ни одна не подходит (через админку,
затем `catSeg` вендора).

## 4. Статусы вместо CHECK/CONDITIONAL (штатные механизмы)

Схема знает только `published/draft/archived` — выдуманные статусы заменяются:

- **CHECK** (цена/условия не подтверждены) → карточка с ПУСТОЙ `price`:
  витрина сама показывает «Цена по запросу» и CTA на КП (ProductCard,
  VendorGenericLanding). Ориентир цены — только в `description` с датой.
  Прямой покупки у таких карточек нет по построению.
- **CONDITIONAL** (Microsoft 365) → то же + обязательный текст (см. §5);
  до утверждения процесса проверки tenant держать в `draft`.
- Товар, не прошедший допуск, → не заводить, строка в rejected-products.md.

## 5. Microsoft

### 5.1 Подписки M365 (все — «условные», без цены и без прямой покупки)

m365-business-basic, m365-business-standard, m365-business-premium,
m365-apps-for-business, m365-copilot-business-addon. Цену не публиковать
(пустая `price` → «Цена по запросу»), CTA — «Проверить возможность» (штатная
форма вопроса/КП), в `description` обязательный текст: оформление только на
tenant клиента в поддерживаемой стране после проверки; новые продажи
Microsoft в России официально приостановлены (источник S16). Публиковать
(`published`) только после утверждения процесса tenant-check, до того — `draft`.

### 5.2 Коробочные ключи (поставка ключа активации, цены фиксированные)

Отдельная модель поставки — критерии §2 к ним не применяются (это не
self-service подписка вендора, а поставка ключа со склада поставщика);
вместо этого обязательна фиксация прайса поставщика и даты в pricing-audit.md.

Правила карточек:
- из `name` убрать «Ключ активации» (например: «Microsoft Office Home and
  Business 2021 (WIN)»);
- способ поставки показывать штатно: `price_note` = «электронный ключ
  активации», первая строка `features` — «Поставка: ключ активации и
  инструкция по установке»;
- **обязательная приписка в `description` и в FAQ каждой карточки:**
  «Активация должна быть произведена в течение 5 дней с момента получения
  ключа. По истечении этого срока успешная активация не гарантируется,
  ключ активации замене и возврату не подлежит.»;
- цена: ₽ по фиксированному курсу 85 ₽/$ (решение руководителя), поэтому
  `price` задаётся готовой суммой и `price_locked = 1` (иначе штатная
  переоценка по курсу ЦБ её перезапишет); `base_price_usd` заполнить для
  аудита, `peg_to_usd` НЕ включать; `origin = Иностранное`;
  категория — существующая (office; Visual Studio → dev; Windows → system);
  `vat_percent` — по действующей логике BizSoft (как у соседних карточек).

| Наименование (после очистки) | USD | ₽ (×85, до рубля) | Примечание |
|---|---|---|---|
| Microsoft Office Home and Business 2021 (WIN) | 256,83 | 21 831 | |
| Microsoft Office Home and Business 2021 (MAC) | 272,41 | 23 155 | |
| Microsoft Office Home and Business 2024 (WIN) | 448,82 | 38 150 | |
| Microsoft Office Home and Business 2024 (MAC) | 833,44 | 70 842 | |
| Microsoft Office Professional Plus 2021 (WIN) | 237,92 | 20 223 | |
| Microsoft Office Professional Plus 2024 (WIN) | 237,92 | 20 223 | цена = 2021 — подтвердить у поставщика |
| Visual Studio Professional 2022 | 703,52 | 59 799 | |
| Visual Studio Professional 2019 | 703,52 | 59 799 | |
| Microsoft Visio Standard 2021 | 478,74 | 40 693 | |
| Microsoft Visio Professional 2024 | 837,80 | 71 213 | |
| Microsoft Visio Professional 2019 | 837,80 | 71 213 | |
| Microsoft Project Professional 2024 | 889,00 | 75 565 | |
| Windows 11 Pro | 222,06 | 18 875 | в прайсе «Windows Pro 11» — официальное имя «Windows 11 Pro» |

**Не заводить без подтверждения поставщиком (таких версий продукта не
существует или версия сомнительна)** — в pricing-audit.md со статусом
«на проверке»: «Visual Studio Professional 2024» и «2021» (версии VS: 2019,
2022), «Microsoft Project Standard 2017» (были 2016/2019/2021), «Microsoft
Project Professional 2022» (была 2021), «Microsoft Project Professional 2010»
(снята с продаж). Если поставщик подтверждает позицию под другим корректным
названием — заводить под официальным названием.

## 6. STOP-LIST (не создавать)

SAP, Oracle, VMware/Broadcom, Veeam, Citrix, Cisco, Salesforce, IBM,
SOLIDWORKS, Archicad, Red Hat, Canonical, MathWorks, MongoDB, Elastic,
TeamViewer, Atlassian, ESET — и enterprise/quote-only тарифы оставленных
брендов.

## 7. Данные SKU — реальная схема

Использовать существующую схему xlsx-импорта (`scripts/make-template.mjs`,
шаблон `public/Шаблон загрузки.xlsx`): sku, name, vendor (точно как в
VENDORS.vendor), origin, category, license_type, short_description,
description, keywords, base_price_usd, base_price_eur, peg_currency,
markup_coeff, price_locked, price, price_note, vat_percent, currency,
promo_price, promo_label, promo_start, promo_end, features (через « | »),
status, sort. `slug` при импорте = sku в нижнем регистре. Дополнительные
SEO-поля (for_whom, use_cases, faq, related_products) — через админку после
импорта. Поля схемы НЕ расширять без отдельного согласования
(`pnpm directus:schema`); всё, чему нет места в схеме (source_url,
checkout_url, checked_at, метрика, страна биллинга), — в pricing-audit.md.

## 8. Цена

Только штатная логика (`src/lib/pricing.ts`): для подписок —
`base_price_usd|eur` + `peg_currency` + `markup_coeff` (курс ЦБ подтянется
сам, курс не хардкодить ни в тексте, ни в цене); учитывать период, годовое
обязательство (monthly billed annually показывать как в checkout, не
умножать слепо на 12), минимальное количество, налоги страны биллинга,
действующую VAT-логику BizSoft, округление. Promo — только через
promo_price/promo_start/promo_end. Неподтверждённая цена = пустая `price`
(«Цена по запросу») + ориентир с датой в описании. Исключение — коробочные
ключи Microsoft (§5.2): фикс ₽ по курсу 85, `price_locked = 1`.

## 9. Страницы

- Вендор: шаблонный маршрут `/vendors/[slug].astro` — breadcrumbs, hero с
  официальным логотипом/юрназванием/H1/CTA, «цена от», плитки товаров живыми
  из Directus, сравнение тарифов + «какой выбрать» + сценарии + FAQ из
  `scripts/content/<slug>.json`, SEO/JSON-LD, перелинковка — всё уже в
  компонентах, ничего не дублировать.
- Товар: `/product/[slug].astro` — наполняется полями Directus (эталон —
  `jb-all-pack-org`): short + расширенное описание, «что входит» (features),
  для кого, ограничения, 4 шага, документы для юрлица, цена с НДС и датой
  курса, related. Карточки без цены не имеют прямой покупки — штатно.

## 10. Контент, дизайн, право

Русский язык, нейтрально и точно; факты — только с официальных источников
вендора. Не обещать доступность в РФ, обход ограничений, VPN, фиктивный
billing address, подмену страны, поддержку без entitlement или передачу
чужого аккаунта. Существующие layout/компоненты/токены; официальные SVG-логотипы
через пайплайн ассетов с alt/width/height; header/поиск/навигация/footer не менять.

## 11. SEO / A11y / тесты

Уникальные title/description/H1/canonical/OG (штатно из полей карточки),
breadcrumbs, Product/Offer/FAQ JSON-LD только с реальными данными; карточки
без цены не должны заявлять InStock/цену в разметке. Прогнать
`pnpm test`, `pnpm build` (+ typecheck/lint, если настроены). Добавить в
`tests/` (vitest, чистая логика): уникальность слагов в VENDORS, отсутствие
stop-list вендоров в VENDORS, валидность `scripts/content/*.json` по схеме
VendorContent, контрольные расчёты цен по формуле `computePegRub` на
фикстурах, для xlsx-прайса — полнота обязательных полей и `price_locked`
у ключей Microsoft. Ручной QA витрины (1440/390 px, переполнения таблиц) —
после деплоя оператором или через `ops-probe`.

## 12. Финал

Перечислить: изменённые файлы, новые записи VENDORS, подготовленные
xlsx-строки, формулу цены + 5 контрольных сравнений с существующими SKU,
rejected-позиции, результаты тестов/сборки и что осталось на оператора
(импорт в Directus, деплой, проверка источников). Без коммита и деплоя без
отдельной команды.

## 13. Контроль приёмки

| Контроль | Принято, если |
|---|---|
| Наследование | использованы VendorGenericLanding/VendorLanding и данные Directus, как у существующих вендоров |
| Ассортимент | только перечисленные self-service SKU; stop-list отсутствует |
| Цена | формула `computePegRub` совпала с 5 существующими SKU; ключи Microsoft — ₽×85 c `price_locked` |
| Checkout | для каждого опубликованного SKU в pricing-audit.md есть источник, checkout URL и дата |
| Без цены | карточки без подтверждённой цены — «Цена по запросу», без прямой покупки |
| Microsoft | M365 — без цены и в `draft` до утверждения tenant-check; ключи — с припиской про 5 дней |
| Графика | официальные SVG-логотипы; layout из дизайн-системы |
| Mobile | нет overflow и нечитаемых таблиц на 390 px |
| SEO | metadata/canonical/breadcrumbs/structured data валидны |
| Качество | tests/build проходят |

## 14. Релизный порядок

1. AnyDesk, Docker, Parallels, 1Password.
2. Acronis, Bitdefender, SketchUp.
3. Коробочные ключи Microsoft — после подтверждения прайса поставщиком
   (позиции «на проверке» — только после уточнения версий).
4. GitLab, Slack, Dropbox, Cloudflare — после тестовых checkout.
5. Подписки Microsoft 365 — после утверждения процесса tenant-check.

## 15. Первичные источники

S1. Эталон вендорской страницы — `src/pages/vendors/[slug].astro` + запись VENDORS (живой пример: https://biz-soft.pro/vendors/canva)
S2. Эталон карточки — https://biz-soft.pro/product/jb-all-pack-org
S3. AnyDesk payment methods — https://support.anydesk.com/docs/payment-methods
S4. Docker payment methods — https://docs.docker.com/billing/payment-method/
S5. Docker pricing — https://www.docker.com/pricing/
S6. GitLab billing account — https://docs.gitlab.com/subscriptions/billing_account/
S7. Parallels Buy now — https://www.parallels.com/products/desktop/buy/
S8. Acronis Cyber Protect SMB — https://www.acronis.com/en/products/cyber-protect/small-business/
S9. 1Password cards — https://support.1password.com/manage-subscription/
S10. Slack payment methods — https://slack.com/help/articles/360002038947-Supported-payment-methods
S11. Dropbox billing — https://help.dropbox.com/billing
S12. SketchUp purchasing — https://help.sketchup.com/en/license-types-and-pricing
S13. Bitdefender GravityZone Premium — https://www.bitdefender.com/business/products/gravityzone-premium-security
S14. Cloudflare billing policy — https://developers.cloudflare.com/billing/understand/billing-policy/
S15. Microsoft business card payment — https://learn.microsoft.com/en-us/microsoft-365/commerce/billing-and-payments/pay-for-your-subscription?view=o365-worldwide
S16. Microsoft Russia sales suspension — https://blogs.microsoft.com/on-the-issues/2022/03/04/microsoft-suspends-russia-sales-ukraine-conflict/
