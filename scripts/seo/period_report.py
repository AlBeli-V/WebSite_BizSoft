#!/usr/bin/env python3
"""Периодные отчёты Growth Intelligence: неделя, месяц, год.

Поручение руководителя 30.08.2026. Ежедневное письмо остаётся как есть;
периодные отчёты — отдельный контур с агрегированной статистикой:

  weekly  — суббота 08:00 МСК, период с прошлой субботы по пятницу
            включительно (граница окна 08:00 МСК; данные агрегируются по
            полным календарным дням, день отправки не входит);
  monthly — 1-го числа 08:00 МСК за весь прошедший календарный месяц;
  yearly  — 1 января 09:00 МСК за весь прошедший календарный год; первый
            выпуск — только когда система отработала полный календарный
            год с хвостиком (данные ведутся с июня 2026 → первый годовой
            отчёт 01.01.2028 за 2027 год).

Каждый показатель сравнивается с предыдущим периодом той же длины.
Источники: дневная факт-витрина (reports/seo/data/daily/), витрина Директа
(reports/seo/ppc/direct-stats.json), снимки на границах периода
(индексация), история вердиктов экспериментов и журналы решений. Источник,
не дозревший к хвосту периода (лаг Вебмастера/GSC ~3 дня), показывается с
покрытием «X из N дней» — цифры честно помечаются как неполные.

Запуск: python3 scripts/seo/period_report.py weekly|monthly|yearly [дата-отправки]
Результат: reports/seo/intelligence/period/<mode>-<from>_<to>.{html,txt,json}
           reports/seo/public/<weekly|monthly|yearly>/<from>_<to>/index.html
           reports/seo/intelligence/period/latest-<mode>.json (маркер сборки)
"""

from __future__ import annotations

import calendar
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from textfmt import num, ru_date, ru_date_full, signed  # noqa: E402
from report_v4 import T, SP, FONT  # noqa: E402  — единые токены оформления

DAILY = pathlib.Path("reports/seo/data/daily")
DIRECT = pathlib.Path("reports/seo/ppc/direct-stats.json")
SNAPSHOTS = pathlib.Path("reports/seo/intelligence/snapshots")
EXP_HISTORY = pathlib.Path("reports/seo/intelligence/experiments-history")
PPC_DECISIONS = pathlib.Path("reports/seo/ppc/decisions.jsonl")
OUT_DIR = pathlib.Path("reports/seo/intelligence/period")
PUBLIC = pathlib.Path("reports/seo/public")
MAILED = pathlib.Path("reports/seo/intelligence/last-period-mailed.json")

# Первый годовой отчёт: система должна отработать полный календарный год
# с хвостиком. Данные ведутся с июня 2026 → первый полный год — 2027.
FIRST_YEARLY_YEAR = 2027

MODE_LABEL = {"weekly": "еженедельный", "monthly": "ежемесячный",
              "yearly": "годовой"}

MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
              "августа", "сентября", "октября", "ноября", "декабря"]
MONTHS_NOM = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
              "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]


# ── Границы периодов ────────────────────────────────────────────────────────

def period_bounds(mode: str, send_date: dt.date) -> tuple[dt.date, dt.date]:
    """[from, to] включительно — полные календарные дни периода."""
    if mode == "weekly":
        # Отправка в субботу: период — прошлая суббота … пятница (7 дней).
        offset = (send_date.weekday() - 5) % 7 or 7
        prev_sat = send_date - dt.timedelta(days=offset)
        return prev_sat, prev_sat + dt.timedelta(days=6)
    if mode == "monthly":
        first_this = send_date.replace(day=1)
        last_prev = first_this - dt.timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    if mode == "yearly":
        y = send_date.year - 1
        return dt.date(y, 1, 1), dt.date(y, 12, 31)
    raise SystemExit(f"неизвестный режим: {mode}")


def prev_bounds(mode: str, p_from: dt.date, p_to: dt.date) -> tuple[dt.date, dt.date]:
    if mode == "monthly":
        last = p_from - dt.timedelta(days=1)
        return last.replace(day=1), last
    if mode == "yearly":
        return dt.date(p_from.year - 1, 1, 1), dt.date(p_from.year - 1, 12, 31)
    span = (p_to - p_from).days + 1
    return p_from - dt.timedelta(days=span), p_from - dt.timedelta(days=1)


