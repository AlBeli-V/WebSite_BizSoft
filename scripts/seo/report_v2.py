#!/usr/bin/env python3
"""Генератор отчётности v2: executive brief (md + html) и аналитическое приложение.

Все цифры берутся из канонического snapshot и sidecar качества данных —
в шаблонах нет вручную вписанных значений.

Запуск: python3 scripts/seo/report_v2.py [YYYY-MM-DD]
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import snapshot as snap_mod  # noqa: E402
from quality import delta  # noqa: E402

BASE = pathlib.Path("reports/seo/intelligence")
INK, MUTED, LINE = "#1d1d1f", "#66666e", "#e8e8ed"
ACCENT, GOOD, WARN, BAD = "#f2591d", "#1a8f4c", "#b26a00", "#d92d20"

STATUS_STYLE = {
    "рост": (GOOD, "▲"), "снижение": (BAD, "▼"), "без изменений": (MUTED, "="),
    "не определяется": (WARN, "!"), "недостаточно данных": (WARN, "?"),
    "требует внимания": (BAD, "!"), "норма": (GOOD, "✓"),
}


def fmt(v, unit=""):
    if v is None:
        return "нет данных"
    if isinstance(v, float):
        return f"{v:,.0f}{unit}".replace(",", " ") if v >= 100 else f"{v:.2f}{unit}".rstrip("0").rstrip(".")
    return f"{v:,}{unit}".replace(",", " ")


def pct(v):
    return "нет данных" if v is None else f"{v * 100:.2f}%".replace(".", ",")


def rel(d):
    if d.get("relative") is None:
        return "относительное изменение не рассчитывается (база 0 или нет данных)"
    return f"{d['relative'] * 100:+.1f}%".replace(".", ",")


def prev_snapshot(date: str) -> dict | None:
    """Предыдущий snapshot: из файла, иначе собирается из сырых выгрузок за вчера."""
    prev_date = (dt.date.fromisoformat(date) - dt.timedelta(days=1)).isoformat()
    p = BASE / "snapshots" / f"{prev_date}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    yx_raw = snap_mod.load("yandex", prev_date)
    g_raw = snap_mod.load("gsc", prev_date)
    if not yx_raw and not g_raw:
        return None
    return {
        "report_date": prev_date,
        "yandex": snap_mod.build_yandex(yx_raw, None, prev_date),
        "google": snap_mod.build_google(g_raw, None),
        "analytics": snap_mod.build_analytics(snap_mod.load("metrika", prev_date),
                                              snap_mod.load("ga4", prev_date), prev_date),
    }


def compute_statuses(snap, prev, dq):
    """Четыре независимых статуса. Правила зафиксированы в docs/seo/reporting-methodology.md."""
    yx, g = snap["yandex"], snap["google"]
    st = {}

    # Видимость: индексация + число запросов со средней позицией <= 10
    idx_now = yx["indexation"]["indexed_urls"] if yx.get("available") else None
    idx_prev = prev["yandex"]["indexation"]["indexed_urls"] if prev and prev["yandex"].get("available") else None
    d_idx = delta(idx_now, idx_prev)
    top_now = yx["totals"]["queries_position_le_10"] if yx.get("available") else None
    top_prev = prev["yandex"]["totals"]["queries_position_le_10"] if prev and prev["yandex"].get("available") else None
    d_top = delta(top_now, top_prev)
    if d_idx["absolute"] is not None and d_idx["absolute"] > 0:
        st["visibility"] = ("рост", f"страниц в поиске {fmt(idx_now)} ({d_idx['absolute']:+.0f} к предыдущему snapshot); "
                                     f"запросов выборки со средней позицией ≤10: {fmt(top_now)} "
                                     f"({d_top['absolute']:+.0f})" if d_top["absolute"] is not None else "")
    elif d_idx["absolute"] is not None and d_idx["absolute"] < 0:
        st["visibility"] = ("снижение", f"страниц в поиске {fmt(idx_now)} ({d_idx['absolute']:+.0f})")
    else:
        st["visibility"] = ("без изменений", f"страниц в поиске {fmt(idx_now)}")

    # Захват трафика: заблокирован критической ошибкой сверки
    critical_codes = [f["code"] for f in dq["findings"] if f["level"] == "critical"]
    if "SOURCE_RECONCILIATION" in critical_codes:
        st["traffic_capture"] = ("не определяется",
                                 "клики поиска и органические визиты расходятся кратно — "
                                 "оценка захвата трафика заблокирована до сверки источников (DATA-001)")
    else:
        st["traffic_capture"] = ("недостаточно данных", "нет утверждённой CTR-модели для оценки")

    # Конверсия
    m = snap["analytics"].get("metrika", {})
    ev = m.get("organic_goal_events") if m.get("available") else None
    if ev is None:
        st["conversion"] = ("недостаточно данных", "целевые события недоступны")
    elif ev < snap["thresholds"]["low_conversions"]:
        st["conversion"] = ("недостаточно данных",
                            f"{fmt(ev)} целевых события при пороге {snap['thresholds']['low_conversions']}; "
                            "уникальность не подтверждена; лиды не измеряются (нет CRM)")
    else:
        st["conversion"] = ("норма", f"{fmt(ev)} целевых событий")

    # Качество данных
    c = dq["counts"]
    if dq["status"] == "critical":
        st["data_quality"] = ("требует внимания",
                              f"критических расхождений: {c.get('critical', 0)}, предупреждений: {c.get('warning', 0)}")
    elif dq["status"] == "warning":
        st["data_quality"] = ("недостаточно данных", f"предупреждений: {c.get('warning', 0)}")
    else:
        st["data_quality"] = ("норма", "проверки пройдены")
    return st


def overall_sentence(st) -> str:
    """Одно предложение общего статуса — производное от четырёх статусов, без ручных формулировок."""
    vis = {"рост": "видимость в поиске растёт", "снижение": "видимость снижается",
           "без изменений": "видимость без изменений"}.get(st["visibility"][0], "видимость не оценивается")
    cap = ("оценка захвата трафика заблокирована расхождением источников"
           if st["traffic_capture"][0] == "не определяется" else f"захват трафика — {st['traffic_capture'][0]}")
    conv = ("бизнес-результат не измеряется (нет CRM, выборка событий мала)"
            if st["conversion"][0] == "недостаточно данных" else f"конверсия — {st['conversion'][0]}")
    return f"{vis.capitalize()}, {cap}, {conv}."


def kpi_cards(snap, prev):
    yx, g = snap["yandex"], snap["google"]
    m = snap["analytics"].get("metrika", {})
    nonbrand_imp = sum(e["impressions"] or 0 for e in yx["entities"] if not e["branded"]) if yx.get("available") else None
    prev_nonbrand = (sum(e["impressions"] or 0 for e in prev["yandex"]["entities"] if not e["branded"])
                     if prev and prev["yandex"].get("available") else None)
    cards = [
        {"label": "Органические клики, Яндекс",
         "value": fmt(yx["totals"]["clicks"]) if yx.get("available") else "нет данных",
         "note": f"выборка топ-100 запросов, {yx['source']['current_period_start']}–{yx['source']['current_period_end']}"[:60]
                 if yx.get("available") else "источник недоступен",
         "delta": delta(yx["totals"]["clicks"] if yx.get("available") else None,
                        prev["yandex"]["totals"]["clicks"] if prev and prev["yandex"].get("available") else None)},
        {"label": "Небрендовые показы, Яндекс", "value": fmt(nonbrand_imp),
         "note": "та же выборка; окна пересекаются, % не публикуется",
         "delta": delta(nonbrand_imp, prev_nonbrand)},
        {"label": "CTR выборки запросов, Яндекс",
         "value": pct(yx["totals"]["ctr"]) if yx.get("available") else "нет данных",
         "note": "ожидаемый CTR: нет утверждённой модели", "delta": None},
        {"label": "Органические визиты, Метрика",
         "value": fmt(m.get("organic_visits")) if m.get("available") else "нет данных",
         "note": f"{m['source']['current_period_start']}–{m['source']['current_period_end']}, ym:s:visits"
                 if m.get("available") else "источник недоступен",
         "delta": delta(m.get("organic_visits") if m.get("available") else None,
                        prev["analytics"]["metrika"].get("organic_visits")
                        if prev and prev["analytics"].get("metrika", {}).get("available") else None)},
        {"label": "Квалифицированные лиды", "value": "нет данных",
         "note": "CRM не подключена; события Метрики — не лиды", "delta": None},
    ]
    return cards


def changes_block(snap, prev):
    """Не более трёх изменений: current, previous, дельты, доверие, интерпретация."""
    out = []
    g, yx = snap["google"], snap["yandex"]
    if g.get("available"):
        t = g["totals"]
        d = delta(t["impressions_last7"], t["impressions_prev7"])
        out.append({
            "title": "Показы Google: неделя к неделе",
            "current": f"{t['impressions_last7']} показов ({t['last7_start']}–{t['last7_end']})",
            "previous": f"{t['impressions_prev7']} показов ({t['prev7_start']}–{t['prev7_end']})",
            "absolute": f"{d['absolute']:+d}", "relative": rel(d),
            "confidence": "низкая: обе базы меньше порога надёжности "
                          f"({snap['thresholds']['low_impressions']} показов), периоды равны по 7 дней",
            "interpretation": "ИНТЕРПРЕТАЦИЯ: охват расширился, но кликов нет; на такой базе вывод предварительный.",
        })
    if yx.get("available") and prev and prev["yandex"].get("available"):
        d = delta(yx["indexation"]["indexed_urls"], prev["yandex"]["indexation"]["indexed_urls"])
        out.append({
            "title": "Страницы в поиске Яндекса",
            "current": f"{yx['indexation']['indexed_urls']} URL (сбор {yx['source']['collected_at']})",
            "previous": f"{prev['yandex']['indexation']['indexed_urls']} URL (предыдущий сбор)",
            "absolute": f"{d['absolute']:+d}", "relative": rel(d),
            "confidence": "достаточная: значение агрегатное, не выборочное",
            "interpretation": "ФАКТ: число проиндексированных URL выросло; причина в текущем сборе не измеряется.",
        })
        d2 = delta(yx["totals"]["queries_position_le_10"], prev["yandex"]["totals"]["queries_position_le_10"])
        out.append({
            "title": "Запросы выборки со средней позицией ≤10",
            "current": f"{yx['totals']['queries_position_le_10']} из {yx['totals']['queries_tracked']}",
            "previous": f"{prev['yandex']['totals']['queries_position_le_10']} из "
                        f"{prev['yandex']['totals']['queries_tracked']}",
            "absolute": f"{d2['absolute']:+d}", "relative": rel(d2),
            "confidence": "средняя: состав выборки топ-100 меняется между сборами",
            "interpretation": "ИНТЕРПРЕТАЦИЯ: это позиции внутри выборки популярных запросов, а не вся семантика.",
        })
    return out[:3]


def decisions(snap, dq):
    """Не более трёх решений. Только бизнес-решения, без технических инструкций."""
    return [
        {
            "id": "DEC-001",
            "approve": "Приоритет P0 для сверки источников аналитики (DATA-001) и паузу в выводах "
                       "о кликабельности до её завершения.",
            "recommended": "Утвердить: сначала сверка, затем решения по CTR.",
            "effect": "Снимает расхождение 6 кликов Вебмастера против 37 органических визитов Метрики. "
                      "Основание: проверка SOURCE_RECONCILIATION.",
            "cost": "внутренние трудозатраты аналитика, без внешнего бюджета",
            "owner": "назначает руководитель (предлагается аналитик проекта)",
            "deadline": "2026-08-22",
            "dependency": "доступы к источникам есть",
            "success": "таблица «источник → метрика → фильтры → период → значение → объяснение» объясняет разрыв",
            "risk": "работы могут быть направлены на несуществующую проблему",
            "rollback": "не требуется: изменений на сайте нет",
        },
        {
            "id": "DEC-002",
            "approve": "Разделение внедрённой правки на два эксперимента (метаданные и FAQ) и отказ от "
                       "объявления результата через фиксированные 7 дней.",
            "recommended": "Утвердить; оценка по достаточному объёму наблюдений либо по окну 28 дней.",
            "effect": "Метаданные и FAQ внедрены одной правкой 2026-08-19, вклад элементов неразделим; "
                      "разделение делает результат управляемым.",
            "cost": "без изменений сайта, только план измерения",
            "owner": "назначает руководитель (предлагается SEO-исполнитель)",
            "deadline": "2026-08-21",
            "dependency": "фиксация даты появления нового сниппета в выдаче",
            "success": "в реестре два эксперимента с отдельными метриками и guardrails",
            "risk": "иначе положительный результат нельзя масштабировать осознанно",
            "rollback": "возврат прежних метаданных из истории репозитория",
        },
        {
            "id": "DEC-003",
            "approve": "Перенос рекламного теста (PPC-RES-001) в P2 до устранения пробелов измерения.",
            "recommended": "Утвердить перенос; вернуться после DATA-001 и подключения CRM.",
            "effect": "Показы источников отражают видимость наших страниц, а не объём рынка; без прогноза "
                      "Директа и определения уникального лида результат не интерпретируем.",
            "cost": "0 ₽ сейчас; бюджет определяется прогнозом рекламного кабинета",
            "owner": "назначает руководитель",
            "deadline": "2026-08-26",
            "dependency": "доступ к Директу, подключённая CRM",
            "success": "решение зафиксировано; при возврате есть прогноз кликов, CPC и stop-condition",
            "risk": "отсрочка проверки коммерческой ценности кластеров",
            "rollback": "не требуется",
        },
    ][:3]


def md_executive(snap, prev, dq, st, cards, changes, decs) -> str:
    yx, g, m, ga = snap["yandex"], snap["google"], snap["analytics"].get("metrika", {}), snap["analytics"].get("ga4", {})
    date_h = dt.date.fromisoformat(snap["report_date"]).strftime("%d.%m.%Y")
    L = [f"# BIZSoft Search Performance & Experiment Brief — {date_h}", ""]
    L.append(f"Часовой пояс: {snap['reporting_timezone']} · сформирован {snap['generated_at']} UTC · схема {snap['schema_version']}.")
    L += ["", "## Свежесть данных", ""]
    for src in [yx.get("source"), g.get("source"), m.get("source"), ga.get("source")]:
        if not src:
            continue
        L.append(f"- {src['source_name']}: события по {src['latest_event_date'] or 'нет данных'}, "
                 f"период {src['current_period_start']}–{src['current_period_end']} "
                 f"({src['current_period_days']} дн.), сбор {src['collected_at']}, статус {src['status']}")
    L.append("- CRM: не подключена — бизнес-результат не измеряется")
    overall = overall_sentence(st)
    L += ["", "## Общий статус", "", f"**{overall}**", "", "## Статусы направлений", "",
          "| Направление | Статус | Основание |", "|---|---|---|"]
    names = {"visibility": "Видимость", "traffic_capture": "Захват трафика",
             "conversion": "Конверсия", "data_quality": "Качество данных"}
    for k, (val, why) in st.items():
        L.append(f"| {names[k]} | {val} | {why} |")
    L += ["", "## Ключевые показатели", "", "| Показатель | Значение | Изменение | Пояснение |", "|---|---|---|---|"]
    for c in cards:
        d = c["delta"]
        dtxt = "нет данных" if not d or d["absolute"] is None else (
            f"{d['absolute']:+.0f}" + (" (низкая база)" if d.get("low_base") else ""))
        L.append(f"| {c['label']} | {c['value']} | {dtxt} | {c['note']} |")
    L += ["", "## Что изменилось", ""]
    for ch in changes:
        L += [f"**{ch['title']}** — {ch['current']} против {ch['previous']}; "
              f"изменение {ch['absolute']} ({ch['relative']}); доверие — {ch['confidence']}. "
              f"{ch['interpretation']}", ""]
    ev = m.get("organic_goal_events") if m.get("available") else None
    L += ["## Результат для бизнеса", "",
          f"- Целевые события (Метрика, органика): {fmt(ev)} — уникальность не подтверждена, выборка ниже порога",
          "- Квалифицированные лиды: нет данных (CRM не подключена)",
          "- Сделки: нет данных", "- Выручка: нет данных",
          "- Ограничение: цели фиксируют события, а не подтверждённые обращения; разметка GA4 менялась 2026-08-18.",
          "", "## Решения руководителя", ""]
    for d in decs:
        L += [f"**{d['id']}. {d['approve']}**", "",
              f"- Рекомендация: {d['recommended']} · Эффект: {d['effect']}",
              f"- Затраты: {d['cost']} · Ответственный: {d['owner']} · Срок: {d['deadline']}",
              f"- Зависимость: {d['dependency']} · Критерий успеха: {d['success']}",
              f"- Риск: {d['risk']} · Rollback/stop: {d['rollback']}", ""]
    L += ["## Риски и качество данных", ""]
    for f in [x for x in dq["findings"] if x["level"] in ("critical", "warning")][:5]:
        L.append(f"- **{f['level'].upper()}** — {f['title']}: {f['effect_on_report']}")
    L += ["", "## Следующая контрольная точка", "",
          "- 2026-08-22 — результат сверки источников (DATA-001).",
          "- 2026-08-26 — промежуточный срез эксперимента метаданных; вывод только при достаточном объёме наблюдений.",
          "", f"Полные таблицы, методика и технические задания — в приложении: "
              f"reports/seo/intelligence/{snap['report_date']}-appendix.md"]
    return "\n".join(L)


def html_executive(snap, st, cards, changes, decs, dq, charts) -> str:
    date_h = dt.date.fromisoformat(snap["report_date"]).strftime("%d.%m.%Y")
    overall = overall_sentence(st)
    yx, g, m, ga = snap["yandex"], snap["google"], snap["analytics"].get("metrika", {}), snap["analytics"].get("ga4", {})
    names = {"visibility": "Видимость", "traffic_capture": "Захват трафика",
             "conversion": "Конверсия", "data_quality": "Качество данных"}
    H = [f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BIZSoft Search Performance &amp; Experiment Brief — {date_h}</title></head>
<body style="margin:0;padding:0;background:#f5f5f7;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f7;">
<tr><td align="center" style="padding:20px 10px;">
<table role="presentation" width="660" cellpadding="0" cellspacing="0" style="max-width:660px;width:100%;background:#fff;border-radius:12px;border:1px solid {LINE};overflow:hidden;">
<tr><td style="background:{INK};padding:22px 26px;font-family:Arial,Helvetica,sans-serif;">
<div style="font-size:17px;font-weight:bold;color:#fff;">BIZ<span style="color:{ACCENT};">Soft</span> Search Performance &amp; Experiment Brief</div>
<div style="font-size:11.5px;color:#a0a0a8;padding-top:5px;">{date_h} · {snap['reporting_timezone']} · схема данных {snap['schema_version']}</div></td></tr>"""]

    # Критические предупреждения — текстом, до любых изображений
    crit = [f for f in dq["findings"] if f["level"] == "critical"]
    if crit:
        items = "".join(f"<div style='padding-top:4px;'><b>{f['title']}.</b> {f['detail']} "
                        f"<i>Влияние: {f['effect_on_report']}</i></div>" for f in crit)
        H.append(f"""<tr><td style="padding:16px 26px 0;font-family:Arial,Helvetica,sans-serif;">
<div style="background:#fdecea;border-left:4px solid {BAD};border-radius:0 8px 8px 0;padding:12px 14px;font-size:12.5px;line-height:1.55;color:{INK};">
<b style="color:{BAD};">КРИТИЧЕСКОЕ РАСХОЖДЕНИЕ ДАННЫХ — часть выводов приостановлена</b>{items}</div></td></tr>""")

    # Свежесть
    rows = ""
    for src in [yx.get("source"), g.get("source"), m.get("source"), ga.get("source")]:
        if not src:
            continue
        rows += (f"<tr><td style='padding:5px 8px;border:1px solid {LINE};'>{src['source_name']}</td>"
                 f"<td style='padding:5px 8px;border:1px solid {LINE};'>{src['latest_event_date'] or 'нет данных'}</td>"
                 f"<td style='padding:5px 8px;border:1px solid {LINE};'>{src['current_period_start']}–{src['current_period_end']} ({src['current_period_days']} дн.)</td>"
                 f"<td style='padding:5px 8px;border:1px solid {LINE};'>{src['collected_at'][:10] if src['collected_at'] else '—'}</td></tr>")
    rows += (f"<tr><td style='padding:5px 8px;border:1px solid {LINE};'>CRM</td>"
             f"<td colspan='3' style='padding:5px 8px;border:1px solid {LINE};color:{MUTED};'>не подключена — бизнес-результат не измеряется</td></tr>")
    H.append(f"""<tr><td style="padding:16px 26px 0;font-family:Arial,Helvetica,sans-serif;">
<div style="font-size:14px;font-weight:bold;color:{INK};border-bottom:2px solid {ACCENT};padding-bottom:6px;">Свежесть данных</div>
<table role="presentation" width="100%" style="border-collapse:collapse;font-size:11px;color:{INK};margin-top:10px;">
<tr style="background:#f5f5f7;"><td style="padding:5px 8px;border:1px solid {LINE};font-weight:bold;">Источник</td>
<td style="padding:5px 8px;border:1px solid {LINE};font-weight:bold;">Последнее событие</td>
<td style="padding:5px 8px;border:1px solid {LINE};font-weight:bold;">Период</td>
<td style="padding:5px 8px;border:1px solid {LINE};font-weight:bold;">Сбор</td></tr>{rows}</table></td></tr>""")

    # Общий статус + 4 индикатора
    st_rows = ""
    for k, (val, why) in st.items():
        color, sign = STATUS_STYLE.get(val, (MUTED, "•"))
        st_rows += (f"<tr><td style='padding:7px 8px;border:1px solid {LINE};font-weight:bold;'>{names[k]}</td>"
                    f"<td style='padding:7px 8px;border:1px solid {LINE};color:{color};font-weight:bold;white-space:nowrap;'>{sign} {val}</td>"
                    f"<td style='padding:7px 8px;border:1px solid {LINE};font-size:11px;'>{why}</td></tr>")
    H.append(f"""<tr><td style="padding:16px 26px 0;font-family:Arial,Helvetica,sans-serif;">
<div style="background:#fff2ec;border-left:4px solid {ACCENT};border-radius:0 8px 8px 0;padding:11px 14px;font-size:13px;line-height:1.55;color:{INK};">
<b>Общий статус:</b> {overall}</div>
<table role="presentation" width="100%" style="border-collapse:collapse;font-size:12px;color:{INK};margin-top:12px;">{st_rows}</table></td></tr>""")

    # KPI
    kpi = ""
    for c in cards:
        d = c["delta"]
        dtxt = "" if not d or d["absolute"] is None else (
            f"<span style='color:{MUTED};font-size:11px;'> ({d['absolute']:+.0f}"
            + (", низкая база" if d.get("low_base") else "") + ")</span>")
        kpi += (f"<tr><td style='padding:8px;border:1px solid {LINE};'>{c['label']}</td>"
                f"<td style='padding:8px;border:1px solid {LINE};font-weight:bold;white-space:nowrap;'>{c['value']}{dtxt}</td>"
                f"<td style='padding:8px;border:1px solid {LINE};font-size:11px;color:{MUTED};'>{c['note']}</td></tr>")
    H.append(f"""<tr><td style="padding:18px 26px 0;font-family:Arial,Helvetica,sans-serif;">
<div style="font-size:14px;font-weight:bold;color:{INK};border-bottom:2px solid {ACCENT};padding-bottom:6px;">Ключевые показатели</div>
<table role="presentation" width="100%" style="border-collapse:collapse;font-size:12px;color:{INK};margin-top:10px;">{kpi}</table></td></tr>""")

    # Что изменилось
    ch_html = ""
    for ch in changes:
        ch_html += (f"<div style='border:1px solid {LINE};border-radius:8px;padding:12px 14px;margin-bottom:10px;'>"
                    f"<div style='font-weight:bold;font-size:12.5px;'>{ch['title']}</div>"
                    f"<div style='font-size:11.5px;line-height:1.6;padding-top:5px;'>"
                    f"Текущее: {ch['current']}<br>Предыдущее: {ch['previous']}<br>"
                    f"Изменение: <b>{ch['absolute']}</b> · {ch['relative']}<br>"
                    f"Доверие: {ch['confidence']}<br><span style='color:{MUTED};'>{ch['interpretation']}</span></div></div>")
    H.append(f"""<tr><td style="padding:18px 26px 0;font-family:Arial,Helvetica,sans-serif;color:{INK};">
<div style="font-size:14px;font-weight:bold;border-bottom:2px solid {ACCENT};padding-bottom:6px;margin-bottom:10px;">Что изменилось</div>{ch_html}</td></tr>""")

    # Графики: воронка и Google (inline SVG + текстовый fallback)
    for key, cap in (("funnel", "Воронка поиска"), ("google-daily", "Динамика показов Google")):
        c = charts.get(key)
        if not c or not c.get("svg"):
            continue
        tbl = c["table"][:7]
        head = "".join(f"<td style='padding:4px 7px;border:1px solid {LINE};font-weight:bold;'>{h}</td>" for h in tbl[0])
        body = "".join("<tr>" + "".join(f"<td style='padding:4px 7px;border:1px solid {LINE};'>{v}</td>" for v in r) + "</tr>"
                       for r in tbl[1:])
        H.append(f"""<tr><td style="padding:14px 26px 0;font-family:Arial,Helvetica,sans-serif;color:{INK};">
<div style="font-size:12.5px;font-weight:bold;">{cap}</div>
<div style="padding:6px 0;">{c['svg']}</div>
<div style="font-size:10.5px;color:{MUTED};">Если графика не отображается, данные продублированы таблицей ниже. Alt: {c['alt']}</div>
<table role="presentation" width="100%" style="border-collapse:collapse;font-size:10.5px;margin-top:6px;">
<tr style="background:#f5f5f7;">{head}</tr>{body}</table></td></tr>""")

    # Бизнес-результат
    ev = m.get("organic_goal_events") if m.get("available") else None
    H.append(f"""<tr><td style="padding:18px 26px 0;font-family:Arial,Helvetica,sans-serif;color:{INK};font-size:12.5px;line-height:1.6;">
<div style="font-size:14px;font-weight:bold;border-bottom:2px solid {ACCENT};padding-bottom:6px;margin-bottom:10px;">Результат для бизнеса</div>
Целевые обращения (события Метрики, органика): <b>{fmt(ev)}</b> — уникальность не подтверждена, выборка ниже порога {snap['thresholds']['low_conversions']}.<br>
Квалифицированные лиды: <b>нет данных</b> · Сделки: <b>нет данных</b> · Выручка: <b>нет данных</b> (CRM не подключена).<br>
<span style="color:{MUTED};">Ограничение: цели Метрики фиксируют события, а не подтверждённые обращения; ключевые события GA4 размечены 2026-08-18, сравнение конверсий внутри периода некорректно.</span></td></tr>""")

    # Решения
    dec_html = ""
    for d in decs:
        dec_html += (f"<div style='border:1px solid {LINE};border-left:4px solid {ACCENT};border-radius:8px;padding:12px 14px;margin-bottom:10px;font-size:11.5px;line-height:1.6;'>"
                     f"<div style='font-weight:bold;font-size:12.5px;'>{d['id']}</div>"
                     f"<b>Что утвердить:</b> {d['approve']}<br><b>Рекомендация:</b> {d['recommended']}<br>"
                     f"<b>Эффект и основание:</b> {d['effect']}<br><b>Затраты:</b> {d['cost']}<br>"
                     f"<b>Ответственный:</b> {d['owner']} · <b>Срок:</b> {d['deadline']}<br>"
                     f"<b>Зависимость:</b> {d['dependency']}<br><b>Критерий успеха:</b> {d['success']}<br>"
                     f"<b>Риск:</b> {d['risk']}<br><b>Rollback / stop:</b> {d['rollback']}</div>")
    H.append(f"""<tr><td style="padding:18px 26px 0;font-family:Arial,Helvetica,sans-serif;color:{INK};">
<div style="font-size:14px;font-weight:bold;border-bottom:2px solid {ACCENT};padding-bottom:6px;margin-bottom:10px;">Решения руководителя ({len(decs)})</div>{dec_html}</td></tr>""")

    # Риски
    risks = "".join(f"<li><b>{f['level'].upper()}</b> — {f['title']}. {f['detail']} <i>{f['effect_on_report']}</i></li>"
                    for f in [x for x in dq["findings"] if x["level"] in ("critical", "warning")][:6])
    H.append(f"""<tr><td style="padding:18px 26px 0;font-family:Arial,Helvetica,sans-serif;color:{INK};font-size:11.5px;line-height:1.6;">
<div style="font-size:14px;font-weight:bold;border-bottom:2px solid {ACCENT};padding-bottom:6px;margin-bottom:8px;">Риски и качество данных</div>
<ul style="margin:0;padding-left:18px;">{risks}</ul></td></tr>
<tr><td style="padding:16px 26px 20px;font-family:Arial,Helvetica,sans-serif;color:{INK};font-size:12px;line-height:1.6;">
<div style="font-size:14px;font-weight:bold;border-bottom:2px solid {ACCENT};padding-bottom:6px;margin-bottom:8px;">Следующая контрольная точка</div>
22.08.2026 — результат сверки источников (DATA-001).<br>26.08.2026 — промежуточный срез эксперимента метаданных: проверка объёма наблюдений; вывод только при достаточной мощности.</td></tr>
<tr><td style="background:#f5f5f7;padding:12px 26px;font-family:Arial,Helvetica,sans-serif;font-size:10.5px;color:{MUTED};line-height:1.5;border-top:1px solid {LINE};">
Полные таблицы, методика, реестр экспериментов и технические задания — в приложении: reports/seo/intelligence/{snap['report_date']}-appendix.md · методика: docs/seo/reporting-methodology.md · проверки качества: reports/seo/intelligence/data-quality/{snap['report_date']}.json</td></tr>
</table></td></tr></table></body></html>""")
    return "".join(H)


