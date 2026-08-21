# Исключённые из поиска Яндекса страницы biz-soft.pro — анализ и план возврата

Дата анализа: 2026-08-19. Источник данных: API Яндекс.Вебмастера v4
(воркфлоу `seo-data-collect` → `data/yandex-2026-08-19.json`,
сборщик `scripts/seo/collect.py`). Ничего на сайте в рамках этого анализа
не менялось — только диагностика и рекомендации.

## Резюме для руководителя

- **Технических проблем нет.** Ни одна страница не исключена из-за дублей,
  редиректов, запретов в robots.txt или ошибок сервера: все исключённые
  страницы отдают HTTP 200, sitemap и canonical в порядке.
- **Единственная системная причина — «малополезная или маловостребованная
  страница» (МПК, статус LOW_QUALITY): 160 из 161 исключённых URL.**
  Один URL (`/product/jb-ai-ultimate`) выпал со статусом NOTHING_FOUND —
  разовый сбой робота, страница живая.
- **Основной удар — по карточкам товаров: 155 из 161.** В поиске осталось
  90 карточек. Причина: тарифные карточки одного продукта — почти близнецы
  (11 карточек Zoom, по 4 у Figma/Framer/Runway/Recraft и т.д.) с коротким
  шаблонным описанием, поэтому Яндекс считает их малополезными.
- **Процесс обратим.** 111 страниц, исключённых в июле, уже вернулись в поиск
  сами по мере доработок сайта (последняя волна возвратов — 12–18 августа,
  вернулись 66 карточек товаров и 31 вендорский лендинг). Волна исключений
  датируется в основном 23 июля и с тех пор не повторялась.
- **Что делать (без затрат на разработку, в основном контент в Directus):**
  уникализировать описания карточек приоритетных вендоров, связать карточки
  тарифов внутренними ссылками с вендорских лендингов, для «тарифов-близнецов»
  выбрать основную карточку (объединение или canonical), после доработок
  отправлять страницы на переобход (`ops-yandex-recrawl`, `ops-indexnow`).
  Приоритет «высокий» — 53 URL (Adobe, Zoom, Figma, Autodesk, JetBrains,
  OpenAI, Canva, Miro, CorelDRAW + 3 посадочные `/solutions/*` и 2 категории
  каталога).

## Цифры

| Метрика | Значение |
|---|---|
| Страниц в поиске (in-search samples) | 186 |
| Исключено сейчас (последнее событие — REMOVED, не в поиске) | 161 |
| Исключено по счётчику сводки Вебмастера¹ | 32 |
| Причина LOW_QUALITY (МПК) | 160 |
| Причина NOTHING_FOUND | 1 |
| Дубли / редиректы / ошибки HTTP среди исключённых | 0 |
| Вернулись в поиск после исключения (июль–август) | 111 |

¹ Счётчик `excluded_pages_count` в сводке учитывает не все статусы
(МПК-страницы Яндекс часто показывает отдельно), поэтому опираемся на
события `REMOVED_FROM_SEARCH` без последующего возврата.

## Разбивка исключённых по типам

| Класс | Кол-во | Комментарий |
|---|---|---|
| Карточка товара (`/product/*`) — МПК | 154 | шаблонные тарифные карточки |
| Карточка товара — ошибка робота (NOTHING_FOUND) | 1 | `/product/jb-ai-ultimate`, отдаёт 200 |
| Малополезная посадочная (`/solutions/*`) | 3 | design-studios, it-companies, marketing-agencies |
| Малополезная категория (`/catalog/*`) | 2 | pm, system |
| Малополезная статья блога | 1 | podpiska-napryamuyu-ili-cherez-postavshchika |
| Дубль | 0 | — |
| Редирект | 0 | — |

## Почему выпали карточки товаров и что с ними делать

Карточка `/product/*` строится из Directus: название, цена,
`short_description`, `description`. У тарифов одного продукта текст почти
идентичен, объём уникального контента мал, входящих внутренних ссылок мало —
классический профиль МПК. Конкретные действия (легенда к таблице ниже):

- **У — уникализировать описание.** 150–300 слов на карточку в Directus
  (`description` + `meta_description`): для кого тариф, чем отличается от
  соседних, лимиты, что входит, условия покупки на юрлицо (счёт, договор,
  ЭДО, сроки 1–3 дня — по образцу эксперимента snippets-5-vendors).
