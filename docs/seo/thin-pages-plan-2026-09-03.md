# План разбора малоценных страниц и линеек ManageEngine (03.09.2026)

Статус: **виза дана 08.09.2026**, применение — операциями с `main`.
Решение 03.09.2026: «разобрать 52 страницы по списку Яндекса + линейки
ManageEngine», применять штатными механизмами. Машинный список —
`data/seo/thin-pages-2026-09-03.json`.

Виза получена в разборе Google-авторитета: бюджет обхода Google —
дефицитный ресурс, из-за которого 67% известных ему страниц сайта остаются
вне индекса (`reports/seo/google-authority-strategy.md`, раздел 3.1).
Дубли, которые Яндекс уже снял сам, продолжают этот бюджет отнимать.

Правила групп A (`*-IND`) и B (`ME-*-PERP`) в коде **уже действуют**
(`productNoindex()` в `src/lib/catalog.ts`). Осталась операционная часть:
точечные группы A-point, C и D применяются `ops-set-noindex` с `main`
(сначала `apply=false`, затем `apply=true`), тексты групп E и I — партией
через `ops-apply-descriptions`, контент F и H — отдельными PR.

## Откуда взялся список

Первый срез сенсора покрытия индекса (`scripts/seo/index_coverage.py`,
`reports/seo/data/index-*-2026-09-03.json` в ветке `seo-data`), инвентарь
sitemap на 810 URL:

| Показатель | Значение |
|---|---|
| Google: в индексе | 149 (из них с показами 17) |
| Google: обнаружена, не сканирована | 290 (258 — карточки товаров, 122 — ManageEngine) |
| Google: URL неизвестен | 131 (99 товаров, 21 статья блога) |
| Google: без статуса (лимит токена, добьётся следующим прогоном) | 239 |
| Google: последний обход известных URL | июнь 8, июль 115, август 23, сентябрь 4 |
| Яндекс: в поиске страниц инвентаря | 536 (554 по хосту) |
| Яндекс: исключено как «малоценная или маловостребованная» | 52 |

Причина у обеих систем одна: молодой домен без внешних ссылок получает
малый бюджет обхода, и он растекается по страницам, которые поисковик
считает дублями. Убрать балласт из индекса — не ради Яндекса (он их уже
снял), а чтобы обход Google шёл на карточки со спросом.

Спрос по данным сайта (Вордстат, показов в месяц): Zoom 1 264 066,
SketchUp 131 944, CorelDRAW 131 087, Miro 111 664, Avid 45 118,
Bitdefender 22 058, Maxon 12 625, Boris FX 7 814, Monotype 4 251,
MAGIX Vegas 3 205, Marmoset 1 718, RizomUV 1 009; «manageengine» — 850,
«endpoint central» — 232, «servicedesk plus» — 3, «manageengine купить» — 4.

## Группы и действия

### A. Личные лицензии — 10 карточек → noindex

Сайт продаёт юрлицам; Яндекс исключил 6 из 7 карточек с суффиксом `-IND`.

| Слаг | Карточка | Цена | Механизм |
|---|---|---|---|
| bitdefender-premium-security-ind | Bitdefender Premium Security (Individual) | 20 601 ₽ | правило `*-IND` (код) |
| bitdefender-total-security-ind | Bitdefender Total Security (Individual) | 24 463 ₽ | правило |
| bitdefender-ultimate-security-ind | Bitdefender Ultimate Security (Individual) | 26 073 ₽ | правило |
| mono-ind | Monotype Fonts — Individual | 16 318 ₽ | правило |
| mrmst-tb-sub-ind | Marmoset Toolbag (подписка, Individual) | 3 130 ₽ | правило |
| mrmst-tb5-ind | Marmoset Toolbag 5 (Individual, бессрочная) | 65 767 ₽ | правило |
| mono-ind-pro | Monotype Fonts — Individual Pro | 32 801 ₽ | ops-set-noindex (sku без суффикса) |
| maxon-redgiant | Red Giant 1Y (Individuals) | 105 622 ₽ | ops-set-noindex; есть maxon-redgiant-teams |
| maxon-redshift | Redshift 1Y (Individuals) | 47 770 ₽ | ops-set-noindex; есть -teams |
| maxon-zbrush | ZBrush 1Y (Individuals) | 65 952 ₽ | ops-set-noindex; есть -teams |

Командные и семейные варианты (Bitdefender Family/GravityZone, Monotype
Team, Marmoset Studio, Maxon Teams) остаются в индексе.

### B. ManageEngine — 81 бессрочная карточка → noindex правилом

