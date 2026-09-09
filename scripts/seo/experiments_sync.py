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

# Поля, без которых запись в реестре бесполезна: по ним считаются занятость
# кластера, экспозиция и вердикт.
REQUIRED = ("id", "status", "pages")


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pending", type=pathlib.Path, default=PENDING)
    ap.add_argument("--registry", type=pathlib.Path, default=REGISTRY)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pending = load_pending(args.pending)
    if not pending:
        print("входящих записей нет")
        return 0
    if not args.registry.exists():
        # Без реестра переносить некуда: скорее всего не сделан data_sync pull,
        # и создавать реестр с нуля здесь нельзя — это стёрло бы хранилище.
        print(f"::error::реестра нет по пути {args.registry}; сделан ли data_sync.sh pull?")
        return 1

    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    result = merge(registry, pending)

    for name, rid, why in result["broken"]:
        print(f"::error::{name}: запись {rid} не перенесена — {why}")
    for name, rid in result["skipped"]:
        print(f"уже в реестре, пропуск: {rid} ({name})")
    for name, rid in result["added"]:
        print(f"перенесено в реестр: {rid} ({name})")

    if result["added"] and not args.dry_run:
        args.registry.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"реестр обновлён: {len(result['added'])} записей, "
              f"всего {len(registry['experiments'])}")
    elif not result["added"]:
        print("новых записей нет — реестр не тронут")

    return 1 if result["broken"] else 0


if __name__ == "__main__":
    sys.exit(main())
