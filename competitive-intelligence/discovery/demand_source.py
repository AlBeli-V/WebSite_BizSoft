"""Частотность запросов из базы Wordstat базового контура — read-only.

Базовый контур ведёт семантическую вселенную (23 тыс. фраз с частотностью,
ветка `seo-data`). Правило независимости контуров запрещает покупать те же
данные повторно, поэтому конкурентная разведка читает их как есть.

Частотность нужна Opportunity для слагаемых «спрос» и «прокси выручки».
Отсутствие фразы в базе — это NO DATA, а не нулевой спрос: незнание и
отсутствие спроса — разные вещи, и Opportunity трактует их по-разному.
"""
from __future__ import annotations

import json
import subprocess
from functools import lru_cache

SEO_BRANCH = "seo-data"
UNIVERSE_PATH = "reports/seo/wordstat/semantic-universe.jsonl"
WEBMASTER_GLOB = "reports/seo/data"


def _normalize(phrase: str) -> str:
    """Сравнимая форма фразы: регистр и лишние пробелы не должны мешать."""
    return " ".join((phrase or "").lower().split())


@lru_cache(maxsize=1)
def load_frequencies(branch: str = SEO_BRANCH) -> dict[str, int]:
    """Словарь «фраза → частотность». Читается один раз за прогон."""
    try:
        blob = subprocess.run(
            ["git", "show", f"origin/{branch}:{UNIVERSE_PATH}"],
            capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return {}

    freq: dict[str, int] = {}
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        value = record.get("wordstat_frequency")
        if value is None:
            continue
        for key in (record.get("phrase"), record.get("normalized_phrase")):
            if key:
                normalized = _normalize(key)
                # Одна и та же фраза может прийти из разных источников;
                # берём максимум, чтобы не занижать спрос случайной записью.
                freq[normalized] = max(freq.get(normalized, 0), int(value))
    return freq


def frequency(phrase: str, table: dict[str, int] | None = None) -> int | None:
    """Частотность фразы или None, если её нет в базе (NO DATA, не ноль)."""
    table = load_frequencies() if table is None else table
    return table.get(_normalize(phrase))


@lru_cache(maxsize=1)
def load_impressions(branch: str = SEO_BRANCH) -> dict[str, int]:
    """Показы запросов из Яндекс.Вебмастера — запасная мера спроса.

    Частотность Wordstat покрывает лишь часть ядра (ядро SERP-мониторинга
    строится в том числе из запросов Вебмастера, которых в базе Wordstat
    нет). Показы отвечают на другой вопрос — сколько раз нас уже показали, —
    но как мера объёма спроса годятся и покрывают заметно больше запросов.
    Источник всегда помечается, чтобы две разные величины не смешивались
    молча.
    """
    try:
        listing = subprocess.run(
            ["git", "ls-tree", "--full-tree", "--name-only",
             f"origin/{branch}", f"{WEBMASTER_GLOB}/"],
            capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return {}
    files = sorted(p for p in listing.splitlines()
                   if p.rsplit("/", 1)[-1].startswith("yandex-"))
    if not files:
        return {}
    try:
        blob = subprocess.run(["git", "show", f"origin/{branch}:{files[-1]}"],
                              capture_output=True, text=True, check=True).stdout
        data = json.loads(blob)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {}

    result: dict[str, int] = {}
    for item in ((data.get("popular_queries") or {}).get("queries") or []):
        phrase = item.get("query_text")
        shows = (item.get("indicators") or {}).get("TOTAL_SHOWS")
        if phrase and shows is not None:
            result[_normalize(phrase)] = int(shows)
    return result


def demand(phrase: str) -> tuple[int | None, str]:
    """Спрос по фразе и источник: wordstat | webmaster | none.

    Порядок важен: частотность Wordstat описывает весь рынок, показы
    Вебмастера — только ту его часть, где нас уже видно. Первое ценнее,
    поэтому проверяется первым.
    """
    value = frequency(phrase)
    if value is not None:
        return value, "wordstat"
    value = load_impressions().get(_normalize(phrase))
    if value is not None:
        return value, "webmaster"
    return None, "none"
