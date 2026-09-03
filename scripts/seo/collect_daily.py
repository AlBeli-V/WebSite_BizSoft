#!/usr/bin/env python3
"""Дневная факт-витрина SEO-показателей: ряды «дата → значение» по источникам.

Зачем отдельный сборщик. Агрегатные снимки (collect.py) запрашивают у
источников скользящее окно «последние N дней», и два соседних снимка почти
никогда не сопоставимы: лаг Вебмастера плавает (окно то 12, то 13 дней),
выборка топ-запросов пересобирается. Отсюда ежедневные critical-находки
WINDOW_LENGTH_MISMATCH и SAMPLE_CHURN и статус «сбой» при исправных
источниках. Витрина хранит значения по календарным дням, а окна сравнения
строит отчёт — равной длины, с фиксированным лагом, без пересечений.

Формат: reports/seo/data/daily/<источник>.json —
{"source", "scope", "updated_at", "series": {метрика: {дата: значение}},
 "last_error", "last_error_at"}.

Дозапись идемпотентна: значения за перечитываемый хвост перезаписываются
(источники дозаполняют последние дни задним числом), остальная история не
трогается. Первый прогон (пустой файл) забирает историю с HISTORY_START.
Ошибка источника не стирает накопленные ряды: фиксируется в last_error,
прежние значения остаются.

Запускается воркфлоу seo-data-collect тем же набором секретов, что и
collect.py, рядом с ним; на переходный период оба пути пишут параллельно.
"""

import datetime as dt
import json
import os
import pathlib
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect as base  # noqa: E402 — общие api_json/константы/часовой пояс

DAILY_DIR = pathlib.Path('reports/seo/data/daily')

# Сайт живёт с конца июня 2026; более ранних данных нет ни у одного источника,
# поэтому глубже запрашивать нечего. GSC хранит 16 месяцев, Метрика и GA4 —
# больше, Вебмастер — меньше всех: если его история короче, он отдаст сколько
# есть, и ряд просто начнётся позже.
HISTORY_START = dt.date(2026, 6, 1)

# Хвост, который перечитывается каждым прогоном. У поисковых источников данные
# «созревают» 2–3 дня и дозаполняются задним числом; 10 дней покрывают это
# с запасом и остаются дешёвыми для API.
TAIL_DAYS = 10


# ---------------------------------------------------------------------------
# Парсеры ответов API — чистые функции, тестируются без сети.
# Каждый возвращает {метрика: {дата ISO: число}}.

def parse_yandex_history(payload: dict) -> dict:
    """/search-queries/all/history: {"indicators": {"TOTAL_SHOWS": [точки]}}.

    Дата приходит как timestamp с часовым поясом — берётся календарная часть.
    Значения у API дробные (float) — сохраняются как есть, округляет отчёт.
    """
    out = {'impressions': {}, 'clicks': {}}
    names = {'TOTAL_SHOWS': 'impressions', 'TOTAL_CLICKS': 'clicks'}
    for api_name, metric in names.items():
        for point in (payload.get('indicators') or {}).get(api_name, []):
            date = str(point.get('date', ''))[:10]
            if date:
                out[metric][date] = point.get('value')
    return out


def parse_gsc_rows(payload: dict) -> dict:
    """searchAnalytics/query c dimensions=[date]: rows[].keys=[дата]."""
    out = {'impressions': {}, 'clicks': {}, 'position': {}}
    for row in payload.get('rows', []):
        keys = row.get('keys') or []
        if not keys:
            continue
        date = str(keys[0])[:10]
        out['impressions'][date] = row.get('impressions')
        out['clicks'][date] = row.get('clicks')
        out['position'][date] = row.get('position')
    return out


def parse_metrika_rows(payload: dict, metrics: list[str]) -> dict:
    """stat/v1/data c dimensions=ym:s:date: имя измерения — дата ISO."""
    out = {m: {} for m in metrics}
    for row in payload.get('data', []):
        dims = row.get('dimensions') or []
        vals = row.get('metrics') or []
        if not dims:
            continue
        date = str(dims[0].get('name', ''))[:10]
        for metric, value in zip(metrics, vals):
            out[metric][date] = value
    return out


def parse_ga4_rows(payload: dict, metrics: list[str]) -> dict:
    """runReport c dimension=date: даты в формате YYYYMMDD — нормализуются."""
    out = {m: {} for m in metrics}
    for row in payload.get('rows', []):
        dims = row.get('dimensionValues') or []
        vals = row.get('metricValues') or []
        if not dims:
            continue
        raw = str(dims[0].get('value', ''))
        if len(raw) == 8 and raw.isdigit():
            date = f'{raw[0:4]}-{raw[4:6]}-{raw[6:8]}'
        else:
            date = raw[:10]
        for metric, cell in zip(metrics, vals):
            try:
                out[metric][date] = float(cell.get('value'))
            except (TypeError, ValueError):
                continue
    return out


