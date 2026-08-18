# BIZSoft Search & Growth Intelligence

Ежедневная система SEO/Growth-аналитики biz-soft.pro: спрос → видимость → гипотеза → действие → эксперимент → лид → вывод. Отчёт-письмо в 9:00 (Бишкек, UTC+6) на avbelyaev@biz-soft.pro.

## Принципы

- Цепочка любого вывода: DATA → CHANGE → INTERPRETATION → BUSINESS IMPACT → ACTION → EXPECTED RESULT → VALIDATION.
- FACT (видно в данных) отделяется от HYPOTHESIS (требует проверки) и ACTION (как проверить).
- Числа не выдумываются: нет данных → «недостаточно данных для надёжного вывода». CPC/CPL/CAC без рекламных прогнозов не оцениваются.
- Каждый блок отчёта заканчивается «Резюме для руководителя» простыми словами + ожидаемая управленческая реакция.
- Блок без действия/решения — не нужен. Отчёт помогает не распыляться (обязателен раздел «Чего НЕ делать»).

## Конвейер

1. **Сбор** — `.github/workflows/seo-data-collect.yml` → `scripts/seo/collect.py` → сырые `data/gsc-*.json`, `data/yandex-*.json`, `data/metrika-*.json` (GSC: 28 дн, запросы/страницы/позиции/клики, задержка ~2–3 дня; Яндекс: индексация, ИКС, популярные запросы за 14 дн; Метрика: 14 дн — источники трафика, органика по ПС и посадочным, цели и их достижения `sumGoalReachesAny` — использовать в отчёте для блока конверсий: запрос→посадочная→визит→цель). Schedule GitHub не работает вне main — сборщик запускает агент (workflow_dispatch) в начале утреннего прогона.
2. **Обработка** — `scripts/seo/intelligence.py` (детерминированный, только факты) → `intelligence/<дата>.json`:
   - окна динамики (7д/пред.7д/28д GSC; Яндекс — по мере накопления срезов);
   - классификация запросов: интент (transactional_b2b/transactional/branded/informational/…), коммерческая ценность High/Medium/Low, vendor;
   - корзины: Quick Wins (поз. 4–15 + коммерческий интент), CTR Opportunities (поз. ≤7, CTR ниже ожидаемого), Near Top (8–20), топ-3/10/30;
   - Vendor Demand Radar, Page Intelligence, кандидаты PPC Research Radar;
   - **SEO Growth Score 0–100** — фиксированная прозрачная формула (веса SCORE_WEIGHTS и калибровки CALIBRATION в коде; компоненты без данных исключаются с перенормировкой); история в `intelligence/score-history.json`.
3. **Отчёт** — агент (утренняя Routine) интерпретирует intelligence-JSON и пишет `YYYY-MM-DD.html` (письмо) + `YYYY-MM-DD.md` (рабочая версия). Контрольные замеры выдачи (WebSearch, US-прокси) — вспомогательный сигнал по конкурентам; history.json — их история.
4. **Доставка** — `.github/workflows/seo-report-email.yml`: пуш отчёта → HTML-письмо на avbelyaev@biz-soft.pro (секрет SMTP_PASS, ящик hello@biz-soft.pro) + файлы пользователю в чат.

## Структура ежедневного отчёта (письма)

1. Executive Summary: Growth Score с дельтой, 3 изменения, 1 проблема, 1 возможность, 1 PPC/asymmetric.
2. Business Impact — что цифры значат для денег.
3. Search Visibility — Яндекс и Google раздельно, окна 24h/7d/28d (по мере накопления), сравнение только по данным.
4. Commercial Query Intelligence — Quick Wins, CTR gaps, Emerging, Lost.
5. Landing Page Intelligence. 6. Vendor Demand Radar. 7. Competitive Intelligence (+SERP-доминирование).
8. PPC Research & Acceleration Radar — обязателен ежедневно; если кандидатов нет, писать «сегодня нет экспериментов с достаточным потенциалом». Для кандидата: SEO Signal, What We Don't Know, эксперимент, Business Question. Бюджеты — только из прогнозов рекламного кабинета.
9. Asymmetric Growth Opportunities (Organic Route vs Paid Route + бизнес-вопрос).
10. SEO Opportunities (сниппеты с Current/Suggested title+description из реальных формулировок, контент, техника, перелинковка).
11. Risks/Alerts + Analytics Gaps (Метрика/GA4/CRM/Директ, пока не подключены — с планом).
12. Action Plan P0/P1/P2 — каждое действие: суть, Opportunity Score (Impact·Effort·Confidence·Speed·Commercial Value, 1–5 каждый), метрика успеха.
13. Active Experiments (реестры `intelligence/seo-experiments.json`, `intelligence/ppc-research-experiments.json`; статусы PPC: SCALE/SEO_INVEST/PPC_ONLY/RETEST/STOP).
14. What We Learned — что подтвердилось/опровергнуто. 15. What NOT To Do.

Стиль: аналитик + growth-стратег + коммерческий директор; факт → значение → действие; без рекламного оптимизма и SEO-жаргона без бизнес-смысла.

## Недельный и месячный отчёты

Недельный (понедельник, дополнительно к дневному): тренды, winners/losers, изменения спроса, результаты экспериментов, конкуренция, изменения backlog, бизнес-выводы — не сумма дневных. Месячный (1-е число): выручка/лиды/CAC/ROI при наличии данных, vendor growth, стратегические решения.

## Ограничения среды мониторинга

Яндекс, biz-soft.pro и рекламные кабинеты из контейнера недоступны (egress); данные ходят через GitHub Actions. WebSearch — US-прокси Google (только контроль конкурентов, не позиции). Не пытаться обходить.

## Процедура ежедневного прогона (для агента)

0. Запустить `seo-data-collect.yml` (workflow_dispatch, ref ветки), дождаться коммита данных, `git pull`.
1. Запустить `python3 scripts/seo/intelligence.py`, прочитать `intelligence/<дата>.json` (+сравнить со score-history и вчерашним intelligence-JSON: динамика, new/lost запросы).
2. WebSearch по корзине `keywords.json` → конкурентный контроль, дописать в `history.json`.
3. Написать отчёт (структура выше): html-письмо + md; каждый блок — с «Резюме для руководителя».
4. Обновить реестры экспериментов (статусы, новые кандидаты — только предложения; запуск PPC требует решения владельца).
5. Коммит и пуш (перед push — `git pull --rebase`); проверить успех воркфлоу seo-report-email; отправить оба файла пользователю (SendUserFile, html с display render).
6. Понедельник — добавить недельный отчёт `weekly/`; 1-е число — месячный `monthly/`.
