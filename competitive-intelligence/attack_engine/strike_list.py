"""Strike List — выгоднейшие точки атаки, а не список всех проблем.

Кандидат в атаку (раздел 20 задания):
  * BIZSoft в выдаче на позиции 4–20 — есть куда расти и откуда дожимать;
  * конкурент из основного рейтинга стоит выше нас в топ-10;
  * запрос коммерческий и по возможности B2B.

Намеренно НЕ кандидаты: запросы, где мы уже в топ-3 (нечего отбирать) и где
нас нет в топ-20 вовсе (одной правкой страницы такой разрыв не закрывается —
это работа Content Gap, а не атаки).

Версия 1.1.0 различает два вида конкуренции. Если выше нас стоит компания,
способная продать тому же покупателю, — на кону сделка. Если только
официальный сайт вендора, статья или маркетплейс — сделку они не заберут, но
переход заберут, и это тоже потеря. Раньше такие запросы выпадали из поля
зрения целиком; теперь они остаются кандидатами с пометкой вида конкуренции,
а приоритет при равной выгоде отдаётся сделке.
"""
from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401
from competitors import classifier  # noqa: E402
from discovery import demand_source, serp_source  # noqa: E402
from scoring import intent as intent_mod  # noqa: E402
from scoring import opportunity as opp_mod  # noqa: E402

OURS = "biz-soft.pro"
OUR_POSITION_MIN = 4
OUR_POSITION_MAX = 20
RIVAL_POSITION_MAX = 10


@dataclass
class AttackCandidate:
    attack_id: str
    query: str
    engine: str
    region: str
    our_position: int
    our_url: str | None
    rival_domain: str
    rival_position: int
    rival_category: str
    # Тип конкуренции (разделение введено в 1.1.0 по замечанию внешнего
    # аудита). «Сделка» — выше нас стоит тот, кто способен продать тому же
    # покупателю. «Клик» — выше только площадки, которые сделку не заберут,
    # но забирают переход: официальные сайты вендоров, статьи, маркетплейсы.
    # Второе тоже наша потеря, просто другого рода, и молча выбрасывать её
    # из поля зрения нельзя.
    competition_kind: str
    demand: int | None
    demand_source: str
    commercial_intent: float
    b2b_intent: float
    opportunity: int
    confidence: str
    breakdown: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _find(top: list[dict], domain: str) -> tuple[int | None, str | None]:
    for index, item in enumerate(top, start=1):
        if serp_source.normalize_domain(item.get("domain", "")) == domain:
            return index, item.get("url")
    return None, None


def build(rows, *, region: str = "213", engine: str = "yandex",
          vendor_hosts: set[str] | None = None) -> list[AttackCandidate]:
    """Кандидаты в атаку по срезу, отсортированные по Opportunity."""
    vendor_hosts = classifier.vendor_domains() if vendor_hosts is None else vendor_hosts
    freq_table = demand_source.load_frequencies()
    candidates: list[AttackCandidate] = []

    for row in rows:
        if not row.has_data or row.region != region:
            continue
        if intent_mod.is_branded(row.query):
            continue  # бренд исключён из конкурентного поля (раздел 6)

        our_pos, our_url = _find(row.top, OURS)
        if our_pos is None or not (OUR_POSITION_MIN <= our_pos <= OUR_POSITION_MAX):
            continue

        # Кто стоит выше нас: отдельно тот, кто заберёт сделку, и отдельно
        # тот, кто заберёт только клик. В 1.0.0 запрос отбрасывался, если
        # выше не было ни одного «делового» конкурента — но если над нами
        # официальный сайт вендора и статья, переход мы всё равно теряем.
        business_rival = None
        serp_rival = None
        for index, item in enumerate(row.top[:RIVAL_POSITION_MAX], start=1):
            if index >= our_pos:
                break
            domain = serp_source.normalize_domain(item.get("domain", ""))
            if domain == OURS:
                continue
            category = classifier.categorize(domain, sample_urls=[item.get("url", "")],
                                             vendor_hosts=vendor_hosts)
            if serp_rival is None:
                serp_rival = (domain, index, category)
            if classifier.in_main_ranking(category) and business_rival is None:
                business_rival = (domain, index, category)
        rival = business_rival or serp_rival
        if rival is None:
            continue
        competition_kind = "сделка" if business_rival else "клик"

        commercial = intent_mod.commercial_intent(row.query)
        if commercial <= 0:
            continue  # некоммерческий запрос — не наша сделка

        demand_value, demand_kind = demand_source.demand(row.query)
        b2b = intent_mod.b2b_intent(row.query)
        opportunity = opp_mod.score(
            commercial=commercial, b2b=b2b, our_position=our_pos,
            has_page=our_url is not None,
            frequency=demand_value, demand_source=demand_kind,
        )

        candidates.append(AttackCandidate(
            attack_id="",  # проставляется после сортировки
            query=row.query, engine=engine, region=region,
            our_position=our_pos, our_url=our_url,
            rival_domain=rival[0], rival_position=rival[1], rival_category=rival[2],
            competition_kind=competition_kind,
            demand=demand_value, demand_source=demand_kind,
            commercial_intent=commercial, b2b_intent=b2b,
            opportunity=opportunity.score, confidence=opportunity.confidence,
            breakdown=opportunity.breakdown, notes=opportunity.notes,
        ))

    # Сначала — где на кону сделка, потом где только клик: при равном
    # Opportunity отобрать покупателя ценнее, чем отобрать посетителя.
    candidates.sort(key=lambda c: (c.competition_kind == "сделка",
                                   c.opportunity, c.b2b_intent), reverse=True)
    for number, candidate in enumerate(candidates, start=1):
        candidate.attack_id = f"ATT-{number:03d}"
    return candidates


def to_dicts(candidates: list[AttackCandidate]) -> list[dict]:
    return [asdict(c) for c in candidates]
