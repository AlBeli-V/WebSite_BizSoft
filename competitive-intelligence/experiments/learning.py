"""Что мы узнали: какие правки дают эффект, а какие нет.

Смысл раздела — превратить журнал экспериментов в правило отбора будущих
поручений. Пока наблюдений мало, раздел честно говорит, что выводов нет: это
важнее красивой таблицы. Ложный вывод на трёх наблюдениях дороже отсутствия
вывода — он на месяцы задаёт неверный приоритет работ.

Порог, с которого тип действия считается изученным, вынесен в конфиг. До него
рядом с любой цифрой стоит пометка «предварительно», и порядок действий в
рекомендациях не меняется.
"""
from __future__ import annotations

import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401
from experiments import journal as jr  # noqa: E402

# Сколько оценённых экспериментов одного типа нужно, чтобы считать вывод
# рабочим, а не наблюдением. Пять — компромисс: меньше не отличает сигнал от
# случайности даже на глаз, больше отодвигает первое применение на квартал.
MIN_FOR_CONCLUSION = 5


def settings(config: dict | None = None) -> int:
    block = ((config or {}).get("эксперименты") or {})
    return int(block.get("минимум_для_вывода", MIN_FOR_CONCLUSION))


def funnel(experiments: list[jr.Experiment]) -> dict:
    """Воронка: сколько предложено, внедрено, оценено и с каким исходом."""
    by_state = {state: 0 for state in
                (jr.STATE_PROPOSED, jr.STATE_WATCH, jr.STATE_DONE,
                 jr.STATE_CANCELLED)}
    verdicts = {jr.VERDICT_BETTER: 0, jr.VERDICT_FLAT: 0, jr.VERDICT_WORSE: 0}
    for exp in experiments:
        by_state[exp.state] = by_state.get(exp.state, 0) + 1
        verdict = (exp.outcome or {}).get("вердикт")
        if verdict in verdicts:
            verdicts[verdict] += 1
    return {"по_состояниям": by_state, "исходы": verdicts,
            "всего": len(experiments)}


def by_action_kind(experiments: list[jr.Experiment],
                   config: dict | None = None) -> list[dict]:
    """Сводка по типам действий: сколько наблюдений и какой медианный эффект."""
    minimum = settings(config)
    buckets: dict[str, list[float]] = {}
    wins: dict[str, int] = {}
    for exp in experiments:
        if exp.state != jr.STATE_DONE:
            continue
        net = (exp.outcome or {}).get("чистый_эффект")
        if net is None:
            continue
        for kind in exp.action_kinds or ["без типа"]:
            buckets.setdefault(kind, []).append(float(net))
            if (exp.outcome or {}).get("вердикт") == jr.VERDICT_BETTER:
                wins[kind] = wins.get(kind, 0) + 1
    rows = []
    for kind, values in sorted(buckets.items()):
        median = round(statistics.median(values), 2)
        rows.append({
            "тип": kind,
            "наблюдений": len(values),
            "медианный_эффект_позиций": median,
            "улучшений": wins.get(kind, 0),
            "вывод": _conclusion(len(values), median, minimum),
            "надёжность": "рабочая" if len(values) >= minimum else "предварительная",
        })
    rows.sort(key=lambda r: (r["надёжность"] != "рабочая",
                             r["медианный_эффект_позиций"]))
    return rows


def _conclusion(count: int, median: float, minimum: int) -> str:
    if count < minimum:
        return (f"наблюдений мало ({count} из {minimum}) — вывода нет, "
                f"цифра приведена как наблюдение")
    if median <= -1:
        return f"работает: медианный выигрыш {abs(median):.1f} позиций"
    if median >= 1:
        return f"вредит: медианная потеря {median:.1f} позиций"
    return "заметного эффекта не даёт"


def ranking(experiments: list[jr.Experiment],
            config: dict | None = None) -> dict[str, float]:
    """Порядок типов действий для будущих рекомендаций.

    Возвращает только изученные типы: пока наблюдений меньше порога, порядок
    действий в поручениях не меняется. Подстраивать приоритет работ под три
    случайных наблюдения — способ закрепить случайность в методике.
    """
    minimum = settings(config)
    return {row["тип"]: row["медианный_эффект_позиций"]
            for row in by_action_kind(experiments, config)
            if row["наблюдений"] >= minimum}


def summary_line(experiments: list[jr.Experiment],
                 config: dict | None = None) -> str:
    """Одна строка для письма: состояние цикла экспериментов."""
    data = funnel(experiments)
    states = data["по_состояниям"]
    verdicts = data["исходы"]
    if not experiments:
        return "Эксперименты: журнал пуст — цикл проверки только запускается."
    parts = [f"предложено {states.get(jr.STATE_PROPOSED, 0)}",
             f"на наблюдении {states.get(jr.STATE_WATCH, 0)}",
             f"оценено {states.get(jr.STATE_DONE, 0)}"]
    tail = ""
    if states.get(jr.STATE_DONE):
        tail = (f"; из оценённых улучшение у {verdicts[jr.VERDICT_BETTER]}, "
                f"без изменений {verdicts[jr.VERDICT_FLAT]}, "
                f"ухудшение {verdicts[jr.VERDICT_WORSE]}")
    return "Эксперименты: " + ", ".join(parts) + tail + "."
