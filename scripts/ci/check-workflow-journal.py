#!/usr/bin/env python3
"""Сторож: локальный action journal-post требует checkout в том же job.

03.09.2026 запись в журнал операций перестала проходить у 31 воркфлоу
одновременно: аудит #352 заменил ~60 копий шага «Post to issue» на общий
локальный action `./.github/actions/journal-post`, но локальный action —
это файлы репозитория, и без `actions/checkout` в том же job раннер его не
находит:

    Can't find 'action.yml' ... under '.github/actions/journal-post'.
    Did you forget to run actions/checkout before running your local action?

Отказ тихий по последствиям: основная работа воркфлоу выполняется (курс
обновлён, переобход заказан, замер снят), падает только запись результата —
и журнал слепнет ровно там, где им пользуются.

Проверяется два условия:
  1. checkout есть и стоит ВЫШЕ шага журнала;
  2. у checkout есть `if: always()`, если он идёт после основного шага.
     Шаг журнала объявлен `if: always()` намеренно — он обязан отработать и
     при падении основной работы. Шаг без этого условия в упавшем job
     пропускается, и checkout снова не случится.

    python3 scripts/ci/check-workflow-journal.py
"""
import pathlib
import re
import sys

ACTION = "./.github/actions/journal-post"
WORKFLOWS = pathlib.Path(".github/workflows")


def step_start(lines: list[str], i: int) -> int:
    """Индекс первой строки шага, внутри которого находится строка i."""
    return next(j for j in range(i, -1, -1) if re.match(r"^\s*- (name|uses):", lines[j]))


def is_first_step(lines: list[str], step_index: int) -> bool:
    """Шаг открывает список steps: — тогда он отработает при любом исходе job.

    Выше него могут стоять только комментарии и сама строка `steps:`.
    """
    for j in range(step_index - 1, -1, -1):
        s = lines[j].strip()
        if not s or s.startswith("#"):
            continue
        return s == "steps:"
    return False


def check(path: pathlib.Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    journal = [i for i, l in enumerate(lines) if ACTION in l]
    if not journal:
        return []
    checkouts = [i for i, l in enumerate(lines) if "actions/checkout@" in l]
    problems = []
    for ji in journal:
        before = [ci for ci in checkouts if ci < ji]
        if not before:
            problems.append(f"строка {ji + 1}: journal-post без actions/checkout выше — "
                            "локальный action не найдётся на раннере")
            continue
        ci = before[-1]
        # Шаг журнала объявлен always()? Тогда и checkout обязан быть always(),
        # иначе он пропускается ровно в тех прогонах, ради которых журнал и нужен.
        js, cs = step_start(lines, ji), step_start(lines, ci)
        journal_always = any("if: always()" in l for l in lines[js:ji + 1])
        checkout_always = any("if: always()" in l for l in lines[cs:ci + 1])
        if journal_always and not checkout_always and not is_first_step(lines, cs):
            problems.append(f"строка {ci + 1}: checkout без `if: always()` перед "
                            "журналом always() — при падении шага он пропустится")
    return problems


def main() -> int:
    files = sorted(WORKFLOWS.glob("*.yml"))
    with_journal = [f for f in files if ACTION in f.read_text(encoding="utf-8")]
    bad = 0
    for f in with_journal:
        for p in check(f):
            print(f"{f.name}: {p}")
            bad += 1
    print(f"воркфлоу с журналом: {len(with_journal)}, замечаний: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
