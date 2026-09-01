#!/usr/bin/env python3
"""Сбор SEO-данных biz-soft.pro из Google Search Console и API Яндекс.Вебмастера.

Запускается воркфлоу seo-data-collect (GitHub Actions): секреты
GSC_SERVICE_ACCOUNT_JSON и YANDEX_WEBMASTER_TOKEN приходят через env.
Пишет reports/seo/data/gsc-<дата>.json и yandex-<дата>.json.
Ошибки каждого источника фиксируются в его JSON, не валя весь сбор.
"""

import datetime as dt
import json
import os
import pathlib
import sys
import urllib.parse
from zoneinfo import ZoneInfo

import requests

SITE = 'biz-soft.pro'
OUT_DIR = pathlib.Path('reports/seo/data')

# Дата сбора — московская, а не по часовому поясу раннера.
#
# Раннер GitHub Actions живёт в UTC, GA4 и Метрика отдают данные в
# Europe/Moscow, а правило проекта требует Москву. Пока сбор идёт в 05:40 МСК,
# UTC и МСК дают одну дату и расхождение не видно. При ручном прогоне после
# 21:00 МСК имя файла ушло бы на сутки назад от содержимого, и сравнение
# периодов сломалось бы молча.
MSK = ZoneInfo('Europe/Moscow')


def today() -> dt.date:
    return dt.datetime.now(MSK).date()


TODAY = today().isoformat()

# Счётчики, которые обязан использовать сборщик. Значения публичны — они
# в HTML каждой страницы, — поэтому лежат в коде, а не в секретах: так их
# можно сверить, а расхождение поймать (см. verify_ids).
EXPECTED_METRIKA_COUNTER = '110206070'
EXPECTED_GA_MEASUREMENT_ID = 'G-V9BK2D1431'

# Вебмастер отдаёт запросы страницами. 100 — предел страницы у API,
# 2000 — потолок на случай, если хост внезапно отдаст десятки тысяч строк:
# сбор не должен превращаться в бесконечный обход.
PAGE_LIMIT = 100
MAX_QUERIES = 2000

# Пары «запрос × страница × день» GSC — сенсор для детекторов каннибализации
# и query-page mismatch (этапы 0–1 Growth Engine). День в измерениях нужен
# каннибализации: смена лидера по запросу видна только в дневном разрезе.
# Пары объёмнее одиночных разрезов, поэтому свой лимит страницы и свой
# потолок обхода (день умножает число строк примерно на длину окна).
PAIRS_PAGE_LIMIT = 1000
PAIRS_MAX_ROWS = 25000

# Источники, которые GA4 считает органическим поиском, а мы — своими визитами
# и не-поиском. Интерфейсы Яндекса — это переходы сотрудников; Алиса — не
# поисковая выдача.
INTERNAL_SOURCES = ('metrika.yandex.ru', 'webmaster.yandex.ru',
                    'direct.yandex.ru', 'alice.yandex.ru')


def api_json(url, *, headers=None, params=None, body=None, timeout=30):
    """Единый разбор ответа API: сеть, HTTP-статус, JSON.

    Возвращает (данные, None) либо (None, «строка ошибки»). Строка кладётся в
    поле error того же вида, что у остальных сборщиков, — её понимают
    snapshot.py (источник → «нет данных») и quality.py (SOURCE_UNAVAILABLE).
    Различаются: сетевая ошибка/таймаут, не-2xx статус, ответ не-JSON.
    Тело ошибки никогда не сохраняется как данные.
    """
    try:
        r = (requests.post(url, headers=headers, json=body, timeout=timeout)
             if body is not None else
             requests.get(url, headers=headers, params=params, timeout=timeout))
    except requests.RequestException as e:
        return None, f'{type(e).__name__}: {e}'
    if not r.ok:
        return None, f'HTTP {r.status_code}: {r.text[:300]}'
    try:
        return r.json(), None
    except ValueError as e:
        return None, f'ответ не является JSON ({e}): {r.text[:200]}'


