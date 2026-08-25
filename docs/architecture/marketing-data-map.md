# Карта данных маркетинговой/аналитической подсистемы — AS-IS (25.08.2026)

Все наборы данных: кто создаёт, где живут, кто читает, есть ли история,
можно ли анализировать отдельно. Классы: RAW / NORMALIZED / HISTORY / DERIVED /
INTELLIGENCE / RECOMMENDATION / REPORT / DIAGNOSTICS / LOG / CONFIG.

Главное правило чтения этой карты: **живые данные — в orphan-ветке `seo-data`**
(каталоги `reports/seo/{data,wordstat,intelligence,public}`); одноимённые файлы
в `main` — замороженный срез на 21.08.2026, оставленный как фикстуры тестов
(коммит `c7693a6`, PR #138). Каталоги `reports/seo/semantics`, `reports/seo/tasks`
и корневые файлы `reports/seo/*.json` живут только в `main`.

---

## 1. Producer → Consumer (обязательная карта)

| Producer | Данные | Хранение | Consumer | Бизнес-использование | История |
|---|---|---|---|---|---|
| GSC API → `collect.py` | показы/клики/позиции Google: дневной ряд ~26 дн, топ-запросы, страницы | `data/gsc-<дата>.json` (seo-data) | `snapshot.py` | видимость в Google | накапливается по датам с 18.08; внутри файла ряд 26 дн |
| Вебмастер API → `collect.py` | SQI, индексация, проблемы, топ-100 популярных запросов (из 506) за окно 12–14 дн | `data/yandex-<дата>.json` | `snapshot.py` | видимость в Яндексе | по датам с 18.08; дневного ряда нет в принципе (тикет DATA-002) |
| Метрика API → `collect.py` | визиты, источники, органика, цели счётчика | `data/metrika-<дата>.json` | `snapshot.py` | трафик и конверсии | по датам; окно 14 дн |
| GA4 API → `collect.py` | сессии, каналы, органические лендинги | `data/ga4-<дата>.json` | `snapshot.py` | трафик (второе мнение) | по датам; окно 14 дн |
| Wordstat API → `wordstat/run.py` | сырые ответы topRequests/dynamics/regions | `wordstat/cache/<hash>.json` (RAW) | `client.py` (кэш), больше никто | экономия квоты; **регионы — никем не читаются** | TTL 30/30/90 дн; всё получено 20–21.08 |
| `wordstat/run.py` | журнал каждого платного вызова: причина, стоимость, статус | `wordstat/ledger/2026-08.jsonl` (LOG/HISTORY, append) | `budget.py`, `report.py` | учёт бюджета 5 500 ₽/мес | помесячные файлы; фактически с 20.08 |
| `wordstat/universe.py` | 19 440 фраз × 37 полей: частотность, интент, кластер, привязка к странице, история | `wordstat/semantic-universe.jsonl` (NORMALIZED+HISTORY) | `report.py`, `coverage.py`, `opportunity.py`, `vendor_expansion.py` | база знаний о спросе | история в полях строк; помесячная динамика — у 101 фразы за 12 мес; дневной ряд загрязнён кэш-хитами |
| `wordstat/report.py` | покрытие, разрывы GAP-A…H, возможности, кандидаты-вендоры | `wordstat/intelligence-state.json` (INTELLIGENCE) | `report_v4.py`, `webreport.py` | блок спроса в письме и веб-отчёте | **перезапись, истории нет**; человекочитаемая история — `<дата>-demand-report.md` |
| `snapshot.py` | канонический срез дня по всем источникам | `intelligence/snapshots/<дата>.json` (NORMALIZED+DERIVED) | `quality.py`, `report_v4.py`, `webreport.py`, wordstat `coverage.py` | «единственный источник цифр» | по датам с 19.08; сравнение в коде — только день к дню |
| `quality.py` | 19 проверок, статус здоровья, publication_rules | `intelligence/data-quality/<дата>.json` (DIAGNOSTICS+CONFIG) | `report_v4.py`, `webreport.py`, `contentcheck.py` | блокировка недостоверных выводов | по датам |
| `report_v4.py` + `charts_v4.py` | письмо (email/preview/txt/eml), блоки, PNG | `intelligence/<дата>-v4*`, `charts/` (REPORT/DERIVED) | `seo-report-email.yml`, гейты | ежедневное информирование | по датам |
| `webreport.py` | полный веб-отчёт | `public/daily/<дата>/index.html`, `public/latest.html` (REPORT) | `seo-publish-web` → nginx → руководитель | полные таблицы, журнал, методика | daily накапливается в git; на сервере — зеркало с `--delete`; latest перезаписывается |
| seo-site-check | счётчики на проде, состояние страниц эксперимента | `intelligence/tags-check.json`, `site-check-<дата>.json` (RAW/DIAGNOSTICS) | `report_v4.py` (экспозиция) | контроль «сайт реально измеряется» | tags-check перезапись; site-check по датам |
| агент Routine (вручную) | реестр задач: статусы, зоны GREEN/YELLOW/RED, сроки, PR/CI | `intelligence/actions.json` (CONFIG+RECOMMENDATION) | `report_v4.py` (блоки «От вас», журнал, контрольные точки), `uxlint_v4.py` | управленческий журнал | перезапись на месте; история — только в git-коммитах seo-data |
| `experiments.py` / агент | реестр экспериментов | `intelligence/seo-experiments.json` (HISTORY+CONFIG) | `snapshot.py`, `experiments.py` | контроль экспериментов | append записей |
| `semantics.py` (заморожен) | спрос старого контура: core, brief, gap | `reports/seo/semantics/` (только main) | `snapshot.build_market_demand` ← `brief-*.json` | блок market_demand снимка | последний замер 20.08; **вне data_sync — стареет** |
| человек | реестр пределов измерения (ANL-001…, SEM-002…) | `reports/seo/measurement-limits.json` (CONFIG+HISTORY) | `quality.py`, `goals_health.py` | границы честного сравнения | журнал лимитов; 3 из 6 открыты |
| человек | тикеты | `reports/seo/tasks/*.md` (RECOMMENDATION) | люди | работы по находкам | по файлам, только main |
| `ops-me-crawl` | снимки магазина ManageEngine | `data/sources/manageengine/<дата>/` (RAW), ветка `claude/me-sources` | `me-parse/taxonomy/verify.mjs` | источники цен/номенклатуры вендора | снимки по датам |
| `src/lib/analytics.ts` (код сайта) | реестр целей GOALS (18 целей, key-флаги) | main (CONFIG) | сайт (trackGoal), `goals_sync.py`, `goals_health.py`, `snapshot.py` | единое определение конверсий | git-история |

## 2. Карта файлов (обязательная)

Полнота: перечислены все существенные файлы; пути — относительно
`reports/seo/`, если не оговорено. «Перезапись»: п — перезаписывается,
н — накапливается (датированные файлы), з — заморожен.

| Путь | Создаёт | Читает | Смысл | Класс | Переза­пись | История |
|---|---|---|---|---|---|---|
| `data/{gsc,yandex,metrika,ga4}-<дата>.json` | collect.py | snapshot.py | сырые срезы источников | RAW | н | с 18.08 (seo-data) |
| `intelligence/snapshots/<дата>.json` | snapshot.py | quality, report_v4, webreport, coverage | канонический срез | NORMALIZED/DERIVED | н | с 19.08 |
| `intelligence/data-quality/<дата>.json` | quality.py | report_v4, webreport, contentcheck | качество + правила публикации | DIAGNOSTICS/CONFIG | н | с 19.08 |
| `intelligence/<дата>-v4-email.html/.txt/.eml/.html` | report_v4.py | seo-report-email | письмо | REPORT | н | с 19.08 |
| `intelligence/<дата>-v4-blocks.json` | report_v4.py | тесты (и только) | структурные блоки письма | DERIVED | н | с 19.08 |
| `intelligence/<дата>-v4-{uxlint,content,render}.json` | uxlint_v4/contentcheck/emailcheck | регламент прогона | результаты гейтов | DIAGNOSTICS | н | с 19.08 |
| `intelligence/charts/<дата>-*.png` | charts_v4.py | письмо (CID), webreport | графики | DERIVED | н | с 19.08 |
| `intelligence/previews/*.png` | previews_v4.py | человек | скриншоты письма | DIAGNOSTICS | н | ~24 МБ, самый тяжёлый каталог |
| `intelligence/actions.json` | агент | report_v4, uxlint_v4, webreport | реестр задач | CONFIG/RECOMMENDATION | п | только git seo-data |
| `intelligence/seo-experiments.json` | агент/experiments | snapshot, experiments | реестр экспериментов | HISTORY/CONFIG | п (append записей) | да |
| `intelligence/site-check-<дата>.json`, `tags-check.json` | seo-site-check | report_v4 | факт с прода | RAW/DIAGNOSTICS | н / п | с 19.08 |
| `intelligence/last-mailed.txt` | seo-report-email | seo-report-email | защита от дублей письма | STATE | п | только seo-data |
| `intelligence/score-history.json` | intelligence.py (выбыл) | никто | история Growth Score v1 | HISTORY | з (19.08) | 2 записи |
| `intelligence/2026-08-1{8,9}.json` | intelligence.py (выбыл) | никто | аналитика v1 | INTELLIGENCE | з | UNUSED |
| `intelligence/ppc-research-experiments.json` | — | никто | пустой реестр | CONFIG | з | UNUSED |
| `wordstat/semantic-universe.jsonl` | universe.py | report, coverage, opportunity, vendor_expansion | база семантики | NORMALIZED/HISTORY | п (файл), история в полях | 20 МБ, 7 версий за 3 дня в истории seo-data |
| `wordstat/intelligence-state.json` | report.py | report_v4, webreport | текущая аналитика спроса | INTELLIGENCE | п | нет |
| `wordstat/<дата>-demand-report.md` | report.py | человек | отчёт спроса | REPORT | н | с 19.08 |
| `wordstat/cache/<hash>.json` | client.py | client.py | сырые ответы API | RAW | н (по TTL удаляются) | 398 файлов |
| `wordstat/ledger/<месяц>.jsonl` | budget.py | budget, report | журнал бюджета | LOG/HISTORY | append | с 20.08 |
| `wordstat/{config,vendor-candidates,decisions}.json` | человек | run/report-цепочка | настройки, 149 кандидатов, решения руководителя | CONFIG | п | git |
| `wordstat/{limiter-state,last-runs,pattern-stats}.json` | код | код | межпрогонное состояние | STATE | п | нет |
| `wordstat/{brand-dominance,payment-check}.json` | brand_dominance/payment_check | normalize/vendor_expansion | замеры омонимов; оплата картой у вендоров | DERIVED | п | нет |
| `public/daily/<дата>/index.html` (+README.md) | webreport.py | nginx → руководитель | полный веб-отчёт | REPORT | н | с 19.08 |
| `public/latest.html` | webreport.py | руководитель (постоянная ссылка) | последний отчёт | REPORT | п | нет |
| `public/report-url.txt` | человек | report_v4 | адрес веб-отчёта (сейчас — артефакт Claude, не прод) | CONFIG | п | — |
| `semantics/{plan,clusters,discovery}.json` | человек | старый контур | план замера спроса v1 | CONFIG | з | main |
| `semantics/core-<дата>.json`, `brief-<дата>.json`, `gap-<дата>.md` | semantics.py (заморожен) | snapshot.py ← brief | спрос v1 | RAW/DERIVED/REPORT | з (посл. 20.08) | main |
| `history.json` | вручную (до v2) | никто | ручные замеры позиций 17–19.08 | HISTORY | з | UNUSED |
| `keywords.json` | вручную | **никто (0 упоминаний)** | 10 запросов | CONFIG | з | UNUSED |
| `measurement-limits.json` | человек | quality, goals_health | журнал пределов измерения | CONFIG/HISTORY | п | ключевой реестр |
| `tasks/*.md` (10 тикетов) | человек | люди | тикеты работ | RECOMMENDATION | н | main |
| `2026-08-1{7,8,9}.{md,html}` | вручную (v1) | fallback seo-report-email | старые отчёты | REPORT | з | легаси |
| `TRIGGER.md` | человек | Routine (источник истины промпта) | регламент ежедневного прогона | CONFIG | п | критичный файл |
| `README.md` | человек | люди | описание конвейера | DOC | п | частично устарел (Bishkek, report_v3/charts.py) |
| `../marketing/*.md` (6 документов) | аудит 21.08 | люди | прошлый аудит аналитики (25 находок) | REPORT/DOC | з | описывают схему до переезда данных |
| `../../data/yandex-2026-08-{19,20}.json` (корень data/) | вручную | compare.py (ручной) | глубокие выгрузки Вебмастера (336 исключённых URL и пр.) | RAW | з | UNUSED автоматически |

## 3. Историческая ценность: что реально доступно

- **Полная история конвейера — 8 дней данных** (18–25.08 в `seo-data`),
  git-истории ветки — 3 дня (создана снимком 23.08). Более ранних SEO-данных
  не существует нигде: сбор начался 17–18.08.2026.
- **Единственные настоящие временные ряды:**
  1) дневной ряд Google внутри каждого `gsc-*.json` (~26 дней, лаг 2–3 дня);
  2) помесячная динамика Wordstat у 101 фразы (12 месяцев);
  3) append-журналы: wordstat ledger, git-коммиты seo-data.
