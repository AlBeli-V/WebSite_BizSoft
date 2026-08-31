#!/usr/bin/env python3
"""Momentum спроса: помесячная динамика коммерческого ядра (механика №19).

«Зелёный свет» руководителя 30.08.2026: Wordstat расширяется вглубь —
не новыми фразами, а динамикой уже известных. Ускоряющийся спрос (новые
AI-сервисы) виден по динамике раньше, чем по абсолютной частотности.

Ядро — то же, что у SERP-среза (serp_watchlist): одна семантика на все
сенсоры. Вызовы идут через штатный WordstatClient — кэш (TTL динамики),
бюджет и часовая квота действуют как для любого прогона; отдельного
бюджета у momentum нет.

Каденция — еженедельно по понедельникам (шаг workflow seo-wordstat);
стоимость ~300 фраз × 0,02 ₽ ≈ 6 ₽ за прогон.

Запуск: python3 scripts/seo/wordstat/momentum.py [YYYY-MM-DD]
Выход:  reports/seo/wordstat/momentum-<дата>.json
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import budget as budget_mod    # noqa: E402
import client as client_mod    # noqa: E402
import config as config_mod    # noqa: E402

OUT_DIR = pathlib.Path("reports/seo/wordstat")
PHRASES_CAP = 300
MONTHS = 13     # 12 полных месяцев для сравнения год-к-году + свежий хвост


def acceleration(series: list[dict]) -> dict:
    """Сигналы ускорения по помесячному ряду [{date|month, value}].

    Сравниваются средние: последние 2 полных месяца против предыдущих 4 и
    против того же окна год назад. Проценты не публикуются при малой базе —
    порог 50 показов/мес, ниже рост «в разы» — шум.
    """
    values = [int(p.get("value") or 0) for p in series]
    if len(values) < 6:
        return {"trend": "insufficient_series", "months": len(values)}
    recent = sum(values[-2:]) / 2
    prior = sum(values[-6:-2]) / 4
    yoy_base = (sum(values[-14:-12]) / 2) if len(values) >= 14 else None
    out = {"recent_avg": round(recent, 1), "prior_avg": round(prior, 1),
           "months": len(values)}
    if prior < 50 and recent < 50:
        out["trend"] = "low_base"
    elif recent >= prior * 1.5:
        out["trend"] = "accelerating"
    elif recent <= prior * 0.67:
        out["trend"] = "decelerating"
    else:
        out["trend"] = "flat"
    if yoy_base and yoy_base >= 50:
        out["yoy_ratio"] = round(recent / yoy_base, 2)
    return out


def parse_dynamics(data: dict) -> list[dict]:
    """Ряд из ответа getDynamics.

    Фактическая форма (кэш 31.08.2026): {"results": [{"date": ...,
    "count": "5", "share": ...}]}; count — строка, у месяцев без показов
    поле отсутствует вовсе (это честный ноль, а не пропуск). Прежние
    ключи dynamics/points оставлены запасными.
    """
    points = ((data or {}).get("results") or (data or {}).get("dynamics")
              or (data or {}).get("points") or [])
    out = []
    for p in points:
        when = (p.get("date") or p.get("period") or p.get("from") or "")[:10]
        value = p.get("count") if p.get("count") is not None else p.get("value")
        if when:
            out.append({"month": when[:7], "value": int(value or 0)})
    return out


def run(date_s: str) -> dict:
    import serp_watchlist
    phrases = serp_watchlist.build(date_s, cap=PHRASES_CAP)
    if not phrases:
        return {"available": False, "reason": "ядро фраз пусто"}
    cfg = config_mod.load()
    bud = budget_mod.BudgetController(cfg, today=date_s)
    cli = client_mod.WordstatClient(bud, cfg)
    items, errors, stopped = [], 0, None
    for phrase in phrases:
        res = cli.dynamics(phrase, reason="momentum-weekly", today=date_s)
        if res["status"] in ("budget_blocked", "quota_exceeded"):
            stopped = res.get("reason") or cli.stopped_by or res["status"]
            break
        if res["status"] != "ok" or not res.get("data"):
            errors += 1
            continue
        series = parse_dynamics(res["data"])
        items.append({"phrase": phrase, "series": series,
                      **acceleration(series)})
    order = {"accelerating": 0, "decelerating": 1, "flat": 2,
             "low_base": 3, "insufficient_series": 4}
    items.sort(key=lambda i: (order.get(i.get("trend"), 9),
                              -(i.get("recent_avg") or 0)))
    return {
        "available": bool(items),
        "date": date_s,
        "phrases_planned": len(phrases),
        "collected": len(items),
        "errors": errors,
        "stopped_by": stopped,
        "accelerating": [i["phrase"] for i in items
                         if i.get("trend") == "accelerating"],
        "decelerating": [i["phrase"] for i in items
                         if i.get("trend") == "decelerating"],
        "items": items,
        "note": ("помесячная динамика Вордстата по коммерческому ядру; "
                 "последний месяц — завершённый; проценты при базе <50 "
                 "показов/мес не публикуются (low_base)"),
    }


def main() -> int:
    date_s = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(
        dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    res = run(date_s)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"momentum-{date_s}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"momentum: {res.get('collected', 0)} фраз, ускоряются "
          f"{len(res.get('accelerating', []))}, замедляются "
          f"{len(res.get('decelerating', []))}"
          + (f", остановлено: {res['stopped_by']}" if res.get("stopped_by")
             else "") + f" -> {out}")
    return 0 if res.get("available") else 1


if __name__ == "__main__":
    sys.exit(main())
