"""Чтение SERP-срезов Яндекса из ветки-хранилища базового контура — read-only.

Базовый SEO-контур с 30.08 ежедневно снимает выдачу Яндекса по коммерческому
ядру (`seo-serp-watch` → ветка `seo-data`). Правило независимости контуров
(раздел 2 задания) требует не покупать эти же снимки повторно: конкурентная
разведка читает их как есть и докупает только то, чего там нет.

Отсюда единственный способ доступа — `git show origin/seo-data:<путь>`.
Ничего не пишем, ветку не трогаем, рабочую копию не меняем.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field

SEO_BRANCH = "seo-data"
# Каталоги срезов в порядке приоритета. Базовый контур перенёс срезы из
# reports/seo/data/serp в reports/seo/serp 01.09.2026; читать надо оба, иначе
# в день миграции конкурентная разведка молча теряет источник — ровно это и
# произошло: прогон 01.09 не нашёл ни одного среза и не отправил письмо.
# Оставлять только новый путь нельзя: в старом лежит история за 30–31.08,
# без которой рвётся ряд наблюдений.
SERP_DIRS = ("reports/seo/serp", "reports/seo/data/serp")
SERP_DIR = SERP_DIRS[0]
# Суффикс файла среза по поисковой системе. Google-срез (xmlriver, с
# 03.09.2026) лежит рядом с Яндексом под своим суффиксом, чтобы прежние
# читатели не приняли его за Яндекс.
SNAPSHOT_SUFFIX = {"yandex": "-serp.jsonl", "google": "-serp-google.jsonl"}


@dataclass
class SerpRow:
    """Одна строка среза: выдача по запросу в одном регионе."""
    date: str
    query: str
    region: str
    engine: str = "yandex"
    found: int | None = None
    top: list[dict] = field(default_factory=list)
    error: str | None = None

    @property
    def has_data(self) -> bool:
        """Строка с ошибкой источника — это NO DATA, а не пустая выдача."""
        return self.error is None and bool(self.top)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          check=True).stdout


def available_dates(branch: str = SEO_BRANCH,
                    engine: str = "yandex") -> list[str]:
    """Даты, за которые в хранилище базового контура есть срезы.

    Объединение по всем известным каталогам: после переноса часть истории
    осталась в старом месте, и ряд наблюдений не должен от этого прерваться.
    """
    suffix = SNAPSHOT_SUFFIX[engine]
    dates: set[str] = set()
    for directory in SERP_DIRS:
        try:
            # --full-tree: пути отсчитываются от корня дерева, а не от
            # текущего каталога. Без него прогон, запущенный не из корня
            # репозитория, молча не находит ни одного среза.
            listing = _git("ls-tree", "--full-tree", "--name-only",
                           f"origin/{branch}", f"{directory}/")
        except subprocess.CalledProcessError:
            continue
        for path in listing.splitlines():
            name = path.rsplit("/", 1)[-1]
            # Точная длина даты: у Google суффикс длиннее, и «-serp.jsonl»
            # на конце имени Яндекса не должен ловить чужие файлы.
            if name.endswith(suffix) and len(name) == 10 + len(suffix):
                dates.add(name[: -len(suffix)])
    return sorted(dates)


def read_snapshot(date: str, branch: str = SEO_BRANCH,
                  engine: str = "yandex") -> list[SerpRow]:
    """Срез за дату. Строки с ошибкой сохраняются — их считает Data Coverage."""
    suffix = SNAPSHOT_SUFFIX[engine]
    blob = None
    for directory in SERP_DIRS:
        try:
            blob = _git("show", f"origin/{branch}:{directory}/{date}{suffix}")
            break
        except subprocess.CalledProcessError:
            continue
    if blob is None:
        return []
    rows = []
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append(SerpRow(
            date=raw.get("date", date),
            query=raw.get("query", ""),
            region=str(raw.get("region", "")),
            engine=raw.get("engine") or engine,
            found=raw.get("found"),
            top=raw.get("top") or [],
            error=raw.get("error"),
        ))
    return rows


def normalize_domain(domain: str) -> str:
    """Домен в сравнимом виде: без www и в нижнем регистре."""
    return (domain or "").strip().lower().removeprefix("www.")