- **Ряды, которых нет:** дневной ряд Яндекс.Вебмастера (API отдаёт агрегат
  окна — тикет DATA-002); история аналитических срезов
  (`intelligence-state.json`, `actions.json` перезаписываются); история
  регионов и глубокая история спроса.
- **Методические границы сравнения** (`measurement-limits.json`): конверсии
  несравнимы через 21.08 (цели заведены), key events GA4 — через 18.08,
  спрос — через смену правил отбора; 3 из 6 лимитов открыты. Даже накопив
  60 дней данных, честно сравнивать «до/после» этих дат нельзя.
- **Ответ на вопрос «можно ли спросить, как менялся спрос на X за 60 дней»:
  сегодня НЕТ** (для 101 фразы — да, но помесячно и с лагом месяц).

## 4. Повторное использование данных без новых API-запросов

| Источник | Повторный анализ возможен? | Основание |
|---|---|---|
| Wordstat | **ДА** — сырые ответы в cache/, нормализованная база в universe, модули анализа чистые (без сети) | см. `wordstat-audit.md` §11 |
| GSC | ДА — сырые rows в `data/gsc-*.json`, включая неиспользуемый дневной ряд | файлы самодостаточны |
| Вебмастер | ЧАСТИЧНО — только то, что попало в срез (топ-100 из 506 запросов); остальное не собрано | `collect.py` |
| Метрика | ДА в пределах окна 14 дн; поля sampled/data_lag сохранены, но не используются | файлы RAW |
| GA4 | ДА в пределах окна 14 дн | файлы RAW |

