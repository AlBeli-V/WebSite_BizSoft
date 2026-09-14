#!/usr/bin/env python3
"""Курсор сплошного переобхода карточек (контур seo-recrawl-sweep).

Состояние прогона — один файл в ветке seo-data:

    reports/seo/data/recrawl-sweep.json
    {"cursor": 300, "total": 520, "last_run": "2026-09-13", "runs": 2}

`read` отдаёт курсор шагу отправки и гасит прогон, если сегодня уже
отправляли: повторный запуск в те же сутки не должен тратить квоту второй
раз. `save` двигает курсор ровно на число принятых адресов — отклонённые
уйдут следующей ночью, а не потеряются.

Печатать в журнал здесь нечего: контур молчит при успехе
(docs/rules/report-integrity.md).
"""
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

MARKER = Path('reports/seo/data/recrawl-sweep.json')


def load() -> dict:
    if MARKER.exists():
        try:
            return json.loads(MARKER.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            # Битый маркер не должен останавливать контур: начинаем сначала,
            # переобход повторно — это потеря квоты, а не порча данных.
            print('маркер нечитаем — очередь начинается сначала')
    return {}


def emit(name: str, value: str) -> None:
    out = os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out, 'a', encoding='utf-8') as fh:
            fh.write(f'{name}={value}\n')


def cmd_read() -> None:
    state = {} if os.environ.get('P_RESET') == 'true' else load()
    cursor = int(state.get('cursor') or 0)
    total = int(state.get('total') or 0)
    today = date.today().isoformat()

    if os.environ.get('P_FORCE') != 'true' and state.get('last_run') == today:
        print(f'сегодня уже отправляли ({today}) — прогон пропущен')
        emit('skip', 'true')
        emit('cursor', str(cursor))
        return
    if total and cursor >= total:
        print(f'очередь пройдена целиком: {cursor} из {total}')
        emit('skip', 'true')
        emit('cursor', str(cursor))
        return

    print(f'курсор: {cursor}' + (f' из {total}' if total else ''))
    emit('skip', 'false')
    emit('cursor', str(cursor))


def cmd_save() -> None:
    stdout = os.environ.get('STDOUT', '')
    cur = re.search(r'SWEEP_CURSOR=(\d+)', stdout)
    tot = re.search(r'SWEEP_TOTAL=(\d+)', stdout)
    if not cur:
        # Шаг отправки упал до первой отправки — курсор не двигаем.
        print('в выводе прогона нет курсора — маркер оставлен без изменений')
        return
    state = load()
    state['cursor'] = int(cur.group(1))
    if tot:
        state['total'] = int(tot.group(1))
    state['last_run'] = date.today().isoformat()
    state['runs'] = int(state.get('runs') or 0) + 1
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(json.dumps(state, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    done, total = state['cursor'], state.get('total') or 0
    print(f'курсор: {done}' + (f' из {total}' if total else ''))
    if total and done >= total:
        print('очередь пройдена целиком')


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'read'
    if action == 'read':
        cmd_read()
    elif action == 'save':
        cmd_save()
    else:
        raise SystemExit(f'неизвестное действие: {action}')
