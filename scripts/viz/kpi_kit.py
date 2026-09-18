#!/usr/bin/env python3
"""KPI-kit — единый визуальный слой отчётов biz-soft.pro.

Один набор компонентов обслуживает обе поверхности и оба контура:

  * веб-страница (SEO Growth Intelligence, конкурентная разведка) — живые
    компоненты: плитки KPI со спарклайнами и углублением по клику, светофор
    целей, «одна цифра» с разложением, теплокарта по дням, малые кратные,
    таблица-дашборд с сортировкой;
  * письмо — те же плитки и светофор на табличной вёрстке без картинок, а
    графики — те же SVG, отрисованные в PNG через scripts/seo/render.mjs.

Правила (docs/rules/kpi-kit.md): одна ось на график; серия = сущность
(Яндекс — синий, Google — фирменный оранжевый, аналитика — зелёный);
статусные цвета отдельно от серий и всегда с глифом; легенда при двух и
более сериях; прямые подписи только у конца ряда; тонкие марки, тонкая
сетка; у каждого графика есть табличный двойник или подпись с числами.

Только стандартная библиотека. Компоненты возвращают строки HTML/SVG.
Палитра проверена валидатором dataviz (CVD ΔE ≥ 9 между соседними сериями).
"""

from __future__ import annotations

import html
import json
import math

# ── Палитра ──────────────────────────────────────────────────────────────────

LIGHT = {
    "plane": "#f5f5f7", "surface": "#ffffff", "surface2": "#fafafb",
    "ink": "#1d1d1f", "ink2": "#3f3f46", "muted": "#6e6e78",
    "hair": "#e8e8ed", "hair2": "#d2d2d7",
    "accent": "#f2591d", "accent_ink": "#b8420f", "accent_soft": "#fff2ec",
    "s1": "#2a78d6", "s2": "#f2591d", "s3": "#1baf7a", "s4": "#4a3aa7",
    "gray": "#c3c2c7",
    "good": "#1a8f4c", "good_soft": "#e6f4ec",
    "warn": "#b97a00", "warn_soft": "#fff5dc",
    "crit": "#d92d20", "crit_soft": "#fdecea",
    "hero": "#1d1d1f", "hero_ink": "#ffffff", "hero_muted": "#a0a0a8",
    "q1": "#e3eefc", "q2": "#b7d3f6", "q3": "#86b6ef", "q4": "#5598e7",
    "q5": "#2a78d6", "q6": "#1c5cab", "q7": "#0d366b",
}
DARK = {
    **LIGHT,
    "plane": "#0f0f11", "surface": "#1b1b1e", "surface2": "#202024",
    "ink": "#f5f5f7", "ink2": "#c9c9cf", "muted": "#9a9aa4",
    "hair": "#2c2c31", "hair2": "#3d3d44",
    "accent_ink": "#ff8a5b", "accent_soft": "#3a2418",
    "s1": "#3987e5", "s3": "#199e70", "s4": "#9085e9", "gray": "#4a4a52",
    "good": "#3dbb6e", "good_soft": "#12301c",
    "warn": "#e0a020", "warn_soft": "#332a10",
    "crit": "#ef5a50", "crit_soft": "#3a1a18",
    "hero": "#0b0b0c",
    "q1": "#1b2a40", "q2": "#184f95", "q3": "#1c5cab", "q4": "#2a78d6",
    "q5": "#3987e5", "q6": "#6da7ec", "q7": "#9ec5f4",
}

# Серия = сущность. Цвет закреплён за источником, а не за порядком в списке.
SERIES = {"yandex": "s1", "google": "s2", "metrika": "s3", "ga4": "s4",
          "ours": "s1", "rival": "s2", "other": "gray"}

FONT_SANS = ("'Raleway',-apple-system,BlinkMacSystemFont,system-ui,'Segoe UI',"
             "Roboto,Helvetica,Arial,sans-serif")
EMAIL_FONT = "Arial,Helvetica,sans-serif"
FONTS_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
              '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
              '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
              'family=Raleway:wght@400;500;600;700&display=swap">')


def tok(name: str, hex_mode: bool = False) -> str:
    """Цвет по имени: CSS-переменная для страницы, hex — для PNG и письма."""
    return LIGHT[name] if hex_mode else f"var(--kit-{name.replace('_', '-')})"


def series_color(source: str, hex_mode: bool = False) -> str:
    return tok(SERIES.get(source, "s1"), hex_mode)


# ── Форматирование ───────────────────────────────────────────────────────────

def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def num(value) -> str:
    """Число по-русски: неразрывный узкий пробел между разрядами, запятая."""
    if value is None:
        return "—"
    if isinstance(value, float) and not value.is_integer():
        s = f"{value:,.2f}".rstrip("0").rstrip(".")
    else:
        s = f"{int(round(value)):,}"
    return s.replace(",", " ").replace(".", ",")


def signed(value, unit: str = "") -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ("−" if value < 0 else "")
    return f"{sign}{num(abs(value))}{unit}"


def delta_dir(delta, good_up: bool = True) -> str | None:
    if delta is None:
        return None
    if abs(delta) < 1e-9:
        return "flat"
    return "up" if (delta > 0) == good_up else "down"


def _nice_max(v: float) -> float:
    if v <= 0:
        return 1.0
    p = 10 ** math.floor(math.log10(v))
    m = v / p
    n = 1 if m <= 1 else 2 if m <= 2 else 2.5 if m <= 2.5 else 5 if m <= 5 else 10
    return n * p


def _clean(values) -> list[float]:
    return [float(v) for v in values if v is not None]


# ── SVG-примитивы ────────────────────────────────────────────────────────────