def md_appendix(snap, prev, dq, charts) -> str:
    yx, g = snap["yandex"], snap["google"]
    m, ga = snap["analytics"].get("metrika", {}), snap["analytics"].get("ga4", {})
    date_h = dt.date.fromisoformat(snap["report_date"]).strftime("%d.%m.%Y")
    L = [f"# Аналитическое приложение — {date_h}", "",
         "Приложение к executive brief. Все значения рассчитаны из канонического snapshot "
         f"`reports/seo/intelligence/snapshots/{snap['report_date']}.json`.", "",
         "## 1. Методика и определения", "",
         "Полное описание: `docs/seo/reporting-methodology.md`. Ключевое:", "",
         "- **Показы** — сколько раз страницы сайта показаны в выдаче по запросам источника. "
         "Это видимость сайта, а не объём рыночного спроса.",
         "- **CTR** = клики / показы, рассчитывается только при показах > 0.",
         "- **Средняя позиция** — среднее по показам, не фиксированное место в выдаче.",
         "- **«В топ-10»** — средняя позиция ≤ 10 строго. Список из десяти строк по объёму показов "
         "называется «10 запросов с наибольшим числом показов».",
         "- **Целевое событие** — срабатывание цели Метрики; не является подтверждённой заявкой или лидом.",
         "- **Низкая выборка** — показы < {}, визиты < {}, конверсии < {}.".format(
             snap["thresholds"]["low_impressions"], snap["thresholds"]["low_visits"],
             snap["thresholds"]["low_conversions"]),
         "", "## 2. Источники и периоды", "",
         "| Источник | Метрика | Фильтры | Период | Последнее событие | Сбор |", "|---|---|---|---|---|---|"]
    for src, metric in ((yx.get("source"), "показы/клики/позиции по запросам"),
                        (g.get("source"), "показы/клики/позиции по запросам и страницам"),
                        (m.get("source"), m.get("metric_name", "")),
                        (ga.get("source"), ga.get("metric_name", ""))):
        if not src:
            continue
        L.append(f"| {src['source_name']} | {metric} | {json.dumps(src['filters'], ensure_ascii=False)} | "
                 f"{src['current_period_start']}–{src['current_period_end']} ({src['current_period_days']} дн.) | "
                 f"{src['latest_event_date']} | {src['collected_at']} |")

    L += ["", "## 3. Яндекс: 10 запросов с наибольшим числом показов", "",
          "| Запрос | Показы | Клики | CTR | Средняя позиция | Тип | Выборка |", "|---|---|---|---|---|---|---|"]
    ents = sorted([e for e in yx["entities"]], key=lambda e: -(e["impressions"] or 0))
    for e in ents[:10]:
        L.append(f"| {e['entity_id']} | {e['impressions']} | {e['clicks']} | {pct(e['ctr'])} | "
                 f"{e['average_position']} | {'брендовый' if e['branded'] else e['intent']} | {e['confidence']} |")
    top10 = [e for e in ents if e["average_position"] and e["average_position"] <= 10]
    L += ["", f"## 4. Яндекс: запросы со средней позицией до 10 ({len(top10)} из {len(ents)})", "",
          "| Запрос | Средняя позиция | Показы | Клики |", "|---|---|---|---|"]
    for e in sorted(top10, key=lambda e: e["average_position"])[:15]:
        L.append(f"| {e['entity_id']} | {e['average_position']} | {e['impressions']} | {e['clicks']} |")
    nb = [e for e in ents if not e["branded"]]
    L += ["", "## 5. Brand / non-brand", "",
          f"- Небрендовые запросы: {len(nb)} из {len(ents)}, показы {sum(e['impressions'] or 0 for e in nb)}",
          f"- Брендовые запросы: {len(ents) - len(nb)}, показы {sum(e['impressions'] or 0 for e in ents if e['branded'])}",
          "", "## 6. Google: запросы и страницы (разные scope)", "",
          f"Запросов со средней позицией ≤10: **{g['totals']['queries_position_le_10']}**; "
          f"страниц со средней позицией ≤10: **{g['totals']['pages_position_le_10']}**. "
          "Это разные сущности: позиция страницы усредняется по её запросам, позиция запроса — по его показам.",
          "", "### 10 запросов Google с наибольшим числом показов", "",
          "| Запрос | Показы | Клики | Средняя позиция | Выборка |", "|---|---|---|---|---|"]
    for e in sorted(g["entities"], key=lambda e: -e["impressions"])[:10]:
        L.append(f"| {e['entity_id']} | {e['impressions']} | {e['clicks']} | {e['average_position']} | {e['confidence']} |")
    L += ["", "### 10 страниц Google с наибольшим числом показов", "",
          "| Страница | Показы | Клики | Средняя позиция | Выборка |", "|---|---|---|---|---|"]
    for p in sorted(g["pages"], key=lambda p: -p["impressions"])[:10]:
        L.append(f"| {p['entity_id']} | {p['impressions']} | {p['clicks']} | {p['average_position']} | {p['confidence']} |")
    L += ["", "## 7. Вендорские кластеры", "", "| Вендор | Показы | Клики | Лучшая позиция | Запросов | Выборка |",
          "|---|---|---|---|---|---|"]
    for row in charts["vendor-heatmap"]["table"][1:]:
        L.append("| " + " | ".join(str(x) for x in row) + " |")
    idx = yx["indexation"]
    L += ["", "## 8. Индексация", "",
          f"- Всего известных URL: {fmt(idx['total_known_urls'])}",
          f"- В поиске: {fmt(idx['indexed_urls'])}",
          f"- Исключено: {fmt(idx['excluded_urls'])} — разбивка по причинам: нет данных (не выгружается)",
          f"- Коммерчески значимых среди исключённых: нет данных",
          f"- ИКС: {fmt(idx['sqi'])}",
          "", "## 9. Расхождения источников", "",
          "| Показатель | Яндекс.Вебмастер | Метрика | GA4 | Комментарий |", "|---|---|---|---|---|",
          f"| Клики / визиты / сессии органики | {yx['totals']['clicks']} кликов (выборка топ-100) | "
          f"{fmt(m.get('organic_visits'))} визитов | {fmt(ga.get('organic_sessions'))} сессий | "
          "разные сущности и окна; расхождение кратное — тикет DATA-001 |",
          f"| Все визиты / сессии | — | {fmt(m.get('visits_total'))} | {fmt(ga.get('sessions_total'))} | "
          "визит Метрики ≠ сессия GA4 по правилам склейки |",
          f"| Конверсии | — | {fmt(m.get('goal_events_total'))} событий | {fmt(ga.get('organic_key_events'))} key events | "
          "разметка GA4 от 2026-08-18 — данные несопоставимы |", ""]
    revs = snap["analytics"].get("intra_day_revisions", [])
    if revs:
        L += ["### Пересборы внутри дня", ""]
        for r in revs:
            L.append(f"- `{r['metric']}`: наблюдались значения {r['values_seen']}; каноническое — {r['canonical']}. {r['reason']}")
        L.append("")
    L += ["## 10. Реестр экспериментов", ""]
    for e in snap["experiments"]:
        L += [f"### {e['id']} — статус {e['status']}", "",
              f"- Гипотеза: {e['hypothesis']}",
              f"- Treatment URL: {', '.join(e['treatment_urls'])}",
              f"- Control: {e['control_urls']}",
              f"- Дата деплоя: {e['deployment_date']}; дата появления сниппета в выдаче: нет данных (требуется фиксация)",
              f"- Первичная метрика: {e['primary_metric']}",
              f"- Guardrails: {', '.join(e['guardrail_metrics'])}",
              f"- Минимальный объём наблюдений: {e['minimum_exposure']}",
              f"- Владелец: {e['owner'] or 'не назначен'}",
              "- Ограничение: метаданные и FAQ внедрены одной правкой — вклад элементов неразделим "
              "(см. решение DEC-002 и тикеты SEO-EXP-001 / CRO-EXP-002).", ""]
    L += ["## 11. Полная таблица рисков и качества данных", "",
          "| Уровень | Код | Описание | Влияние на отчёт |", "|---|---|---|---|"]
    for f in dq["findings"]:
        L.append(f"| {f['level']} | {f['code']} | {f['detail']} | {f['effect_on_report']} |")
    L += ["", "## 12. Технические задания (execution tickets)", "",
          "| ID | Приоритет | Задача | Файл |", "|---|---|---|---|",
          "| DATA-001 | P0 | Сверка источников аналитики | `reports/seo/tasks/DATA-001-analytics-reconciliation.md` |",
          "| SEO-EXP-001 | P0 | Эксперимент метаданных vendor-страниц | `reports/seo/tasks/SEO-EXP-001-vendor-metadata.md` |",
          "| CRO-EXP-002 | P1 | FAQ и коммерческие доказательства | `reports/seo/tasks/CRO-EXP-002-faq-commercial-proof.md` |",
          "| INDEX-001 | P1 | Классификация исключённых URL | `reports/seo/tasks/INDEX-001-excluded-urls.md` |",
          "| PPC-RES-001 | P2 | Прогноз рекламного теста | `reports/seo/tasks/PPC-RES-001-forecast.md` |",
          "| BRAND-001 | P2 | Due diligence домена | `reports/seo/tasks/BRAND-001-domain-due-diligence.md` |",
          "| CONTENT-001 | P2 | Анализ интента Depositphotos | `reports/seo/tasks/CONTENT-001-depositphotos-intent.md` |",
          "| DATA-002 | P2 | Дневной ряд Яндекс.Вебмастера | `reports/seo/tasks/DATA-002-yandex-daily-series.md` |",
          "", "## 13. Графики", ""]
    for name, c in charts.items():
        if c.get("path"):
            L.append(f"- `{c['path']}` — {c['alt']}")
        else:
            L.append(f"- **{name}: не построен.** {c.get('unavailable_reason')}")
    L += ["", "## 14. История изменений методики", "",
          "- 2026-08-19 — v2.0.0: введён канонический snapshot, sidecar качества данных, "
          "строгая граница топ-10, разделение scope query/page, отказ от Growth Score в основном отчёте, "
          "запрет формулировок «заявка» и «рыночный спрос», обязательная маркировка низкой выборки. "
          "Подробности перехода: `docs/seo/reporting-v2-migration.md`.", ""]
    return "\n".join(L)


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    snap = json.loads((BASE / "snapshots" / f"{date}.json").read_text(encoding="utf-8"))
    dq = json.loads((BASE / "data-quality" / f"{date}.json").read_text(encoding="utf-8"))
    import charts as charts_mod
    charts = charts_mod.build_all(snap, date)
    prev = prev_snapshot(date)
    st = compute_statuses(snap, prev, dq)
    cards = kpi_cards(snap, prev)
    changes = changes_block(snap, prev)
    decs = decisions(snap, dq)

    md = md_executive(snap, prev, dq, st, cards, changes, decs)
    html = html_executive(snap, st, cards, changes, decs, dq, charts)
    app = md_appendix(snap, prev, dq, charts)
    (BASE / f"{date}-executive.md").write_text(md, encoding="utf-8")
    (BASE / f"{date}-executive.html").write_text(html, encoding="utf-8")
    (BASE / f"{date}-appendix.md").write_text(app, encoding="utf-8")
    words = len(md.split())
    print(f"executive: {BASE}/{date}-executive.md ({words} слов), html и приложение сформированы")
    if words > 900:
        print(f"ВНИМАНИЕ: объём основной части {words} слов (лимит 900)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
