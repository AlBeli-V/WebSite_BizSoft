#!/usr/bin/env python3
"""Синхронизация целей сайта с кабинетами Яндекс.Метрики и GA4.

Цель, которую шлёт сайт, но которой нет в кабинете, летит в пустоту: счётчик
вызов принимает, а в отчёте её нет — и ноль по ней читается как «обращений не
было». Именно так была потеряна конверсионная статистика (ANL-001). Поэтому
кабинеты заполняются не руками, а из одного реестра — src/lib/analytics.ts.

Реестр читается из TypeScript намеренно. Вторая копия списка на Python
разошлась бы с кодом при первой же правке, и мы вернулись бы к тому же:
сайт шлёт одно, кабинет ждёт другое, а расхождение видно только по нулям.

Режимы:
  --dry-run   показать, что будет заведено (по умолчанию);
  --apply     завести недостающее.

Ничего не удаляет: лишняя цель в кабинете безвредна, а снятая по ошибке
обнуляет историю.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'src/lib/analytics.ts'

GOAL_RE = re.compile(
    r"^\s*([a-z_]+):\s*\{\s*ga4:\s*'([^']+)',\s*key:\s*(true|false),\s*\n?\s*"
    r"meaning:\s*'([^']+)'\s*\}", re.M)


def load_goals() -> dict[str, dict]:
    """Разобрать реестр целей из TypeScript."""
    src = REGISTRY.read_text(encoding='utf-8')
    try:
        block = src.split('export const GOALS: Record<string, GoalSpec> = {', 1)[1]
        block = block.split('\n};', 1)[0]
    except IndexError:
        raise SystemExit('не найден блок GOALS в src/lib/analytics.ts')
    goals = {m.group(1): {'ga4': m.group(2), 'key': m.group(3) == 'true',
                          'meaning': m.group(4)} for m in GOAL_RE.finditer(block)}
    if not goals:
        raise SystemExit('реестр целей пуст — проверьте формат GOALS')
    return goals


def request(url: str, *, headers: dict, method: str = 'GET', body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        return e.code, {'error': e.read().decode()[:500]}


# ── Яндекс.Метрика ──────────────────────────────────────────────────────────

def metrika_sync(goals: dict[str, dict], apply: bool) -> list[str] | None:
    """Недостающие цели, либо None — если проверить не удалось.

    Разница принципиальна: пустой список значит «всё заведено», None значит
    «не смотрели». Складывать их в одно «всё на месте» — то же самое, что
    выдавать отсутствие замера за отсутствие проблемы.
    """
    token = os.environ.get('YANDEX_METRIKA_TOKEN', '').strip()
    counter = os.environ.get('YANDEX_METRIKA_COUNTER_ID', '').strip()
    if not token or not counter:
        print('Метрика: нет YANDEX_METRIKA_TOKEN или YANDEX_METRIKA_COUNTER_ID — пропуск')
        return None

    h = {'Authorization': f'OAuth {token}', 'Content-Type': 'application/json'}
    base = f'https://api-metrika.yandex.net/management/v1/counter/{counter}/goals'
    code, data = request(base, headers=h)
    if code != 200:
        print(f'Метрика: не удалось прочитать цели ({code}) {data.get("error", "")}')
        return None

    existing = {}
    for g in data.get('goals', []):
        for cond in g.get('conditions', []):
            if cond.get('type') == 'exact':
                existing[cond.get('url', '')] = g
    print(f'Метрика: заведено целей — {len(data.get("goals", []))}, '
          f'из них по событиям — {len(existing)}')

    created = []
    for name, spec in goals.items():
        if name in existing:
            continue
        created.append(name)
        if not apply:
            continue
        # Тип JavaScript-события: сайт шлёт reachGoal с этим именем.
        payload = {'goal': {
            'name': spec['meaning'][:100],
            'type': 'action',
            'is_retargeting': 0,
            'conditions': [{'type': 'exact', 'url': name}],
        }}
        code, resp = request(base, headers=h, method='POST', body=payload)
        mark = 'ok' if code in (200, 201) else f'ОШИБКА {code} {resp.get("error", "")[:200]}'
        print(f'  + {name} — {mark}')
    return created


# ── Google Analytics 4 ──────────────────────────────────────────────────────

def ga4_sync(goals: dict[str, dict], apply: bool) -> list[str] | None:
    """В GA4 события создаются сами; вручную помечаются только ключевые.

    None означает «проверить не удалось», а не «всё на месте».
    """
    raw = os.environ.get('GSC_SERVICE_ACCOUNT_JSON', '').strip()
    prop = os.environ.get('GA4_PROPERTY_ID', '').strip()
    if not raw or not prop:
        print('GA4: нет GSC_SERVICE_ACCOUNT_JSON или GA4_PROPERTY_ID — пропуск')
        return None
    try:
        from google.auth.transport.requests import Request as GRequest
        from google.oauth2 import service_account
    except ImportError:
        print('GA4: нет google-auth — pip install google-auth')
        return None

    creds = service_account.Credentials.from_service_account_info(
        json.loads(raw), scopes=['https://www.googleapis.com/auth/analytics.edit'])
    creds.refresh(GRequest())
    h = {'Authorization': f'Bearer {creds.token}', 'Content-Type': 'application/json'}
    base = f'https://analyticsadmin.googleapis.com/v1beta/properties/{prop}/keyEvents'

    code, data = request(base, headers=h)
    if code != 200:
        print(f'GA4: не удалось прочитать ключевые события ({code}) {data.get("error", "")}')
        return None
    existing = {k.get('eventName') for k in data.get('keyEvents', [])}
    print(f'GA4: ключевых событий — {len(existing)}')

    # Конверсии в GA4 помечаются по имени события GA4, а не по нашему:
    # generate_lead приходит и от формы, и от скачивания КП — различаем их
    # параметром bz_goal, а ключевым помечается само событие один раз.
    want = sorted({spec['ga4'] for spec in goals.values() if spec['key']})
    created = []
    for event in want:
        if event in existing:
            continue
        created.append(event)
        if not apply:
            continue
        code, resp = request(base, headers=h, method='POST',
                             body={'eventName': event, 'countingMethod': 'ONCE_PER_SESSION'})
        mark = 'ok' if code in (200, 201) else f'ОШИБКА {code} {resp.get("error", "")[:200]}'
        print(f'  + {event} — {mark}')
    return created


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true', help='завести недостающие цели')
    args = ap.parse_args()

    goals = load_goals()
    key = [n for n, s in goals.items() if s['key']]
    print(f'Реестр: {len(goals)} целей, из них конверсий {len(key)}: {", ".join(key)}')
    print(f'Режим: {"перенос" if args.apply else "сухой прогон"}\n')

    m = metrika_sync(goals, args.apply)
    print()
    g = ga4_sync(goals, args.apply)

    def verdict(missing: list[str] | None) -> str:
        if missing is None:
            return 'не проверено — нет доступа'
        if not missing:
            return 'всё заведено'
        return f'не хватает {len(missing)}: ' + ', '.join(missing)

    print('\nИтог:')
    print(f'  Метрика — {verdict(m)}')
    print(f'  GA4     — {verdict(g)}')
    if not args.apply and (m or g):
        print('\nСухой прогон: ничего не изменено. Запуск с --apply заведёт перечисленное.')
    # Нет доступа — не успех: молчаливый ноль здесь стоил бы месяца конверсий.
    return 1 if (m is None or g is None) else 0


if __name__ == '__main__':
    sys.exit(main())