def collect_gsc() -> dict:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    info = json.loads(os.environ['GSC_SERVICE_ACCOUNT_JSON'])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
    creds.refresh(Request())
    headers = {'Authorization': f'Bearer {creds.token}'}

    sites, err = api_json('https://www.googleapis.com/webmasters/v3/sites',
                          headers=headers)
    if err:
        return {'date': TODAY, 'error': f'/sites: {err}'}
    entries = [s for s in sites.get('siteEntry', []) if SITE in s['siteUrl']]
    result = {'date': TODAY, 'sites': sites.get('siteEntry', []), 'analytics': {}}
    if not entries:
        result['error'] = f'{SITE} не найден среди ресурсов сервисного аккаунта'
        return result

    site_url = urllib.parse.quote(entries[0]['siteUrl'], safe='')
    end = today()
    start = end - dt.timedelta(days=28)
    for dims in (['date'], ['query'], ['page']):
        body = {
            'startDate': start.isoformat(),
            'endDate': end.isoformat(),
            'dimensions': dims,
            'rowLimit': 100,
        }
        # Без этой проверки тело ошибки Google сохранялось как данные. Ключа
        # `rows` в нём нет, поэтому дальше по конвейеру получалось 0 показов —
        # и сбой доступа читался как обвал поискового трафика.
        data, err = api_json(
            f'https://www.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query',
            headers=headers, body=body)
        result['analytics'][dims[0]] = {'error': err} if err else data
    errors = [v['error'] for v in result['analytics'].values() if 'error' in v]
    if len(errors) == len(result['analytics']):
        result['error'] = 'все разрезы Search Analytics вернули ошибку: ' + errors[0]

    # Пары «запрос × страница» лежат отдельным ключом, а не в analytics:
    # это вспомогательный сенсор, и его сбой не должен закрывать весь источник
    # (правило «ошибка любого читаемого среза = данных нет» действует для
    # разрезов письма, а пары письмом не читаются — только детекторами).
    result['pairs'] = collect_gsc_pairs(site_url, headers,
                                        start.isoformat(), end.isoformat())
    return result


def collect_gsc_pairs(site_url: str, headers: dict,
                      start: str, end: str) -> dict:
    """Разрез Search Analytics по измерениям query+page+date.

    Пагинация через startRow: GSC отдаёт максимум rowLimit строк за вызов,
    без обхода страницами выборка обрезалась бы молча — как это уже было с
    одной страницей популярных запросов Вебмастера.
    """
    rows, error = [], None
    while len(rows) < PAIRS_MAX_ROWS:
        body = {
            'startDate': start,
            'endDate': end,
            'dimensions': ['query', 'page', 'date'],
            'rowLimit': PAIRS_PAGE_LIMIT,
            'startRow': len(rows),
        }
        data, err = api_json(
            f'https://www.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query',
            headers=headers, body=body)
        if err:
            error = err
            break
        chunk = data.get('rows') or []
        rows.extend(chunk)
        if len(chunk) < PAIRS_PAGE_LIMIT:
            break
    out = {'dimensions': ['query', 'page', 'date'],
           'window': {'from': start, 'to': end},
           'rows': rows, 'fetched': len(rows),
           'truncated': len(rows) >= PAIRS_MAX_ROWS}
    if error:
        # Ошибка после части страниц: собранное не выдаётся за полную выборку.
        out['error'] = error
        out['rows'] = []
        out['fetched'] = 0
    return out


def collect_yandex() -> dict:
    headers = {'Authorization': f"OAuth {os.environ['YANDEX_WEBMASTER_TOKEN']}"}
    base = 'https://api.webmaster.yandex.net/v4/user'
    date_to = today()
    date_from = date_to - dt.timedelta(days=14)
    # Запрошенное окно фиксируется до первого запроса: при сбое письмо обязано
    # назвать период, за который данных нет, а из тела ошибки он не извлекается.
    result = {'date': TODAY,
              'window': {'from': date_from.isoformat(), 'to': date_to.isoformat()}}

    user_data, err = api_json(base, headers=headers)
    if err or 'user_id' not in (user_data or {}):
        result['error'] = ('/user: ' + err) if err else (
            'API /user не вернул user_id: '
            + json.dumps(user_data, ensure_ascii=False)[:500])
        return result
    uid = user_data['user_id']

    hosts, err = api_json(f'{base}/{uid}/hosts', headers=headers)
    if err:
        result['error'] = f'/hosts: {err}'
        return result
    result['hosts'] = hosts.get('hosts', [])
    match = [h for h in result['hosts'] if SITE in h.get('host_id', '')]
    if not match:
        result['error'] = f'{SITE} не найден в Вебмастере этого аккаунта (или не подтверждён)'
        return result

    host_id = match[0]['host_id']
    result['host_id'] = host_id
    # Прежде summary читался без проверки статуса и формата ответа: тело
    # HTTP-ошибки сохранялось как данные, дальше по конвейеру оно не имело
    # ключа error и не распознавалось как сбой — поля индексации молча
    # превращались в «нет данных» без называния причины.
    summary, err = api_json(f'{base}/{uid}/hosts/{host_id}/summary', headers=headers)
    if err is None and isinstance(summary, dict) and summary.get('error_message'):
        # API умеет возвращать ошибку в теле формально успешного ответа.
        err = f"API вернул ошибку в теле ответа: {summary['error_message']}"
    result['summary'] = {'error': err} if err else summary

    params = {
        'order_by': 'TOTAL_SHOWS',
        'query_indicator': ['TOTAL_SHOWS', 'TOTAL_CLICKS', 'AVG_SHOW_POSITION', 'AVG_CLICK_POSITION'],
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'limit': PAGE_LIMIT,
    }
    url = f'{base}/{uid}/hosts/{host_id}/search-queries/popular/'

    # Постраничный забор вместо первых ста строк.
    #
    # Прежде бралась одна страница из 100 запросов при `count` в 506. Отбор шёл
    # по TOTAL_SHOWS, поэтому выборка была смещена в сторону высокочастотных
    # запросов и систематически теряла длинный хвост — а именно там у B2B-сайта
    # живут конверсионные запросы вида «оплата X для юрлиц». Это же объясняло
    # восьмикратный разрыв между кликами Вебмастера и органическими визитами
    # Метрики.
    queries, page, meta = [], None, {}
    for offset in range(0, MAX_QUERIES, PAGE_LIMIT):
        data, err = api_json(url, headers=headers, params={**params, 'offset': offset})
        if err:
            meta = meta or {'error': err}
            break
        page = data
        chunk = page.get('queries') or []
        meta = meta or {k: v for k, v in page.items() if k != 'queries'}
        queries.extend(chunk)
        if len(chunk) < PAGE_LIMIT or len(queries) >= (page.get('count') or 0):
            break

    result['popular_queries'] = {**meta, 'queries': queries,
                                 'fetched': len(queries),
                                 'count': (page or {}).get('count', len(queries))}
    return result


