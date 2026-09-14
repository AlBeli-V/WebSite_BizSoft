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
трогается. Первый прогон (пустой файл) забирает историю с HISTORY_START;
её же забирает прогон, у которого в витрине нет ряда из обязательного набора
(EXPECTED) — так новый разрез дозаполняется задним числом, а не начинается
с сегодняшнего дня. Ошибка источника не стирает накопленные ряды: фиксируется
в last_error, прежние значения остаются.

Разрез «устройство × канал» (блок «Аудитория» письма и веб-отчёта) живёт
теми же рядами: показы и клики поиска — по типу устройства, визиты и сессии —
по каналу и устройству. Классы внешних переходов (каталог, площадка, прочая
ссылка) берутся из реестра data/seo/referral-classes.json: домена нет в
реестре — переход считается обычной внешней ссылкой, а не угадывается.

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


# Разрез «устройство × канал»: словари и реестр.
#
# Устройства названы так же, как их называют оба поисковика и обе системы
# аналитики; всё, что не попало в три знакомых класса (телевизоры, приставки,
# неопознанное), складывается в other и в письме показывается только тогда,
# когда там что-то есть.
DEVICES = ('desktop', 'mobile', 'tablet', 'other')

# Каналы визитов. Органика и реклама приходят каналом самого счётчика;
# три внешних класса разводит реестр доменов, остальное (прямые заходы,
# внутренние переходы, почта, закладки) — other.
CHANNELS = ('organic', 'ads', 'links', 'catalogs', 'platforms', 'other')

REFERRAL_CLASSES = pathlib.Path('data/seo/referral-classes.json')

# Канал Метрики (ym:s:lastTrafficSource) → наш канал. Соцсети, мессенджеры и
# рекомендательные системы — это площадки, где мы присутствуем содержанием,
# поэтому они идут одним классом с Дзеном и VC.
METRIKA_CHANNEL = {
    'organic': 'organic', 'ad': 'ads',
    'social': 'platforms', 'messenger': 'platforms', 'recommend': 'platforms',
    'direct': 'other', 'internal': 'other', 'saved': 'other',
    'email': 'other', 'qr': 'other',
}
# Группа каналов GA4 (sessionDefaultChannelGroup) → наш канал. Группы Referral
# здесь нет намеренно: переходы с сайтов раскрывает отдельный запрос по
# доменам, и в общем срезе они пропускаются, чтобы не считаться дважды.
#
# Unassigned — сессии, которым GA4 не смог назначить канал; они относятся к
# «прочему» явной записью, а не умолчанием словаря: зонд 14.09.2026 нашёл их
# в нашем ресурсе, и незнакомое значение в письме — это молчаливая потеря
# визитов, даже когда итог тот же.
GA4_CHANNEL = {
    'organic search': 'organic', 'organic shopping': 'organic',
    'paid search': 'ads', 'paid social': 'ads', 'paid shopping': 'ads',
    'paid video': 'ads', 'paid other': 'ads', 'display': 'ads',
    'cross-network': 'ads',
    'organic social': 'platforms', 'organic video': 'platforms',
    'audio': 'platforms',
    'direct': 'other', 'email': 'other', 'affiliates': 'other',
    'sms': 'other', 'mobile push notifications': 'other',
    'push notifications': 'other', 'unassigned': 'other',
}
# Тип устройства у источника → наш класс. Ключи — то, что реально приходит в
# id измерения; незнакомое значение уходит в other, а не отбрасывается.
# Телевизоры и приставки перечислены явно: Метрика отдаёт их значением tv,
# GA4 — smart tv (зонд 14.09.2026), и они сознательно относятся к «прочим»,
# а не попадают туда умолчанием, о котором никто не знает.
DEVICE_ALIAS = {
    'desktop': 'desktop', 'pc': 'desktop',
    'mobile': 'mobile', 'phone': 'mobile', 'smartphone': 'mobile',
    'tablet': 'tablet',
    'tv': 'other', 'smart tv': 'other', 'smarttv': 'other',
}
# Значение device_type_indicator Вебмастера для каждого класса. Планшеты
# Вебмастер отдаёт отдельным значением, поэтому MOBILE_AND_TABLET не нужен.
YANDEX_DEVICE = {'desktop': 'DESKTOP', 'mobile': 'MOBILE', 'tablet': 'TABLET'}
# Значение измерения device в Search Console.
GSC_DEVICE = {'DESKTOP': 'desktop', 'MOBILE': 'mobile', 'TABLET': 'tablet'}


