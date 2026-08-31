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
import statistics
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402

VERDICT_GROWTH = "🟢"
VERDICT_NEUTRAL = "🟡"
VERDICT_DECLINE = "🔴"
VERDICT_NO_DATA = "⚪"

# Порог значимости изменения доли видимости в процентных пунктах. Меньшее
# движение — шум, а не сигнал (раздел 9 задания).
SIGNIFICANT_SHARE_PP = 0.5

# Сколько сравнимых измерений нужно, чтобы говорить о динамике. Общий фильтр
# значимости сравнивает медиану трёх последних измерений с медианой трёх
# предыдущих — значит раньше шестого валидного среза тренда не существует.
#
# В версии 1.0.0 здесь была логическая коллизия, найденная внешним аудитом:
# методика декларировала сглаживание 3×3, а вердикт менялся уже на втором
# дне, по разнице двух соседних точек. Теперь правило одно и жёсткое.
WINDOW = 3
MIN_OBSERVATIONS_FOR_TREND = WINDOW * 2

# Доля мониторингового ядра, ниже которой срез считается непригодным. Без
# порога 149 валидных запросов из 150 и 20 из 150 одинаково назывались бы
# «неполными данными», хотя первое — рабочий день, а второе — сбой сбора.
CRITICAL_COVERAGE_RATIO = 0.80

# Обязательные источники: их отсутствие делает вердикт невозможным.
# Необязательные (Google, B2B Confidence, уязвимость страниц) снижают
# достоверность отдельных показателей, но не блокируют остальные выводы —
# иначе система, у которой Google ещё не запущен, обязана была бы вечно
# отвечать «недостаточно данных».
REQUIRED_SOURCES = ("яндекс",)


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


def trend_change(history: list[float]) -> float | None:
    """Изменение доли между сравнимыми окнами, в процентных пунктах.

    Медиана трёх последних измерений против медианы трёх предыдущих — то же
    сглаживание, что и в остальной системе. Меньше шести измерений — тренда
    нет, возвращается None, а не ноль.
    """
    if len(history) < MIN_OBSERVATIONS_FOR_TREND:
        return None
    recent = statistics.median(history[-WINDOW:])
    earlier = statistics.median(history[-MIN_OBSERVATIONS_FOR_TREND:-WINDOW])
    return round(100 * (recent - earlier), 3)


def structural_verdict(kpi: Kpi, field_leader: tuple[str, float] | None = None
                       ) -> str:
    """Структурный вывод: где мы стоим прямо сейчас.

    Не требует истории и доступен с первого дня. Отвечает на вопрос «какова
    расстановка», а не «куда движемся» — это разные утверждения, и смешивать
    их нельзя.
    """
    share = format_share(kpi.share_yandex)
    base = f"BIZSoft занимает {share} взвешенной видимости поля"
    if kpi.top3 is not None and kpi.queries:
        base += f", в ТОП-3 по {kpi.top3} запросам из {kpi.queries}"
    if field_leader:
        domain, value = field_leader
        base += f"; ведущий конкурент — {domain} с {format_share(value)}"
    return base + "."


def coverage_state(snapshot: dict) -> tuple[str, str]:
    """Состояние покрытия данных: критическое или рабочее.

    Возвращает («ок» | «критическое», пояснение). Критическое означает, что
    обязательный источник собран настолько плохо, что выводы делать нельзя.
    Отсутствие необязательных источников критическим не является.
    """
    coverage = snapshot.get("покрытие") or {}
    total = coverage.get("яндекс_запросов_всего") or 0
    usable = coverage.get("яндекс_запросов_с_данными") or 0
    if total <= 0:
        return "критическое", "срез выдачи не собран вовсе"
    ratio = usable / total
    if ratio < CRITICAL_COVERAGE_RATIO:
        return "критическое", (
            f"собрано {usable} запросов из {total} "
            f"({100 * ratio:.0f}% при пороге "
            f"{100 * CRITICAL_COVERAGE_RATIO:.0f}%)")
    missing = []
    if coverage.get("google") is None:
        missing.append("Google не собирается")
    note = ("; ".join(missing) if missing else "все обязательные источники собраны")
    return "ок", note


def verdict(kpi: Kpi, history: list[float] | None = None) -> tuple[str, str]:
    """Динамический вердикт: усиливаемся, слабеем или движения нет.

    Требует шести сравнимых измерений — раньше динамики не существует, и
    любой вердикт о ней был бы утверждением о шуме. Структурная картина при
    этом доступна всегда, её даёт structural_verdict().
    """
    if not kpi.coverage_ok:
        return VERDICT_NO_DATA, ("Данные неполные: срез выдачи не собран — "
                                 "выводы по такому дню не делаем")

    history = history or []
    if len(history) < MIN_OBSERVATIONS_FOR_TREND:
        need = MIN_OBSERVATIONS_FOR_TREND - len(history)
        return VERDICT_NO_DATA, (
            f"Недостаточно данных для оценки динамики: нужно "
            f"{MIN_OBSERVATIONS_FOR_TREND} сравнимых измерений, "
            f"не хватает {need}")

    change = trend_change(history)
    if change is None:
        return VERDICT_NO_DATA, "Динамика не определена"
    if change >= SIGNIFICANT_SHARE_PP:
        return VERDICT_GROWTH, (f"Доля видимости выросла на {change:+.2f} п.п. "
                                f"между сравнимыми окнами")
    if change <= -SIGNIFICANT_SHARE_PP:
        return VERDICT_DECLINE, (f"Доля видимости упала на {change:+.2f} п.п. "
                                 f"между сравнимыми окнами")
    return VERDICT_NEUTRAL, (f"Доля видимости устойчива "
                             f"({change:+.2f} п.п. между окнами)")


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
