"""Пакеты работ — точки атаки, сведённые в поручения.

Пятьдесят девять отдельных запросов невозможно поручить: это не задача, а
список. Но за ними стоит два десятка страниц, и одна правка страницы
закрывает сразу несколько запросов. Пакет работ — это страница, все её
запросы, суммарный спрос и оценка того, что даст доработка.

Оценка эффекта считается по той же кривой CTR, что и видимость: разница
между весом текущей позиции и весом целевой, умноженная на спрос. Это
оценка потенциала при выходе в ТОП-3, а не обещание — так и подписано.

**Индекс потенциала считается не всегда (правка 1.3.0).** До этой версии
запрос с неизмеренным спросом входил в сумму с нулевым весом, то есть
молча приравнивался к запросу без спроса. Это то же самое «нет данных = 0»,
которое система запрещает себе в остальных местах: пакет из пяти запросов,
где спрос известен по двум, получал индекс как будто три запроса никому не
нужны, и в очереди поручений опускался ниже, чем заслуживает.

Теперь правило явное:

  * индекс считается по тем запросам пакета, где спрос измерен;
  * рядом с индексом хранится покрытие спроса («3 из 5»), и оно попадает
    в отчёт: индекс, посчитанный по двум запросам из пяти, — это оценка
    по двум запросам, а не по пакету;
  * если спрос не измерен ни по одному запросу, индекс не считается вовсе
    (None, метка «не оценён»), пакет уходит в конец очереди и остаётся
    видимым как задача на доизмерение спроса, а не как задача без ценности.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401
from scoring import opportunity as opp_mod  # noqa: E402
from scoring import visibility  # noqa: E402

TARGET_POSITION = 3  # к чему стремимся: попадание в тройку
EFFORT_BY_SIZE = {1: "S", 3: "S", 6: "M"}  # число запросов → трудоёмкость

# Источник спроса, по которому допустимо считать прирост переходов.
# Частотность Wordstat описывает объём рынка за месяц — от неё можно перейти
# к оценке кликов через кривую CTR. Показы Вебмастера меряют другое: сколько
# раз показали нас за две недели. Умножать их на прирост CTR и называть
# результат «переходами рынка» нельзя — это разные знаменатели.
COMPARABLE_DEMAND_SOURCE = "wordstat"



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
    # Абсолютный спрос НЕ суммируется между источниками даже для показа:
    # 700 запросов рынка в месяц и 670 показов нам за две недели — величины
    # разной природы, и «1370» вводило бы в заблуждение, даже когда
    # математика уже разведена.
    demand_by_source: dict[str, int] = field(default_factory=dict)
    demand_queries_by_source: dict[str, int] = field(default_factory=dict)
    demand_sources: list[str] = field(default_factory=list)
    # Сколько запросов пакета имеют измеренный спрос: индекс потенциала
    # считается только по ним, и знать это соотношение обязательно.
    demand_measured_queries: int = 0
    demand_coverage: str = "0/0"
    demand_coverage_ratio: float = 0.0
    demand_index: float | None = None
    position_best: int | None = None
    position_worst: int | None = None
    rivals: list[str] = field(default_factory=list)
    opportunity_best: int = 0
    confidence: str = "MEDIUM"
    # Индекс потенциала — безразмерная величина для сравнения пакетов между
    # собой; в переходы не переводится. None означает «спрос не измерен ни по
    # одному запросу», а не «потенциала нет».
    potential_index: float | None = None
    potential_label: str = "средний"
    potential_note: str = ""
    # Оценка прироста переходов — только там, где весь спрос группы измерен
    # сопоставимой шкалой (частотность Wordstat). Иначе None: величину,
    # собранную из разных знаменателей, нельзя называть переходами.
    traffic_upside: float | None = None
    upside_note: str = ""
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
        by_source: dict[str, int] = {}
        queries_by_source: dict[str, int] = {}
        for attack in group:
            source = attack.get("demand_source", "none")
            if source == "none" or not attack.get("demand"):
                continue
            by_source[source] = by_source.get(source, 0) + attack["demand"]
            queries_by_source[source] = queries_by_source.get(source, 0) + 1

        # Два разных измерения потенциала — их нельзя подменять друг другом.
        #
        # potential_index: безразмерная величина для сравнения пакетов между
        # собой. Спрос входит нормированным по своей шкале, поэтому складывать
        # запросы с разными источниками здесь корректно. Считается только по
        # запросам с измеренным спросом; покрытие хранится рядом.
        #
        # traffic_upside: оценка прироста переходов в штуках. Допустима
        # только когда весь спрос группы измерен сопоставимой шкалой —
        # частотностью Wordstat. Смешивать её с показами Вебмастера значит
        # складывать «запросов рынка в месяц» с «показов нам за две недели»,
        # а потом называть сумму переходами.
        potential = 0.0
        upside = 0.0
        measured = 0
        sources = {a.get("demand_source", "none") for a in group}
        comparable = sources == {COMPARABLE_DEMAND_SOURCE}

        for attack in group:
            current = visibility.ctr_weight(attack["our_position"], config)
            gain = max(0.0, target_weight - current)
            raw = attack.get("demand")
            source = attack.get("demand_source", "none")
            normalized = opp_mod.demand_factor(raw, source)
            if normalized is None:
                continue  # спрос не измерен — запрос не участвует в индексе
            measured += 1
            potential += gain * normalized
            if comparable and raw:
                upside += gain * raw

        coverage_ratio = measured / len(group) if group else 0.0
        if measured == 0:
            potential_index = None
            potential_note = ("индекс не считается: спрос не измерен ни по "
                              "одному запросу пакета — сначала нужна оценка "
                              "спроса, а не работа со страницей")
        else:
            potential_index = round(potential, 4)
            potential_note = (
                f"индекс посчитан по {measured} запросам из {len(group)} — "
                f"по остальным спрос не измерен и они в индекс не входят"
                if measured < len(group)
                else f"спрос измерен по всем {len(group)} запросам пакета")

        named = ", ".join(sorted(s for s in sources if s != "none"))
        if comparable:
            traffic_upside = round(upside, 1)
            upside_note = ("оценка по частотности Wordstat: прирост кликов при "
                           "выходе в ТОП-3 и неизменном спросе")
        else:
            traffic_upside = None
            if not named:
                upside_note = ("перевод в переходы невозможен: спрос группы "
                               "не измерен")
            elif len(sources - {"none"}) > 1:
                upside_note = (f"перевод в переходы невозможен: спрос группы "
                               f"измерен разными шкалами ({named}) — складывать "
                               f"их и называть результат переходами нельзя")
            else:
                upside_note = (f"перевод в переходы невозможен: спрос измерен "
                               f"показами Вебмастера — это видимая нам часть "
                               f"спроса за две недели, а не объём рынка")

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
            demand_by_source=by_source,
            demand_queries_by_source=queries_by_source,
            demand_sources=sorted(s for s in sources if s != "none"),
            demand_measured_queries=measured,
            demand_coverage=f"{measured}/{len(group)}",
            demand_coverage_ratio=round(coverage_ratio, 3),
            demand_index=potential_index,
            position_best=min(positions),
            position_worst=max(positions),
            rivals=sorted({a["rival_domain"] for a in group}),
            opportunity_best=max(a["opportunity"] for a in group),
            confidence=confidence,
            potential_index=potential_index,
            potential_label="",  # проставляется после сортировки, см. ниже
            potential_note=potential_note,
            traffic_upside=traffic_upside,
            upside_note=upside_note,
            effort=effort,
            action=action,
            checklist=checklist,
        ))

    # Порядок — по индексу потенциала: он безразмерный и потому сравним
    # между пакетами с разными источниками спроса. Пакеты без измеренного
    # спроса индекса не имеют и уходят в конец: их нельзя ни сравнить с
    # остальными, ни выбросить — по ним сначала нужно измерить спрос.
    packages.sort(key=lambda p: (p.potential_index is not None,
                                 p.potential_index or 0.0,
                                 sum(p.demand_by_source.values())), reverse=True)

    # Метка потенциала — относительная, по месту в текущем наборе: верхняя
    # треть «высокий», средняя «средний», нижняя «низкий». Абсолютные пороги
    # здесь были бы произволом: величина индекса зависит от конфигурации
    # кривой CTR и от того, каким источником измерен спрос, поэтому
    # сравнивать её с фиксированным числом нельзя. Относительная шкала
    # отвечает на тот вопрос, который и задаёт руководитель: с чего начать.
    scored = [p for p in packages if p.potential_index is not None]
    count = len(scored)
    for index, package in enumerate(packages):
        package.package_id = f"WP-{index + 1:02d}"
        if package.potential_index is None:
            package.potential_label = "не оценён"
        elif package.potential_index <= 0:
            package.potential_label = "нет потенциала"
        elif index < max(1, count // 3):
            package.potential_label = "высокий"
        elif index < max(2, 2 * count // 3):
            package.potential_label = "средний"
        else:
            package.potential_label = "низкий"
    return packages


def to_dicts(packages: list[WorkPackage]) -> list[dict]:
    return [asdict(p) for p in packages]
