"""Threat Score 0–100 — «насколько этот конкурент опасен сейчас».

Версия 1.3.0 (после четвёртой внешней рецензии, 31.08.2026).

В 1.0.0 счёт складывался из доли видимости, присутствия в ТОП-3 и присутствия
в ТОП-10. Это давало тройной учёт одного преимущества: домен на втором месте
попадал во все три слагаемых сразу. С 1.1.0 компонентов три, и они
ортогональны:

  Presence 50    — взвешенная видимость: где и как высоко домен вообще стоит;
  Superiority 20 — доля запросов, где он стоит **выше BIZSoft**: это про
                   отношение к нам, а не про абсолютную высоту;
  Momentum 30    — изменение присутствия между сравнимыми окнами наблюдений.

**Явные формулы (1.3.0).** До этой версии компоненты считались inline и
описывались словами; внешний аудит справедливо потребовал записать их как
функции, чтобы поведение на краях было проверяемым, а не подразумеваемым.

    presence(share)         = 50 · min(share / 0.15, 1)          → [0; 50]
    superiority(above, n)   = 20 · min(above / n, 1)             → [0; 20]
    momentum(Δ п.п.)        = 30 · min(max(Δ, 0) / 2.0, 1)       → [0; 30]

Все три монотонно не убывают по своему аргументу и насыщаются в точке,
вынесенной в конфиг. Ни один не может стать отрицательным.

**Поведение при отрицательной динамике задано явно:** Momentum = 0. Конкурент,
теряющий долю, не становится безопаснее тех позиций, которые он занимает
сегодня, — но и не получает добавки за падение. Отрицательное значение
компонента означало бы, что падение уменьшает угрозу ниже текущего
присутствия, а присутствие уже измерено компонентом Presence. Само изменение
не теряется: оно хранится в breakdown как «динамика_пп» и выводится в отчёте
со знаком, поэтому «падает» и «стоит на месте» различимы, хотя обе ситуации
дают ноль баллов динамики.

**Две шкалы вместо одной.** Пока сравнимых измерений меньше шести, динамика
не считается вовсе, и оценка живёт на шкале 0–70. Полная шкала 0–100
включается только с появлением истории. Иначе оценка 32 из достижимых 70
выглядела бы как 32 из 100, и переход к полному режиму давал бы 62 — рост
вдвое без единого движения конкурента. Режим хранится рядом с числом, и
сравнивать оценки через его границу запрещено.

**Устойчивость ядра (1.3.0).** История долей сравнима только при неизменном
составе мониторингового ядра: доля считается внутри поля, и добавление или
удаление запросов меняет знаменатель у всех сразу. Если ядро между
измерениями менялось, динамика не считается и оценка остаётся в базовом
режиме — это тот же запрет, что и «мало измерений», просто по другой причине.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

WEIGHT_PRESENCE = 50
WEIGHT_SUPERIORITY = 20
WEIGHT_MOMENTUM = 30
# Историческое имя компонента (до 1.3.0 назывался Dominance).
WEIGHT_DOMINANCE = WEIGHT_SUPERIORITY

# Доля видимости, при которой компонент Presence набирает максимум. Значение
# выбрано по текущей конфигурации поля и подлежит эмпирической калибровке:
# это точка насыщения функции, а не утверждение об уровне лидерства.
PRESENCE_SATURATION = 0.15
# Изменение доли между окнами, при котором Momentum набирает максимум.
MOMENTUM_SATURATION_PP = 2.0
# Окно сглаживания — то же, что в общем фильтре значимости.
WINDOW = 3


# Режимы зрелости оценки. Числа из разных режимов между собой несравнимы:
# у них разные знаменатели, и рост «с 32 до 62» означал бы не усиление
# конкурента, а появление истории наблюдений.
MODE_BASE = "base_0_70"      # без истории: присутствие + превосходство
MODE_FULL = "full_0_100"     # с историей: плюс динамика

MAX_BASE = WEIGHT_PRESENCE + WEIGHT_SUPERIORITY   # 70
MAX_FULL = MAX_BASE + WEIGHT_MOMENTUM             # 100


@dataclass
class Threat:
    score: int
    confidence: str  # HIGH | MEDIUM | LOW
    mode: str = MODE_BASE
    scale_max: int = MAX_BASE
    breakdown: dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    momentum_pp: float | None = None

    @property
    def comparable_key(self) -> str:
        """Ключ сравнимости: оценки с разными ключами сопоставлять нельзя."""
        return self.mode


def _clamp(value: float, limit: float) -> float:
    return max(0.0, min(value, limit))


def presence_component(share: float | None,
                       saturation: float = PRESENCE_SATURATION) -> float:
    """Presence = 50 · min(доля / насыщение, 1). Нет доли — ноль баллов."""
    return _clamp(WEIGHT_PRESENCE * (share or 0.0) / saturation,
                  WEIGHT_PRESENCE)


def superiority_component(above_us: int | None, queries_total: int | None
                          ) -> float:
    """Superiority = 20 · min(запросов выше нас / всего запросов, 1).

    Знаменатель — число запросов поля, а не число его появлений: вопрос
    компонента «по какой доле нашего поля он стоит выше нас», и ответ должен
    быть долей, а не счётчиком.
    """
    total = max(queries_total or 0, 1)
    return _clamp(WEIGHT_SUPERIORITY * (above_us or 0) / total,
                  WEIGHT_SUPERIORITY)


def momentum_component(change_pp: float | None,
                       saturation: float = MOMENTUM_SATURATION_PP) -> float:
    """Momentum = 30 · min(max(Δ, 0) / насыщение, 1).

    Отрицательная динамика даёт ноль (см. docstring модуля): падение не
    уменьшает угрозу ниже уже занятых позиций. Само значение Δ сохраняется
    отдельно и показывается со знаком.
    """
    if change_pp is None:
        return 0.0
    return _clamp(WEIGHT_MOMENTUM * change_pp / saturation, WEIGHT_MOMENTUM)


def momentum_change(history: list[float]) -> float | None:
    """Изменение доли между сравнимыми окнами, в процентных пунктах.

    Требует шести валидных измерений: три на текущее окно и три на прошлое.
    Меньше — динамика не определена, и возвращается None, а не ноль:
    отсутствие тренда и нулевой тренд — разные утверждения.
    """
    if len(history) < WINDOW * 2:
        return None
    recent = statistics.median(history[-WINDOW:])
    earlier = statistics.median(history[-WINDOW * 2:-WINDOW])
    return 100 * (recent - earlier)


def score(card: dict, *, history: list[float] | None = None,
          queries_total: int | None = None,
          above_us: int | None = None,
          core_stable: bool = True) -> Threat:
    """Threat одного конкурента.

    `card` — запись домена из снимка (доля, топ-3, топ-10);
    `history` — ряд его долей по дням, старые в начале;
    `above_us` — по скольким запросам он стоит выше BIZSoft;
    `core_stable` — оставался ли состав ядра неизменным на всём ряду. При
    False динамика не считается: доля измеряется внутри поля, и смена состава
    поля двигает её у всех сразу, не отражая ничьего движения.
    """
    share = card.get("доля") or 0.0
    total = queries_total or max(card.get("топ10") or 1, 1)

    presence = presence_component(share)

    # Superiority: величина едет в самой карточке домена (registry считает её
    # из того же среза). Отдельный аргумент оставлен для проб и тестов.
    #
    # До 1.9.4 карточка её не несла, а аргумент не передавал ни один вызов —
    # и компонент весом 20 из 100 всегда подменялся приближением по ТОП-3, во
    # всех строках таблицы каждый день. Приближение не просто занижало оценку,
    # оно меняло порядок: конкурент, который редко берёт ТОП-3, но стабильно
    # стоит выше нас, уходил вниз рейтинга. 10.09.2026 aifory.pro при ТОП-3 по
    # 4 запросам стоял выше нас по 67 и висел седьмым вместо четвёртого.
    superiority_source = "по запросам выше BIZSoft"
    if above_us is None:
        above_us = card.get("выше_нас")
    if above_us is None:
        above_us = card.get("топ3") or 0
        superiority_source = ("приближение по ТОП-3: счётчик «выше нас» "
                              "не передан")
    superiority = superiority_component(above_us, total)

    breakdown = {
        "присутствие": round(presence, 1),
        "превосходство_над_нами": round(superiority, 1),
    }

    change = momentum_change(history or []) if core_stable else None
    if change is None:
        # Базовый режим: шкала 0–70, динамика не входит вовсе. Её вес не
        # добавляется нулём к сотне — иначе оценка выглядела бы низкой не
        # потому, что конкурент слаб, а потому, что мы мало наблюдали.
        if not core_stable:
            reason = ("состав ядра менялся: доли по разным ядрам "
                      "несопоставимы")
        else:
            needed = max(WINDOW * 2 - len(history or []), 0)
            reason = (f"динамика требует {WINDOW * 2} сравнимых измерений, "
                      f"не хватает {needed}")
        explanation = (f"базовый режим (шкала 0–{MAX_BASE}): {reason}; "
                       f"{superiority_source}")
        total_score = int(round(presence + superiority))
        return Threat(score=min(MAX_BASE, total_score), confidence="LOW",
                      mode=MODE_BASE, scale_max=MAX_BASE,
                      breakdown=breakdown, explanation=explanation,
                      momentum_pp=None)

    momentum = momentum_component(change)
    breakdown["динамика"] = round(momentum, 1)
    breakdown["динамика_пп"] = round(change, 2)
    direction = ("рост" if change > 0 else "падение" if change < 0
                 else "без изменения")
    explanation = (f"полный режим (шкала 0–{MAX_FULL}): {direction} доли между "
                   f"окнами {change:+.2f} п.п. (медианы по {WINDOW} измерений)"
                   + ("; падение баллов динамики не даёт" if change < 0 else "")
                   + f"; {superiority_source}")
    total_score = int(round(presence + superiority + momentum))
    return Threat(score=min(MAX_FULL, total_score), confidence="MEDIUM",
                  mode=MODE_FULL, scale_max=MAX_FULL,
                  breakdown=breakdown, explanation=explanation,
                  momentum_pp=round(change, 2))


def rank(cards: list[dict], *, histories: dict[str, list[float]] | None = None,
         queries_total: int | None = None,
         above_us: dict[str, int] | None = None,
         core_stable: bool = True) -> list[tuple[dict, Threat]]:
    """Конкуренты по убыванию Threat."""
    histories = histories or {}
    above_us = above_us or {}
    scored = [(card, score(card,
                           history=histories.get(card["домен"]),
                           queries_total=queries_total,
                           above_us=above_us.get(card["домен"]),
                           core_stable=core_stable))
              for card in cards]
    scored.sort(key=lambda pair: pair[1].score, reverse=True)
    return scored
