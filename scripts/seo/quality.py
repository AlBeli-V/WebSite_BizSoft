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

# Классы находок (решение руководителя 03.09.2026).
#
# Один список с одинаковым весом смешивал три разные вещи: сбой дня (сбор не
# прошёл, источник не обновился, цель не заведена), постоянное ограничение
# методики (CRM не отдаёт выручку, CTR-модели нет) и правило (запросы и
# страницы Google считаются отдельно). Из 16 строк за 03.09.2026 сбоев было
# ноль, а зелёный статус отчёта оставался недостижим: шесть предупреждений
# стояли каждый день при исправных источниках, и раздел отвечал на вопрос
# «что вообще неидеально» вместо «что сломалось сегодня».
#
# Статус отчёта и счётчики считаются только по сбоям. Ограничение несёт
# условие снятия (lifted_when) и дату начала (since), если она известна.
# Правило — не находка, а свойство методики; оно уходит в блок методики.
# Критический уровень допускается только у сбоя: тест это стережёт.
KIND_INCIDENT, KIND_LIMIT, KIND_RULE = "incident", "limit", "rule"
KIND_LABEL = {KIND_INCIDENT: "сбой", KIND_LIMIT: "ограничение", KIND_RULE: "правило"}
CODE_KIND = {
    "SOURCE_UNAVAILABLE": KIND_INCIDENT,
    "SOURCE_NOT_UPDATED": KIND_INCIDENT,
    "DAILY_MISSING": KIND_INCIDENT,
    "DAILY_GAP": KIND_INCIDENT,
    "WINDOW_LENGTH_MISMATCH": KIND_INCIDENT,
    "SAMPLE_CHURN": KIND_INCIDENT,
    "SAMPLE_TRUNCATED": KIND_INCIDENT,
    "INTRA_DAY_REVISION": KIND_INCIDENT,
    "BASELINE_REVISED": KIND_INCIDENT,
    "API_ERROR_AS_ZERO": KIND_INCIDENT,
    "GOAL_NOT_CONFIGURED": KIND_INCIDENT,
    "GOALS_CONFIGURED_AFTER_COLLECTION": KIND_INCIDENT,
    "CRM_DATA_STALE": KIND_INCIDENT,
    "MARKET_DEMAND_STALE": KIND_INCIDENT,
    "ROLLING_WINDOW_OVERLAP": KIND_LIMIT,
    "YANDEX_SAMPLE_SCOPE": KIND_LIMIT,
    "SCOPE_MISMATCH": KIND_LIMIT,
    "PERIOD_MISMATCH": KIND_LIMIT,
    "MEASUREMENT_GAP": KIND_LIMIT,
    "MEASUREMENT_CHANGE": KIND_LIMIT,
    "LOW_CONVERSION_SAMPLE": KIND_LIMIT,
    "GOAL_UNIQUENESS_UNKNOWN": KIND_LIMIT,
    "LOW_IMPRESSION_BASE_GOOGLE": KIND_LIMIT,
    "NO_CTR_MODEL": KIND_LIMIT,
    "NO_CRM": KIND_LIMIT,
    "NO_CRM_REVENUE": KIND_LIMIT,
    "INDEXATION_UNCLASSIFIED": KIND_LIMIT,
    "INDEXATION_COMMERCIAL_EXCLUDED": KIND_INCIDENT,
    "INDEXATION_CLASSIFIED": KIND_RULE,
    "MARKET_DEMAND_ABSENT": KIND_LIMIT,
    "MARKET_DEMAND_PARTIAL": KIND_LIMIT,
    "INTERNAL_TRAFFIC_IN_ORGANIC": KIND_LIMIT,
    "TIMEZONE_MISMATCH": KIND_LIMIT,
    "SCOPE_QUERY_VS_PAGE": KIND_RULE,
    "DEMAND_NOT_COMPARABLE_TO_VISIBILITY": KIND_RULE,
    "INTERNAL_TRAFFIC_EXCLUDED": KIND_RULE,
}