def collect_metrika() -> dict:
    """Яндекс.Метрика: источники трафика, органика по ПС и посадочным, цели.
    Токен — YANDEX_METRIKA_TOKEN (scope metrika:read), счётчик — YANDEX_METRIKA_COUNTER_ID."""
    token = os.environ['YANDEX_METRIKA_TOKEN']
    counter = os.environ['YANDEX_METRIKA_COUNTER_ID'].strip()
    # Счётчик сборщика обязан совпадать со счётчиком, который стоит на сайте.
    # Иначе отчёт соберётся из чужих данных и будет выглядеть правдоподобно.
    if counter != EXPECTED_METRIKA_COUNTER:
        return {'date': TODAY,
                'error': (f'счётчик сборщика {counter} не совпадает со счётчиком сайта '
                          f'{EXPECTED_METRIKA_COUNTER} (src/lib/analytics.ts)')}
    headers = {'Authorization': f'OAuth {token}'}
    stat = 'https://api-metrika.yandex.net/stat/v1/data'
    date_to = today() - dt.timedelta(days=1)
    date_from = date_to - dt.timedelta(days=13)
    base = {'ids': counter, 'date1': date_from.isoformat(), 'date2': date_to.isoformat(),
            'accuracy': 'full', 'limit': 100}
    result = {'date': TODAY, 'counter': counter,
              'window': {'from': date_from.isoformat(), 'to': date_to.isoformat()}}

    goals_data, err = api_json(
        f'https://api-metrika.yandex.net/management/v1/counter/{counter}/goals',
        headers=headers)
    result['goals'] = {'error': err} if err else goals_data.get('goals', [])

    queries = {
        'traffic_sources': {
            'dimensions': 'ym:s:lastTrafficSource',
            'metrics': 'ym:s:visits,ym:s:users,ym:s:bounceRate,ym:s:pageDepth,ym:s:sumGoalReachesAny',
        },
        'organic_by_engine': {
            'dimensions': 'ym:s:lastSearchEngineRoot',
            'metrics': 'ym:s:visits,ym:s:users,ym:s:bounceRate,ym:s:sumGoalReachesAny',
            'filters': "ym:s:lastTrafficSource=='organic'",
        },
        'organic_landing_pages': {
            'dimensions': 'ym:s:startURLPath',
            'metrics': 'ym:s:visits,ym:s:bounceRate,ym:s:sumGoalReachesAny',
            'filters': "ym:s:lastTrafficSource=='organic'",
        },
    }
    for key, params in queries.items():
        data, err = api_json(stat, headers=headers, params={**base, **params})
        result[key] = {'error': err} if err else data

    # Разбивка целевых событий органики по целям (вопрос руководителя
    # 01.09.2026: сумма «N целевых событий» без состава нечитаема — в ней
    # смешаны клик по телефону и автоцель «поиск по сайту»). Метрика отдаёт
    # по-цельные достижения метриками ym:s:goal<ID>reaches, до 20 метрик на
    # запрос — цели разбиваются на порции.
    goal_ids = [g['id'] for g in result['goals']
                if isinstance(result['goals'], list) and g.get('id')] \
        if isinstance(result['goals'], list) else []
    reaches: dict[str, float] = {}
    for i in range(0, len(goal_ids), 20):
        chunk = goal_ids[i:i + 20]
        data, err = api_json(stat, headers=headers, params={
            **base,
            'metrics': ','.join(f'ym:s:goal{gid}reaches' for gid in chunk),
            'filters': "ym:s:lastTrafficSource=='organic'"})
        if err:
            result['organic_goal_reaches'] = {'error': err}
            break
        totals = data.get('totals') or []
        # totals бывает плоским списком значений или списком строк.
        row = totals[0] if totals and isinstance(totals[0], list) else totals
        for gid, val in zip(chunk, row):
            reaches[str(gid)] = val
    else:
        result['organic_goal_reaches'] = reaches
    return result


