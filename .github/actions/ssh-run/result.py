#!/usr/bin/env python3
"""Разбор вывода шага ssh-run: маркер кода завершения → исход для журнала.

Читает окружение:
  SSH_OUTCOME — исход шага appleboy/ssh-action (success | failure | …);
  SSH_STDOUT  — захваченный вывод сеанса; последняя содержательная строка
                скрипта-обёртки — маркер `__OPS_RC=<код>`.

Пишет в GITHUB_OUTPUT: outcome, rc, stdout, body-file. Файл body-file лежит
в RUNNER_TEMP и содержит вывод без маркера и без баннера drone-ssh
«✅ Successfully executed commands to all hosts» — баннер печатается всегда,
потому что сеанс завершается нулём, и при сбое скрипта он врал бы.

Проверки — scripts/ops/tests/test_ssh_run_result.py.
"""
import os
import re
import secrets
import sys

MARKER = re.compile(r'^__OPS_RC=(\d+)\s*$')
BANNER = re.compile(r'^(=+|✅ Successfully executed commands to all hosts\.)\s*$')


def parse(ssh_outcome: str, stdout: str) -> dict:
    """Исход шага по маркеру и статусу сеанса.

    Возвращает outcome (success | failure), rc ('' без маркера), stdout —
    вывод скрипта без маркера и баннера, body — тот же вывод с пометкой о
    коде завершения или об обрыве сеанса.
    """
    rc = None
    lines = []
    for line in stdout.replace('\r\n', '\n').split('\n'):
        m = MARKER.match(line)
        if m:
            rc = int(m.group(1))
            continue
        if BANNER.match(line):
            continue
        lines.append(line)
    text = '\n'.join(lines).strip()

    if ssh_outcome != 'success' or rc is None:
        note = ('сеанс SSH завершился со статусом %s, до маркера кода завершения '
                'не дошёл: обрыв соединения, таймаут или отказ запуска скрипта'
                % (ssh_outcome or 'unknown'))
        body = (text + '\n\n' if text else '') + note
        return {'outcome': 'failure', 'rc': '' if rc is None else str(rc),
                'stdout': text, 'body': body}

    body = text if rc == 0 else (text + '\n\n' if text else '') + f'код завершения скрипта: {rc}'
    return {'outcome': 'success' if rc == 0 else 'failure', 'rc': str(rc),
            'stdout': text, 'body': body}


def emit(name: str, value: str) -> None:
    out = os.environ.get('GITHUB_OUTPUT')
    if not out:
        print(f'{name}={value}')
        return
    with open(out, 'a', encoding='utf-8') as f:
        if '\n' in value:
            delim = 'ghadelimiter_' + secrets.token_hex(8)
            f.write(f'{name}<<{delim}\n{value}\n{delim}\n')
        else:
            f.write(f'{name}={value}\n')


def main() -> int:
    res = parse(os.environ.get('SSH_OUTCOME', ''), os.environ.get('SSH_STDOUT', ''))
    tmp = os.environ.get('RUNNER_TEMP') or '/tmp'
    body_file = os.path.join(tmp, 'ssh-run-' + secrets.token_hex(6) + '.txt')
    with open(body_file, 'w', encoding='utf-8') as f:
        f.write(res['body'] + '\n')
    emit('outcome', res['outcome'])
    emit('rc', res['rc'])
    emit('stdout', res['stdout'])
    emit('body-file', body_file)
    print(res['body'])
    print(f"\nисход шага: {res['outcome']}" + (f" (код {res['rc']})" if res['rc'] else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
