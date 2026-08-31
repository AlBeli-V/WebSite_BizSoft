# Переразложение товаров по разделам каталога по описаниям

Задача владельца от 30.08.2026: проверить распределение карточек по разделам
`/catalog` по описаниям товаров и переразложить неправильно лежащие.

## 1. Может ли товар лежать в нескольких разделах

В модели данных — нет: у товара в Directus одно поле `category` (m2o), весь
слой сайта (витрина, фильтры, микроразметка, WebMCP) собран вокруг одной
категории. Поэтому каждому товару выбран один — профильный — раздел, по
описанию и назначению.

Там, где «две категории» действительно нужны, это уже решено архитектурно:

- **AI-хаб**: `/catalog/ai` агрегирует родительский `ai` и все подкатегории
  `ai-*` — товар, перенесённый в `ai-video`, остаётся видимым и на
  `/catalog/ai`, и появляется в профильной `/catalog/ai/video`.
- **`ai-enterprise` («Корпоративные AI»)** по замыслу
  (`docs/ai-catalog-redesign.md`) — кросс-коллекция: enterprise-тарифы живут в
  тематических подкатегориях (ai-text, ai-code, ai-office), а в
  `ai-enterprise` попадают кросс-листингом. Кросс-листинг пока не реализован,
  поэтому раздел пуст и страница `/catalog/ai/enterprise` отдаёт «в
  подготовке» (noindex). Перевешивать товары в него — неправильно: они
  пропадут из тематической выдачи.

## 2. Что лежало не там (проверено по описаниям)

Источник текущих привязок: живая база (отчёты `ops-categories` и
`ops-export-products` от 30.08 в issue #22) и пакеты импорта
`scripts/catalog/*.json` — у пакетных товаров категория задана в пакете и
перезаписывается каждым прогоном `ops-import-vendors`.

| Товары | Было | Станет | Почему |
|---|---|---|---|
| DeepL Pro ×3 | ai | ai-text | профессиональный перевод текста |
| SuperGrok ×2, Kimi | ai | ai-text | текстовые AI-ассистенты |
| ChatGPT Business, ChatGPT Enterprise | ai | ai-text | по `docs/ai-catalog-import.md`; enterprise — через будущую кросс-коллекцию |
| Kling AI ×3, Higgsfield Pro | ai | ai-video | генеративное видео |
| Leonardo AI ×3, Krea ×2 | ai | ai-image | генерация изображений (у Krea ядро — realtime-изображения и апскейл) |
| Suno ×2 | ai | ai-audio | генерация музыки |
| Lovable ×2 | ai | ai-code | AI-сборка приложений — рядом с Cursor и Copilot |
| Windsurf ×2 | development | ai-code | прямой конкурент Cursor, который уже в ai-code |
| JetBrains AI Free/Pro/Ultimate | ai | ai-code | AI-ассистент в IDE |
| Jira Standard/Premium | collaboration | pm | «задачи, спринты и доски» — это раздел «Трекеры», стоявший почти пустым (2 товара); Confluence остаётся в «Досках» |
| JetBrains YouTrack | — | pm | трекер задач |
| MS Project Professional 2024 | office | pm | управление проектами |
| MS Visual Studio Pro 2019/2022 | office | development | IDE в «Офисном ПО» — явная ошибка |
| JetBrains TeamCity, Qodana | — | development | CI и статический анализ кода |
| MS Windows 11 Pro | office | system | операционная система |
| JetBrains Datalore | — | database | аналитика и работа с данными |
| Lumion View/Pro/Pro Floating ×3 | design | architecture | архитектурная визуализация; в самом пакете вендор заявлен `catSeg: architecture`, а товары были в design |

Итого 39 позиций в плане (часть, возможно, уже на месте — прогон покажет
«было → станет», совпадения — no-op). После переезда «Трекеры и управление
проектами» вырастает с 2 до ~6 товаров, профильные AI-подкатегории получают
свои флагманы, «Офисное ПО» перестаёт содержать IDE и ОС.

Проверено и оставлено как есть (по описаниям лежат верно): Acronis/Bitdefender
(security), AnyDesk/TeamViewer/Parallels/WinRAR (system), медиапакет (Ableton,
Cubase, FL Studio, iZotope, Avid, Boris FX и др. — media), Maxon/Autodesk
M&E/CorelDRAW/Sketch/Figma/Framer/Canva (design), SketchUp (architecture),
SOLIDWORKS/КОМПАС (engineering), Slack/Zoom/Контур.Толк (vcs),
Box/Dropbox/Miro/Confluence (collaboration), OpenRouter (родительский ai —
API-доступ к моделям, профильной подкатегории нет), стоки
(Shutterstock/Depositphotos/Envato/Artlist — media), Monotype (design/media по
текущей привязке), ManageEngine (разложен 21.08 по карте семейств).

## 3. Механика: два слоя правок

1. **Пакеты импорта** `scripts/catalog/*.json` — категории исправлены в
   источнике, иначе следующий `ops-import-vendors` молча откатил бы перенос.
2. **План** `data/catalog/recategorize.json` + новый воркфлоу
   **`ops-recategorize`** (по образцу `ops-categories`): apply=false — отчёт
   «было → станет» в issue #22, apply=true — точечные PATCH под
   администратором. Покрывает и непакетные товары (JetBrains, ChatGPT).

Тест `catalog-categories.test.ts` стережёт консистентность: целевой раздел
плана существует, пакетная позиция плана несёт ту же категорию и в пакете.
`ALLOWED_CATEGORIES` в `vendor-catalog.test.ts` расширен AI-подкатегориями.

## 4. Порядок выкатки

1. Мерж этой ветки в main.
2. `ops-recategorize` `apply=false` → сверить отчёт «было → станет».
3. `ops-recategorize` `apply=true`.
4. Приёмка: `ops-categories` `apply=false` — новые счётчики разделов; адреса
   карточек не меняются, sitemap и переобход не нужны.

## 5. Осталось на решение руководителя

- **WordPress.com ×4 в «Дизайне и графике»** — хостинг сайтов, по описанию не
  дизайн. Подходящего раздела нет; вариант — новый раздел «Сайты и хостинг»
  (завести через `data/catalog/categories.json` + `ops-categories`). Пока
  оставлено как есть.
- **7 сид-карточек без вендора** (vendor «—»: «Видеоконференцсвязь — Бизнес»,
  «Корпоративный мессенджер — Команда», «AI-ассистент для кода — Команда»
  и т.п.) — обезличенные заготовки ранней витрины, опубликованы и видны
  покупателю рядом с настоящими товарами. Предлагаю снять с публикации.
- **Gamedev-пласт** (Unity, Unreal, Photon, FMOD, Wwise, Spine, SpeedTree,
  Gaea, Marmoset, Reallusion, RizomUV, Houdini — десятки позиций) размазан по
  development/media/design. Если направление развивается, может заслуживать
  раздела «Разработка игр».
- **Кросс-коллекция `ai-enterprise`** не реализована — плитка «Корпоративные
  AI» на `/catalog/ai` ведёт на «раздел наполняется». Реализовать листинг или
  временно снять плитку.
