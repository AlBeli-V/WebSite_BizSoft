#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сравнение двух снимков Яндекс.Вебмастера: что вернулось в поиск.

    python3 scripts/seo/compare.py <до.json> <после.json> [--batch <файл описаний>]

Считает по каждому снимку: сколько страниц в поиске, сколько исключено, с
какими причинами. Отдельно — судьба карточек партии: по каждому слагу из
data/seo/product-descriptions.json видно, в поиске страница или исключена.

Для исключений берём последнее по дате событие REMOVED_FROM_SEARCH на URL:
в выгрузке событий один и тот же URL встречается многократно (история), и
без схлопывания по URL счёт исключённых завышается втрое.
"""

import argparse
import json
import sys
from collections import Counter


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def snapshot(data):
    """Множества URL в поиске и исключённых + причины исключения."""
    in_search = {s['url'] for s in (data.get('in_search_samples') or {}).get('samples', [])}

    latest = {}
    for s in (data.get('excluded_samples') or {}).get('removed_from_search', []):
        url = s.get('url')
        if not url:
            continue
        prev = latest.get(url)
        if prev is None or (s.get('event_date') or '') >= (prev.get('event_date') or ''):
            latest[url] = s
    # Страница считается исключённой, если её нет в текущем «в поиске».
    excluded = {u: v for u, v in latest.items() if u not in in_search}
    reasons = Counter(v.get('excluded_url_status') or 'UNKNOWN' for v in excluded.values())
    summary = data.get('summary') or {}
    return {
        'collected_at': data.get('collected_at'),
        'in_search': in_search,
        'excluded': excluded,
        'reasons': reasons,
        'searchable_pages_count': summary.get('searchable_pages_count'),
        'excluded_pages_count': summary.get('excluded_pages_count'),
    }


def batch_urls(path):
    data = load(path)
    slugs = list(data.get('products', data))
    return [(s, f'https://biz-soft.pro/product/{s}') for s in slugs]


def main(argv=None):
    ap = argparse.ArgumentParser(description='Сравнение снимков Вебмастера')
    ap.add_argument('before')
    ap.add_argument('after')
    ap.add_argument('--batch', default='data/seo/product-descriptions.json')
    args = ap.parse_args(argv)

    a, b = snapshot(load(args.before)), snapshot(load(args.after))

    print('== Снимки ==')
    print(f'  до:    {a["collected_at"]}')
    print(f'  после: {b["collected_at"]}')

    print('\n== Сводка хоста (счётчик Вебмастера) ==')
    print(f'  страниц в поиске:  {a["searchable_pages_count"]} → {b["searchable_pages_count"]}')
    print(f'  исключено:         {a["excluded_pages_count"]} → {b["excluded_pages_count"]}')

    print('\n== По выгрузке URL ==')
    print(f'  в поиске:   {len(a["in_search"])} → {len(b["in_search"])}')
    print(f'  исключено:  {len(a["excluded"])} → {len(b["excluded"])}')
    all_reasons = sorted(set(a['reasons']) | set(b['reasons']))
    for r in all_reasons:
        print(f'    {r}: {a["reasons"].get(r, 0)} → {b["reasons"].get(r, 0)}')

    returned = sorted(set(a['excluded']) & b['in_search'])
    dropped = sorted(set(a['in_search']) & set(b['excluded']))
    print(f'\n  вернулось в поиск: {len(returned)}')
    for u in returned[:40]:
        print(f'    + {u}')
    print(f'  выпало из поиска:  {len(dropped)}')
    for u in dropped[:40]:
        print(f'    - {u}')

    try:
        pairs = batch_urls(args.batch)
    except Exception as e:
        print(f'\n(партия не прочитана: {e})')
        return 0

    print(f'\n== Карточки партии ({len(pairs)}) ==')
    stat = Counter()
    for slug, url in pairs:
        was = 'в поиске' if url in a['in_search'] else (
            a['excluded'].get(url, {}).get('excluded_url_status') or 'нет данных')
        now = 'в поиске' if url in b['in_search'] else (
            b['excluded'].get(url, {}).get('excluded_url_status') or 'нет данных')
        mark = '↑' if was != 'в поиске' and now == 'в поиске' else (
               '↓' if was == 'в поиске' and now != 'в поиске' else ' ')
        stat[now] += 1
        print(f'  {mark} {slug}: {was} → {now}')
    print('\n  итог по партии:', ', '.join(f'{k} — {v}' for k, v in stat.most_common()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
