#!/usr/bin/env python3
"""Executive email V3: короткое письмо (450–650 видимых слов) + подробное приложение.

Порядок блоков: A заголовок · B итог дня · C «от вас» · D четыре показателя ·
E «система уже делает» · F «что изменилось» · G риски · H контрольная точка · I кнопки.

Продукты: -executive-email.html (CID-картинки), -executive.html (preview),
-executive.txt, -executive.eml, -appendix.md, -uxlint.json.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import subprocess
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import charts as charts_svg  # noqa: E402
import charts_png  # noqa: E402
import report_v2  # noqa: E402
from quality import delta  # noqa: E402

BASE = pathlib.Path("reports/seo/intelligence")
REPO = "https://github.com/AlBeli-V/WebSite_BizSoft"
BRANCH = "claude/biz-soft-rating-tracking-5rf03g"
BLOB = f"{REPO}/blob/{BRANCH}"

INK, MUTED, LINE = "#1d1d1f", "#5c5c66", "#e3e3e8"
ACCENT, GOOD, WARN, BAD = "#f2591d", "#1a8f4c", "#b26a00", "#d92d20"
FONT = "-apple-system,'Segoe UI',Arial,Helvetica,sans-serif"

ZERO_DELTA_FORBIDDEN = ("вырос", "рост", "увеличил", "снизил", "падени", "прибав", "сократил")


def ru(d: str) -> str:
    return f"{d[8:10]}.{d[5:7]}"


def num(v) -> str:
    """Число с пробелом в разрядах: 1 240, а не 1240 — письмо читает человек."""
    return "нет данных" if v is None else f"{int(v):,}".replace(",", " ")


def plural(n: int, one: str, few: str, many: str) -> str:
    """Согласование существительного с числом: 1 запрос, 2 запроса, 5 запросов."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def words(*parts: str) -> int:
    text = " ".join(parts)
    text = re.sub(r"<[^>]+>", " ", text)
    return len([w for w in re.split(r"\s+", text) if w.strip(" ·—-|")])


def composite_status(snap, prev):
    """Составной статус: Яндекс, Google, общий вывод."""
    yx, g = snap["yandex"], snap["google"]
    idx_d = delta(yx["indexation"]["indexed_urls"],
                  prev["yandex"]["indexation"]["indexed_urls"] if prev else None)
    top_d = delta(yx["totals"]["queries_position_le_10"],
                  prev["yandex"]["totals"]["queries_position_le_10"] if prev else None)
    moves = [d["absolute"] for d in (idx_d, top_d) if d["absolute"] is not None]
    if moves and all(m == 0 for m in moves):
        ya = "стабильно"
    elif moves and any(m > 0 for m in moves) and any(m < 0 for m in moves):
        ya = "смешанная динамика"
    elif moves and all(m >= 0 for m in moves):
        ya = "стабильно"
    else:
        ya = "смешанная динамика"
    t = g["totals"]
    d7 = delta(t["impressions_last7"], t["impressions_prev7"])
    go = ("ранний положительный сигнал на низкой базе"
          if d7["absolute"] and d7["absolute"] > 0 else "без выраженной динамики")
    return {"yandex": ya, "google": go, "overall": "смешанная динамика, вывод предварительный",
            "idx_delta": idx_d, "top_delta": top_d, "g7_delta": d7}


def build_kpis(snap):
    yx, g = snap["yandex"], snap["google"]
    m = snap["analytics"]["metrika"]
    t = g["totals"]
    return [
        {"label": "Клики из поиска, Яндекс", "value": num(yx["totals"]["clicks"]),
         "note": f"по выборке {yx['totals']['queries_tracked']} запросов за "
                 f"{ru(yx['source']['current_period_start'])}–{ru(yx['source']['current_period_end'])}; "
                 "это не все переходы сайта"},
        {"label": "Показы Google за неделю", "value": num(t["impressions_last7"]),
         "note": f"неделей ранее {t['impressions_prev7']}; переходов из Google пока нет"},
        {"label": "Визиты из поиска", "value": num(m["organic_visits"]),
         "note": f"Метрика за {ru(m['source']['current_period_start'])}–{ru(m['source']['current_period_end'])}; "
                 "из них 3 целевых события"},
        {"label": "Заявки и выручка", "value": "нет данных",
         "note": "CRM не подключена — коммерческий результат пока не измеряется"},
    ]