def merge_series(existing: dict, fresh: dict) -> dict:
    """Свежие значения перекрывают прежние по совпадающим датам.

    Метрики и даты, которых нет в свежей выгрузке, сохраняются: короткое окно
    хвоста не должно стирать длинную историю.
    """
    merged = {m: dict(days) for m, days in (existing or {}).items()}
    for metric, days in fresh.items():
        merged.setdefault(metric, {})
        merged[metric].update({d: v for d, v in days.items() if v is not None})
    for metric in merged:
        merged[metric] = dict(sorted(merged[metric].items()))
    return merged


# ---------------------------------------------------------------------------
# Обвязка хранилища.

def load_store(name: str) -> dict:
    path = DAILY_DIR / f'{name}.json'
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except ValueError:
            # Битый файл не должен молча обнулять историю: сохраняется копия,
            # ряд начинается заново, а причина видна в last_error.
            broken = path.with_suffix('.json.broken')
            path.rename(broken)
            return {'last_error': f'файл повреждён, отложен в {broken.name}'}
    return {}


def window_for(store: dict) -> tuple[dt.date, dt.date]:
    """Пустой ряд — забрать историю целиком; иначе — только хвост."""
    end = base.today()
    has_data = any((store.get('series') or {}).values())
    if not has_data:
        return HISTORY_START, end
    return end - dt.timedelta(days=TAIL_DAYS), end


def save_store(name: str, store: dict, scope: str, fresh: dict | None,
               error: str | None) -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    store['source'] = name
    store['scope'] = scope
    if error:
        store['last_error'] = error
        store['last_error_at'] = now
    else:
        store['series'] = merge_series(store.get('series'), fresh or {})
        store['updated_at'] = now
        store.pop('last_error', None)
        store.pop('last_error_at', None)
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    (DAILY_DIR / f'{name}.json').write_text(
        json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True),
        encoding='utf-8')


# ---------------------------------------------------------------------------
# Источники. Каждый возвращает (series, None) или (None, 'ошибка').

def fetch_yandex(date_from: dt.date, date_to: dt.date):
    headers = {'Authorization': f"OAuth {os.environ['YANDEX_WEBMASTER_TOKEN']}"}
    api = 'https://api.webmaster.yandex.net/v4/user'
    user, err = base.api_json(api, headers=headers)
    if err or 'user_id' not in (user or {}):
        return None, f'/user: {err or "нет user_id"}'
    uid = user['user_id']
    hosts, err = base.api_json(f'{api}/{uid}/hosts', headers=headers)
    if err:
        return None, f'/hosts: {err}'
    match = [h for h in hosts.get('hosts', []) if base.SITE in h.get('host_id', '')]
    if not match:
        return None, f'{base.SITE} не найден в Вебмастере'
    host_id = match[0]['host_id']
    params = {
        'query_indicator': ['TOTAL_SHOWS', 'TOTAL_CLICKS'],
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
    }
    data, err = base.api_json(
        f'{api}/{uid}/hosts/{host_id}/search-queries/all/history',
        headers=headers, params=params)
    if err:
        return None, f'/search-queries/all/history: {err}'
    series = parse_yandex_history(data)
    if not any(series.values()):
        return None, ('история пуста: ответ без точек indicators '
                      + json.dumps(data, ensure_ascii=False)[:300])
    return series, None


def fetch_gsc(date_from: dt.date, date_to: dt.date):
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    info = json.loads(os.environ['GSC_SERVICE_ACCOUNT_JSON'])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
    creds.refresh(Request())
    headers = {'Authorization': f'Bearer {creds.token}'}
    sites, err = base.api_json('https://www.googleapis.com/webmasters/v3/sites',
                               headers=headers)
    if err:
        return None, f'/sites: {err}'
    entries = [s for s in sites.get('siteEntry', []) if base.SITE in s['siteUrl']]
    if not entries:
        return None, f'{base.SITE} не найден среди ресурсов сервисного аккаунта'
    site_url = urllib.parse.quote(entries[0]['siteUrl'], safe='')
    body = {
        'startDate': date_from.isoformat(),
        'endDate': date_to.isoformat(),
        'dimensions': ['date'],
        # Дней в максимальном окне заведомо меньше тысячи; лимит с запасом.
        'rowLimit': 1000,
    }
    data, err = base.api_json(
        f'https://www.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query',
        headers=headers, body=body)
    if err:
        return None, f'searchAnalytics/query(date): {err}'
    return parse_gsc_rows(data), None


