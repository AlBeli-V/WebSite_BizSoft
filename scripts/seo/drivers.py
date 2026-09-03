#!/usr/bin/env python3
"""Разложение изменения на драйверы: какие страницы и запросы его дали.

Правило отчёта: причина изменения либо подтверждена конкретными страницами и
запросами, либо не называется. Формулировки вида «поиск стал чаще показывать
наши карточки» без списка страниц запрещены — вместо них выводится
«причина изменения пока не определена».

Сравниваются одноимённые сущности двух соседних снимков. Окно источника при этом
сдвигается на сутки, поэтому разложение описывает изменение накопленного окна,
а не изменение за календарный день; это указывается рядом с числами.
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import measurement  # noqa: E402
import passport

VENDOR_PATH = re.compile(r"^/vendors/([a-z0-9-]+)")
MIN_SHARE = 0.05          # вклад меньше 5 % в отдельный драйвер не выносим
MIN_ABS = 3               # и меньше трёх показов тоже
# Порог считается ещё и от базы: при недельной базе Google в 38 показов
# разница в два показа неотличима от пуассоновского шума, и называть её
# драйвером — это выдавать шум за причину.
MIN_SHARE_OF_BASE = 0.05
# Ниже этой базы разложение на драйверы описывает шум, а не причину.
LOW_BASE = 60


def vendor_of(entity_id: str, vendors: set[str]) -> str | None:
    m = VENDOR_PATH.match(entity_id)
    if m:
        return m.group(1)
    low = entity_id.lower()
    for slug in vendors:
        if slug.replace("-", " ") in low or slug in low:
            return slug
    return None


def index(rows: list[dict]) -> dict[str, dict]:
    return {r["entity_id"]: r for r in rows or []}


def threshold(base: int) -> int:
    """Минимальная дельта, которую имеет смысл называть драйвером."""
    return max(MIN_ABS, round(base * MIN_SHARE_OF_BASE))


def decompose(cur_rows, prev_rows, vendors, metric="impressions", limit=5):
    """Драйверы и детракторы изменения метрики между двумя снимками."""
    cur, prev = index(cur_rows), index(prev_rows)
    if not cur or not prev:
        return passport.unavailable("no_previous", drivers=[], total_delta=None)

    items = []
    for key in set(cur) | set(prev):
        c, p = cur.get(key), prev.get(key)
        cv = (c or {}).get(metric) or 0
        pv = (p or {}).get(metric) or 0
        d = cv - pv
        if d == 0:
            continue
        items.append({
            "entity": key,
            "vendor": vendor_of(key, vendors),
            "current": cv,
            "previous": pv,
            "delta": d,
            "clicks_delta": ((c or {}).get("clicks") or 0) - ((p or {}).get("clicks") or 0),
            "position_delta": (round((c or {}).get("average_position") - (p or {}).get("average_position"), 2)
                               if c and p and c.get("average_position") is not None
                               and p.get("average_position") is not None else None),
            # Сущность, выбывшая из выборки, не упала до нуля — она перестала
            # измеряться. Для Яндекса это обычное дело: выборка пересобирается
            # каждый сбор, и «потеря» страницы чаще означает смену состава
            # списка, а не потерю показов.
            "state": "new" if p is None else ("dropped_from_sample" if c is None else "changed"),
            "confidence": (c or p or {}).get("confidence", "unknown"),
        })

    total = sum(i["delta"] for i in items)
    gross = sum(abs(i["delta"]) for i in items) or 1
    for i in items:
        i["share_of_total_delta"] = abs(i["delta"]) / gross
    # При равной дельте порядок иначе зависит от того, как источник разложил
    # словарь, и отчёт меняется от прогона к прогону без единого изменения в
    # данных. Разводим сначала по текущему объёму — из двух страниц с одинаковым
    # приростом важнее та, у которой больше показов, — а затем по имени, чтобы
    # порядок был определён до конца.
    items.sort(key=lambda i: (-abs(i["delta"]), -i["current"], i["entity"]))

    # Рост и снижение отбираются раздельно: иначе при общем падении в верхних
    # строках по модулю не остаётся ни одного драйвера роста, и блок «драйверы
    # и детракторы» показывает только одну сторону изменения.
    base = sum(i["current"] for i in items) or 1
    floor = threshold(base)
    # При малой базе доля от общего изменения перестаёт что-либо значить:
    # когда суммарная дельта — двадцать показов, вклад в 10 % это два показа.
    # Поэтому «или» превращается в «и»: драйвером называется только то, что
    # заметно и по абсолютной величине, и по доле.
    small = base < LOW_BASE
    significant = [i for i in items
                   if i["state"] != "dropped_from_sample"
                   and ((abs(i["delta"]) >= floor and i["share_of_total_delta"] >= MIN_SHARE)
                        if small else
                        (abs(i["delta"]) >= floor or i["share_of_total_delta"] >= MIN_SHARE))]
    half = max(1, limit // 2)
    gains = [i for i in significant if i["delta"] > 0][:half]
    losses = [i for i in significant if i["delta"] < 0][:limit - len(gains)]
    shown = gains + losses
    return {
        **passport.flag(bool(shown), "no_signal", detail="изменений выше порога нет"),
        "total_delta": total,
        "net_delta_of_shown": sum(i["delta"] for i in shown),
        "drivers": gains,
        "detractors": losses,
        "all": shown,
        "counted": len(items),
        "min_delta": floor,
        "dropped_from_sample": [i["entity"] for i in items
                                if i["state"] == "dropped_from_sample"],
    }


def vendor_slugs(snap: dict) -> set[str]:
    out = set()
    for e in (snap.get("experiments") or []):
        slug = e.get("slug") or e.get("vendor")
        if slug:
            out.add(str(slug).lower())
    for p in ((snap.get("google") or {}).get("pages") or []):
        m = VENDOR_PATH.match(p["entity_id"])
        if m:
            out.add(m.group(1))
    return out


def build(snap: dict, prev: dict | None) -> dict:
    """Разложение по обеим поисковым системам с явным указанием окна."""
    if not prev:
        return passport.unavailable("no_previous", source="снимок за предыдущий день",
                                    blocks=[])
    vendors = vendor_slugs(snap)
    blocks = []

    g, gp = snap.get("google") or {}, prev.get("google") or {}
    if g.get("available") and gp.get("available"):
        pages = decompose(g.get("pages"), gp.get("pages"), vendors)
        queries = decompose(g.get("entities"), gp.get("entities"), vendors)
        window = g["totals"]["window_days"]
        blocks.append({
            "engine": "google",
            "engine_label": "Google",
            "metric_label": "показы",
            "window_label": f"накопленное окно {window} дней, сдвинуто на сутки",
            "pages": pages,
            "queries": queries,
        })

    y, yp = snap.get("yandex") or {}, prev.get("yandex") or {}
    if y.get("available") and yp.get("available"):
        queries = decompose(y.get("entities"), yp.get("entities"), vendors)
        src = y["source"]
        blocks.append({
            "engine": "yandex",
            "engine_label": "Яндекс",
            "metric_label": "показы",
            "window_label": f"{measurement.yandex_scope_label(y)}, окно "
                            f"{src['current_period_start']}–{src['current_period_end']}",
            "pages": passport.unavailable("unsupported", source="Вебмастер",
                                          detail="разбивка по страницам"),
            "queries": queries,
        })

    usable = [b for b in blocks
              if b["pages"].get("available") or b["queries"].get("available")]
    return {
        **passport.flag(bool(usable), "no_rows", source="разложение по источникам"),
        "blocks": blocks,
    }


def summarise(block: dict) -> str:
    """Фраза о драйверах, опирающаяся на конкретные страницы, а не на догадку."""
    part = block["pages"] if block["pages"].get("available") else block["queries"]
    if not part.get("available"):
        return "Причина изменения пока не определена."
    ups = part["drivers"][:3]
    if not ups:
        return "Рост не разложен: изменения дают только снижения."
    names = ", ".join(f"{d['entity']} ({d['delta']:+d})" for d in ups)
    return f"Показы выросли на страницах: {names}."