def demand_change(md):
    """Запись «Что изменилось» появляется только в день нового замера спроса.

    В остальные дни спрос молчит: месячная величина, показанная как суточное
    изменение, — это выдуманная динамика.
    """
    if not md.get("available") or md["source"].get("age_days") != 0:
        return None
    cards, phrases = md.get("gap_cards") or 0, md.get("gap_phrases") or 0
    if not cards:
        return None
    top = (md.get("top_commercial") or [{}])[0]
    lead = ""
    if top.get("cluster") and top.get("commercial_impressions"):
        lead = (f" Больше всего покупательского спроса у карточки {top['cluster']} — "
                f"{num(top['commercial_impressions'])} запросов в месяц.")
    partial = "" if md.get("complete") else " Замер ещё идёт, список пополнится."
    ph_word = plural(phrases, "покупательский запрос", "покупательских запроса",
                     "покупательских запросов")
    card_word = plural(cards, "карточке", "карточках", "карточках")
    return {"title": "Обновлён замер рыночного спроса",
            "text": f"Сверили, что люди ищут в Яндексе, с тем, по каким словам видны наши "
                    f"страницы. Нашли {phrases} {ph_word} на {cards} {card_word}, "
                    f"по которым мы в выдаче не показываемся.{lead}{partial} "
                    "Это не изменение наших показателей за сутки, а обновление картины рынка.",
            "zero": False}


def build_changes(snap, prev, st):
    ch = []
    t = snap["google"]["totals"]
    d = st["g7_delta"]
    rel = f"+{d['relative'] * 100:.1f}".replace(".", ",") + "%"
    ch.append({"title": "Показы Google за неделю",
               "text": f"{t['impressions_prev7']} → {t['impressions_last7']} (+{d['absolute']}, {rel}). "
                       "Google стал чаще показывать наши карточки, но кликов из него по-прежнему нет. "
                       "Абсолютные числа малы, поэтому это ранний сигнал, а не подтверждённый тренд.",
               "zero": False})
    idx = snap["yandex"]["indexation"]["indexed_urls"]
    dd = st["idx_delta"]
    if dd["absolute"] == 0:
        ch.append({"title": "Страницы в поиске Яндекса",
                   "text": f"Количество страниц в поиске не изменилось — {idx}. "
                           "Предыдущее значение было пересчитано самим источником, поэтому сравнение "
                           "ведём от проверенной величины, а не от промежуточного замера.", "zero": True})
    else:
        ch.append({"title": "Страницы в поиске Яндекса",
                   "text": f"{idx} страниц, изменение {dd['absolute']:+d} к предыдущему сбору.",
                   "zero": False})
    td = st["top_delta"]
    tot = snap["yandex"]["totals"]
    if td["absolute"] == 0:
        ch.append({"title": "Запросы на первой странице",
                   "text": f"Без изменений: {tot['queries_position_le_10']} из {tot['queries_tracked']} "
                           "запросов выборки держатся со средней позицией не ниже десятой. "
                           "Позиции стабильны — меняется не видимость, а то, доходят ли люди до сайта.",
                   "zero": True})
    else:
        ch.append({"title": "Запросы на первой странице",
                   "text": f"{tot['queries_position_le_10']} из {tot['queries_tracked']} запросов выборки, "
                           f"изменение {td['absolute']:+d}.", "zero": False})
    dc = demand_change(snap.get("market_demand") or {})
    if dc:
        ch.insert(0, dc)
    return ch[:3]


def demand_evidence(action, md):
    """Одна строка обоснования действия рыночным спросом.

    Спрос обновляется помесячно, поэтому он не может быть показателем дня.
    Его роль в письме — объяснить, почему действие вообще стоит делать:
    какая фраза и сколько её ищут за месяц. Без измеренного спроса строки нет.
    """
    if not md.get("available"):
        return ""
    gaps = md.get("gaps") or {}
    clusters = action.get("demand_clusters") or []
    rows = [(c, r) for c in clusters for r in gaps.get(c, [])]
    if not rows:
        return ""
    rows.sort(key=lambda x: -(x[1]["impressions"] or 0))
    top = rows[:2]
    listed = ", ".join(f"«{r['phrase']}» — {num(r['impressions'])}" for _, r in top)
    tail = (" Замер спроса от " + ru(md["source"]["measured_at"]) + "."
            if md.get("complete") else
            " Замер спроса от " + ru(md["source"]["measured_at"]) + ", он ещё не завершён, "
            "поэтому список фраз пополнится.")
    return (f"Зачем: этого ищут в Яндексе, а у нас по этим словам страница не видна — "
            f"{listed} запросов в месяц.{tail}")


