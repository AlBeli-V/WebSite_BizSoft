#!/usr/bin/env python3
"""Блок «Аудитория»: показы и визиты в разрезе устройств и каналов.

Отвечает на два вопроса руководителя (постановка 14.09.2026): сколько показов
дали Яндекс и Google по отдельности и с каких устройств их смотрели; сколько
людей после этого зашло на сайт — по каналам (органика, реклама, внешние
ссылки, внешние каталоги, внешние площадки) и снова по устройствам.

Что здесь считается:

* показы — Вебмастер и Search Console, ряды витрины `impressions_<устройство>`;
* визиты — Метрика и GA4, ряды `visits_<канал>_<устройство>` и
  `sessions_<канал>_<устройство>` (сбор — collect_daily.py);
* «Яндекс» и «Гугл» в таблице визитов — это два счётчика одного сайта,
  а не два источника перехода: Метрика и GA4 считают всю аудиторию сайта
  каждая по-своему, и расхождение между ними — свойство измерения, а не
  разница трафика. Письмо это называет прямо.

Периоды — только полные окна дневной витрины (правило
docs/rules/report-integrity.md): текущие семь зрелых дней против предыдущих
семи, встык, без пересечений. Лаг созревания у поиска три дня, у аналитики
один, поэтому окна поиска и аналитики заканчиваются разными днями — каждая
таблица называет своё окно. Неполное окно не публикуется: блок говорит
«нет данных» с перечнем недостающих дней, а не дорисовывает нули.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import collect_daily as cd   # noqa: E402 — словари устройств и каналов
import daily_windows as dw   # noqa: E402
import passport              # noqa: E402
from textfmt import num, pct  # noqa: E402 — числа и доли как во всём отчёте

# Три знакомых класса устройств печатаются всегда, четвёртый (телевизоры,
# приставки, неопознанное) — только когда в нём что-то есть: пустая колонка
# «прочие» в каждом письме была бы шумом.
DEVICES = ("desktop", "mobile", "tablet", "other")
DEVICE_LABEL = {"desktop": "Десктоп", "mobile": "Мобильные",
                "tablet": "Планшеты", "other": "Прочие"}
DEVICE_SHORT = {"desktop": "Десктоп", "mobile": "Моб.",
                "tablet": "Планш.", "other": "Проч."}

CHANNELS = ("organic", "ads", "links", "catalogs", "platforms", "other")
CHANNEL_LABEL = {
    "organic": "Органика",
    "ads": "Реклама",
    "links": "Внешние ссылки",
    "catalogs": "Внешние каталоги",
    "platforms": "Внешние площадки",
    "other": "Прочее (прямые, внутренние)",
}

# Источник → как он называется читателю и какой ряд витрины читается.
IMPRESSION_SOURCES = (
    {"key": "yandex", "label": "Яндекс", "source_label": "Яндекс.Вебмастер",
     "series": "impressions", "clicks": "clicks"},
    {"key": "gsc", "label": "Google", "source_label": "Search Console",
     "series": "impressions", "clicks": "clicks"},
)
VISIT_SOURCES = (
    {"key": "metrika", "label": "Яндекс", "source_label": "Яндекс.Метрика",
     "series": "visits", "unit": "визитов"},
    {"key": "ga4", "label": "Гугл", "source_label": "GA4",
     "series": "sessions", "unit": "сессий"},
)

# База, ниже которой относительное изменение не публикуется. То же число, что
# в отчёте и в quality.delta: одно определение малой базы на всю систему.
LOW_BASE = 30


def _share(part: float, total: float) -> float | None:
    """Доля части в целом; None — целое равно нулю и доли не существует."""
    return (part / total) if total else None


def _delta_pct(current: float, previous: float) -> float | None:
    """Относительное изменение окна к окну; None — база ниже порога."""
    if previous is None or previous < LOW_BASE:
        return None
    return (current - previous) / previous


def _window_block(report_date: str, source: str, metrics: list[str],
                  base_dir: pathlib.Path | None) -> dict:
    """Окна витрины по своему набору рядов."""
    store = dw.load_series(source, base_dir)
    return dw.build_source(report_date, source, store, metrics=tuple(metrics))


def _totals(win: dict, metrics: list[str]) -> tuple[float, float]:
    """Суммы текущего и предыдущего окна по набору рядов."""
    cur = sum(win["windows"][m]["current"]["sum"] for m in metrics)
    prev = sum(win["windows"][m]["previous"]["sum"] for m in metrics)
    return cur, prev


def _by_device(win: dict, prefix: str) -> dict:
    """Значения текущего окна по устройствам для ряда с данным префиксом."""
    return {dev: win["windows"][f"{prefix}_{dev}"]["current"]["sum"]
            for dev in DEVICES if f"{prefix}_{dev}" in win["windows"]}


def _unavailable(win: dict, source_label: str) -> dict | None:
    """Паспорт недоступности окна: нет витрины, неполное окно — или None."""
    if not win.get("available"):
        return passport.unavailable("no_file", source=source_label)
    if not win.get("complete"):
        missing = win.get("missing_dates") or []
        return passport.unavailable(
            "no_rows", source=source_label,
            detail=("окно неполное, нет дней: " + ", ".join(missing[:5])
                    + ("…" if len(missing) > 5 else "")))
    return None


def _period(win: dict) -> dict:
    """Границы обоих окон источника — их называет каждая таблица."""
    any_metric = next(iter(win["windows"].values()))
    return {"current": {"from": any_metric["current"]["from"],
                        "to": any_metric["current"]["to"]},
            "previous": {"from": any_metric["previous"]["from"],
                         "to": any_metric["previous"]["to"]}}


def impressions_rows(report_date: str, base_dir: pathlib.Path | None = None) -> dict:
    """Показы поиска по устройствам: строка на поисковую систему."""
    rows, period = [], None
    for src in IMPRESSION_SOURCES:
        by_device = [f"{src['series']}_{d}" for d in cd.YANDEX_DEVICE]
        clicks = [f"{src['clicks']}_{d}" for d in cd.YANDEX_DEVICE]
        win = _window_block(report_date, src["key"],
                            [src["series"], src["clicks"]] + by_device + clicks,
                            base_dir)
        bad = _unavailable(win, src["source_label"])
        if bad:
            rows.append({**bad, "key": src["key"], "label": src["label"],
                         "source_label": src["source_label"]})
            continue
        period = period or _period(win)
        # Итог берётся из того же ряда, что и карточка видимости в шапке
        # письма: два числа об одном и том же обязаны совпадать. Разбивка
        # по устройствам — отдельные ряды источника, и если их сумма
        # расходится с итогом, блок называет покрытие, а не молчит.
        cur, prev = _totals(win, [src["series"]])
        devices = _by_device(win, src["series"])
        devices_total = sum(devices.values())
        clicks_cur, _ = _totals(win, [src["clicks"]])
        rows.append({
            **passport.available(_period(win)["current"]["to"]),
            "key": src["key"], "label": src["label"],
            "source_label": src["source_label"],
            "total": cur, "previous": prev, "delta": cur - prev,
            "delta_pct": _delta_pct(cur, prev),
            "clicks": clicks_cur,
            "ctr": _share(clicks_cur, cur),
            "devices": devices,
            "devices_total": devices_total,
            "coverage": _share(devices_total, cur),
            "shares": {d: _share(v, devices_total) for d, v in devices.items()},
            "period": _period(win),
        })
    return {**passport.flag(any(r.get("available") for r in rows), "no_file",
                            source="дневная витрина показов по устройствам"),
            "rows": rows, "period": period}


def visits_rows(report_date: str, base_dir: pathlib.Path | None = None) -> dict:
    """Визиты по каналам и устройствам: блок на систему учёта."""
    blocks, period = [], None
    for src in VISIT_SOURCES:
        metrics = cd.channel_metrics(src["series"])
        win = _window_block(report_date, src["key"], metrics, base_dir)
        bad = _unavailable(win, src["source_label"])
        if bad:
            blocks.append({**bad, "key": src["key"], "label": src["label"],
                           "source_label": src["source_label"],
                           "unit": src["unit"], "channels": []})
            continue
        period = period or _period(win)
        channels = []
        for ch in CHANNELS:
            names = [f"{src['series']}_{ch}_{d}" for d in DEVICES]
            cur, prev = _totals(win, names)
            devices = {d: win["windows"][f"{src['series']}_{ch}_{d}"]["current"]["sum"]
                       for d in DEVICES}
            channels.append({
                "key": ch, "label": CHANNEL_LABEL[ch],
                "total": cur, "previous": prev, "delta": cur - prev,
                "delta_pct": _delta_pct(cur, prev),
                "devices": devices,
                "shares": {d: _share(v, cur) for d, v in devices.items()},
            })
        total, total_prev = _totals(win, metrics)
        devices = {d: sum(c["devices"][d] for c in channels) for d in DEVICES}
        blocks.append({
            **passport.available(_period(win)["current"]["to"]),
            "key": src["key"], "label": src["label"],
            "source_label": src["source_label"], "unit": src["unit"],
            "total": total, "previous": total_prev, "delta": total - total_prev,
            "delta_pct": _delta_pct(total, total_prev),
            "devices": devices,
            "shares": {d: _share(v, total) for d, v in devices.items()},
            "channels": channels,
            "period": _period(win),
        })
    return {**passport.flag(any(b.get("available") for b in blocks), "no_file",
                            source="дневная витрина визитов по каналам"),
            "blocks": blocks, "period": period}


def visible_devices(block: dict) -> list[str]:
    """Классы устройств, которые печатаются: три знакомых плюс непустые прочие.

    «Прочие» (телевизоры, приставки, неопознанное) появляются колонкой только
    тогда, когда в них есть хоть один визит: пустая колонка в каждом письме —
    шум, а молча выброшенные визиты — потеря.
    """
    devices = ["desktop", "mobile", "tablet"]
    rest = 0.0
    for row in (block.get("impressions") or {}).get("rows", []):
        rest += (row.get("devices") or {}).get("other") or 0
    for blk in (block.get("visits") or {}).get("blocks", []):
        rest += (blk.get("devices") or {}).get("other") or 0
    return devices + (["other"] if rest else [])


def tiles(block: dict) -> list[dict]:
    """Четыре плитки блока: показы двух поисковиков и визиты двух счётчиков.

    Порядок постоянный — Яндекс, Google, Метрика, GA4, — чтобы взгляд
    руководителя каждый день попадал в одно и то же место.
    """
    out = []
    for row in (block.get("impressions") or {}).get("rows", []):
        out.append({**row, "kind": "impressions",
                    "title": f"Показы · {row['label']}",
                    "unit": "показов за неделю"})
    for blk in (block.get("visits") or {}).get("blocks", []):
        out.append({**blk, "kind": "visits",
                    "title": f"Визиты · {blk['source_label']}",
                    "unit": f"{blk.get('unit', 'визитов')} за неделю"})
    return out


def headline(block: dict) -> str:
    """Одна строка о главном: где аудитория смотрит и откуда приходит.

    Строка собирается из чисел блока; ни одного утверждения, которого нет
    в данных, в ней не появляется. Нет данных — так и говорится.
    """
    imp = [r for r in (block.get("impressions") or {}).get("rows", [])
           if r.get("available")]
    vis = [b for b in (block.get("visits") or {}).get("blocks", [])
           if b.get("available")]
    if not imp and not vis:
        return ("Разрез по устройствам и каналам за неделю не собран — "
                "ни один ряд витрины не полон.")
    parts = []
    for row in imp:
        share = (row.get("shares") or {}).get("mobile")
        if share is not None:
            parts.append(f"{row['label']}: с телефонов {pct(share, 0)} показов")
    for blk in vis:
        top = max((c for c in blk.get("channels") or [] if c["total"]),
                  key=lambda c: c["total"], default=None)
        if top:
            parts.append(f"{blk['source_label']}: больше всего визитов даёт "
                         f"{top['label'].lower()} ({num(top['total'])})")
    return "; ".join(parts) + "." if parts else (
        "Данные за неделю собраны, но ни показов, ни визитов в окне нет.")


def build(report_date: str, base_dir: pathlib.Path | None = None) -> dict:
    """Блок «Аудитория» целиком: показы, визиты и общая доступность."""
    imp = impressions_rows(report_date, base_dir)
    vis = visits_rows(report_date, base_dir)
    block = {
        **passport.flag(imp.get("available") or vis.get("available"), "no_file",
                        source="дневная витрина устройств и каналов"),
        "impressions": imp,
        "visits": vis,
    }
    block["devices"] = visible_devices(block)
    block["tiles"] = tiles(block)
    block["headline"] = headline(block)
    return block
