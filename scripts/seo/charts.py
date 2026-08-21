#!/usr/bin/env python3
"""Статические SVG-графики отчёта (без клиентских зависимостей и JS).

Каждый график: заголовок, период, источник, единицы, дата данных, alt-text
и табличный fallback (возвращается вместе с SVG для вставки в приложение).
Читаемость обеспечивается viewBox + width:100% (375–680 px).

Запуск: python3 scripts/seo/charts.py [YYYY-MM-DD]
Результат: reports/seo/intelligence/charts/<дата>-*.svg
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

SNAP_DIR = pathlib.Path("reports/seo/intelligence/snapshots")
OUT_DIR = pathlib.Path("reports/seo/intelligence/charts")

INK, MUTED, LINE = "#1d1d1f", "#66666e", "#e8e8ed"
ACCENT, GOOD, BAD, GREY = "#f2591d", "#1a8f4c", "#d92d20", "#c7c7cf"
FONT = "font-family='Arial,Helvetica,sans-serif'"


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def frame(w: int, h: int, title: str, subtitle: str, body: str, alt: str) -> str:
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='100%' "
        f"role='img' aria-label='{esc(alt)}' style='max-width:{w}px;height:auto'>"
        f"<title>{esc(alt)}</title>"
        f"<rect width='{w}' height='{h}' fill='#ffffff'/>"
        f"<text x='16' y='24' {FONT} font-size='14' font-weight='bold' fill='{INK}'>{esc(title)}</text>"
        f"<text x='16' y='42' {FONT} font-size='11' fill='{MUTED}'>{esc(subtitle)}</text>"
        f"{body}</svg>")


def chart_google_daily(snap: dict) -> tuple[str, str, list]:
    g = snap["google"]
    daily = g["daily"]
    w, h = 660, 300
    x0, y0, pw, ph = 46, 70, w - 70, 170
    mx = max([d["impressions"] for d in daily] + [1])
    n = len(daily)
    step = pw / max(n - 1, 1)
    pts = [(x0 + i * step, y0 + ph - (d["impressions"] / mx) * ph) for i, d in enumerate(daily)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    # семидневная скользящая средняя
    ma = []
    for i in range(len(daily)):
        window = [d["impressions"] for d in daily[max(0, i - 6):i + 1]]
        ma.append(sum(window) / len(window))
    mapts = " ".join(f"{x0 + i * step:.1f},{y0 + ph - (v / mx) * ph:.1f}" for i, v in enumerate(ma))
    body = [f"<line x1='{x0}' y1='{y0 + ph}' x2='{x0 + pw}' y2='{y0 + ph}' stroke='{LINE}'/>"]
    for frac in (0, 0.5, 1):
        yy = y0 + ph - frac * ph
        body.append(f"<line x1='{x0}' y1='{yy:.0f}' x2='{x0 + pw}' y2='{yy:.0f}' stroke='{LINE}' stroke-dasharray='2,3'/>")
        body.append(f"<text x='{x0 - 8}' y='{yy + 4:.0f}' {FONT} font-size='10' fill='{MUTED}' text-anchor='end'>{mx * frac:.0f}</text>")
    body.append(f"<polyline points='{poly}' fill='none' stroke='{ACCENT}' stroke-width='2'/>")
    body.append(f"<polyline points='{mapts}' fill='none' stroke='{INK}' stroke-width='1.5' stroke-dasharray='5,3'/>")
    for i, d in enumerate(daily):
        if i % 6 == 0 or i == n - 1:
            body.append(f"<text x='{x0 + i * step:.0f}' y='{y0 + ph + 16}' {FONT} font-size='9' fill='{MUTED}' text-anchor='middle'>{d['date'][5:]}</text>")
    # клики (все нули в текущем срезе) — подписываем явно
    body.append(f"<text x='{x0}' y='{y0 + ph + 36}' {FONT} font-size='10' fill='{MUTED}'>"
                f"Клики за период: {g['totals']['clicks_window']} (линия кликов совпадает с осью X)</text>")
    body.append(f"<rect x='{x0}' y='{h - 26}' width='10' height='3' fill='{ACCENT}'/>"
                f"<text x='{x0 + 16}' y='{h - 21}' {FONT} font-size='10' fill='{INK}'>показы/день</text>"
                f"<rect x='{x0 + 120}' y='{h - 26}' width='10' height='3' fill='{INK}'/>"
                f"<text x='{x0 + 136}' y='{h - 21}' {FONT} font-size='10' fill='{INK}'>скользящая средняя 7 дн.</text>")
    body.append(f"<text x='{x0 + 330}' y='{h - 21}' {FONT} font-size='10' fill='{MUTED}'>"
                f"внедрение метаданных 19.08 — вне окна данных</text>")
    sub = (f"Показы и клики по дням · источник: Google Search Console · единицы: показы/сутки · "
           f"данные по {g['source']['latest_event_date']}")
    alt = (f"Линейный график показов Google по дням за {g['totals']['window_days']} дней; "
           f"сумма показов {g['totals']['impressions_window']}, кликов {g['totals']['clicks_window']}")
    table = [("Дата", "Показы", "Клики")] + [(d["date"], d["impressions"], d["clicks"]) for d in daily]
    return frame(w, h, "Google: динамика показов", sub, "".join(body), alt), alt, table


def chart_funnel(snap: dict) -> tuple[str, str, list]:
    yx, an = snap["yandex"], snap["analytics"]
    m, ga = an.get("metrika", {}), an.get("ga4", {})
    stages = [
        ("Показы (Яндекс, выборка топ-100 запросов)", yx["totals"]["impressions"] if yx.get("available") else None, "05–17.08"),
        ("Клики (Яндекс, та же выборка)", yx["totals"]["clicks"] if yx.get("available") else None, "05–17.08"),
        ("Органические визиты (Метрика)", int(m["organic_visits"]) if m.get("available") else None, "05–18.08"),
        ("Целевые события органики (Метрика)", int(m["organic_goal_events"]) if m.get("available") else None, "05–18.08"),
        ("Квалифицированные лиды", None, "CRM не подключена"),
        ("Сделки / выручка", None, "CRM не подключена"),
    ]
    w = 660
    h = 90 + len(stages) * 42
    mx = max([v for _, v, _ in stages if v] + [1])
    body = []
    for i, (label, val, period) in enumerate(stages):
        y = 70 + i * 42
        known = val is not None
        bw = (val / mx) * 380 if known and mx else 380
        fill = ACCENT if known else GREY
        dash = "" if known else " stroke='#b9b9c2' stroke-dasharray='4,3'"
        body.append(f"<rect x='16' y='{y}' width='{max(bw, 4):.0f}' height='24' rx='4' fill='{fill}'{dash}/>")
        txt = f"{val}" if known else "нет данных"
        body.append(f"<text x='{max(bw, 4) + 24:.0f}' y='{y + 17}' {FONT} font-size='12' font-weight='bold' fill='{INK}'>{esc(txt)}</text>")
        body.append(f"<text x='{max(bw, 4) + 24 + (len(txt) * 8):.0f}' y='{y + 17}' {FONT} font-size='10.5' fill='{MUTED}'>{esc(label)} · {esc(period)}</text>")
    body.append(f"<text x='16' y='{h - 16}' {FONT} font-size='10' fill='{MUTED}'>"
                "Этапы измеряются разными системами и окнами — воронка не является сквозной цепочкой одних и тех же сессий.</text>")
    sub = "Источники: Яндекс.Вебмастер, Яндекс.Метрика, CRM (не подключена) · единицы: события"
    alt = "Воронка поиска: показы, клики, визиты, целевые события; лиды и сделки — нет данных"
    table = [("Этап", "Значение", "Период")] + [(s, (v if v is not None else "нет данных"), p) for s, v, p in stages]
    return frame(w, h, "Воронка поиска (по доступным источникам)", sub, "".join(body), alt), alt, table


def chart_ctr_matrix(snap: dict) -> tuple[str, str, list]:
    yx = snap["yandex"]
    ents = [e for e in yx["entities"] if e["average_position"] and e["impressions"]]
    ents.sort(key=lambda e: -e["impressions"])
    top = ents[:24]
    w, h = 660, 340
    x0, y0, pw, ph = 52, 70, w - 90, 200
    maxpos, maximp = 20.0, max([e["impressions"] for e in top] + [1])
    body = [f"<line x1='{x0}' y1='{y0 + ph}' x2='{x0 + pw}' y2='{y0 + ph}' stroke='{LINE}'/>",
            f"<line x1='{x0}' y1='{y0}' x2='{x0}' y2='{y0 + ph}' stroke='{LINE}'/>"]
    for p in (1, 5, 10, 15, 20):
        x = x0 + (p / maxpos) * pw
        body.append(f"<line x1='{x:.0f}' y1='{y0}' x2='{x:.0f}' y2='{y0 + ph}' stroke='{LINE}' stroke-dasharray='2,3'/>")
        body.append(f"<text x='{x:.0f}' y='{y0 + ph + 16}' {FONT} font-size='10' fill='{MUTED}' text-anchor='middle'>{p}</text>")
    low = snap["thresholds"]["low_impressions"]
    for e in top:
        pos = min(e["average_position"], maxpos)
        x = x0 + (pos / maxpos) * pw
        y = y0 + ph - (e["impressions"] / maximp) * ph
        r = 4 + 10 * (e["impressions"] / maximp)
        weak = e["impressions"] < low
        wdash = " stroke-dasharray='3,2'" if weak else ""
        body.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{r:.1f}' fill='{ACCENT}' fill-opacity='0.35' stroke='{ACCENT}'{wdash}/>")
    for e in top[:5]:
        pos = min(e["average_position"], maxpos)
        x = x0 + (pos / maxpos) * pw
        y = y0 + ph - (e["impressions"] / maximp) * ph
        label = e["entity_id"][:28] + ("…" if len(e["entity_id"]) > 28 else "")
        mark = "" if e["impressions"] >= low else " (низкая выборка)"
        body.append(f"<text x='{min(x + 12, w - 200):.0f}' y='{y - 6:.0f}' {FONT} font-size='9.5' fill='{INK}'>{esc(label + mark)}</text>")
    body.append(f"<text x='{x0 + pw / 2:.0f}' y='{y0 + ph + 34}' {FONT} font-size='10.5' fill='{MUTED}' text-anchor='middle'>средняя позиция (левее — выше)</text>")
    body.append(f"<text x='16' y='{y0 - 6}' {FONT} font-size='10.5' fill='{MUTED}'>показы за период (выше — больше)</text>")
    body.append(f"<text x='16' y='{h - 16}' {FONT} font-size='10' fill='{MUTED}'>Размер круга = показы. Пунктирная обводка = выборка меньше "
                f"{low} показов. Утверждённой CTR-модели нет, поэтому потенциальные клики не оцениваются.</text>")
    sub = (f"Запросы Яндекса (выборка топ-100) · период {yx['source']['current_period_start']}–"
           f"{yx['source']['current_period_end']} · единицы: показы и средняя позиция")
    alt = "Точечная диаграмма: средняя позиция против числа показов по запросам Яндекса"
    table = [("Запрос", "Показы", "Средняя позиция", "Выборка")] + [
        (e["entity_id"], e["impressions"], e["average_position"],
         "низкая" if e["impressions"] < low else "достаточная") for e in top[:12]]
    return frame(w, h, "Матрица возможностей: позиция × показы", sub, "".join(body), alt), alt, table


def chart_indexation(snap: dict) -> tuple[str, str, list]:
    idx = snap["yandex"].get("indexation") if snap["yandex"].get("available") else None
    w, h = 660, 210
    if not idx:
        return frame(w, 120, "Индексация", "нет данных", "", "нет данных"), "нет данных", []
    parts = [("В поиске", idx["indexed_urls"], GOOD, "измерено"),
             ("Исключено — причина не классифицирована", idx["unclassified_excluded_urls"], GREY, "требуется разбор")]
    total = sum(p[1] for p in parts if p[1]) or 1
    body, x = [], 16
    for label, val, color, _ in parts:
        bw = (val / total) * (w - 32)
        body.append(f"<rect x='{x:.0f}' y='70' width='{bw:.0f}' height='34' fill='{color}'/>")
        body.append(f"<text x='{x + 8:.0f}' y='92' {FONT} font-size='12' font-weight='bold' fill='#ffffff'>{val}</text>")
        x += bw
    y = 126
    for label, val, color, note in parts:
        body.append(f"<rect x='16' y='{y - 9}' width='10' height='10' fill='{color}'/>")
        body.append(f"<text x='32' y='{y}' {FONT} font-size='11' fill='{INK}'>{esc(label)}: {val} — {esc(note)}</text>")
        y += 20
    body.append(f"<text x='16' y='{y + 4}' {FONT} font-size='10' fill='{MUTED}'>Разбивка исключённых по причинам "
                "(дубли, canonical, noindex, технические ошибки, коммерческие страницы) — нет данных: "
                "источник не выгружается (тикет INDEX-001).</text>")
    sub = (f"Источник: Яндекс.Вебмастер · всего известных URL: {idx['total_known_urls']} · "
           f"дата данных: {snap['yandex']['source']['collected_at']}")
    alt = f"Индексация: {idx['indexed_urls']} страниц в поиске, {idx['excluded_urls']} исключено без классификации"
    table = [("Категория", "URL")] + [(p[0], p[1]) for p in parts]
    return frame(w, h, "Индексация в Яндексе", sub, "".join(body), alt), alt, table


def chart_vendor_heatmap(snap: dict) -> tuple[str, str, list]:
    yx = snap["yandex"]
    vendors = {}
    markers = ["depositphotos", "heygen", "coreldraw", "marmoset", "canva", "figma", "unity", "procreate"]
    for e in yx["entities"]:
        for m in markers:
            if m in e["entity_id"].lower():
                v = vendors.setdefault(m, {"impressions": 0, "clicks": 0, "positions": [], "queries": 0})
                v["impressions"] += e["impressions"] or 0
                v["clicks"] += e["clicks"] or 0
                v["queries"] += 1
                if e["average_position"]:
                    v["positions"].append(e["average_position"])
                break
    rows = sorted(vendors.items(), key=lambda kv: -kv[1]["impressions"])
    w = 660
    h = 96 + len(rows) * 26
    body = [f"<text x='16' y='66' {FONT} font-size='10.5' font-weight='bold' fill='{MUTED}'>Вендор</text>",
            f"<text x='210' y='66' {FONT} font-size='10.5' font-weight='bold' fill='{MUTED}'>Показы</text>",
            f"<text x='330' y='66' {FONT} font-size='10.5' font-weight='bold' fill='{MUTED}'>Клики</text>",
            f"<text x='410' y='66' {FONT} font-size='10.5' font-weight='bold' fill='{MUTED}'>Лучшая поз.</text>",
            f"<text x='520' y='66' {FONT} font-size='10.5' font-weight='bold' fill='{MUTED}'>Выборка</text>"]
    mx = max([v["impressions"] for _, v in rows] + [1])
    low = snap["thresholds"]["low_impressions"]
    for i, (name, v) in enumerate(rows):
        y = 86 + i * 26
        shade = 0.12 + 0.55 * (v["impressions"] / mx)
        body.append(f"<rect x='16' y='{y - 14}' width='628' height='22' fill='{ACCENT}' fill-opacity='{shade:.2f}'/>")
        best = min(v["positions"]) if v["positions"] else None
        conf = "достаточная" if v["impressions"] >= low else "низкая"
        body.append(f"<text x='24' y='{y}' {FONT} font-size='11' fill='{INK}'>{esc(name)}</text>")
        body.append(f"<text x='210' y='{y}' {FONT} font-size='11' fill='{INK}'>{v['impressions']}</text>")
        body.append(f"<text x='330' y='{y}' {FONT} font-size='11' fill='{INK}'>{v['clicks']}</text>")
        body.append(f"<text x='410' y='{y}' {FONT} font-size='11' fill='{INK}'>{best if best else 'нет данных'}</text>")
        body.append(f"<text x='520' y='{y}' {FONT} font-size='11' fill='{INK}'>{conf}</text>")
    sub = (f"Кластеры по вхождению названия вендора в запрос · период "
           f"{yx['source']['current_period_start']}–{yx['source']['current_period_end']} · "
           "источник: Яндекс.Вебмастер (выборка топ-100 запросов)")
    alt = "Таблица-теплокарта вендорских кластеров: показы, клики, лучшая позиция, надёжность выборки"
    table = [("Вендор", "Показы", "Клики", "Лучшая позиция", "Запросов", "Выборка")] + [
        (n, v["impressions"], v["clicks"], (min(v["positions"]) if v["positions"] else "нет данных"),
         v["queries"], "достаточная" if v["impressions"] >= low else "низкая") for n, v in rows]
    return frame(w, h, "Вендорские кластеры", sub, "".join(body), alt), alt, table


def build_all(snap: dict, date: str) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    charts = {
        "google-daily": chart_google_daily(snap),
        "funnel": chart_funnel(snap),
        "ctr-matrix": chart_ctr_matrix(snap),
        "indexation": chart_indexation(snap),
        "vendor-heatmap": chart_vendor_heatmap(snap),
    }
    meta = {}
    for name, (svg, alt, table) in charts.items():
        p = OUT_DIR / f"{date}-{name}.svg"
        p.write_text(svg, encoding="utf-8")
        meta[name] = {"path": str(p), "alt": alt, "table": table, "svg": svg}
    meta["yandex-daily"] = {
        "path": None, "alt": None, "table": [],
        "unavailable_reason": "Яндекс.Вебмастер в текущем сборе не отдаёт дневной ряд показов/кликов "
                              "(используется endpoint popular queries с агрегатом за окно). "
                              "График будет построен после добавления выгрузки истории (тикет DATA-002).",
    }
    return meta


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    snap = json.loads((SNAP_DIR / f"{date}.json").read_text(encoding="utf-8"))
    meta = build_all(snap, date)
    built = [k for k, v in meta.items() if v.get("path")]
    print(f"charts: построено {len(built)} — {', '.join(built)}; "
          f"не построено: yandex-daily (нет дневного ряда)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