def period_title(mode: str, p_from: dt.date, p_to: dt.date) -> str:
    if mode == "weekly":
        return f"за период {p_from.strftime('%d.%m')} по {p_to.strftime('%d.%m.%Y')}"
    if mode == "monthly":
        return (f"за {MONTHS_NOM[p_from.month - 1]} {p_from.year} "
                f"({p_from.strftime('%d.%m')} по {p_to.strftime('%d.%m.%Y')})")
    return f"за {p_from.year} год"


# ── Агрегация дневных рядов ─────────────────────────────────────────────────

def _days(p_from: dt.date, p_to: dt.date) -> list[str]:
    return [(p_from + dt.timedelta(days=i)).isoformat()
            for i in range((p_to - p_from).days + 1)]


def _load_series() -> dict:
    out = {}
    for name in ("yandex", "gsc", "metrika", "ga4"):
        p = DAILY / f"{name}.json"
        if p.exists():
            try:
                out[name] = json.loads(p.read_text(encoding="utf-8"))["series"]
            except (json.JSONDecodeError, KeyError, OSError):
                out[name] = {}
        else:
            out[name] = {}
    return out


def _agg(series: dict, days: list[str]) -> tuple[float, int]:
    """Сумма ряда за дни периода и число дней, где значение есть."""
    vals = [series.get(d) for d in days]
    present = [v for v in vals if v is not None]
    return float(sum(present)), len(present)


def collect_metrics(p_from: dt.date, p_to: dt.date) -> dict:
    """KPI периода: суммы, покрытие по дням, экстремумы."""
    days = _days(p_from, p_to)
    s = _load_series()
    metrics = {}
    spec = [
        ("yandex_impressions", "yandex", "impressions", "Яндекс, показы"),
        ("yandex_clicks", "yandex", "clicks", "Яндекс, клики"),
        ("gsc_impressions", "gsc", "impressions", "Google, показы"),
        ("gsc_clicks", "gsc", "clicks", "Google, клики"),
        ("visits_all", "metrika", "visits_all", "Визиты сайта, все"),
        ("visits_organic", "metrika", "visits_organic", "Визиты, органика"),
        ("goals_organic", "metrika", "goal_reaches_organic",
         "Достижения целей (органика)"),
        ("ga4_sessions", "ga4", "sessions_organic", "GA4, органические сессии"),
    ]
    for key, src, row, label in spec:
        total, covered = _agg(s.get(src, {}).get(row, {}), days)
        metrics[key] = {"label": label, "total": total, "covered_days": covered,
                        "days": len(days)}
    # CTR Яндекса за период — из уже посчитанных сумм.
    yi, yc = metrics["yandex_impressions"]["total"], metrics["yandex_clicks"]["total"]
    metrics["yandex_ctr"] = {"label": "Яндекс, CTR",
                             "total": (yc / yi) if yi else None,
                             "covered_days": metrics["yandex_clicks"]["covered_days"],
                             "days": len(days), "is_ratio": True}
    # Экстремумы: лучший и худший день по кликам Яндекса и по целям.
    def extremes(row: dict) -> dict | None:
        vals = {d: row.get(d) for d in days if row.get(d) is not None}
        if not vals:
            return None
        best = max(vals, key=vals.get)
        worst = min(vals, key=vals.get)
        return {"best": {"date": best, "value": vals[best]},
                "worst": {"date": worst, "value": vals[worst]}}
    metrics["_extremes"] = {
        "yandex_clicks": extremes(s.get("yandex", {}).get("clicks", {})),
        "goals": extremes(s.get("metrika", {}).get("goal_reaches_organic", {})),
    }
    return metrics


# ── Реклама за период ───────────────────────────────────────────────────────

