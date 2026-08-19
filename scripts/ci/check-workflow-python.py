#!/usr/bin/env python3
"""Проверка встроенных python-скриптов в ops-воркфлоу.

Ошибка синтаксиса внутри heredoc обнаруживается только при запуске на
сервере — это дорого. Скрипт вырезает блоки python3 - <<PYEOF ... PYEOF
из .github/workflows/*.yml и компилирует их локально.

    python3 scripts/ci/check-workflow-python.py
"""
import glob
import py_compile
import re
import sys
import tempfile
import os

BLOCK = re.compile(r"python3 - <<'PYEOF'\n(.*?)\n\s*PYEOF", re.S)

def dedent_block(text):
    lines = text.split('\n')
    indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
    pad = min(indents) if indents else 0
    return '\n'.join(l[pad:] if len(l) >= pad else l for l in lines)

def main():
    bad = 0
    checked = 0
    for path in sorted(glob.glob('.github/workflows/*.yml')):
        for i, m in enumerate(BLOCK.finditer(open(path, encoding='utf-8').read()), 1):
            checked += 1
            tmp = tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8')
            tmp.write(dedent_block(m.group(1)))
            tmp.close()
            try:
                py_compile.compile(tmp.name, doraise=True)
            except py_compile.PyCompileError as e:
                bad += 1
                print(f'{path} (блок {i}): {e.msg.strip()}')
            finally:
                os.unlink(tmp.name)
    print(f'проверено блоков: {checked}, с ошибками: {bad}')
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())
