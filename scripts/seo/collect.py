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

import requests

SITE = 'biz-soft.pro'
OUT_DIR = pathlib.Path('reports/seo/data')
TODAY = dt.date.today().isoformat()


def collect_gsc() -> dict:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    info = json.loads(os.environ['GSC_SERVICE_ACCOUNT_JSON'])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
    creds.refresh(Request())
    headers = {'Authorization': f'Bearer {creds.token}'}

    sites = requests.get(
        'https://www.googleapis.com/webmasters/v3/sites', headers=headers, timeout=30).json()
    entries = [s for s in sites.get('siteEntry', []) if SITE in s['siteUrl']]
    result = {'date': TODAY, 'sites': sites.get('siteEntry', []), 'analytics': {}}
    if not entries:
        result['error'] = f'{SITE} не найден среди ресурсов сервисного аккаунта'
        return result

    site_url = urllib.parse.quote(entries[0]['siteUrl'], safe='')
    end = dt.date.today()
    start = end - dt.timedelta(days=28)
    for dims in (['date'], ['query'], ['page']):
        body = {
            'startDate': start.isoformat(),
            'endDate': end.isoformat(),
            'dimensions': dims,
            'rowLimit': 100,
        }
        r = requests.post(
            f'https://www.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query',
            headers=headers, json=body, timeout=30)
        result['analytics'][dims[0]] = r.json()
    return result


def collect_yandex() -> dict:
    headers = {'Authorization': f"OAuth {os.environ['YANDEX_WEBMASTER_TOKEN']}"}
    base = 'https://api.webmaster.yandex.net/v4/user'
    result = {'date': TODAY}

    user_resp = requests.get(base, headers=headers, timeout=30)
    user_data = user_resp.json()
    if 'user_id' not in user_data:
        result['error'] = (
            f'API /user не вернул user_id (HTTP {user_resp.status_code}): '
            f'{json.dumps(user_data, ensure_ascii=False)[:500]}'
        )
        return result
    uid = user_data['user_id']
    hosts = requests.get(f'{base}/{uid}/hosts', headers=headers, timeout=30).json()
    result['hosts'] = hosts.get('hosts', [])
    match = [h for h in result['hosts'] if SITE in h['host_id']]
    if not match:
        result['error'] = f'{SITE} не найден в Вебмастере этого аккаунта (или не подтверждён)'
        return result

    host_id = match[0]['host_id']
    result['host_id'] = host_id
    result['summary'] = requests.get(
        f'{base}/{uid}/hosts/{host_id}/summary', headers=headers, timeout=30).json()

    date_to = dt.date.today()
    date_from = date_to - dt.timedelta(days=14)
    params = {
        'order_by': 'TOTAL_SHOWS',
        'query_indicator': ['TOTAL_SHOWS', 'TOTAL_CLICKS', 'AVG_SHOW_POSITION', 'AVG_CLICK_POSITION'],
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'limit': 100,
    }
    result['popular_queries'] = requests.get(
        f'{base}/{uid}/hosts/{host_id}/search-queries/popular/',
        headers=headers, params=params, timeout=30).json()
    return result


def collect_metrika() -> dict:
    """Яндекс.Метрика: источники трафика, органика по ПС и посадочным, цели.
    Токен — YANDEX_METRIKA_TOKEN (scope metrika:read), счётчик — YANDEX_METRIKA_COUNTER_ID."""
    token = os.environ['YANDEX_METRIKA_TOKEN']
    counter = os.environ['YANDEX_METRIKA_COUNTER_ID'].strip()
    headers = {'Authorization': f'OAuth {token}'}
    stat = 'https://api-metrika.yandex.net/stat/v1/data'
    date_to = dt.date.today() - dt.timedelta(days=1)
    date_from = date_to - dt.timedelta(days=13)
    base = {'ids': counter, 'date1': date_from.isoformat(), 'date2': date_to.isoformat(),
            'accuracy': 'full', 'limit': 100}
    result = {'date': TODAY, 'counter': counter,
              'window': {'from': date_from.isoformat(), 'to': date_to.isoformat()}}

    goals_resp = requests.get(
        f'https://api-metrika.yandex.net/management/v1/counter/{counter}/goals',
        headers=headers, timeout=30)
    result['goals'] = goals_resp.json().get('goals', []) if goals_resp.ok else {
        'error': f'HTTP {goals_resp.status_code}: {goals_resp.text[:300]}'}

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
        r = requests.get(stat, headers=headers, params={**base, **params}, timeout=30)
        result[key] = r.json() if r.ok else {'error': f'HTTP {r.status_code}: {r.text[:300]}'}
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
    date_to = dt.date.today() - dt.timedelta(days=1)
    date_from = date_to - dt.timedelta(days=13)
    dates = [{'startDate': date_from.isoformat(), 'endDate': date_to.isoformat()}]
    result = {'date': TODAY, 'property': prop,
              'window': {'from': date_from.isoformat(), 'to': date_to.isoformat()}}

    organic_filter = {'filter': {'fieldName': 'sessionDefaultChannelGroup',
                                 'stringFilter': {'value': 'Organic Search'}}}
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
            'dimensionFilter': organic_filter,
            'limit': 50,
        },
    }
    for key, body in reports.items():
        r = requests.post(url, headers=headers, json=body, timeout=30)
        result[key] = r.json() if r.ok else {'error': f'HTTP {r.status_code}: {r.text[:400]}'}
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
