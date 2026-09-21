#!/usr/bin/env python3
"""Очередь замера позиций: фразы, по которым мы не знаем, где стоим.

Зачем. Правило «рекламируем только то, где нас нет в первой тройке»
применялось к одному проценту коммерческого спроса: позиции известны лишь
по контрольному ядру среза и запросам Вебмастера, а база спроса — почти
25 000 фраз. Остальные проходили отбор как «органики нет», хотя это
означало всего лишь «мы не смотрели». Платить за собственный трафик
по незнанию — ровно то, чего велено избегать.

Что в очереди. Только фразы, которые имеет смысл рекламировать:
коммерческий интент, спрос не ниже порога и привязка к каталогу
(`catalog_match`) — карточка товара или бренд, чью линейку мы продаём.
Замерять позиции по «google pixel купить» незачем: продать нечего.

Как разбирается. Ночным прогоном seo-serp-watch, партиями по остатку
бюджета: отложенный ночной тариф — 25,41 ₽ за 1000 запросов против ~488 ₽
у синхронного, поэтому очередь ждёт ночи, а не идёт днём.

Запуск: python3 scripts/seo/serp_queue.py build|show [--min-frequency N]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "wordstat"))

import catalog_match  # noqa: E402

UNIVERSE = pathlib.Path("reports/seo/wordstat/semantic-universe.jsonl")
SERP_DIR = pathlib.Path("reports/seo/serp")
QUEUE = SERP_DIR / "position-queue.json"
WEBMASTER_DIR = pathlib.Path("reports/seo/data")
OUR_DOMAIN = "biz-soft"
MIN_FREQUENCY = 30


def load_queue(path: pathlib.Path = QUEUE) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"pending": [], "done": {}}


def save_queue(data: dict, path: pathlib.Path = QUEUE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def measured_phrases(serp_dir: pathlib.Path = SERP_DIR,
                     wm_dir: pathlib.Path = WEBMASTER_DIR) -> set[str]:
    """Фразы, по которым позиция уже известна — из всех срезов и Вебмастера.

    Берётся весь архив срезов, а не последний файл: замер месячной давности
    отвечает на вопрос «стоим ли мы там» не хуже вчерашнего, а повторять
    его — значит платить дважды.
    """
    out: set[str] = set()
    for path in sorted(serp_dir.glob("*-serp.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("query"):
                out.add(row["query"].strip().lower())
    for path in sorted(wm_dir.glob("yandex-2026-*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for q in ((data.get("popular_queries") or {}).get("queries") or []):
            if q.get("query_text"):
                out.add(q["query_text"].strip().lower())
    return out


def build(min_frequency: int = MIN_FREQUENCY,
          universe: pathlib.Path = UNIVERSE,
          catalog: catalog_match.Catalog | None = None,
          measured: set[str] | None = None,
          queue_path: pathlib.Path = QUEUE) -> dict:
    """Пересобрать очередь. Уже замеренное и уже пройденное в неё не попадает."""
    if not universe.exists():
        raise SystemExit(f"нет базы семантики {universe} — сначала data_sync.sh pull")
    cat = catalog or catalog_match.Catalog()
    known = measured if measured is not None else measured_phrases()
    data = load_queue(queue_path)
    done = data.get("done") or {}

    pending, skipped = [], {"не коммерческая": 0, "спрос ниже порога": 0,
                            "уже замерено": 0, "продавать нечего": 0}
    for line in universe.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        phrase = (row.get("phrase") or "").strip()
        low = phrase.lower()
        if not phrase:
            continue
        if (row.get("commercial_intent_score") or 0) < 0.5:
            skipped["не коммерческая"] += 1
            continue
        if (row.get("wordstat_frequency") or 0) < min_frequency:
            skipped["спрос ниже порога"] += 1
            continue
        if low in known or low in done:
            skipped["уже замерено"] += 1
            continue
        m = cat.match(phrase)
        if m["kind"] == "none":
            skipped["продавать нечего"] += 1
            continue
        pending.append({"phrase": phrase,
                        "frequency": row.get("wordstat_frequency") or 0,
                        "kind": m["kind"], "url": m.get("url"),
                        "vendor": m.get("vendor")})
    pending.sort(key=lambda r: -r["frequency"])
    data.update({"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "min_frequency": min_frequency,
                 "pending": pending, "done": done, "skipped": skipped})
    save_queue(data, queue_path)
    return data


def take(limit: int, queue_path: pathlib.Path = QUEUE) -> list[str]:
    """Следующая партия фраз — самые частотные из неразобранных."""
    if limit <= 0:
        return []
    return [r["phrase"] for r in (load_queue(queue_path).get("pending") or [])[:limit]]


def mark_done(phrases: list[str], date_s: str, queue_path: pathlib.Path = QUEUE) -> int:
    """Убрать из очереди то, что реально замерено в этот день."""
    data = load_queue(queue_path)
    hit = {p.strip().lower() for p in phrases}
    done = data.get("done") or {}
    kept = []
    moved = 0
    for row in data.get("pending") or []:
        if row["phrase"].strip().lower() in hit:
            done[row["phrase"].strip().lower()] = date_s
            moved += 1
        else:
            kept.append(row)
    data["pending"], data["done"] = kept, done
    save_queue(data, queue_path)
    return moved


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=("build", "show"))
    ap.add_argument("--min-frequency", type=int, default=MIN_FREQUENCY)
    args = ap.parse_args()
    data = build(args.min_frequency) if args.command == "build" else load_queue()
    pending = data.get("pending") or []
    print(f"в очереди на замер: {len(pending)} фраз; разобрано ранее: {len(data.get('done') or {})}")
    if data.get("skipped"):
        for why, n in sorted(data["skipped"].items(), key=lambda kv: -kv[1]):
            print(f"  {n:6} — {why}")
    print(f"суммарный спрос очереди: {sum(r['frequency'] for r in pending)} в месяц")
    for row in pending[:15]:
        print(f"  {row['frequency']:7}  {row['phrase']:45} → {row['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
