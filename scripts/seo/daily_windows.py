#!/usr/bin/env python3
"""Окна сравнения из дневной факт-витрины (reports/seo/data/daily/).

Агрегатные выгрузки сравнивали скользящие окна источников, которые почти
никогда не совпадали ни длиной, ни составом. Здесь окна строит отчёт сам:
текущее и предыдущее — равной длины, встык, без пересечений, с фиксированным
лагом на созревание данных источника. Дельта двух таких окон — честное
сравнение независимых периодов; проверки WINDOW_LENGTH_MISMATCH и
SAMPLE_CHURN к нему неприменимы по построению.

Лаг: поисковые источники дозаполняют последние 2–3 дня задним числом
(у Яндекса свежие даты сначала лежат нулями), поэтому их окна заканчиваются
на T−3; аналитика полна уже за вчера — T−1.

Окно публикуется только целиком: если в ряду нет хотя бы одного дня окна,
блок помечается incomplete с перечнем дыр, и потребитель обязан не считать
дельту, а не «дозаполнить нулями».
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

DAILY_DIR = pathlib.Path('reports/seo/data/daily')
WINDOW_DAYS = 7

# Лаг созревания: последний день окна — report_date минус лаг.
LAG_DAYS = {'yandex': 3, 'gsc': 3, 'metrika': 1, 'ga4': 1}

# У stat-API Метрики и GA4 день без событий отсутствует в ответе вовсе:
# пропущенная дата внутри диапазона ряда — измеренный ноль, а не дыра.
# У Вебмастера и GSC нулевые дни приходят явными нулями, поэтому там
# отсутствие даты остаётся настоящим пропуском.
ZERO_FILL_SOURCES = {'metrika', 'ga4'}

# Метрики, которые каждый источник обязан отдавать в витрину.
METRICS = {
    'yandex': ('impressions', 'clicks'),
    'gsc': ('impressions', 'clicks'),
    'metrika': ('visits_organic', 'visits_all', 'goal_reaches_organic'),
    'ga4': ('sessions_organic', 'key_events_organic'),
}


def _dates(start: dt.date, days: int) -> list[str]:
    return [(start + dt.timedelta(days=i)).isoformat() for i in range(days)]


def load_series(source: str, base_dir: pathlib.Path | None = None) -> dict | None:
    path = (base_dir or DAILY_DIR) / f'{source}.json'
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except ValueError:
        return None


def build_source(report_date: str, source: str, store: dict | None,
                 lag: int | None = None, metrics: tuple | None = None) -> dict:
    """Окна одного источника: {available, complete, windows, missing_dates}.

    lag — переопределение лага созревания: общее окно воронки строится с
    лагом самого медленного источника, чтобы все ряды кончались одним днём.
    metrics — свой набор рядов вместо обязательного: так блок «Аудитория»
    строит окна по разрезу «устройство × канал», не делая эти ряды
    обязательными для KPI (их история короче, и старые дни без них не
    должны объявлять неполным окно показателей роста).
    """
    if not store or not (store.get('series') or {}):
        return {'available': False, 'error': 'витрина не заполнена',
                'complete': False}
    series = store['series']
    zero_fill = source in ZERO_FILL_SOURCES
    all_dates = sorted({d for days in series.values() for d in days})
    span_min, span_max = (all_dates[0], all_dates[-1]) if all_dates else (None, None)

    def value_of(days: dict, d: str):
        v = days.get(d)
        if v is None and zero_fill and span_min and span_min <= d <= span_max:
            return 0.0
        return v

    lag = LAG_DAYS[source] if lag is None else lag
    metrics = METRICS[source] if metrics is None else tuple(metrics)
    end = dt.date.fromisoformat(report_date) - dt.timedelta(days=lag)
    cur_start = end - dt.timedelta(days=WINDOW_DAYS - 1)
    prev_start = cur_start - dt.timedelta(days=WINDOW_DAYS)
    cur_dates = _dates(cur_start, WINDOW_DAYS)
    prev_dates = _dates(prev_start, WINDOW_DAYS)

    windows: dict = {}
    missing: set[str] = set()
    for metric in metrics:
        days = series.get(metric) or {}
        cur_vals = [value_of(days, d) for d in cur_dates]
        prev_vals = [value_of(days, d) for d in prev_dates]
        missing.update(d for d, v in zip(cur_dates, cur_vals) if v is None)
        missing.update(d for d, v in zip(prev_dates, prev_vals) if v is None)
        cur_ok = all(v is not None for v in cur_vals)
        prev_ok = all(v is not None for v in prev_vals)
        windows[metric] = {
            'current': {'from': cur_dates[0], 'to': cur_dates[-1],
                        'sum': round(sum(v for v in cur_vals if v is not None), 2),
                        'complete': cur_ok},
            'previous': {'from': prev_dates[0], 'to': prev_dates[-1],
                         'sum': round(sum(v for v in prev_vals if v is not None), 2),
                         'complete': prev_ok},
            'delta': (round(sum(cur_vals) - sum(prev_vals), 2)
                      if cur_ok and prev_ok else None),
            # Хвост для спарклайна: последние 14 зрелых дней подряд.
            'tail': [value_of(days, d) for d in prev_dates + cur_dates],
        }
    return {
        'available': True,
        'complete': not missing,
        'missing_dates': sorted(missing),
        'lag_days': lag,
        'window_days': WINDOW_DAYS,
        'updated_at': store.get('updated_at'),
        'windows': windows,
    }


def build_aligned(report_date: str, stores: dict[str, dict | None]) -> dict:
    """Общее окно воронки: все источники обрезаны по самому медленному лагу.

    Решение руководителя 03.09.2026 («двойное окно»). Карточки источников
    остаются на своих свежих окнах: визиты и заявки Метрики за вчера — самый
    оперативный сигнал письма, и терять два дня ради сопоставимости нельзя.
    А воронка «показы → клики → визиты → цели» и любые сверки между
    источниками складываются только из этого окна: у Вебмастера и GSC данные
    зреют три дня, у аналитики один, и без общего конца воронка состояла из
    разных недель.
    """
    lag = max(LAG_DAYS.values())
    end = dt.date.fromisoformat(report_date) - dt.timedelta(days=lag)
    cur_start = end - dt.timedelta(days=WINDOW_DAYS - 1)
    prev_start = cur_start - dt.timedelta(days=WINDOW_DAYS)
    sources, missing = {}, set()
    for source in METRICS:
        blk = build_source(report_date, source, stores.get(source), lag=lag)
        sources[source] = blk
        if not blk.get('available'):
            missing.add(f'{source}: витрина не заполнена')
        else:
            missing.update(blk.get('missing_dates') or [])
    return {
        'available': all(v.get('available') for v in sources.values()),
        'complete': all(v.get('available') and v.get('complete')
                        for v in sources.values()),
        'lag_days': lag,
        'window_days': WINDOW_DAYS,
        'current': {'from': cur_start.isoformat(), 'to': end.isoformat()},
        'previous': {'from': prev_start.isoformat(),
                     'to': (cur_start - dt.timedelta(days=1)).isoformat()},
        'missing_dates': sorted(missing),
        'sources': {s: (v.get('windows') or {}) for s, v in sources.items()},
    }


def build(report_date: str, base_dir: pathlib.Path | None = None) -> dict:
    """Блок daily для снимка: окна всех источников + сводный признак."""
    out = {}
    stores = {source: load_series(source, base_dir) for source in METRICS}
    for source in METRICS:
        out[source] = build_source(report_date, source, stores[source])
    out['any_available'] = any(v.get('available') for v in out.values()
                               if isinstance(v, dict))
    # Общее окно воронки (см. build_aligned): ключ не совпадает с именем
    # источника, потребители перебирают источники по METRICS.
    out['aligned'] = build_aligned(report_date, stores)
    return out
