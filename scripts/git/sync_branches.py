#!/usr/bin/env python3
"""Выравнивание веток по main: слияние, отчёт, уборка влитых.

Ветки расходятся с main молча, и цена расхождения растёт незаметно. Сегодня
это стоило двух ошибок за день: исследование считало рекомендации по списку
вендоров недельной давности и предлагало завести то, что уже стоит на сайте,
а слияние отставшей ветки чуть не снесло 53 тысячи строк чужой работы.

Механика намеренно односторонняя: main вливается в ветки, но не наоборот.
Автоматически отправлять работу из веток в main нельзя — туда попадёт
непроверенное; а вот держать ветки на свежем основании безопасно и как раз
предотвращает конфликты, пока они маленькие.

Ветка считается влитой, когда её содержимое не отличается от main, — сравнением
деревьев, а не счётом коммитов. При squash-мерже в ветке остаётся «свой»
коммит, которого нет в main по хешу, хотя все его изменения там уже есть;
по счёту коммитов такая ветка выглядит живой вечно.

Режимы: по умолчанию сухой прогон, --apply выполняет.
"""
from __future__ import annotations

import argparse
import subprocess
import time
import sys

PREFIX = "claude/"
MAIN = "origin/main"


def git(*args: str, check: bool = True) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def branches() -> list[str]:
    out = git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin")
    names = []
    for line in out.splitlines():
        name = line.strip().removeprefix("origin/")
        if name and name != "main" and "HEAD" not in name and name.startswith(PREFIX):
            names.append(name)
    return sorted(names)


def counts(branch: str) -> tuple[int, int]:
    behind = int(git("rev-list", "--count", f"origin/{branch}..{MAIN}"))
    ahead = int(git("rev-list", "--count", f"{MAIN}..origin/{branch}"))
    return behind, ahead


def has_own_changes(branch: str) -> bool:
    """Есть ли в ветке работа, которой нет в main.

    Ни один diff на этот вопрос не отвечает. Двухточечный сравнивает вершины
    и показывает в том числе то, чем main ушёл вперёд: отставшая ветка
    выглядит так, будто откатывает чужую работу. Трёхточечный показывает
    изменения ветки от общего предка — но при squash-мерже они там и есть,
    просто те же изменения уже лежат в main отдельным коммитом.

    git cherry сравнивает коммиты по содержанию патча, а не по хешу: строки
    с «-» — то, что в main уже есть в другом виде, с «+» — настоящая работа.
    Только это отличает живую ветку от следа squash-мержа, который иначе
    висел бы в списке годами.
    """
    out = git("cherry", MAIN, f"origin/{branch}", check=False)
    return any(line.startswith("+") for line in out.splitlines())