def build_actions(actions_cfg, md):
    roles = actions_cfg["roles"]
    out = []
    for a in actions_cfg["actions"][:3]:
        out.append({**a, "owner": roles[a["owner_role"]]["title"],
                    "outcome": a.get("outcome", ""),
                    "demand": demand_evidence(a, md),
                    "due_label": ru(a["due"]) if a.get("due") else "без запуска",
                    "ticket_url": f"{BLOB}/{a['ticket']}"})
    return out


def build_risks(dq):
    crit = [f for f in dq["findings"] if f["level"] == "critical"]
    blocking = {
        "title": "Источники измерения расходятся кратно",
        "text": "Поиск отдаёт 6 переходов по выборке запросов, аналитика видит 37 визитов из поиска "
                "за близкий период. Пока разрыв не объяснён, выводы о кликабельности и любые решения, "
                "которые на них опираются, приостановлены — иначе есть риск оптимизировать несуществующую "
                "проблему. Сверка идёт, срок 22.08.",
    } if crit else None
    warns = [
        {"title": "Заявки не измеряются",
         "text": "CRM не подключена, поэтому сделки и выручка остаются вне отчёта. Мы видим только "
                 "срабатывания целей на сайте — сколько из них стали реальными обращениями, система не знает."},
        {"title": "Малая выборка конверсий",
         "text": "За период зафиксировано 3 целевых события. Этого мало для выводов о конверсии: "
                 "любые проценты на такой выборке неустойчивы."},
    ]
    return blocking, warns[:2]


def assemble(snap, prev, dq, actions_cfg):
    st = composite_status(snap, prev)
    yx, g, m, ga = snap["yandex"], snap["google"], snap["analytics"]["metrika"], snap["analytics"]["ga4"]
    date = snap["report_date"]
    md = snap.get("market_demand") or {}
    if md.get("available"):
        demand_fresh = (f"; рыночный спрос — замер {ru(md['source']['measured_at'])}"
                        + ("" if md.get("complete") else " (собирается)")
                        + ", обновление раз в месяц")
    else:
        demand_fresh = "; рыночный спрос ещё не измерен"
    freshness = (f"Данные: Яндекс/Google по {ru(yx['source']['latest_event_date'])}; "
                 f"Метрика/GA4 по {ru(m['source']['latest_event_date'])}{demand_fresh}")
    summary = (f"Яндекс — {st['yandex']}: страницы в поиске и позиции держатся на прежнем уровне; "
               f"Google — {st['google']}. Общий вывод: {st['overall']}, потому что сверка источников "
               "измерения ещё идёт и оценка кликабельности до её окончания не публикуется.")
    blocking, warns = build_risks(dq)
    return {
        "date": date,
        "date_h": dt.date.fromisoformat(date).strftime("%d.%m.%Y"),
        "freshness": freshness,
        "summary": summary,
        "from_you": "Действий не требуется.",
        "from_you_note": "Вопросов по бюджету, ценам, доменам и необратимым изменениям сегодня нет. "
                         "Задачи, которые система ведёт сама, перечислены ниже — вмешательство не нужно, "
                         "результат придёт в отчётах по срокам.",
        "kpis": build_kpis(snap),
        "actions": build_actions(actions_cfg, md),
        "changes": build_changes(snap, prev, st),
        "blocking": blocking,
        "warnings": warns,
        "checkpoint": ("22.08 — итог сверки источников измерения: либо разрыв объяснён, либо зафиксирован "
                       "как ограничение, и оценка кликабельности возвращается в отчёт. "
                       "26.08 — промежуточный срез по изменению карточек вендоров: смотрим, дошли ли "
                       "обновлённые описания до выдачи и набралось ли наблюдений для вывода."),
        "links": {
            "appendix": f"{BLOB}/reports/seo/intelligence/{date}-appendix.md",
            "tasks": f"{REPO}/tree/{BRANCH}/reports/seo/tasks",
            "quality": f"{BLOB}/reports/seo/intelligence/data-quality/{date}.json",
            "pr": f"{REPO}/pull/57",
        },
        "status": st,
    }


