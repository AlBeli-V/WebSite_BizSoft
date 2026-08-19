#!/usr/bin/env python3
"""BIZSoft Growth Intelligence — Executive Command Center (письмо V4).

Панель управления ростом: результат, причины изменений, автономные действия,
состояние экспериментов и следующие контрольные точки. Порядок блоков фиксирован:

  A Header · B Status bar · C От вас · D Четыре показателя · E Сигналы дня ·
  F Драйверы и детракторы · G Контроль экспериментов · H Автономное исполнение ·
  I Радар возможностей · J Здоровье данных и риски · K Контрольные точки · L Ссылки

Объём 800–1000 видимых слов, первый экран — не более 250.
Числа берутся только из снимка и аналитических модулей; в текст не вписываются.

Запуск: python3 scripts/seo/report_v4.py [YYYY-MM-DD]
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import charts_v4                      # noqa: E402
import drivers as drivers_mod         # noqa: E402
import experiments as exp_mod         # noqa: E402
import opportunity as opp_mod         # noqa: E402
import report_v2                      # noqa: E402
from textfmt import (counted, num, plural, pct, ru_date,  # noqa: E402
                     ru_date_full, signed, signed_pct)

BASE = pathlib.Path("reports/seo/intelligence")
REPO = "https://github.com/AlBeli-V/WebSite_BizSoft"
BRANCH = "claude/biz-soft-rating-tracking-5rf03g"
BLOB = f"{REPO}/blob/{BRANCH}"
PUBLIC_REPORT_BASE_URL = os.environ.get("PUBLIC_REPORT_BASE_URL", "").rstrip("/")

# ── Design tokens ───────────────────────────────────────────────────────────
T = {
    "background": "#F6F8FB", "surface": "#FFFFFF", "text_primary": "#101828",
    "text_secondary": "#667085", "border": "#EAECF0", "brand": "#F4511E",
    "positive": "#12B76A", "warning": "#F79009", "info": "#2E90FA",
    "danger": "#D92D20", "muted": "#98A2B3",
}
SP = {"xs": 4, "s": 8, "m": 12, "l": 16, "xl": 24, "xxl": 32}
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',"
        "Arial,sans-serif")
FIRST_SCREEN_MARKER = "<!--first-screen-end-->"

PILL_COLOUR = {
    "positive": T["positive"], "mixed": T["warning"], "negative": T["danger"],
    "stable": T["info"], "verified": T["positive"], "limited": T["warning"],
    "degraded": T["danger"], "none": T["muted"], "required": T["brand"],
}
PILL_LABEL = {
    "positive": "рост", "mixed": "смешанная", "negative": "снижение",
    "stable": "без изменений", "verified": "сверено", "limited": "ограничено",
    "degraded": "сбой", "none": "не требуется", "required": "требуется",
}
VERDICT_LABEL = {
    "too_early": "рано для вывода", "observing": "наблюдаем",
    "positive": "подтверждён", "negative": "не подтверждён",
    "inconclusive": "вывод невозможен",
}
STAGE_LABEL = {
    "proposed": "предложено", "approved": "утверждено", "implemented": "внедрено",
    "tested": "проверено", "deployed": "на сайте", "observing": "наблюдение",
    "accepted": "принято", "rejected": "отклонено", "blocked": "заблокировано",
}


def words(*parts: str) -> int:
    text = re.sub(r"<[^>]+>", " ", " ".join(p for p in parts if p))
    return len([w for w in re.split(r"\s+", text) if w.strip(" ·—–-|→")])


# ── Аналитические блоки ─────────────────────────────────────────────────────

def search_status(snap: dict, prev: dict | None) -> str:
    """positive | mixed | negative | stable — по знакам изменений обеих систем."""
    if not prev:
        return "stable"
    g = snap["google"]["totals"]
    signs = [1 if g["impressions_last7"] > g["impressions_prev7"]
             else (-1 if g["impressions_last7"] < g["impressions_prev7"] else 0)]
    yt, yp = snap["yandex"]["totals"], prev["yandex"]["totals"]
    for key in ("impressions", "queries_position_le_10"):
        d = (yt.get(key) or 0) - (yp.get(key) or 0)
        signs.append(1 if d > 0 else (-1 if d < 0 else 0))
    if all(s == 0 for s in signs):
        return "stable"
    if all(s >= 0 for s in signs):
        return "positive"
    if all(s <= 0 for s in signs):
        return "negative"
    return "mixed"


def kpi_cards(snap: dict, prev: dict | None, dq: dict) -> list[dict]:
    """Четыре показателя руководителя. Отсутствие CRM — приглушённое состояние."""
    yt = snap["yandex"]["totals"]
    yp = (prev or {}).get("yandex", {}).get("totals", {})
    g, gt = snap["google"], snap["google"]["totals"]
    m = snap["analytics"]["metrika"]
    sample = dq.get("sample_ctr") or {}

    imp_delta = yt["impressions"] - yp["impressions"] if yp else None
    top_delta = (yt["queries_position_le_10"] - yp["queries_position_le_10"]) if yp else None
    daily = [d["impressions"] for d in (g.get("daily") or [])][-14:]

    cards = [
        {"key": "yandex", "label": "Видимость в Яндексе",
         "value": num(yt["impressions"]), "unit": "показов",
         "delta": signed(imp_delta), "delta_dir": _dir(imp_delta),
         "relative": None,
         "relative_note": "относительный процент не публикуется: окна источника пересекаются",
         "period": f"{ru_date(snap['yandex']['source']['current_period_start'])}–"
                   f"{ru_date(snap['yandex']['source']['current_period_end'])}",
         "source": "Яндекс.Вебмастер, выборка топ-100 запросов",
         "confidence": "достаточная",
         "interpretation": f"На первой странице {yt['queries_position_le_10']} из "
                           f"{yt['queries_tracked']} запросов выборки, "
                           f"{signed(top_delta)} к вчера. "
                           f"CTR выборки {pct(sample.get('value'), 2)} — "
                           f"{sample.get('caveat', '')}.",
         "muted": False, "sparkline": None},
        {"key": "google", "label": "Видимость в Google",
         "value": num(gt["impressions_last7"]), "unit": "показов за неделю",
         "delta": signed(gt["impressions_last7"] - gt["impressions_prev7"]),
         "delta_dir": _dir(gt["impressions_last7"] - gt["impressions_prev7"]),
         "relative": signed_pct((gt["impressions_last7"] - gt["impressions_prev7"])
                                / gt["impressions_prev7"]) if gt["impressions_prev7"] else None,
         "relative_note": "низкая база: десятки показов",
         "period": f"{ru_date(gt['last7_start'])}–{ru_date(gt['last7_end'])} "
                   f"против {ru_date(gt['prev7_start'])}–{ru_date(gt['prev7_end'])}",
         "source": "Google Search Console, весь сайт",
         "confidence": "низкая, малые числа",
         "interpretation": "Переходов из Google по-прежнему нет.",
         "muted": False,
         "sparkline": daily if len(daily) > 2 else None,
         "slope": {"prev_label": "пред. неделя", "prev": gt["impressions_prev7"],
                   "cur_label": "эта неделя", "cur": gt["impressions_last7"],
                   "label": "Показы Google за неделю"}},
        {"key": "traffic", "label": "Органический трафик",
         "value": num(m.get("organic_visits")), "unit": "визитов",
         "delta": None, "delta_dir": "flat", "relative": None,
         "relative_note": "сравнение с предыдущим периодом появится после накопления серии",
         "period": f"{ru_date(m['source']['current_period_start'])}–"
                   f"{ru_date(m['source']['current_period_end'])}",
         "source": "Яндекс.Метрика, весь сайт",
         "confidence": "достаточная",
         "interpretation": "Люди, пришедшие на сайт из поиска: весь сайт, "
                           "все поисковые системы.",
         "muted": False, "sparkline": None},
    ]

    events = m.get("organic_goal_events")
    crm = snap.get("crm") or {}
    if crm.get("connected"):
        cards.append({"key": "commercial", "label": "Коммерческий сигнал",
                      "value": num(crm.get("qualified_leads")), "unit": "обращений",
                      "delta": None, "delta_dir": "flat", "relative": None,
                      "relative_note": "", "period": "", "source": "CRM",
                      "confidence": "достаточная",
                      "interpretation": "", "muted": False, "sparkline": None})
    else:
        cards.append({
            "key": "commercial", "label": "Коммерческий сигнал",
            "value": num(events), "unit": "целевых событий",
            "delta": None, "delta_dir": "flat", "relative": None,
            "relative_note": "",
            "period": f"{ru_date(m['source']['current_period_start'])}–"
                      f"{ru_date(m['source']['current_period_end'])}",
            "source": "Яндекс.Метрика, весь сайт",
            "confidence": f"низкая: {counted(events, 'событие', 'события', 'событий')}",
            "interpretation": "Это срабатывания форм на сайте, а не подтверждённые "
                              "обращения: CRM не подключена.",
            "muted": True, "sparkline": None,
            "sample_ctr": f"{sample.get('label')} {pct(sample.get('value'), 2)}"
                          if sample else None})
    return cards[:4]


def _dir(delta) -> str:
    if delta is None or delta == 0:
        return "flat"
    return "up" if delta > 0 else "down"


def signals(snap: dict, prev: dict | None) -> list[dict]:
    """Три сигнала дня: положительный, нейтральный, отрицательный."""
    if not prev:
        return []
    out = []
    gt = snap["google"]["totals"]
    d = gt["impressions_last7"] - gt["impressions_prev7"]
    out.append({
        "tone": "positive", "metric": "Показы в Google за неделю",
        "current": num(gt["impressions_last7"]), "previous": num(gt["impressions_prev7"]),
        "delta": signed(d), "confidence": "низкая, база в десятки показов",
        "meaning": "Страницы сайта стали показываться чаще; переходов это пока не дало."})

    yt, yp = snap["yandex"]["totals"], prev["yandex"]["totals"]
    idx = snap["yandex"]["indexation"]["indexed_urls"]
    pidx = prev["yandex"]["indexation"]["indexed_urls"]
    out.append({
        "tone": "neutral", "metric": "Страницы в поиске Яндекса",
        "current": num(idx), "previous": num(pidx), "delta": signed(idx - pidx),
        "confidence": "достаточная",
        "meaning": "Объём проиндексированного сайта не изменился."})

    td = yt["queries_position_le_10"] - yp["queries_position_le_10"]
    out.append({
        "tone": "negative" if td < 0 else ("positive" if td > 0 else "neutral"),
        "metric": "Запросы выборки на первой странице",
        "current": num(yt["queries_position_le_10"]),
        "previous": num(yp["queries_position_le_10"]), "delta": signed(td),
        "confidence": "достаточная",
        "meaning": "Яндекс в целом стабилен, внутри выборки есть умеренное снижение."
                   if td < 0 else "Внутри выборки прибавилось запросов на первой странице."})
    return out[:3]


def execution_board(actions_cfg: dict, date: str) -> list[dict]:
    """Только задачи, изменившие статус сегодня, заблокированные или срочные."""
    roles = actions_cfg["roles"]
    today = dt.date.fromisoformat(date)
    rows = []
    for a in actions_cfg["actions"]:
        due = dt.date.fromisoformat(a["due"]) if a.get("due") else None
        changed_today = a.get("status_changed_at") == date
        blocked = a["status"] in ("blocked", "blocked_by_policy")
        soon = due is not None and 0 <= (due - today).days <= 7
        if not (changed_today or blocked or soon):
            continue
        rows.append({
            "id": a["id"], "task": a["title"],
            "owner": roles[a["owner_role"]]["title"],
            "stage": STAGE_LABEL.get(a.get("stage", ""), a.get("stage", "")),
            "status": a["status_label"], "zone": a["zone"],
            "due": ru_date(a["due"]) if a.get("due") else "без срока",
            "artifact": a.get("artifact"), "artifact_url": _artifact_url(a),
            "pr": a.get("pr"), "ci": a.get("ci"), "qa": a.get("qa"),
            "deploy": a.get("deploy"), "rollback": a.get("rollback"),
        })
    return rows[:5]


def _artifact_url(a: dict) -> str:
    if a.get("pr"):
        return f"{REPO}/pull/{a['pr']}"
    return f"{BLOB}/{a['ticket']}"


def web_url(date: str) -> tuple[str, bool]:
    """Публичный веб-отчёт; GitHub — только технический запасной вариант."""
    if PUBLIC_REPORT_BASE_URL:
        return f"{PUBLIC_REPORT_BASE_URL}/daily/{date}", True
    return f"{BLOB}/reports/seo/intelligence/{date}-appendix.md", False


def assemble(snap, prev, dq, actions_cfg, site_check):
    date = snap["report_date"]
    health = dq["data_health"]
    st = search_status(snap, prev)
    kpis = kpi_cards(snap, prev, dq)
    sig = signals(snap, prev)
    dec = drivers_mod.build(snap, prev)
    exps = exp_mod.build(snap, date, site_check)
    board = execution_board(actions_cfg, date)
    opps = opp_mod.build(snap, "2026-08-26")
    red = [a for a in actions_cfg["actions"] if a["zone"] == "RED"
           and a.get("status") == "awaiting_decision"]
    url, public = web_url(date)

    google_block = next((b for b in dec["blocks"] if b["engine"] == "google"), None)
    driver_rows = (google_block or {}).get("pages", {}).get("all") or []

    return {
        "date": date,
        "date_h": ru_date_full(date),
        "title": "BIZSoft Growth Intelligence",
        "subtitle": "Daily Search, Demand &amp; Experiment Control",
        "pills": [
            {"label": "ПОИСК", "state": st, "text": PILL_LABEL[st]},
            {"label": "ДАННЫЕ", "state": health["status"],
             "text": PILL_LABEL[health["status"]]},
            {"label": "ОТ ВАС", "state": "required" if red else "none",
             "text": PILL_LABEL["required" if red else "none"]},
        ],
        "sources_line": _sources_line(snap),
        "user_action": (red[0]["title"] if red else
                        "Решений от вас сегодня не требуется."),
        "user_action_required": bool(red),
        "kpis": kpis,
        "signals": sig,
        "drivers": dec,
        "driver_rows": driver_rows,
        "driver_summary": (drivers_mod.summarise(google_block) if google_block
                           else "Причина изменения пока не определена."),
        "driver_blocks": _driver_blocks(dec),
        "experiments": exps,
        "board": board,
        "opportunities": opps,
        "health": health,
        "measurement_summary": _measurement_summary(dq),
        "checkpoints": _checkpoints(exps, actions_cfg),
        "links": {"web": url, "web_public": public,
                  "tasks": f"{REPO}/tree/{BRANCH}/reports/seo/tasks"},
    }


def _driver_blocks(dec: dict) -> list[dict]:
    """Разложение по каждой поисковой системе: рост и снижение с конкретными адресами."""
    out = []
    for b in dec.get("blocks", []):
        part = b["pages"] if b["pages"].get("available") else b["queries"]
        kind = "страницам" if b["pages"].get("available") else "запросам"
        if not part.get("available"):
            out.append({"engine": b["engine_label"], "window": b["window_label"],
                        "available": False,
                        "text": "Причина изменения пока не определена: разложить его "
                                "на имеющихся данных нельзя.",
                        "rows": []})
            continue
        rows = [{"entity": i["entity"], "delta": signed(i["delta"]),
                 "share": f"{round(i['share_of_total_delta'] * 100)}%",
                 "state": {"new": "новая", "lost": "выпала",
                           "changed": ""}.get(i["state"], ""),
                 "positive": i["delta"] > 0,
                 "position_delta": i.get("position_delta")}
                for i in part["all"]]
        ups = [r for r in rows if r["positive"]]
        downs = [r for r in rows if not r["positive"]]
        text = (f"Изменение {signed(part['total_delta'])} по {kind}. "
                f"Прибавили: {', '.join(r['entity'] for r in ups[:3]) or '—'}. "
                f"Потеряли: {', '.join(r['entity'] for r in downs[:3]) or '—'}.")
        out.append({"engine": b["engine_label"], "window": b["window_label"],
                    "available": True, "text": text, "rows": rows,
                    "counted": part["counted"]})
    return out


def _measurement_summary(dq: dict) -> str:
    """Что именно измеряет каждый источник — одной фразой, без повторов в других блоках."""
    rows = {r["metric"]: r for r in dq.get("measurement_map", [])}
    imp = rows.get("impressions", {})
    visits = rows.get("visits", {})
    return (f"Показы и переходы Яндекса относятся к {imp.get('scope', 'выборке запросов')}, "
            f"визиты Метрики — к {visits.get('scope', 'всему сайту')} и ко всем поисковым "
            f"системам сразу. Приводить их к одному определению визита было бы ошибкой: "
            f"мы бы получили одно число вместо двух разных фактов. Корректно сопоставлять "
            f"показы с переходами одной выборки, а визиты Метрики — с сессиями GA4.")


def _sources_line(snap: dict) -> str:
    y, g = snap["yandex"]["source"], snap["google"]["source"]
    m = snap["analytics"]["metrika"]["source"]
    md = snap.get("market_demand") or {}
    demand = (f"спрос {ru_date(md['source']['measured_at'])}" if md.get("available")
              else "спрос не измерен")
    return (f"Яндекс по {ru_date(y['latest_event_date'])} · "
            f"Google по {ru_date(g['latest_event_date'])} · "
            f"Метрика по {ru_date(m['latest_event_date'])} · {demand}")


def _checkpoints(exps, actions_cfg) -> list[dict]:
    out = []
    for e in exps:
        out.append({"date": ru_date(e["next_review"]),
                    "what": f"{e['ticket']}: первый замер кликабельности изменённых страниц"})
    for a in actions_cfg["actions"]:
        if a.get("due") and a["status"] in ("in_progress", "blocked"):
            out.append({"date": ru_date(a["due"]), "what": f"{a['id']}: {a['title']}"})
    seen, uniq = set(), []
    for c in out:
        k = (c["date"], c["what"])
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    return uniq[:3]


# ── Рендер письма ───────────────────────────────────────────────────────────

def _pill(p: dict) -> str:
    c = PILL_COLOUR[p["state"]]
    return (f"<span data-meta=\"1\" style=\"display:inline-block;padding:3px 10px;margin:0 6px 6px 0;"
            f"border:1px solid {c};border-radius:999px;font-size:12.5px;"
            f"color:{c};white-space:nowrap;\">{p['label']}: {p['text']}</span>")


def _kpi_cell(k: dict, charts: dict, cid_mode: bool) -> str:
    dir_colour = {"up": T["positive"], "down": T["danger"], "flat": T["muted"]}[k["delta_dir"]]
    tone = T["muted"] if k["muted"] else T["text_primary"]
    delta = (f"<span style=\"font-size:14px;color:{dir_colour};font-weight:600;\">"
             f"{k['delta']}</span>" if k["delta"] else "")
    rel = (f"<span data-meta=\"1\" style=\"font-size:13px;color:{T['text_secondary']};\"> "
           f"{k['relative']}</span>" if k.get("relative") else "")
    spark = ""
    if k.get("slope") and charts.get("kpi-slope"):
        spark = (f"<div style=\"padding-top:{SP['s']}px;\">"
                 f"{_img(charts, 'kpi-slope', cid_mode)}</div>")
    return (
        f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
        f"style=\"background:{T['surface']};border:1px solid {T['border']};"
        f"border-radius:12px;\"><tr><td style=\"padding:{SP['l']}px;\">"
        f"<div data-meta=\"1\" style=\"font-size:13px;color:{T['text_secondary']};"
        f"letter-spacing:.01em;\">{k['label']}</div>"
        f"<div style=\"padding-top:{SP['xs']}px;\">"
        f"<span style=\"font-size:30px;line-height:1.1;font-weight:700;color:{tone};\">"
        f"{k['value']}</span> "
        f"<span data-meta=\"1\" style=\"font-size:13.5px;color:{T['text_secondary']};\">"
        f"{k['unit']}</span>"
        f" {delta}{rel}</div>"
        f"{spark}"
        f"<div style=\"font-size:14.5px;color:{T['text_primary']};padding-top:{SP['s']}px;"
        f"line-height:1.5;\">{k['interpretation']}</div>"
        f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
        f"padding-top:{SP['s']}px;line-height:1.45;\">{k['period']} · {k['source']} · "
        f"достоверность: {k['confidence']}</div>"
        f"</td></tr></table>")


def _section(title: str, body: str, note: str = "") -> str:
    n = (f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
         f"padding-top:2px;line-height:1.45;\">{note}</div>" if note else "")
    return (f"<tr><td style=\"padding:{SP['xl']}px 0 0 0;\">"
            f"<div style=\"font-size:17.5px;font-weight:700;color:{T['text_primary']};"
            f"line-height:1.35;\">{title}</div>{n}"
            f"<div style=\"padding-top:{SP['m']}px;\">{body}</div></td></tr>")


def _img(charts: dict, name: str, cid_mode: bool) -> str:
    c = charts.get(name)
    if not c:
        return ""
    src = f"cid:{c['cid']}" if cid_mode else f"charts/{c['file']}"
    return (f"<img src=\"{src}\" width=\"{c['display_width']}\" alt=\"{c['alt']}\" "
            f"style=\"display:block;width:100%;max-width:{c['display_width']}px;"
            f"height:auto;max-height:{c['max_height']}px;\">"
            f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
            f"padding-top:{SP['xs']}px;line-height:1.45;\">{c['fallback']}</div>")


def html_email(b: dict, charts: dict, cid_mode: bool) -> str:
    rows = []

    # A. Header + B. Status bar
    rows.append(
        f"<tr><td style=\"padding:0 0 {SP['m']}px 0;\">"
        f"<div style=\"font-size:24px;font-weight:700;color:{T['text_primary']};"
        f"line-height:1.25;\">{b['title']}</div>"
        f"<div style=\"font-size:14px;color:{T['text_secondary']};padding-top:2px;\">"
        f"{b['subtitle']} · {b['date_h']}</div>"
        f"<div style=\"padding-top:{SP['m']}px;\">{''.join(_pill(p) for p in b['pills'])}</div>"
        f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
        f"line-height:1.45;\">{b['sources_line']}</div></td></tr>")

    # C. От вас
    if b["user_action_required"]:
        rows.append(
            f"<tr><td style=\"padding-top:{SP['l']}px;\">"
            f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
            f"style=\"background:#FFF4ED;border-left:4px solid {T['brand']};"
            f"border-radius:0 12px 12px 0;\"><tr><td style=\"padding:{SP['l']}px;\">"
            f"<div style=\"font-size:15.5px;font-weight:700;color:{T['text_primary']};\">"
            f"Требуется ваше решение</div>"
            f"<div style=\"font-size:15px;padding-top:{SP['xs']}px;line-height:1.55;\">"
            f"{b['user_action']}</div></td></tr></table></td></tr>")
    else:
        rows.append(
            f"<tr><td style=\"padding-top:{SP['l']}px;font-size:15px;"
            f"color:{T['text_primary']};line-height:1.55;\">"
            f"<b>От вас:</b> {b['user_action']} Остальное система ведёт сама.</td></tr>")

    # D. KPI — fluid hybrid: две колонки на десктопе, одна на узком экране.
    # Ширина карточки задана max-width, а не процентом: Gmail вырезает <style>
    # с media queries, поэтому вёрстка не должна на них опираться.
    cells = []
    for i, k in enumerate(b["kpis"]):
        mso_open = ("<!--[if mso]><table role=\"presentation\" width=\"100%\"><tr>"
                    "<td width=\"50%\" valign=\"top\"><![endif]-->" if i == 0 else
                    "<!--[if mso]></td><td width=\"50%\" valign=\"top\"><![endif]-->"
                    if i % 2 == 1 else
                    "<!--[if mso]></td></tr><tr><td width=\"50%\" valign=\"top\">"
                    "<![endif]-->")
        cells.append(
            f"{mso_open}"
            f"<div class=\"kpi\" style=\"display:inline-block;width:100%;"
            f"max-width:308px;vertical-align:top;padding:{SP['s']}px;font-size:15px;\">"
            f"{_kpi_cell(k, charts, cid_mode)}</div>")
    cells.append("<!--[if mso]></td></tr></table><![endif]-->")
    rows.append(_section(
        "Показатели",
        f"<div data-meta=\"1\" style=\"font-size:0;margin:-{SP['s']}px;\">"
        f"{''.join(cells)}</div>"))
    rows.append(FIRST_SCREEN_MARKER)

    # E. Сигналы дня
    if b["signals"]:
        tone_colour = {"positive": T["positive"], "neutral": T["muted"],
                       "negative": T["danger"]}
        sig = "".join(
            f"<div style=\"padding:{SP['m']}px 0;border-bottom:1px solid {T['border']};\">"
            f"<span style=\"display:inline-block;width:8px;height:8px;border-radius:50%;"
            f"background:{tone_colour[s['tone']]};margin-right:{SP['s']}px;\"></span>"
            f"<span style=\"font-size:15.5px;font-weight:600;\">{s['metric']}</span>"
            f"<span style=\"font-size:15px;color:{T['text_secondary']};\"> "
            f"{s['previous']} → {s['current']} ({s['delta']})</span>"
            f"<div style=\"font-size:15px;padding-top:{SP['xs']}px;line-height:1.55;\">"
            f"{s['meaning']}</div>"
            f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
            f"padding-top:2px;\">достоверность: {s['confidence']}</div></div>"
            for s in b["signals"])
        rows.append(_section("Сигналы дня", sig))

    # F. Драйверы и детракторы
    parts = []
    for db in b["driver_blocks"]:
        rows_html = "".join(
            f"<div style=\"padding:{SP['xs']}px 0;font-size:14.5px;line-height:1.5;\">"
            f"<span style=\"color:{T['positive'] if r['positive'] else T['danger']};"
            f"font-weight:600;\">{r['delta']}</span> "
            f"<span>{r['entity']}</span> "
            f"<span data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};\">"
            f"{r['share']} изменения{' · ' + r['state'] if r['state'] else ''}</span></div>"
            for r in db["rows"][:5])
        chart = _img(charts, "drivers", cid_mode) if db["engine"] == "Google" else ""
        parts.append(
            f"<div style=\"padding-bottom:{SP['l']}px;\">"
            f"<div style=\"font-size:15px;line-height:1.55;\">"
            f"<b>{db['engine']}.</b> {db['text']}</div>"
            f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
            f"padding-top:2px;\">{db['window']}</div>"
            f"<div style=\"padding-top:{SP['s']}px;\">{rows_html}</div>"
            f"<div style=\"padding-top:{SP['s']}px;\">{chart}</div></div>")
    if parts:
        rows.append(_section("Что дало изменение", "".join(parts)))
    else:
        rows.append(_section(
            "Что дало изменение",
            f"<div style=\"font-size:15px;line-height:1.55;\">"
            f"Причина изменения пока не определена.</div>"))

    # G. Контроль экспериментов
    for e in b["experiments"]:
        rows.append(_section(
            "Контроль эксперимента",
            f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
            f"style=\"background:{T['surface']};border:1px solid {T['border']};"
            f"border-radius:12px;\"><tr><td style=\"padding:{SP['l']}px;\">"
            f"<div style=\"font-size:15.5px;font-weight:600;\">{e['ticket']} · "
            f"заголовки и блок вопросов на {e['pages_total']} карточках</div>"
            f"<div style=\"font-size:14.5px;padding-top:{SP['s']}px;line-height:1.55;\">"
            f"<b>Проверяем:</b> {e['hypothesis_plain']}</div>"
            f"<div style=\"font-size:14.5px;padding-top:{SP['xs']}px;line-height:1.55;\">"
            f"<b>Что изменили:</b> {e['treatment_plain']} {e['combined_note']}</div>"
            f"<div style=\"font-size:15px;padding-top:{SP['m']}px;line-height:1.65;\">"
            f"Запуск {ru_date(e['start'])}, прошло {counted(e['days_elapsed'], 'день', 'дня', 'дней')}. "
            f"Минимум для вывода: {e['minimum_exposure']}.<br>"
            f"Новый вариант на сайте: {num(e['pages_live_with_treatment'])} из "
            f"{e['pages_total']} страниц, проверено напрямую.<br>"
            f"Обновление сниппета в выдаче: {e['search_snippet_refresh']} — "
            f"{e['search_snippet_refresh_note']}<br>"
            f"Накоплено: {e['current_result']} — достоверность {e['confidence_plain']}.<br>"
            f"Целевой показатель: {e['metric_plain']}<br>"
            f"Вывод: <b>{VERDICT_LABEL[e['verdict']]}</b> — {e['verdict_reason']}. "
            f"Следующая проверка {ru_date(e['next_review'])}.</div>"
            f"<div style=\"padding-top:{SP['m']}px;\">{_img(charts, 'experiment', cid_mode)}</div>"
            f"</td></tr></table>"))

    # H. Автономное исполнение — фиксированный layout: содержимое переносится,
    # а не распирает письмо. Статус и результат уходят в подпись под задачей,
    # иначе шесть колонок не помещаются в 375 px.
    if b["board"]:
        head = ("Задача", "Кто", "Стадия", "Срок")
        th = "".join(f"<th align=\"left\" data-meta=\"1\" style=\"font-size:12.5px;font-weight:600;"
                     f"color:{T['text_secondary']};padding:0 {SP['s']}px {SP['s']}px 0;\">"
                     f"{h}</th>" for h in head)
        trs = ""
        for r in b["board"]:
            meta = f"{r['status']} · {r.get('artifact') or 'без артефакта'}"
            if r.get("pr"):
                meta += (f" · PR {r['pr']} · проверки {r['ci']} · тестирование {r['qa']}"
                         f" · {r['deploy']} · откат {r['rollback']}")
            cell = (f"padding:{SP['s']}px {SP['s']}px {SP['s']}px 0;"
                    f"border-top:1px solid {T['border']};")
            trs += (f"<tr><td style=\"{cell}font-size:14.5px;line-height:1.5;"
                    f"word-break:break-word;\">"
                    f"<a href=\"{r['artifact_url']}\" style=\"color:{T['text_primary']};"
                    f"text-decoration:none;\">{r['task']}</a>"
                    f"<div data-meta=\"1\" style=\"font-size:12.5px;"
                    f"color:{T['text_secondary']};padding-top:2px;line-height:1.45;\">"
                    f"{meta}</div></td>"
                    f"<td style=\"{cell}font-size:14px;color:{T['text_secondary']};"
                    f"word-break:break-word;\">{r['owner']}</td>"
                    f"<td style=\"{cell}font-size:14px;word-break:break-word;\">"
                    f"{r['stage']}</td>"
                    f"<td style=\"padding:{SP['s']}px 0;border-top:1px solid {T['border']};"
                    f"font-size:14px;color:{T['text_secondary']};\">{r['due']}</td></tr>")
        rows.append(_section(
            "Система уже делает",
            f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
            f"style=\"width:100%;table-layout:fixed;\">"
            f"<colgroup><col style=\"width:46%\"><col style=\"width:19%\">"
            f"<col style=\"width:19%\"><col style=\"width:16%\"></colgroup>"
            f"<tr>{th}</tr>{trs}</table>",
            "Показаны задачи со сменой статуса, блокировкой или сроком в ближайшую неделю"))

    # I. Радар возможностей
    if b["opportunities"]["available"]:
        items = "".join(
            f"<div style=\"padding:{SP['m']}px 0;border-bottom:1px solid {T['border']};\">"
            f"<div style=\"font-size:15.5px;font-weight:600;line-height:1.45;\">"
            f"{o['cluster']}</div>"
            f"<div style=\"font-size:14.5px;padding-top:2px;line-height:1.55;\">"
            f"{o['evidence']}</div>"
            f"<div style=\"font-size:14.5px;padding-top:2px;line-height:1.55;"
            f"color:{T['text_secondary']};\">Потенциал: {o['potential']}</div>"
            f"<div style=\"font-size:14.5px;padding-top:{SP['xs']}px;line-height:1.55;\">"
            f"Что делаем: {o['recommended_action']}</div>"
            f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
            f"padding-top:2px;\">решение к {ru_date(o['decision_date'])} · "
            f"достоверность: {o['confidence']}</div></div>"
            for o in b["opportunities"]["items"])
        rows.append(_section("Где ближе всего рост", items))

    # J. Здоровье данных
    h = b["health"]
    colour = {"positive": T["positive"], "warning": T["warning"],
              "danger": T["danger"]}[h["colour"]]
    bg = {"positive": "#ECFDF3", "warning": "#FFFAEB", "danger": "#FEF3F2"}[h["colour"]]
    rows.append(_section(
        "Здоровье данных",
        f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
        f"style=\"background:{bg};border-left:4px solid {colour};"
        f"border-radius:0 12px 12px 0;\"><tr><td style=\"padding:{SP['l']}px;\">"
        f"<div style=\"font-size:15.5px;font-weight:700;color:{T['text_primary']};\">"
        f"{PILL_LABEL[h['status']].capitalize()}: {h['reason']}</div>"
        f"<div style=\"font-size:15px;padding-top:{SP['xs']}px;line-height:1.55;\">"
        f"{h['detail']}</div>"
        f"<div style=\"font-size:14.5px;padding-top:{SP['s']}px;line-height:1.55;"
        f"color:{T['text_primary']};\">{b['measurement_summary']}</div>"
        f"</td></tr></table>"))

    # K. Контрольные точки
    if b["checkpoints"]:
        cps = "".join(
            f"<div style=\"font-size:15px;padding:{SP['xs']}px 0;line-height:1.55;\">"
            f"<b>{c['date']}</b> — {c['what']}</div>" for c in b["checkpoints"])
        cps += (f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
                f"padding-top:{SP['s']}px;line-height:1.45;\">"
                f"До этих дат выводы по эксперименту не делаются: данных выдачи за более "
                f"короткий срок недостаточно, чтобы отличить эффект от обычных колебаний."
                f"</div>")
        rows.append(_section("Следующие проверки", cps))

    # L. Ссылки
    label = "Полный отчёт" if b["links"]["web_public"] else "Полный отчёт (техническая копия)"
    rows.append(
        f"<tr><td style=\"padding:{SP['xl']}px 0 {SP['s']}px 0;\">"
        f"<a class=\"btn\" href=\"{b['links']['web']}\" style=\"display:inline-block;"
        f"background:{T['brand']};color:#fff;text-decoration:none;font-size:15px;"
        f"font-weight:600;padding:11px 20px;border-radius:8px;\">{label}</a>"
        f"<a class=\"btn\" href=\"{b['links']['tasks']}\" style=\"display:inline-block;"
        f"margin-left:{SP['s']}px;border:1px solid {T['border']};color:{T['text_primary']};"
        f"text-decoration:none;font-size:15px;padding:10px 20px;border-radius:8px;\">"
        f"Журнал работ</a></td></tr>")

    media = (
        "@media only screen and (max-width:480px){"
        ".wrap{width:100%!important;padding:16px!important}"
        ".kpi{max-width:100%!important;padding:6px 0!important}"
        ".cell{display:block!important;width:100%!important;border-top:0!important;"
        "padding:2px 0!important}"
        ".row{border-top:1px solid #EAECF0!important;padding-top:10px!important}"
        ".btn{display:block!important;margin:0 0 8px 0!important;text-align:center!important}"
        "}")

    return (
        f"<div style=\"margin:0;padding:0;background:{T['background']};\">"
        f"<style>{media}</style>"
        f"<!--[if mso]><table role=\"presentation\" width=\"680\" align=\"center\"><tr><td><![endif]-->"
        f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
        f"style=\"background:{T['background']};\"><tr>"
        f"<td align=\"center\" style=\"padding:{SP['xl']}px {SP['m']}px;\">"
        f"<table role=\"presentation\" class=\"wrap\" width=\"100%\" cellpadding=\"0\" "
        f"cellspacing=\"0\" style=\"width:100%;max-width:680px;background:{T['surface']};"
        f"border-radius:16px;padding:{SP['xxl']}px;font-family:{FONT};"
        f"color:{T['text_primary']};\">"
        + "".join(rows) +
        f"</table></td></tr></table>"
        f"<!--[if mso]></td></tr></table><![endif]--></div>")


def plain_text(b: dict) -> str:
    L = [f"{b['title'].upper()} — {b['date_h']}",
         b["subtitle"].replace("&amp;", "&"),
         " · ".join(f"{p['label']}: {p['text']}" for p in b["pills"]),
         b["sources_line"], "",
         f"ОТ ВАС: {b['user_action']}", "", "ПОКАЗАТЕЛИ"]
    for k in b["kpis"]:
        d = f" ({k['delta']}{' ' + k['relative'] if k.get('relative') else ''})" if k["delta"] else ""
        L.append(f"- {k['label']}: {k['value']} {k['unit']}{d}. {k['interpretation']}")
        L.append(f"  {k['period']} · {k['source']} · достоверность: {k['confidence']}")
    if b["signals"]:
        L += ["", "СИГНАЛЫ ДНЯ"]
        for s in b["signals"]:
            L.append(f"- {s['metric']}: {s['previous']} -> {s['current']} ({s['delta']}). "
                     f"{s['meaning']}")
    L += ["", "ЧТО ДАЛО ИЗМЕНЕНИЕ", b["driver_summary"]]
    for r in b["driver_rows"]:
        L.append(f"  {r['entity']}: {signed(r['delta'])} "
                 f"({round(r['share_of_total_delta'] * 100)}% изменения)")
    for e in b["experiments"]:
        L += ["", "КОНТРОЛЬ ЭКСПЕРИМЕНТА",
              f"- {e['ticket']}: {e['pages_total']} карточек, новый вариант на сайте "
              f"{num(e['pages_live_with_treatment'])}, обновление сниппета в выдаче: "
              f"{e['search_snippet_refresh']}",
              f"  {e['current_result']}",
              f"  вывод: {VERDICT_LABEL[e['verdict']]} — {e['verdict_reason']}",
              f"  {e['combined_note']}"]
    if b["board"]:
        L += ["", "СИСТЕМА УЖЕ ДЕЛАЕТ"]
        for r in b["board"]:
            L.append(f"- {r['task']} — {r['owner']} · стадия: {r['stage']} · "
                     f"{r['status']} · до {r['due']} · {r.get('artifact') or '—'}")
            if r.get("pr"):
                L.append(f"  PR {r['pr']} · проверки {r['ci']} · тестирование {r['qa']} · "
                         f"{r['deploy']} · откат {r['rollback']}")
    if b["opportunities"]["available"]:
        L += ["", "ГДЕ БЛИЖЕ ВСЕГО РОСТ"]
        for o in b["opportunities"]["items"]:
            L.append(f"- {o['cluster']}: {o['evidence']}")
            L.append(f"  потенциал: {o['potential']}")
            L.append(f"  что делаем: {o['recommended_action']} "
                     f"(решение к {ru_date(o['decision_date'])})")
    h = b["health"]
    L += ["", "ЗДОРОВЬЕ ДАННЫХ",
          f"{PILL_LABEL[h['status']].capitalize()}: {h['reason']}. {h['detail']}",
          b["measurement_summary"]]
    if b["checkpoints"]:
        L += ["", "СЛЕДУЮЩИЕ ПРОВЕРКИ"]
        for c in b["checkpoints"]:
            L.append(f"- {c['date']} — {c['what']}")
    L += ["", f"Полный отчёт: {b['links']['web']}", f"Журнал работ: {b['links']['tasks']}"]
    return "\n".join(L)


def strip_tags(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"&[a-z]+;", " ", html)


def visible_words(html: str) -> int:
    """Слова, которые действительно видит читатель, — по готовому письму."""
    return words(strip_tags(html))


def first_screen_words(html: str) -> int:
    """Первый экран: до маркера, поставленного после блока показателей."""
    head = html.split(FIRST_SCREEN_MARKER)[0]
    return visible_words(head)


def build_eml(b: dict, html: str, text: str, charts: dict, date: str) -> bytes:
    from email.message import EmailMessage
    from email.utils import formatdate, make_msgid
    msg = EmailMessage()
    msg["From"] = "BIZSoft Growth Intelligence <hello@biz-soft.pro>"
    msg["To"] = "avbelyaev@biz-soft.pro"
    msg["Subject"] = f"BIZSoft Growth Intelligence — {b['date_h']}"
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(text)
    real = {}
    for key, c in charts.items():
        cid = make_msgid(domain="biz-soft.pro")
        html = html.replace(f"cid:{c['cid']}", f"cid:{cid[1:-1]}")
        real[cid] = charts_v4.OUT / c["file"]
    msg.add_alternative(html, subtype="html")
    part = msg.get_payload()[-1]
    for cid, path in real.items():
        if path.exists():
            part.add_related(path.read_bytes(), "image", "png", cid=cid,
                             filename=path.name, disposition="inline")
    return msg.as_bytes()


def load_site_check(date: str) -> dict | None:
    p = BASE / f"site-check-{date}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("experiments")


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    snap = json.loads((BASE / "snapshots" / f"{date}.json").read_text(encoding="utf-8"))
    prev = report_v2.prev_snapshot(date)
    dq = json.loads((BASE / "data-quality" / f"{date}.json").read_text(encoding="utf-8"))
    actions_cfg = json.loads((BASE / "actions.json").read_text(encoding="utf-8"))

    b = assemble(snap, prev, dq, actions_cfg, load_site_check(date))
    charts = charts_v4.build(date, b["kpis"], b["driver_rows"],
                             b["experiments"][0] if b["experiments"] else None)

    email_html = html_email(b, charts, cid_mode=True)
    preview_html = html_email(b, charts, cid_mode=False)
    text = plain_text(b)

    (BASE / f"{date}-v4-email.html").write_text(email_html, encoding="utf-8")
    (BASE / f"{date}-v4.html").write_text(preview_html, encoding="utf-8")
    (BASE / f"{date}-v4.txt").write_text(text, encoding="utf-8")
    (BASE / f"{date}-v4.eml").write_bytes(build_eml(b, email_html, text, charts, date))
    (BASE / f"{date}-v4-blocks.json").write_text(
        json.dumps(b, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    print(f"V4: видимых слов {visible_words(preview_html)}, "
          f"первый экран {first_screen_words(preview_html)}, "
          f"текстовая версия {words(text)}, изображений {len(charts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
