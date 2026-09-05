#!/usr/bin/env python3
"""Кандидаты на тиражирование подтверждённого приёма.

Правило 10 (`reports/seo/README.md`): спрос Вордстата — показы в поиске, а не
покупки, и общая частотность бренда за покупательский спрос не выдаётся —
решение принимается по коммерческим фразам. До 02.09.2026 кандидатов выдавала
сортировка `src/data/vendor-demand.json`, то есть сумма ВСЕХ фраз вендора.
Вердикт CONTENT-001 на контрольной точке 02.09 предложил из-за этого
тиражировать статью на Google, Microsoft, GitHub, Unity и Docker, хотя
«коммерческие» фразы кластера Docker — это «dockers купить» (джинсы), а по
Google и Microsoft сайт вне топ-10 и переносить приём некуда.

Здесь общая частотность бренда не используется вовсе. Каждый профиль
расширения считает кандидатов по тому источнику, который отвечает за его
приём:

  snippet — сниппет меняет долю кликов при показе, а не показы и позиции,
            поэтому приём воспроизводим только там, где страница уже
            показывается и недобирает переходы (случай GAP-D). Порядок — по
            замеренным показам кластера в Вебмастере при средней позиции в
            топ-10 и CTR ниже порога; спрос Вордстата идёт основанием и
            вторым ключом сортировки, а не отбором. До 03.09.2026 отбор шёл
            по коммерческому спросу Вордстата, и в кандидатах стояли Adobe и
            Autodesk — страницы, у которых показов нет вовсе: разбор
            SEO-EXP-002 показал, что сниппет-тест на таких страницах не даёт
            вывода ни при какой длительности
            (`docs/seo/experiments/seo-exp-002-restart.md`);
  content — приём CONTENT-001 (статья под транзакционный интент + взаимная
            перелинковка с карточками) воспроизводим лишь там, где сошлись
            условия оригинала. Сам оригинал отобран не по Вордстату:
            в реестре у CONTENT-001 записано «Depositphotos — лидер спроса
            среди кластеров вендоров по данным Яндекс.Вебмастера», а гипотеза
            прямо опиралась на то, что «карточки и лендинг стоят на позициях
            3–9». Поэтому порядок здесь — по замеренным показам кластера в
            Вебмастере при средней позиции в топ-10; спрос Вордстата идёт
            основанием, а не сортировкой. Дополнительный гейт — минимум две
            карточки товара: без них не собрать ни таблицу тарифов, ни
            взаимную перелинковку.

Разница профилей не косметическая. У Postman коммерческий спрос Вордстата
нулевой (сборщик не отнёс «оплата postman юридическим лицом» к коммерческим
фразам), а в Вебмастере кластер даёт сотню показов на позиции 5 — по
Вордстату такой кластер не был бы предложен вовсе, хотя условия приёма
выполнены полностью.

Нет данных источника — кандидаты профиля не выдаются вовсе: пустой список
честнее списка, собранного не по тому признаку.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re

UNIVERSE = pathlib.Path("reports/seo/wordstat/semantic-universe.jsonl")
VENDORS_TS = pathlib.Path("src/data/vendors.ts")
REGISTRY = pathlib.Path("reports/seo/intelligence/seo-experiments.json")
YANDEX_DIR = pathlib.Path("reports/seo/data")
ICON_MAP = pathlib.Path("docs/catalog-product-icon-map.json")
CATALOG_DIR = pathlib.Path("scripts/catalog")

#: Минимум карточек товара для приёма «статья + взаимная перелинковка».
MIN_PRODUCTS_FOR_CONTENT = 2

#: Нижняя граница присутствия кластера в выдаче, показов в день. У кластера
#: CONTENT-001 baseline был 273 показа за 14 дней (20/день); десятая часть от
#: него отделяет кластер с присутствием от единичных показов-шума.
MIN_CLUSTER_IMPRESSIONS_PER_DAY = 2.0

#: «В топ-10» — строго средняя позиция ≤ 10 (правило 6 отчётности).
MAX_CLUSTER_POSITION = 10.0

#: Потолок CTR кластера для сниппет-приёма: выше — сниппет уже собирает
#: переходы, и менять его незачем. Порог из наблюдений GAP-D: у кластеров с
#: экспозицией в топ-10 CTR либо нулевой, либо сразу выше 2%.
MAX_CLUSTER_CTR_FOR_SNIPPET = 0.01

PROFILES = ("snippet", "content")


def commercial_demand() -> dict[str, int]:
    """Коммерческий спрос по вендорам: сумма частот фраз с intent=commercial."""
    out: dict[str, int] = {}
    try:
        with UNIVERSE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("in_scope") is False:      # чужой интент — не наш спрос
                    continue
                if row.get("intent") != "commercial":
                    continue
                vendor = row.get("vendor")
                if not vendor:
                    continue
                out[vendor] = out.get(vendor, 0) + (row.get("wordstat_frequency") or 0)
    except OSError:
        return {}
    return out


def vendor_slugs() -> dict[str, str]:
    """Вендор → slug посадочной страницы из реестра сайта."""
    try:
        text = VENDORS_TS.read_text(encoding="utf-8")
    except OSError:
        return {}
    return {vendor: slug for slug, vendor in
            re.findall(r"\{\s*slug:\s*'([^']+)',\s*vendor:\s*'([^']+)'", text)}


def products_by_vendor() -> dict[str, int]:
    """Число карточек товара по вендорам из оффлайн-источников каталога.

    Живой каталог лежит в Directus, сессии он недоступен; здесь берутся два
    снимка, которые есть в репозитории, и по каждому вендору выбирается
    больший — снимки сделаны в разное время и дополняют друг друга.
    """
    out: dict[str, int] = {}

    def bump(vendor: str, count: int) -> None:
        if vendor and count > out.get(vendor, 0):
            out[vendor] = count

    try:
        rows = json.loads(ICON_MAP.read_text(encoding="utf-8"))
        counts: dict[str, int] = {}
        for row in rows:
            v = row.get("vendor")
            if v:
                counts[v] = counts.get(v, 0) + 1
        for v, c in counts.items():
            bump(v, c)
    except (OSError, json.JSONDecodeError):
        pass

    for path in sorted(CATALOG_DIR.glob("*.json")):
        try:
            pack = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        vendor = (pack.get("vendor_entry") or {}).get("vendor")
        bump(vendor, len(pack.get("products") or []))

    return out


def _latest_yandex() -> dict | None:
    """Свежайшая выгрузка Вебмастера с непустым списком запросов."""
    files = sorted(YANDEX_DIR.glob("yandex-????-??-??.json"))
    for path in reversed(files):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        pq = data.get("popular_queries") or {}
        if pq.get("queries"):
            return pq
    return None


def _window_days(pq: dict) -> int:
    try:
        start = dt.date.fromisoformat(pq["date_from"])
        end = dt.date.fromisoformat(pq["date_to"])
    except (KeyError, TypeError, ValueError):
        return 1
    return max((end - start).days + 1, 1)


def cluster_visibility() -> dict[str, dict]:
    """Показы и средняя позиция по кластеру каждого вендора.

    Привязки «запрос → страница» у Вебмастера нет, поэтому запрос относится к
    кластеру по вхождению названия вендора или его slug — та же эвристика, что
    в `experiments.cluster_keys`, и такая же оценка, а не факт. Средняя позиция
    взвешивается показами: позиция запроса с тремя показами не должна весить
    столько же, сколько позиция запроса с полусотней.
    """
    pq = _latest_yandex()
    if not pq:
        return {}
    days = _window_days(pq)
    markers = {vendor: {vendor.lower(), slug.replace("-", " ")}
               for vendor, slug in vendor_slugs().items()}
    acc: dict[str, dict] = {}
    for row in pq["queries"]:
        text = (row.get("query_text") or "").lower()
        ind = row.get("indicators") or {}
        shows = ind.get("TOTAL_SHOWS") or 0
        clicks = ind.get("TOTAL_CLICKS") or 0
        position = ind.get("AVG_SHOW_POSITION")
        if not shows:
            continue
        for vendor, keys in markers.items():
            if not any(re.search(rf"(?<![a-zа-я0-9]){re.escape(k)}(?![a-zа-я0-9])", text)
                       for k in keys):
                continue
            a = acc.setdefault(vendor, {"impressions": 0.0, "clicks": 0.0,
                                        "weighted": 0.0, "positioned": 0.0})
            a["impressions"] += shows
            a["clicks"] += clicks
            if position is not None:
                a["weighted"] += position * shows
                a["positioned"] += shows
    return {vendor: {
        "impressions": int(a["impressions"]),
        "clicks": int(a["clicks"]),
        "ctr": (a["clicks"] / a["impressions"]) if a["impressions"] else None,
        "per_day": round(a["impressions"] / days, 2),
        "avg_position": (round(a["weighted"] / a["positioned"], 1)
                         if a["positioned"] else None),
        "window_days": days,
    } for vendor, a in acc.items()}


def busy_slugs(exclude_pages: list[str] | None = None) -> set[str]:
    """Слаги страниц, занятых действующими экспериментами.

    Занят и кластер, у которого эксперимент идёт на другом типе страниц:
    /alternatives/notion делает Notion негодным кандидатом на статью —
    два одновременных внедрения на одном кластере оценивались бы как одно
    (правило 7г отчётности).
    """
    busy = {p.rstrip("/").rsplit("/", 1)[-1] for p in (exclude_pages or [])}
    try:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return busy
    for exp in registry.get("experiments", []):
        if exp.get("status") == "closed":
            continue
        busy |= {p.rstrip("/").rsplit("/", 1)[-1] for p in exp.get("pages") or []}
    return busy


def candidates(exclude_pages: list[str] | None = None, limit: int = 10,
               profile: str = "snippet") -> list[dict]:
    """Кандидаты профиля с основанием по каждому: спрос, показы, карточки."""
    if profile not in PROFILES:
        raise ValueError(f"неизвестный профиль расширения: {profile}")
    slugs = vendor_slugs()
    busy = busy_slugs(exclude_pages)
    demand = commercial_demand()
    if profile == "content":
        return _content_candidates(slugs, busy, demand, limit)
    return _snippet_candidates(slugs, busy, demand, limit)


def _snippet_candidates(slugs: dict[str, str], busy: set[str],
                        demand: dict[str, int], limit: int) -> list[dict]:
    """Кластеры случая GAP-D: показы в топ-10 есть, переходов почти нет.

    Порядок — по замеренным показам: сниппет работает долей кликов, и чем
    больше показов, тем быстрее эффект станет различимым. Спрос Вордстата —
    второй ключ и основание в карточке кандидата, отбором он не служит.
    """
    visibility = cluster_visibility()
    if not visibility:
        return []
    out: list[dict] = []
    for vendor, vis in sorted(visibility.items(),
                              key=lambda kv: (-kv[1]["impressions"],
                                              -demand.get(kv[0], 0))):
        slug = slugs.get(vendor)
        if not slug or slug in busy:
            continue
        position = vis["avg_position"]
        if position is None or position > MAX_CLUSTER_POSITION:
            continue
        if vis["per_day"] < MIN_CLUSTER_IMPRESSIONS_PER_DAY:
            continue
        ctr = vis["ctr"]
        if ctr is None or ctr > MAX_CLUSTER_CTR_FOR_SNIPPET:
            continue
        out.append({"url": f"/vendors/{slug}", "vendor": vendor,
                    "impressions": vis["impressions"],
                    "impressions_per_day": vis["per_day"],
                    "clicks": vis["clicks"],
                    "ctr": round(ctr, 4),
                    "avg_position": position,
                    "window_days": vis["window_days"],
                    "commercial_demand": demand.get(vendor, 0)})
        if len(out) >= limit:
            break
    return out


def _content_candidates(slugs: dict[str, str], busy: set[str],
                        demand: dict[str, int], limit: int) -> list[dict]:
    """Кластеры, где условия CONTENT-001 выполняются целиком.

    Порядок — по замеренным показам кластера: приём перехватывает запросы,
    по которым сайт уже показывается, поэтому решает фактическое присутствие
    в выдаче, а не рыночный объём фраз.
    """
    visibility = cluster_visibility()
    if not visibility:
        return []
    products = products_by_vendor()
    out: list[dict] = []
    for vendor, vis in sorted(visibility.items(),
                              key=lambda kv: -kv[1]["impressions"]):
        slug = slugs.get(vendor)
        if not slug or slug in busy:
            continue
        position = vis["avg_position"]
        if position is None or position > MAX_CLUSTER_POSITION:
            continue
        if vis["per_day"] < MIN_CLUSTER_IMPRESSIONS_PER_DAY:
            continue
        cards = products.get(vendor, 0)
        if cards < MIN_PRODUCTS_FOR_CONTENT:
            continue
        out.append({"url": f"/vendors/{slug}", "vendor": vendor,
                    "impressions": vis["impressions"],
                    "impressions_per_day": vis["per_day"],
                    "avg_position": position,
                    "window_days": vis["window_days"],
                    "products": cards,
                    "commercial_demand": demand.get(vendor, 0)})
        if len(out) >= limit:
            break
    return out


def candidate_urls(exclude_pages: list[str] | None = None, limit: int = 10,
                   profile: str = "snippet") -> list[str]:
    return [c["url"] for c in candidates(exclude_pages, limit, profile)]


if __name__ == "__main__":  # ручная сверка списка перед решением
    import sys
    prof = sys.argv[1] if len(sys.argv) > 1 else "snippet"
    for c in candidates(limit=15, profile=prof):
        if prof == "content":
            print(f"{c['url']:28} показов {c['impressions']:>4} за "
                  f"{c['window_days']} дн., позиция {c['avg_position']}, "
                  f"карточек {c['products']}, спрос {c['commercial_demand']}")
        else:
            print(f"{c['url']:28} показов {c['impressions']:>4} за "
                  f"{c['window_days']} дн., позиция {c['avg_position']}, "
                  f"CTR {c['ctr'] * 100:.1f}% ({c['clicks']} кликов), "
                  f"спрос {c['commercial_demand']}")