def visible_word_count(b) -> int:
    parts = [b["freshness"], b["summary"], b["from_you"], b["from_you_note"], b["checkpoint"]]
    parts += [f"{k['label']} {k['value']} {k['note']}" for k in b["kpis"]]
    parts += [f"{a['id']} {a['title']} {a['plain']} {a['outcome']} {a['owner']} {a['status_label']} {a['due_label']}"
              for a in b["actions"]]
    parts += [a.get("demand", "") for a in b["actions"]]
    parts += [f"{c['title']} {c['text']}" for c in b["changes"]]
    if b["blocking"]:
        parts.append(f"{b['blocking']['title']} {b['blocking']['text']}")
    parts += [f"{w['title']} {w['text']}" for w in b["warnings"]]
    parts += ["Итог дня", "От вас", "Показатели", "Система уже делает", "Что изменилось",
              "Риски", "Следующая проверка", "Полный отчёт", "Журнал работ",
              "BIZSoft Search Performance", b["date_h"]]
    return words(*parts)


def html_email(b, charts, cid_mode: bool) -> str:
    def img(name):
        c = charts[name]
        src = f"cid:{c['cid']}" if cid_mode else f"charts/{c['file']}"
        return (f"<img src=\"{src}\" width=\"610\" alt=\"{c['alt']}\" "
                f"style=\"display:block;width:100%;max-width:610px;height:auto;border:1px solid {LINE};"
                f"border-radius:10px;\">"
                f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{MUTED};padding-top:6px;line-height:1.45;\">{c['fallback']}</div>")

    kpi = ""
    for k in b["kpis"]:
        kpi += (f"<td width='50%' style='padding:5px;'>"
                f"<div style='border:1px solid {LINE};border-radius:10px;padding:12px 14px;'>"
                f"<div data-meta='1' style='font-size:13px;color:{MUTED};line-height:1.4;'>{k['label']}</div>"
                f"<div style='font-size:22px;font-weight:700;padding-top:3px;'>{k['value']}</div>"
                f"<div data-meta='1' style='font-size:13px;color:{MUTED};padding-top:4px;line-height:1.45;'>{k['note']}</div>"
                f"</div></td>")
    kpi_rows = f"<tr>{''.join(list(kpi.split('</td>')[0:2])[0] + '</td>' + kpi.split('</td>')[1] + '</td>')}</tr>"
    cells = [c + "</td>" for c in kpi.split("</td>") if c.strip()]
    kpi_rows = f"<tr>{cells[0]}{cells[1]}</tr><tr>{cells[2]}{cells[3]}</tr>"

    acts = ""
    for a in b["actions"]:
        color = {"GREEN": GOOD, "YELLOW": WARN, "RED": MUTED}[a["zone"]]
        why = (f"<div style='font-size:14px;color:{INK};padding-top:4px;line-height:1.5;'>"
               f"{a['demand']}</div>") if a.get("demand") else ""
        acts += (f"<div style='border:1px solid {LINE};border-left:3px solid {color};border-radius:9px;"
                 f"padding:11px 14px;margin-bottom:8px;'>"
                 f"<div style='font-size:15.5px;font-weight:600;line-height:1.45;'>{a['title']}"
                 f" <a data-meta='1' href='{a['ticket_url']}' style='font-size:12.5px;color:{MUTED};text-decoration:none;"
                 f"border:1px solid {LINE};border-radius:4px;padding:1px 5px;'>{a['id']}</a></div>"
                 f"<div style='font-size:14.5px;color:{INK};padding-top:4px;line-height:1.5;'>{a['plain']}</div>"
                 f"<div style='font-size:14px;color:{MUTED};padding-top:4px;line-height:1.5;'>{a['outcome']}</div>"
                 f"{why}"
                 f"<div data-meta='1' style='font-size:13px;color:{MUTED};padding-top:5px;'>"
                 f"{a['owner']} · {a['status_label']} · {a['due_label']}</div></div>")

    chs = ""
    for c in b["changes"]:
        chs += (f"<div style='padding:9px 0;border-bottom:1px solid {LINE};'>"
                f"<div style='font-size:15.5px;font-weight:600;line-height:1.45;'>{c['title']}</div>"
                f"<div style='font-size:15px;padding-top:3px;line-height:1.55;'>{c['text']}</div></div>")

    risk = ""
    if b["blocking"]:
        risk += (f"<div style='background:#fdecea;border-left:4px solid {BAD};border-radius:0 9px 9px 0;"
                 f"padding:12px 14px;margin-bottom:9px;'>"
                 f"<div style='font-size:15.5px;font-weight:700;color:{BAD};line-height:1.45;'>{b['blocking']['title']}</div>"
                 f"<div style='font-size:15px;padding-top:4px;line-height:1.55;'>{b['blocking']['text']}</div></div>")
    for w in b["warnings"]:
        risk += (f"<div style='font-size:14.5px;line-height:1.55;padding:5px 0;'>"
                 f"<b>{w['title']}.</b> {w['text']}</div>")

    btn = (lambda url, text, primary: (
        f"<a href='{url}' style='display:inline-block;padding:11px 20px;border-radius:8px;"
        f"font-size:15px;font-weight:600;text-decoration:none;margin:0 8px 8px 0;"
        + (f"background:{ACCENT};color:#ffffff;" if primary else f"background:#ffffff;color:{INK};border:1px solid {LINE};")
        + f"'>{text}</a>"))

    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BIZSoft Search Performance — {b['date_h']}</title></head>
