#!/usr/bin/env python3
"""Search Demand Coverage и Gap Analysis.

Покрытие считается по частотности, а не по числу ключевых слов: тысяча
низкочастотных фраз не равна одной фразе с тысячей показов, и метрика,
считающая строки, ведёт к неверным приоритетам.

Шесть уровней покрытия, каждый следующий строго вложен в предыдущий:
  discovered → page → indexed → top-10 → clicks → conversion-measured.

Классы разрывов A–H соответствуют разным действиям: страница, техническое SEO,
оптимизация, сниппет, конверсия, реклама, растущий спрос, снижение.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import audience                    # noqa: E402
import playbook                    # noqa: E402
import normalize as N  # noqa: E402

TOP_POSITION = 10.0
MIN_CLUSTER_DEMAND = 100      # ниже — кластер не выносится в разрывы
WEAK_CTR = 0.01


def load_site_signals(snapshot: dict) -> dict:
    """Сигналы сайта по фразам: показы, клики, позиция, поисковая система."""
    signals: dict[str, dict] = {}
    for engine in ("yandex", "google"):
        block = snapshot.get(engine) or {}
        if not block.get("available"):
            continue
        for e in block.get("entities") or []:
            if e.get("entity_type") != "query":
                continue
            key = N.morph_key(e["entity_id"])
            row = signals.setdefault(key, {"phrase": e["entity_id"]})
            row[f"{engine}_impressions"] = e.get("impressions")
            row[f"{engine}_clicks"] = e.get("clicks")
            row[f"{engine}_position"] = e.get("average_position")
    return signals


def load_pages(snapshot: dict) -> dict[str, dict]:
    pages = {}
    for p in ((snapshot.get("google") or {}).get("pages") or []):
        pages[p["entity_id"]] = p
    return pages


def enrich_universe(uni, snapshot: dict, vendor_urls: dict[str, str]) -> int:
    """Связать семантику с сайтом: URL, индексация, позиции, показы, клики."""
    signals = load_site_signals(snapshot)
    pages = load_pages(snapshot)
    indexed_urls = set(pages)
    linked = 0
    for row in uni.rows.values():
        cluster = row.get("cluster")
        url = vendor_urls.get(cluster)
        sig = signals.get(row["morph_key"], {})
        y_imp = sig.get("yandex_impressions")
        g_imp = sig.get("google_impressions")
        clicks = (sig.get("yandex_clicks") or 0) + (sig.get("google_clicks") or 0)
        impressions = (y_imp or 0) + (g_imp or 0)
        row.update({
            "mapped_url": url,
            "page_exists": bool(url),
            "indexed_yandex": bool(y_imp) if y_imp is not None else None,
            "indexed_google": (url in indexed_urls) if url else None,
            "yandex_position": sig.get("yandex_position"),
            "google_position": sig.get("google_position"),
            "yandex_impressions": y_imp,
            "google_impressions": g_imp,
            "clicks": clicks or None,
            "ctr": round(clicks / impressions, 4) if impressions else None,
        })
        if sig:
            linked += 1
    return linked


def clusters_of(uni) -> dict[str, dict]:
    """Свернуть фразы в кластеры: спрос кластера — сумма частотностей его фраз.

    Имя кластера приводится к вендору каталога, если такой есть. Часть фраз
    приходит под именем seed-запроса — «docker купить» вместо «docker», — и
    без приведения один и тот же вендор распадался на два кластера: один со
    страницей, другой без. Второй попадал в непокрытый спрос, хотя страница
    существует.
    """
    index = getattr(uni, "vendors", None) or {}

    def canonical(name: str) -> str:
        if not name or name in index.values():
            return name
        brand = audience.brand_of(name)
        return index.get(brand, name)

    out: dict[str, dict] = {}
    for row in uni.rows.values():
        if row.get("in_scope") is False:
            continue        # чужой интент в спрос BIZSoft не входит
        cluster = canonical(row.get("cluster") or "") or "без кластера"
        c = out.setdefault(cluster, {
            "cluster": cluster, "phrases": 0, "commercial_phrases": 0,
            "demand": 0, "commercial_demand": 0, "url": None, "page_exists": False,
            "indexed": False, "best_position": None, "impressions": 0, "clicks": 0,
            "top_phrases": [], "vendor": row.get("vendor"),
            "category": row.get("category"), "subclusters": {},
        })
        freq = row.get("wordstat_frequency") or 0
        c["phrases"] += 1
        c["demand"] += freq
        if row.get("intent") == "commercial":
            c["commercial_phrases"] += 1
            c["commercial_demand"] += freq
            c["top_phrases"].append({"phrase": row["phrase"], "frequency": freq})
            sub = row.get("subcluster") or "прочее"
            c["subclusters"][sub] = c["subclusters"].get(sub, 0) + freq
        if row.get("mapped_url"):
            c["url"] = row["mapped_url"]
            c["page_exists"] = True
        if row.get("indexed_yandex") or row.get("indexed_google"):
            c["indexed"] = True
        pos = row.get("yandex_position") or row.get("google_position")
        if pos is not None:
            c["best_position"] = pos if c["best_position"] is None else min(
                c["best_position"], pos)
        c["impressions"] += (row.get("yandex_impressions") or 0) + \
                            (row.get("google_impressions") or 0)
        c["clicks"] += row.get("clicks") or 0
    for c in out.values():
        c["top_phrases"].sort(key=lambda p: -p["frequency"])
        c["top_phrases"] = c["top_phrases"][:8]
        c["ctr"] = round(c["clicks"] / c["impressions"], 4) if c["impressions"] else None
    return out


def unattributed_demand(uni) -> dict:
    """Спрос, принадлежность которого не определена.

    Это не «спроса нет» и не «спрос есть»: голая фраза омонимичного бренда
    («zoom купить», «box купить») делится между вендором и посторонним товаром,
    и данными Вордстата их не разделить. В коммерческий спрос такие фразы не
    входят, иначе приоритеты уводит чужой товар. Но и молча выбрасывать их
    нельзя: тогда вендор с собственным лендингом становится невидим. Поэтому
    величина считается отдельно и показывается рядом — как объявленный предел
    измерения, а не как ноль.
    """
    rows = [r for r in uni.rows.values() if r.get("attribution") == "ambiguous"]
    by_cluster: dict[str, int] = {}
    for r in rows:
        freq = r.get("wordstat_frequency") or 0
        if r.get("intent") != "commercial" or not freq:
            continue
        key = r.get("cluster") or "без кластера"
        by_cluster[key] = by_cluster.get(key, 0) + freq
    total = sum(by_cluster.values())
    return {
        "available": bool(total),
        "total": total,
        "phrases": len([r for r in rows if r.get("intent") == "commercial"]),
        "by_cluster": dict(sorted(by_cluster.items(), key=lambda kv: -kv[1])),
        "reason": ("голая фраза омонимичного бренда: принадлежность вендору "
                   "не доказана и не опровергнута"),
    }


def demand_coverage(clusters: dict[str, dict], conversion_clusters: set[str]) -> dict:
    """Шесть уровней покрытия спроса, каждый считается по частотности."""
    total = sum(c["commercial_demand"] for c in clusters.values())
    if not total:
        return {"total_commercial_demand": 0, "levels": {}, "available": False}

    def share(pred) -> float:
        return round(sum(c["commercial_demand"] for c in clusters.values() if pred(c))
                     / total, 4)

    return {
        "available": True,
        "total_commercial_demand": total,
        "levels": {
            "page": share(lambda c: c["page_exists"]),
            "indexed": share(lambda c: c["indexed"]),
            "top10": share(lambda c: c["best_position"] is not None
                           and c["best_position"] <= TOP_POSITION),
            "clicks": share(lambda c: c["clicks"] > 0),
            # Ноль здесь означал бы «спрос покрыт страницами, но не
            # конвертируется». Пока цели не заведены в счётчике, верное
            # утверждение другое: конверсия по этим кластерам не измерялась.
            # Соседний уровень qualified_leads уже стоит как None — уровни с
            # одинаковым статусом обязаны выглядеть одинаково.
            "conversion_measured": (share(lambda c: c["cluster"] in conversion_clusters)
                                    if conversion_clusters else None),
            "qualified_leads": None,
        },
        "note": "Доли считаются по сумме частотностей коммерческих фраз кластера. "
                "Уровень «обращения» появится после подключения CRM.",
    }


def coverage_by(clusters: dict[str, dict], field: str) -> dict:
    """Покрытие в разрезе вендора, категории или подкластера."""
    groups: dict[str, dict] = {}
    for c in clusters.values():
        key = c.get(field) or "не определено"
        g = groups.setdefault(key, {"demand": 0, "covered": 0, "top10": 0, "clicks": 0})
        g["demand"] += c["commercial_demand"]
        if c["page_exists"]:
            g["covered"] += c["commercial_demand"]
        if c["best_position"] is not None and c["best_position"] <= TOP_POSITION:
            g["top10"] += c["commercial_demand"]
        if c["clicks"] > 0:
            g["clicks"] += c["commercial_demand"]
    for g in groups.values():
        d = g["demand"] or 1
        g["page_coverage"] = round(g["covered"] / d, 3)
        g["top10_coverage"] = round(g["top10"] / d, 3)
        g["click_coverage"] = round(g["clicks"] / d, 3)
    return dict(sorted(groups.items(), key=lambda kv: -kv[1]["demand"]))


GAP_ACTIONS = {
    "GAP-A": ("Спрос есть, страницы нет", "новая посадочная страница или материал"),
    "GAP-B": ("Страница есть, не индексируется", "техническое SEO"),
    "GAP-C": ("Индексируется, позиции слабые", "оптимизация страницы"),
    "GAP-D": ("Позиция хорошая, показы есть, переходов мало", "эксперимент со сниппетом"),
    "GAP-E": ("Трафик есть, конверсий мало", "работа с предложением и формой"),
    "GAP-F": ("Спрос большой, органика будет долгой", "исследование платного канала"),
    "GAP-G": ("Спрос растёт", "ранняя возможность"),
    "GAP-H": ("Спрос снижается", "снизить приоритет, наблюдать"),
}


def classify_gap(c: dict, trend: str, conversion_clusters: set[str]) -> str:
    """Один класс на кластер: тот, который определяет ближайшее действие."""
    if trend == "declining":
        return "GAP-H"
    if not c["page_exists"]:
        return "GAP-G" if trend == "growing" else "GAP-A"
    if not c["indexed"]:
        return "GAP-B"
    pos = c["best_position"]
    if pos is None or pos > TOP_POSITION:
        return "GAP-F" if c["commercial_demand"] >= 5000 else "GAP-C"
    if c["impressions"] and (c["ctr"] or 0) < WEAK_CTR:
        return "GAP-D"
    if c["clicks"] and c["cluster"] not in conversion_clusters:
        return "GAP-E"
    return "GAP-C"


def gap_analysis(uni, clusters: dict[str, dict],
                 conversion_clusters: set[str], today: str | None = None) -> list[dict]:
    today = today or dt.date.today().isoformat()
    out = []
    for c in clusters.values():
        if c["commercial_demand"] < MIN_CLUSTER_DEMAND:
            continue
        # Направление, по которому решение принято, или сервис для частных
        # лиц в список «что делать» не попадает. Раньше руководитель видел
        # там Spotify и ChatGPT Plus, которые сам же отклонил накануне.
        skip = audience.skip_reason(c["cluster"])
        if skip:
            continue
        top = c["top_phrases"][0]["phrase"] if c["top_phrases"] else c["cluster"]
        trend = uni.trend(top)["direction"]
        gap = classify_gap(c, trend, conversion_clusters)
        title, action = GAP_ACTIONS[gap]
        row = {
            "cluster": c["cluster"], "vendor": c["vendor"], "category": c["category"],
            "gap": gap, "gap_title": title, "recommended_action": action,
            "commercial_demand": c["commercial_demand"],
            "commercial_phrases": c["commercial_phrases"],
            "url": c["url"], "page_exists": c["page_exists"], "indexed": c["indexed"],
            "best_position": c["best_position"], "impressions": c["impressions"],
            "clicks": c["clicks"], "ctr": c["ctr"], "trend": trend,
            "top_phrases": c["top_phrases"][:5],
            "subclusters": dict(sorted(c["subclusters"].items(),
                                       key=lambda kv: -kv[1])[:4]),
        }
        # Ярлык класса называет тип задачи, но не задачу. Практический шаг,
        # готовый промт и измеримый признак завершения собираются здесь же:
        # без них список разрывов не превращается в работу.
        row.update(playbook.build(row, today))
        out.append(row)
    out.sort(key=lambda g: -g["commercial_demand"])
    return out
