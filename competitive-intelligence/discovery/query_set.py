"""Версия мониторингового ядра: из каких запросов состоит поле измерения.

Зачем это существует (правка 1.3.0 по четвёртой внешней рецензии). B2B Share
— доля внутри поля, а поле задаётся списком запросов. Добавили в ядро десять
запросов, где нас нет, — наша доля упала, хотя в выдаче ничего не
изменилось. Убрали запросы, где нас нет, — доля выросла. Динамика,
посчитанная через границу такого изменения, описывает не конкурентную
обстановку, а редактирование собственного списка.

Поэтому каждый снимок фиксирует:

  * `хеш` — отпечаток состава ядра (sha256 по нормализованному
    отсортированному списку, первые 12 hex-символов). Одинаковый хеш =
    буквально тот же набор запросов;
  * `версия` — человекочитаемый номер (v1, v2, …), присваиваемый по порядку
    появления состава в реестре `data/competitive/query-sets.json`;
  * сам список запросов — чтобы динамику можно было пересчитать по
    пересечению ядер задним числом, а не только «по совпадению хеша».

Реестр append-only: состав, встреченный однажды, номер не меняет.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402

HASH_LENGTH = 12


def normalize(query: str) -> str:
    """Сравнимая форма запроса: регистр и лишние пробелы не меняют состав."""
    return " ".join((query or "").lower().split())


def canonical(queries) -> list[str]:
    """Канонический состав ядра: уникальные нормализованные запросы по алфавиту."""
    return sorted({normalize(q) for q in queries if normalize(q)})


def fingerprint(queries) -> str:
    """Отпечаток состава ядра. Пустое ядро отпечатка не имеет."""
    core = canonical(queries)
    if not core:
        return ""
    digest = hashlib.sha256("\n".join(core).encode("utf-8")).hexdigest()
    return digest[:HASH_LENGTH]


def register(core_hash: str, count: int, date: str,
             path: str | None = None) -> str:
    """Номер версии состава. Новый состав получает следующий номер.

    Реестр только дополняется: пересчёт задним числом не должен переименовать
    уже разосланные отчёты.
    """
    if not core_hash:
        return ""
    path = path or paths.QUERY_SETS_PATH
    registry = {"версии": []}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            try:
                registry = json.load(fh)
            except json.JSONDecodeError:
                registry = {"версии": []}
    for entry in registry.get("версии", []):
        if entry.get("хеш") == core_hash:
            return entry.get("версия", "")
    version = f"v{len(registry.get('версии', [])) + 1}"
    registry.setdefault("версии", []).append({
        "версия": version,
        "хеш": core_hash,
        "запросов": count,
        "первый_день": date,
    })
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(registry, fh, ensure_ascii=False, indent=2)
    return version


def describe(queries, date: str, path: str | None = None) -> dict:
    """Блок «ядро_запросов» для снимка дня."""
    core = canonical(queries)
    core_hash = fingerprint(core)
    return {
        "версия": register(core_hash, len(core), date, path),
        "хеш": core_hash,
        "запросов": len(core),
        "запросы": core,
    }


def intersection(*cores) -> list[str]:
    """Пересечение составов ядер — то, что сравнимо между всеми днями."""
    sets = [set(canonical(core)) for core in cores if core]
    if not sets:
        return []
    common = set.intersection(*sets)
    return sorted(common)
