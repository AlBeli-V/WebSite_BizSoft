#!/usr/bin/env python3
"""Перенос заготовленных записей экспериментов в реестр ветки seo-data.

Реестр живёт в orphan-ветке seo-data, а сессия в неё не пишет (правило
prod-access). Раньше это означало ручной шаг: сессия оставляла запись в файле,
человек переносил её руками. Шаг, который делает человек и о котором помнит
только он, рано или поздно не делается — а цена ровно этого пропуска уже
измерена: партия snippets-10-expand выкачена в код 02.09.2026 без записи в
реестре, и шесть дней её нельзя было ни оценить, ни закрыть, а её десять
страниц для любой модели выглядели свободными.

Поэтому перенос стал шагом workflow. Сессия кладёт запись в
data/seo/experiments-pending/*.json (ветка main, обычный код-ревью), а
seo-site-check ежедневно вносит её в реестр — до активации, чтобы новый
эксперимент в тот же прогон получил дату старта и фиксированные окна.

Правило слияния одно: **запись с уже существующим id не трогается никогда.**
Реестр ведут и другие прогоны (activate проставляет старт, окна и вердикты),
и перезапись затёрла бы их работу. Входящая папка при этом не чистится: файл
остаётся, повторный прогон видит id в реестре и молча его пропускает.

Тем же порядком переносятся решения владельца по эксперименту. Записать
вердикт в журнал и закрыть запись в реестре сессия не может по той же
причине — журнал живёт в seo-data. Поэтому решение кладётся в
data/seo/decisions-pending/*.json, а прогон дописывает его в append-only
журнал experiment-decisions.jsonl и переводит запись реестра в closed.
Без этого шага остановленный эксперимент остаётся для всех моделей идущим:
его страницы считаются занятыми, а кластер — недоступным для новых проверок.

Запуск (шаг seo-site-check, после data_sync.sh pull):
    python3 scripts/seo/experiments_sync.py [--dry-run]
Возврат: 0 всегда, кроме поломки самих файлов. «Нечего переносить» — норма.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

PENDING = pathlib.Path("data/seo/experiments-pending")
REGISTRY = pathlib.Path("reports/seo/intelligence/seo-experiments.json")
DECISIONS_PENDING = pathlib.Path("data/seo/decisions-pending")
DECISIONS = pathlib.Path("reports/seo/intelligence/experiment-decisions.jsonl")

# Поля, без которых запись в реестре бесполезна: по ним считаются занятость
# кластера, экспозиция и вердикт.
REQUIRED = ("id", "status", "pages")

# Словарь решений и вердиктов — тот же, что у оценки (experiments.py).
# Своё слово здесь означало бы, что журнал и письма говорят разное.
VERDICTS = ("CONFIRMED", "REJECTED", "INCONCLUSIVE", "INSUFFICIENT_DATA")
DECISIONS_VOCAB = ("EXPAND", "REVERT", "KEEP", "EXTEND", "NEW_TEST", "CLOSE")
# Решения, после которых эксперимент больше не измеряется.
CLOSING = ("KEEP", "REVERT", "EXPAND", "CLOSE")
DECISION_REQUIRED = ("experiment_id", "date", "verdict", "owner_decision")


def load_pending(root: pathlib.Path) -> list[tuple[pathlib.Path, dict]]:
    out: list[tuple[pathlib.Path, dict]] = []
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for record in data.get("experiments") or []:
            out.append((path, record))
    return out


def validate(record: dict) -> list[str]:
    missing = [f for f in REQUIRED if not record.get(f)]
    problems = [f"нет обязательных полей: {', '.join(missing)}"] if missing else []
    # planned без start — норма: старт проставляет activate по факту выката.
    # А вот running без start нечем измерять: окна считаются от даты старта.
    if record.get("status") == "running" and not record.get("start"):
        problems.append("статус running без даты start — окна считать не от чего")
    return problems


def merge(registry: dict, pending: list[tuple[pathlib.Path, dict]]) -> dict:
    have = {e["id"] for e in registry.get("experiments", [])}
    added, skipped, broken = [], [], []
    for path, record in pending:
        rid = record.get("id", "(без id)")
        problems = validate(record)
        if problems:
            broken.append((path.name, rid, "; ".join(problems)))
            continue
        if rid in have:
            skipped.append((path.name, rid))
            continue
        registry.setdefault("experiments", []).append(record)
        have.add(rid)
        added.append((path.name, rid))
    return {"added": added, "skipped": skipped, "broken": broken}


def load_decisions(root: pathlib.Path) -> list[tuple[pathlib.Path, dict]]:
    out: list[tuple[pathlib.Path, dict]] = []
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for record in data.get("decisions") or []:
            out.append((path, record))
    return out


def validate_decision(record: dict) -> list[str]:
    missing = [f for f in DECISION_REQUIRED if not record.get(f)]
    problems = [f"нет обязательных полей: {', '.join(missing)}"] if missing else []
    if record.get("verdict") and record["verdict"] not in VERDICTS:
        problems.append(f"неизвестный вердикт {record['verdict']}")
    if record.get("owner_decision") and record["owner_decision"] not in DECISIONS_VOCAB:
        problems.append(f"неизвестное решение {record['owner_decision']}")
    return problems


def _same_decision(a: dict, b: dict) -> bool:
    """Одно и то же решение: эксперимент, дата и выбор владельца."""
    return all(a.get(k) == b.get(k) for k in ("experiment_id", "date", "owner_decision"))


def merge_decisions(registry: dict, journal: list[dict],
                    pending: list[tuple[pathlib.Path, dict]]) -> dict:
    """Дописать решения в журнал и закрыть записи реестра.

    Журнал append-only: повторный прогон видит то же решение и молчит.
    Решение по эксперименту, которого нет в реестре, не пишется вовсе —
    это расхождение кода и реестра, и оно должно быть видно, а не тихо
    осесть записью в журнале.
    """
    by_id = {e["id"]: e for e in registry.get("experiments", [])}
    appended, skipped, broken, closed = [], [], [], []
    for path, record in pending:
        rid = record.get("experiment_id", "(без id)")
        problems = validate_decision(record)
        if rid not in by_id:
            problems.append("эксперимента нет в реестре")
        if problems:
            broken.append((path.name, rid, "; ".join(problems)))
            continue
        if any(_same_decision(record, seen) for seen in journal):
            skipped.append((path.name, rid))
            continue
        journal.append(record)
        appended.append((path.name, rid))
        # После решения эксперимент перестаёт измеряться: пока статус
        # running, его страницы для любой модели заняты, а кластер закрыт
        # для новых проверок.
        if record["owner_decision"] in CLOSING and by_id[rid].get("status") != "closed":
            by_id[rid]["status"] = "closed"
            by_id[rid]["end"] = record["date"]
            by_id[rid]["closed_by"] = record["owner_decision"]
            closed.append((path.name, rid))
    return {"appended": appended, "skipped": skipped, "broken": broken, "closed": closed}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pending", type=pathlib.Path, default=PENDING)
    ap.add_argument("--registry", type=pathlib.Path, default=REGISTRY)
    ap.add_argument("--decisions-pending", type=pathlib.Path, default=DECISIONS_PENDING)
    ap.add_argument("--decisions", type=pathlib.Path, default=DECISIONS)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pending = load_pending(args.pending)
    decisions = load_decisions(args.decisions_pending)
    if not pending and not decisions:
        print("входящих записей нет")
        return 0
    if not args.registry.exists():
        # Без реестра переносить некуда: скорее всего не сделан data_sync pull,
        # и создавать реестр с нуля здесь нельзя — это стёрло бы хранилище.
        print(f"::error::реестра нет по пути {args.registry}; сделан ли data_sync.sh pull?")
        return 1

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    result = merge(registry, pending)

    journal: list[dict] = []
    if args.decisions.exists():
        journal = [json.loads(line) for line in
                   args.decisions.read_text(encoding="utf-8").splitlines() if line.strip()]
    before = len(journal)
    dres = merge_decisions(registry, journal, decisions)

    for name, rid, why in result["broken"]:
        print(f"::error::{name}: запись {rid} не перенесена — {why}")
    for name, rid in result["skipped"]:
        print(f"уже в реестре, пропуск: {rid} ({name})")
    for name, rid in result["added"]:
        print(f"перенесено в реестр: {rid} ({name})")

    for name, rid, why in dres["broken"]:
        print(f"::error::{name}: решение по {rid} не перенесено — {why}")
    for name, rid in dres["skipped"]:
        print(f"решение уже в журнале, пропуск: {rid} ({name})")
    for name, rid in dres["appended"]:
        print(f"решение записано: {rid} ({name})")
    for name, rid in dres["closed"]:
        print(f"эксперимент закрыт в реестре: {rid} ({name})")

    changed = bool(result["added"] or dres["closed"])
    if changed and not args.dry_run:
        args.registry.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"реестр обновлён: {len(result['added'])} записей, "
              f"{len(dres['closed'])} закрыто, всего {len(registry['experiments'])}")
    elif not changed:
        print("новых записей нет — реестр не тронут")

    if dres["appended"] and not args.dry_run:
        args.decisions.parent.mkdir(parents=True, exist_ok=True)
        # Журнал append-only: дописываем только новые строки, прежние не
        # переписываем — иначе один сбой записи потерял бы всю историю.
        with args.decisions.open("a", encoding="utf-8") as f:
            for record in journal[before:]:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"журнал решений дополнен: {len(dres['appended'])} записей")

    return 1 if (result["broken"] or dres["broken"]) else 0


if __name__ == "__main__":
    sys.exit(main())
