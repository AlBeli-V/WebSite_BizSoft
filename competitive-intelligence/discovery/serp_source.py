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
SERP_DIR = "reports/seo/data/serp"


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


def available_dates(branch: str = SEO_BRANCH) -> list[str]:
    """Даты, за которые в хранилище базового контура есть срезы."""
    try:
        listing = _git("ls-tree", "--name-only", f"origin/{branch}", f"{SERP_DIR}/")
    except subprocess.CalledProcessError:
        return []
    dates = []
    for path in listing.splitlines():
        name = path.rsplit("/", 1)[-1]
        if name.endswith("-serp.jsonl"):
            dates.append(name[: -len("-serp.jsonl")])
    return sorted(dates)


def read_snapshot(date: str, branch: str = SEO_BRANCH) -> list[SerpRow]:
    """Срез за дату. Строки с ошибкой сохраняются — их считает Data Coverage."""
    path = f"{SERP_DIR}/{date}-serp.jsonl"
    try:
        blob = _git("show", f"origin/{branch}:{path}")
    except subprocess.CalledProcessError:
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
            found=raw.get("found"),
            top=raw.get("top") or [],
            error=raw.get("error"),
        ))
    return rows


def normalize_domain(domain: str) -> str:
    """Домен в сравнимом виде: без www и в нижнем регистре."""
    return (domain or "").strip().lower().removeprefix("www.")
