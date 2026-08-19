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
        if clicks is not None and visits:
            ratio = visits / clicks if clicks else None
            if ratio is None or ratio > snap["thresholds"]["reconciliation_ratio"]:
                add("critical", "SOURCE_RECONCILIATION",
                    "Клики поиска и органические визиты расходятся кратно",
                    f"Яндекс.Вебмастер: {clicks} кликов (выборка топ-100 запросов, "
                    f"{yx['source']['current_period_start']}–{yx['source']['current_period_end']}); "
                    f"Метрика: {visits:.0f} органических визитов; "
                    f"GA4: {sessions} органических сессий "
                    f"({an['metrika']['source']['current_period_start']}–"
                    f"{an['metrika']['source']['current_period_end']}).",
                    "Низкий CTR по выборке запросов не может считаться доказанным «узким местом» "
                    "до сверки источников (тикет DATA-001).")

    # 4. Разные окна аналитики и поиска
    if an.get("metrika", {}).get("available") and yx.get("available"):
        if an["metrika"]["source"]["current_period_end"] != yx["source"]["current_period_end"]:
            add("warning", "PERIOD_MISMATCH",
                "Окна источников не совпадают",
                f"Вебмастер до {yx['source']['current_period_end']}, "
                f"Метрика до {an['metrika']['source']['current_period_end']}.",
                "Показатели поиска и аналитики не складываются в одну воронку без оговорки.")

    # 5. Изменение разметки конверсий внутри периода
    ga4 = an.get("ga4", {})
    if ga4.get("available") and ga4.get("key_events_marked_at"):
        s = ga4["source"]
        if s["current_period_start"] <= ga4["key_events_marked_at"] <= s["current_period_end"]:
            add("warning", "MEASUREMENT_CHANGE",
                "Разметка ключевых событий GA4 изменена внутри периода",
                f"key events размечены {ga4['key_events_marked_at']}, окно "
                f"{s['current_period_start']}–{s['current_period_end']}.",
                "Прямое сравнение конверсий GA4 по периодам запрещено; "
                f"текущее значение key events = {ga4['organic_key_events']} не означает отсутствие обращений.")

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

    levels = [f["level"] for f in findings]
    status = "critical" if "critical" in levels else ("warning" if "warning" in levels else "ok")
    return {
        "schema_version": "2.0.0",
        "report_date": snap["report_date"],
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "counts": {lvl: levels.count(lvl) for lvl in ("critical", "warning", "info")},
        "findings": findings,
        "publication_rules": {
            "allow_green_overall_status": status == "ok",
            "allow_expected_ctr_claims": bool(snap.get("ctr_model", {}).get("approved")),
            "allow_lead_wording": False,
            "allow_market_demand_wording": False,
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
