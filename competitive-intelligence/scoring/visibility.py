"""Взвешенная видимость и B2B Search Share — главный KPI контура.

Чистые функции без сети: считают долю взвешенной поисковой видимости внутри
контролируемого B2B-семантического поля (раздел 10 задания). Не «процент
присутствия», а вес позиции × спрос × коммерческий интент.

Все коэффициенты берутся из scoring/config.json и не зашиваются в код: Share
обязан быть воспроизводимым, а кривая CTR — предметом калибровки.
"""
from __future__ import annotations

import json
import os
from typing import Iterable

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def ctr_weight(position: int, config: dict) -> float:
    """Вес позиции по зафиксированной CTR-кривой. Вне топ-20 — ноль."""
    return float(config["ctr_кривая"].get(str(position), 0.0))


def feature_factor(features: Iterable[str] | None, config: dict) -> float:
    """Понижающий множитель органического CTR для SERP с крупными элементами.

    Берётся самый сильный (минимальный) множитель из присутствующих:
    AI-ответ давит выдачу сильнее товарной галереи, и складывать эффекты
    было бы двойным счётом.
    """
    factors = config["коэффициент_serp_features"]
    present = [factors[f] for f in (features or []) if f in factors]
    return min(present) if present else factors["без_особенностей"]


def query_visibility(position: int, config: dict, *,
                     demand_weight: float = 1.0,
                     commercial_intent: float = 1.0,
                     b2b_intent: float = 1.0,
                     revenue_weight: float = 1.0,
                     features: Iterable[str] | None = None) -> float:
    """Взвешенная видимость одного домена по одному запросу.

    Множители нормализованы к 1.0 и по умолчанию нейтральны: пока спрос и
    интент не размечены (Phase 1), Share считается по чистой CTR-кривой, и
    это честно отражается в письме пометкой «Scoring: базовый».
    """
    return (ctr_weight(position, config)
            * feature_factor(features, config)
            * demand_weight * commercial_intent * b2b_intent * revenue_weight)


def share(domain_visibility: float, total_visibility: float) -> float | None:
    """Доля домена во взвешенной видимости поля.

    Возвращает None, а не ноль, когда поле пустое: отсутствие данных нельзя
    показывать как нулевую видимость (правило NO DATA ≠ 0).
    """
    if total_visibility <= 0:
        return None
    return domain_visibility / total_visibility