## 5. Недоиспользуемые данные (собираются, применяются уже — но меньше, чем могли бы)

| Данные | Сейчас используется для | Дополнительно можно | Что потребуется |
|---|---|---|---|
| Дневной ряд GSC (26 дн в каждом файле) | last7 vs prev7 | недельные/месячные тренды, сезонность по дням недели | читатель ряда глубже 7 дней |
| monthly_dynamics Wordstat (101 фраза × 12 мес) | TREND_FACTOR и GAP-G/H | полноценный мониторинг спроса по всем коммерческим кластерам | расширить план динамики (квота позволяет с запасом) |
| Ledger Wordstat | предохранители бюджета | аналитика эффективности исследования (стоимость знания) | отчёт по ledger |
| `*-v4-blocks.json` | тесты | машинный анализ истории писем (что сообщалось руководителю) | читатель |
| Поля sampled/sample_share/data_lag Метрики и GA4 | не используются | пометки достоверности в отчёте | правка snapshot |
| 506 популярных запросов Вебмастера (берётся 100) | топ-100 | полнее видимость Яндекса | поднять лимит выборки в collect.py |
| site-check-<дата>.json | экспозиция эксперимента | история состояния прода | читатель истории |
| Git-история seo-data (7–11 коммитов/сутки) | восстановление | история actions.json / intelligence-state задним числом | git-археология |