В sitemap 182 карточки ManageEngine: 101 годовая подписка и 81 бессрочная
(`ME-*-PERP`). У каждой бессрочной есть парная подписка с тем же
описанием, отличие — слова «вечная лицензия» в названии. Google держит
их в очереди «обнаружена, не сканирована» (122) и «неизвестна» (60),
в поиске Яндекса из 182 — восемь. Правило в `productNoindex()`: бессрочный
вариант остаётся на витрине, в корзине и в КП, в поиск идёт подписка.

Три подписочные карточки, которые Яндекс исключил (DDI Central
Professional, Password Manager Pro Enterprise/Standard), остаются и идут
в партию текстов (группа E).

Спрос на ManageEngine — брендовый и на продукт («manageengine» 850,
«endpoint central» 232), а не на объём лицензии. Следующий шаг после
этого разбора — архитектурный и отдельным решением: карточка = продукт +
редакция, объёмы — селектор внутри карточки.

### C. Бессрочные дубли с парной подпиской у других вендоров — 10 (+2) → noindex точечно

| Слаг | Карточка | Цена | Остаётся в индексе |
|---|---|---|---|
| avid-mc-perp | Avid Media Composer (бессрочная) | 214 115 ₽ | avid-mc-sub, avid-mc-ult |
| boris-continuum-perp | Boris FX Continuum (бессрочная) | 328 837 ₽ | boris-continuum-sub |
| boris-mocha-perp | Boris FX Mocha Pro (бессрочная) | 246 422 ₽ | boris-mocha-sub |
| boris-sapphire-perp | Boris FX Sapphire (бессрочная) | 506 854 ₽ | boris-sapphire-sub |
| cdr-gs-perp | CorelDRAW Graphics Suite (бессрочная) | 148 896 ₽ | cdr-gs-sub, cdr-gs-biz |
| csp-ex-perp | Clip Studio Paint EX (бессрочная) | 36 261 ₽ | csp-ex-sub |
| rizom-rs-perp | RizomUV Real Space (бессрочная, Indie) | 68 787 ₽ | rizom-rs-sub |
| rizom-vs-perp | RizomUV Virtual Spaces (бессрочная, Indie) | 34 382 ₽ | rizom-vs-sub |
| vegas-edit-perp | VEGAS Pro Edit (бессрочная) | 38 036 ₽ | vegas-edit-sub |
| wndr-filmora-perp-win | Wondershare Filmora (бессрочная, Windows) | 13 185 ₽ | filmora-annual, -xplat, -team |

Предлагаю добавить по той же логике: `csp-pro-perp` (в индексе Google без
показов, пара csp-pro-sub) и `cdr-painter-perp` (пара cdr-painter-sub).
Без пары остаются и идут в тексты: avid-pt-ult-perp, vegas-suite-perp.

### D. Zoom — 8 аддонов → noindex точечно

Из 12 карточек Zoom Яндекс исключил 11; в поиске — только Workplace Pro.
Спрос на Zoom (1,26 млн показов в месяц) брендовый, его держит
`/vendors/zoom` — первая страница сайта по показам в Google.

noindex: zoom-ai-companion, zoom-events, zoom-large-meeting-500,
zoom-phone-global, zoom-phone-metered, zoom-phone-us-ca, zoom-rooms,
zoom-webinars-500. Все остаются на витрине и в КП.

Остаются в индексе и уходят в тексты: zoom-wp-business (47 658 ₽),
zoom-wp-business-plus (53 752 ₽), zoom-wp-enterprise (по запросу) — у них
свой интент «zoom workplace business купить», но описания сейчас
неразличимы.

### E. Остаются в индексе — партия уникальных текстов

zoom-wp-business, zoom-wp-business-plus, zoom-wp-enterprise,
box-business-plus (пара box-business), confluence-standard (пара
confluence-premium), miro-business (пара miro-starter), avid-pt-ult-perp,
vegas-suite-perp и три подписочные карточки ManageEngine из группы B.

Механизм — `data/seo/product-descriptions.json` → `ops-apply-descriptions`
(план → apply), различитель в `name`/`meta_title` по правилу CLAUDE.md.
Тексты пишутся отдельной партией после визы.

### F. Разделы и лендинги — контент отдельной партией

Исключены Яндексом как малоценные: `/catalog/ai/image`,
`/catalog/collaboration`, `/catalog/design`, `/catalog/monitoring`
(нет intro-текста раздела — `data/catalog/categories.json` →
`ops-categories`), `/solutions/ai-dlya-marketinga`,
`/solutions/ai-servisy-dlya-biznesa` (`src/data/solutions.ts`) и
`/vendors/sketchup` — при спросе 131 944 показа в месяц это первый кандидат
на доработку лендинга.

Сделано (PR группы F, 03.09.2026):

