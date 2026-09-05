"""Мораторий по факту правки страницы, а не по авторству поручения.

Зачем модуль появился (разбор отчёта 04.09.2026). Мораторий в `lifecycle`
снимает страницу с поручений только тогда, когда контур сам её предложил, а
потом увидел на ней свои фразы. Вся работа, сделанная мимо контура — по
тикету CONTENT-003, по решению руководителя, по плану базового SEO-контура, —
для него невидима: в журнале ничего нет, значит страница «свободна».

Что из этого вышло. 03.09 опубликованы десять статей второй волны тиража, в
том числе про GitLab, Windsurf, Box и счёт от Atlassian. Наутро 04.09 пять
пакетов из девятнадцати указывали ровно на эти страницы и требовали дописать
в них текст. Формально верно — конкретных фраз там действительно не было; по
существу это поручение дорабатывать статью, которую вчера написали и которую
поиск ещё даже не переобошёл.

Как чинится. Контур запоминает отпечаток проверенного текста каждой страницы,
по которой строит пакет. Изменился отпечаток — страница правилась, и она
выводится из очереди поручений на тот же срок наблюдения, что и после
собственной правки контура. Кто внёс правку, значения не имеет: измерению
мешает вторая правка в окне, а не её авторство.

**Правка шаблона исключением не становится.** Шаблон вендорской страницы
входит в проверяемый текст всех вендорских страниц сразу, и одна его правка
сдвинула бы отпечаток у всех сразу — очередь поручений опустела бы целиком.
Поэтому при массовом сдвиге отпечатков внутри одного типа страниц мораторий
не ставится: это правка шаблона, а не работа над конкретной страницей, и
отчёт говорит об этом прямо.

Первый прогон моратория не создаёт: отпечатков ещё нет, и «изменение»
относительно пустоты — это не правка, а начало наблюдения.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402
from experiments import journal as jr  # noqa: E402

STATE_PATH = os.path.join(paths.DATA_DIR, "experiments", "page-fingerprints.json")

# Доля страниц одного типа, сдвиг отпечатка у которых читается как правка
# шаблона, а не как работа над страницами.
TEMPLATE_SHARE = 0.5
# Меньше этого числа страниц одного типа — судить о шаблоне не по чему:
# три вендорские страницы из трёх могли и правда править по одной.
TEMPLATE_MIN_PAGES = 4

REASON_EDITED = "страница правилась вне контура"
REASON_TEMPLATE = "правка шаблона: страницы этого типа под мораторий не выводятся"


def fingerprint(text: str) -> str:
    """Отпечаток проверяемого текста страницы.

    Считается от того же нормализованного текста, который читает проверка
    вхождений: смысл моратория — «то, на что смотрит аудит, изменилось».
    Правка, которой аудит не видит (обложка статьи, вёрстка), отпечаток не
    двигает и поручений не блокирует — и это правильно.
    """
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:16]


def load(path: str | None = None) -> dict:
    path = path or STATE_PATH
    if not os.path.exists(path):
        return {"страницы": {}}
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "страницы" not in data:
        return {"страницы": {}}
    return data


def save(state: dict, date: str, path: str | None = None) -> str:
    path = path or STATE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "_смысл": ("отпечаток проверяемого текста каждой страницы, по которой "
                   "строился пакет работ; изменение отпечатка выводит страницу "
                   "из очереди поручений на срок наблюдения независимо от того, "
                   "кто внёс правку"),
        "обновлён": date,
        "всего": len(state.get("страницы") or {}),
        "страницы": state.get("страницы") or {},
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def _watch_days(config: dict | None) -> int:
    block = ((config or {}).get("эксперименты") or {})
    return int(block.get("окно_наблюдения_дней", 14))


def update(state: dict, pages: dict, date: str,
           config: dict | None = None) -> dict:
    """Сверяет отпечатки страниц с прошлым прогоном и ставит мораторий.

    `pages` — адрес страницы → PageContent. Возвращает отчёт о том, что
    изменилось: списки страниц под новым мораторием и типов, у которых сдвиг
    признан правкой шаблона.
    """
    days = _watch_days(config)
    known = state.setdefault("страницы", {})

    changed: dict[str, str] = {}      # url → тип страницы
    seen_by_kind: dict[str, int] = {}
    for url, page in pages.items():
        if not page.available:
            continue
        seen_by_kind[page.kind] = seen_by_kind.get(page.kind, 0) + 1
        current = fingerprint(page.haystack)
        entry = known.get(url)
        if entry is None:
            known[url] = {"отпечаток": current, "проверено": date}
            continue
        if entry.get("отпечаток") != current:
            changed[url] = page.kind
        entry["отпечаток"] = current
        entry["проверено"] = date

    # Типы, где сдвинулось слишком много страниц сразу, — это шаблон.
    template_kinds = {
        kind for kind, total in seen_by_kind.items()
        if total >= TEMPLATE_MIN_PAGES
        and sum(1 for k in changed.values() if k == kind) >= TEMPLATE_SHARE * total
    }

    frozen_now = []
    for url, kind in changed.items():
        entry = known[url]
        if kind in template_kinds:
            entry["последняя_правка"] = date
            entry["примечание"] = REASON_TEMPLATE
            continue
        entry["последняя_правка"] = date
        entry["мораторий_до"] = jr.add_days(date, days)
        entry["причина"] = REASON_EDITED
        entry.pop("примечание", None)
        frozen_now.append(url)

    return {
        "изменились": sorted(changed),
        "под_мораторием_с_сегодня": sorted(frozen_now),
        "правка_шаблона": sorted(template_kinds),
        "окно_наблюдения_дней": days,
    }


def frozen(state: dict, date: str) -> dict[str, dict]:
    """Страницы, по которым мораторий ещё не истёк: адрес → запись."""
    result = {}
    for url, entry in (state.get("страницы") or {}).items():
        until = entry.get("мораторий_до")
        if until and until > date:
            result[url] = entry
    return result
