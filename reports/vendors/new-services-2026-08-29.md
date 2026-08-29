# Партия этапа 1 — 29.08.2026: 17 производителей (1а: AI-кластер, 1б: аудио/креатив)

Отмашка руководителя 29.08.2026 по итогам отчёта этапа 0 (базовая линия +
замер спроса Вордстатом по 38 кандидатам конкурентного анализа). Состав партий
утверждён целиком; AWS отложен (спрос — в основном омоним «присадка AWS»).

## Партия 1а — AI-кластер (8 вендоров)

| Вендор | Спрос, показов/мес | Карточки | Цена |
|---|---|---|---|
| xAI (Grok) | 6 087 | SuperGrok, SuperGrok Heavy | по запросу¹ |
| Moonshot AI (Kimi) | 5 165 | Kimi (подписка) | по запросу¹ |
| OpenRouter | ≈259 | Пополнение баланса | по запросу (модель баланса)² |
| Higgsfield | 584 | Pro | по запросу¹ |
| Krea | 369 | Pro, Business | по запросу¹ |
| Lovable | ≈213 | Pro $250/год, Business $500/год | vendor-page |
| DeepL | 184 | Starter $104.88, Advanced $344.88, Business $689.88 (за польз./год) | vendor-page |
| Windsurf | 114 | Pro, Teams | по запросу¹ |

¹ Страницы тарифов защищены от автоматического снятия (Chrome-рендер вис/пуст,
дампы в issue #22): публикуем «Цена по запросу», прайс подтверждает оператор
при первой сделке — штатный режим §4 регламента.

² OpenRouter: отклонение 20.08 касалось продажи как годовой подписки (такого
товара не существует). Решением руководителя 29.08 заведён альтернативной
моделью из rejected-products.md — разовая услуга «пополнение баланса по
договору»; комиссия вендора за пополнение (5,5% по FAQ) учитывается в КП.

## Партия 1б — аудио, архвиз, креатив, утилиты (9 вендоров)

| Вендор | Спрос | Карточки | Цена |
|---|---|---|---|
| Image-Line (FL Studio) | 2 495 | Fruity 99, Producer 179, Signature 269, All Plugins 449 (USD, бессрочные) | vendor-page |
| Ableton | 2 111 | Intro 99, Standard 349, Suite 749 (USD, бессрочные) | vendor-page |
| Steinberg (Cubase) | 662 | Elements 99.99, Artist 329, Pro 579.99 (USD, бессрочные) | vendor-page |
| iZotope | ≈161 | Ozone Std 219, Ozone Adv 499, RX Std 399, Neutron 299 (USD, бессрочные) | vendor-page |
| Lumion | 1 023 | View 229, Pro 1 149, Pro Floating 1 499 (USD/год) | vendor-page |
| Capture One | ≈182 | Pro (годовая) | по запросу (гео-прайс) |
| Toon Boom | ≈137 | Harmony Advanced 1 128 USD/год; Premium по запросу | смешанно³ |
| RARLAB (WinRAR) | ≈361 | Корпоративная лицензия | по запросу (магазин 404 раннеру) |
| think-cell | ≈114 | Suite (за польз./год) | по запросу (гео-прайс) |

³ Toon Boom: на странице вендора однозначно связана с названием только пара
«Harmony Advanced — USD 1,128.00/год»; остальные редакции без меток — Premium
заведён без цены, Essentials не заводится (начальный уровень).

## Механики спроса в этой же партии

- 4 новых сравнения /compare/*: cursor-vs-windsurf, chatgpt-vs-grok,
  kimi-vs-chatgpt, fl-studio-vs-ableton — по измеренным кластерам.
- Перелинковка AI-карточек (ai-interlinks.ts) для 8 новых вендоров.
- Контент лендингов (сравнение тарифов, decision, сценарии, FAQ) — все 17.

## Графика

Официальные глифы (пары color/mono, 512×512, safe zone 12.5%): Grok, Kimi,
OpenRouter, Krea, Lovable — коллекция LobeHub Icons; DeepL, Windsurf,
Steinberg — simple-icons (тем же путём brand-logos автогенерацией). Визуальный
QA contact sheet пройден (исправлены Kimi-color и fill-rule LobeHub-глифов).
UNRESOLVED (буквенный знак до пакета оператора): Higgsfield, Image-Line,
Ableton, iZotope, Lumion, Capture One, Toon Boom, RARLAB, think-cell —
официальный вектор недоступен из среды (Wikimedia/сайты вендоров закрыты
egress), выдуманные знаки не ставим по политике графики.

## Аудит и правила

- reports/vendors/pricing-audit.md: +36 SKU со источниками и датой 29.08.2026.
- Стоп-листы соблюдены (VPN, Ansys, Archicad, MathWorks и др. не заводились).
- Rejected-позиции зафиксированы в пакетах scripts/catalog/*.json (поле rejected).
- Долларов на витрине нет: рублёвая цена — штатная формула base_price_usd ×
  курс ЦБ × 1.85, пересчёт ежедневный (ops-currency-refresh).

## Проверки

vitest 375/375, py-тесты 296/296, astro check — 0 ошибок; сборка xlsx
импорта (import-vendors.mjs --emit) — 17 контрольных SKU на месте.
