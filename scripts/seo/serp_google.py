#!/usr/bin/env python3
"""Google-срез по ядру запросов через xmlriver (российская выдача).

Дополняет ночной срез Яндекса (serp_watch.py) второй поисковой системой.
Ядро — то же, из данных (serp_watchlist.py); регион один — местоположение
из data/seo/xmlriver.json (по умолчанию Россия, 2643).

Страница выдачи у xmlriver — 10 позиций. Механизм нескольких страниц
(`pages` в конфиге, параметр page) есть, но выключен (pages=1): проба
03.09.2026 показала, что page сервис игнорирует и «вторая страница» —
дубль первой. При pages>1 вторая страница идёт только после удачной
первой, повторы по URL не склеиваются (`duplicates_dropped`), сбой второй
страницы не стирает первую (`partial_error`).

Дисциплина — как у Яндекс-среза:
  - ни один вызов без строки в журнале serp/ledger/google-<месяц>.jsonl
    (потолки считаются в ВЫЗОВАХ, а не в ключах);
  - дневной и месячный потолки из конфига проверяются до вызовов;
  - расписание: weekly (день недели из конфига, решение руководителя
    31.08.2026 — Google еженедельно) или daily; --force снимает срез в любой
    день (ручной прогон).

Запуск (workflow seo-serp-watch): python3 scripts/seo/serp_google.py [дата] [--force]
Выход: reports/seo/serp/<дата>-serp-google.jsonl (строка на запрос, engine=google)
       reports/seo/serp/xmlriver-balance.json (остаток кабинета после прогона)
Без секретов XMLRIVER_USER/XMLRIVER_KEY шаг тихо пропускается (код 0):
Яндекс-срез от этого не зависит.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import xmlriver  # noqa: E402

SERP_DIR = pathlib.Path("reports/seo/serp")
LEDGER_DIR = SERP_DIR / "ledger"
BALANCE_FILE = SERP_DIR / "xmlriver-balance.json"
ENGINE = "google"
WORKERS = 4
PAUSE_S = 0.2

MSK = ZoneInfo("Europe/Moscow")


def ledger_path(date: dt.date) -> pathlib.Path:
    return LEDGER_DIR / f"google-{date.strftime('%Y-%m')}.jsonl"


def _ledger_lines(date: dt.date) -> list[dict]:
    p = ledger_path(date)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def month_spent(date: dt.date) -> int:
    return len(_ledger_lines(date))


def day_spent(date: dt.date) -> int:
    """Расход за день по журналу: потолок держит день, а не прогон.

    День — дата среза (`date`, по МСК), а не момент вызова: ночной прогон
    идёт в 22:37 UTC, когда в Москве уже следующая дата, и сравнение по
    `at` разошлось бы с датой файла. Старые строки без `date` — по `at`.
    """
    day = date.isoformat()
    return sum(1 for e in _ledger_lines(date)
               if (e.get("date") or e.get("at", "")[:10]) == day)


def log_call(date: dt.date, query: str, status: str, found: int | None,
             loc, page: int = 0) -> None:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             "date": date.isoformat(),
             "query": query, "engine": ENGINE, "loc": loc, "page": page,
             "status": status, "found": found}
    with ledger_path(date).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def is_collection_day(date: dt.date, cfg: dict) -> bool:
    """weekly — только в день недели из конфига (1 = понедельник);
    daily — каждый день; иное значение — как daily, чтобы опечатка в
    конфиге не остановила сбор молча."""
    if cfg.get("cadence") == "weekly":
        return date.isoweekday() == int(cfg.get("weekday", 1))
    return True


def fetch_query(session, user: str, key: str, q: str, cfg: dict) -> dict:
    """Все страницы одного ключа: список результатов по страницам.

    Вторая страница запрашивается только после удачной первой — иначе
    платный вызов уйдёт впустую. Возвращает {"pages": [res0, res1, …]}.
    """
    pages = max(int(cfg.get("pages", 1)), 1)
    out = []
    for page in range(pages):
        try:
            res = xmlriver.search_google(session, user, key, q,
                                        cfg["query"], cfg["top_n"], page)
        except Exception as e:  # noqa: BLE001
            res = {"error": f"{type(e).__name__}: {e}"}
        out.append(res)
        if "error" in res:
            break
        if len(res.get("top") or []) < xmlriver.PAGE_SIZE:
            break     # выдача короче страницы — дальше пусто
        time.sleep(PAUSE_S)
    return {"pages": out}


def merge_pages(results: list[dict], top_n: int) -> dict:
    """Одна строка среза из страниц: топ склеивается по порядку страниц,
    found и blocks — с первой; ошибка первой страницы — ошибка строки,
    ошибка следующей — partial_error при сохранённом топе."""
    first = results[0]
    if "error" in first:
        return {"error": first["error"]}
    row = {"found": first.get("found"), "top": list(first.get("top") or [])}
    blocks = dict(first.get("blocks") or {})
    seen_urls = {d.get("url") for d in row["top"]}
    for res in results[1:]:
        if "error" in res:
            row["partial_error"] = res["error"]
            break
        # Сервис может отдать на «следующей» странице ту же выдачу
        # (xmlriver игнорирует page — проба 03.09.2026): повторы по URL не
        # склеиваем, а считаем, чтобы дубль был виден в срезе.
        fresh = [d for d in (res.get("top") or [])
                 if d.get("url") not in seen_urls]
        row["duplicates_dropped"] = (row.get("duplicates_dropped", 0)
                                     + len(res.get("top") or []) - len(fresh))
        row["top"] += fresh
        seen_urls.update(d.get("url") for d in fresh)
        for k, v in (res.get("blocks") or {}).items():
            blocks[k] = blocks.get(k, 0) + v
    row["top"] = row["top"][:top_n]
    if blocks:
        row["blocks"] = blocks
    row["pages_fetched"] = len(results)
    return row


def collect(session, user: str, key: str, date: dt.date, queries: list[str],
            cfg: dict, writer) -> tuple[int, int, int]:
    """Снять выдачу по списку запросов в несколько потоков.

    Журнал и файл среза пишутся только из главного потока: каждый
    платный вызов (страница) — строка журнала; каждый ключ — строка среза
    (объединённый топ или ошибка). Возвращает (ok, failed, calls).
    """
    loc = cfg["query"].get("loc")
    ok = failed = calls = 0

    def one(q: str) -> tuple[str, dict]:
        time.sleep(PAUSE_S)
        return q, fetch_query(session, user, key, q, cfg)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(one, q) for q in queries]
        for fut in as_completed(futures):
            q, fetched = fut.result()
            for page, res in enumerate(fetched["pages"]):
                log_call(date, q, "ok" if "error" not in res else "error",
                         res.get("found"), loc, page)
                calls += 1
            merged = merge_pages(fetched["pages"], cfg["top_n"])
            row = {"date": date.isoformat(), "query": q, "engine": ENGINE,
                   "region": str(loc) if loc is not None else "",
                   "loc": loc, **merged}
            if "error" in merged:
                failed += 1
            else:
                ok += 1
            writer(row)
    return ok, failed, calls


def write_balance(session, user: str, key: str, cfg: dict,
                  spent_today: int) -> dict:
    """Остаток кабинета после прогона + оценка запаса в днях сбора."""
    bal = xmlriver.get_balance(session, user, key)
    out = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "price_rub_per_1000": cfg["price_rub_per_1000"]}
    if "error" in bal:
        out["error"] = bal["error"]
    else:
        out["balance_rub"] = bal["balance_rub"]
        per_run = max(spent_today, 1) * cfg["price_rub_per_1000"] / 1000
        runs_left = bal["balance_rub"] / per_run if per_run > 0 else None
        days_per_run = 7 if cfg.get("cadence") == "weekly" else 1
        out["runs_left_estimate"] = round(runs_left, 1) if runs_left else None
        out["days_left_estimate"] = (round(runs_left * days_per_run)
                                     if runs_left else None)
        out["needs_topup"] = bool(
            out["days_left_estimate"] is not None
            and out["days_left_estimate"] < cfg.get("balance_warn_days", 14))
    SERP_DIR.mkdir(parents=True, exist_ok=True)
    BALANCE_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    return out


def run(date_s: str, queries: list[str], cfg: dict, user: str, key: str,
        force: bool = False) -> dict:
    import requests

    date = dt.date.fromisoformat(date_s)
    if not cfg.get("enabled", True):
        return {"skipped": "сбор выключен в data/seo/xmlriver.json"}
    if not force and not is_collection_day(date, cfg):
        return {"skipped": f"{date_s} не день сбора Google "
                           f"(cadence={cfg.get('cadence')}, "
                           f"weekday={cfg.get('weekday')})"}
    spent = month_spent(date)
    today = day_spent(date)
    pages = max(int(cfg.get("pages", 1)), 1)
    # Потолки — в вызовах; на ключ уходит `pages` вызовов.
    budget = min(cfg["daily_cap"] - today, cfg["monthly_cap"] - spent) // pages
    if budget <= 0:
        reason = (f"месячный потолок {cfg['monthly_cap']} запросов исчерпан "
                  f"({spent} израсходовано)"
                  if cfg["monthly_cap"] - spent <= 0 else
                  f"дневной потолок {cfg['daily_cap']} запросов исчерпан "
                  f"({today} за сегодня)")
        return {"error": reason, "spent_month": spent, "spent_today": today}
    todo = queries[:budget]
    skipped = len(queries) - len(todo)

    SERP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SERP_DIR / f"{date_s}-serp-google.jsonl"
    session = requests.Session()
    with out_path.open("w", encoding="utf-8") as out:
        def writer(row: dict):
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
        ok, failed, calls = collect(session, user, key, date, todo, cfg,
                                    writer)
    balance = write_balance(session, user, key, cfg, today + calls)
    return {"date": date_s, "engine": ENGINE, "requested": len(todo),
            "pages": pages, "calls": calls,
            "ok": ok, "failed": failed, "skipped_over_budget": skipped,
            "spent_month": spent + calls, "cap_month": cfg["monthly_cap"],
            "loc": cfg["query"].get("loc"), "balance": balance,
            "out": str(out_path)}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv[1:]
    date_s = args[0] if args else dt.datetime.now(MSK).date().isoformat()
    user, key = xmlriver.credentials()
    if not user or not key:
        print("секреты XMLRIVER_USER / XMLRIVER_KEY не заданы — Google-срез пропущен")
        return 0
    cfg = xmlriver.load_config()
    import serp_watchlist
    core = serp_watchlist.build(date_s, cap=cfg["core_cap"])
    if not core:
        print("watchlist пуст — собирать нечего")
        return 1
    res = run(date_s, core, cfg, user, key, force=force)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if res.get("skipped"):
        return 0
    if res.get("balance", {}).get("needs_topup"):
        print(f"::warning::баланс xmlriver {res['balance'].get('balance_rub')} ₽ "
              f"— хватит примерно на {res['balance'].get('days_left_estimate')} "
              f"дн. сбора, нужно пополнение")
    return 1 if res.get("error") or res.get("failed") == res.get("requested") \
        else 0


if __name__ == "__main__":
    sys.exit(main())
