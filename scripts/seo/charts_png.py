#!/usr/bin/env python3
"""PNG-графики письма V3 (рендер через Playwright, без inline SVG в письме).

Два визуальных блока:
  1. google-wow  — Google неделя к неделе (единственный аналитический график);
  2. measure-map — карта измерения: источники и явный разрыв сопоставимости.

Каждый PNG отдаётся в 2x, ширина отображения 610 px.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

OUT_DIR = pathlib.Path("reports/seo/intelligence/charts")
DISPLAY_W = 610
INK, MUTED, LINE = "#1d1d1f", "#5c5c66", "#e3e3e8"
ACCENT, GOOD, WARN = "#f2591d", "#1a8f4c", "#b26a00"
BASE_CSS = (
    "margin:0;padding:0;background:#ffffff;"
    "font-family:-apple-system,'Segoe UI',Arial,Helvetica,sans-serif;"
    f"color:{INK};-webkit-font-smoothing:antialiased;"
)


def google_wow_html(cur: int, prev: int, cur_period: str, prev_period: str,
                    absolute: int, relative: float) -> str:
    rel_txt = f"+{relative:.1f}".replace(".", ",") + "%"
    mx = max(cur, prev, 1)
    h_cur, h_prev = int(150 * cur / mx), int(150 * prev / mx)
    return f"""<html><body style="{BASE_CSS}"><div style="width:{DISPLAY_W}px;padding:18px 20px;box-sizing:border-box;">
<div style="font-size:17px;font-weight:700;">Google: показы неделя к неделе</div>
<div style="font-size:13px;color:{MUTED};padding-top:4px;">Источник: Google Search Console · показы за 7 дней</div>
<table style="border-collapse:collapse;margin-top:18px;"><tr>
<td style="vertical-align:bottom;padding-right:34px;text-align:center;">
  <div style="font-size:20px;font-weight:700;color:{MUTED};padding-bottom:6px;">{prev}</div>
  <div style="width:104px;height:{h_prev}px;background:{LINE};border-radius:6px 6px 0 0;"></div>
  <div style="font-size:13px;color:{MUTED};padding-top:8px;">{prev_period}</div>
</td>
<td style="vertical-align:bottom;padding-right:30px;text-align:center;">
  <div style="font-size:20px;font-weight:700;color:{ACCENT};padding-bottom:6px;">{cur}</div>
  <div style="width:104px;height:{h_cur}px;background:{ACCENT};border-radius:6px 6px 0 0;"></div>
  <div style="font-size:13px;color:{MUTED};padding-top:8px;">{cur_period}</div>
</td>
<td style="vertical-align:middle;">
  <div style="font-size:26px;font-weight:700;color:{GOOD};">+{absolute}</div>
  <div style="font-size:17px;color:{GOOD};padding-top:2px;">{rel_txt}</div>
  <div style="display:inline-block;margin-top:10px;padding:4px 9px;border:1px solid {WARN};
       border-radius:5px;font-size:12.5px;color:{WARN};font-weight:600;">низкая база</div>
</td></tr></table>
<div style="font-size:12.5px;color:{MUTED};padding-top:14px;line-height:1.45;">
Обе недели измерены за 7 дней. Абсолютные значения малы, поэтому изменение — ранний сигнал, а не тренд.</div>
</div></body></html>"""


def measure_map_html(yx_imp: int, yx_clicks: int, yx_queries: int, yx_period: str,
                     visits: int, events: int, an_period: str) -> str:
    card = ("border:1px solid " + LINE + ";border-radius:10px;padding:13px 15px;"
            "box-sizing:border-box;width:100%;")
    return f"""<html><body style="{BASE_CSS}"><div style="width:{DISPLAY_W}px;padding:18px 20px;box-sizing:border-box;">
