"""MAIN SIGNAL — ровно одно главное наблюдение дня.

Требование раздела 24 задания: в письме один сигнал, не список. Выбор
устроен так, чтобы система не молчала в «тихий день» и не выдумывала
движение там, где его нет:

  * есть сравнимое прошлое → берётся самое значимое изменение, прошедшее
    фильтр значимости;
  * прошлого нет (первые дни) → структурный факт о поле: кто его держит.
    Это не «заглушка», а самая ценная информация первого дня.

**Сравнимое прошлое — не любое прошлое (правка 1.3.1).** Доля конкурента
считается внутри поля, и при изменении состава мониторингового ядра она
меняется у всех сразу, никого при этом не двигая. 01.09.2026 ядро выросло со
150 запросов до 369, и письмо сообщило «raketapay.ru просел на 4,4 п.п.» —
он не проседал, просто знаменатель стал другим. Пересчитать долю конкурента
по пересечению ядер нельзя: по-доменная видимость по каждому запросу не
хранится (для нашего домена она есть, для конкурентов — нет). Поэтому при
разном составе ядра сигнал об изменении не строится вовсе, а письмо получает
структурный сигнал с явной пометкой, почему сравнение недоступно.
"""
from __future__ import annotations

from datetime import datetime

import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401
from competitors import classifier  # noqa: E402
from decision_engine import kpi  # noqa: E402

# Изменение доли домена, ниже которого движение считается шумом (п.п.)
SIGNIFICANT_DOMAIN_PP = 1.0


@dataclass
class Signal:
    text: str
    kind: str  # "структура" | "рост_конкурента" | "падение_конкурента" | "нет_данных"
    evidence: list[str]


def _category_leader(snapshot: dict) -> tuple[str, float] | None:
    """Категория с наибольшей долей видимости среди тех, кто в рейтинге."""
    shares = snapshot.get("доли_по_категориям") or {}
    ranked = {cat: value for cat, value in shares.items()
              if classifier.in_main_ranking(cat)}
    if not ranked:
        return None
    cat = max(ranked, key=ranked.get)
    return cat, ranked[cat]


def structural_signal(snapshot: dict) -> Signal:
    """Кто держит поле — главный факт, пока нет истории для сравнения."""
    leader = _category_leader(snapshot)
    ours = (snapshot.get("наши_показатели") or {}).get("доля_видимости")
    leaders = snapshot.get("лидеры") or []
    if not leader:
        return Signal("Конкурентное поле пока не описано: ни одна категория "
                      "не набрала видимости.", "нет_данных", [])

    cat, share = leader
    name = classifier.CATEGORY_NAMES.get(cat, cat)
    top = [d for d in leaders if d.get("категория") == cat][:3]
    names = ", ".join(f"{d['домен']} {kpi.ru_number(100 * d['доля'])}%" for d in top)
    ours_text = (f"; BIZSoft — {kpi.ru_number(100 * ours)}%" if ours is not None else "")
    return Signal(
        text=(f"Коммерческую выдачу держат {name} — "
              f"{kpi.ru_number(100 * share)}% взвешенной видимости ({names}){ours_text}."),
        kind="структура",
        evidence=[d["домен"] for d in top],
    )


def comparable_cores(snapshot: dict, previous: dict) -> bool:
    """Совпадает ли состав ядра у двух снимков.

    Пустой отпечаток (снимок старого формата) считается несравнимым: лучше
    не сказать ничего, чем сказать про движение, которого не было.
    """
    a, b = kpi.core_hash(snapshot), kpi.core_hash(previous)
    return bool(a) and bool(b) and a == b


def change_signal(snapshot: dict, previous: dict) -> Signal | None:
    """Самое значимое изменение доли среди конкурентов основного рейтинга.

    Возвращает None, если состав ядра между днями различался: доли по разным
    ядрам несопоставимы, и «изменение» описывало бы правку списка запросов.
    """
    if not comparable_cores(snapshot, previous):
        return None
    now = {d["домен"]: d for d in (snapshot.get("лидеры") or [])}
    was = {d["домен"]: d for d in (previous.get("лидеры") or [])}
    best_domain, best_delta = None, 0.0
    for domain, card in now.items():
        prev_share = (was.get(domain) or {}).get("доля")
        if prev_share is None or card.get("доля") is None:
            continue
        delta_pp = 100 * (card["доля"] - prev_share)
        if abs(delta_pp) > abs(best_delta):
            best_domain, best_delta = domain, delta_pp
    if best_domain is None or abs(best_delta) < SIGNIFICANT_DOMAIN_PP:
        return None

    card = now[best_domain]
    direction = "вырос" if best_delta > 0 else "просел"
    kind = "рост_конкурента" if best_delta > 0 else "падение_конкурента"
    prev_date = previous.get("дата")
    since = (f"к {datetime.strptime(prev_date, '%Y-%m-%d').strftime('%d.%m')}"
             if prev_date else "к прошлому снимку")
    return Signal(
        text=(f"{best_domain} {direction} на {kpi.ru_number(abs(best_delta))} п.п. "
              f"видимости {since} (сейчас {kpi.ru_number(100 * card['доля'])}%, "
              f"топ-3 по {card['топ3']} запросам)."),
        kind=kind,
        evidence=[best_domain],
    )


def pick(snapshot: dict, previous: dict | None = None) -> Signal:
    """Главный сигнал дня: изменение, если оно значимо, иначе структура поля."""
    if previous:
        changed = change_signal(snapshot, previous)
        if changed is not None:
            return changed
    signal = structural_signal(snapshot)
    if previous and not comparable_cores(snapshot, previous):
        # Причина отсутствия сравнения называется прямо: молчаливый переход
        # к структурному сигналу выглядел бы как «изменений не было».
        core = (snapshot.get("ядро_запросов") or {}).get("запросов")
        core_was = (previous.get("ядро_запросов") or {}).get("запросов")
        # Сказать надо ровно то, что отказано: ПРЯМОЕ сравнение долей. До
        # 1.9.8 фраза звучала «сравнение не приводится», а строкой выше в
        # том же письме стояло «к 09.09 +0,63 п.п.» — сравнимая дельта по
        # пересечению составов. Обе величины верны и разные, но рядом они
        # читались как спор письма с самим собой.
        причина = (f"ядро выросло с {core_was} до {core} запросов"
                   if (core or 0) > (core_was or 0) else
                   f"состав ядра изменился ({core_was} → {core} запросов)")
        signal.text += (
            f" Прямое сравнение долей с {previous.get('дата')} не приводится: "
            f"{причина}, доли по разным ядрам несопоставимы. Сравнимая "
            f"величина считается по пересечению составов и стоит выше, "
            f"в показателях.")
    return signal