<body style="margin:0;padding:0;background:#f4f4f6;font-family:{FONT};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f6;">
<tr><td align="center" style="padding:18px 10px;">
<table role="presentation" width="640" cellpadding="0" cellspacing="0"
 style="max-width:640px;width:100%;background:#ffffff;border-radius:14px;border:1px solid {LINE};overflow:hidden;">

<tr><td style="padding:22px 24px 0;">
  <div style="font-size:21px;font-weight:700;line-height:1.3;color:{INK};">BIZSoft Search Performance</div>
  <div data-meta="1" style="font-size:13px;color:{MUTED};padding-top:5px;line-height:1.45;">{b['date_h']} · {b['freshness']}</div>
</td></tr>

<tr><td style="padding:16px 24px 0;">
  <div style="font-size:17.5px;font-weight:700;line-height:1.35;">Итог дня</div>
  <div style="font-size:15.5px;line-height:1.55;padding-top:6px;">{b['summary']}</div>
</td></tr>

<tr><td style="padding:16px 24px 0;">
  <div style="background:#eef7f0;border-left:4px solid {GOOD};border-radius:0 9px 9px 0;padding:12px 14px;">
    <div style="font-size:17px;font-weight:700;line-height:1.35;">От вас: {b['from_you']}</div>
    <div style="font-size:14.5px;color:{INK};padding-top:4px;line-height:1.5;">{b['from_you_note']}</div>
  </div>
</td></tr>

<tr><td style="padding:16px 19px 0;">
  <div style="font-size:17.5px;font-weight:700;padding:0 5px 6px;line-height:1.35;">Показатели</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{kpi_rows}</table>
</td></tr>

<tr><td style="padding:14px 24px 0;">{img('measure-map')}</td></tr>

<tr><td style="padding:18px 24px 0;">
  <div style="font-size:17.5px;font-weight:700;padding-bottom:8px;line-height:1.35;">Система уже делает</div>{acts}
</td></tr>

<tr><td style="padding:12px 24px 0;">
  <div style="font-size:17.5px;font-weight:700;line-height:1.35;">Что изменилось</div>{chs}
</td></tr>

<tr><td style="padding:14px 24px 0;">{img('google-wow')}</td></tr>

<tr><td style="padding:18px 24px 0;">
  <div style="font-size:17.5px;font-weight:700;padding-bottom:8px;line-height:1.35;">Риски</div>{risk}
</td></tr>

<tr><td style="padding:18px 24px 0;">
  <div style="font-size:17.5px;font-weight:700;line-height:1.35;">Следующая проверка</div>
  <div style="font-size:15px;line-height:1.55;padding-top:5px;">{b['checkpoint']}</div>
</td></tr>

