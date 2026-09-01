#!/usr/bin/env python3
"""Сбор заявок и восстановление пути клиента по визитам Метрики.

Запускается воркфлоу ops-leads-collect: заявки выгружаются на прод-сервере
из Directus (сессия к базе не ходит, правило доступа), кладутся в файл, а
этот скрипт поднимает по каждому посетителю его визиты в Метрике и
складывает витрину reports/seo/data/leads-<дата>.json — оттуда её читают
snapshot.py и письмо.

Что в витрине есть и чего в ней нет. Есть: время заявки, компания и ИНН
(это реквизиты юрлица, а не персональные данные), состав запроса, сумма,
метки источника и путь визитов. Нет: имени контактного лица, телефона и
почты — они нужны менеджеру в письме о заявке и в воронке, а не в
аналитической витрине, которая живёт в репозитории и в журналах прогонов.

Обогащение Метрикой мягкое: любая ошибка API оставляет заявку без пути и
записывается в поле error. Отчёт в этом случае честно скажет, что канал
восстановлен по метке браузера, — но письмо соберётся.

Запуск: python3 scripts/seo/leads_collect.py [--raw файл] [--date YYYY-MM-DD]
Секреты: YANDEX_METRIKA_TOKEN, YANDEX_METRIKA_COUNTER_ID.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect as base  # noqa: E402 — общие api_json, счётчик, московская дата

OUT_DIR = pathlib.Path('reports/seo/data')
STAT_URL = 'https://api-metrika.yandex.net/stat/v1/data'

# Глубина поиска визитов назад от заявки. Цикл сделки в B2B — недели, и
# первое касание тремя днями раньше заявки скорее правило, чем исключение;
# 90 дней совпадают со сроком жизни first-touch в браузере
# (src/lib/attribution.ts), поэтому оба источника говорят об одном окне.
JOURNEY_DAYS = 90

# Сколько заявок обогащать за прогон. Каждая — отдельный запрос к API;
# суточный поток заявок меньше на порядок, потолок нужен на случай
# первого прогона по накопленной истории.
MAX_ENRICHED = 40

# Поля выгрузки, которые переносятся в витрину как есть.
PASS_FIELDS = (
    'id', 'created_at', 'company', 'inn', 'form_source', 'source',
    'product_ref', 'amount', 'quote_no', 'status',
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
    'yclid', 'gclid', 'first_touch_source', 'first_touch_ts',
    'last_touch_source', 'landing_path', 'ym_client_id',
)

# Персональные данные: в витрину не попадают ни при каких обстоятельствах.
# Список перечислен явно, чтобы новое поле в Directus не проехало в
# репозиторий вместе с остальной записью.
DROP_FIELDS = ('name', 'email', 'phone', 'message', 'note', 'owner')


def normalize(rows: list[dict]) -> list[dict]:
    """Запись Directus → запись витрины: только разрешённые поля."""
    out = []
    for row in rows:
        lead = {k: row.get(k) for k in PASS_FIELDS if row.get(k) not in (None, '')}
        for k in DROP_FIELDS:
            lead.pop(k, None)
        out.append(lead)
    return out


def parse_steps(payload: dict) -> list[dict]:
    """Ответ Stat API → шаги пути, от раннего визита к позднему.

    Дименсии запрашиваются в фиксированном порядке (дата, источник,
    поисковая система, страница входа), поэтому разбор идёт по индексу:
    имена полей у Метрики различаются между версиями справочника, а
    порядок задаём мы сами.
    """
    steps = []
    for row in payload.get('data', []):
        dims = row.get('dimensions') or []
        if len(dims) < 4:
            continue
        date = str(dims[0].get('name') or '')[:10]
        source = dims[1].get('id') or dims[1].get('name') or 'undefined'
        engine = dims[2].get('name') or ''
        landing = dims[3].get('name') or ''
        visits = (row.get('metrics') or [0])[0]
        steps.append({
            'date': date,
            'source': str(source).lower(),
            # «Search engine traffic» без разбивки по системе Метрика
            # отдаёт как N/A — пустая строка честнее подписи-заглушки.
            'engine': '' if engine.lower() in ('n/a', 'нет данных') else engine,
            'landing': landing,
            'visits': visits,
        })
    steps.sort(key=lambda s: s['date'])
    return steps


def fetch_journey(client_id: str, until: str, *, headers: dict, counter: str) -> dict:
    """Визиты одного посетителя до дня заявки включительно."""
    date2 = (until or base.TODAY)[:10]
    date1 = (dt.date.fromisoformat(date2) - dt.timedelta(days=JOURNEY_DAYS)).isoformat()
    data, err = base.api_json(STAT_URL, headers=headers, params={
        'ids': counter, 'date1': date1, 'date2': date2, 'accuracy': 'full',
        'limit': 100, 'sort': 'ym:s:date',
        'dimensions': ('ym:s:date,ym:s:lastTrafficSource,'
                       'ym:s:lastSearchEngineRoot,ym:s:startURLPath'),
        'metrics': 'ym:s:visits',
        'filters': f"ym:s:clientID=='{client_id}'",
    })
    if err:
        return {'available': False, 'error': err}
    steps = parse_steps(data)
    if not steps:
        return {'available': False, 'error': ''}
    totals = data.get('totals') or []
    visits = totals[0] if totals and not isinstance(totals[0], list) else sum(
        s['visits'] for s in steps)
    return {
        'available': True,
        'visits': int(visits or 0),
        'first_visit': steps[0]['date'],
        'last_visit': steps[-1]['date'],
        'steps': steps,
    }


def enrich(leads: list[dict]) -> dict:
    """Путь по каждой заявке. Возвращает состояние источника для витрины."""
    token = os.environ.get('YANDEX_METRIKA_TOKEN', '')
    counter = os.environ.get('YANDEX_METRIKA_COUNTER_ID', '').strip()
    if not token or not counter:
        return {'available': False, 'error': 'токен или счётчик Метрики не заданы'}
    if counter != base.EXPECTED_METRIKA_COUNTER:
        # То же правило, что у collect.py: чужой счётчик даёт правдоподобный,
        # но не наш путь клиента — это хуже отсутствия пути.
        return {'available': False,
                'error': (f'счётчик сборщика {counter} не совпадает со счётчиком '
                          f'сайта {base.EXPECTED_METRIKA_COUNTER}')}
    headers = {'Authorization': f'OAuth {token}'}
    first_error = None
    for lead in leads[:MAX_ENRICHED]:
        client_id = lead.get('ym_client_id')
        if not client_id:
            continue
        journey = fetch_journey(str(client_id), lead.get('created_at', ''),
                                headers=headers, counter=counter)
        lead['journey'] = journey
        if journey.get('error') and first_error is None:
            first_error = journey['error']
    return {'available': True, 'error': first_error, 'counter': counter}


def load_raw(path: pathlib.Path) -> list[dict]:
    """Выгрузка с сервера: массив записей или объект с ключом leads/data."""
    payload = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(payload, dict):
        payload = payload.get('leads') or payload.get('data') or []
    return [r for r in payload if isinstance(r, dict)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default=os.environ.get('LEADS_RAW', 'leads-raw.json'))
    ap.add_argument('--date', default=base.TODAY)
    args = ap.parse_args()

    raw_path = pathlib.Path(args.raw)
    if not raw_path.exists():
        print(f'выгрузка заявок не найдена: {raw_path}', file=sys.stderr)
        return 1

    leads = normalize(load_raw(raw_path))
    leads.sort(key=lambda l: l.get('created_at') or '')
    metrika = enrich(leads)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f'leads-{args.date}.json'
    out.write_text(json.dumps({
        'date': args.date,
        'collected_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'source': 'directus:leads',
        'leads_available': True,
        'leads': leads,
        'metrika': metrika,
    }, ensure_ascii=False, indent=1), encoding='utf-8')
    resolved = sum(1 for l in leads if (l.get('journey') or {}).get('available'))
    print(f'leads: {out} — заявок {len(leads)}, путь восстановлен у {resolved}')
    if metrika.get('error'):
        print(f'Метрика: {metrika["error"]}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