def collect_ads(p_from: dt.date, p_to: dt.date) -> dict:
    if not DIRECT.exists():
        return {"available": False, "reason": "выгрузки Директа нет"}
    try:
        d = json.loads(DIRECT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"available": False, "reason": "витрина Директа нечитаема"}
    days = set(_days(p_from, p_to))
    rows = [r for r in d.get("groups", []) if r.get("Date") in days]
    if not rows:
        return {"available": False,
                "reason": "в периоде не было открутки (или данных за него нет)"}
    by_group: dict[str, dict] = {}
    for r in rows:
        g = by_group.setdefault(r["AdGroupName"], {"imp": 0, "clicks": 0, "cost": 0.0})
        g["imp"] += r.get("Impressions") or 0
        g["clicks"] += r.get("Clicks") or 0
        g["cost"] += r.get("Cost") or 0.0
    total_cost = sum(g["cost"] for g in by_group.values())
    total_clicks = sum(g["clicks"] for g in by_group.values())
    return {
        "available": True,
        "campaign": "bs-test-2026-09",
        "cost": total_cost, "clicks": total_clicks,
        "impressions": sum(g["imp"] for g in by_group.values()),
        "cpc": (total_cost / total_clicks) if total_clicks else None,
        "groups": sorted(
            ({"name": k.split(" — ")[0], **v,
              "cpc": (v["cost"] / v["clicks"]) if v["clicks"] else None}
             for k, v in by_group.items()), key=lambda g: -g["cost"]),
    }


# ── Индексация: границы периода по снимкам ──────────────────────────────────

def _nearest_snapshot(date: dt.date, direction: int) -> dict | None:
    """Снимок на дату или ближайший в сторону direction (±1), до 3 дней."""
    for shift in range(0, 4):
        p = SNAPSHOTS / f"{(date + dt.timedelta(days=direction * shift)).isoformat()}.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
    return None


def collect_indexation(p_from: dt.date, p_to: dt.date) -> dict:
    start = _nearest_snapshot(p_from, +1)
    end = _nearest_snapshot(p_to + dt.timedelta(days=1), -1)
    def idx(snap):
        return ((snap or {}).get("yandex") or {}).get("indexation") or {}
    a, b = idx(start), idx(end)
    if not b:
        return {"available": False, "reason": "нет снимка на конец периода"}
    return {"available": True,
            "start": {"indexed": a.get("indexed_urls"), "known": a.get("total_known_urls")},
            "end": {"indexed": b.get("indexed_urls"), "known": b.get("total_known_urls")},
            "start_missing": not a}


# ── События периода: эксперименты и решения ─────────────────────────────────

def collect_events(p_from: dt.date, p_to: dt.date) -> dict:
    days = set(_days(p_from, p_to))
    verdicts = []
    if EXP_HISTORY.exists():
        for f in sorted(EXP_HISTORY.glob("*/*.json")):
            if f.stem in days:
                try:
                    r = json.loads(f.read_text(encoding="utf-8"))
                    verdicts.append({"ticket": r.get("ticket"), "date": r.get("date"),
                                     "verdict": r.get("verdict"),
                                     "recommendation": r.get("recommendation")})
                except (json.JSONDecodeError, OSError):
                    continue
    decisions = []
    if PPC_DECISIONS.exists():
        for line in PPC_DECISIONS.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            when = (r.get("date") or r.get("decided_at") or "")[:10]
            if when in days:
                decisions.append({"date": when,
                                  "text": r.get("summary") or r.get("decision_id")
                                  or r.get("action") or "решение"})
    return {"experiment_verdicts": verdicts, "ppc_decisions": decisions[:6]}


# ── Сборка блоков ───────────────────────────────────────────────────────────

def build(mode: str, send_date: dt.date) -> dict:
    p_from, p_to = period_bounds(mode, send_date)
    q_from, q_to = prev_bounds(mode, p_from, p_to)
    cur = collect_metrics(p_from, p_to)
    prev = collect_metrics(q_from, q_to)
    b = {
        "mode": mode, "mode_label": MODE_LABEL[mode],
        "send_date": send_date.isoformat(),
        "from": p_from.isoformat(), "to": p_to.isoformat(),
        "prev_from": q_from.isoformat(), "prev_to": q_to.isoformat(),
        "title_period": period_title(mode, p_from, p_to),
        "subject": (f"BIZSoft Growth Intelligence — {MODE_LABEL[mode]} "
                    f"{period_title(mode, p_from, p_to)}"),
        "metrics": cur, "prev_metrics": prev,
        "ads": collect_ads(p_from, p_to),
        "prev_ads": collect_ads(q_from, q_to),
        "indexation": collect_indexation(p_from, p_to),
        "events": collect_events(p_from, p_to),
        "summary": "",
        "attention": [],
    }
    _summarise(b)
    return b


