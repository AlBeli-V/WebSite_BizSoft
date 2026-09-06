#!/usr/bin/env python3
"""Визуализации письма V4 на компонентах KPI-kit (scripts/viz/kpi_kit.py).

Три изображения, не больше (uxlint `charts` ≤ 3, высота ≤ 220 px):

  * kpi-trend — показатель по дням: текущая неделя цветом источника, прошлая
    серым контекстом; вкладывается в плитку того показателя, по которому
    построен. Без дневных рядов — «было → стало» двумя столбиками;
  * drivers — вклад страниц в изменение показов, полосы вправо/влево;
  * experiment — таймлайн эксперимента.

Правила: без заголовка внутри изображения, легенда только при двух сериях,
прямые подписи, цвета серий закреплены за источниками, белый фон, экспорт 2x,
отображаемая высота не выше 220 px, читаемость при ширине 375 px.
График не создаётся, если он лишь повторяет два числа.

Запуск: как модуль из report_v4.py
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "viz"))
import kpi_kit as kit  # noqa: E402
from textfmt import num, signed  # noqa: E402

OUT = pathlib.Path("reports/seo/intelligence/charts")
RENDER = pathlib.Path("scripts/seo/render.mjs")

INK = kit.LIGHT["ink"]
MUTED = kit.LIGHT["muted"]
BORDER = kit.LIGHT["hair"]
POSITIVE = kit.LIGHT["good"]
DANGER = kit.LIGHT["crit"]
BRAND = kit.LIGHT["accent"]

WINDOW = 7


def _page(body: str, width: int, height: int) -> str:
    return kit.png_document(body, width, height)


def sparkline_svg(values: list[float], width: int, height: int, colour: str) -> str:
    """Спарклайн KPI-kit: одна линия без осей, кольцо на последнем значении."""
    return kit.sparkline(values, colour, width, height, hex_mode=True)


def _week_labels(start: str | None, n: int) -> list[str]:
    if not start:
        return [f"д{i + 1}" for i in range(n)]
    d0 = dt.date.fromisoformat(start)
    return [f"{(d0 + dt.timedelta(days=i)).day:02d}.{(d0 + dt.timedelta(days=i)).month:02d}"
            for i in range(n)]


def trend_html(kpi: dict, width: int) -> str:
    """Неделя к неделе по дням: текущее окно цветом источника, прошлое — серым."""
    tail = list(kpi.get("sparkline") or [])
    prev, cur = tail[:WINDOW], tail[WINDOW:WINDOW * 2]
    start = kpi.get("sparkline_from")
    cur_start = None
    if start:
        cur_start = (dt.date.fromisoformat(start) + dt.timedelta(days=WINDOW)).isoformat()
    labels = _week_labels(cur_start, len(cur))
    colour = kit.series_color(kpi.get("key", "yandex"), hex_mode=True)
    chart = kit.line_chart(
        [{"name": "эта неделя", "values": cur, "color": colour},
         {"name": "прошлая неделя", "values": prev, "context": True}],
        labels, w=width, h=140, ticks=3, area=True, title=kpi["label"], hex_mode=True)
    return _page(chart, width, 160)


def slope_html(prev_label: str, prev_value: int, cur_label: str, cur_value: int,
               width: int) -> str:
    """Мини-график «было → стало» внутри KPI-плитки: два столбика, прямые подписи."""
    hi = max(prev_value, cur_value) or 1
    h = 46
    bar = lambda v, c: (f"<div style='width:24px;height:{max(3, round(v / hi * h))}px;"  # noqa: E731
                        f"background:{c};border-radius:4px 4px 0 0;'></div>")
    colour = POSITIVE if cur_value >= prev_value else DANGER
    return _page(
        f"<div style='display:flex;align-items:flex-end;gap:14px;height:{h + 18}px;'>"
        f"<div style='display:flex;flex-direction:column;align-items:center;gap:3px;'>"
        f"{bar(prev_value, kit.LIGHT['gray'])}"
        f"<span style='font-size:11px;color:{MUTED};'>{prev_label}</span></div>"
        f"<div style='display:flex;flex-direction:column;align-items:center;gap:3px;'>"
        f"{bar(cur_value, colour)}"
        f"<span style='font-size:11px;color:{MUTED};'>{cur_label}</span></div>"
        f"<div style='padding-bottom:16px;font-size:13px;color:{INK};'>"
        f"{num(prev_value)} → <b>{num(cur_value)}</b></div></div>",
        width, h + 20)


def contribution_html(rows: list[dict], width: int) -> str:
    """Вклад драйверов: полосы от общей оси, рост вправо, снижение влево (KPI-kit)."""
    if not rows:
        return ""
    body = kit.delta_bars(rows, hex_mode=True)
    if width < 400:
        body = body.replace('class="kit-db-row"',
                            'class="kit-db-row" style="grid-template-columns:120px 1fr 70px"')
    return _page(body, width, 24 * len(rows) + 8)


def timeline_html(exp: dict, width: int) -> str:
    """Таймлайн эксперимента: внедрение, минимальная экспозиция, контрольная дата."""
    done = min(1.0, exp["days_elapsed"] / 7) if exp.get("days_elapsed") is not None else 0
    filled = round((width - 40) * done)
    return _page(
        f"<div style='padding:4px 0;'>"
        f"<div style='position:relative;height:10px;background:{kit.LIGHT['q1']};border-radius:5px;'>"
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


def _trend_candidate(kpis: list[dict]) -> dict | None:
    """Показатель для графика по дням: полный двухнедельный ряд, Яндекс первым."""
    ordered = sorted(kpis, key=lambda k: 0 if k.get("key") == "yandex" else 1)
    for k in ordered:
        tail = [v for v in (k.get("sparkline") or [])]
        if len(tail) >= WINDOW * 2 and sum(v is not None for v in tail[:WINDOW]) >= 2 \
                and sum(v is not None for v in tail[WINDOW:WINDOW * 2]) >= 2:
            return k
    return None


def build(date: str, kpis: list[dict], drivers_rows: list[dict],
          experiment: dict | None) -> dict:
    """Готовит до трёх изображений и возвращает их описания для письма."""
    OUT.mkdir(parents=True, exist_ok=True)
    jobs, charts = [], {}

    trend = _trend_candidate(kpis)
    slope = next((k for k in kpis if k.get("slope")), None)
    if trend:
        tail = trend["sparkline"]
        cur = sum(v for v in tail[WINDOW:WINDOW * 2] if v is not None)
        prev = sum(v for v in tail[:WINDOW] if v is not None)
        for tag, w in (("", 300), ("-mobile", 330)):
            jobs.append({"html": trend_html(trend, w),
                         "out": str(OUT / f"{date}-kpi-trend{tag}.png"),
                         "width": w, "height": 160, "dsf": 2, "fullPage": True})
        charts["kpi-trend"] = {
            "file": f"{date}-kpi-trend.png", "mobile": f"{date}-kpi-trend-mobile.png",
            "cid": "chart-kpi-trend", "display_width": 300, "max_height": 160,
            "kpi_key": trend.get("key"),
            "alt": f"{trend['label']} по дням: неделя {num(cur)} против {num(prev)}",
            "fallback": f"По дням: эта неделя {num(cur)}, прошлая {num(prev)}."}
    elif slope:
        s = slope["slope"]
        for tag, w in (("", 300), ("-mobile", 330)):
            jobs.append({"html": slope_html(s["prev_label"], s["prev"], s["cur_label"],
                                            s["cur"], w),
                         "out": str(OUT / f"{date}-kpi-trend{tag}.png"),
                         "width": w, "height": 66, "dsf": 2, "fullPage": True})
        charts["kpi-trend"] = {
            "file": f"{date}-kpi-trend.png", "mobile": f"{date}-kpi-trend-mobile.png",
            "cid": "chart-kpi-trend", "display_width": 300, "max_height": 70,
            "kpi_key": slope.get("key"),
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
            "max_height": min(220, 24 * len(drivers_rows) + 10),
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
