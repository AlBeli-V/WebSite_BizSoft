#!/usr/bin/env python3
"""Обогащение заявок данными Метрики и Директа для письма об источнике.

Запускается воркфлоу ops-lead-source-mail на раннере: там лежат токены
Метрики и Директа, а на прод-сервере их нет и быть не должно. На вход
подаётся безличный список заявок (идентификатор, дата, clientID, метки
клика) — его отдаёт эндпоинт /api/admin/leads/source-mail. На выход
кладётся слепок по каждой заявке, который тот же эндпоинт вставляет в
письмо. Персональные данные в этом контуре не участвуют вовсе: имя,
телефон, почта и текст обращения остаются на сервере.

Что собирается по каждой заявке:

  * канал визита (ym:s:lastTrafficSource) — органика, реклама, переход с
    сайта, прямой заход;
  * поисковая система и поисковая фраза, если Метрика её отдала;
  * домен площадки, с которой пришёл переход;
  * цепочка визитов посетителя за 90 дней до заявки;
  * для рекламных заявок — кампания, группа, объявление, условие показа и
    средняя цена клика по нему за день (точную цену клика Директ не отдаёт).

Ничего не выдумывает: недоступный раздел превращается в текст причины,
который письмо печатает дословно.

Запуск: python3 scripts/ops/lead_source_enrich.py --leads вход.json --out выход.json
Секреты: YANDEX_METRIKA_TOKEN, YANDEX_METRIKA_COUNTER_ID, YANDEX_DIRECT_TOKEN.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

STAT_URL = 'https://api-metrika.yandex.net/stat/v1/data'
DIRECT_URL = 'https://api.direct.yandex.com/json/v5/'

# Глубина поиска визитов назад от заявки — как в leads_collect.py и как срок
# жизни первого касания в браузере: три источника говорят об одном окне.
JOURNEY_DAYS = 90

# Наборы измерений от богатого к бедному. Справочник Метрики со временем
# меняется, и неизвестное измерение роняет запрос целиком: вместо разбора
# ошибки берём следующий набор, а в слепок кладём, какой именно сработал.
DIM_SETS = [
    ('ym:s:date,ym:s:lastTrafficSource,ym:s:lastSearchEngine,'
     'ym:s:lastSearchPhrase,ym:s:lastReferalSource,ym:s:startURLPath'),
    ('ym:s:date,ym:s:lastTrafficSource,ym:s:lastSearchEngineRoot,'
     'ym:s:lastSearchPhrase,ym:s:startURLPath'),
    'ym:s:date,ym:s:lastTrafficSource,ym:s:lastSearchEngineRoot,ym:s:startURLPath',
]

# Измерения Директа: кампания, группа, объявление, условие показа.
DIRECT_DIMS = ('ym:s:date,ym:s:lastDirectClickOrder,ym:s:lastDirectBannerGroup,'
               'ym:s:lastDirectClickBanner,ym:s:lastDirectPhraseOrCond')

# Канал Метрики → как он называется в письме.
SOURCE_LABEL = {
    'organic': 'поиск',
    'ad': 'реклама',
    'direct': 'прямой заход',
    'referral': 'переход с сайта',
    'social': 'соцсеть',
    'recommend': 'рекомендательная система',
    'internal': 'внутренний переход',
    'saved': 'закладки',
    'email': 'письмо',
    'messenger': 'мессенджер',
}


def api_json(url: str, headers: dict, params: dict) -> tuple[dict, str]:
    """GET с разбором JSON. Вторым значением — причина отказа для письма."""
    full = f'{url}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(full, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode('utf-8')), ''
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')[:300]
        return {}, f'HTTP {e.code}: {body}'
    except (urllib.error.URLError, OSError, ValueError) as e:
        return {}, f'{type(e).__name__}: {e}'


def window(created_at: str) -> tuple[str, str]:
    """Окно поиска визитов: 90 дней до дня заявки включительно."""
    day = (created_at or '')[:10]
    try:
        end = dt.date.fromisoformat(day)
    except ValueError:
        end = dt.datetime.now(dt.timezone.utc).date()
    return (end - dt.timedelta(days=JOURNEY_DAYS)).isoformat(), end.isoformat()


def _name(dim: dict) -> str:
    """Значение измерения: имя, а при его отсутствии — идентификатор."""
    value = dim.get('name') or dim.get('id') or ''
    value = str(value).strip()
    # Метрика отдаёт «N/A» и «Не определено» там, где данных нет. Подпись-
    # заглушка в письме хуже пустоты: пустое поле честно молчит.
    if value.lower() in ('n/a', 'не определено', 'нет данных', 'none', 'null'):
        return ''
    return value


def fetch_visits(client_id: str, created_at: str, headers: dict, counter: str) -> dict:
    """Визиты посетителя из Метрики. Возвращает слепок для письма."""
    date1, date2 = window(created_at)
    last_error = ''
    for dims in DIM_SETS:
        data, err = api_json(STAT_URL, headers, {
            'ids': counter, 'date1': date1, 'date2': date2, 'accuracy': 'full',
            'limit': 100, 'sort': 'ym:s:date',
            'dimensions': dims,
            'metrics': 'ym:s:visits',
            'filters': f"ym:s:clientID=='{client_id}'",
        })
        if err:
            last_error = err
            continue
        return parse_visits(data, dims)
    return {'available': False, 'error': f'Метрика не ответила — {last_error}'}


def parse_visits(payload: dict, dims: str) -> dict:
    """Ответ Stat API → слепок источника. Порядок измерений задаём мы сами."""
    names = dims.split(',')
    idx = {n: i for i, n in enumerate(names)}
    steps = []
    for row in payload.get('data', []):
        d = row.get('dimensions') or []
        if len(d) < len(names):
            continue

        def val(key: str) -> str:
            i = idx.get(key)
            return _name(d[i]) if i is not None else ''

        source = (val('ym:s:lastTrafficSource') or '').lower()
        steps.append({
            'when': val('ym:s:date')[:10],
            'source': SOURCE_LABEL.get(source, source),
            'engine': val('ym:s:lastSearchEngine') or val('ym:s:lastSearchEngineRoot'),
            'phrase': val('ym:s:lastSearchPhrase'),
            'page': val('ym:s:startURLPath'),
            'visits': int((row.get('metrics') or [0])[0] or 0),
            '_source_id': source,
            '_referral': val('ym:s:lastReferalSource'),
        })
    if not steps:
        return {'available': False,
                'error': 'Метрика не нашла визитов этого посетителя: '
                         'счётчик мог не успеть их обработать или ClientID не совпал'}
    steps.sort(key=lambda s: s['when'])
    last = steps[-1]
    out = {
        'available': True,
        'trafficSource': last['_source_id'],
        'searchEngine': last['engine'],
        'searchPhrase': last['phrase'],
        'referralSource': last['_referral'],
        'visits': sum(s['visits'] for s in steps),
        'firstVisit': steps[0]['when'],
        'lastVisit': last['when'],
        'steps': [{k: v for k, v in s.items() if not k.startswith('_') and v not in ('', 0)}
                  for s in steps],
    }
    return {k: v for k, v in out.items() if v not in ('', None)}


def fetch_direct_dims(client_id: str, created_at: str, headers: dict, counter: str) -> dict:
    """Кампания, группа, объявление и условие показа рекламного визита."""
    date1, date2 = window(created_at)
    data, err = api_json(STAT_URL, headers, {
        'ids': counter, 'date1': date1, 'date2': date2, 'accuracy': 'full',
        'limit': 20, 'sort': '-ym:s:date',
        'dimensions': DIRECT_DIMS,
        'metrics': 'ym:s:visits',
        'filters': f"ym:s:clientID=='{client_id}'",
    })
    if err:
        return {'costNote': f'разделы Директа в Метрике недоступны — {err}'}
    for row in data.get('data', []):
        d = row.get('dimensions') or []
        if len(d) < 5:
            continue
        facts = {
            'date': _name(d[0])[:10],
            'campaign': _name(d[1]),
            'group': _name(d[2]),
            'ad': _name(d[3]),
            'phrase': _name(d[4]),
        }
        if facts['campaign']:
            return facts
    return {'costNote': 'Метрика не связала визит с кампанией Директа'}


def direct_report(definition: dict, token: str, name: str) -> tuple[str, str]:
    """Отчёт Директа в TSV. Вторым значением — причина отказа для письма.

    Заголовки запроса те же, что в scripts/ppc/direct_stats.py: деньги в
    рублях, а не в миллионных долях, шапка отчёта отброшена, режим — авто с
    ожиданием офлайн-очереди (Директ ставит отчёт в очередь и отвечает 201/202).
    """
    body = json.dumps({'params': definition}).encode('utf-8')
    for _ in range(10):
        req = urllib.request.Request(DIRECT_URL + 'reports', data=body, headers={
            'Authorization': f'Bearer {token}',
            'Accept-Language': 'ru',
            'Content-Type': 'application/json; charset=utf-8',
            'processingMode': 'auto',
            'returnMoneyInMicros': 'false',
            'skipReportHeader': 'true',
            'skipReportSummary': 'true',
        })
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                if resp.status == 200:
                    return resp.read().decode('utf-8'), ''
                retry = int(resp.headers.get('retryIn', '10') or '10')
        except urllib.error.HTTPError as e:
            return '', f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:200]}'
        except (urllib.error.URLError, OSError) as e:
            return '', f'{type(e).__name__}: {e}'
        time.sleep(min(retry, 30))
    return '', f'отчёт {name} не дождался готовности'


def fetch_cpc(facts: dict, token: str) -> dict:
    """Средняя цена клика по условию показа за день клика.

    Точной цены конкретного клика Директ не отдаёт ни одним отчётом: в
    выгрузке есть расход и число кликов за период, а не цена события. Поэтому
    берётся средняя по тому же условию показа за тот же день, и письмо
    называет её именно так — выдавать её за цену клика этого посетителя
    нельзя.
    """
    date = facts.get('date') or ''
    campaign = facts.get('campaign') or ''
    if not date or not campaign:
        return {'costNote': 'цену клика не запросить: неизвестны кампания или дата клика'}
    tsv, err = direct_report({
        'SelectionCriteria': {'DateFrom': date, 'DateTo': date},
        'FieldNames': ['CampaignName', 'Criterion', 'Clicks', 'Cost'],
        'ReportName': f'lead-cpc-{date}-{abs(hash(campaign)) % 10**6}',
        'ReportType': 'CRITERIA_PERFORMANCE_REPORT',
        'DateRangeType': 'CUSTOM_DATE',
        'Format': 'TSV',
        'IncludeVAT': 'YES',
        'IncludeDiscount': 'NO',
    }, token, 'цена клика')
    if err:
        return {'costNote': f'расход Директа недоступен — {err}'}
    lines = [l for l in tsv.rstrip('\n').split('\n') if l.strip()]
    if len(lines) < 2:
        return {'costNote': f'за {date} отчёт Директа пуст'}
    header = lines[0].split('\t')
    try:
        i_camp, i_crit = header.index('CampaignName'), header.index('Criterion')
        i_clicks, i_cost = header.index('Clicks'), header.index('Cost')
    except ValueError:
        return {'costNote': 'в отчёте Директа нет ожидаемых колонок'}

    clicks, cost = 0, 0.0
    phrase = facts.get('phrase') or ''
    for line in lines[1:]:
        row = line.split('\t')
        if len(row) <= max(i_camp, i_crit, i_clicks, i_cost):
            continue
        if row[i_camp] != campaign:
            continue
        # Условие показа сверяется, только когда Метрика его назвала: иначе
        # берётся средняя по кампании, и письмо говорит об этом прямо.
        if phrase and row[i_crit] != phrase:
            continue
        clicks += int(float(row[i_clicks] or 0))
        cost += float(row[i_cost] or 0)
    if not clicks:
        return {'costNote': f'за {date} по этой кампании кликов в отчёте Директа нет'}
    return {'avgCpcRub': round(cost / clicks, 2), 'costDate': date}


def enrich(leads: list[dict]) -> dict:
    """Слепок источника по каждой заявке: идентификатор → данные для письма."""
    token = os.environ.get('YANDEX_METRIKA_TOKEN', '')
    counter = os.environ.get('YANDEX_METRIKA_COUNTER_ID', '').strip()
    direct_token = os.environ.get('YANDEX_DIRECT_TOKEN', '')
    out: dict[str, dict] = {}

    if not token or not counter:
        reason = 'токен или счётчик Метрики не заданы в прогоне'
        return {str(l.get('id')): {'available': False, 'error': reason} for l in leads}

    headers = {'Authorization': f'OAuth {token}'}
    for lead in leads:
        key = str(lead.get('id'))
        client_id = str(lead.get('ym_client_id') or '').strip()
        if not client_id:
            out[key] = {
                'available': False,
                'error': 'у заявки нет ClientID Метрики: посетитель заблокировал счётчик '
                         'или заявка заведена до того, как сайт стал его записывать',
            }
            continue

        facts = fetch_visits(client_id, str(lead.get('created_at') or ''), headers, counter)
        paid = bool(lead.get('yclid')) or facts.get('trafficSource') == 'ad'
        if facts.get('available') and paid:
            direct = fetch_direct_dims(client_id, str(lead.get('created_at') or ''),
                                       headers, counter)
            if direct.get('campaign'):
                direct.update(fetch_cpc(direct, direct_token) if direct_token
                              else {'costNote': 'токен Директа в прогоне не задан'})
            facts['direct'] = direct
        out[key] = facts
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--leads', required=True, help='JSON со списком заявок (эндпоинт GET)')
    ap.add_argument('--out', required=True, help='куда положить слепок источника')
    args = ap.parse_args()

    payload = json.loads(pathlib.Path(args.leads).read_text(encoding='utf-8'))
    leads = payload.get('leads') if isinstance(payload, dict) else payload
    if not isinstance(leads, list):
        print('::error::во входном файле нет списка заявок')
        return 1

    data = enrich(leads)
    pathlib.Path(args.out).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    ready = sum(1 for v in data.values() if v.get('available'))
    print(f'заявок: {len(leads)}, с данными Метрики: {ready}')
    for key, value in data.items():
        if not value.get('available'):
            print(f'  заявка {key}: {value.get("error")}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
