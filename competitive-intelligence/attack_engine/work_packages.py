"""Пакеты работ — точки атаки, сведённые в поручения.

Пятьдесят девять отдельных запросов невозможно поручить: это не задача, а
список. Но за ними стоит два десятка страниц, и одна правка страницы
закрывает сразу несколько запросов. Пакет работ — это страница, все её
запросы, суммарный спрос и оценка того, что даст доработка.

Оценка эффекта считается по той же кривой CTR, что и видимость: разница
между весом текущей позиции и весом целевой, умноженная на спрос. Это
оценка потенциала при выходе в ТОП-3, а не обещание — так и подписано.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401
from scoring import visibility  # noqa: E402

TARGET_POSITION = 3  # к чему стремимся: попадание в тройку
EFFORT_BY_SIZE = {1: "S", 3: "S", 6: "M"}  # число запросов → трудоёмкость


@dataclass
class WorkPackage:
    """Одно поручение: страница, её запросы и что с ней сделать."""
    package_id: str
    url: str
    page_kind: str          # vendor | product | blog | нет страницы
    subject: str            # о чём страница (вендор или продукт)
    queries: list[str] = field(default_factory=list)
    attack_ids: list[str] = field(default_factory=list)
    queries_count: int = 0
    demand_total: int = 0
    position_best: int | None = None
    position_worst: int | None = None
    rivals: list[str] = field(default_factory=list)
    opportunity_best: int = 0
    confidence: str = "MEDIUM"
    uplift_estimate: float = 0.0
    effort: str = "M"
    action: str = ""
    checklist: list[str] = field(default_factory=list)


def _page_kind(url: str) -> tuple[str, str]:
    """Тип страницы и её предмет — определяют, что именно на ней править."""
    if not url:
        return "нет страницы", ""
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    if "/vendors/" in url:
        return "vendor", tail
    if "/product/" in url:
        return "product", tail
    if "/blog/" in url:
        return "blog", tail
    return "другая", tail


def _action_for(kind: str, subject: str, queries: list[str]) -> tuple[str, list[str]]:
    """Что именно сделать со страницей и по каким пунктам это проверяется.

    Формулировки конкретны намеренно: «улучшить SEO» и «усилить контент» —
    запрещённые формулировки (раздел 20 задания), поручить их нельзя.
    """
    b2b = [q for q in queries
           if any(m in q for m in ("юридическ", "юрлиц", "юр лиц", "счет", "счёт",
                                   "ндс", "документ", "договор"))]
    common = [
        "Блок «Оплата по счёту для юридических лиц»: договор, счёт, НДС, "
        "закрывающие документы, ЭДО — на первом экране, не в подвале",
        "FAQ из вопросов покупателя-юрлица: как оплатить с расчётного счёта, "
        "какие документы придут, сроки поставки лицензии",
    ]
    if kind == "vendor":
        action = (f"Страница вендора {subject}: развернуть условия покупки "
                  f"юридическим лицом и лицензирование")
        checks = common + [
            "Таблица тарифов с указанием, что доступно для команд и компаний",
            "Ссылки с карточек товаров этого вендора на страницу вендора",
        ]
    elif kind == "product":
        action = (f"Карточка {subject}: довести условия для юрлиц до уровня "
                  f"конкурентов из выдачи")
        checks = common + [
            "Явное указание, что позиция продаётся организациям, а не физлицам",
            "Условия продления и добавления пользователей",
        ]
    elif kind == "blog":
        action = (f"Статья «{subject}»: добавить коммерческий блок — сейчас она "
                  f"отвечает на вопрос, но не ведёт к покупке")
        checks = [
            "Блок «Купить у нас» со ссылкой на карточку товара и вендора",
            "Условия для юрлиц кратко, с переходом на страницу оплаты",
            "Обновить дату материала и цены, если они устарели",
        ]
    else:
        action = "Создать посадочную страницу под эту группу запросов"
        checks = common + ["Определить, к какому вендору и продукту относится группа"]

    if b2b:
        checks.append(f"Проверить, что формулировки покрывают запросы вида "
                      f"«{b2b[0]}»")
    return action, checks


def build(attacks: list[dict], config: dict | None = None) -> list[WorkPackage]:
    """Сводит точки атаки в пакеты работ по страницам."""
    config = config or visibility.load_config()
    by_url: dict[str, list[dict]] = defaultdict(list)
    for attack in attacks:
        by_url[attack.get("our_url") or ""].append(attack)

    target_weight = visibility.ctr_weight(TARGET_POSITION, config)
    packages: list[WorkPackage] = []

    for url, group in by_url.items():
        kind, subject = _page_kind(url)
        positions = [a["our_position"] for a in group]
        demand = sum(a.get("demand") or 0 for a in group)

        # Оценка прироста переходов: сколько добавит выход в ТОП-3 при
        # неизменном спросе. Считается по каждому запросу отдельно, потому
        # что позиции разные.
        uplift = 0.0
        for attack in group:
            current = visibility.ctr_weight(attack["our_position"], config)
            gain = max(0.0, target_weight - current)
            uplift += gain * (attack.get("demand") or 0)

        confidences = {a.get("confidence") for a in group}
        confidence = ("LOW" if "LOW" in confidences
                      else "MEDIUM" if "MEDIUM" in confidences else "HIGH")
        effort = next((v for k, v in sorted(EFFORT_BY_SIZE.items())
                       if len(group) <= k), "L")
        action, checklist = _action_for(kind, subject, [a["query"] for a in group])

        packages.append(WorkPackage(
            package_id="",
            url=url or "нет страницы",
            page_kind=kind,
            subject=subject,
            queries=[a["query"] for a in group],
            attack_ids=[a["attack_id"] for a in group],
            queries_count=len(group),
            demand_total=demand,
            position_best=min(positions),
            position_worst=max(positions),
            rivals=sorted({a["rival_domain"] for a in group}),
            opportunity_best=max(a["opportunity"] for a in group),
            confidence=confidence,
            uplift_estimate=round(uplift, 1),
            effort=effort,
            action=action,
            checklist=checklist,
        ))

    # Порядок — по ожидаемому приросту: сначала то, что даст больше всего.
    packages.sort(key=lambda p: (p.uplift_estimate, p.demand_total), reverse=True)
    for number, package in enumerate(packages, start=1):
        package.package_id = f"WP-{number:02d}"
    return packages


def to_dicts(packages: list[WorkPackage]) -> list[dict]:
    return [asdict(p) for p in packages]