- **О — определить основную карточку в группе тарифов-близнецов.**
  Либо объединить тарифы в одну карточку с выбором версии, либо оставить
  отдельные страницы, но на «младших» проставить canonical на основную
  (например, `zoom-wp-business-plus`/`-enterprise` → `zoom-wp-business`;
  `zoom-phone-*`, `framer-*`, `runway-*`, `recraft-*`, `heygen-*`,
  `wndr-filmora-*`, `ni-komplete-*`, `cdr-gs-*`, `dscrpt-*`). Требует
  отдельного согласования, т.к. меняет структуру каталога.
- **П — внутренние ссылки.** Блок «Тарифы и версии» на вендорском лендинге
  `/vendors/<vendor>` со ссылками на карточки; блок «Похожие продукты» на
  карточках; ссылки из статей блога. Вендорские лендинги в поиске (54 URL) —
  это готовые доноры ссылочного веса.
- **К — доработать контент страницы** (посадочные/категории/статья):
  кейсы, список ПО с ссылками на карточки, FAQ, SEO-текст категории.
- **Р — отправить на переобход** (`ops-yandex-recrawl`), после любых доработок.

После доработки партии страниц — переобход и контроль через 2–4 недели
повторным запуском `seo-data-collect`.

## Таблица: URL → класс → причина → действие → приоритет

Отсортировано по приоритету (выс → сред → низ), внутри — по URL.
«Дата» — дата исключения из поиска.