def load_referral_classes(path: pathlib.Path | None = None) -> dict:
    """Реестр доменов: {класс: (домен, ...)}. Нет файла — классов нет.

    Отсутствие реестра не ломает сбор: все внешние переходы останутся
    «внешними ссылками», и это видно в отчёте, а не подменяется догадкой.
    """
    path = path or REFERRAL_CLASSES
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    classes = data.get('classes') or {}
    return {name: tuple(str(d).strip().lower().lstrip('.')
                        for d in (body.get('domains') or []) if str(d).strip())
            for name, body in classes.items()}


def classify_referral(source: str, classes: dict) -> str:
    """Класс внешнего перехода по домену источника.

    Совпадение по домену и его поддоменам: запись vc.ru покрывает vc.ru и
    m.vc.ru, но не myvc.ru. Запись с путём (yandex.ru/maps) требует ещё и
    совпадения начала пути. Домен вне реестра — обычная внешняя ссылка:
    класс не угадывается.
    """
    raw = str(source or '').strip().lower()
    for prefix in ('https://', 'http://'):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    host, _, path = raw.lstrip('.').partition('/')
    if host.startswith('www.'):
        host = host[4:]
    if not host:
        return 'links'
    for name, domains in classes.items():
        for domain in domains:
            dhost, _, dpath = domain.partition('/')
            if host != dhost and not host.endswith('.' + dhost):
                continue
            if dpath and not path.startswith(dpath):
                continue
            return name
    return 'links'


def device_class(value: str) -> str:
    """Класс устройства по значению измерения источника."""
    return DEVICE_ALIAS.get(str(value or '').strip().lower(), 'other')


def channel_metrics(prefix: str) -> list[str]:
    """Полный набор имён рядов «канал × устройство» для источника."""
    return [f'{prefix}_{ch}_{dev}' for ch in CHANNELS for dev in DEVICES]


def device_metrics(*bases: str) -> list[str]:
    """Полный набор имён рядов «метрика × устройство» поискового источника."""
    return [f'{base}_{dev}' for base in bases for dev in YANDEX_DEVICE]


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


def _dim_key(dim: dict) -> str:
    """Значение измерения Метрики: идентификатор, а при его отсутствии — имя.

    Имя измерения локализовано и меняется вместе с языком ответа, поэтому
    классификация опирается на id («organic», «mobile»), а имя — страховка.
    """
    return str((dim or {}).get('id') or (dim or {}).get('name') or '').strip()


def _ga4_date(raw) -> str:
    """Дата GA4: YYYYMMDD → ISO."""
    raw = str(raw or '')
    return f'{raw[0:4]}-{raw[4:6]}-{raw[6:8]}' if len(raw) == 8 and raw.isdigit() else raw[:10]


def parse_yandex_device_history(payload: dict, device: str) -> dict:
    """История Вебмастера, запрошенная с device_type_indicator одного класса."""
    base_series = parse_yandex_history(payload)
    return {f'impressions_{device}': base_series['impressions'],
            f'clicks_{device}': base_series['clicks']}


def parse_gsc_device_rows(payload: dict) -> dict:
    """searchAnalytics/query c dimensions=[date, device].

    День, в который устройство не дало ни показа, в ответе отсутствует. Для
    поисковых источников пропущенная дата означает дыру в данных, поэтому
    такие дни заполняются нулём: ноль здесь измерен, а не предположен —
    сама дата в ответе есть.
    """
    out = {m: {} for m in device_metrics('impressions', 'clicks')}
    dates = set()
    for row in payload.get('rows', []):
        keys = row.get('keys') or []
        if len(keys) < 2:
            continue
        date = str(keys[0])[:10]
        dates.add(date)
        device = GSC_DEVICE.get(str(keys[1]).strip().upper())
        if not device:
            continue
        out[f'impressions_{device}'][date] = row.get('impressions')
        out[f'clicks_{device}'][date] = row.get('clicks')
    for date in dates:
        for metric in out:
            out[metric].setdefault(date, 0)
    return out


