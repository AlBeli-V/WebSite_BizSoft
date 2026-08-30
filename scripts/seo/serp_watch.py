#!/usr/bin/env python3
"""SERP-watch: ежедневный архив выдачи Яндекса по ядру запросов.

Источник — Yandex Search API v2 (веб-поиск), тот же сервис и ключ, что у
Wordstat (`WORDSTAT_API_KEY`). Решение руководителя 30.08.2026: рабочий
сценарий, потолок 5 000 запросов в месяц; сбор — ночным слотом (скидка
ночного тарифа, 00:00–07:59 МСК).

Дисциплина — как у Wordstat:
  - ни один вызов без записи в журнал (serp/ledger/<месяц>.jsonl, append-only);
  - месячный потолок запросов зашит и проверяется до каждого вызова;
  - ядро запросов (watchlist) строится из данных, а не руками: money-радар,
    возможности Вордстата, кластеры активных экспериментов.

Запуск (workflow seo-serp-watch): python3 scripts/seo/serp_watch.py [дата]
Выход: reports/seo/data/serp/<дата>-serp.jsonl (строка на запрос: топ-20).
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import pathlib
import sys
import time
from zoneinfo import ZoneInfo

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from serp_probe import parse_serp  # noqa: E402

URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"
SERP_DIR = pathlib.Path("reports/seo/data/serp")
LEDGER_DIR = SERP_DIR / "ledger"

MONTHLY_CAP = 5000        # решение руководителя 30.08.2026
DAILY_CAP = 170           # 150 ядро + запас; держит месяц в потолке
REGION = "213"            # Москва; выдача Яндекса регионозависима
TOP_N = 20

MSK = ZoneInfo("Europe/Moscow")


def month_key(date: dt.date) -> str:
    return date.strftime("%Y-%m")


def ledger_path(date: dt.date) -> pathlib.Path:
    return LEDGER_DIR / f"{month_key(date)}.jsonl"


def month_spent(date: dt.date) -> int:
    p = ledger_path(date)
    if not p.exists():
        return 0
    return sum(1 for line in p.read_text(encoding="utf-8").splitlines()
               if line.strip())


def day_spent(date: dt.date) -> int:
    """Запросы, уже израсходованные СЕГОДНЯ (по журналу): дневной потолок
    обязан держать день, а не отдельный прогон — повторный запуск в тот же
    день не должен удваивать расход."""
    p = ledger_path(date)
    if not p.exists():
        return 0
    day = date.isoformat()
    n = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            if json.loads(line).get("at", "")[:10] == day:
                n += 1
        except ValueError:
            continue
    return n


def log_call(date: dt.date, query: str, status: str, found: int | None):
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             "query": query, "region": REGION, "status": status,
             "found": found}
    with ledger_path(date).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def fetch_serp(session, key: str, query: str) -> dict:
    """Один синхронный запрос веб-поиска → разобранный топ.

    Синхронный режим выбран сознательно: прогон идёт ночным слотом (ночной
    тариф), объём ≤170 запросов, а отложенный режим требует двухфазного
    забора с неопределённым сроком готовности — хрупкость дороже разницы
    в копейках.
    """
    body = {"query": {"searchType": "SEARCH_TYPE_RU", "queryText": query},
            "region": REGION}
    r = session.post(URL, json=body, timeout=60,
                     headers={"Authorization": f"Api-Key {key}",
                              "Content-Type": "application/json"})
    if not r.ok:
        return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}
    raw = (r.json() or {}).get("rawData")
    if not raw:
        return {"error": "ответ 200 без rawData"}
    parsed = parse_serp(base64.b64decode(raw).decode("utf-8", "replace"))
    if parsed.get("error"):
        return {"error": parsed["error"]}
    return {"found": parsed.get("found"), "top": parsed["docs"][:TOP_N]}


def run(date_s: str, queries: list[str]) -> dict:
    import requests

    key = os.environ.get("WORDSTAT_API_KEY", "").strip()
    if not key:
        return {"error": "секрет WORDSTAT_API_KEY не задан"}
    date = dt.date.fromisoformat(date_s)
    spent = month_spent(date)
    today = day_spent(date)
    budget = min(DAILY_CAP - today, MONTHLY_CAP - spent)
    if budget <= 0:
        reason = (f"месячный потолок {MONTHLY_CAP} запросов исчерпан "
                  f"({spent} израсходовано)"
                  if MONTHLY_CAP - spent <= 0 else
                  f"дневной потолок {DAILY_CAP} запросов исчерпан "
                  f"({today} за сегодня)")
        return {"error": reason, "spent_month": spent, "spent_today": today}
    todo = queries[:budget]
    skipped = len(queries) - len(todo)

    SERP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SERP_DIR / f"{date_s}-serp.jsonl"
    session = requests.Session()
    ok = failed = 0
    with out_path.open("w", encoding="utf-8") as out:
        for q in todo:
            try:
                res = fetch_serp(session, key, q)
            except requests.RequestException as e:
                res = {"error": f"{type(e).__name__}: {e}"}
            status = "error" if res.get("error") else "ok"
            log_call(date, q, status, res.get("found"))
            row = {"date": date_s, "query": q, "region": REGION, **res}
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            ok += status == "ok"
            failed += status == "error"
            time.sleep(0.15)      # заведомо ниже RPS-квоты сервиса
    return {"date": date_s, "requested": len(todo), "ok": ok,
            "failed": failed, "skipped_over_budget": skipped,
            "spent_month": spent + len(todo), "cap_month": MONTHLY_CAP,
            "out": str(out_path)}


def main() -> int:
    date_s = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(
        MSK).date().isoformat()
    import serp_watchlist
    queries = serp_watchlist.build(date_s)
    if not queries:
        print("watchlist пуст — собирать нечего")
        return 1
    res = run(date_s, queries)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 1 if res.get("error") or res.get("failed") == res.get("requested") \
        else 0


if __name__ == "__main__":
    sys.exit(main())
