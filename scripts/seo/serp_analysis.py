#!/usr/bin/env python3
"""Разбор SERP-архива: наша позиция, конкуренты, слабые выдачи, изменения.

Читает срезы serp_watch (reports/seo/serp/<дата>-serp.jsonl) и отвечает
на управленческие вопросы: где мы стоим в реальной выдаче Яндекса (не по
усреднённой позиции Вебмастера, а по факту топа), кто занимает топ по нашим
коммерческим запросам, какие выдачи «слабые» (маркетплейсы и форумы вместо
специализированных конкурентов — лёгкая точка входа, механика №18) и что
изменилось к прошлому срезу (семя детектора вытеснения, №16).

С 03.09.2026 тот же разбор строится и по Google (engine="google"): срез
serp_google.py через xmlriver, российское местоположение, файл
<дата>-serp-google.jsonl. Сбор еженедельный, поэтому окно свежести шире.
Второй источник — только чтение готового среза: собственных запросов к
xmlriver здесь нет (правило «один сбор — все потребители»).

cross_engine_gap() сопоставляет обе выдачи по одному ядру: запросы, где
Яндекс уже держит нас в топ-10, а Google не показывает вовсе, — главный
управленческий вопрос по Google (индексация, релевантность или авторитет
домена), и без российской Google-выдачи он был неразличим.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

SERP_DIR = pathlib.Path("reports/seo/serp")
LOOKBACK_DAYS = 7
OUR_DOMAIN = "biz-soft.pro"

# Поисковые системы: суффикс файла среза, регион по умолчанию, окно свежести.
# Google собирается раз в неделю (data/seo/xmlriver.json), окно — 8 дней с
# запасом на дрейф расписания; Яндекс — ежедневно, окно 7 дней.
ENGINES = {
    "yandex": {"suffix": "-serp.jsonl", "region": "213", "lookback": LOOKBACK_DAYS,
               "label": "Яндекса", "where": "Search API, регион Москва"},
    "google": {"suffix": "-serp-google.jsonl", "region": "2643", "lookback": 8,
               "label": "Google", "where": "xmlriver, местоположение Россия"},
}

# Классификация доменов топа. Списки консервативны и пополняются по фактам
# из архива; всё неизвестное честно остаётся «прочие».
MARKETPLACES = {
    "avito.ru", "wildberries.ru", "ozon.ru", "market.yandex.ru",
    "megamarket.ru", "aliexpress.ru", "plati.market", "ggsel.net",
    "kupikod.com", "payment.mts.ru",
}
FORUMS_INFO = {
    "otzovik.com", "irecommend.ru", "pikabu.ru", "habr.com", "vc.ru",
    "dtf.ru", "dzen.ru", "ya.ru", "youtube.com", "rutube.ru",
    "wikipedia.org", "ru.wikipedia.org",
}
SPECIALIST_COMPETITORS = {
    "softline.ru", "store.softline.ru", "syssoft.ru", "allsoft.ru",
    "softmagazin.ru", "migsoft.ru", "softkey.ru", "1csoft.ru",
    "digitalsoft.ru", "softorg.ru", "itshop.ru", "ml-soft.ru",
}
# Платёжные посредники «оплата зарубежных сервисов из РФ» — главная
# конкурентная группа по факту первого среза 30.08.2026 (в топ-10 наших
# запросов чаще софтверных магазинов). Прямые конкуренты BIZSoft по нише.
PAYMENT_INTERMEDIARIES = {
    "platipomiru.com", "raketapay.ru", "pipl.io", "finteka.io",
    "aifory.pro", "kartli.io", "card-open.ru", "remoney.ru",
    "xn----7sbb6agbixj6ab4j.xn--p1ai", "oplatym.ru", "payservice.pro",
}

WEAK_SHARE = 0.6      # доля маркетплейсов+форумов в топ-10, с которой выдача «слабая»


def classify_domain(domain: str) -> str:
    d = (domain or "").lower().removeprefix("www.")
    if d == OUR_DOMAIN:
        return "ours"
    if d in PAYMENT_INTERMEDIARIES:
        return "intermediary"
    if d in SPECIALIST_COMPETITORS:
        return "competitor"
    if d in MARKETPLACES:
        return "marketplace"
    if d in FORUMS_INFO:
        return "info"
    return "other"


def _load(date_s: str, offset_from: str | None = None,
          engine: str = "yandex") -> dict | None:
    """Последний срез не старше окна свежести системы; offset_from — искать
    строго раньше этой даты (для сравнения с предыдущим срезом)."""
    spec = ENGINES[engine]
    date = dt.date.fromisoformat(date_s)
    start = 1 if offset_from else 0
    for back in range(start, spec["lookback"] + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        if offset_from and d >= offset_from:
            continue
        p = SERP_DIR / f"{d}{spec['suffix']}"
        if not p.exists():
            continue
        rows = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
        rows = [r for r in rows if not r.get("error") and r.get("top")]
        if rows:
            return {"date": d, "rows": rows}
    return None


def _our_position(top: list[dict]) -> int | None:
    for i, doc in enumerate(top, 1):
        if classify_domain(doc.get("domain", "")) == "ours":
            return i
    return None


def build(date_s: str, region: str | None = None,
          engine: str = "yandex") -> dict:
    """Анализ по одной системе и одному региону: выдача регионозависима, и
    смешивание Москвы с СПб (или Яндекса с Google) в одних счётчиках дало
    бы кашу вместо позиций."""
    spec = ENGINES[engine]
    region = region or spec["region"]
    data = _load(date_s, engine=engine)
    if not data:
        reason = ("SERP-архив ещё не накоплен (workflow seo-serp-watch)"
                  if engine == "yandex" else
                  f"свежего Google-среза нет (сбор еженедельный, окно "
                  f"{spec['lookback']} дней; шаг Collect Google SERP в "
                  f"seo-serp-watch)")
        return {"available": False, "engine": engine, "reason": reason,
                "items": []}
    region_rows = [r for r in data["rows"]
                   if (r.get("region") or spec["region"]) == region]
    if not region_rows:
        return {"available": False, "engine": engine,
                "reason": f"по региону {region} срезов ещё нет",
                "items": []}
    prev = _load(date_s, offset_from=data["date"], engine=engine)
    prev_tops = {r["query"]: {d.get("domain", "").lower().removeprefix("www.")
                              for d in (r.get("top") or [])[:10]}
                 for r in (prev or {}).get("rows", [])
                 if (r.get("region") or spec["region"]) == region}

    items, domain_hits = [], {}
    ours_in_top10 = weak = 0
    for r in region_rows:
        top = r["top"]
        top10 = top[:10]
        pos = _our_position(top)
        kinds = [classify_domain(d.get("domain", "")) for d in top10]
        weak_share = (sum(k in ("marketplace", "info") for k in kinds)
                      / len(top10)) if top10 else 0.0
        is_weak = weak_share >= WEAK_SHARE
        ours_in_top10 += bool(pos and pos <= 10)
        weak += is_weak
        for d in top10:
            dom = (d.get("domain") or "").lower().removeprefix("www.")
            if dom and classify_domain(dom) != "ours":
                domain_hits[dom] = domain_hits.get(dom, 0) + 1
        entered = left = []
        if r["query"] in prev_tops:
            cur = {(d.get("domain") or "").lower().removeprefix("www.")
                   for d in top10}
            entered = sorted(cur - prev_tops[r["query"]])
            left = sorted(prev_tops[r["query"]] - cur)
        items.append({
            "query": r["query"],
            "our_position": pos,
            "weak_share": round(weak_share, 2),
            "weak": is_weak,
            "top3": [{"domain": d.get("domain"), "kind":
                      classify_domain(d.get("domain", ""))} for d in top[:3]],
            "entered_top10": entered,
            "left_top10": left,
        })
    items.sort(key=lambda i: (i["our_position"] or 99, -i["weak_share"]))
    competitors = sorted(
        ((d, n, classify_domain(d)) for d, n in domain_hits.items()),
        key=lambda t: -t[1])
    return {
        "available": True,
        "engine": engine,
        "as_of": data["date"],
        "region": region,
        "prev_date": (prev or {}).get("date"),
        "queries_total": len(region_rows),
        "ours_in_top10": ours_in_top10,
        "weak_serps": weak,
        "items": items,
        "top_domains": [{"domain": d, "hits": n, "kind": k}
                        for d, n, k in competitors[:15]],
        "note": (f"реальная выдача {spec['label']} ({spec['where']}, "
                 "топ-20); «слабая» выдача — ≥60% топ-10 занято "
                 "маркетплейсами и форумами, а не специализированными "
                 "конкурентами"),
    }


def _norm_query(q: str) -> str:
    return " ".join((q or "").lower().split())


def cross_engine_gap(date_s: str, yandex_region: str = "213",
                     google_region: str | None = None) -> dict:
    """Разрыв между системами по одному ядру запросов.

    Три множества по запросам, измеренным в обеих выдачах:
      - «яндекс_топ10_google_вне_топ20» — Яндекс держит нас в топ-10, Google
        не показывает в топ-20: страница есть и релевантна (Яндекс её
        ранжирует), значит вопрос к Google — индексация, авторитет или
        конкурентоспособность страницы именно там;
      - «google_топ10_яндекс_вне_топ20» — обратное;
      - «в_обеих_топ10» — счётчик, где всё в порядке.
    Позиции берутся как есть, без усреднения; сравнивать их как равноточные
    нельзя (разные системы), сравнивается только присутствие в топе.
    """
    yx = _load(date_s, engine="yandex")
    g = _load(date_s, engine="google")
    if not yx or not g:
        return {"available": False,
                "reason": ("нет свежего среза " +
                           ("Google" if yx else "Яндекса") +
                           " — сопоставлять нечего")}
    google_region = google_region or ENGINES["google"]["region"]
    ymap = {_norm_query(r["query"]): r for r in yx["rows"]
            if (r.get("region") or "213") == yandex_region}
    gmap = {_norm_query(r["query"]): r for r in g["rows"]
            if (r.get("region") or google_region) == google_region}
    common = sorted(set(ymap) & set(gmap))
    ya_only, g_only, both = [], [], 0
    for key in common:
        ypos = _our_position(ymap[key].get("top") or [])
        gpos = _our_position(gmap[key].get("top") or [])
        if ypos and ypos <= 10 and gpos and gpos <= 10:
            both += 1
        elif ypos and ypos <= 10 and not gpos:
            ya_only.append({
                "query": ymap[key]["query"], "yandex_position": ypos,
                "google_position": None,
                "google_top3": [d.get("domain") for d in
                                (gmap[key].get("top") or [])[:3]],
            })
        elif gpos and gpos <= 10 and not ypos:
            g_only.append({
                "query": gmap[key]["query"], "google_position": gpos,
                "yandex_position": None,
                "yandex_top3": [d.get("domain") for d in
                                (ymap[key].get("top") or [])[:3]],
            })
    ya_only.sort(key=lambda i: i["yandex_position"])
    g_only.sort(key=lambda i: i["google_position"])
    return {
        "available": True,
        "as_of_yandex": yx["date"],
        "as_of_google": g["date"],
        "queries_compared": len(common),
        "both_top10": both,
        "yandex_top10_google_absent": ya_only,
        "google_top10_yandex_absent": g_only,
        "note": ("запросы одного ядра, измеренные в обеих системах: Яндекс "
                 "(Москва) и Google (Россия, xmlriver). Сравнивается "
                 "присутствие в топе, а не позиции: системы разные"),
    }
