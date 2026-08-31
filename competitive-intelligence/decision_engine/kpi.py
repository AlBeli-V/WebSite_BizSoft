"""KPI дня и вердикт письма — из снимка, и только из него.

Единственный источник цифр для письма и отчёта — канонический снимок дня
(правило методики базового контура: никаких пересчётов «на лету» в момент
вёрстки письма, иначе письмо и отчёт разойдутся в цифрах).

Вердикт (раздел 23 задания): 🟢 усиливаемся · 🟡 нейтрально-риск ·
🔴 значимое ухудшение · ⚪ недостаточно данных. Отдельно важно: пока истории
меньше двух сравнимых дней, вердикт обязан быть ⚪ — не потому что всё плохо,
а потому что сравнивать не с чем.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402

VERDICT_GROWTH = "🟢"
VERDICT_NEUTRAL = "🟡"
VERDICT_DECLINE = "🔴"
VERDICT_NO_DATA = "⚪"

# Порог значимости изменения доли видимости в процентных пунктах. Меньшее
# движение — шум одного дня, а не сигнал (раздел 9 задания).
SIGNIFICANT_SHARE_PP = 0.5


@dataclass
class Kpi:
    """Показатели дня и их изменение к сравнимому прошлому."""
    date: str
    share_yandex: float | None
    share_google: float | None
    top3: int | None
    top10: int | None
    queries: int | None
    share_delta_pp: float | None = None
    top3_delta: int | None = None
    top10_delta: int | None = None
    compared_with: str | None = None
    coverage_ok: bool = True
    maturity: str = "базовый"


def load_snapshot(date: str, directory: str | None = None) -> dict | None:
    directory = directory or paths.SNAPSHOTS_DIR
    path = os.path.join(directory, f"{date}-discovery.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def available_snapshots(directory: str | None = None) -> list[str]:
    directory = directory or paths.SNAPSHOTS_DIR
    files = glob.glob(os.path.join(directory, "*-discovery.json"))
    return sorted(os.path.basename(f)[: -len("-discovery.json")] for f in files)


def build_kpi(snapshot: dict, previous: dict | None = None) -> Kpi:
    """KPI дня. Дельты считаются только при наличии сравнимого прошлого."""
    ours = snapshot.get("наши_показатели") or {}
    coverage = snapshot.get("покрытие") or {}
    kpi = Kpi(
        date=snapshot.get("дата", ""),
        share_yandex=ours.get("доля_видимости"),
        share_google=coverage.get("google"),
        top3=ours.get("топ3"),
        top10=ours.get("топ10"),
        queries=ours.get("запросов_в_поле"),
        maturity=snapshot.get("зрелость_скоринга", "базовый"),
        coverage_ok=bool(coverage.get("яндекс_запросов_с_данными")),
    )
    if previous:
        prev = previous.get("наши_показатели") or {}
        if kpi.share_yandex is not None and prev.get("доля_видимости") is not None:
            kpi.share_delta_pp = round(
                100 * (kpi.share_yandex - prev["доля_видимости"]), 2)
        if kpi.top3 is not None and prev.get("топ3") is not None:
            kpi.top3_delta = kpi.top3 - prev["топ3"]
        if kpi.top10 is not None and prev.get("топ10") is not None:
            kpi.top10_delta = kpi.top10 - prev["топ10"]
        kpi.compared_with = previous.get("дата")
    return kpi


def verdict(kpi: Kpi) -> tuple[str, str]:
    """Вердикт дня и строка-объяснение к нему.

    Осторожность здесь важнее выразительности: система, которая на второй
    день наблюдений объявляет «усиливаемся», обесценивает собственный сигнал.
    """
    if not kpi.coverage_ok:
        return VERDICT_NO_DATA, ("Данные неполные: срез выдачи не собран — "
                                 "выводы по такому дню не делаем")
    if kpi.share_delta_pp is None:
        return VERDICT_NO_DATA, ("Недостаточно данных: базовая линия зафиксирована, "
                                 "сравнивать пока не с чем")
    if kpi.share_delta_pp >= SIGNIFICANT_SHARE_PP:
        return VERDICT_GROWTH, (f"Доля видимости выросла на "
                                f"{kpi.share_delta_pp:+.2f} п.п.")
    if kpi.share_delta_pp <= -SIGNIFICANT_SHARE_PP:
        return VERDICT_DECLINE, (f"Доля видимости упала на "
                                 f"{kpi.share_delta_pp:+.2f} п.п.")
    return VERDICT_NEUTRAL, (f"Доля видимости почти не изменилась "
                             f"({kpi.share_delta_pp:+.2f} п.п.)")


def ru_number(value: float, digits: int = 1) -> str:
    """Число в русской записи: разделитель дробной части — запятая."""
    return f"{value:.{digits}f}".replace(".", ",")


def format_share(value: float | None) -> str:
    """Доля для письма. NO DATA пишется словами, а не нулём."""
    return "NO DATA" if value is None else f"{ru_number(100 * value)}%"


def format_delta(value: float | None, *, unit: str = "") -> str:
    if value is None:
        return "н/д"
    if isinstance(value, float):
        sign = "+" if value >= 0 else "−"
        return f"{sign}{ru_number(abs(value), 2)}{unit}"
    return f"{value:+d}{unit}"