def parse_metrika_channel_rows(payload: dict, classes: dict,
                               *, referral: bool = False) -> dict:
    """Визиты Метрики в разрезе «дата × канал (или домен) × устройство».

    referral=False — общий срез по каналам; строки переходов с сайтов из него
    исключаются: их раскрывает отдельный запрос по доменам, и учёт в обоих
    привёл бы к двойному счёту.
    """
    out = {m: {} for m in channel_metrics('visits')}
    for row in payload.get('data', []):
        dims = row.get('dimensions') or []
        metrics = row.get('metrics') or []
        if len(dims) < 3 or not metrics:
            continue
        date = str((dims[0] or {}).get('name') or '')[:10]
        key = _dim_key(dims[1])
        if not date:
            continue
        if referral:
            channel = classify_referral(key, classes)
        elif key == 'referral':
            continue
        else:
            channel = METRIKA_CHANNEL.get(key.lower(), 'other')
        metric = f'visits_{channel}_{device_class(_dim_key(dims[2]))}'
        try:
            value = float(metrics[0] or 0)
        except (TypeError, ValueError):
            continue
        out[metric][date] = out[metric].get(date, 0) + value
    return out


def parse_ga4_channel_rows(payload: dict, classes: dict,
                           *, referral: bool = False) -> dict:
    """Сессии GA4 в разрезе «дата × группа каналов (или источник) × устройство»."""
    out = {m: {} for m in channel_metrics('sessions')}
    for row in payload.get('rows', []):
        dims = [str((d or {}).get('value') or '') for d in (row.get('dimensionValues') or [])]
        metrics = row.get('metricValues') or []
        if len(dims) < 3 or not metrics:
            continue
        date = _ga4_date(dims[0])
        group = dims[1].strip().lower()
        if referral:
            channel = classify_referral(dims[1], classes)
        elif group == 'referral':
            continue
        else:
            channel = GA4_CHANNEL.get(group, 'other')
        metric = f'sessions_{channel}_{device_class(dims[2])}'
        try:
            value = float((metrics[0] or {}).get('value') or 0)
        except (TypeError, ValueError):
            continue
        out[metric][date] = out[metric].get(date, 0) + value
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


def window_for(store: dict, expected: tuple = ()) -> tuple[dt.date, dt.date]:
    """Пустой ряд — забрать историю целиком; иначе — только хвост.

    Новый разрез (например, «устройство × канал») появляется в коде позже
    самой витрины. Если обязательного ряда в ней ещё нет, окно снова
    становится историческим: разрез дозаполняется задним числом на всю
    глубину источника, а не начинается с сегодняшнего дня. Ряд, который
    источник отдал пустым, в витрине всё равно заведён — повторной выкачки
    истории он не вызывает.
    """
    end = base.today()
    series = store.get('series') or {}
    if not any(series.values()):
        return HISTORY_START, end
    if any(metric not in series for metric in expected):
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
    # Разрез по типу устройства — отдельный запрос на класс. Его сбой не
    # закрывает источник: общий ряд показов уже собран, а блок «Аудитория»
    # честно скажет «нет данных» по устройствам, пока ряда нет.
    for device, indicator in YANDEX_DEVICE.items():
        data, err = base.api_json(
            f'{api}/{uid}/hosts/{host_id}/search-queries/all/history',
            headers=headers, params={**params, 'device_type_indicator': indicator})
        if err:
            print(f'daily/yandex: разрез {device} не собран: {err}')
            continue
        series.update(parse_yandex_device_history(data, device))
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
    url = f'https://www.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query'
    data, err = base.api_json(url, headers=headers, body=body)
    if err:
        return None, f'searchAnalytics/query(date): {err}'
    series = parse_gsc_rows(data)
    # Дней в окне меньше тысячи, устройств три — потолок строк с запасом.
    devices, err = base.api_json(url, headers=headers, body={
        **body, 'dimensions': ['date', 'device'], 'rowLimit': 25000})
    if err:
        print(f'daily/gsc: разрез по устройствам не собран: {err}')
    else:
        series.update(parse_gsc_device_rows(devices))
    return series, None


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
    # Разрез «канал × устройство». Оба запроса кладутся в витрину только
    # вместе: срез без переходов с сайтов и срез по их доменам дополняют
    # друг друга, и половина разреза дала бы заниженные внешние каналы.
    channels, err = fetch_metrika_channels(stat, headers, {
        'ids': counter, 'date1': date_from.isoformat(),
        'date2': date_to.isoformat(), 'accuracy': 'full'})
    if err:
        print(f'daily/metrika: разрез «канал × устройство» не собран: {err}')
    else:
        series.update(channels)
    return series, None


def _metrika_paged(url: str, headers: dict, params: dict, limit: int = 10000):
    """Постраничный обход stat-API: строк «дата × канал × устройство» много."""
    rows, offset = [], 1
    while True:
        data, err = base.api_json(url, headers=headers,
                                  params={**params, 'limit': limit, 'offset': offset})
        if err:
            return None, err
        chunk = data.get('data') or []
        rows.extend(chunk)
        if len(chunk) < limit:
            return {'data': rows}, None
        offset += limit


