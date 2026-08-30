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
ASYNC_URL = "https://searchapi.api.cloud.yandex.net/v2/web/searchAsync"
OPERATIONS_URL = "https://operations.api.cloud.yandex.net/operations/"
SERP_DIR = pathlib.Path("reports/seo/data/serp")
LEDGER_DIR = SERP_DIR / "ledger"

# Отложенный режим (решение 30.08.2026 по фактическому прайсу): ночной
# deferred — 25,41 ₽/1000 против ~488 ₽/1000 у синхронного, ~в 19 раз
# дешевле. Все операции отправляются пакетом, затем добираются опросом.
POLL_TIMEOUT_S = 35 * 60
POLL_INTERVAL_S = 20

# Потолки — решение руководителя 30.08.2026 («зелёный свет» на расширение
# по фактическому прайсу отложенного ночного тарифа 25,41 ₽/1000):
# полное коммерческое ядро по Москве + топ ядра по Санкт-Петербургу.
MONTHLY_CAP = 20000
DAILY_CAP = 700           # ~500 ядро Мск + 150 СПб + запас на ручные пробы
REGION_MSK = "213"
REGION_SPB = "2"
SPB_TOP = 150             # сколько верхних запросов ядра дублируется по СПб
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


def log_call(date: dt.date, query: str, status: str, found: int | None,
             region: str = REGION_MSK):
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             "query": query, "region": region, "status": status,
             "found": found}
    with ledger_path(date).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _headers(key: str) -> dict:
    return {"Authorization": f"Api-Key {key}",
            "Content-Type": "application/json"}


def _parse_raw(raw: str) -> dict:
    parsed = parse_serp(base64.b64decode(raw).decode("utf-8", "replace"))
    if parsed.get("error"):
        return {"error": parsed["error"]}
    return {"found": parsed.get("found"), "top": parsed["docs"][:TOP_N]}


def submit_deferred(session, key: str, query: str,
                    region: str = REGION_MSK) -> dict:
    """Отправка отложенного запроса → id операции. Тарифицируется отправка;
    опрос операции бесплатен."""
    body = {"query": {"searchType": "SEARCH_TYPE_RU", "queryText": query},
            "region": region}
    r = session.post(ASYNC_URL, json=body, timeout=60, headers=_headers(key))
    if not r.ok:
        return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}
    op = (r.json() or {}).get("id")
    if not op:
        return {"error": "ответ 200 без id операции"}
    return {"op": op}


def fetch_operation(session, key: str, op: str) -> dict | None:
    """Результат операции: None — ещё выполняется; dict — готово/ошибка."""
    r = session.get(OPERATIONS_URL + op, timeout=60, headers=_headers(key))
    if not r.ok:
        return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}
    data = r.json() or {}
    if not data.get("done"):
        return None
    if data.get("error"):
        return {"error": json.dumps(data["error"], ensure_ascii=False)[:300]}
    raw = (data.get("response") or {}).get("rawData")
    if not raw:
        return {"error": "операция done без rawData"}
    return _parse_raw(raw)


def collect_deferred(session, key: str, date: dt.date,
                     tasks: list[dict], writer) -> tuple[int, int]:
    """Пакет отложенных запросов: отправить все, затем добирать опросом.

    Задание — {"query", "region"}: одно ядро снимается по нескольким
    регионам. Каждая отправка — строка журнала (платный вызов). Не готовое
    к дедлайну пишется ошибкой в срез, а id операций — в pending-файл.
    """
    pending: dict[tuple[str, str], str] = {}
    ok = failed = 0
    for t in tasks:
        q, region = t["query"], t.get("region", REGION_MSK)
        try:
            res = submit_deferred(session, key, q, region)
        except Exception as e:  # noqa: BLE001
            res = {"error": f"{type(e).__name__}: {e}"}
        log_call(date, q, "submitted" if "op" in res else "submit-error",
                 None, region)
        if "op" in res:
            pending[(q, region)] = res["op"]
        else:
            failed += 1
            writer({"date": date.isoformat(), "query": q, "region": region,
                    "error": res["error"]})
        time.sleep(0.15)

    deadline = time.monotonic() + POLL_TIMEOUT_S
    while pending and time.monotonic() < deadline:
        for (q, region), op in list(pending.items()):
            try:
                res = fetch_operation(session, key, op)
            except Exception as e:  # noqa: BLE001
                res = {"error": f"{type(e).__name__}: {e}"}
            if res is None:
                continue
            del pending[(q, region)]
            row = {"date": date.isoformat(), "query": q, "region": region,
                   **res}
            writer(row)
            ok += "error" not in res
            failed += "error" in res
        if pending:
            time.sleep(POLL_INTERVAL_S)

    if pending:
        pfile = SERP_DIR / f"pending-{date.isoformat()}.json"
        pfile.write_text(json.dumps(
            [{"query": q, "region": r, "op": op}
             for (q, r), op in pending.items()],
            ensure_ascii=False, indent=1), encoding="utf-8")
        for (q, region), op in pending.items():
            failed += 1
            writer({"date": date.isoformat(), "query": q, "region": region,
                    "error": f"результат не готов к дедлайну (operation {op})"})
    return ok, failed


def run(date_s: str, tasks: list[dict]) -> dict:
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
    todo = tasks[:budget]
    skipped = len(tasks) - len(todo)

    SERP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SERP_DIR / f"{date_s}-serp.jsonl"
    session = requests.Session()
    with out_path.open("w", encoding="utf-8") as out:
        def writer(row: dict):
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
        ok, failed = collect_deferred(session, key, date, todo, writer)
    return {"date": date_s, "requested": len(todo), "ok": ok,
            "failed": failed, "skipped_over_budget": skipped,
            "spent_month": spent + len(todo), "cap_month": MONTHLY_CAP,
            "mode": "deferred-night",
            "out": str(out_path)}


def build_tasks(core: list[str]) -> list[dict]:
    """Задания среза: всё ядро по Москве + верх ядра по Санкт-Петербургу.

    СПб идёт после всего московского списка: при усечении бюджетом
    страдает дубль-регион, а не основное покрытие.
    """
    return ([{"query": q, "region": REGION_MSK} for q in core]
            + [{"query": q, "region": REGION_SPB} for q in core[:SPB_TOP]])


def main() -> int:
    date_s = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(
        MSK).date().isoformat()
    import serp_watchlist
    core = serp_watchlist.build(date_s)
    if not core:
        print("watchlist пуст — собирать нечего")
        return 1
    res = run(date_s, build_tasks(core))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 1 if res.get("error") or res.get("failed") == res.get("requested") \
        else 0


if __name__ == "__main__":
    sys.exit(main())
