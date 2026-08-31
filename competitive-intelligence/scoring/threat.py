"""Threat Score 0–100 — «насколько этот конкурент опасен сейчас».

Версия 1.1.0 (после внешнего аудита методики, 31.08.2026).

В 1.0.0 счёт складывался из доли видимости, присутствия в ТОП-3 и
присутствия в ТОП-10. Это давало тройной учёт одного преимущества: домен на
втором месте попадал во все три слагаемых сразу — его позиция уже учтена
весом внутри доли видимости, потом отдельно как ТОП-3, потом ещё раз как
ТОП-10 (тройка входит в десятку). Модель непропорционально усиливала
верхние позиции, и объяснить это было нечем.

Теперь три ортогональных компонента:

  Presence 50  — взвешенная видимость: где и как высоко домен вообще стоит;
  Dominance 20 — доля запросов, где он стоит **выше BIZSoft**: это про
                 отношение к нам, а не про абсолютную высоту, и с Presence
                 не пересекается;
  Momentum 30  — изменение присутствия между сравнимыми окнами наблюдений.

**Две шкалы вместо одной.** Пока сравнимых измерений меньше шести, динамика
не считается вовсе, и оценка живёт на шкале 0–70 (присутствие плюс
превосходство). Полная шкала 0–100 включается только с появлением истории.
Раньше вес динамики просто не добавлялся, и оценка 32 из достижимых 70
выглядела как 32 из 100 — при переходе к полному режиму то же самое
положение конкурента давало бы 62, то есть рост вдвое без единого его
движения. Режим хранится рядом с числом, и сравнивать оценки через его
границу запрещено.

Momentum считается по тому же сглаживанию, что и общий фильтр значимости
(медиана трёх последних измерений против медианы трёх предыдущих). В 1.0.0
здесь был «рост за сутки» — вторая, несогласованная модель динамики, из-за
которой Threat реагировал на шум, который основной фильтр отбрасывал.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

WEIGHT_PRESENCE = 50
WEIGHT_DOMINANCE = 20
WEIGHT_MOMENTUM = 30

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
# конкурента, а появление истории наблюдений. Режим хранится вместе с
# оценкой, чтобы сравнение через его границу нельзя было сделать по
# недосмотру.
MODE_BASE = "base_0_70"      # без истории: присутствие + превосходство
MODE_FULL = "full_0_100"     # с историей: плюс динамика

MAX_BASE = WEIGHT_PRESENCE + WEIGHT_DOMINANCE   # 70
MAX_FULL = MAX_BASE + WEIGHT_MOMENTUM           # 100


@dataclass
class Threat:
    score: int
    confidence: str  # HIGH | MEDIUM | LOW
    mode: str = MODE_BASE
    scale_max: int = MAX_BASE
    breakdown: dict[str, float] = field(default_factory=dict)
    explanation: str = ""

    @property
    def comparable_key(self) -> str:
        """Ключ сравнимости: оценки с разными ключами сопоставлять нельзя."""
        return self.mode


def _clamp(value: float, limit: float) -> float:
    return max(0.0, min(value, limit))


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
          above_us: int | None = None) -> Threat:
    """Threat одного конкурента.

    `card` — запись домена из снимка (доля, топ-3, топ-10);
    `history` — ряд его долей по дням, старые в начале;
    `above_us` — по скольким запросам он стоит выше BIZSoft.
    """
    share = card.get("доля") or 0.0
    total = queries_total or max(card.get("топ10") or 1, 1)

    presence = _clamp(WEIGHT_PRESENCE * share / PRESENCE_SATURATION,
                      WEIGHT_PRESENCE)

    # Dominance: если счётчик «выше нас» не передан, используем присутствие в
    # ТОП-3 как приближение — но помечаем это в объяснении, чтобы приближение
    # не выдавалось за измерение.
    dominance_source = "по запросам выше BIZSoft"
    if above_us is None:
        above_us = card.get("топ3") or 0
        dominance_source = "приближение по ТОП-3: счётчик «выше нас» не передан"
    dominance = _clamp(WEIGHT_DOMINANCE * above_us / total, WEIGHT_DOMINANCE)

    breakdown = {
        "присутствие": round(presence, 1),
        "превосходство_над_нами": round(dominance, 1),
    }

    change = momentum_change(history or [])
    if change is None:
        # Базовый режим: шкала 0–70, динамика не входит вовсе. Её вес не
        # добавляется нулём к сотне — иначе оценка выглядела бы низкой не
        # потому, что конкурент слаб, а потому, что мы мало наблюдали.
        confidence = "LOW"
        needed = WINDOW * 2 - len(history or [])
        explanation = (f"базовый режим (шкала 0–{MAX_BASE}): динамика требует "
                       f"{WINDOW * 2} сравнимых измерений, не хватает "
                       f"{max(needed, 0)}; {dominance_source}")
        total_score = int(round(presence + dominance))
        return Threat(score=min(MAX_BASE, total_score), confidence=confidence,
                      mode=MODE_BASE, scale_max=MAX_BASE,
                      breakdown=breakdown, explanation=explanation)

    momentum = _clamp(WEIGHT_MOMENTUM * change / MOMENTUM_SATURATION_PP,
                      WEIGHT_MOMENTUM)
    breakdown["динамика"] = round(momentum, 1)
    explanation = (f"полный режим (шкала 0–{MAX_FULL}): изменение доли между "
                   f"окнами {change:+.2f} п.п. (медианы по {WINDOW} измерений); "
                   f"{dominance_source}")
    total_score = int(round(presence + dominance + momentum))
    return Threat(score=min(MAX_FULL, total_score), confidence="MEDIUM",
                  mode=MODE_FULL, scale_max=MAX_FULL,
                  breakdown=breakdown, explanation=explanation)


def rank(cards: list[dict], *, histories: dict[str, list[float]] | None = None,
         queries_total: int | None = None,
         above_us: dict[str, int] | None = None) -> list[tuple[dict, Threat]]:
    """Конкуренты по убыванию Threat."""
    histories = histories or {}
    above_us = above_us or {}
    scored = [(card, score(card,
                           history=histories.get(card["домен"]),
                           queries_total=queries_total,
                           above_us=above_us.get(card["домен"])))
              for card in cards]
    scored.sort(key=lambda pair: pair[1].score, reverse=True)
    return scored
