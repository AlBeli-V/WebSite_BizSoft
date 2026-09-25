#!/usr/bin/env python3
"""Замер: каким вызовом Вебмастер отдаёт показы и клики в разрезе URL.

Повод. Срез `popular_urls` заведён 18.09.2026 для разбора выпадения карточек
из поиска (INDEX-004): показов по хосту хватало на сумму по сайту, но не на
ответ, чем выпавшие карточки отличались от уцелевших. Срез не отдал ни одной
строки ни в один из дней — все прогоны с 18 по 24.09 возвращают
`HTTP 404 RESOURCE_NOT_FOUND` на `search-urls/popular/`. Контракт сработал
как задумано (ошибка вместо пустого списка), но увидеть её было некому:
у среза нет потребителей в коде, и конвейер идёт дальше.

Почему замер, а не правка. Соседние методы того же хоста отвечают:
`search-queries/popular/` отдаёт полторы тысячи запросов, а
`search-urls/events/samples` — выборку событий. Значит доступ, токен и
host_id в порядке, и расходится только сам вызов. Урок отказа Метрики
22.09.2026 записан в историю прямо: две правки вслепую — понижение точности
и сокращение окна — отказ не сняли, и третья догадка ничем не лучше первых
двух. Поэтому перебираем по одному различию за раз и печатаем ответ целиком.

Что перебирается:
  1. контроли — вызовы, которые сегодня работают (популярные запросы,
     выборка событий, сводка хоста). Если упадут и они, дело не в пути;
  2. текущий вызов среза — воспроизведение отказа в тех же параметрах;
  3. тот же путь без хвостового слэша и без каждого из параметров по
     очереди: 404 в API Вебмастера отдаётся и на неизвестный параметр,
     не только на неизвестный путь;
  4. другие имена того же семейства: `search-urls/in-search/samples`,
     `search-urls/in-search/history`, `search-urls/events/history`,
     `search-urls/all/popular`, `search-urls/popular-urls` и корень
     `search-urls`;
  5. `search-queries/all/history` — семейство запросов умеет историю по
     индикаторам; если разрез по URL в API живёт там, это будет видно.

Ответ каждого вызова печатается статусом, а у успешного — ключами верхнего
уровня и первой строкой данных: имя метода без формы ответа не говорит,
годится ли он под задачу.

Только чтение: ни сайт, ни кабинет, ни счётчик не меняются.

Запуск — workflow ops-webmaster-urls-probe (секрет YANDEX_WEBMASTER_TOKEN),
вывод уходит в журнал issue #22.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import requests  # noqa: E402  (после sys.path — как в остальных скриптах контура)

API = 'https://api.webmaster.yandex.net/v4/user'
SITE = 'biz-soft.pro'
TIMEOUT = 30

# Окно берётся тем же, каким его строит сборщик: замер должен воспроизводить
# боевой вызов, а не свой собственный.
DATE_TO = dt.date.today()
DATE_FROM = DATE_TO - dt.timedelta(days=14)

# Параметры боевого вызова среза — точка отсчёта для вариаций.
URLS_PARAMS = {
    'order_by': 'TOTAL_SHOWS',
    'url_indicator': ['TOTAL_SHOWS', 'TOTAL_CLICKS'],
    'date_from': DATE_FROM.isoformat(),
    'date_to': DATE_TO.isoformat(),
    'limit': 100,
}


def call(url: str, params: dict | None = None) -> tuple[int | None, object, str]:
    """(HTTP-статус, разобранное тело или None, короткая строка ответа)."""
    headers = {'Authorization': f"OAuth {os.environ['YANDEX_WEBMASTER_TOKEN']}"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        return None, None, f'{type(e).__name__}: {e}'
    try:
        body = r.json()
    except ValueError:
        return r.status_code, None, f'ответ не JSON: {r.text[:200]}'
    return r.status_code, body, r.text[:300]


def describe(body: object) -> str:
    """Форма успешного ответа: ключи и первая строка данных."""
    if not isinstance(body, dict):
        return f'тело не объект: {json.dumps(body, ensure_ascii=False)[:200]}'
    keys = list(body)
    out = [f'ключи: {keys}']
    for k in ('urls', 'queries', 'samples', 'indicators', 'history'):
        rows = body.get(k)
        if isinstance(rows, list):
            out.append(f'{k}: строк {len(rows)}')
            if rows:
                out.append(f'первая строка: {json.dumps(rows[0], ensure_ascii=False)[:300]}')
            break
    return ' | '.join(out)


def probe(label: str, url: str, params: dict | None = None) -> bool:
    status, body, raw = call(url, params)
    head = f'[{label}]'
    if status == 200:
        print(f'{head} прошёл 200 — {describe(body)}')
        return True
    print(f'{head} отказ {status}: {raw}')
    return False


def main() -> int:
    host_url = f'{API}'
    status, body, raw = call(host_url)
    if status != 200 or not isinstance(body, dict) or 'user_id' not in body:
        print(f'/user недоступен ({status}): {raw}')
        return 1
    uid = body['user_id']

    status, body, raw = call(f'{API}/{uid}/hosts')
    if status != 200 or not isinstance(body, dict):
        print(f'/hosts недоступен ({status}): {raw}')
        return 1
    match = [h for h in body.get('hosts', []) if SITE in h.get('host_id', '')]
    if not match:
        print(f'{SITE} не найден в аккаунте Вебмастера')
        return 1
    host_id = match[0]['host_id']
    base = f'{API}/{uid}/hosts/{host_id}'
    print(f'аккаунт: user_id={uid}, host_id={host_id}')
    print(f'окно замера: {DATE_FROM.isoformat()} → {DATE_TO.isoformat()}')
    print()

    print('== Контроли: вызовы, которые работают сегодня ==')
    probe('сводка хоста', f'{base}/summary')
    probe('популярные запросы (боевой вызов)', f'{base}/search-queries/popular/', {
        'order_by': 'TOTAL_SHOWS',
        'query_indicator': ['TOTAL_SHOWS', 'TOTAL_CLICKS'],
        'date_from': DATE_FROM.isoformat(),
        'date_to': DATE_TO.isoformat(),
        'limit': 100,
    })
    probe('выборка событий по URL', f'{base}/search-urls/events/samples', {
        'date_from': DATE_FROM.isoformat(),
        'date_to': DATE_TO.isoformat(),
        'limit': 10,
    })
    print()

    print('== Отказ среза: воспроизведение и вариации по одному различию ==')
    probe('боевой вызов среза', f'{base}/search-urls/popular/', URLS_PARAMS)
    probe('без хвостового слэша', f'{base}/search-urls/popular', URLS_PARAMS)
    probe('без url_indicator',
          f'{base}/search-urls/popular/',
          {k: v for k, v in URLS_PARAMS.items() if k != 'url_indicator'})
    probe('без order_by',
          f'{base}/search-urls/popular/',
          {k: v for k, v in URLS_PARAMS.items() if k != 'order_by'})
    probe('только окно и лимит',
          f'{base}/search-urls/popular/',
          {'date_from': DATE_FROM.isoformat(), 'date_to': DATE_TO.isoformat(), 'limit': 10})
    probe('вовсе без параметров', f'{base}/search-urls/popular/')
    print()

    print('== Другие имена того же семейства ==')
    window = {'date_from': DATE_FROM.isoformat(), 'date_to': DATE_TO.isoformat(), 'limit': 10}
    probe('корень search-urls', f'{base}/search-urls')
    probe('in-search/samples', f'{base}/search-urls/in-search/samples', window)
    probe('in-search/history', f'{base}/search-urls/in-search/history', window)
    probe('events/history', f'{base}/search-urls/events/history', window)
    probe('all/popular', f'{base}/search-urls/all/popular', URLS_PARAMS)
    probe('popular-urls', f'{base}/search-urls/popular-urls', URLS_PARAMS)
    print()

    print('== Семейство запросов: история по индикаторам ==')
    probe('search-queries/all/history', f'{base}/search-queries/all/history', {
        'query_indicator': ['TOTAL_SHOWS', 'TOTAL_CLICKS'],
        'date_from': DATE_FROM.isoformat(),
        'date_to': DATE_TO.isoformat(),
    })
    print()

    print('Замер закончен. Рабочим считается вызов, который вернул 200 и отдал '
          'строки с показами и кликами в разрезе URL; если такого нет — метода '
          'в API нет, и признак отклика по страницам этим путём не берётся.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