def _delta_pct(cur: float, prev: float) -> float | None:
    if prev:
        return (cur - prev) / prev
    return None


def _clicks_sentence(cur: dict, prev: dict) -> str:
    """Фраза о кликах: вердикт только по полным окнам.

    Вердикт «снизились» по неполному окну — ложь: недозревший хвост периода
    прежде считался нулём (аудит 03.09.2026).
    """
    yc, yp = cur["total"], prev["total"]
    if not (_fully_covered(cur) and _fully_covered(prev)):
        return (f"кликов из Яндекса {num(yc)} за {cur['covered_days']} из "
                f"{cur['days']} дн., сравнение с прошлым периодом не приводится: "
                f"окна покрыты не полностью")
    d = _delta_pct(yc, yp)
    if d is None:
        return f"кликов из Яндекса {num(yc)}"
    word = "выросли" if d > 0.05 else "снизились" if d < -0.05 else "держатся"
    return f"клики из Яндекса {word} ({num(yp)} → {num(yc)}, {d:+.0%})"


def _summarise(b: dict) -> None:
    """Итог периода одним абзацем + список «на что смотреть»."""
    cur, prev = b["metrics"], b["prev_metrics"]
    parts = []
    parts.append(_clicks_sentence(cur["yandex_clicks"], prev["yandex_clicks"]))
    gc = cur["goals_organic"]["total"]
    gp = prev["goals_organic"]["total"]
    parts.append(f"достижений целей {num(gc)}"
                 + (f" против {num(gp)} прошлым периодом" if gp else ""))
    if b["ads"].get("available"):
        parts.append(f"реклама: {b['ads']['cost']:.0f} ₽ и "
                     f"{num(b['ads']['clicks'])} кликов")
    b["summary"] = "За период " + "; ".join(parts) + "."

    # Внимание: недозревшие источники и заметные падения.
    for key in ("yandex_clicks", "gsc_clicks", "visits_all"):
        m = cur[key]
        if m["covered_days"] < m["days"]:
            b["attention"].append(
                f"{m['label']}: данные за {m['covered_days']} из {m['days']} дней — "
                "хвост периода дозреет у источника, цифры уточнятся")
    # Поисковые источники дозревают задним числом (~3 дня): если период
    # кончился только что, последние его дни могут быть занижены — и это не
    # ловится покрытием, потому что нули в ряду уже стоят.
    if (dt.date.fromisoformat(b["send_date"])
            - dt.date.fromisoformat(b["to"])).days <= 3:
        b["attention"].append(
            "последние ~3 дня периода у Яндекс.Вебмастера и GSC дозревают "
            "задним числом — суммы по поиску могут вырасти при уточнении")
    d_imp = _delta_pct(cur["yandex_impressions"]["total"],
                       prev["yandex_impressions"]["total"])
    if d_imp is not None and d_imp < -0.25:
        b["attention"].append(
            f"показы Яндекса просели на {abs(d_imp):.0%} к прошлому периоду — "
            "смотреть страницы-детракторы в ежедневных отчётах")


# ── Рендер письма ───────────────────────────────────────────────────────────

def _fully_covered(m: dict) -> bool:
    return bool(m.get("days")) and m.get("covered_days") == m.get("days")


def _fmt_metric(m: dict) -> str:
    """«—» для источника без данных за период: ноль и «нет данных» различны."""
    if not m.get("covered_days"):
        return "—"
    if m.get("is_ratio"):
        return "—" if m["total"] is None else f"{m['total'] * 100:.2f}%"
    return num(int(m["total"]))