METRIKA_METRICS = ['visits_organic', 'users_organic', 'goal_reaches_organic']
METRIKA_ALL_METRICS = ['visits_all']


def fetch_metrika(date_from: dt.date, date_to: dt.date):
    token = os.environ['YANDEX_METRIKA_TOKEN']
    counter = os.environ.get('YANDEX_METRIKA_COUNTER_ID', '').strip()
    if counter != base.EXPECTED_METRIKA_COUNTER:
        return None, (f'счётчик сборщика {counter} не совпадает со счётчиком '
                      f'сайта {base.EXPECTED_METRIKA_COUNTER}')
    headers = {'Authorization': f'OAuth {token}'}
    stat = 'https://api-metrika.yandex.net/stat/v1/data'
    common = {'ids': counter, 'date1': date_from.isoformat(),
              'date2': date_to.isoformat(), 'accuracy': 'full',
              'dimensions': 'ym:s:date', 'limit': 1000}
    organic, err = base.api_json(stat, headers=headers, params={
        **common,
        'metrics': 'ym:s:visits,ym:s:users,ym:s:sumGoalReachesAny',
        'filters': "ym:s:lastTrafficSource=='organic'",
    })
    if err:
        return None, f'stat(organic by date): {err}'
    series = parse_metrika_rows(organic, METRIKA_METRICS)
    total, err = base.api_json(stat, headers=headers, params={
        **common, 'metrics': 'ym:s:visits',
    })
    if err:
        return None, f'stat(all by date): {err}'
    series.update(parse_metrika_rows(total, METRIKA_ALL_METRICS))
    return series, None


GA4_METRICS = ['sessions_organic', 'key_events_organic']


def fetch_ga4(date_from: dt.date, date_to: dt.date):
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    info = json.loads(os.environ['GSC_SERVICE_ACCOUNT_JSON'])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/analytics.readonly'])
    creds.refresh(Request())
    headers = {'Authorization': f'Bearer {creds.token}'}
    prop = os.environ['GA4_PROPERTY_ID'].strip()
    # Очистка от собственных визитов — та же, что в агрегатном сборщике:
    # интерфейсы Яндекса не являются поисковой выдачей.
    organic_clean = {'andGroup': {'expressions': [
        {'filter': {'fieldName': 'sessionDefaultChannelGroup',
                    'stringFilter': {'value': 'Organic Search'}}},
        {'notExpression': {'filter': {
            'fieldName': 'sessionSource',
            'inListFilter': {'values': list(base.NON_SEARCH_SOURCES)}}}},
    ]}}
    body = {
        'dateRanges': [{'startDate': date_from.isoformat(),
                        'endDate': date_to.isoformat()}],
        'dimensions': [{'name': 'date'}],
        'metrics': [{'name': 'sessions'}, {'name': 'keyEvents'}],
        'dimensionFilter': organic_clean,
        'limit': 1000,
    }
    data, err = base.api_json(
        f'https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport',
        headers=headers, body=body)
    if err:
        return None, f'runReport(date): {err}'
    return parse_ga4_rows(data, GA4_METRICS), None


# ---------------------------------------------------------------------------

SOURCES = (
    # (имя файла, функция, обязательный секрет, охват ряда)
    ('yandex', fetch_yandex, 'YANDEX_WEBMASTER_TOKEN', 'site'),
    ('gsc', fetch_gsc, 'GSC_SERVICE_ACCOUNT_JSON', 'site'),
    ('metrika', fetch_metrika, 'YANDEX_METRIKA_TOKEN', 'site'),
    ('ga4', fetch_ga4, 'GA4_PROPERTY_ID', 'site'),
)


def main() -> int:
    ok = True
    for name, fn, secret, scope in SOURCES:
        store = load_store(name)
        date_from, date_to = window_for(store)
        if not os.environ.get(secret):
            series, err = None, f'секрет {secret} не задан'
        else:
            try:
                series, err = fn(date_from, date_to)
            except Exception as e:  # noqa: BLE001 — ошибка источника не валит остальные
                series, err = None, f'{type(e).__name__}: {e}'
        save_store(name, store, scope, series, err)
        if err:
            ok = False
            print(f'daily/{name}: ошибка: {err}')
        else:
            days = max((len(d) for d in series.values()), default=0)
            print(f'daily/{name}: {date_from}..{date_to}, дней в выгрузке: {days}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
