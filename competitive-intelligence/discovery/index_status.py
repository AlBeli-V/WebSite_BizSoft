"""Статус страницы в индексе Google — из выгрузки базового SEO-контура.

Зачем модуль появился (разбор 10.09.2026, второй заход). Разведка нашла
главный вопрос дня — 216 запросов, где Яндекс держит нас в топ-10, а в
Google-срезе нас нет, — и предложила проверить индексацию руками в Search
Console. Проверка руками была лишней: базовый контур снимает статус по всему
инвентарю sitemap ежедневно через URL Inspection API и кладёт его в
`reports/seo/data/index-google-<дата>.json` ветки seo-data.

Правило «один сбор — все потребители» действует и здесь: разведка читает
готовый файл и ничего не запрашивает у Google сама.

Что даёт статус, чего не даёт наблюдение за выдачей. Отсутствие страницы в
собранной выдаче — один факт с тремя разными причинами, и они требуют разной
работы:

  URL is unknown to Google        — Google не знает адреса вовсе: вопрос
                                    обхода и перелинковки, тексты ни при чём;
  Discovered - currently not indexed — адрес известен, в индекс не взят:
                                    вопрос ценности страницы и бюджета обхода;
  Submitted and indexed           — страница в индексе и просто проигрывает
                                    в ранжировании: вот это работа с
                                    содержимым и конкурентоспособностью.

Первый вывод разведки — «проверять надо видимость, а не качество» — верен для
первых двух групп и неверен для третьей. На срезе 09.09 из сорока страниц
разрыва их было 6, 21 и 13: треть требовала ровно той работы, от которой
вывод отговаривал.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401

SEO_BRANCH = "seo-data"
DATA_DIR = "reports/seo/data"
PREFIX = "index-google-"
SITE = "https://biz-soft.pro"

# Классы причин. Ключ — то, что отдаёт Search Console; значение — что с этим
# делать. Неизвестный статус не подменяется ближайшим: он так и называется.
UNKNOWN = "не знает адреса"
NOT_INDEXED = "знает, но не индексирует"
INDEXED = "в индексе, проигрывает в выдаче"
NO_DATA = "статуса нет"

_CLASSES = {
    "URL is unknown to Google": UNKNOWN,
    "Discovered - currently not indexed": NOT_INDEXED,
    "Crawled - currently not indexed": NOT_INDEXED,
    "Submitted and indexed": INDEXED,
    "Indexed, not submitted in sitemap": INDEXED,
}


def _path(url: str) -> str:
    """Путь без домена и без завершающего слеша — ключ выгрузки."""
    return (url or "").replace(SITE, "").rstrip("/") or "/"


@lru_cache(maxsize=1)
def load(branch: str = SEO_BRANCH) -> dict:
    """Свежая выгрузка статусов индексации целиком. Читается раз за прогон."""
    try:
        listing = subprocess.run(
            ["git", "ls-tree", "--full-tree", "--name-only",
             f"origin/{branch}", f"{DATA_DIR}/"],
            capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return {}
    files = sorted(p for p in listing.splitlines()
                   if p.rsplit("/", 1)[-1].startswith(PREFIX))
    if not files:
        return {}
    try:
        blob = subprocess.run(["git", "show", f"origin/{branch}:{files[-1]}"],
                              capture_output=True, text=True, check=True).stdout
        return json.loads(blob)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {}


def available(branch: str = SEO_BRANCH) -> bool:
    return bool((load(branch).get("pages") or {}))


def snapshot_date(branch: str = SEO_BRANCH) -> str:
    return load(branch).get("date") or ""


def state(url: str, branch: str = SEO_BRANCH) -> tuple[str, str]:
    """(класс причины, дословный статус Search Console) по адресу страницы."""
    page = (load(branch).get("pages") or {}).get(_path(url)) or {}
    raw = page.get("coverage_state") or ""
    if not raw:
        return NO_DATA, ""
    return _CLASSES.get(raw, NOT_INDEXED), raw


def crawled(url: str, branch: str = SEO_BRANCH) -> bool:
    """Скачивал ли Google эту страницу хоть раз.

    Отличает очередь от приговора. «Discovered - currently not indexed» в
    общем случае может значить и «посмотрел и не взял», и «знаю адрес, руки
    не дошли». Для biz-soft.pro это второе: на срезе 09.09 из 363 страниц
    такого статуса Google скачал ровно одну. Разница определяет работу —
    страницу, которую не скачивали, бесполезно переписывать.
    """
    page = (load(branch).get("pages") or {}).get(_path(url)) or {}
    return bool(page.get("last_crawl"))


def crawl_summary(branch: str = SEO_BRANCH) -> dict:
    """Сколько страниц сайта Google скачивал и когда в последний раз."""
    pages = load(branch).get("pages") or {}
    даты = [v.get("last_crawl") for v in pages.values() if (v or {}).get("last_crawl")]
    return {"страниц": len(pages), "скачано": len(даты),
            "не скачано": len(pages) - len(даты),
            "последний_обход": max(даты)[:10] if даты else ""}
