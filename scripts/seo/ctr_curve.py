#!/usr/bin/env python3
"""Кривая CTR по позициям из собственных данных Вебмастера.

Зачем. Модель денежных запросов считает недобор кликов через кривую
«позиция → ожидаемый CTR». Своей кривой у проекта не было, а внешняя
отраслевая запрещена методикой как фиктивная, поэтому расчёт «потерянных
кликов» не публиковался вовсе (quality.NO_CTR_MODEL).

Как считается. Вебмастер отдаёт запросы окнами по 10–28 дней, и соседние
срезы перекрываются: сложить их нельзя, один и тот же показ попал бы в сумму
дважды. Скрипт берёт из хранилища все срезы, у каждого читает границы окна
популярных запросов и выбирает набор непересекающихся окон с наибольшей
суммой показов (точная динамика по интервалам, не жадный отбор). Дальше
запросы раскладываются по корзинам средней позиции; на корзину считается
доля кликов и доверительный интервал Уилсона.

Чего эта кривая не делает. Она описывает, как кликают по нашей выдаче
сейчас, и не является эталоном «сколько кликов даёт позиция при нормальном
сниппете». Если отклик сайта аномально низок — а разбор второй волны
исключений это и подозревает, — то кривая по своим данным закрепит аномалию
как норму, и недобор кликов посчитается нулевым. Поэтому расчёт помечает
каждую корзину пригодностью, а поле approved скрипт не выставляет никогда:
кривую утверждает руководитель правкой реестра.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys

DATA_DIR = pathlib.Path('reports/seo/data')
OUT = pathlib.Path('data/seo/ctr-curve.json')

# Границы корзин: (нижняя исключая, верхняя включая, подпись). Верхние позиции
# разведены поштучно — там кривая и решает, — низ собран в широкие корзины,
# где показов много, а различать нечего.
BUCKETS = [(0, 1.5, '1'), (1.5, 2.5, '2'), (2.5, 3.5, '3'), (3.5, 5.5, '4–5'),
           (5.5, 7.5, '6–7'), (7.5, 10.5, '8–10'), (10.5, 20.5, '11–20'),
           (20.5, float('inf'), '21+')]

# Корзина считается пригодной, когда показов хватает на оценку доли и когда
# она не держится на одном запросе. Второе важнее первого: в выборке
# популярных запросов длинный хвост представлен строками с единичным показом,
# и корзина верхних позиций легко собирается из десятка таких строк плюс один
# крупный запрос — доля кликов в ней описывает этот запрос, а не позицию.
MIN_IMPRESSIONS = 500
MAX_SHARE_OF_TOP_QUERY = 0.25

SLICE_RE = re.compile(r'yandex-(?:window-)?20\d{2}-\d{2}-\d{2}')


def wilson(clicks: int, shows: int, z: float = 1.96) -> tuple[float, float]:
    """Доверительный интервал доли по Уилсону: на малых долях он не уезжает
    в отрицательные значения, в отличие от нормального приближения."""
    if shows <= 0:
        return (0.0, 0.0)
    p = clicks / shows
    denom = 1 + z * z / shows
    centre = p + z * z / (2 * shows)
    margin = z * math.sqrt(p * (1 - p) / shows + z * z / (4 * shows * shows))
    return ((centre - margin) / denom, (centre + margin) / denom)


def read_slices(data_dir: pathlib.Path) -> list[dict]:
    """Срезы Вебмастера с непустой выборкой запросов: {from, to, queries}."""
    out = []
    for path in sorted(data_dir.glob('yandex-*.json')):
        if not SLICE_RE.match(path.stem):
            continue
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
        except ValueError:
            continue
        pq = (raw or {}).get('popular_queries') or {}
        queries = pq.get('queries') or []
        if pq.get('error') or not queries:
            continue
        if not (pq.get('date_from') and pq.get('date_to')):
            continue
        out.append({'source': path.name, 'from': pq['date_from'], 'to': pq['date_to'],
                    'queries': queries,
                    'shows': sum(q.get('indicators', {}).get('TOTAL_SHOWS') or 0
                                 for q in queries)})
    return out


def pick_windows(slices: list[dict]) -> list[dict]:
    """Непересекающийся набор окон с наибольшей суммой показов.

    Классическая задача о взвешенных интервалах: сортировка по правому концу
    и динамика по префиксу. Жадный отбор «сначала самое крупное окно» здесь
    ошибается: одно широкое окно закрывает два узких, которые вместе дают
    больше показов.
    """
    if not slices:
        return []
    items = sorted(slices, key=lambda s: (s['to'], s['from']))
    best = [0.0] * (len(items) + 1)
    take = [False] * (len(items) + 1)
    prev = [0] * (len(items) + 1)
    for i, cur in enumerate(items, start=1):
        # Ближайшее окно, которое кончается строго раньше начала текущего.
        j = 0
        for k in range(i - 1, 0, -1):
            if items[k - 1]['to'] < cur['from']:
                j = k
                break
        with_cur = best[j] + cur['shows']
        if with_cur > best[i - 1]:
            best[i], take[i], prev[i] = with_cur, True, j
        else:
            best[i], take[i], prev[i] = best[i - 1], False, i - 1
    chosen, i = [], len(items)
    while i > 0:
        if take[i]:
            chosen.append(items[i - 1])
            i = prev[i]
        else:
            i -= 1
    return list(reversed(chosen))


def build(windows: list[dict]) -> dict:
    agg = {name: {'shows': 0.0, 'clicks': 0.0, 'queries': 0, 'top_query_shows': 0.0}
           for *_, name in BUCKETS}
    for window in windows:
        for q in window['queries']:
            ind = q.get('indicators') or {}
            pos = ind.get('AVG_SHOW_POSITION')
            if pos is None:
                continue
            shows = ind.get('TOTAL_SHOWS') or 0
            name = next(n for lo, hi, n in BUCKETS if lo < pos <= hi)
            cell = agg[name]
            cell['shows'] += shows
            cell['clicks'] += ind.get('TOTAL_CLICKS') or 0
            cell['queries'] += 1
            cell['top_query_shows'] = max(cell['top_query_shows'], shows)

    points = []
    for *_, name in BUCKETS:
        cell = agg[name]
        shows, clicks = cell['shows'], cell['clicks']
        lo, hi = wilson(int(clicks), int(shows))
        share = (cell['top_query_shows'] / shows) if shows else 1.0
        reasons = []
        if shows < MIN_IMPRESSIONS:
            reasons.append('мало показов')
        if share > MAX_SHARE_OF_TOP_QUERY:
            reasons.append('корзину определяет один запрос')
        points.append({
            'position': name,
            'impressions': round(shows),
            'clicks': round(clicks),
            'queries': cell['queries'],
            'ctr': round(clicks / shows, 5) if shows else None,
            'ctr_low': round(lo, 5),
            'ctr_high': round(hi, 5),
            'top_query_share': round(share, 3) if shows else None,
            'usable': not reasons,
            'unusable_reason': '; '.join(reasons) or None,
        })
    return {'points': points}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data-dir', type=pathlib.Path, default=DATA_DIR)
    ap.add_argument('--out', type=pathlib.Path, default=OUT)
    args = ap.parse_args()

    slices = read_slices(args.data_dir)
    if not slices:
        print('срезов Вебмастера с выборкой запросов не найдено', file=sys.stderr)
        return 1
    windows = pick_windows(slices)
    curve = build(windows)
    total_shows = sum(p['impressions'] for p in curve['points'])
    total_clicks = sum(p['clicks'] for p in curve['points'])

    payload = {
        'schema_version': '1.0.0',
        # Утверждение — решение руководителя, а не расчёта: кривая по своим
        # данным описывает наш отклик, а не эталонный. Пока здесь false,
        # snapshot держит ctr_model неутверждённой, и недобор кликов не
        # публикуется.
        'approved': False,
        'source': 'yandex_webmaster_popular_queries',
        'windows': [{'from': w['from'], 'to': w['to'], 'source': w['source'],
                     'impressions': round(w['shows'])} for w in windows],
        'coverage': {'from': windows[0]['from'], 'to': windows[-1]['to'],
                     'windows': len(windows),
                     'slices_available': len(slices),
                     'impressions': total_shows, 'clicks': total_clicks,
                     'ctr': round(total_clicks / total_shows, 5) if total_shows else None},
        'method': {
            'buckets': 'средняя позиция запроса за окно источника',
            'interval': 'доля кликов и интервал Уилсона, доверие 95%',
            'windows': 'непересекающиеся окна с наибольшей суммой показов',
            'limits': ('средняя позиция сглаживает показы запроса по разным '
                       'местам выдачи; корзина с одним крупным запросом '
                       'описывает запрос, а не позицию'),
            'min_impressions': MIN_IMPRESSIONS,
            'max_share_of_top_query': MAX_SHARE_OF_TOP_QUERY,
        },
        **curve,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    usable = sum(1 for p in curve['points'] if p['usable'])
    print(f"окон: {len(windows)}, показов: {total_shows}, кликов: {total_clicks}")
    print(f"корзин пригодных: {usable} из {len(curve['points'])}")
    print(f"записано: {args.out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