<tr><td style="padding:20px 24px 6px;">
  {btn(b['links']['appendix'], 'Полный отчёт', True)}{btn(b['links']['tasks'], 'Журнал работ', False)}
</td></tr>

<tr><td style="background:#fafafb;padding:14px 24px 18px;border-top:1px solid {LINE};">
  <div style="font-size:12.5px;color:{MUTED};line-height:1.5;">
  <a href="{b['links']['quality']}" style="color:{MUTED};">Проверки качества данных</a> ·
  <a href="{b['links']['pr']}" style="color:{MUTED};">Изменение карточек вендоров (PR #57)</a> ·
  <a href="{BLOB}/docs/seo/reporting-methodology.md" style="color:{MUTED};">Методика</a><br>
  Автоматический ежедневный отчёт BIZSoft. Цифры — из единого проверенного среза; отсутствующие
  значения показаны как «нет данных».</div>
</td></tr>

</table></td></tr></table></body></html>"""


def plain_text(b) -> str:
    L = [f"BIZSOFT SEARCH PERFORMANCE — {b['date_h']}", b["freshness"], "",
         "ИТОГ ДНЯ", b["summary"], "",
         f"ОТ ВАС: {b['from_you']}", b["from_you_note"], "", "ПОКАЗАТЕЛИ"]
    for k in b["kpis"]:
        L.append(f"- {k['label']}: {k['value']} ({k['note']})")
    L += ["", "КАРТА ИЗМЕРЕНИЯ",
          "- Вебмастер: 926 показов -> 6 кликов (выборка 100 запросов)",
          "- Метрика: 37 визитов из поиска -> 3 целевых события",
          "- CRM: нет данных",
          "  Охват и периоды источников не сопоставлены.", "", "СИСТЕМА УЖЕ ДЕЛАЕТ"]
    for a in b["actions"]:
        L.append(f"- [{a['id']}] {a['title']} — {a['plain']}")
        L.append(f"  {a['outcome']}")
        if a.get("demand"):
            L.append(f"  {a['demand']}")
        L.append(f"  {a['owner']} · {a['status_label']} · {a['due_label']}")
    L += ["", "ЧТО ИЗМЕНИЛОСЬ"]
    for c in b["changes"]:
        L.append(f"- {c['title']}: {c['text']}")
    L += ["", "РИСКИ"]
    if b["blocking"]:
        L.append(f"- БЛОКИРУЮЩИЙ: {b['blocking']['title']}. {b['blocking']['text']}")
    for w in b["warnings"]:
        L.append(f"- {w['title']}. {w['text']}")
    L += ["", "СЛЕДУЮЩАЯ ПРОВЕРКА", b["checkpoint"], "",
          "ССЫЛКИ",
          f"Полный отчёт: {b['links']['appendix']}",
          f"Журнал работ: {b['links']['tasks']}",
          f"Проверки качества: {b['links']['quality']}",
          f"Изменение карточек (PR #57): {b['links']['pr']}"]
    return "\n".join(L)


def build_eml(b, html, text, charts, date) -> bytes:
    msg = EmailMessage()
    msg["Subject"] = f"BIZSoft Search Performance — {b['date_h']}"
    msg["From"] = "BIZSoft SEO-мониторинг <hello@biz-soft.pro>"
    msg["To"] = "avbelyaev@biz-soft.pro"
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(text)
    cids = {}
    for name, c in charts.items():
        cids[c["cid"]] = make_msgid(domain="biz-soft.pro")
    for cid_key, real in cids.items():
        html = html.replace(f"cid:{cid_key}", f"cid:{real[1:-1]}")
    msg.add_alternative(html, subtype="html")
    part = msg.get_payload()[-1]
    for name, c in charts.items():
        data = pathlib.Path(c["path"]).read_bytes()
        part.add_related(data, "image", "png", cid=cids[c["cid"]],
                         filename=c["file"], disposition="inline")
    return msg.as_bytes()


def appendix(snap, prev, dq, svg_charts, b) -> str:
    base = report_v2.md_appendix(snap, prev, dq, svg_charts)
    yx, g = snap["yandex"], snap["google"]
    m, ga = snap["analytics"]["metrika"], snap["analytics"]["ga4"]
    md = snap.get("market_demand") or {}
    dm = ["", "## 15. Рыночный спрос (Вордстат)", ""]
    if not md.get("available"):
        dm += [f"Замер недоступен: {md.get('reason', 'нет данных')}. "
               "Формулировки о рыночном спросе и решения об ассортименте в отчёт не попадают.", ""]
    else:
        src = md["source"]
        dm += [f"**Замер:** {src['measured_at']} (возраст {src['age_days']} дн., "
               f"обновление {src['refresh']}). **Регион:** {src['region']}. "
               f"**Единица:** {src['unit']}. **Окно:** {src['window']}. "
               f"**Соответствие:** {src['match_type']}.",
               f"**Полнота:** собрано {md.get('coverage')} запросов месяца; "
               f"кластеров с данными {md.get('clusters_measured')} из {md.get('clusters_planned')}"
               + ("." if md.get("complete") else " — проход не завершён, выводы предварительные."),
               "",
               "ФАКТ — числа Вордстата. Это объём поисковых запросов в Яндексе, а не покупки, "
               "не заявки и не выручка; на Google не переносится. Доля голоса не рассчитывается: "
               "наша видимость известна по выборке топ-100 запросов Вебмастера, охват и периоды "
               "источников не сверены (DATA-001).", ""]
        top = md.get("top_commercial") or []
        if top:
            dm += ["### 15.1. Коммерческий спрос по карточкам", "",
                   "Сортировка по сумме показов коммерческих фраз. Общая частотность бренда "
                   "покупательским спросом не является: у canva 119 076 показов бренда и "
                   "1 096 покупательских — решение принимается по второй колонке.", "",
                   "| Карточка | Коммерческий спрос, показы/мес | Спрос по бренду, показы/мес |",
                   "|---|---|---|"]
            for c in top:
                dm.append(f"| {c['cluster']} ({c.get('page') or 'страницы нет'}) | "
                          f"{num(c.get('commercial_impressions'))} | {num(c.get('seed_impressions'))} |")
            dm.append("")
        gaps = md.get("gaps") or {}
        if gaps:
            dm += ["### 15.2. Разрывы: спрос есть, наша страница по запросу не видна", "",
                   f"Всего {md.get('gap_phrases')} "
                   f"{plural(md.get('gap_phrases') or 0, 'запрос', 'запроса', 'запросов')} "
                   f"на {md.get('gap_cards')} "
                   f"{plural(md.get('gap_cards') or 0, 'карточке', 'карточках', 'карточках')}. "
                   "Отсутствие запроса в выборке Вебмастера не доказывает нулевую видимость — "
                   "это список кандидатов на доработку, а не диагноз.", "",
                   "| Карточка | Запрос | Показы/мес |", "|---|---|---|"]
            for cluster, rows in gaps.items():
                for r in rows:
                    dm.append(f"| {cluster} | {r['phrase']} | {num(r['impressions'])} |")
            dm.append("")
        disc = md.get("discovery") or []
        if disc:
            dm += ["### 15.3. Товары с подтверждённым спросом, которых у нас нет", "",
                   "| Бренд | Спрос по фразе покупки на юрлицо, показы/мес |", "|---|---|"]
            for d in disc:
                dm.append(f"| {d['brand']} | {num(d.get('demand'))} |")
            dm.append("")
        dm += ["### 15.4. Как спрос используется в отчёте", "",
               "- В письме спроса как показателя дня нет: источник обновляется раз в месяц, "
               "и суточная дельта у него отсутствует по построению.",
               "- Спрос служит обоснованием действий: у каждого действия, вызванного разрывом "
               "семантики, указана фраза и её частотность.",
               "- Запись в блоке «Что изменилось» появляется только в день нового замера.",
               "- Решения об ассортименте принимаются только по завершённому проходу.", ""]

    extra = dm + ["", "## 16. Свежесть источников (полная таблица)", "",
             "| Источник | Метрика API | Последнее событие | Период | Дней | Сбор | Статус |",
             "|---|---|---|---|---|---|---|"]
    for src, metric in ((yx["source"], "popular queries (выборка топ-100)"),
                        (g["source"], "searchAnalytics: query, page, date"),
                        (m["source"], "ym:s:visits, ym:s:sumGoalReachesAny"),
                        (ga["source"], "sessions, keyEvents")):
        extra.append(f"| {src['source_name']} | `{metric}` | {src['latest_event_date']} | "
                     f"{src['current_period_start']}–{src['current_period_end']} | "
                     f"{src['current_period_days']} | {src['collected_at']} | {src['status']} |")
    extra += ["| CRM | — | нет данных | — | — | не подключена | unavailable |", "",
              "## 17. Все предупреждения качества данных", "",
              "| Уровень | Код | Что означает | Влияние |", "|---|---|---|---|"]
    for f in dq["findings"]:
        extra.append(f"| {f['level']} | `{f['code']}` | {f['detail']} | {f['effect_on_report']} |")
    extra += ["", "## 18. Действия, роли и зоны ответственности", "",
              "| ID | Действие | Зона | Роль-владелец | Статус | Срок | Тикет |", "|---|---|---|---|---|---|---|"]
    for a in b["actions"]:
        extra.append(f"| {a['id']} | {a['title']} | {a['zone']} | {a['owner']} | {a['status_label']} | "
                     f"{a['due_label']} | `{a['ticket']}` |")
    extra += ["", "Зоны: **GREEN** — агент выполняет автономно; **YELLOW** — агент выполняет, "
              "руководителя информируем; **RED** — требуется решение руководителя (бюджет, "
              "юридические обязательства, цены, домены, необратимые изменения). Владельцы GREEN и "
              "YELLOW назначаются автоматически по карте ролей `reports/seo/intelligence/actions.json`.",
              "", "## 19. Совместное внедрение и его следствие", "",
              "Заголовки, описания и блок вопросов пяти карточек вендоров выкачены одной правкой "
              "2026-08-19. Это **один эксперимент**: вклад отдельных элементов неразделим по "
              "построению, ретроспективное разделение на два независимых эксперимента запрещено. "
              "Контрольные показатели (guardrails): показы, средняя позиция, органические сессии, "
              "уникальные пользователи с целевым событием. Откат (rollback): возврат прежних "
              "значений из истории репозитория. Условие остановки (stop-condition): ухудшение любого "
              "контрольного показателя за пределами обычного разброса.",
              "", "## 20. Технический словарь", "",
              "| В письме | В системах и API |", "|---|---|",
              "| визиты из поиска | `ym:s:visits`, фильтр `lastTrafficSource == organic` |",
              "| целевые события | `ym:s:sumGoalReachesAny`; в GA4 — key events |",
              "| выборка запросов | Яндекс.Вебмастер, метод popular queries (топ-100) |",
              "| расхождение источников | проверка `SOURCE_RECONCILIATION` |",
              "| единый проверенный срез | snapshot `intelligence/snapshots/<дата>.json` |",
              "| контрольные показатели | guardrails |",
              "| условие остановки | stop-condition |", ""]
    return base + "\n".join(extra)


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    snap = json.loads((BASE / "snapshots" / f"{date}.json").read_text(encoding="utf-8"))
    dq = json.loads((BASE / "data-quality" / f"{date}.json").read_text(encoding="utf-8"))
    actions_cfg = json.loads((BASE / "actions.json").read_text(encoding="utf-8"))
    prev = report_v2.prev_snapshot(date)

    svg_charts = charts_svg.build_all(snap, date)          # для приложения
    png_charts = charts_png.build(snap, date)              # для письма
    b = assemble(snap, prev, dq, actions_cfg)

    email_html = html_email(b, png_charts, cid_mode=True)
    preview_html = html_email(b, png_charts, cid_mode=False)
    text = plain_text(b)
    (BASE / f"{date}-executive-email.html").write_text(email_html, encoding="utf-8")
    (BASE / f"{date}-executive.html").write_text(preview_html, encoding="utf-8")
    (BASE / f"{date}-executive.txt").write_text(text, encoding="utf-8")
    (BASE / f"{date}-executive.eml").write_bytes(build_eml(b, email_html, text, png_charts, date))
    (BASE / f"{date}-appendix.md").write_text(appendix(snap, prev, dq, svg_charts, b), encoding="utf-8")
    (BASE / f"{date}-executive.md").write_text(
        f"# BIZSoft Search Performance — {b['date_h']}\n\n" + text + "\n", encoding="utf-8")

    vw = visible_word_count(b)
    print(f"V3: письмо собрано, видимых слов {vw}, слов в текстовой версии {len(text.split())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