def sparkline(values, color: str | None = None, w: int = 96, h: int = 28,
              hex_mode: bool = False) -> str:
    """Спарклайн: одна линия без осей, кольцо-точка на последнем значении."""
    vals = _clean(values)
    if len(vals) < 2:
        return ""
    color = color or tok("s1", hex_mode)
    ring = tok("surface", hex_mode)
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    # Поле по краям: кольцо последней точки (r 3,5 + обводка 2) целиком внутри
    # viewBox. Без него svg срезал половину точки и линия обрывалась о рамку.
    pad = 5.0
    step = (w - 2 * pad) / (len(vals) - 1)
    pts = [(pad + i * step, h - pad - (v - lo) / span * (h - 2 * pad))
           for i, v in enumerate(vals)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    lx, ly = pts[-1]
    return (f'<svg class="kit-spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'aria-hidden="true"><polyline points="{poly}" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3.5" fill="{color}" '
            f'stroke="{ring}" stroke-width="2"/></svg>')


def line_chart(series: list[dict], labels: list[str], w: int = 640, h: int = 200,
               ticks: int = 4, y_min: float = 0, area: bool = False,
               title: str = "", hex_mode: bool = False, fmt=num) -> str:
    """Линейный график: одна шкала, тонкая сетка, подпись у конца ряда.

    series: [{"name", "values", "color"?, "context": bool}]; контекстная серия
    (прошлый период) рисуется серым тоньше и без подписи. labels — подписи
    оси X той же длины, что и ряды; печатаются пять равномерных.
    На странице график получает crosshair-тултип: данные лежат в
    data-kit-line, их читает kit_js().
    """
    n = max((len(s["values"]) for s in series), default=0)
    if n < 2:
        return ""
    pad_l, pad_r, pad_t, pad_b = 44, 56, 12, 26
    iw, ih = w - pad_l - pad_r, h - pad_t - pad_b
    all_vals = [v for s in series for v in _clean(s["values"])]
    hi = max(all_vals) if all_vals else 1.0
    top = _nice_max(hi) if hi > y_min else y_min + 1
    if top <= y_min:
        top = y_min + 1
    # Деления шкалы — круглые: число делений подбирается так, чтобы шаг был
    # целым или половинным (50 → 5 делений по 10, а не 3 по 16,67).
    for t in (ticks, 5, 4, 2, 1):
        step = (top - y_min) / t
        if abs(step * 2 - round(step * 2)) < 1e-9:
            ticks = t
            break

    def X(i):
        return pad_l + i * iw / (n - 1)

    def Y(v):
        return pad_t + ih - (v - y_min) / (top - y_min) * ih

    ink, muted, hair, hair2, surf = (tok(k, hex_mode) for k in
                                     ("ink", "muted", "hair", "hair2", "surface"))
    g = []
    for t in range(ticks + 1):
        v = y_min + (top - y_min) * t / ticks
        y = Y(v)
        g.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{y:.1f}" y2="{y:.1f}" '
                 f'stroke="{hair}" stroke-width="1"/>'
                 f'<text x="{pad_l - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="11" '
                 f'fill="{muted}">{esc(fmt(round(v, 2)))}</text>')
    xt = sorted({0, n // 4, n // 2, 3 * n // 4, n - 1})
    for i in xt:
        if i < len(labels):
            g.append(f'<text x="{X(i):.1f}" y="{h - 8}" text-anchor="middle" font-size="11" '
                     f'fill="{muted}">{esc(labels[i])}</text>')
    paths = []
    for s in series:
        vals = s["values"]
        color = s.get("color") or (tok("gray", hex_mode) if s.get("context")
                                   else tok("s1", hex_mode))
        d, prev_none = [], True
        for i, v in enumerate(vals):
            if v is None:
                prev_none = True
                continue
            d.append(f"{'M' if prev_none else 'L'}{X(i):.1f} {Y(float(v)):.1f}")
            prev_none = False
        if not d:
            continue
        if area and not s.get("context"):
            first = next(i for i, v in enumerate(vals) if v is not None)
            last_i = max(i for i, v in enumerate(vals) if v is not None)
            paths.append(f'<path d="{" ".join(d)} L{X(last_i):.1f} {Y(y_min):.1f} '
                         f'L{X(first):.1f} {Y(y_min):.1f} Z" fill="{color}" opacity=".10"/>')
        paths.append(f'<path d="{" ".join(d)}" fill="none" stroke="{color}" '
                     f'stroke-width="{1.5 if s.get("context") else 2}" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        if not s.get("context"):
            last_i = max(i for i, v in enumerate(vals) if v is not None)
            lx, ly = X(last_i), Y(float(vals[last_i]))
            label = fmt(vals[last_i])
            # Подпись конца ряда живёт в правом поле (pad_r). Широкое число
            # там не помещается, а svg обрезает всё, что вышло за viewBox, —
            # подпись молча исчезала бы. Не влезает справа — печатается слева
            # от точки. Ширина оценивается по числу знаков: 12 px моноширинных
            # цифр — около 7 px на знак.
            side_right = lx + 8 + len(label) * 7.0 <= w - 2
            paths.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4" fill="{color}" '
                         f'stroke="{surf}" stroke-width="2"/>'
                         f'<text x="{lx + 8 if side_right else lx - 8:.1f}" '
                         f'y="{ly + 4:.1f}" font-size="12" '
                         f'text-anchor="{"start" if side_right else "end"}" '
                         f'font-weight="600" fill="{ink}">{esc(label)}</text>')
    data = {"labels": list(labels), "pad": [pad_l, pad_r, pad_t, pad_b], "w": w, "h": h,
            "ymin": y_min, "top": top,
            "series": [{"name": s["name"], "values": s["values"],
                        "color": s.get("color") or (tok("gray", hex_mode) if s.get("context")
                                                    else tok("s1", hex_mode))}
                       for s in series]}
    legend = ""
    named = [s for s in series]
    if len(named) >= 2:
        legend = '<div class="kit-legend">' + "".join(
            f'<span><i style="background:{s.get("color") or (tok("gray", hex_mode) if s.get("context") else tok("s1", hex_mode))}"></i>{esc(s["name"])}</span>'
            for s in named) + "</div>"
    return (f'<div class="kit-chart">{legend}<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{esc(title)}" data-kit-line=\'{esc(json.dumps(data, ensure_ascii=False))}\'>'
            + "".join(g)
            + f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{Y(y_min):.1f}" y2="{Y(y_min):.1f}" '
              f'stroke="{hair2}" stroke-width="1"/>'
            + "".join(paths) + "</svg></div>")


# ── Плитки KPI (страница) ────────────────────────────────────────────────────

def delta_html(text: str | None, direction: str | None) -> str:
    """Дельта плитки: стрелка неразрывно приклеена к первому числу.

    Внутри плитки дельта состоит из двух чисел («+3486 +157,6%»). Пробел
    между ними — единственное место, где строку можно перенести; стрелка от
    своего числа не отрывается, поэтому после неё стоит U+00A0.
    """
    if not text:
        return ""
    arrow = {"up": "▲\u00a0", "down": "▼\u00a0", "flat": "→\u00a0"}.get(direction or "", "")
    return f'<span class="kit-delta {direction or "flat"}">{arrow}{esc(text)}</span>'


def stat_tile(label: str, value: str, unit: str = "", delta: str | None = None,
              direction: str | None = None, spark=None, color: str | None = None,
              note: str = "", meta: str = "", key: str = "", active: bool = False,
              muted: bool = False) -> str:
    """Плитка KPI: подпись, число, дельта и спарклайн; note — одна строка смысла.

    key задаёт углубление: клик по плитке показывает панель с тем же
    data-kit-panel внутри ближайшего .kit-dash (см. kit_js()).
    """
    tag = "button" if key else "div"
    attrs = (f' data-kit-key="{esc(key)}" aria-pressed="{"true" if active else "false"}"'
             if key else "")
    spark_html = sparkline(spark, color) if spark else ""
    return (f'<{tag} class="kit-tile{" kit-active" if active else ""}{" kit-muted" if muted else ""}"{attrs}>'
            f'<span class="kit-lbl">{esc(label)}</span>'
            f'<span class="kit-val">{esc(value)}{f"<small>{esc(unit)}</small>" if unit else ""}</span>'
            + (f'<span class="kit-note">{note}</span>' if note else "")
            + f'<span class="kit-sub">{delta_html(delta, direction)}{spark_html}</span>'
            + (f'<span class="kit-meta">{meta}</span>' if meta else "")
            + f'</{tag}>')


def kpi_row(tiles: list[str]) -> str:
    return f'<div class="kit-row">{"".join(tiles)}</div>'


def panel(key: str, body: str, active: bool = False) -> str:
    """Панель углубления под рядом плиток; открыта только активная."""
    return (f'<div class="kit-panel" data-kit-panel="{esc(key)}"'
            f'{"" if active else " hidden"}>{body}</div>')


def dash(head: str, body: str, title: str = "", period: str = "") -> str:
    """Контейнер дашборда: заголовок, период, ряд плиток и панели."""
    t = (f'<div class="kit-dash-title"><h3>{esc(title)}</h3>'
         f'<span class="kit-period">{esc(period)}</span></div>' if title else "")
    return f'<div class="kit-dash">{t}{head}{body}</div>'


# ── Светофор целей ───────────────────────────────────────────────────────────

STATE_GLYPH = {"good": "✓", "warn": "!", "crit": "×", "neutral": "·"}
STATE_TITLE = {"good": "в норме", "warn": "внимание", "crit": "проблема",
               "neutral": "нет данных"}


def status_rows(rows: list[dict], head: bool = True) -> str:
    """Светофор: статус · KPI · факт · Δ · шкала до цели · что это значит.

    row: {"state": good|warn|crit|neutral, "name", "sub"?, "value", "delta"?,
          "direction"?, "progress"?: 0..1, "target"?: str, "comment"?}
    """
    out = []
    if head:
        out.append('<div class="kit-srow kit-shead"><span></span><span>KPI</span>'
                   '<span>Факт</span><span>Δ</span><span class="kit-m">До цели</span>'
                   '<span>Что это значит</span></div>')
    for r in rows:
        st = r.get("state", "neutral")
        prog = r.get("progress")
        meter = ""
        if prog is not None:
            p = max(0.0, min(1.0, float(prog))) * 100
            cap = r.get("target") or ""
            meter = (f'<span class="kit-meter" data-tip="{esc(f"{p:.0f}% от цели {cap}".strip())}">'
                     f'<b class="{st}" style="width:{p:.0f}%"></b></span>'
                     f'<span class="kit-meter-cap">{esc(cap)}</span>')
        out.append(
            f'<div class="kit-srow"><span class="kit-dot {st}" title="{STATE_TITLE[st]}">'
            f'{STATE_GLYPH[st]}</span>'
            f'<span class="kit-name">{esc(r["name"])}'
            + (f'<small>{esc(r["sub"])}</small>' if r.get("sub") else "")
            + f'</span><span class="kit-v">{esc(r.get("value", "—"))}</span>'
            f'<span>{delta_html(r.get("delta"), r.get("direction"))}</span>'
            f'<span class="kit-m kit-meter-wrap">{meter}</span>'
            f'<span class="kit-cmt">{r.get("comment", "")}</span></div>')
    return f'<div class="kit-status">{"".join(out)}</div>'


# ── Одна цифра и разложение ──────────────────────────────────────────────────

def hero(label: str, value: str, unit: str = "", delta: str = "", foot: str = "",
         hex_mode: bool = False) -> str:
    return (f'<div class="kit-hero"><div><div class="kit-hero-lbl">{esc(label)}</div>'
            f'<div class="kit-hero-big">{esc(value)}'
            + (f'<small>{esc(unit)}</small>' if unit else "")
            + f'</div>' + (f'<div class="kit-hero-delta">{esc(delta)}</div>' if delta else "")
            + '</div>' + (f'<div class="kit-hero-foot">{foot}</div>' if foot else "")
            + '</div>')


def waterfall(base_label: str, base: float, steps: list[tuple[str, float]],
              total_label: str, fmt=num, hex_mode: bool = False) -> str:
    """Разложение: базовая линия, шаги-вклады (вправо/влево), итог."""
    run = base
    levels = [base]
    for _, d in steps:
        run += d
        levels.append(run)
    top = max(levels + [base]) * 1.05 or 1.0
    px = lambda v: max(0.0, v) / top * 100  # noqa: E731
    rows = [(base_label, None, 0, px(base), tok("gray", hex_mode), fmt(base), "base")]
    run = base
    for label, d in steps:
        a, b = run, run + d
        color = tok("good" if d > 0 else "crit", hex_mode)
        rows.append((label, d, px(min(a, b)), px(abs(d)), color, signed(d), ""))
        run = b
    rows.append((total_label, None, 0, px(run), tok("s1", hex_mode), fmt(run), "total"))
    html_rows = "".join(
        f'<div class="kit-wf-row {kind}"><span class="kit-wf-lab">{esc(label)}</span>'
        f'<span class="kit-wf-track" data-tip="{esc(label)}: {esc(text)}">'
        f'<i class="kit-wf-zero" style="left:{px(base):.1f}%"></i>'
        f'<b style="left:{left:.1f}%;width:{max(width, 0.6):.1f}%;background:{color}"></b></span>'
        f'<span class="kit-wf-v">{esc(text)}</span></div>'
        for label, _, left, width, color, text, kind in rows)
    return f'<div class="kit-wf">{html_rows}</div>'


# ── Вклад драйверов: полосы от общей оси ─────────────────────────────────────

def delta_bars(rows: list[dict], hex_mode: bool = False, label: str = "entity",
               fmt=signed) -> str:
    """Полосы изменения по сущностям: рост вправо, снижение влево от одной оси.

    row: {"entity", "delta", "share_of_total_delta"?}. Одинаково рисуется на
    странице (классы, CSS-переменные) и в PNG для письма (hex через
    png_document, где подключён component_css()).
    """
    if not rows:
        return ""
    top = max(abs(float(r["delta"])) for r in rows) or 1.0
    good, crit, hair2 = tok("good", hex_mode), tok("crit", hex_mode), tok("hair2", hex_mode)
    out = []
    for r in rows:
        d = float(r["delta"])
        w = abs(d) / top * 50
        left = 50 if d > 0 else 50 - w
        share = r.get("share_of_total_delta")
        share_html = (f' <span class="kit-db-share">{round(share * 100)}%</span>'
                      if share is not None else "")
        out.append(
            f'<div class="kit-db-row"><span class="kit-db-lab">{esc(r[label])}</span>'
            f'<span class="kit-db-track"><i style="left:50%;background:{hair2}"></i>'
            f'<b style="left:{left:.1f}%;width:{max(w, 0.6):.1f}%;background:{good if d > 0 else crit};'
            f'border-radius:{"0 4px 4px 0" if d > 0 else "4px 0 0 4px"}"></b></span>'
            f'<span class="kit-db-v">{esc(fmt(d if not float(d).is_integer() else int(d)))}{share_html}</span></div>')
    return f'<div class="kit-db">{"".join(out)}</div>'


# ── Теплокарта по дням ───────────────────────────────────────────────────────

DOW = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def _dm(iso: str) -> str:
    return f"{iso[8:10]}.{iso[5:7]}"


def heatmap(dates: list[str], values: list, unit: str = "показов",
            hex_mode: bool = False) -> str:
    """Календарь-теплокарта: недели строками, дни столбцами, итог недели справа.

    dates — ISO-даты подряд (любой день недели в начале); None — нет данных.
    """
    import datetime as _dt
    if not dates:
        return ""
    first = _dt.date.fromisoformat(dates[0])
    offset = first.weekday()
    cells: list = [None] * offset + list(zip(dates, values))
    while len(cells) % 7:
        cells.append(None)
    vals = _clean(values)
    hi = max(vals) if vals else 0
    ramp = [tok(f"q{i}", hex_mode) for i in range(1, 8)]

    def step(v):
        return min(6, int(v / (hi + 1e-9) * 7)) if hi else 0

    # Сетка не ужимается ниже читаемого размера (min-width в CSS), поэтому
    # на узком экране прокручивается внутри своего контейнера. Без него
    # теплокарта тянула вбок всю страницу отчёта.
    out = ['<div class="kit-scroll"><div class="kit-heat"><div></div>'
           + "".join(f'<div class="kit-heat-col">{d}</div>' for d in DOW)
           + '<div class="kit-heat-col kit-heat-wk">нед.</div>']
    for w in range(len(cells) // 7):
        week = cells[w * 7:w * 7 + 7]
        real = [c for c in week if c]
        label = f"{_dm(real[0][0])} – {_dm(real[-1][0])}" if real else ""
        out.append(f'<div class="kit-heat-row">{esc(label)}</div>')
        total = 0.0
        for c in week:
            if not c or c[1] is None:
                out.append('<div class="kit-heat-cell kit-heat-empty" '
                           f'title="{"нет данных" if c else ""}">{"—" if c else ""}</div>')
                continue
            d, v = c
            total += float(v)
            s = step(float(v))
            out.append(f'<div class="kit-heat-cell{" kit-heat-ink" if s >= 3 else ""}" '
                       f'style="background:{ramp[s]}" data-tip="{_dm(d)}: {esc(num(v))} {esc(unit)}">'
                       f'{esc(num(v))}</div>')
        out.append(f'<div class="kit-heat-wk kit-num">{esc(num(total)) if real else ""}</div>')
    out.append('</div></div><div class="kit-ramp">меньше '
               + "".join(f'<i style="background:{c}"></i>' for c in ramp)
               + f' больше · всего <b>{esc(num(sum(vals)))}</b> {esc(unit)}</div>')
    return "".join(out)


# ── Малые кратные ────────────────────────────────────────────────────────────

def small_multiples(cards: list[dict], labels: list[str], w: int = 320, h: int = 130,
                    hex_mode: bool = False) -> str:
    """Ряд маленьких графиков на одной оси времени.

    card: {"title", "values", "prev"?, "color"?, "caption"?, "y_min"?}
    """
    out = []
    for c in cards:
        series = [{"name": c["title"], "values": c["values"],
                   "color": c.get("color") or tok("s1", hex_mode)}]
        if c.get("prev"):
            series.append({"name": "прошлый период", "values": c["prev"], "context": True})
        chart = line_chart(series, labels, w=w, h=h, ticks=2, area=True,
                           y_min=c.get("y_min", 0), title=c["title"], hex_mode=hex_mode)
        out.append(f'<div class="kit-mcard"><div class="kit-mcard-h"><b>{esc(c["title"])}</b>'
                   f'<span>{esc(c.get("caption", ""))}</span></div>{chart}</div>')
    return f'<div class="kit-multi">{"".join(out)}</div>'


# ── Таблица-дашборд ──────────────────────────────────────────────────────────

def bar_cell(value, vmax, color: str | None = None, text: str | None = None,
             hex_mode: bool = False) -> dict:
    v = float(value or 0)
    width = 0 if not vmax else max(2, round(v / float(vmax) * 56))
    color = color or tok("s1", hex_mode)
    return {"html": f'<i class="kit-bar" style="width:{width}px;background:{color}"></i>'
                    f'{esc(text if text is not None else num(value))}',
            "sort": v}


def pos_cell(position, delta=None) -> dict:
    """Позиция с дельтой: у позиций «меньше — лучше», поэтому знак инвертирован."""
    if position is None:
        return {"html": "—", "sort": 10 ** 6}
    d = ""
    if delta:
        d = delta_html(num(abs(delta)), "up" if delta < 0 else "down")
    return {"html": f'<span class="kit-pos">{esc(num(position))}</span> {d}',
            "sort": float(position)}


def chip(text: str, tone: str = "neutral") -> str:
    return f'<span class="kit-chip {tone}">{esc(text)}</span>'


def dense_table(columns: list[dict], rows: list[dict], sortable: bool = True,
                empty: str = "Строк нет.") -> str:
    """Таблица-дашборд: бары, спарклайны, позиции и статусы в строках.

    columns: [{"key", "label", "align": "left|right"}]
    rows: {key: str | {"html", "sort"?}} — dict даёт значение сортировки.
    """
    if not rows:
        return f'<p class="kit-muted">{esc(empty)}</p>'
    head = "".join(
        f'<th class="{c.get("align", "left")}"{" data-kit-sort" if sortable and c.get("sortable", True) else ""}>'
        f'{esc(c["label"])}</th>' for c in columns)
    body = []
    for r in rows:
        tds = []
        for c in columns:
            cell = r.get(c["key"], "")
            if isinstance(cell, dict):
                sort = cell.get("sort")
                tds.append(f'<td class="{c.get("align", "left")}"'
                           + (f' data-sort="{sort}"' if sort is not None else "")
                           + f'>{cell.get("html", "")}</td>')
            else:
                tds.append(f'<td class="{c.get("align", "left")}">{cell}</td>')
        body.append(f'<tr>{"".join(tds)}</tr>')
    cls = "kit-table kit-sortable" if sortable else "kit-table"
    return (f'<div class="kit-scroll"><table class="{cls}"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


# ── Письмо: табличная вёрстка без картинок ───────────────────────────────────

def email_masthead(brand_html: str, subtitle: str, width_note: str = "") -> str:
    """Тёмная шапка письма: BIZ<span>Soft</span> + подзаголовок."""
    return (f'<tr><td style="background:{LIGHT["hero"]};padding:22px 28px;border-radius:14px 14px 0 0;">'
            f'<div style="font-family:{EMAIL_FONT};font-size:19px;font-weight:bold;color:#ffffff;">'
            f'{brand_html}</div>'
            f'<div data-meta="1" style="font-family:{EMAIL_FONT};font-size:12.5px;'
            f'color:{LIGHT["hero_muted"]};padding-top:5px;line-height:1.45;">{subtitle}</div>'
            f'</td></tr>')


def email_tile(label: str, value: str, unit: str = "", delta: str | None = None,
               direction: str | None = None, note: str = "", meta: str = "",
               muted: bool = False, extra: str = "") -> str:
    """Плитка KPI для письма: одна таблица, шрифты ≥14 px, мета ≥12,5 px."""
    colour = {"up": LIGHT["good"], "down": LIGHT["crit"]}.get(direction or "", LIGHT["muted"])
    arrow = {"up": "▲ ", "down": "▼ ", "flat": "→ "}.get(direction or "", "")
    tone = LIGHT["muted"] if muted else LIGHT["ink"]
    d = (f'<span style="font-size:14px;font-weight:bold;color:{colour};">{arrow}{esc(delta)}</span>'
         if delta else "")
    return (
        # box-sizing инлайном: почтовые клиенты режут внешние стили, и тогда
        # рамка и внутренние поля ложатся поверх ширины 100%. Плитка в 290px
        # становится 298, пара таких не влезает в ряд, и письмо едет вбок —
        # отчёт за 17.09.2026 встал на этом гейте.
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="background:{LIGHT["surface"]};border:1px solid {LIGHT["hair"]};'
        f'border-radius:12px;box-sizing:border-box;">'
        f'<tr><td style="padding:14px 16px 12px;font-family:{EMAIL_FONT};">'
        f'<div data-meta="1" style="font-size:12.5px;font-weight:bold;color:{LIGHT["muted"]};">'
        f'{esc(label)}</div>'
        f'<div style="padding-top:4px;"><span style="font-size:28px;line-height:1.1;'
        f'font-weight:bold;color:{tone};">{esc(value)}</span>'
        + (f' <span data-meta="1" style="font-size:13px;color:{LIGHT["muted"]};">{esc(unit)}</span>'
           if unit else "")
        + (f'</div><div style="padding-top:4px;">{d}</div>' if d else '</div>')
        + extra
        + (f'<div style="font-size:14px;color:{LIGHT["ink"]};padding-top:8px;line-height:1.5;">{note}</div>'
           if note else "")
        + (f'<div data-meta="1" style="font-size:12.5px;color:{LIGHT["muted"]};padding-top:8px;'
           f'line-height:1.45;">{meta}</div>' if meta else "")
        + '</td></tr></table>')


def email_status_rows(rows: list[dict]) -> str:
    """Светофор для письма: глиф + название + значение, без картинок и шкал."""
    colour = {"good": LIGHT["good"], "warn": LIGHT["warn"], "crit": LIGHT["crit"],
              "neutral": LIGHT["muted"]}
    trs = "".join(
        f'<tr><td style="width:22px;padding:7px 0;border-bottom:1px solid {LIGHT["hair"]};'
        f'font-size:14px;font-weight:bold;color:{colour[r.get("state", "neutral")]};">'
        f'{STATE_GLYPH[r.get("state", "neutral")]}</td>'
        f'<td style="padding:7px 8px 7px 0;border-bottom:1px solid {LIGHT["hair"]};font-size:14px;'
        f'line-height:1.45;color:{LIGHT["ink"]};"><b>{esc(r["name"])}</b>'
        + (f' — {r["comment"]}' if r.get("comment") else "")
        + f'</td><td align="right" style="padding:7px 0;border-bottom:1px solid {LIGHT["hair"]};'
        f'font-size:14px;white-space:nowrap;color:{LIGHT["ink2"]};">{esc(r.get("value", ""))}</td></tr>'
        for r in rows)
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="font-family:{EMAIL_FONT};">{trs}</table>')


def email_bar_rows(rows: list[dict], vmax: float | None = None) -> str:
    """Горизонтальные полосы для письма: полоса — ячейка td заданной ширины.

    row: {"label", "value": float, "text"?, "color"?, "note"?}
    """
    if not rows:
        return ""
    top = vmax or max(float(r["value"]) for r in rows) or 1.0
    trs = []
    for r in rows:
        width = max(2, round(100 * float(r["value"]) / top))
        color = r.get("color") or LIGHT["s1"]
        trs.append(
            f'<tr><td style="padding:5px 8px 5px 0;font-size:14px;color:{LIGHT["ink"]};'
            f'white-space:nowrap;width:42%;">{esc(r["label"])}'
            + (f' <span data-meta="1" style="font-size:12.5px;color:{LIGHT["muted"]};">{esc(r["note"])}</span>'
               if r.get("note") else "")
            + f'</td><td style="padding:5px 0;">'
            f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr>'
            f'<td style="background:{color};height:10px;width:{width}%;border-radius:0 4px 4px 0;'
            f'font-size:0;line-height:0;">&nbsp;</td><td style="font-size:0;line-height:0;">&nbsp;</td>'
            f'</tr></table></td>'
            f'<td align="right" style="padding:5px 0 5px 10px;font-size:14px;font-weight:bold;'
            f'white-space:nowrap;color:{LIGHT["ink"]};">{esc(r.get("text", num(r["value"])))}</td></tr>')
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="font-family:{EMAIL_FONT};">{"".join(trs)}</table>')


# ── PNG для письма ───────────────────────────────────────────────────────────

def png_document(body: str, width: int, height: int) -> str:
    """Самодостаточная страница для render.mjs: светлые токены как hex."""
    vars_ = _vars(LIGHT)
    return (f"<html><head><meta charset='utf-8'><style>:root{{{vars_}}}"
            f"*{{margin:0;padding:0;box-sizing:border-box}}"
            f"body{{width:{width}px;height:{height}px;background:#fff;"
            f"font:400 12px/1.35 {EMAIL_FONT};color:{LIGHT['ink']};}}"
            f"{component_css()}</style></head><body>{body}</body></html>")


# ── CSS и JS страницы ────────────────────────────────────────────────────────

def _vars(p: dict) -> str:
    return ";".join(f"--kit-{k.replace('_', '-')}:{v}" for k, v in p.items())


def tokens_css() -> str:
    """Токены трёх состояний темы: голый :root, системная тёмная, явный выбор."""
    return (f":root{{{_vars(LIGHT)}}}"
            f'@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{{_vars(DARK)}}}}}'
            f':root[data-theme="dark"]{{{_vars(DARK)}}}')


def component_css() -> str:
    return """
.kit-num,.kit-table td,.kit-v,.kit-wf-v,.kit-heat-cell,.kit-heat-wk{font-variant-numeric:tabular-nums}
.kit-muted{color:var(--kit-muted)}
.kit-dash{background:var(--kit-surface);border:1px solid var(--kit-hair);border-radius:14px;padding:20px 22px;margin:0 0 18px}
.kit-dash-title{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.kit-dash-title h3{margin:0;font-size:16px;font-weight:700;letter-spacing:0;text-transform:none}
.kit-period{font-size:12.5px;color:var(--kit-muted)}
.kit-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(170px,100%),1fr));gap:12px}
.kit-tile{position:relative;font:inherit;color:inherit;text-align:left;background:var(--kit-surface);border:1px solid var(--kit-hair);border-radius:10px;padding:14px 14px 12px;display:flex;flex-direction:column;gap:5px;min-height:112px;cursor:default;overflow:hidden}
button.kit-tile{cursor:pointer;transition:border-color .15s}
button.kit-tile:hover{border-color:var(--kit-hair2)}
button.kit-tile:focus-visible{outline:2px solid var(--kit-accent);outline-offset:2px}
.kit-tile.kit-active{border-color:var(--kit-accent);box-shadow:inset 0 0 0 1px var(--kit-accent)}
.kit-tile.kit-muted .kit-val{color:var(--kit-muted)}
.kit-lbl{font-size:12px;color:var(--kit-muted);font-weight:600}
.kit-val{font-size:26px;font-weight:600;line-height:1.05;letter-spacing:-.01em;color:var(--kit-ink)}
.kit-val small{font-size:13px;font-weight:500;color:var(--kit-muted);margin-left:4px;letter-spacing:0}
.kit-note{font-size:13px;line-height:1.4;color:var(--kit-ink2);display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.kit-sub{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px 8px;margin-top:auto;min-width:0}
.kit-sub .kit-delta{white-space:normal}
.kit-sub .kit-spark{max-width:100%;height:auto}
.kit-meta{font-size:12px;color:var(--kit-muted);line-height:1.4}
.kit-delta{font-size:12.5px;font-weight:600;white-space:nowrap}
.kit-delta.up{color:var(--kit-good)} .kit-delta.down{color:var(--kit-crit)} .kit-delta.flat{color:var(--kit-muted)}
.kit-spark{display:block;flex-shrink:0}
.kit-panel{margin-top:14px;border-top:1px solid var(--kit-hair);padding-top:14px;display:grid;grid-template-columns:1.4fr 1fr;gap:18px}
.kit-panel>*,.kit-two>*,.kit-multi>*,.kit-hero-grid>*,.kit-row>*{min-width:0}
.kit-panel h4{margin:0 0 6px;font-size:13.5px;font-weight:700}
.kit-panel .kit-hint{font-size:12px;color:var(--kit-muted);margin:0 0 8px}
@media (max-width:820px){.kit-panel{grid-template-columns:1fr}}
.kit-chart svg{display:block;max-width:100%;height:auto}
.kit-legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--kit-ink2);margin-bottom:6px}
.kit-legend i{display:inline-block;width:14px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}
.kit-tip{position:fixed;z-index:200;pointer-events:none;background:var(--kit-ink);color:var(--kit-plane);font-size:12px;line-height:1.35;padding:6px 9px;border-radius:7px;opacity:0;transform:translate(-50%,-115%);transition:opacity .08s;white-space:nowrap}
.kit-tip.show{opacity:1}
.kit-status{display:flex;flex-direction:column}
.kit-srow{display:grid;grid-template-columns:26px 1.3fr 90px 90px 1.5fr 1.5fr;gap:12px;align-items:center;padding:10px 6px;border-bottom:1px solid var(--kit-hair)}
.kit-srow:last-child{border-bottom:0}
.kit-shead{font-size:11.5px;font-weight:600;color:var(--kit-muted);padding:4px 6px;letter-spacing:.02em}
.kit-name{font-weight:600;font-size:14px}
.kit-name small{display:block;font-weight:500;color:var(--kit-muted);font-size:11.5px}
.kit-v{font-size:17px;font-weight:600}
.kit-cmt{font-size:12.5px;color:var(--kit-ink2);line-height:1.4}
.kit-dot{width:15px;height:15px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:9px;font-weight:700}
.kit-dot.good{background:var(--kit-good)} .kit-dot.warn{background:var(--kit-warn)} .kit-dot.crit{background:var(--kit-crit)} .kit-dot.neutral{background:var(--kit-gray)}
.kit-meter-wrap{display:flex;align-items:center;gap:10px}
.kit-meter{position:relative;flex:1;height:8px;border-radius:4px;background:var(--kit-q1);display:block}
.kit-meter b{position:absolute;left:0;top:0;height:100%;border-radius:4px;background:var(--kit-s1)}
.kit-meter b.good{background:var(--kit-good)} .kit-meter b.warn{background:var(--kit-warn)} .kit-meter b.crit{background:var(--kit-crit)}
.kit-meter-cap{font-size:11.5px;color:var(--kit-muted);white-space:nowrap}
@media (max-width:820px){.kit-srow{grid-template-columns:24px 1fr 80px 70px}.kit-srow .kit-m,.kit-srow .kit-cmt{display:none}}
.kit-hero-grid{display:grid;grid-template-columns:260px 1fr;gap:20px;align-items:stretch}
@media (max-width:820px){.kit-hero-grid{grid-template-columns:1fr}}
.kit-hero{background:var(--kit-hero);color:var(--kit-hero-ink);border-radius:14px;padding:22px 22px 18px;display:flex;flex-direction:column;justify-content:space-between;min-height:220px}
.kit-hero-lbl{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--kit-hero-muted);font-weight:600}
.kit-hero-big{font-size:72px;font-weight:700;line-height:1;letter-spacing:-.03em;margin-top:6px}
.kit-hero-big small{font-size:20px;color:var(--kit-hero-muted);font-weight:500;letter-spacing:0}
.kit-hero-delta{color:#4ad07a;font-weight:600;font-size:14px;margin-top:6px}
.kit-hero-foot{font-size:12px;color:var(--kit-hero-muted);margin-top:12px;line-height:1.45}
.kit-wf{display:grid;gap:6px}
.kit-wf-row{display:grid;grid-template-columns:minmax(120px,220px) 1fr 60px;gap:10px;align-items:center;font-size:13px}
.kit-wf-lab{color:var(--kit-ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kit-wf-row.total .kit-wf-lab,.kit-wf-row.base .kit-wf-lab{font-weight:600;color:var(--kit-ink)}
.kit-wf-track{position:relative;height:14px;display:block}
.kit-wf-track b{position:absolute;top:0;height:14px;border-radius:4px}
.kit-wf-zero{position:absolute;top:-4px;bottom:-4px;width:1px;background:var(--kit-hair2)}
.kit-wf-v{text-align:right;font-weight:600}
.kit-db{display:grid;gap:4px}
.kit-db-row{display:grid;grid-template-columns:minmax(120px,220px) 1fr 90px;gap:10px;align-items:center;font-size:12.5px;height:24px}
.kit-db-lab{color:var(--kit-ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kit-db-track{position:relative;height:12px;display:block}
.kit-db-track i{position:absolute;top:-4px;width:1px;height:20px}
.kit-db-track b{position:absolute;top:0;height:12px}
.kit-db-v{font-weight:600;white-space:nowrap;color:var(--kit-ink)}
.kit-db-share{color:var(--kit-muted);font-weight:400}
.kit-heat{display:grid;grid-template-columns:110px repeat(7,minmax(0,1fr)) 60px;gap:3px;align-items:center;min-width:432px}
.kit-heat-row{font-size:12px;color:var(--kit-ink2);padding-right:6px;white-space:nowrap}
.kit-heat-col{font-size:11px;color:var(--kit-muted);text-align:center;padding-bottom:2px}
.kit-heat-cell{height:30px;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:11.5px;font-weight:600;color:var(--kit-ink2);min-width:0;overflow:hidden}
.kit-heat-cell.kit-heat-ink{color:#fff}
.kit-heat-empty{background:transparent;border:1px dashed var(--kit-hair2);color:var(--kit-muted)}
.kit-heat-wk{font-size:12px;font-weight:600;text-align:right;padding-right:4px}
.kit-ramp{display:flex;align-items:center;gap:5px;font-size:11.5px;color:var(--kit-muted);margin-top:10px;flex-wrap:wrap}
.kit-ramp i{display:inline-block;width:22px;height:10px;border-radius:2px}
.kit-ramp b{color:var(--kit-ink)}
.kit-multi{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr));gap:14px}
.kit-mcard{border:1px solid var(--kit-hair);border-radius:10px;padding:12px 12px 8px;background:var(--kit-surface)}
.kit-mcard-h{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:4px}
.kit-mcard-h b{font-size:13px;font-weight:600}
.kit-mcard-h span{font-size:12px;color:var(--kit-muted)}
.kit-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.kit-table{width:100%;border-collapse:collapse;font-size:13.5px}
.kit-table th{font-size:11.5px;font-weight:600;color:var(--kit-muted);text-align:left;padding:6px 8px;border-bottom:1px solid var(--kit-hair2);letter-spacing:.02em;white-space:nowrap;text-transform:none;position:static;background:transparent}
.kit-table th[data-kit-sort]{cursor:pointer;user-select:none}
.kit-table th.kit-sorted::after{content:" ↓";color:var(--kit-accent)}
.kit-table th.kit-sorted.asc::after{content:" ↑"}
.kit-table td{padding:7px 8px;border-bottom:1px solid var(--kit-hair);vertical-align:middle}
.kit-table tr:last-child td{border-bottom:0}
.kit-table td.right,.kit-table th.right{text-align:right;white-space:nowrap}
.kit-table td .kit-spark{display:inline-block;vertical-align:middle}
.kit-bar{display:inline-block;height:10px;background:var(--kit-s1);border-radius:0 4px 4px 0;vertical-align:middle;margin-right:8px}
.kit-pos{display:inline-block;min-width:32px;text-align:right;font-weight:600}
.kit-chip{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;padding:2px 8px;border-radius:999px;white-space:nowrap;text-transform:none;letter-spacing:0}
.kit-chip.good{background:var(--kit-good-soft);color:var(--kit-good)} .kit-chip.warn{background:var(--kit-warn-soft);color:var(--kit-warn)} .kit-chip.crit{background:var(--kit-crit-soft);color:var(--kit-crit)} .kit-chip.neutral{background:var(--kit-plane);color:var(--kit-ink2)} .kit-chip.accent{background:var(--kit-accent-soft);color:var(--kit-accent-ink)}
.kit-two{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media (max-width:820px){.kit-two{grid-template-columns:1fr}}
"""


def kit_css() -> str:
    return tokens_css() + component_css()


def light_css() -> str:
    """Только светлая тема: для страниц, чья собственная вёрстка светлая."""
    return f":root{{{_vars(LIGHT)}}}" + component_css()


def kit_js() -> str:
    """Тултипы, crosshair на линиях, углубление плиток, сортировка таблиц."""
    return r"""
(function(){
  var tip=document.createElement('div');tip.className='kit-tip';document.body.appendChild(tip);
  function show(h,x,y){tip.innerHTML=h;tip.style.left=x+'px';tip.style.top=(y-8)+'px';tip.classList.add('show');}
  function hide(){tip.classList.remove('show');}
  document.addEventListener('mousemove',function(e){
    var t=e.target.closest&&e.target.closest('[data-tip]');
    if(t){show(t.getAttribute('data-tip'),e.clientX,e.clientY);}
    else if(!(e.target.closest&&e.target.closest('svg[data-kit-line]'))){hide();}
  });
  document.querySelectorAll('svg[data-kit-line]').forEach(function(svg){
    var d;try{d=JSON.parse(svg.getAttribute('data-kit-line'));}catch(err){return;}
    var n=d.labels.length,iw=d.w-d.pad[0]-d.pad[1],ih=d.h-d.pad[2]-d.pad[3];
    var ns='http://www.w3.org/2000/svg',g=document.createElementNS(ns,'g');g.style.display='none';
    var ln=document.createElementNS(ns,'line');ln.setAttribute('y1',d.pad[2]);ln.setAttribute('y2',d.pad[2]+ih);
    ln.setAttribute('stroke','var(--kit-hair2)');g.appendChild(ln);
    var dots=d.series.map(function(s){var c=document.createElementNS(ns,'circle');c.setAttribute('r',5);
      c.setAttribute('fill',s.color);c.setAttribute('stroke','var(--kit-surface)');c.setAttribute('stroke-width',2);g.appendChild(c);return c;});
    svg.appendChild(g);
    var X=function(i){return d.pad[0]+i*iw/(n-1);},Y=function(v){return d.pad[2]+ih-(v-d.ymin)/(d.top-d.ymin)*ih;};
    svg.addEventListener('mousemove',function(e){
      var b=svg.getBoundingClientRect(),mx=(e.clientX-b.left)*(d.w/b.width);
      var i=Math.max(0,Math.min(n-1,Math.round((mx-d.pad[0])/iw*(n-1))));
      g.style.display='';ln.setAttribute('x1',X(i));ln.setAttribute('x2',X(i));
      var rows=[];
      d.series.forEach(function(s,k){var v=s.values[i];if(v==null){dots[k].style.display='none';rows.push(s.name+': нет данных');return;}
        dots[k].style.display='';dots[k].setAttribute('cx',X(i));dots[k].setAttribute('cy',Y(v));rows.push(s.name+': <b>'+v.toLocaleString('ru-RU')+'</b>');});
      show('<b>'+d.labels[i]+'</b><br>'+rows.join('<br>'),e.clientX,e.clientY);
    });
    svg.addEventListener('mouseleave',function(){g.style.display='none';hide();});
  });
  document.querySelectorAll('.kit-dash').forEach(function(dash){
    var tiles=dash.querySelectorAll('[data-kit-key]');
    tiles.forEach(function(t){t.addEventListener('click',function(){
      tiles.forEach(function(x){x.classList.remove('kit-active');x.setAttribute('aria-pressed','false');});
      t.classList.add('kit-active');t.setAttribute('aria-pressed','true');
      dash.querySelectorAll('[data-kit-panel]').forEach(function(p){p.hidden=p.getAttribute('data-kit-panel')!==t.getAttribute('data-kit-key');});
    });});
  });
  document.querySelectorAll('table.kit-sortable').forEach(function(tbl){
    var ths=tbl.querySelectorAll('th[data-kit-sort]');
    ths.forEach(function(th,idx){th.addEventListener('click',function(){
      var asc=th.classList.contains('kit-sorted')&&!th.classList.contains('asc');
      ths.forEach(function(x){x.classList.remove('kit-sorted','asc');});
      th.classList.add('kit-sorted');if(asc)th.classList.add('asc');
      var col=Array.prototype.indexOf.call(th.parentNode.children,th);
      var body=tbl.tBodies[0],rows=Array.prototype.slice.call(body.rows);
      var val=function(r){var td=r.cells[col];if(!td)return '';var s=td.getAttribute('data-sort');return s!==null?parseFloat(s):td.textContent.trim();};
      rows.sort(function(a,b){var x=val(a),y=val(b);var num=typeof x==='number'&&typeof y==='number';
        var c=num?x-y:String(x).localeCompare(String(y),'ru');return asc?c:-c;});
      rows.forEach(function(r){body.appendChild(r);});
    });});
  });
})();
"""


__all__ = [n for n in dir() if not n.startswith("_")]