def fetch_metrika_channels(stat: str, headers: dict, common: dict):
    """Визиты Метрики по каналам и устройствам: (ряды, None) либо (None, ошибка)."""
    classes = load_referral_classes()
    plain, err = _metrika_paged(stat, headers, {
        **common, 'metrics': 'ym:s:visits',
        'dimensions': 'ym:s:date,ym:s:lastTrafficSource,ym:s:deviceCategory'})
    if err:
        return None, f'stat(channels): {err}'
    series = parse_metrika_channel_rows(plain, classes)
    referral, err = _metrika_paged(stat, headers, {
        **common, 'metrics': 'ym:s:visits',
        'dimensions': 'ym:s:date,ym:s:lastReferalSource,ym:s:deviceCategory',
        'filters': "ym:s:lastTrafficSource=='referral'"})
    if err:
        return None, f'stat(referral): {err}'
    for metric, days in parse_metrika_channel_rows(referral, classes,
                                                   referral=True).items():
        for day, value in days.items():
            series[metric][day] = series[metric].get(day, 0) + value
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
    url = f'https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport'
    data, err = base.api_json(url, headers=headers, body=body)
    if err:
        return None, f'runReport(date): {err}'
    series = parse_ga4_rows(data, GA4_METRICS)
    dates = body['dateRanges']
    channels, err = fetch_ga4_channels(url, headers, dates)
    if err:
        print(f'daily/ga4: разрез «канал × устройство» не собран: {err}')
    else:
        series.update(channels)
    return series, None


def fetch_ga4_channels(url: str, headers: dict, dates: list):
    """Сессии GA4 по группам каналов и устройствам: (ряды, None) либо (None, ошибка).

    Как и у Метрики, переходы с сайтов раскрываются отдельным запросом по
    источникам: группа Referral в общем срезе пропускается.
    """
    classes = load_referral_classes()
    body = {'dateRanges': dates,
            'dimensions': [{'name': 'date'}, {'name': 'sessionDefaultChannelGroup'},
                           {'name': 'deviceCategory'}],
            'metrics': [{'name': 'sessions'}], 'limit': 100000}
    plain, err = base.api_json(url, headers=headers, body=body)
    if err:
        return None, f'runReport(channels): {err}'
    series = parse_ga4_channel_rows(plain, classes)
    referral, err = base.api_json(url, headers=headers, body={
        **body,
        'dimensions': [{'name': 'date'}, {'name': 'sessionSource'},
                       {'name': 'deviceCategory'}],
        'dimensionFilter': {'filter': {
            'fieldName': 'sessionDefaultChannelGroup',
            'stringFilter': {'value': 'Referral'}}}})
    if err:
        return None, f'runReport(referral): {err}'
    for metric, days in parse_ga4_channel_rows(referral, classes,
                                               referral=True).items():
        for day, value in days.items():
            series[metric][day] = series[metric].get(day, 0) + value
    return series, None


# ---------------------------------------------------------------------------

SOURCES = (
    # (имя файла, функция, обязательный секрет, охват ряда)
    ('yandex', fetch_yandex, 'YANDEX_WEBMASTER_TOKEN', 'site'),
    ('gsc', fetch_gsc, 'GSC_SERVICE_ACCOUNT_JSON', 'site'),
    ('metrika', fetch_metrika, 'YANDEX_METRIKA_TOKEN', 'site'),
    ('ga4', fetch_ga4, 'GA4_PROPERTY_ID', 'site'),
)

# Ряды, которые витрина источника обязана содержать. Нет хотя бы одного —
# прогон забирает историю целиком (см. window_for), а не хвост: так разрез,
# заведённый позже витрины, дозаполняется задним числом.
EXPECTED = {
    'yandex': ('impressions', 'clicks', *device_metrics('impressions', 'clicks')),
    'gsc': ('impressions', 'clicks', 'position',
            *device_metrics('impressions', 'clicks')),
    'metrika': (*METRIKA_METRICS, *METRIKA_ALL_METRICS, *channel_metrics('visits')),
    'ga4': (*GA4_METRICS, *channel_metrics('sessions')),
}


def main() -> int:
    ok = True
    for name, fn, secret, scope in SOURCES:
        store = load_store(name)
        date_from, date_to = window_for(store, EXPECTED[name])
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