def _kpi_rows_html(b: dict) -> str:
    rows = ""
    for key in ("yandex_impressions", "yandex_clicks", "yandex_ctr",
                "gsc_impressions", "gsc_clicks", "visits_all",
                "visits_organic", "goals_organic", "ga4_sessions"):
        cur, prev = b["metrics"][key], b["prev_metrics"][key]
        comparable = _fully_covered(cur) and _fully_covered(prev)
        if not comparable:
            delta = "—"
        elif cur.get("is_ratio"):
            delta = ("—" if cur["total"] is None or prev["total"] is None else
                     f"{(cur['total'] - prev['total']) * 100:+.2f} п.п.")
        else:
            d = _delta_pct(cur["total"], prev["total"])
            delta = "—" if d is None else f"{d:+.0%}"
        # Покрытие подписывается обеим колонкам: у прошлого периода оно
        # прежде не показывалось, и «0» читался как измеренный ноль.
        cov = ("" if _fully_covered(cur) else
               f" <span data-meta=\"1\" style=\"color:{T['warning']};\">"
               f"({cur['covered_days']}/{cur['days']} дн.")
        cov += ("" if _fully_covered(prev) or not cov else
                f"; прошлый {prev['covered_days']}/{prev['days']}")
        if cov:
            cov += ")</span>"
        elif not _fully_covered(prev):
            cov = (f" <span data-meta=\"1\" style=\"color:{T['warning']};\">"
                   f"(прошлый {prev['covered_days']}/{prev['days']} дн.)</span>")
        colour = (T["text_primary"] if delta in ("—",) else
                  T["positive"] if delta.startswith("+") else
                  T["danger"] if delta.startswith("-") else T["text_primary"])
        rows += (f"<tr><td style=\"padding:6px 8px 6px 0;font-size:14.5px;"
                 f"border-top:1px solid {T['border']};\">{cur['label']}{cov}</td>"
                 f"<td align=\"right\" style=\"padding:6px 8px;font-size:14.5px;"
                 f"border-top:1px solid {T['border']};\">{_fmt_metric(prev)}</td>"
                 f"<td align=\"right\" style=\"padding:6px 8px;font-size:14.5px;"
                 f"font-weight:600;border-top:1px solid {T['border']};\">"
                 f"{_fmt_metric(cur)}</td>"
                 f"<td align=\"right\" style=\"padding:6px 0 6px 8px;font-size:14.5px;"
                 f"font-weight:600;color:{colour};border-top:1px solid {T['border']};\">"
                 f"{delta}</td></tr>")
    return rows


def _sec(title: str, body: str) -> str:
    return (f"<tr><td style=\"padding:{SP['xl']}px 0 0 0;\">"
            f"<div style=\"font-size:17px;font-weight:700;color:{T['text_primary']};\">"
            f"{title}</div><div style=\"padding-top:{SP['m']}px;\">{body}</div>"
            f"</td></tr>")