def finding_kind(f: dict) -> str:
    """Класс находки; для файлов старой схемы (без kind) — по коду."""
    return f.get("kind") or CODE_KIND.get(f.get("code"), KIND_INCIDENT)


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

    def add(level, code, title, detail, effect=None, source=None,
            kind=None, since=None, lifted_when=None):
        # source — машиночитаемый ключ источника (yandex|google|metrika|ga4):
        # письмо сопоставляет находку с карточкой по нему, а не по подстроке
        # русского заголовка. Поле необязательное: старые файлы data-quality
        # без него читаются как прежде.
        # kind — класс находки (см. CODE_KIND); since и lifted_when — дата
        # начала и условие снятия ограничения: без них читатель не отличит
        # ограничение, которое стоит месяц, от появившегося сегодня.
        kind = kind or CODE_KIND.get(code, KIND_INCIDENT)
        if level == "critical":
            kind = KIND_INCIDENT
        findings.append({"level": level, "code": code, "title": title,
                         "detail": detail, "effect_on_report": effect,
                         "source": source, "kind": kind, "since": since,
                         "lifted_when": lifted_when})

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
        if ov and yx_daily_ok:
            # «Предыдущий период» агрегатного пути — окно вчерашнего сбора,
            # поэтому пересечение на всё окно минус день структурно и будет
            # каждый день. KPI и дельты считаются из дневной витрины по окнам
            # равной длины встык; плавающее окно источника задевает только
            # выборку запросов раздела возможностей. Это правило, а не сбой.
            add("info", "ROLLING_WINDOW_OVERLAP",
                "Окно запросов Вебмастера плавает вслед за задержкой источника",
                f"Окно выборки запросов {s['current_period_start']}–{s['current_period_end']} "
                f"({s['current_period_days']} дн.) пересекается с окном вчерашнего "
                f"сбора на {ov} дн.",
                "KPI и дельты считаются по дневной витрине (окна равной длины "
                "встык). Выборка запросов используется только в разделе "
                "возможностей; её суммы день к дню не сравниваются.",
                kind=KIND_RULE)
        elif ov:
            add("warning", "ROLLING_WINDOW_OVERLAP",
                "Периоды Яндекс.Вебмастера пересекаются",
                f"Текущее окно {s['current_period_start']}–{s['current_period_end']} "
                f"({s['current_period_days']} дн.) пересекается с предыдущим на {ov} дн.",
                "Изменение показов день к дню не является сравнением независимых периодов; "
                "относительные проценты не публикуются.",
                lifted_when="дневная витрина Яндекса заполнена за оба окна")
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
            add("info" if yx_daily_ok else "critical", "WINDOW_LENGTH_MISMATCH",
                "Окна сравнения разной длины",
                f"Текущее окно {cur_days} дн., предыдущее {cmp_days} дн. "
                f"Задержка источника плавает, длина окна вслед за ней.",
                ("KPI считаются по витрине с окнами равной длины; разница длин "
                 "касается только выборки запросов раздела возможностей."
                 if yx_daily_ok else
                 "Абсолютная разница показов не публикуется: она включает вклад "
                 "лишних суток. Публикуется среднее за день с указанием длины окна."),
                kind=KIND_RULE if yx_daily_ok else KIND_INCIDENT)

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
            add("info" if yx_daily_ok else "critical", "SAMPLE_CHURN",
                "Состав выборки запросов изменился",
                f"Сменилось {churn['changed']} из {churn['previous']} запросов "
                f"({churn['share']:.0%}). Вошедшие принесли {churn['gained']} показов, "
                f"выбывшие унесли {churn['lost']}.",
                "Разница сумм по двум разным множествам запросов не является "
                "изменением видимости и не публикуется как дельта.",
                kind=KIND_RULE if yx_daily_ok else KIND_INCIDENT)

        # 2. Scope выборки
        #
        # Постраничный забор берёт все запросы хоста, и «выборка 1016 из 1016»
        # выборкой не является: заголовок спорил сам с собой, а следом — с
        # карточкой здоровья «KPI по всему сайту». Предупреждение остаётся
        # только когда источник отдал не всё; при полном заборе — правило о
        # том, где какие числа считаются.
        fetched = yx["totals"].get("queries_fetched") or 0
        available = yx["totals"].get("queries_available") or 0
        truncated = available > fetched
        if truncated:
            add("warning", "YANDEX_SAMPLE_SCOPE",
                f"Метрики Яндекса рассчитаны по выборке {fetched} из {available} запросов",
                f"Показы {yx['totals']['impressions']} и клики {yx['totals']['clicks']} — "
                f"сумма по {fetched} запросам из API popular queries, не по всему сайту.",
                "CTR Яндекса нельзя называть CTR сайта.",
                lifted_when="сборщик забирает все запросы хоста")
            add("warning", "SAMPLE_TRUNCATED",
                "Источник отдал не все запросы",
                f"Доступно {available}, забрано {fetched}.",
                "Длинный хвост запросов в показателях не учтён.")
        else:
            add("info", "YANDEX_SAMPLE_SCOPE",
                f"Раздел возможностей считается по всем {fetched} запросам Вебмастера",
                f"Показы {yx['totals']['impressions']} и клики {yx['totals']['clicks']} — "
                f"сумма по всем запросам хоста за окно источника "
                f"{s['current_period_start']}–{s['current_period_end']}; "
                "KPI письма — из дневной витрины за окна равной длины." if yx_daily_ok else
                f"Показы {yx['totals']['impressions']} и клики {yx['totals']['clicks']} — "
                f"сумма по всем запросам хоста за окно источника "
                f"{s['current_period_start']}–{s['current_period_end']}.",
                "CTR по запросам публикуется как CTR за окно источника; с окном "
                "витрины и с другими поисковыми системами не смешивается.",
                kind=KIND_RULE)

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
    #
    # Вебмастер и GSC зреют три дня, аналитика — один, поэтому концы окон
    # источников не совпадают по построению и будут расходиться каждый
    # день. Решение руководителя 03.09.2026 — двойное окно: карточки
    # источников на своих свежих окнах, а воронка и сверки между
    # источниками — по общему окну витрины с концом по самому медленному
    # источнику (daily.aligned). При полном общем окне расхождение концов —
    # правило, а не сбой; без общего окна — прежнее ограничение.
    aligned = daily.get("aligned") or {}
    if an.get("metrika", {}).get("available") and yx.get("available"):
        if an["metrika"]["source"]["current_period_end"] != yx["source"]["current_period_end"]:
            if aligned.get("complete"):
                add("info", "PERIOD_MISMATCH",
                    "Окна источников кончаются разными днями",
                    f"Вебмастер до {yx['source']['current_period_end']}, "
                    f"Метрика до {an['metrika']['source']['current_period_end']}: "
                    "задержка созревания у источников разная.",
                    "Карточки показателей считаются по свежему окну своего "
                    "источника; воронка и сверки между источниками — по общему "
                    f"окну {aligned['current']['from']}–{aligned['current']['to']} "
                    "(раздел «Карта измерений»).",
                    kind=KIND_RULE)
            else:
                add("warning", "PERIOD_MISMATCH",
                    "Окна источников не совпадают",
                    f"Вебмастер до {yx['source']['current_period_end']}, "
                    f"Метрика до {an['metrika']['source']['current_period_end']}.",
                    "Показатели поиска и аналитики не складываются в одну воронку "
                    "без оговорки.",
                    lifted_when="общее окно витрины заполнено по всем источникам")

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
                lim["rule"], since=lim.get("since"),
                lifted_when=f"дата закрытия записи {lim['id']} в реестре пределов")
        elif start and start <= resolved <= end:
            add("warning", "MEASUREMENT_CHANGE",
                f"{lim['title']}: методика изменилась внутри периода",
                f"{lim['detail']} Изменение вступило в силу {resolved}, окно {start}–{end}.",
                lim["rule"], since=resolved,
                lifted_when=f"окно источника сдвинется за {resolved}")

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
                "события не называются заявками.",
                lifted_when=f"не менее {snap['thresholds']['low_conversions']} "
                            "целевых событий за окно")
        if an["metrika"]["unique_goal_users"] is None:
            add("warning", "GOAL_UNIQUENESS_UNKNOWN",
                "Уникальность целевых обращений не подтверждена",
                "Собираются goal events (ym:s:sumGoalReachesAny) без дедупликации по посетителю.",
                "Формулировка «заявка/лид» запрещена; используется «целевое событие».",
                lifted_when="сборщик отдаёт посетителей, достигших конверсионных целей")

    # 8. Scope: query vs page (Google)
    if g.get("available"):
        t = g["totals"]
        # Google скрывает редкие запросы: строки по запросам покрывают лишь
        # часть показов ресурса, а запросы с верхними позициями как раз среди
        # скрытых. Поэтому «0 запросов в топ-10 при 16 страницах в топ-10» —
        # не противоречие данных, а разное покрытие срезов. Правило называет
        # долю покрытия, чтобы читатель не сопоставлял эти числа.
        q_imp = sum((e.get("impressions") or 0) for e in (g.get("entities") or []))
        total_imp = t.get("impressions_window") or 0
        share = (f"{q_imp / total_imp:.0%}" if total_imp else "—")
        add("info", "SCOPE_QUERY_VS_PAGE",
            "Google: запросы и страницы считаются отдельно",
            f"Видимые запросы ({t['queries_tracked']}) покрывают {q_imp} из "
            f"{total_imp} показов ({share}); остальные показы Google относит к "
            f"скрытым запросам. В топ-10 запросов: {t['queries_position_le_10']}, "
            f"страниц: {t['pages_position_le_10']} — это разные срезы с разным "
            "покрытием.",
            "Число запросов и страниц в топ-10 между собой не сравнивается; "
            "позиции по запросам публикуются с долей покрытия показов.")
        if t["impressions_window"] < snap["thresholds"]["low_impressions"] * 4:
            add("warning", "LOW_IMPRESSION_BASE_GOOGLE",
                "Малая абсолютная база показов Google",
                f"{t['impressions_window']} показов за {t['window_days']} дн.",
                "Относительные изменения сопровождаются абсолютными и маркером низкой базы.",
                lifted_when=f"не менее {snap['thresholds']['low_impressions'] * 4} "
                            "показов за окно источника")

    # 9. CTR-модель
    if not snap.get("ctr_model", {}).get("approved"):
        # Кривую по своим данным строить не на чем: за окно источника 25
        # кликов на 3816 показов (03.09.2026). Внешняя кривая запрещена
        # методикой как фиктивная. Условие снятия названо явно, чтобы
        # ограничение не выглядело поломкой.
        add("warning", "NO_CTR_MODEL",
            "Утверждённая CTR-модель отсутствует",
            "Нет документированной кривой CTR по позициям для наших поисковиков и устройств.",
            "Расчёт «ожидаемого CTR» и «потерянных кликов» не публикуется.",
            lifted_when="не менее 300 кликов по запросам Вебмастера за окно "
                        "источника и утверждённая руководителем кривая")

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
            "Бизнес-результат в отчёте помечается «нет данных», цели Метрики его не заменяют.",
            lifted_when="выгрузка заявок воронки подключена (ops-leads-collect)")
    else:
        if crm.get("revenue") is None:
            add("info", "NO_CRM_REVENUE",
                "Сделки и выручка не измеряются",
                "Воронка отдаёт заявки с каналом и составом запроса; стадии "
                "«выиграна/проиграна» и сумма сделки ведутся менеджером вручную.",
                "Бизнес-результат публикуется на уровне обращений; выручка — «нет данных».",
                since="2026-09-01",
                lifted_when="стадии сделок и суммы ведутся в воронке и выгружаются")
        if crm.get("stale"):
            add("warning", "CRM_DATA_STALE",
                "Выгрузка заявок отстала от даты отчёта",
                f"Использована выгрузка за {crm.get('data_date')} "
                f"при дате отчёта {snap.get('report_date')}.",
                "Заявки показываются по последней удачной выгрузке, её дата названа в письме.")

    # 11. Индексация: классификация исключённых (INDEX-001)
    idx = yx.get("indexation") if yx.get("available") else None
    if idx and idx.get("excluded_by_reason") is not None:
        reasons = ", ".join(f"{k}: {v}" for k, v in idx["excluded_by_reason"].items())
        smp = idx.get("excluded_samples") or {}
        commercial = idx.get("commercial_excluded_urls") or 0
        if commercial:
            paths = [u["path"] for u in (smp.get("unexpected") or []) if u.get("commercial")]
            add("warning", "INDEXATION_COMMERCIAL_EXCLUDED",
                "Коммерческие страницы сняты из поиска без ожидаемой причины",
                f"{commercial} адресов из sitemap: {', '.join(paths[:5])}"
                f"{' и ещё ' + str(len(paths) - 5) if len(paths) > 5 else ''}. "
                f"Статусы исключения за окно: {reasons}.",
                "Исключение этих страниц считается проблемой до разбора причины; "
                "остальные исключения — ожидаемые (переадресация, canonical, "
                "noindex, вне sitemap).", source="yandex")
        else:
            add("info", "INDEXATION_CLASSIFIED",
                "Исключённые страницы классифицированы",
                f"Разобрано {smp.get('classified')} из {idx.get('excluded_urls')} "
                f"исключённых URL, статусы: {reasons}. Коммерческих страниц из "
                "sitemap с неожиданным статусом нет.",
                "Исключения из поиска не считаются проблемой; число исключённых "
                "публикуется со статусами.", kind=KIND_RULE, source="yandex")
        if (idx.get("unclassified_excluded_urls") or 0) > 0:
            add("info", "INDEXATION_UNCLASSIFIED",
                "Часть исключённых страниц без классификации",
                f"Выборка событий поиска покрыла {smp.get('classified')} из "
                f"{idx.get('excluded_urls')} исключённых URL; остальные сняты раньше "
                f"окна выборки ({(smp.get('window') or {}).get('from')}–"
                f"{(smp.get('window') or {}).get('to')}).",
                "Утверждения о причинах делаются только по разобранной части.",
                kind=KIND_LIMIT, since="2026-08-19",
                lifted_when="окно выборки событий покрывает все исключения")
    elif idx and idx.get("excluded_by_reason") is None and idx.get("excluded_urls"):
        add("warning", "INDEXATION_UNCLASSIFIED",
            "Исключённые страницы не классифицированы",
            f"Исключено {idx['excluded_urls']} URL; причины и коммерческая значимость неизвестны.",
            "Нельзя утверждать, что все исключения — проблема (тикет INDEX-001).",
            since="2026-08-19",
            lifted_when="сборщик отдаёт причины исключения (INDEX-001)")

    # 12. Рыночный спрос: свежесть, полнота и запрет на сравнение с нашей видимостью
    md = snap.get("market_demand") or {}
    if not md.get("available"):
        add("info", "MARKET_DEMAND_ABSENT",
            "Рыночный спрос не измерен",
            md.get("reason", "замер отсутствует"),
            "Формулировки о рыночном спросе и о товарах с подтверждённым спросом "
            "в отчёт не попадают.",
            lifted_when="исследование Wordstat отработало полный цикл")
    else:
        src = md["source"]
        if md.get("stale"):
            add("warning", "MARKET_DEMAND_STALE",
                "Замер спроса устарел",
                f"Последний замер {src['measured_at']}, возраст {src['age_days']} дн. "
                f"при обновлении {src['refresh']}.",
                "Числа спроса публикуются с датой замера и не выдаются за текущие.",
                source="wordstat")
        if not md.get("complete"):
            add("warning", "MARKET_DEMAND_PARTIAL",
                "Замер спроса неполный",
                f"Собрано {md.get('coverage')}; "
                f"кластеров с данными {md.get('clusters_measured')} "
                f"из {md.get('clusters_planned')}; последний полный цикл — "
                f"{src.get('last_full_cycle') or 'не было'}.",
                "Выводы о разрывах семантики помечаются как предварительные, "
                "решения об ассортименте по неполному замеру не принимаются.",
                lifted_when="полный цикл Wordstat не старше месяца")
        add("info", "DEMAND_NOT_COMPARABLE_TO_VISIBILITY",
            "Спрос и наша видимость не сопоставляются напрямую",
            f"Спрос — {src.get('unit')}, {src.get('window')}, регион {src.get('region')}, "
            "соответствие "
            f"{src.get('match_type')}. Наша видимость — запросы Вебмастера за окно "
            "источника и дневная витрина показов.",
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
    ai_assist = ga_block.get("ai_assistant_in_organic") if ga_block.get("available") else None
    clean = ga_block.get("organic_sessions_clean") if ga_block.get("available") else None
    if (internal or ai_assist) and clean is not None:
        # Решение руководителя 03.09.2026: свои визиты вычитаются в снимке,
        # Алиса выделяется отдельным каналом. Конверсия канала публикуется
        # по очищенной органике; это правило подсчёта, а не сбой.
        parts = []
        if internal:
            parts.append(f"собственные визиты ({', '.join(internal['sources'])}): "
                         f"{internal['sessions']} сессий, "
                         f"{internal['key_events']:.0f} ключевых событий — вычтены")
        if ai_assist:
            parts.append(f"переходы из Алисы и Нейро ({', '.join(ai_assist['sources'])}): "
                         f"{ai_assist['sessions']} сессий — отдельный канал, не поиск")
        add("info", "INTERNAL_TRAFFIC_EXCLUDED",
            "Органика GA4 очищена от своих визитов и переходов из Алисы",
            "; ".join(parts) + f". Очищенная органика: {clean} сессий из "
            f"{ga_block.get('organic_sessions')}.",
            "Конверсия органического канала публикуется по очищенным сессиям; "
            "дневной ряд GA4 собран с тем же фильтром.",
            source="ga4")
    elif internal:
        add("warning", "INTERNAL_TRAFFIC_IN_ORGANIC",
            "В органике GA4 есть собственные визиты",
            f"Источники {', '.join(internal['sources'])}: {internal['sessions']} сессий, "
            f"{internal['key_events']} ключевых событий. GA4 относит домены Яндекса "
            "к поисковым системам, включая интерфейс Метрики.",
            "Конверсия органического канала не публикуется до очистки источника.",
            source="ga4", lifted_when="снимок отдаёт очищенную органику")

    # 16. Часовой пояс
    tz = snap.get("reporting_timezone") or ""
    src_tz = ga_block.get("source_timezone")
    if src_tz and src_tz.split()[0] not in tz:
        add("warning", "TIMEZONE_MISMATCH",
            "Часовой пояс отчёта не совпадает с поясом источника",
            f"Отчёт: {tz}; GA4 отдаёт данные в {src_tz}.",
            "Границы суток источника и отчёта расходятся; «сегодня» означает "
            "разное в разных числах.",
            lifted_when="часовой пояс ресурса GA4 переведён на пояс отчёта")

    levels = [f["level"] for f in findings]
    # Статус отчёта — по сбоям дня. Ограничения и правила в него не входят:
    # иначе зелёный статус недостижим при исправных источниках.
    incident_levels = [f["level"] for f in findings if f["kind"] == KIND_INCIDENT]
    status = ("critical" if "critical" in incident_levels
              else ("warning" if "warning" in incident_levels else "ok"))
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
        "funnel": measurement.funnel(snap),
        "sample_ctr": measurement.sample_ctr(snap),
        "report_date": snap["report_date"],
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "counts": {lvl: levels.count(lvl) for lvl in ("critical", "warning", "info")},
        "incident_counts": {lvl: incident_levels.count(lvl)
                            for lvl in ("critical", "warning", "info")},
        "kind_counts": {k: sum(1 for f in findings if f["kind"] == k)
                        for k in (KIND_INCIDENT, KIND_LIMIT, KIND_RULE)},
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