def days_idle(branch: str) -> int:
    """Сколько дней в ветке ничего не происходило.

    От текущего момента, а не от даты последнего коммита main: main может
    отставать сам, и тогда свежая ветка выглядела бы заброшенной.
    """
    ts = int(git("log", "-1", "--format=%ct", f"origin/{branch}"))
    return max(0, (int(time.time()) - ts) // 86400)


def try_merge(branch: str, apply: bool) -> tuple[str, str]:
    """('merged'|'clean'|'conflict'|'error', подробности)."""
    try:
        git("checkout", "-B", f"sync/{branch}", f"origin/{branch}")
    except RuntimeError as e:
        return "error", str(e)[:200]

    r = subprocess.run(["git", "merge", "--no-edit", MAIN], capture_output=True, text=True)
    if r.returncode != 0:
        files = git("diff", "--name-only", "--diff-filter=U", check=False)
        git("merge", "--abort", check=False)
        return "conflict", files.replace("\n", ", ")[:300]

    if "Already up to date" in r.stdout:
        return "clean", ""
    if not apply:
        return "merged", "сухой прогон — не отправлено"
    # Отправляем только то, что собирается. Слияние без конфликтов — ещё не
    # рабочее состояние: git не знает, что переименованная функция вызывается
    # из файла, которого он не трогал. Отправить сломанную ветку хуже, чем
    # оставить отставшую: отставание видно в отчёте, поломка — нет.
    ok, why = verify()
    if not ok:
        return "broken", why
    try:
        git("push", "origin", f"HEAD:refs/heads/{branch}")
    except RuntimeError as e:
        return "error", str(e)[:200]
    return "merged", "проверено и отправлено"


def verify() -> tuple[bool, str]:
    """Проверка собранного состояния: типы и тесты."""
    for name, cmd in (("проверка типов", ["pnpm", "check"]),
                      ("тесты", ["pnpm", "test"])):
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            tail = (r.stdout + r.stderr).strip().splitlines()[-4:]
            return False, f"{name} не прошла: " + " | ".join(t.strip() for t in tail)
    return True, "" 


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="выполнить, а не только показать")
    ap.add_argument("--delete-merged", action="store_true",
                    help="удалять ветки, содержимое которых уже в main")
    ap.add_argument("--idle-days", type=int, default=1,
                    help="не трогать ветки, обновлявшиеся позже этого срока")
    args = ap.parse_args()

    git("fetch", "origin", "--prune", "--quiet")
    start = git("rev-parse", "--abbrev-ref", "HEAD")

    merged, updated, conflicts, errors, skipped, broken = [], [], [], [], [], []
    for b in branches():
        behind, ahead = counts(b)
        idle = days_idle(b)

        if not has_own_changes(b):
            merged.append((b, behind, ahead, idle))
            continue
        if behind == 0:
            skipped.append((b, "уже на свежем main"))
            continue
        if idle < args.idle_days:
            # Ветка в активной работе: вливать в неё main без ведома автора
            # значит переписать то, над чем он прямо сейчас работает.
            skipped.append((b, f"обновлялась {idle} дн. назад — не трогаем"))
            continue

        state, detail = try_merge(b, args.apply)
        if state == "conflict":
            conflicts.append((b, detail))
        elif state == "error":
            errors.append((b, detail))
        elif state == "broken":
            broken.append((b, detail))
        elif state == "merged":
            updated.append((b, behind, detail))
        else:
            skipped.append((b, "нечего вливать"))

    git("checkout", start, check=False)

    print(f"Веток с префиксом {PREFIX}: {len(branches())}")
    print(f"Режим: {'выполнение' if args.apply else 'сухой прогон'}\n")

    print(f"── Выровнено по main: {len(updated)}")
    for b, behind, detail in updated:
        print(f"   {b} (+{behind} коммитов main) — {detail}")

    print(f"\n── Содержимое уже в main: {len(merged)}")
    for b, behind, ahead, idle in merged:
        mark = ""
        if args.delete_merged and idle >= args.idle_days:
            if args.apply:
                try:
                    git("push", "origin", "--delete", b)
                    mark = " — удалена"
                except RuntimeError as e:
                    mark = f" — удалить не вышло: {str(e)[:80]}"
            else:
                mark = " — будет удалена"
        print(f"   {b} (отставала на {behind}, простой {idle} дн.){mark}")

    if broken:
        print(f"\n── Слились, но не собираются — не отправлено: {len(broken)}")
        for b, why in broken:
            print(f"   {b}: {why}")

    print(f"\n── Конфликты, нужен человек: {len(conflicts)}")
    for b, files in conflicts:
        print(f"   {b}: {files}")

    if errors:
        print(f"\n── Ошибки: {len(errors)}")
        for b, e in errors:
            print(f"   {b}: {e}")

    if skipped:
        print(f"\n── Пропущено: {len(skipped)}")
        for b, why in skipped:
            print(f"   {b}: {why}")

    # Конфликт — не поломка механизма, а работа для человека. Ненулевой код
    # возврата только на ошибках: иначе прогон будет краснеть каждый час и
    # на него перестанут смотреть.
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