def render_html(b: dict) -> str:
    rows = [
        f"<tr><td style=\"padding:0 0 {SP['m']}px 0;\">"
        f"<div style=\"font-size:23px;font-weight:700;color:{T['text_primary']};\">"
        f"BIZSoft Growth Intelligence</div>"
        f"<div style=\"font-size:15px;color:{T['text_secondary']};padding-top:4px;\">"
        f"{b['mode_label'].capitalize()} отчёт {b['title_period']}</div>"
        f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
        f"padding-top:4px;\">Сравнение с предыдущим периодом "
        f"{ru_date(b['prev_from'])}–{ru_date(b['prev_to'])} · данные по полным "
        f"календарным дням, граница окна 08:00 МСК</div></td></tr>",
        f"<tr><td style=\"padding-top:{SP['m']}px;font-size:15.5px;line-height:1.6;"
        f"color:{T['text_primary']};\"><b>Итог:</b> {b['summary']}</td></tr>",
        _sec("Показатели периода",
             f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" "
             f"cellspacing=\"0\"><tr>"
             f"<th align=\"left\" data-meta=\"1\" style=\"font-size:12px;"
             f"color:{T['text_secondary']};padding-bottom:6px;\">Показатель</th>"
             f"<th align=\"right\" data-meta=\"1\" style=\"font-size:12px;"
             f"color:{T['text_secondary']};\">Прошлый</th>"
             f"<th align=\"right\" data-meta=\"1\" style=\"font-size:12px;"
             f"color:{T['text_secondary']};\">Текущий</th>"
             f"<th align=\"right\" data-meta=\"1\" style=\"font-size:12px;"
             f"color:{T['text_secondary']};\">Δ</th></tr>"
             f"{_kpi_rows_html(b)}</table>"),
    ]

    ex = b["metrics"].get("_extremes") or {}
    dyn = []
    if ex.get("yandex_clicks"):
        e = ex["yandex_clicks"]
        dyn.append(f"пик кликов Яндекса — {ru_date(e['best']['date'])} "
                   f"({num(int(e['best']['value']))}), минимум — "
                   f"{ru_date(e['worst']['date'])} ({num(int(e['worst']['value']))})")
    if ex.get("goals") and ex["goals"]["best"]["value"] > 0:
        e = ex["goals"]
        dyn.append(f"больше всего целей — {ru_date(e['best']['date'])} "
                   f"({num(int(e['best']['value']))})")
    if dyn:
        rows.append(_sec("Динамика внутри периода",
                         f"<div style=\"font-size:14.5px;line-height:1.6;\">"
                         + "; ".join(dyn) + ".</div>"))

    ads = b["ads"]
    if ads.get("available"):
        g_rows = "".join(
            f"<div style=\"font-size:14.5px;padding:4px 0;line-height:1.5;\">"
            f"<b>{g['name']}</b> — {g['cost']:.0f} ₽, {num(g['clicks'])} кл."
            + (f", CPC {g['cpc']:.0f} ₽" if g["cpc"] else "") + "</div>"
            for g in ads["groups"])
        prev_ads = b.get("prev_ads") or {}
        cmp_line = ""
        if prev_ads.get("available"):
            cmp_line = (f" Прошлый период: {prev_ads['cost']:.0f} ₽, "
                        f"{num(prev_ads['clicks'])} кл.")
        rows.append(_sec(
            "Реклама — Яндекс.Директ",
            f"<div style=\"font-size:15px;line-height:1.6;\">"
            f"Расход {ads['cost']:.0f} ₽, {num(ads['clicks'])} кликов"
            + (f", CPC {ads['cpc']:.0f} ₽" if ads["cpc"] else "")
            + f".{cmp_line}</div>{g_rows}"))
    else:
        rows.append(_sec("Реклама — Яндекс.Директ",
                         f"<div style=\"font-size:14.5px;color:{T['text_secondary']};\">"
                         f"{ads.get('reason', 'нет данных')}.</div>"))

    ix = b["indexation"]
    if ix.get("available"):
        line = (f"страниц в поиске Яндекса на конец периода: "
                f"{num(ix['end']['indexed'])} из {num(ix['end']['known'])} известных")
        if ix["start"].get("indexed") is not None:
            d = ix["end"]["indexed"] - ix["start"]["indexed"]
            line += f" ({signed(d)} за период)"
        elif ix.get("start_missing"):
            line += " (снимка на начало периода нет — дельта не считается)"
        rows.append(_sec("Индексация",
                         f"<div style=\"font-size:14.5px;line-height:1.6;\">{line}.</div>"))

    ev = b["events"]
    ev_lines = []
    for v in ev["experiment_verdicts"]:
        ev_lines.append(f"{ru_date(v['date'])} — {v['ticket']}: вердикт "
                        f"{v['verdict']}, рекомендация {v['recommendation']}")
    for d in ev["ppc_decisions"]:
        ev_lines.append(f"{ru_date(d['date'])} — Директ: {d['text']}")
    if ev_lines:
        rows.append(_sec("События периода", "".join(
            f"<div style=\"font-size:14.5px;padding:3px 0;line-height:1.5;\">"
            f"{ln}</div>" for ln in ev_lines[:8])))

    if b["attention"]:
        rows.append(_sec("На что смотреть", "".join(
            f"<div style=\"font-size:14.5px;padding:3px 0;line-height:1.55;\">"
            f"• {a}</div>" for a in b["attention"])))

    body = "".join(rows)
    # Один и тот же HTML уходит письмом и публикуется страницей отчёта.
    # Ширина 640 px задана атрибутом и стилем ради почтовых клиентов, но на
    # странице она делала таблицу нижним порогом ширины: телефон получал
    # отчёт с горизонтальной прокруткой всей страницы. Медиазапрос снимает
    # фиксированную ширину только на узком экране; почтовые клиенты, которые
    # вырезают <style> (Gmail), видят прежнюю вёрстку без изменений.
    mobile_css = ("<style>@media (max-width:680px){"
                  ".shell{padding:12px 8px!important}"
                  ".wrap{width:auto!important;max-width:100%!important;padding:16px!important;"
                  "overflow-wrap:anywhere}"
                  ".wrap table{width:100%!important}"
                  "}</style>")
    return (f"<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{b['subject']}</title>{mobile_css}</head>"
            f"<body style=\"margin:0;background:{T['background']};\">"
            f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" "
            f"cellspacing=\"0\"><tr><td align=\"center\" class=\"shell\" "
            f"style=\"padding:24px 12px;\">"
            f"<table role=\"presentation\" width=\"640\" cellpadding=\"0\" "
            f"cellspacing=\"0\" class=\"wrap\" style=\"width:640px;max-width:100%;"
            f"background:{T['surface']};border-radius:14px;padding:28px;"
            f"font-family:{FONT};color:{T['text_primary']};\">{body}"
            f"<tr><td data-meta=\"1\" style=\"padding-top:{SP['xl']}px;font-size:12px;"
            f"color:{T['text_secondary']};\">Ежедневные отчёты продолжают приходить "
            f"отдельно; периодные письма их не заменяют.</td></tr>"
            f"</table></td></tr></table></body></html>")