## 6. Бесполезно собираемое / мёртвое (UNUSED COLLECTION)

| Артефакт | Факт |
|---|---|
| Регионы Wordstat (227 вызовов, 2,70 ₽ = 27 % расхода API) | лежат только в cache/, ни один модуль не читает |
| `keywords.json` | 0 упоминаний в репозитории |
| `history.json` | читателей нет, заморожен 19.08 |
| `intelligence/2026-08-1{8,9}.json`, `score-history.json` | продукт выбывшего `intelligence.py`; содержит упразднённый Growth Score и неутверждённую CTR-модель |
| `ppc-research-experiments.json` | пустой, никем не читается |
| SVG-графики и google-wow/measure-map PNG | производители (`charts.py`, `charts_png.py`) выпали из конвейера V4 |
| `previews/` 24 МБ | потребитель — только человек; главный источник роста веса |
| `data/yandex-2026-08-*.json` (корень) | разовые ручные выгрузки; писателя в коде нет |
| Копии `reports/seo/**` в main (535 файлов, 48,6 МБ) | остались после переезда #138 «до контрольного периода»; чистка запланирована Routine 30.08 |

## 7. Git как хранилище данных: диагностика

**Как устроено.** Машинные данные коммитятся в orphan-ветку `seo-data`
(без общего предка с main — случайное слияние невозможно). Автор всех
коммитов — «Claude», 7–11 коммитов в сутки. Append-файлы дают честную
историю; перезаписываемые файлы имеют историю только на уровне git-коммитов.

**Преимущества (фактически используемые):** бесплатная история и
воспроизводимость (каждый отчёт можно пересобрать из данных его дня);
provenance на уровне коммитов; отсутствие отдельной инфраструктуры БД;
push-триггеры GitHub как шина событий (письмо и публикация запускаются
пушем данных).

**Ограничения (наблюдаемые):**
- рост: дерево seo-data 74 МБ, ~19 МБ/сутки on-disk; главный вклад —
  7 версий 20-мегабайтного `semantic-universe.jsonl` за 3 дня (~73 % истории
  ветки) и несжимаемые PNG-превью; README ветки предусматривает ежемесячный
  squash — ещё ни разу не выполнялся;
- в main остался балласт 48,6 МБ данных (каждый clone тянет);
- запросов «срез по датам» нет: анализ истории перезаписываемых файлов —
  это git-археология, не запрос к данным;
- гонки решаются «последний победил» (`rebase -X theirs` + полная замена
  каталогов) — возможна тихая потеря результата прогона;
- для бизнес-пользователя данные в git невидимы без веб-отчёта.