| URL | Класс | Причина | Действие | Приоритет | Дата |
|---|---|---|---|---|---|
| `/catalog/pm` | малополезная (категория) | МПК (LOW_QUALITY) | К+П | выс | 2026-07-23 |
| `/catalog/system` | малополезная (категория) | МПК (LOW_QUALITY) | К+П | выс | 2026-07-23 |
| `/product/adobe-acro-studio` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/adobe-ae` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/adobe-ai` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/adobe-animate` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/adobe-cc-pro` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/adobe-cc-std` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/adobe-dw` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/adobe-express` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/adobe-express-team` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/adobe-incopy` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/adobe-lr` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/adobe-photo` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-21 |
| `/product/adobe-single-team` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/adsk-3dsmax` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/adsk-mecoll` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/adsk-mudbox` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/canva-ent` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/cdr-gs-biz` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/cdr-gs-perp` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/cdr-gs-sub` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/figma-ent-dev` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/figma-org-collab` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/figma-org-dev` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/figma-prof-dev` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/int-collab-miro` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/int-design-figma` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/jb-ai-ultimate` | карточка товара | ошибка (NOTHING_FOUND) | Р, затем У+П | выс | 2026-07-29 |
| `/product/jb-all-pack-org` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/jb-clion-org` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/jb-dotultimate-org` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/jb-goland-org` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/jb-qodana` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/jb-rubymine-org` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/jb-youtrack` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/miro-business` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/miro-starter` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/openai-business` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/zoom-ai-companion` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/zoom-events` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/zoom-large-meeting-500` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/zoom-phone-global` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/zoom-phone-metered` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/zoom-phone-us-ca` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/zoom-rooms` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/zoom-webinars-500` | карточка товара | МПК (LOW_QUALITY) | У+П | выс | 2026-07-23 |
| `/product/zoom-wp-business` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/zoom-wp-business-plus` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/product/zoom-wp-enterprise` | карточка товара | МПК (LOW_QUALITY) | У+О+П | выс | 2026-07-23 |
| `/solutions/design-studios` | малополезная (посадочная) | МПК (LOW_QUALITY) | К+П | выс | 2026-07-23 |
| `/solutions/it-companies` | малополезная (посадочная) | МПК (LOW_QUALITY) | К+П | выс | 2026-07-23 |
| `/solutions/marketing-agencies` | малополезная (посадочная) | МПК (LOW_QUALITY) | К+П | выс | 2026-07-23 |
| `/product/artlst-pro` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/avid-mc-perp` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/avid-mc-sub` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/avid-pt-artist` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/avid-pt-ult-perp` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/bmd-resolve-studio` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/boris-continuum-perp` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/boris-continuum-sub` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/boris-mocha-perp` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/boris-sapphire-perp` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/boris-sapphire-sub` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/boris-suite-sub` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/deposit-pack-100` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/deposit-unl-month` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/deposit-unl-year` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/dscrpt-business` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/dscrpt-creator` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/eleven-creator` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/eleven-scale` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/envato-core` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-16 |
| `/product/envato-plus` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/envato-team-core` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-21 |
| `/product/fndry-katana-team` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/fndry-mari` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/fndry-nuke-studio` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/framer-basic` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/framer-ent` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/framer-pro` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-18 |
| `/product/framer-scale` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/freepik-premium` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/heygen-business` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/heygen-ent` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/heygen-pro` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/hou-core` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/hou-engine-ws` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/hou-indie` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/maxon-redshift` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/maxon-zbrush` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/mj-basic` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/mj-mega` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/moarr-everything` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/moarr-team` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/mono-myfonts` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-21 |
| `/product/mrmst-tb-sub-studio` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/mvls-ent-y` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/ni-komplete-sel` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/ni-komplete-std` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/ni-komplete-ult` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/ni-rx-std` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/recraft-advanced` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/recraft-basic` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/recraft-ent` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/recraft-team` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/rlsn-suite365` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/runway-ent` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/runway-max` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/runway-pro` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/runway-standard` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/shutter-img-10` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/shutter-img-50` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-16 |
| `/product/sketch-mac` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/sketch-pro` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-18 |
| `/product/topaz-gigapixel` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/topaz-video` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/vegas-edit-perp` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/vegas-post-sub` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/vegas-suite-perp` | карточка товара | МПК (LOW_QUALITY) | У+П | сред | 2026-07-23 |
| `/product/wndr-filmora-annual` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/wndr-filmora-perp-win` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/product/wndr-filmora-team` | карточка товара | МПК (LOW_QUALITY) | У+О+П | сред | 2026-07-23 |
| `/blog/podpiska-napryamuyu-ili-cherez-postavshchika` | малополезная (статья) | МПК (LOW_QUALITY) | К | низ | 2026-07-23 |
| `/product/astute-bundle` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/cdr-painter-sub` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/csp-ex-perp` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/csp-ex-sub` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/csp-pro-sub` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/dscrpt-hobbyist` | карточка товара | МПК (LOW_QUALITY) | У+О+П | низ | 2026-07-23 |
| `/product/epsnd-personal` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-21 |
| `/product/fmod-basic` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/fmod-premium` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/gaea-ent` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/gaea-pro` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/jb-ai-free` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/mono-ind-pro` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-16 |
| `/product/mrmst-tb-sub-ind` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-16 |
| `/product/mrmst-tb5-ind` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-21 |
| `/product/mvls-personal-m` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/mvls-personal-y` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/photon-ent` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/photon-fusion-2000` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/photon-fusion-500` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/prfrc-p4-cloud` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/prfrc-p4-platform` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/procr-ipad` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/rive-cadet` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/rive-voyager` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/rizom-rs-perp` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/rizom-rs-sub` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/rizom-vs-perp` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/rizom-vs-sub` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/spdtr-indie` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/spdtr-pro-fl` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/spdtr-pro-nl` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/tlstr-screenflow` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/tlstr-wirecast-pro` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/ue-realityscan` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/wwise-platinum` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |
| `/product/wwise-premium` | карточка товара | МПК (LOW_QUALITY) | У+П | низ | 2026-07-23 |

## Приложение: страницы, вернувшиеся в поиск сами (111)

Исключались в июле той же волной МПК и вернулись по мере доработок сайта:
66 карточек товаров, 31 вендорский лендинг, 9 страниц каталога, по одной —
solutions, about, cases, how-we-work, privacy. Основные даты возвратов:
24 июля, 1–14 августа, 18 августа. Их не трогаем — только наблюдаем, чтобы
не выпали снова (риск флаппинга: 154 URL за период имели ≥3 событий
появление/исключение).

## Ограничения данных

- API отдаёт выборки (samples), а не полный реестр: 858 событий поиска,
  1890 записей обхода — по данному сайту это полное покрытие (fetched = count).
- Эндпоинт `search-urls/samples` из ТЗ в API v4 отсутствует (404,
  RESOURCE_NOT_FOUND) — зафиксировано в данных; причины исключения взяты из
  `search-urls/events/samples` (событие REMOVED_FROM_SEARCH).
- Счётчик исключённых в сводке (32) расходится с событийным расчётом (161) —
  см. сноску ¹.