def render_text(b: dict) -> str:
    L = [f"BIZSOFT GROWTH INTELLIGENCE — {b['mode_label'].upper()} ОТЧЁТ",
         b["title_period"].capitalize(),
         f"Сравнение с {ru_date(b['prev_from'])}–{ru_date(b['prev_to'])}", "",
         f"ИТОГ: {b['summary']}", "", "ПОКАЗАТЕЛИ (прошлый -> текущий)"]
    for key in ("yandex_impressions", "yandex_clicks", "yandex_ctr",
                "gsc_impressions", "gsc_clicks", "visits_all",
                "visits_organic", "goals_organic", "ga4_sessions"):
        cur, prev = b["metrics"][key], b["prev_metrics"][key]
        cov = ("" if cur["covered_days"] == cur["days"]
               else f" [{cur['covered_days']}/{cur['days']} дн.]")
        L.append(f"- {cur['label']}: {_fmt_metric(prev)} -> {_fmt_metric(cur)}{cov}")
    ads = b["ads"]
    L += ["", "РЕКЛАМА"]
    if ads.get("available"):
        L.append(f"- расход {ads['cost']:.0f} р., {num(ads['clicks'])} кликов"
                 + (f", CPC {ads['cpc']:.0f} р." if ads["cpc"] else ""))
        for g in ads["groups"]:
            L.append(f"  {g['name']}: {g['cost']:.0f} р., {num(g['clicks'])} кл.")
    else:
        L.append(f"- {ads.get('reason', 'нет данных')}")
    if b["attention"]:
        L += ["", "НА ЧТО СМОТРЕТЬ"] + [f"- {a}" for a in b["attention"]]
    return "\n".join(L)


# ── Точка входа ─────────────────────────────────────────────────────────────

def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    send_date = (dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2
                 else dt.date.today())
    if mode == "yearly" and send_date.year - 1 < FIRST_YEARLY_YEAR:
        print(f"годовой отчёт начинается с итогов {FIRST_YEARLY_YEAR} года "
              f"(система должна отработать полный календарный год) — пропуск")
        return
    b = build(mode, send_date)
    stem = f"{mode}-{b['from']}_{b['to']}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{stem}.json").write_text(
        json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT_DIR / f"{stem}.html").write_text(render_html(b), encoding="utf-8")
    (OUT_DIR / f"{stem}.txt").write_text(render_text(b), encoding="utf-8")
    # Маркер «что отправлять»: workflow берёт из него тему и путь письма.
    (OUT_DIR / f"latest-{mode}.json").write_text(json.dumps({
        "subject": b["subject"], "html": f"{stem}.html", "txt": f"{stem}.txt",
        "from": b["from"], "to": b["to"], "built_at":
            dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")},
        ensure_ascii=False, indent=1), encoding="utf-8")
    # Веб-версия — публикуется на прод вместе с каталогом public.
    web_dir = PUBLIC / mode / f"{b['from']}_{b['to']}"
    web_dir.mkdir(parents=True, exist_ok=True)
    (web_dir / "index.html").write_text(render_html(b), encoding="utf-8")
    print(f"{b['subject']} -> {OUT_DIR / (stem + '.html')} и {web_dir}/index.html")


if __name__ == "__main__":
    main()
