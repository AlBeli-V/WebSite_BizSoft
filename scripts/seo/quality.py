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


def run_checks(snap: dict) -> dict:
    findings: list[dict] = []

    def add(level, code, title, detail, effect=None):
        findings.append({"level": level, "code": code, "title": title,
                         "detail": detail, "effect_on_report": effect})

    yx, g, an = snap["yandex"], snap["google"], snap["analytics"]

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
        # 2. Scope выборки
        add("warning", "YANDEX_SAMPLE_SCOPE",
            "Метрики Яндекса рассчитаны по выборке топ-100 запросов",
            f"Показы {yx['totals']['impressions']} и клики {yx['totals']['clicks']} — "
            "сумма по 100 запросам из API popular queries, не по всему сайту.",
            "CTR Яндекса нельзя называть CTR сайта.")

    # 3. Кросс-источниковая сверка: клики поиска против визитов/сессий
    if yx.get("available") and an.get("metrika", {}).get("available"):
        clicks = yx["totals"]["clicks"]
        visits = an["metrika"]["organic_visits"]
        sessions = an.get("ga4", {}).get("organic_sessions")
        # Клики по выборке топ-100 запросов и визиты всего сайта измеряют разные
        # множества. Их отношение — не «расхождение источников», а разница охвата,
        # поэтому это ограничение (limited), а не поломка (degraded).
        if clicks is not None and visits and not measurement.scopes_comparable(snap):
            add("warning", "SCOPE_MISMATCH",
                "Охваты поиска и аналитики различаются",
                f"Яндекс.Вебмастер: {clicks} кликов по выборке "
                f"{yx['totals']['queries_tracked']} запросов "
                f"({yx['source']['current_period_start']}–{yx['source']['current_period_end']}); "
                f"Метрика: {visits:.0f} органических визитов всего сайта; "
                f"GA4: {sessions} органических сессий "
                f"({an['metrika']['source']['current_period_start']}–"
                f"{an['metrika']['source']['current_period_end']}).",
                "Клики выборки и визиты сайта не сравниваются между собой. CTR "
                "публикуется как CTR выборки с указанием охвата; вывод о кликабельности "
                "всего сайта не делается.")

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
    if not snap.get("crm", {}).get("connected"):
        add("warning", "NO_CRM",
            "CRM не подключена",
            "Квалифицированные лиды, сделки и выручка не измеряются.",
            "Бизнес-результат в отчёте помечается «нет данных», цели Метрики его не заменяют.")

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

    levels = [f["level"] for f in findings]
    status = "critical" if "critical" in levels else ("warning" if "warning" in levels else "ok")
    health = measurement.data_health(snap, findings)
    return {
        "schema_version": "3.0.0",
        "data_health": health,
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
        },
    }


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    snap_path = SNAP_DIR / f"{date}.json"
    if not snap_path.exists():
        print(f"нет snapshot {snap_path}", file=sys.stderr)
        return 1
    snap = json.loads(snap_path.read_text(encoding="utf-8"))
    report = run_checks(snap)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{date}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"data-quality: {report['status']} ({report['counts']}) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