<div style="font-size:17px;font-weight:700;">Карта измерения</div>
<div style="font-size:13px;color:{MUTED};padding-top:4px;">Что каким источником измерено. Сквозная воронка не строится: сверка не завершена.</div>
<div style="{card}margin-top:14px;">
  <div style="font-size:13px;color:{MUTED};">Яндекс.Вебмастер · {yx_period}</div>
  <div style="font-size:16px;padding-top:5px;"><b>{yx_imp}</b> показов → <b>{yx_clicks}</b> кликов
  <span style="color:{MUTED};font-size:13.5px;">· выборка {yx_queries} запросов</span></div>
</div>
<div style="text-align:center;padding:9px 0;">
  <div style="border-top:2px dashed {WARN};margin:0 30px;"></div>
  <div style="display:inline-block;margin-top:-11px;background:#fff;padding:0 10px;font-size:12.5px;color:{WARN};font-weight:600;">
    ✕ охват и периоды не сопоставлены</div>
</div>
<div style="{card}">
  <div style="font-size:13px;color:{MUTED};">Яндекс.Метрика · {an_period}</div>
  <div style="font-size:16px;padding-top:5px;"><b>{visits}</b> визитов из поиска → <b>{events}</b> целевых события</div>
</div>
<div style="{card}margin-top:9px;background:#fafafb;">
  <div style="font-size:13px;color:{MUTED};">CRM</div>
  <div style="font-size:16px;padding-top:5px;color:{MUTED};">нет данных — заявки, сделки и выручка не измеряются</div>
</div>
</div></body></html>"""


def build(snap: dict, date: str) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    g, yx = snap["google"], snap["yandex"]
    m = snap["analytics"]["metrika"]
    t = g["totals"]
    cur, prev = t["impressions_last7"], t["impressions_prev7"]
    absolute = cur - prev
    relative = (absolute / prev * 100) if prev else 0.0

    def ru(d: str) -> str:
        return f"{d[8:10]}.{d[5:7]}"

    charts = {
        "google-wow": {
            "html": google_wow_html(cur, prev, f"{ru(t['last7_start'])}–{ru(t['last7_end'])}",
                                    f"{ru(t['prev7_start'])}–{ru(t['prev7_end'])}", absolute, relative),
            "alt": (f"Столбчатая диаграмма: показы Google выросли с {prev} до {cur} за неделю, "
                    f"изменение +{absolute} (+{relative:.1f}%), низкая база".replace(".", ",")),
            "fallback": f"Показы Google за неделю: {prev} → {cur} (+{absolute}); база низкая.",
        },
        "measure-map": {
            "html": measure_map_html(
                yx["totals"]["impressions"], yx["totals"]["clicks"], yx["totals"]["queries_tracked"],
                f"{ru(yx['source']['current_period_start'])}–{ru(yx['source']['current_period_end'])}",
                int(m["organic_visits"]), int(m["organic_goal_events"]),
                f"{ru(m['source']['current_period_start'])}–{ru(m['source']['current_period_end'])}"),
            "alt": ("Карта измерения: Вебмастер 926 показов и 6 кликов по выборке 100 запросов; "
                    "Метрика 37 визитов из поиска и 3 целевых события; CRM без данных; "
                    "между источниками разрыв сопоставимости"),
            "fallback": "Источники измеряют разное и за разные периоды — сквозная воронка не строится.",
        },
    }
    jobs = []
    for name, c in charts.items():
        out = OUT_DIR / f"{date}-{name}.png"
        c["path"] = str(out)
        c["file"] = f"{date}-{name}.png"
        c["cid"] = f"chart-{name}"
        jobs.append({"html": c["html"], "out": str(out), "width": DISPLAY_W, "height": 60,
                     "dsf": 2, "fullPage": True})
    manifest = OUT_DIR / f".render-{date}.json"
    manifest.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["node", "scripts/seo/render.mjs", str(manifest)], check=True)
    manifest.unlink(missing_ok=True)
    for c in charts.values():
        c.pop("html", None)
    return charts


if __name__ == "__main__":
    d = sys.argv[1]
    s = json.loads(pathlib.Path(f"reports/seo/intelligence/snapshots/{d}.json").read_text(encoding="utf-8"))
    print(json.dumps({k: v["path"] for k, v in build(s, d).items()}, ensure_ascii=False))
