#!/usr/bin/env python3
"""Проверки качества данных перед генерацией отчёта (schema v2).

Выполняются ДО формирования текста. Критическая ошибка запрещает публикацию
неподтверждённых выводов и общий «зелёный» статус в отчёте.

Запуск: python3 scripts/seo/quality.py [YYYY-MM-DD]
Результат: reports/seo/intelligence/data-quality/<дата>.json
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import measurement  # noqa: E402
import snapshot as snapshot_mod  # noqa: E402

SNAP_DIR = pathlib.Path("reports/seo/intelligence/snapshots")
OUT_DIR = pathlib.Path("reports/seo/intelligence/data-quality")


def delta(current, previous):
    """Абсолютная и относительная дельта. Относительная — только при previous > 0."""
    if current is None or previous is None:
        return {"absolute": None, "relative": None, "low_base": None}
    absolute = current - previous
    relative = (absolute / previous) if previous > 0 else None
    return {"absolute": absolute, "relative": relative,
            "low_base": previous > 0 and previous < 30}


def ctr(clicks, impressions):
    if not impressions:
        return None
    return clicks / impressions


def overlap_days(a_start, a_end, b_start, b_end):
    if not all([a_start, a_end, b_start, b_end]):
        return None
    a1, a2 = dt.date.fromisoformat(a_start), dt.date.fromisoformat(a_end)
    b1, b2 = dt.date.fromisoformat(b_start), dt.date.fromisoformat(b_end)
    latest_start, earliest_end = max(a1, b1), min(a2, b2)
    return max(0, (earliest_end - latest_start).days + 1)


def sample_churn(cur: dict, prev: dict | None) -> dict | None:
    """Насколько сменился состав выборки запросов между снимками.

    Вебмастер отбирает запросы по числу показов, поэтому список пересобирается
    от сбора к сбору. На 20.08 → 21.08 сменилось 26 запросов из 100: вошедшие
    принесли 92 показа, выбывшие унесли 55. Треть заявленного прироста в 107
    показов создала сама пересборка списка.
    """
    if not prev or not cur.get("available") or not prev.get("available"):
        return None
    cur_map = {e["entity_id"]: (e.get("impressions") or 0) for e in cur.get("entities") or []}
    prev_map = {e["entity_id"]: (e.get("impressions") or 0) for e in prev.get("entities") or []}
    if not cur_map or not prev_map:
        return None
    entered, left = set(cur_map) - set(prev_map), set(prev_map) - set(cur_map)
    changed = max(len(entered), len(left))
    return {
        "changed": changed,
        "previous": len(prev_map),
        "share": changed / len(prev_map),
        "gained": sum(cur_map[q] for q in entered),
        "lost": sum(prev_map[q] for q in left),
    }


LIMITS_PATH = pathlib.Path("reports/seo/measurement-limits.json")


def load_measurement_limits() -> list:
    """Реестр объявленных пределов измерения.

    Лежит данными, а не в коде: закрыть запись после починки счётчика должно
    быть правкой одного поля, а не выкладкой.
    """
    if not LIMITS_PATH.exists():
        return []
    try:
        return json.loads(LIMITS_PATH.read_text(encoding="utf-8")).get("limits", [])
    except (ValueError, OSError):
        return []


def run_checks(snap: dict, prev: dict | None = None) -> dict:
    findings: list[dict] = []
    prev_yandex = (prev or {}).get("yandex")

    def add(level, code, title, detail, effect=None, source=None):
        # source — машиночитаемый ключ источника (yandex|google|metrika|ga4):
        # письмо сопоставляет находку с карточкой по нему, а не по подстроке
        # русского заголовка. Поле необязательное: старые файлы data-quality
        # без него читаются как прежде.
        findings.append({"level": level, "code": code, "title": title,
                         "detail": detail, "effect_on_report": effect,
                         "source": source})

    yx, g, an = snap["yandex"], snap["google"], snap["analytics"]

    # 0. Недоступные источники: письмо обязано назвать источник, причину и период
    #
    # «Выгрузки нет» (missing) и «источник вернул ошибку» (error) — разные
    # состояния: первое чинится в конвейере сбора, второе — в доступах и API.
    # Оба отличаются от «источник не обновился», при котором данные есть, но
    # latest_event_date не сдвинулась, — то состояние письмо помечает само.
    for key, label, blk in (("yandex", "Яндекс.Вебмастер", yx),
                            ("google", "Google Search Console", g),
                            ("metrika", "Яндекс.Метрика", an.get("metrika") or {}),
                            ("ga4", "GA4", an.get("ga4") or {})):
        if blk.get("available"):
            continue
        src = blk.get("source") or {}
        period = (f"{src['current_period_start']}–{src['current_period_end']}"
                  if src.get("current_period_start") else "период неизвестен")
        reason = {"missing": "выгрузки нет",
                  "empty": "источник ответил без данных",
                  "malformed": "формат выгрузки не распознан"}.get(
            src.get("status"), "источник вернул ошибку")
        add("critical", "SOURCE_UNAVAILABLE",
            f"{label}: {reason}",
            f"{blk.get('error') or 'нет данных'} ({period}).",
            "Показатели источника публикуются как «нет данных», а не ноль; "
            "дельты и сравнения по нему не публикуются.", source=key)

    # 0б. Источник доступен, но не обновился: latest_event_date не сдвинулась.
    #
    # Третье состояние из триады «нет выгрузки / ошибка / не обновился»:
    # данные есть и они валидны, но повторяют предыдущий сбор. Их изменение
    # публиковать как новость нельзя — это одно наблюдение, поданное дважды.
    prev_an = (prev or {}).get("analytics") or {}
    for key, label, cur_b, prev_b in (
            ("yandex", "Яндекс.Вебмастер", yx, (prev or {}).get("yandex") or {}),
            ("google", "Google Search Console", g, (prev or {}).get("google") or {}),
            ("metrika", "Яндекс.Метрика", an.get("metrika") or {},
             prev_an.get("metrika") or {}),
            ("ga4", "GA4", an.get("ga4") or {}, prev_an.get("ga4") or {})):
        if not (cur_b.get("available") and prev_b.get("available")):
            continue
        cur_last = (cur_b.get("source") or {}).get("latest_event_date")
        prev_last = (prev_b.get("source") or {}).get("latest_event_date")
        if cur_last and cur_last == prev_last:
            add("info", "SOURCE_NOT_UPDATED",
                f"{label}: данные не обновились",
                f"Последняя дата события прежняя — {cur_last}.",
                "Значения повторяют предыдущий сбор; их совпадение с вчерашними "
                "не является новым наблюдением и не подаётся как новость.",
                source=key)

    # 0в. Дневная факт-витрина: полнота окон KPI.
    #
    # Окна равной длины строит отчёт из дневных рядов; дыра в окне — это
    # настоящий сбой (день не собрался и не был дозаполнен), а не особенность
    # источника. Отсутствие витрины — деградация до старого агрегатного пути.
    daily = snap.get("daily") or {}
    daily_labels = {"yandex": "Яндекс.Вебмастер", "gsc": "Google Search Console",
                    "metrika": "Яндекс.Метрика", "ga4": "GA4"}
    for key, label in daily_labels.items():
        blk = daily.get(key) or {}
        if not blk.get("available"):
            add("warning", "DAILY_MISSING",
                f"{label}: дневная витрина не заполнена",
                blk.get("error") or "рядов по дням нет.",
                "KPI по источнику считается по агрегатному пути со скользящими "
                "окнами; дельты публикуются только при сопоставимых окнах.",
                source=key)
        elif not blk.get("complete"):
            add("critical", "DAILY_GAP",
                f"{label}: пропуски в окнах дневной витрины",
                "Нет значений за: " + ", ".join(blk.get("missing_dates") or []) + ".",
                "Дельта по неполному окну не публикуется: пропущенный день — "
                "несобранные данные, а не измеренный ноль.", source=key)
    # KPI Яндекса считается из витрины, когда оба окна полны.
    yx_daily_ok = bool((daily.get("yandex") or {}).get("complete"))

    # 1. Скользящее окно Яндекса: сравнение периодов пересекается
    if yx.get("available"):
        s = yx["source"]
        ov = overlap_days(s["current_period_start"], s["current_period_end"],
                          s["comparison_period_start"], s["comparison_period_end"])
        if ov:
            add("warning", "ROLLING_WINDOW_OVERLAP",
                "Периоды Яндекс.Вебмастера пересекаются",
                f"Текущее окно {s['current_period_start']}–{s['current_period_end']} "
                f"({s['current_period_days']} дн.) пересекается с предыдущим на {ov} дн.",
                "Изменение показов день к дню не является сравнением независимых периодов; "
                "относительные проценты не публикуются.")
        # 1б. Длина окон сравнения
        #
        # Пересечение окон проверялось и раньше, а вот равенство их длины — нет,
        # хотя оба значения уже лежат в source_meta. Между 20.08 и 21.08 окна
        # были 12 и 13 дней: лишние сутки давали около 74 показов при заявленном
        # приросте 107. Абсолютная дельта — ровно то, что портит эта разница,
        # поэтому проверка критическая.
        cur_days, cmp_days = s.get("current_period_days"), s.get("comparison_period_days")
        if cur_days and cmp_days and cur_days != cmp_days:
            # При полной дневной витрине KPI и дельты считаются по окнам
            # равной длины, и плавающее окно агрегата задевает только
            # выборку запросов в блоке возможностей — это предупреждение,
            # а не сбой.
            add("warning" if yx_daily_ok else "critical", "WINDOW_LENGTH_MISMATCH",
                "Окна сравнения разной длины",
                f"Текущее окно {cur_days} дн., предыдущее {cmp_days} дн. "
                f"Задержка источника плавает, длина окна вслед за ней.",
                "Абсолютная разница показов не публикуется: она включает вклад "
                "лишних суток. Публикуется среднее за день с указанием длины окна.")

        # 1в. Смена состава выборки
        #
        # Вебмастер отбирает запросы по TOTAL_SHOWS, поэтому между сборами
        # список пересобирается. Сумма по разным множествам — не изменение
        # видимости, а другой набор слагаемых.
        churn = sample_churn(yx, prev_yandex)
        if churn and churn["share"] > 0.10:
            # Смена состава выборки больше не трогает KPI: показы всего сайта
            # идут из дневной витрины. Предупреждение остаётся для блока
            # возможностей, который по-прежнему опирается на выборку.
            add("warning" if yx_daily_ok else "critical", "SAMPLE_CHURN",
                "Состав выборки запросов изменился",
                f"Сменилось {churn['changed']} из {churn['previous']} запросов "
                f"({churn['share']:.0%}). Вошедшие принесли {churn['gained']} показов, "
                f"выбывшие унесли {churn['lost']}.",
                "Разница сумм по двум разным множествам запросов не является "
                "изменением видимости и не публикуется как дельта.")

        # 2. Scope выборки
        add("warning", "YANDEX_SAMPLE_SCOPE",
            f"Метрики Яндекса рассчитаны по выборке {yx['totals'].get('queries_fetched')} "
            f"из {yx['totals'].get('queries_available')} запросов",
            f"Показы {yx['totals']['impressions']} и клики {yx['totals']['clicks']} — "
            f"сумма по {yx['totals'].get('queries_fetched')} запросам из API popular "
            f"queries, не по всему сайту.",
            "CTR Яндекса нельзя называть CTR сайта.")
        if (yx["totals"].get("queries_available") or 0) > (yx["totals"].get("queries_fetched") or 0):
            add("warning", "SAMPLE_TRUNCATED",
                "Источник отдал не все запросы",
                f"Доступно {yx['totals']['queries_available']}, забрано "
                f"{yx['totals']['queries_fetched']}.",
                "Длинный хвост запросов в показателях не учтён.")

    # 3. Кросс-источниковая сверка: клики поиска против визитов/сессий
    if yx.get("available") and an.get("metrika", {}).get("available"):
        clicks = yx["totals"]["clicks"]
        visits = an["metrika"]["organic_visits"]
        sessions = an.get("ga4", {}).get("organic_sessions")
        # Клики по выборке топ-100 запросов и визиты всего сайта измеряют разные
        # множества. Их отношение — не «расхождение источников», а разница охвата,
        # поэтому это ограничение (limited), а не поломка (degraded).
        if clicks is not None and visits and not measurement.scopes_comparable(snap):
            # Разбивка органики по поисковым системам сужает сверку: клики
            # Вебмастера корректно ставить рядом с визитами именно из Яндекса,
            # а не со всей органикой сайта, куда входит и Google.
            by_engine = an["metrika"].get("organic_by_engine") or {}
            ya_visits = by_engine.get("Yandex")
            engine_note = (f"из них из Яндекса — {ya_visits:.0f}; "
                           if ya_visits is not None else "")
            add("warning", "SCOPE_MISMATCH",
                "Охваты поиска и аналитики различаются",
                f"Яндекс.Вебмастер: {clicks} кликов по выборке "
                f"{yx['totals']['queries_tracked']} запросов "
                f"({yx['source']['current_period_start']}–{yx['source']['current_period_end']}); "
                f"Метрика: {visits:.0f} органических визитов всего сайта, "
                f"{engine_note}"
                f"GA4: {sessions} органических сессий "
                f"({an['metrika']['source']['current_period_start']}–"
                f"{an['metrika']['source']['current_period_end']}).",
                "Клики выборки и визиты сайта не сравниваются между собой: "
                "сопоставимая пара — клики выборки Вебмастера и органические "
                "визиты из Яндекса, и даже она различается охватом (выборка "
                "против всего сайта). CTR публикуется как CTR выборки; вывод "
                "о кликабельности всего сайта не делается.")

    # 4. Разные окна аналитики и поиска
    if an.get("metrika", {}).get("available") and yx.get("available"):
        if an["metrika"]["source"]["current_period_end"] != yx["source"]["current_period_end"]:
            add("warning", "PERIOD_MISMATCH",
                "Окна источников не совпадают",
                f"Вебмастер до {yx['source']['current_period_end']}, "
                f"Метрика до {an['metrika']['source']['current_period_end']}.",
                "Показатели поиска и аналитики не складываются в одну воронку без оговорки.")

    # 5. Изменение разметки конверсий внутри периода
    # Разметка GA4 объявлена в реестре пределов (ANL-002) — проверка ниже, в 5б.
    # Держать её ещё и здесь значило бы иметь два источника правды об одном факте.

    # 5б. Объявленные пределы измерения
    #
    # Ноль по неизмеряемому показателю — не результат, а отсутствие замера.
    # Разница принципиальная: «обращений не было» требует объяснения и действий,
    # «не измерялось» требует починки счётчика.
    ga4_src = an.get("ga4", {}).get("source") or {}
    start = ga4_src.get("current_period_start") or ""
    end = ga4_src.get("current_period_end") or snap.get("report_date", "")
    for lim in load_measurement_limits():
        resolved = lim.get("resolved_on")
        # Запись, объявленная заранее, молчит до своей даты: предупреждать о том,
        # что ещё не сделано, значит приучать читателя пропускать этот раздел.
        if lim.get("status") == "planned" and not resolved:
            continue
        if not resolved:
            add("warning", "MEASUREMENT_GAP",
                lim["title"],
                f"{lim['detail']} Источник: {lim['evidence']}.",
                lim["rule"])
        elif start and start <= resolved <= end:
            add("warning", "MEASUREMENT_CHANGE",
                f"{lim['title']}: методика изменилась внутри периода",
                f"{lim['detail']} Изменение вступило в силу {resolved}, окно {start}–{end}.",
                lim["rule"])

    # 6. Пересборы внутри дня
    for rev in an.get("intra_day_revisions", []):
        add("warning", "INTRA_DAY_REVISION",
            "Показатель пересчитывался в течение дня",
            f"{rev['metric']}: наблюдались значения {rev['values_seen']}; "
            f"каноническое — {rev['canonical']}.",
            "В отчёте публикуется одно каноническое значение из актуального snapshot.")

    for rev in snap.get("data_revisions", []):
        add("warning", "BASELINE_REVISED",
            "Базовое значение пересматривалось источником",
            f"{rev['metric']} за {rev['date']}: значения {rev['values_seen']}, "
            f"каноническое {rev['canonical']}.",
            "Изменение относительно предыдущего дня считается от канонического значения; "
            "ранее опубликованные дельты, взятые от промежуточного сбора, недействительны.")

    # 7. Низкая выборка по конверсиям
    if an.get("metrika", {}).get("available"):
        events = an["metrika"]["organic_goal_events"]
        if events is not None and events < snap["thresholds"]["low_conversions"]:
            add("warning", "LOW_CONVERSION_SAMPLE",
                "Недостаточная выборка по целевым событиям",
                f"Зафиксировано {events:.0f} целевых событий (порог надёжности — "
                f"{snap['thresholds']['low_conversions']}).",
                "Доли конверсии публикуются только с указанием n и маркером низкой выборки; "
                "события не называются заявками.")
        if an["metrika"]["unique_goal_users"] is None:
            add("warning", "GOAL_UNIQUENESS_UNKNOWN",
                "Уникальность целевых обращений не подтверждена",
                "Собираются goal events (ym:s:sumGoalReachesAny) без дедупликации по посетителю.",
                "Формулировка «заявка/лид» запрещена; используется «целевое событие».")

    # 8. Scope: query vs page (Google)
    if g.get("available"):
        t = g["totals"]
        if t["queries_position_le_10"] == 0 and t["pages_position_le_10"] > 0:
            add("info", "SCOPE_QUERY_VS_PAGE",
                "Разные scope: запросы и страницы считаются отдельно",
                f"Запросов со средней позицией ≤10: {t['queries_position_le_10']}; "
                f"страниц со средней позицией ≤10: {t['pages_position_le_10']}. "
                "Средняя позиция страницы и средняя позиция запроса — разные сущности.",
                "В отчёте показатели по запросам и по страницам не смешиваются.")
        if t["impressions_window"] < snap["thresholds"]["low_impressions"] * 4:
            add("warning", "LOW_IMPRESSION_BASE_GOOGLE",
                "Малая абсолютная база показов Google",
                f"{t['impressions_window']} показов за {t['window_days']} дн.",
                "Относительные изменения сопровождаются абсолютными и маркером низкой базы.")

    # 9. CTR-модель
    if not snap.get("ctr_model", {}).get("approved"):
        add("warning", "NO_CTR_MODEL",
            "Утверждённая CTR-модель отсутствует",
            "Нет документированной кривой CTR по позициям для наших поисковиков и устройств.",
            "Расчёт «ожидаемого CTR» и «потерянных кликов» не публикуется.")

    # 10. CRM
    #
    # С 01.09.2026 воронка сайта отдаёт заявки (ops-leads-collect), поэтому
    # находка перестала быть одной. Заявки измеряются — сделки и выручка нет:
    # стадии двигает менеджер руками, и брать их как факт рано. Ещё одно
    # состояние — отставшая выгрузка: числа в письме тогда вчерашние, и
    # молчать об этом нельзя.
    crm = snap.get("crm") or {}
    if not crm.get("connected"):
        add("warning", "NO_CRM",
            "CRM не подключена",
            "Квалифицированные лиды, сделки и выручка не измеряются.",
            "Бизнес-результат в отчёте помечается «нет данных», цели Метрики его не заменяют.")
    else:
        if crm.get("revenue") is None:
            add("info", "NO_CRM_REVENUE",
                "Сделки и выручка не измеряются",
                "Воронка отдаёт заявки с каналом и составом запроса; стадии "
                "«выиграна/проиграна» и сумма сделки ведутся менеджером вручную.",
                "Бизнес-результат публикуется на уровне обращений; выручка — «нет данных».")
        if crm.get("stale"):
            add("warning", "CRM_DATA_STALE",
                "Выгрузка заявок отстала от даты отчёта",
                f"Использована выгрузка за {crm.get('data_date')} "
                f"при дате отчёта {snap.get('report_date')}.",
                "Заявки показываются по последней удачной выгрузке, её дата названа в письме.")

    # 11. Индексация без классификации
    idx = yx.get("indexation") if yx.get("available") else None
    if idx and idx.get("excluded_by_reason") is None and idx.get("excluded_urls"):
        add("warning", "INDEXATION_UNCLASSIFIED",
            "Исключённые страницы не классифицированы",
            f"Исключено {idx['excluded_urls']} URL; причины и коммерческая значимость неизвестны.",
            "Нельзя утверждать, что все исключения — проблема (тикет INDEX-001).")

    # 12. Рыночный спрос: свежесть, полнота и запрет на сравнение с нашей видимостью
    md = snap.get("market_demand") or {}
    if not md.get("available"):
        add("info", "MARKET_DEMAND_ABSENT",
            "Рыночный спрос не измерен",
            md.get("reason", "замер отсутствует"),
            "Формулировки о рыночном спросе и о товарах с подтверждённым спросом "
            "в отчёт не попадают.")
    else:
        src = md["source"]
        if md.get("stale"):
            add("warning", "MARKET_DEMAND_STALE",
                "Замер спроса устарел",
                f"Последний замер {src['measured_at']}, возраст {src['age_days']} дн. "
                f"при обновлении {src['refresh']}.",
                "Числа спроса публикуются с датой замера и не выдаются за текущие.")
        if not md.get("complete"):
            add("warning", "MARKET_DEMAND_PARTIAL",
                "Замер спроса неполный",
                f"Собрано {md.get('coverage')} запросов месяца; "
                f"кластеров с данными {md.get('clusters_measured')} "
                f"из {md.get('clusters_planned')}.",
                "Выводы о разрывах семантики помечаются как предварительные, "
                "решения об ассортименте по неполному замеру не принимаются.")
        add("info", "DEMAND_NOT_COMPARABLE_TO_VISIBILITY",
            "Спрос и наша видимость не сопоставляются напрямую",
            f"Спрос — {src.get('unit')}, {src.get('window')}, регион {src.get('region')}, "
            "соответствие "
            f"{src.get('match_type')}. Наша видимость — выборка топ-100 запросов Вебмастера.",
            "Доля голоса не рассчитывается; спрос используется как обоснование действий, "
            "а не как наш показатель.")

    # 13. Ошибка источника, выданная за ноль
    #
    # Разница между «показов не было» и «сбор не прошёл» принципиальна: первое
    # требует объяснения, второе — починки доступа. Прежде тело ошибки Google
    # сохранялось как данные, ключа rows в нём не было, и дальше получался
    # честный на вид ноль показов.
    if g.get("available") and g["totals"]["impressions_window"] == 0 \
            and not (g.get("daily") or []):
        add("critical", "API_ERROR_AS_ZERO",
            "Источник доступен, но не отдал ни одной строки",
            "Google Search Console: ответ без ошибки и без данных.",
            "Ноль показов не публикуется как результат: это отсутствие замера.",
            source="google")
    # Тот же принцип для GA4 и Вебмастера: частичную ошибку среза закрывает
    # snapshot (источник становится недоступным), а здесь ловится «пустой
    # успех» — ответ без ошибки и без единой строки.
    ga_blk = an.get("ga4") or {}
    if ga_blk.get("available") and not (ga_blk.get("channels") or {}):
        add("critical", "API_ERROR_AS_ZERO",
            "Источник доступен, но не отдал ни одной строки",
            "GA4: ответ без ошибки и без строк по каналам.",
            "Ноль сессий не публикуется как результат: это отсутствие замера.",
            source="ga4")
    if yx.get("available") and not (yx.get("entities") or []) \
            and (yx["totals"].get("queries_available") or 0) > 0:
        add("critical", "API_ERROR_AS_ZERO",
            "Источник доступен, но не отдал ни одной строки",
            "Яндекс.Вебмастер: запросы заявлены источником, но не получены.",
            "Ноль показов не публикуется как результат: это отсутствие замера.",
            source="yandex")

    # 14. Цели, которые сайт шлёт, но которых нет в счётчике
    #
    # Самая дешёвая из всех проверок и самая дорогая из всех находок: сайт
    # отправляет 23 имени целей, в счётчике заведено 4 автоцели, пересечение
    # пустое. Данные для сверки уже лежали в снимке — сверки не было.
    declared = snap.get("declared_goals") or []
    levels = snap.get("goal_levels") or {}
    # Цели могли быть заведены позже, чем собран список целей счётчика. Тогда
    # снимок честно показывает состояние на момент сбора, а вывод «цели не
    # заведены» на его основании уже неверен: это утверждение о настоящем,
    # сделанное по вчерашним данным. Различаем два случая по дате закрытия
    # записи в реестре пределов.
    goals_fixed_on = next(
        (lim.get("resolved_on") for lim in load_measurement_limits()
         if lim.get("metric") == "metrika.goal_events" and lim.get("resolved_on")),
        None)
    goals_collected = (an.get("metrika", {}).get("source") or {}).get("collected_at") or ""
    goals_data_is_stale = bool(goals_fixed_on and goals_collected
                               and goals_collected[:10] <= goals_fixed_on)
    # Сверяются только конверсии (key=true в реестре src/lib/analytics.ts).
    # Сигналы намерения и просмотры живут в GA4: требовать для них цель Метрики
    # значит утопить список конверсий в просмотрах, после чего им перестают
    # пользоваться.
    required = {"lead"}
    goals_missing_out, goals_lagging_out = None, False
    if declared and an.get("metrika", {}).get("available"):
        # Цель считается заведённой, если наш ключ совпал с именем цели ИЛИ с
        # идентификатором события в её условиях: заведённые через API цели
        # называются по-русски, а ключ (lead_sent) лежит в conditions[].url.
        configured = set()
        for g_ in an["metrika"].get("goals_configured") or []:
            configured.add(g_["name"])
            configured.update(g_.get("events") or [])
        missing = [n for n in declared
                   if levels.get(n, "engagement") in required and n not in configured]
        declared = [n for n in declared if levels.get(n, "engagement") in required]
        if missing and goals_data_is_stale:
            add("info", "GOALS_CONFIGURED_AFTER_COLLECTION",
                "Цели заведены позже, чем собран список счётчика",
                f"Цели заведены {goals_fixed_on}, а список целей счётчика собран "
                f"{goals_collected[:10]}. В снимке их ещё нет — это отставание "
                f"выгрузки, а не отсутствие целей.",
                "Утверждение «цели не заведены» не публикуется. Первые сопоставимые "
                "данные по конверсиям — со следующего сбора.", source="metrika")
            missing = []
            goals_lagging_out = True
        if missing:
            add("critical", "GOAL_NOT_CONFIGURED",
                "Сайт отправляет цели, которых нет в счётчике",
                f"Не заведено {len(missing)} из {len(declared)}: "
                f"{', '.join(sorted(missing)[:6])}"
                f"{' и ещё ' + str(len(missing) - 6) if len(missing) > 6 else ''}. "
                "Вызов reachGoal по незаведённой цели счётчик отбрасывает.",
                "Ноль по этим целям означает «не измерялось». Конверсия сайта "
                "и конверсия канала не публикуются.", source="metrika")
        goals_missing_out = len(missing)

    # 15. Собственные визиты в органике
    m_block = an.get("metrika", {})
    ga_block = an.get("ga4", {})
    internal = ga_block.get("internal_in_organic") if ga_block.get("available") else None
    if internal:
        add("warning", "INTERNAL_TRAFFIC_IN_ORGANIC",
            "В органике GA4 есть собственные визиты",
            f"Источники {', '.join(internal['sources'])}: {internal['sessions']} сессий, "
            f"{internal['key_events']} ключевых событий. GA4 относит домены Яндекса "
            "к поисковым системам, включая интерфейс Метрики.",
            "Конверсия органического канала не публикуется до очистки источника.",
            source="ga4")

    # 16. Часовой пояс
    tz = snap.get("reporting_timezone") or ""
    src_tz = ga_block.get("source_timezone")
    if src_tz and src_tz.split()[0] not in tz:
        add("warning", "TIMEZONE_MISMATCH",
            "Часовой пояс отчёта не совпадает с поясом источника",
            f"Отчёт: {tz}; GA4 отдаёт данные в {src_tz}.",
            "Границы суток источника и отчёта расходятся; «сегодня» означает "
            "разное в разных числах.")

    levels = [f["level"] for f in findings]
    status = "critical" if "critical" in levels else ("warning" if "warning" in levels else "ok")
    health = measurement.data_health(snap, findings)
    return {
        "schema_version": "3.1.0",
        "data_health": health,
        # Готовые выводы для письма: presentation-слой их отображает, а не
        # вычисляет заново по сырым полям снимка — иначе два слоя дают два
        # разных ответа на один вопрос (см. GOAL_NOT_CONFIGURED: сверка по
        # именам и событиям против сверки только по именам).
        "derived": {
            "stale_sources": sorted({f["source"] for f in findings
                                     if f["code"] == "SOURCE_NOT_UPDATED"
                                     and f.get("source")}),
            "goals_missing": goals_missing_out,
            "goals_lagging": goals_lagging_out,
        },
        "measurement_map": measurement.build_map(snap),
        "sample_ctr": measurement.sample_ctr(snap),
        "report_date": snap["report_date"],
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "counts": {lvl: levels.count(lvl) for lvl in ("critical", "warning", "info")},
        "findings": findings,
        "publication_rules": {
            "allow_green_overall_status": status == "ok",
            "allow_sitewide_ctr_claims": measurement.scopes_comparable(snap),
            "allow_expected_ctr_claims": bool(snap.get("ctr_model", {}).get("approved")),
            "allow_lead_wording": False,
            "allow_market_demand_wording": bool(
                (snap.get("market_demand") or {}).get("available")),
            "allow_assortment_decisions": bool(
                (snap.get("market_demand") or {}).get("complete")),
            # Абсолютная дельта запрещается ровно тем, что её портит: разной
            # длиной окна и пересборкой выборки.
            "allow_absolute_delta": yx_daily_ok or not any(
                f["code"] in ("WINDOW_LENGTH_MISMATCH", "SAMPLE_CHURN")
                for f in findings),
            # KPI письма считается из дневной витрины (окна равной длины).
            "kpi_from_daily": yx_daily_ok,
            "allow_channel_conversion_claims": not any(
                f["code"] in ("INTERNAL_TRAFFIC_IN_ORGANIC", "GOAL_NOT_CONFIGURED")
                for f in findings),
            "allow_conversion_wording": not any(
                f["code"] == "GOAL_NOT_CONFIGURED" for f in findings),
        },
    }


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    snap_path = SNAP_DIR / f"{date}.json"
    if not snap_path.exists():
        print(f"нет snapshot {snap_path}", file=sys.stderr)
        return 1
    snap = json.loads(snap_path.read_text(encoding="utf-8"))
    # «Вчера» берётся той же функцией, что у письма: иначе проверки качества и
    # отчёт видели бы разные предыдущие снимки, и вывод «не обновился» одного
    # слоя не совпадал бы с дельтами другого.
    prev = snapshot_mod.prev_snapshot(date)
    report = run_checks(snap, prev)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{date}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"data-quality: {report['status']} ({report['counts']}) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