- разделы `collaboration`, `design`, `monitoring` — блок `content` в
  `data/catalog/categories.json` (seo_text «Как выбрать», свои `faqs`,
  `meta_title`, `meta_description`); переносит `ops-categories`
  (`apply=false` → `apply=true`), витрина выводит seo_text под списком
  товаров (`src/lib/text-blocks.ts`), а не вместо лида;
- `/catalog/ai/image` — `guide`, `faq`, `metaTitle`, `metaDescription` в
  `src/data/ai-hub.ts`, шаблон `[sub].astro` их рендерит;
- решения — поле `sections` («Как выбрать») в `src/data/solutions.ts`,
  `ai-dlya-marketinga` переписана целиком, `ai-servisy-dlya-biznesa`
  дополнена; связанные разделы ведут на основные адреса, а не на слитые
  дубли с 301;
- `/vendors/sketchup` — контент приведён к прайсу: сравнение и сценарии по
  Go / Pro / Pro Scan / Pro Civil Contractor (Studio из прайса снят
  19.08.2026, а лендинг всё ещё сравнивал с ним), FAQ 9 вопросов, включая
  бесплатную и образовательную версии.

После мержа: деплой → `ops-categories` → переобход семи URL
(`ops-yandex-recrawl`) → контроль статуса через сенсор покрытия.

### G. Уже сняты с витрины — действий нет

ai-image-business, corporate-chat-team, dscrpt-hobbyist, mj-basic,
recraft-basic: в свежем sitemap их нет, запись об исключении у Яндекса
осталась от 23.07.

Отдельная проверка: 15 URL, которые Яндекс держит в поиске, а в sitemap их
уже нет (openai-plus, openai-pro, openai-api, ai-text-team, int-collab-miro,
ni-ozone-adv и другие) — убедиться, что они отдают 301 через `old_slugs`,
а не 404.

### H. Разделы каталога из выборки событий поиска — контент разделов

Добавлено 03.09.2026 по решению руководителя. Первый прогон сбора с
выборкой событий поиска Вебмастера (INDEX-001, PR #341) назвал причину у
42 из 50 исключений: все — «малоценная или маловостребованная». Среди них
восемь разделов каталога, которых в группе F не было: `/catalog/architecture`,
`/catalog/endpoint`, `/catalog/iam`, `/catalog/media`, `/catalog/office`,
`/catalog/pm`, `/catalog/system`, `/catalog/vcs`. Механизм тот же, что у F:
intro-текст раздела в `data/catalog/categories.json` → `ops-categories`.
У части разделов intro в плане уже есть (architecture) — сначала сверить,
доехал ли текст до прода и показывается ли он на странице раздела.

### I. Карточки тарифов Business — партия уникальных текстов

Тем же срезом сняты восемь карточек тарифов Business: `bitdefender-gravityzone-business`,
`cloudflare-business`, `cursor-business`, `cursor-business-premium`,
`docker-business`, `parallels-desktop-business`, `prfrc-p4-cloud`,
`sentry-business`. У каждой есть соседний тариф того же продукта с почти
тем же описанием (Cursor Business против Cursor Business Premium, Docker
Business против Docker Team). Механизм — как у группы E: различитель
тарифа в `name`/`meta_title`/`short_description`, партия через
`ops-apply-descriptions` после визы; noindex не ставится — это
коммерческие карточки с собственным интентом.

Полный перечень снятых адресов с датами — в снимке дня
(`yandex.indexation.excluded_samples.unexpected`, ветка `seo-data`); в
отчёте это сбой дня `INDEXATION_COMMERCIAL_EXCLUDED`, пока страницы не
разобраны.

## Что даёт

| | Было | Станет |
|---|---|---|
| URL в sitemap | 810 | около 700 |
| Карточек ManageEngine в индексе | 182 | 101 |
| Дублей «подписка/бессрочная» в индексе | 91 пара | 0 |

Бюджет обхода Google перестаёт делиться на 110 страниц, которые обе
системы считают дублями; остальное (внешние ссылки, честный `lastmod`,
переобход) работает на оставшиеся.

## Порядок применения после визы

1. Мерж PR с правилами A/B и workflow `ops-set-noindex` — деплой убирает
   87 URL из sitemap и ставит noindex на страницах.
2. `ops-set-noindex` с main: `apply=false` (план в issue #22), затем
   `apply=true` списком групп A-точечно, C, D (22 слага, плюс 2 по
   решению).
3. Партия текстов E и контент F — отдельными PR по правилам контента.
4. `ops-yandex-recrawl` по остающимся парным карточкам подписки (20 URL).
5. Контроль — сенсор покрытия: доля «обнаружена, не сканирована» и число
   исключений Яндекса через 2 и 4 недели в утреннем отчёте.
