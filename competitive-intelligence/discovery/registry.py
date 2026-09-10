"""Реестр конкурентов: кто присутствует в нашем поле и с каким весом.

Собирается из SERP-срезов (свои + read-only из базового контура). Для каждого
домена считаются присутствие, позиции и взвешенная видимость; категория
ставится классификатором. B2B Confidence на этом шаге не считается — он
требует чтения страниц конкурента и появляется отдельным шагом, поэтому в
карточке остаётся None, а не ноль (NO DATA ≠ 0).

Реестр — append-only история: каждый прогон дописывает состояние на дату, а
не перезаписывает прошлое (правило хранилища).
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401 — подключает корень контура к sys.path
from competitors import classifier  # noqa: E402
from discovery import serp_source  # noqa: E402
from scoring import visibility  # noqa: E402

OURS = "biz-soft.pro"

REGISTRY_FILE = "registry.jsonl"
MAX_QUERY_EXAMPLES = 5
MAX_EVIDENCE_URLS = 3


@dataclass
class DomainCard:
    """Карточка домена на дату среза."""
    domain: str
    date: str
    engine: str
    region: str
    category: str
    appearances: int = 0
    top3: int = 0
    top10: int = 0
    best_position: int | None = None
    weighted_visibility: float = 0.0
    share: float | None = None
    in_main_ranking: bool = False
    query_examples: list[str] = field(default_factory=list)
    evidence_urls: list[str] = field(default_factory=list)
    # По скольким запросам поля домен стоит выше BIZSoft. Считается здесь, а
    # не у потребителя: величина выводится из того же среза, что и остальная
    # карточка, и обязана ехать вместе с ней. До 1.9.4 её не передавал ни один
    # вызов, и Threat всегда подменял её приближением по ТОП-3 — компонент
    # весом 20 из 100 ни разу не был измерен (разбор 10.09.2026).
    above_us: int = 0
    b2b_confidence: int | None = None
    b2b_signals: list[str] = field(default_factory=list)
    b2b_checked_at: str | None = None


def build(rows, config, *, engine: str = "yandex", region: str = "213",
          date: str | None = None) -> list[DomainCard]:
    """Строит карточки доменов по срезу.

    Строки с ошибкой источника пропускаются: NO DATA не должно ни повышать,
    ни понижать чью-либо видимость.
    """
    usable = [r for r in rows if r.has_data and r.region == region]
    acc: dict[str, dict] = defaultdict(lambda: {
        "appearances": 0, "top3": 0, "top10": 0, "best": None,
        "vis": 0.0, "queries": [], "urls": [], "above_us": 0,
    })

    for row in usable:
        # Наша позиция в этой выдаче — точка отсчёта для «выше нас». None
        # означает, что нас нет в собранной глубине: тогда выше нас стоят все,
        # кто в ней есть, и это не натяжка — по такому запросу конкурент
        # получает переход, а мы нет.
        our_index = next(
            (i for i, item in enumerate(row.top, start=1)
             if serp_source.normalize_domain(item.get("domain", "")) == OURS),
            None)
        for index, item in enumerate(row.top, start=1):
            domain = serp_source.normalize_domain(item.get("domain", ""))
            if not domain:
                continue
            bucket = acc[domain]
            bucket["appearances"] += 1
            if domain != OURS and (our_index is None or index < our_index):
                bucket["above_us"] += 1
            if index <= 3:
                bucket["top3"] += 1
            if index <= 10:
                bucket["top10"] += 1
            if bucket["best"] is None or index < bucket["best"]:
                bucket["best"] = index
            bucket["vis"] += visibility.query_visibility(index, config)
            if len(bucket["queries"]) < MAX_QUERY_EXAMPLES:
                bucket["queries"].append(row.query)
            if len(bucket["urls"]) < MAX_EVIDENCE_URLS and item.get("url"):
                bucket["urls"].append(item["url"])

    total = sum(b["vis"] for b in acc.values())
    vendor_hosts = classifier.vendor_domains()
    cards = []
    for domain, b in acc.items():
        category = classifier.categorize(domain, sample_urls=b["urls"],
                                         vendor_hosts=vendor_hosts)
        domain_share = visibility.share(b["vis"], total)
        cards.append(DomainCard(
            domain=domain,
            date=date or (usable[0].date if usable else ""),
            engine=engine,
            region=region,
            category=category,
            appearances=b["appearances"],
            top3=b["top3"],
            top10=b["top10"],
            best_position=b["best"],
            weighted_visibility=round(b["vis"], 6),
            share=round(domain_share, 6) if domain_share is not None else None,
            above_us=b["above_us"],
            in_main_ranking=classifier.in_main_ranking(category),
            query_examples=b["queries"],
            evidence_urls=b["urls"],
        ))
    cards.sort(key=lambda c: c.weighted_visibility, reverse=True)
    return cards


def append(cards: list[DomainCard], directory: str | None = None) -> str:
    """Дозаписывает состояние на дату в append-only реестр."""
    directory = directory or paths.COMPETITORS_DIR
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, REGISTRY_FILE)
    with open(path, "a", encoding="utf-8") as fh:
        for card in cards:
            fh.write(json.dumps(asdict(card), ensure_ascii=False) + "\n")
    return path