def collect_ga4() -> dict:
    """GA4 Data API: каналы, органические посадочные, источники. Авторизация —
    тот же сервисный аккаунт, что и GSC; property — секрет GA4_PROPERTY_ID."""
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    info = json.loads(os.environ['GSC_SERVICE_ACCOUNT_JSON'])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/analytics.readonly'])
    creds.refresh(Request())
    headers = {'Authorization': f'Bearer {creds.token}'}
    prop = os.environ['GA4_PROPERTY_ID'].strip()
    url = f'https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport'
    date_to = today() - dt.timedelta(days=1)
    date_from = date_to - dt.timedelta(days=13)
    dates = [{'startDate': date_from.isoformat(), 'endDate': date_to.isoformat()}]
    result = {'date': TODAY, 'property': prop,
              'window': {'from': date_from.isoformat(), 'to': date_to.isoformat()}}

    organic_filter = {'filter': {'fieldName': 'sessionDefaultChannelGroup',
                                 'stringFilter': {'value': 'Organic Search'}}}

    # GA4 относит к поисковым системам любой домен *.yandex.*, включая интерфейс
    # Метрики и Вебмастера. Переход «посмотреть сайт» из Вебвизора становился
    # органической сессией: на замере 21.08.2026 источник metrika.yandex.ru дал
    # 5 сессий и оба зафиксированных key events — то есть сто процентов
    # «конверсий органики» были визитами владельца сайта.
    organic_clean = {'andGroup': {'expressions': [
        organic_filter,
        {'notExpression': {'filter': {
            'fieldName': 'sessionSource',
            'inListFilter': {'values': list(INTERNAL_SOURCES)}}}},
    ]}}
    reports = {
        'channels': {
            'dateRanges': dates,
            'dimensions': [{'name': 'sessionDefaultChannelGroup'}],
            'metrics': [{'name': 'sessions'}, {'name': 'totalUsers'}, {'name': 'keyEvents'}],
        },
        'organic_sources': {
            'dateRanges': dates,
            'dimensions': [{'name': 'sessionSource'}],
            'metrics': [{'name': 'sessions'}, {'name': 'keyEvents'}],
            'dimensionFilter': organic_filter,
        },
        'organic_landing_pages': {
            'dateRanges': dates,
            'dimensions': [{'name': 'landingPage'}],
            'metrics': [{'name': 'sessions'}, {'name': 'keyEvents'}],
            'dimensionFilter': organic_clean,
            'limit': 50,
        },
        # Тот же срез без очистки. Нужен именно для сравнения: разница между
        # ним и organic_landing_pages показывает объём собственных визитов,
        # и проверка INTERNAL_TRAFFIC_IN_ORGANIC опирается на неё, а не на
        # предположение.
        'organic_landing_pages_raw': {
            'dateRanges': dates,
            'dimensions': [{'name': 'landingPage'}],
            'metrics': [{'name': 'sessions'}, {'name': 'keyEvents'}],
            'dimensionFilter': organic_filter,
            'limit': 50,
        },
    }
    for key, body in reports.items():
        data, err = api_json(url, headers=headers, body=body)
        result[key] = {'error': err} if err else data
    return result


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = True
    for name, fn, secret in (
        ('gsc', collect_gsc, 'GSC_SERVICE_ACCOUNT_JSON'),
        ('yandex', collect_yandex, 'YANDEX_WEBMASTER_TOKEN'),
        ('metrika', collect_metrika, 'YANDEX_METRIKA_TOKEN'),
        ('ga4', collect_ga4, 'GA4_PROPERTY_ID'),
    ):
        if not os.environ.get(secret):
            data = {'date': TODAY, 'error': f'секрет {secret} не задан'}
            ok = False
        else:
            try:
                data = fn()
            except Exception as e:  # noqa: BLE001 — фиксируем любую ошибку источника в JSON
                data = {'date': TODAY, 'error': f'{type(e).__name__}: {e}'}
                ok = False
        path = OUT_DIR / f'{name}-{TODAY}.json'
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        status = 'ошибка: ' + data['error'] if 'error' in data else 'ок'
        print(f'{name}: {status} -> {path}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
