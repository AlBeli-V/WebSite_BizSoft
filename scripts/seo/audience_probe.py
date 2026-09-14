#!/usr/bin/env python3
"""Зонд разреза «устройство × канал»: доступ к API и наличие индикаторов.

Блок «Аудитория» (docs/rules/audience-devices.md) опирается на четыре запроса,
которых в конвейере раньше не было: device_type_indicator у Вебмастера, разрез
date × device у Search Console, измерения deviceCategory и lastReferalSource у
Метрики, deviceCategory и sessionSource у GA4. Проверить их из сессии нечем —
сеть к API закрыта, токены живут в секретах Actions. Зонд запускается
воркфлоу ops-audience-probe и отвечает на три вопроса:

  1) доступ: принимает ли источник запрос теми же параметрами, какими его
     шлёт сборщик (вызываются функции самого сборщика, не их копии);
  2) индикаторы: пришёл ли каждый обязательный ряд витрины и есть ли в нём
     непустые дни;
  3) полнота: сходится ли сумма по устройствам с общим рядом и не появилось
     ли у источника значения измерения, которого нет в словарях сборщика
     (новая группа каналов, новый тип устройства) — такое значение молча
     утекло бы в «прочее».

Запуск: python3 scripts/seo/audience_probe.py [дней]
Код возврата: 0 — все обязательные проверки зелёные, 1 — есть красные.
Значения секретов не печатаются: в отчёт идут только имена и статусы.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import collect as base          # noqa: E402
import collect_daily as cd      # noqa: E402

# Окно зонда. Десять дней — тот же хвост, что перечитывает ежедневный сбор:
# достаточно, чтобы у источника были непустые дни, и мало, чтобы прогон был
# быстрым и дешёвым по квоте.
DEFAULT_DAYS = 10

# Расхождение суммы устройств с общим рядом, которое считается нормой.
# Источники округляют и относят часть показов к неопознанному устройству;
# больше десятой доли — уже не округление, а другой охват.
COVERAGE_TOLERANCE = 0.10

SECRETS = {
    'yandex': ('YANDEX_WEBMASTER_TOKEN',),
    'gsc': ('GSC_SERVICE_ACCOUNT_JSON',),
    'metrika': ('YANDEX_METRIKA_TOKEN', 'YANDEX_METRIKA_COUNTER_ID'),
    'ga4': ('GA4_PROPERTY_ID', 'GSC_SERVICE_ACCOUNT_JSON'),
}

checks: list[dict] = []


def add(source: str, name: str, ok: bool | None, detail: str) -> None:
    """Строка отчёта. ok=None — проверка не выполнялась (нет секрета)."""
    checks.append({'source': source, 'check': name, 'ok': ok, 'detail': detail})


def nonempty_days(series: dict, metric: str) -> int:
    """Сколько дней ряда несут значение больше нуля."""
    return sum(1 for v in (series.get(metric) or {}).values() if v)


def window_sum(series: dict, metric: str) -> float:
    return sum(float(v or 0) for v in (series.get(metric) or {}).values())


def check_series(source: str, series: dict, metrics: tuple) -> None:
    """Наличие каждого обязательного ряда и непустых дней в нём."""
    missing = [m for m in metrics if m not in series]
    add(source, 'ряды витрины', not missing,
        f'обязательных рядов {len(metrics)}, отсутствуют: '
        + (', '.join(missing) if missing else 'нет'))
    empty = [m for m in metrics if m in series and not nonempty_days(series, m)]
    # Пустой ряд — не обязательно поломка: планшетов может не быть вовсе.
    # Поэтому это предупреждение отчёта, а не красная проверка.
    add(source, 'непустые дни', True,
        'ряды без единого ненулевого дня: ' + (', '.join(empty) if empty else 'нет'))


def check_device_coverage(source: str, series: dict, total_metric: str,
                          device_metrics: list[str]) -> None:
    """Сходится ли сумма по устройствам с общим рядом того же окна."""
    total = window_sum(series, total_metric)
    by_device = sum(window_sum(series, m) for m in device_metrics)
    if not total:
        add(source, 'покрытие устройствами', None,
            f'общий ряд {total_metric} пуст за окно — сверять нечего')
        return
    gap = abs(total - by_device) / total
    add(source, 'покрытие устройствами', gap <= COVERAGE_TOLERANCE,
        f'{total_metric} {total:.0f}, сумма по устройствам {by_device:.0f}, '
        f'расхождение {gap * 100:.1f}% при допуске {COVERAGE_TOLERANCE * 100:.0f}%')


def probe_yandex(date_from: dt.date, date_to: dt.date) -> None:
    """Вебмастер: история показов целиком и по каждому типу устройства."""
    series, err = cd.fetch_yandex(date_from, date_to)
    add('yandex', 'доступ к API', not err, err or 'история отдана без ошибок')
    if err:
        return
    check_series('yandex', series,
                 tuple(m for m in cd.EXPECTED['yandex']))
    check_device_coverage('yandex', series, 'impressions',
                          [f'impressions_{d}' for d in cd.YANDEX_DEVICE])
    # device_type_indicator принят, если ряд устройства вообще появился:
    # fetch_yandex пропускает класс, запрос по которому дал ошибку.
    accepted = [d for d in cd.YANDEX_DEVICE if f'impressions_{d}' in series]
    add('yandex', 'device_type_indicator',
        len(accepted) == len(cd.YANDEX_DEVICE),
        'приняты классы: ' + (', '.join(accepted) if accepted else 'ни одного')
        + f' из {", ".join(cd.YANDEX_DEVICE)}')


def probe_gsc(date_from: dt.date, date_to: dt.date) -> None:
    """Search Console: разрез date × device."""
    series, err = cd.fetch_gsc(date_from, date_to)
    add('gsc', 'доступ к API', not err, err or 'Search Analytics отдал данные')
    if err:
        return
    check_series('gsc', series, tuple(cd.EXPECTED['gsc']))
    check_device_coverage('gsc', series, 'impressions',
                          [f'impressions_{d}' for d in cd.GSC_DEVICE.values()])


def _metrika_headers() -> dict:
    return {'Authorization': f"OAuth {os.environ['YANDEX_METRIKA_TOKEN']}"}


def probe_metrika(date_from: dt.date, date_to: dt.date) -> None:
    """Метрика: каналы, устройства и домены переходов."""
    series, err = cd.fetch_metrika(date_from, date_to)
    add('metrika', 'доступ к API', not err, err or 'stat-API отдал данные')
    if err:
        return
    check_series('metrika', series, tuple(cd.EXPECTED['metrika']))
    # Значения измерений, которых нет в словарях сборщика: они уходят в
    # «прочее» молча, и увидеть их можно только перечислив ответ.
    stat = 'https://api-metrika.yandex.net/stat/v1/data'
    counter = os.environ['YANDEX_METRIKA_COUNTER_ID'].strip()
    common = {'ids': counter, 'date1': date_from.isoformat(),
              'date2': date_to.isoformat(), 'accuracy': 'full', 'limit': 500}
    data, err = base.api_json(stat, headers=_metrika_headers(), params={
        **common, 'metrics': 'ym:s:visits',
        'dimensions': 'ym:s:lastTrafficSource,ym:s:deviceCategory'})
    if err:
        add('metrika', 'словарь каналов и устройств', False,
            f'перечисление значений измерений не выполнено: {err}')
        return
    known_channels = set(cd.METRIKA_CHANNEL) | {'referral'}
    unknown_ch, unknown_dev = set(), set()
    for row in data.get('data', []):
        dims = row.get('dimensions') or []
        if len(dims) < 2:
            continue
        channel = cd._dim_key(dims[0]).lower()
        device = cd._dim_key(dims[1]).lower()
        if channel and channel not in known_channels:
            unknown_ch.add(channel)
        if device and device not in cd.DEVICE_ALIAS:
            unknown_dev.add(device)
    add('metrika', 'словарь каналов', not unknown_ch,
        'значения ym:s:lastTrafficSource вне словаря: '
        + (', '.join(sorted(unknown_ch)) if unknown_ch else 'нет'))
    add('metrika', 'словарь устройств', not unknown_dev,
        'значения ym:s:deviceCategory вне словаря (уйдут в «прочие»): '
        + (', '.join(sorted(unknown_dev)) if unknown_dev else 'нет'))
    # Домены переходов: видно, какие из них реестр уже знает, а какие нет.
    data, err = base.api_json(stat, headers=_metrika_headers(), params={
        **common, 'metrics': 'ym:s:visits', 'dimensions': 'ym:s:lastReferalSource',
        'filters': "ym:s:lastTrafficSource=='referral'"})
    if err:
        add('metrika', 'домены переходов', False, f'разрез не выполнен: {err}')
        return
    classes = cd.load_referral_classes()
    seen = {}
    for row in data.get('data', []):
        dims = row.get('dimensions') or []
        if not dims:
            continue
        domain = cd._dim_key(dims[0])
        if domain:
            seen[domain] = cd.classify_referral(domain, classes)
    plain = sorted(d for d, cls in seen.items() if cls == 'links')
    add('metrika', 'реестр внешних переходов', True,
        f'доменов за окно: {len(seen)}; распознаны каталогом или площадкой: '
        f'{len(seen) - len(plain)}; считаются обычными ссылками: '
        + (', '.join(plain[:15]) + ('…' if len(plain) > 15 else '') if plain else 'нет'))


def probe_ga4(date_from: dt.date, date_to: dt.date) -> None:
    """GA4: группы каналов, устройства и источники переходов."""
    series, err = cd.fetch_ga4(date_from, date_to)
    add('ga4', 'доступ к API', not err, err or 'Data API отдал данные')
    if err:
        return
    check_series('ga4', series, tuple(cd.EXPECTED['ga4']))
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    info = json.loads(os.environ['GSC_SERVICE_ACCOUNT_JSON'])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/analytics.readonly'])
    creds.refresh(Request())
    headers = {'Authorization': f'Bearer {creds.token}'}
    prop = os.environ['GA4_PROPERTY_ID'].strip()
    url = f'https://analyticsdata.googleapis.com/v1beta/properties/{prop}:runReport'
    data, err = base.api_json(url, headers=headers, body={
        'dateRanges': [{'startDate': date_from.isoformat(),
                        'endDate': date_to.isoformat()}],
        'dimensions': [{'name': 'sessionDefaultChannelGroup'},
                       {'name': 'deviceCategory'}],
        'metrics': [{'name': 'sessions'}], 'limit': 500})
    if err:
        add('ga4', 'словарь каналов и устройств', False,
            f'перечисление значений измерений не выполнено: {err}')
        return
    known = set(cd.GA4_CHANNEL) | {'referral'}
    unknown_ch, unknown_dev = set(), set()
    for row in data.get('rows', []):
        dims = [str((d or {}).get('value') or '').strip().lower()
                for d in (row.get('dimensionValues') or [])]
        if len(dims) < 2:
            continue
        if dims[0] and dims[0] not in known:
            unknown_ch.add(dims[0])
        if dims[1] and dims[1] not in cd.DEVICE_ALIAS:
            unknown_dev.add(dims[1])
    add('ga4', 'словарь каналов', not unknown_ch,
        'группы sessionDefaultChannelGroup вне словаря: '
        + (', '.join(sorted(unknown_ch)) if unknown_ch else 'нет'))
    add('ga4', 'словарь устройств', not unknown_dev,
        'значения deviceCategory вне словаря (уйдут в «прочие»): '
        + (', '.join(sorted(unknown_dev)) if unknown_dev else 'нет'))


PROBES = (('yandex', probe_yandex), ('gsc', probe_gsc),
          ('metrika', probe_metrika), ('ga4', probe_ga4))


def report() -> str:
    """Отчёт для журнала: строка на проверку, источник за источником."""
    mark = {True: '✓', False: '✗', None: '·'}
    lines = []
    for source, _ in PROBES:
        rows = [c for c in checks if c['source'] == source]
        lines.append(f'[{source}]')
        for row in rows:
            lines.append(f"  {mark[row['ok']]} {row['check']}: {row['detail']}")
    failed = [c for c in checks if c['ok'] is False]
    done = [c for c in checks if c['ok'] is not None]
    lines.append('')
    if failed:
        lines.append(f'красных проверок: {len(failed)}')
    elif not done:
        # Прогон без единой выполненной проверки — не «всё хорошо», а
        # отсутствие проверки: без этой ветки зонд отчитывался зелёным,
        # не сходив ни в один источник.
        lines.append('проверок не выполнено ни одной: ни один источник не опрошен')
    else:
        lines.append(f'все выполненные проверки зелёные ({len(done)})')
    return '\n'.join(lines)


def main(argv: list[str]) -> int:
    days = int(argv[1]) if len(argv) > 1 else DEFAULT_DAYS
    date_to = base.today()
    date_from = date_to - dt.timedelta(days=days)
    for source, probe in PROBES:
        missing = [s for s in SECRETS[source] if not os.environ.get(s)]
        if missing:
            add(source, 'секреты', None, 'не заданы: ' + ', '.join(missing))
            continue
        try:
            probe(date_from, date_to)
        except Exception as e:  # noqa: BLE001 — сбой одного источника не валит зонд
            add(source, 'зонд', False, f'{type(e).__name__}: {e}')
    print(f'Окно зонда: {date_from.isoformat()}–{date_to.isoformat()}')
    print(report())
    failed = any(c['ok'] is False for c in checks)
    ran = any(c['ok'] is not None for c in checks)
    return 1 if failed or not ran else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
