#!/usr/bin/env python3
"""Визуализации письма V4: спарклайны, вклад драйверов, таймлайн эксперимента.

Правила: без заголовка внутри изображения, без легенды для одной серии, прямые
подписи, не более трёх цветов, белый фон, минимальная сетка, экспорт 2x,
отображаемая высота не выше 220 px, читаемость при ширине 375 px.

График не создаётся, если он лишь повторяет два числа: изменение Google
19 → 31 живёт в KPI-карточке как slope-мини-график, а не как отдельная диаграмма.

Запуск: как модуль из report_v4.py
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from textfmt import num, signed  # noqa: E402

OUT = pathlib.Path("reports/seo/intelligence/charts")
RENDER = pathlib.Path("scripts/seo/render.mjs")

INK = "#101828"
MUTED = "#667085"
BORDER = "#EAECF0"
POSITIVE = "#12B76A"
DANGER = "#D92D20"
BRAND = "#F4511E"


def _page(body: str, width: int, height: int) -> str:
    return (f"<html><head><meta charset='utf-8'><style>"
            f"*{{margin:0;padding:0;box-sizing:border-box}}"
            f"body{{width:{width}px;height:{height}px;background:#fff;"
            f"font:400 12px/1.35 -apple-system,'Segoe UI',Roboto,Arial,sans-serif;"
            f"color:{INK};}}</style></head><body>{body}</body></html>")


def sparkline_svg(values: list[float], width: int, height: int, colour: str) -> str:
    """Минимальный спарклайн: одна линия без осей, сетки и подписей."""
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = width / (len(values) - 1)
    pts = " ".join(
        f"{i * step:.1f},{height - 2 - (v - lo) / span * (height - 4):.1f}"
        for i, v in enumerate(values))
    last_x = width
    last_y = height - 2 - (values[-1] - lo) / span * (height - 4)
    return (f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}' "
            f"xmlns='http://www.w3.org/2000/svg'>"
            f"<polyline points='{pts}' fill='none' stroke='{colour}' stroke-width='2' "
            f"stroke-linejoin='round' stroke-linecap='round'/>"
            f"<circle cx='{last_x - 1.5:.1f}' cy='{last_y:.1f}' r='2.5' fill='{colour}'/>"
            f"</svg>")


def slope_html(prev_label: str, prev_value: int, cur_label: str, cur_value: int,
               width: int) -> str:
    """Мини-график «было → стало» внутри KPI-карточки: два столбика, прямые подписи."""
    hi = max(prev_value, cur_value) or 1
    h = 46
    bar = lambda v, c: (f"<div style='width:26px;height:{max(3, round(v / hi * h))}px;"
                        f"background:{c};border-radius:3px 3px 0 0;'></div>")
    up = cur_value >= prev_value
    colour = POSITIVE if up else DANGER
    return _page(
        f"<div style='display:flex;align-items:flex-end;gap:14px;height:{h + 18}px;'>"
        f"<div style='display:flex;flex-direction:column;align-items:center;gap:3px;'>"
        f"{bar(prev_value, '#D0D5DD')}"
        f"<span style='font-size:11px;color:{MUTED};'>{prev_label}</span></div>"
        f"<div style='display:flex;flex-direction:column;align-items:center;gap:3px;'>"
        f"{bar(cur_value, colour)}"
        f"<span style='font-size:11px;color:{MUTED};'>{cur_label}</span></div>"
        f"<div style='padding-bottom:16px;font-size:13px;color:{INK};'>"
        f"{num(prev_value)} → <b>{num(cur_value)}</b></div></div>",
        width, h + 20)


def contribution_html(rows: list[dict], width: int) -> str:
    """Горизонтальный вклад драйверов: доля каждого в общем изменении."""
    if not rows:
        return ""
    top = max(abs(r["delta"]) for r in rows) or 1
    bars = []
    for r in rows:
        w = round(abs(r["delta"]) / top * (width - 250))
        colour = POSITIVE if r["delta"] > 0 else DANGER
        bars.append(
            f"<div style='display:flex;align-items:center;gap:10px;height:24px;'>"
            f"<div style='width:190px;font-size:12.5px;color:{INK};overflow:hidden;"
            f"text-overflow:ellipsis;white-space:nowrap;'>{r['entity']}</div>"
            f"<div style='width:{max(4, w)}px;height:12px;background:{colour};"
            f"border-radius:3px;'></div>"
            f"<div style='font-size:12.5px;color:{MUTED};white-space:nowrap;'>"
            f"{signed(r['delta'])} · {round(r['share_of_total_delta'] * 100)}%</div></div>")
    height = 24 * len(rows) + 8
    return _page("<div style='display:flex;flex-direction:column;gap:0;'>"
                 + "".join(bars) + "</div>", width, height)


def timeline_html(exp: dict, width: int) -> str:
    """Таймлайн эксперимента: внедрение, минимальная экспозиция, контрольная дата."""
    done = min(1.0, exp["days_elapsed"] / 7) if exp.get("days_elapsed") is not None else 0
    filled = round((width - 40) * done)
    return _page(
        f"<div style='padding:4px 0;'>"
        f"<div style='position:relative;height:10px;background:{BORDER};border-radius:5px;'>"
        f"<div style='position:absolute;left:0;top:0;height:10px;width:{filled}px;"
        f"background:{BRAND};border-radius:5px;'></div></div>"
        f"<div style='display:flex;justify-content:space-between;margin-top:6px;"
        f"font-size:11.5px;color:{MUTED};'>"
        f"<span>внедрение {exp['start'][8:10]}.{exp['start'][5:7]}</span>"
        f"<span>прошло {exp['days_elapsed']} из 7 дней</span>"
        f"<span>проверка {exp['next_review'][8:10]}.{exp['next_review'][5:7]}</span>"
        f"</div></div>", width, 42)


def render(jobs: list[dict]) -> None:
    if not jobs:
        return
    manifest = OUT / "_v4-manifest.json"
    OUT.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["node", str(RENDER), str(manifest)], check=True)
    manifest.unlink(missing_ok=True)


def build(date: str, kpis: list[dict], drivers_rows: list[dict],
          experiment: dict | None) -> dict:
    """Готовит до трёх изображений и возвращает их описания для письма."""
    OUT.mkdir(parents=True, exist_ok=True)
    jobs, charts = [], {}

    slope = next((k for k in kpis if k.get("slope")), None)
    if slope:
        s = slope["slope"]
        for tag, w in (("", 300), ("-mobile", 330)):
            jobs.append({"html": slope_html(s["prev_label"], s["prev"], s["cur_label"],
                                            s["cur"], w),
                         "out": str(OUT / f"{date}-kpi-slope{tag}.png"),
                         "width": w, "height": 66, "dsf": 2, "fullPage": True})
        charts["kpi-slope"] = {
            "file": f"{date}-kpi-slope.png", "mobile": f"{date}-kpi-slope-mobile.png",
            "cid": "chart-kpi-slope", "display_width": 300, "max_height": 70,
            "alt": f"{slope['label']}: {num(s['prev'])} → {num(s['cur'])}",
            "fallback": f"{slope['label']}: {num(s['prev'])} → {num(s['cur'])}."}

    if drivers_rows:
        for tag, w in (("", 610), ("-mobile", 335)):
            jobs.append({"html": contribution_html(drivers_rows, w),
                         "out": str(OUT / f"{date}-drivers{tag}.png"),
                         "width": w, "height": 24 * len(drivers_rows) + 10,
                         "dsf": 2, "fullPage": True})
        charts["drivers"] = {
            "file": f"{date}-drivers.png", "mobile": f"{date}-drivers-mobile.png",
            "cid": "chart-drivers", "display_width": 610,
            "max_height": 24 * len(drivers_rows) + 10,
            "alt": "Вклад страниц в изменение показов",
            "fallback": "; ".join(f"{r['entity']} {signed(r['delta'])}"
                                  for r in drivers_rows)}

    if experiment:
        for tag, w in (("", 610), ("-mobile", 335)):
            jobs.append({"html": timeline_html(experiment, w),
                         "out": str(OUT / f"{date}-experiment{tag}.png"),
                         "width": w, "height": 46, "dsf": 2, "fullPage": True})
        charts["experiment"] = {
            "file": f"{date}-experiment.png", "mobile": f"{date}-experiment-mobile.png",
            "cid": "chart-experiment", "display_width": 610, "max_height": 50,
            "alt": f"Ход эксперимента: {experiment['days_elapsed']} из 7 дней",
            "fallback": f"Прошло {experiment['days_elapsed']} из 7 дней, "
                        f"проверка {experiment['next_review']}."}

    render(jobs)
    return charts
