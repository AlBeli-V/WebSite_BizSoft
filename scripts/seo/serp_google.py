#!/usr/bin/env python3
"""Google-срез по ядру запросов через xmlriver (российская выдача).

Дополняет ночной срез Яндекса (serp_watch.py) второй поисковой системой.
Ядро — то же, из данных (serp_watchlist.py); регион один — местоположение
из data/seo/xmlriver.json (по умолчанию Россия, 2643).

Страница выдачи у xmlriver — 10 позиций; глубже — постранично, параметр
page с нумерацией с единицы (ответ поддержки 03.09.2026). `pages` в
конфиге — сколько страниц снимать на ключ (2 = топ-20). Следующая
страница идёт только после удачной и полной предыдущей, повторы по URL не
склеиваются (`duplicates_dropped`), сбой следующей страницы не стирает
собранное (`partial_error`).

Дисциплина — как у Яндекс-среза:
  - ни один вызов без строки в журнале serp/ledger/google-<месяц>.jsonl
    (потолки считаются в ВЫЗОВАХ, а не в ключах);
  - дневной и месячный потолки из конфига проверяются до вызовов;
  - расписание: weekly (день недели из конфига, решение руководителя
    31.08.2026 — Google еженедельно) или daily; --force снимает срез в любой
    день (ручной прогон).

Один сбор — все потребители (архитектура 03.09.2026). Срез — единственный
источник Google-выдачи для обоих контуров: веб-отчёт Growth Intelligence
(serp_analysis.py) и конкурентная разведка (competitive-intelligence,
читает ветку seo-data только на чтение). Никто из них к xmlriver не ходит.
Отсюда две меры против повторной оплаты одного и того же:
  - докачка: если срез за дату уже есть (повторный запуск, --force после
    сбоя, добивка), ключи с данными не запрашиваются повторно — платятся
    только недостающие и ошибочные; полный пересбор — только --refetch;
  - провенанс в каждой строке (provider, series, loc, device, lang,
    collector_version): потребители отличают российскую серию google_ru от
    любой другой и не склеивают их в один ряд.
Журнал прогонов serp/ledger/google-runs.jsonl — по строке на прогон: сколько
ключей запрошено, сколько взято из готового среза, сколько вызовов и рублей
ушло. По нему видно, что дедупликация действительно экономит.

Запуск (workflow seo-serp-watch): python3 scripts/seo/serp_google.py [дата] [--force] [--refetch]
Выход: reports/seo/serp/<дата>-serp-google.jsonl (строка на запрос, engine=google)
       reports/seo/serp/ledger/google-runs.jsonl (строка на прогон)
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
RUNS_FILE_NAME = "google-runs.jsonl"
ENGINE = "google"
PROVIDER = "xmlriver"
# Версия сборщика пишется в каждую строку среза: смена разбора или склейки
# страниц — повод не сравнивать строки как равноточные.
COLLECTOR_VERSION = "1.2.0"
# Потоков — 3, не 4: пересбор 03.09.2026 при четырёх потоках упёрся в
# «Нет свободных каналов» (code=111) по 26 ключам даже с четырьмя повторами.
WORKERS = 3
PAUSE_S = 0.5
# Страница считается «полной», если органики на ней не меньше стольких
# позиций: Google почти всегда отдаёт 8–9 органических результатов на
# первой странице (блоки видео/рекламы занимают места), и порог в 10
# оставлял без второй страницы 271 ключ из 328 (пересбор 03.09.2026).
PAGE_FULL_MIN = 7

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
             loc, page: int = 1) -> None:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             "date": date.isoformat(),
             "query": query, "engine": ENGINE, "loc": loc, "page": page,
             "status": status, "found": found}
    with ledger_path(date).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def snapshot_path(date_s: str) -> pathlib.Path:
    return SERP_DIR / f"{date_s}-serp-google.jsonl"


def _norm(query: str) -> str:
    return " ".join((query or "").lower().split())


def pages_missing(row: dict, cfg: dict) -> int:
    """Сколько страниц ключу ещё не хватает до `pages` из конфига.

    Ноль — строка полная: страниц снято сколько нужно, либо последняя
    снятая страница оказалась короче PAGE_FULL_MIN (глубина выдачи
    исчерпана, дальше пусто). Строка с partial_error — последняя страница
    не снята, её надо повторить.
    """
    pages = max(int(cfg.get("pages", 1)), 1)
    fetched = int(row.get("pages_fetched") or 1)
    if row.get("partial_error"):
        fetched -= 1          # страница с ошибкой не считается снятой
    if fetched >= pages:
        return 0
    got = len(row.get("top") or [])
    if got < PAGE_FULL_MIN * fetched:
        return 0              # выдача короче — глубже ничего нет
    return pages - fetched


def existing_rows(date_s: str, cfg: dict) -> dict[str, dict]:
    """Строки с данными из уже записанного среза за дату — по нормализованному
    запросу. Годятся только строки той же серии и того же местоположения:
    смена loc в конфиге делает старые строки другим измерением.
    Строки с ошибкой не возвращаются — их надо докачать. Строки, у которых
    снято меньше страниц, чем задано в конфиге, возвращаются: недостающие
    страницы докачиваются поверх (pages_missing)."""
    p = snapshot_path(date_s)
    if not p.exists():
        return {}
    series = cfg.get("series", "google_ru")
    loc = cfg["query"].get("loc")
    out: dict[str, dict] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("error"):
            continue
        if not isinstance(row.get("top"), list):
            continue          # строка без результата замера — докачать
        # Пустая выдача без ошибки — полный замер; докачивать и платить
        # за неё повторно не нужно (pages_missing видит короткую страницу).
        if row.get("series", series) != series or row.get("loc", loc) != loc:
            continue
        out[_norm(row.get("query", ""))] = row
    return out


def log_run(summary: dict) -> None:
    """Строка журнала прогонов: сколько запрошено, сколько взято из готового
    среза, сколько вызовов и рублей ушло. Пишется и при полной докачке
    (нулевой расход) — нулевая строка и есть доказательство экономии."""
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
             **{k: summary.get(k) for k in (
                 "date", "engine", "provider", "series", "loc",
                 "requested", "reused", "calls", "ok", "failed",
                 "skipped_over_budget", "cost_rub")}}
    bal = summary.get("balance") or {}
    if bal.get("balance_rub") is not None:
        entry["balance_rub"] = bal["balance_rub"]
    with (LEDGER_DIR / RUNS_FILE_NAME).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def is_collection_day(date: dt.date, cfg: dict) -> bool:
    """weekly — только в день недели из конфига (1 = понедельник);
    daily — каждый день; иное значение — как daily, чтобы опечатка в
    конфиге не остановила сбор молча."""
    if cfg.get("cadence") == "weekly":
        return date.isoweekday() == int(cfg.get("weekday", 1))
    return True


def fetch_query(session, user: str, key: str, q: str, cfg: dict,
                start_page: int = 1) -> dict:
    """Страницы одного ключа начиная с start_page: список результатов.

    Следующая страница запрашивается только после удачной и «полной»
    (≥ PAGE_FULL_MIN позиций) предыдущей — иначе платный вызов уйдёт
    впустую. Возвращает {"pages": [res, …], "start_page": N}.
    """
    pages = max(int(cfg.get("pages", 1)), 1)
    out = []
    # Нумерация страниц xmlriver — с единицы (ответ поддержки 03.09.2026).
    for page in range(max(start_page, 1), pages + 1):
        try:
            res = xmlriver.search_google(session, user, key, q,
                                        cfg["query"], cfg["top_n"], page)
        except Exception as e:  # noqa: BLE001
            res = {"error": f"{type(e).__name__}: {e}"}
        out.append(res)
        if "error" in res:
            break
        if len(res.get("top") or []) < PAGE_FULL_MIN:
            break     # выдача короче страницы — дальше пусто
        time.sleep(PAUSE_S)
    return {"pages": out, "start_page": max(start_page, 1)}


def merge_pages(results: list[dict], top_n: int,
                base: dict | None = None) -> dict:
    """Одна строка среза из страниц: топ склеивается по порядку страниц,
    found и blocks — с первой; ошибка первой страницы — ошибка строки,
    ошибка следующей — partial_error при сохранённом топе.

    base — уже записанная строка ключа (докачка страниц): её топ идёт
    первым, новые страницы приклеиваются следом, pages_fetched растёт.
    """
    if base is not None:
        row = {"found": base.get("found"), "top": list(base.get("top") or [])}
        blocks = dict(base.get("blocks") or {})
        prior_pages = int(base.get("pages_fetched") or 1)
        if base.get("partial_error"):
            prior_pages -= 1
        rest = results
        if base.get("duplicates_dropped"):
            row["duplicates_dropped"] = base["duplicates_dropped"]
    else:
        first = results[0]
        if "error" in first:
            return {"error": first["error"]}
        row = {"found": first.get("found"), "top": list(first.get("top") or [])}
        blocks = dict(first.get("blocks") or {})
        prior_pages = 1
        rest = results[1:]
    seen_urls = {d.get("url") for d in row["top"]}
    for res in rest:
        if "error" in res:
            row["partial_error"] = res["error"]
            break
        # Google повторяет часть URL на соседних страницах (проверено на
        # срезе 03.09.2026: 113 повторов на 373 ключа): повторы по URL не
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
    row["pages_fetched"] = prior_pages + len(rest)
    return row


def collect(session, user: str, key: str, date: dt.date, queries: list,
            cfg: dict, writer) -> tuple[int, int, int]:
    """Снять выдачу по списку запросов в несколько потоков.

    Элемент queries — ключ (str) либо пара (ключ, прежняя строка): во
    втором случае докачиваются только недостающие страницы поверх
    прежней строки. Журнал и файл среза пишутся только из главного
    потока: каждый платный вызов (страница) — строка журнала; каждый
    ключ — строка среза (объединённый топ или ошибка).
    Возвращает (ok, failed, calls).
    """
    loc = cfg["query"].get("loc")
    provenance = {"provider": PROVIDER, "series": cfg.get("series", "google_ru"),
                  "device": cfg["query"].get("device"),
                  "lang": cfg["query"].get("lr"),
                  "collector_version": COLLECTOR_VERSION}
    ok = failed = calls = 0

    tasks = [(t, None) if isinstance(t, str) else (t[0], t[1])
             for t in queries]

    def one(task) -> tuple[str, dict | None, dict]:
        q, base = task
        time.sleep(PAUSE_S)
        start = 1
        if base is not None:
            fetched_pages = int(base.get("pages_fetched") or 1)
            start = fetched_pages if base.get("partial_error") \
                else fetched_pages + 1
        return q, base, fetch_query(session, user, key, q, cfg, start)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(one, t) for t in tasks]
        for fut in as_completed(futures):
            q, base, fetched = fut.result()
            for page, res in enumerate(fetched["pages"],
                                       start=fetched["start_page"]):
                log_call(date, q, "ok" if "error" not in res else "error",
                         res.get("found"), loc, page)
                calls += 1
            merged = merge_pages(fetched["pages"], cfg["top_n"], base)
            row = {"date": date.isoformat(), "query": q, "engine": ENGINE,
                   "region": str(loc) if loc is not None else "",
                   "loc": loc, **provenance, **merged}
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
        force: bool = False, refetch: bool = False) -> dict:
    """Срез за дату: докачка недостающего поверх уже собранного.

    Ключи, по которым в срезе за эту дату уже есть данные, повторно не
    запрашиваются (повторный запуск, --force после сбоя, добивка) — за них
    не платим. `refetch` отключает докачку и пересобирает всё.
    """
    import requests

    date = dt.date.fromisoformat(date_s)
    if not cfg.get("enabled", True):
        return {"skipped": "сбор выключен в data/seo/xmlriver.json"}
    if not force and not is_collection_day(date, cfg):
        return {"skipped": f"{date_s} не день сбора Google "
                           f"(cadence={cfg.get('cadence')}, "
                           f"weekday={cfg.get('weekday')})"}
    ready = {} if refetch else existing_rows(date_s, cfg)
    pages = max(int(cfg.get("pages", 1)), 1)
    # Готовые строки: полные берутся как есть, неполным докачиваются
    # недостающие страницы (по одному вызову на страницу).
    reused = [q for q in queries if _norm(q) in ready
              and pages_missing(ready[_norm(q)], cfg) == 0]
    topup = [q for q in queries if _norm(q) in ready
             and pages_missing(ready[_norm(q)], cfg) > 0]
    missing = [q for q in queries if _norm(q) not in ready]

    spent = month_spent(date)
    today = day_spent(date)
    # Потолки — в вызовах: новый ключ стоит `pages` вызовов, докачка —
    # столько, сколько страниц не хватает. Сначала докачка (дешевле и
    # доводит уже оплаченное до нужной глубины), затем новые ключи.
    budget = min(cfg["daily_cap"] - today, cfg["monthly_cap"] - spent)
    if budget <= 0 and (missing or topup):
        reason = (f"месячный потолок {cfg['monthly_cap']} запросов исчерпан "
                  f"({spent} израсходовано)"
                  if cfg["monthly_cap"] - spent <= 0 else
                  f"дневной потолок {cfg['daily_cap']} запросов исчерпан "
                  f"({today} за сегодня)")
        return {"error": reason, "spent_month": spent, "spent_today": today,
                "reused": len(reused)}
    todo: list = []
    left = max(budget, 0)
    for q in topup:
        cost = pages_missing(ready[_norm(q)], cfg)
        if cost > left:
            break
        todo.append((q, ready[_norm(q)]))
        left -= cost
    for q in missing:
        if pages > left:
            break
        todo.append(q)
        left -= pages
    planned = {t if isinstance(t, str) else t[0] for t in todo}
    skipped = sum(1 for q in topup + missing if q not in planned)
    # Неполные строки, не влезшие в бюджет, остаются в срезе как есть.
    reused += [q for q in topup if q not in planned]

    SERP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = snapshot_path(date_s)
    session = requests.Session()
    with out_path.open("w", encoding="utf-8") as out:
        def writer(row: dict):
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
        # Сначала — уже собранное (как было записано), потом докачка.
        for q in reused:
            writer(ready[_norm(q)])
        ok, failed, calls = collect(session, user, key, date, todo, cfg,
                                    writer)
    balance = write_balance(session, user, key, cfg, today + calls)
    summary = {"date": date_s, "engine": ENGINE, "provider": PROVIDER,
               "series": cfg.get("series", "google_ru"),
               "requested": len(todo), "reused": len(reused),
               "topped_up": sum(1 for t in todo if not isinstance(t, str)),
               "pages": pages, "calls": calls,
               "cost_rub": round(calls * cfg["price_rub_per_1000"] / 1000, 3),
               "ok": ok, "failed": failed, "skipped_over_budget": skipped,
               "spent_month": spent + calls, "cap_month": cfg["monthly_cap"],
               "loc": cfg["query"].get("loc"), "balance": balance,
               "out": str(out_path)}
    log_run(summary)
    return summary


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv[1:]
    refetch = "--refetch" in sys.argv[1:]
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
    res = run(date_s, core, cfg, user, key, force=force, refetch=refetch)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if res.get("skipped"):
        return 0
    if res.get("reused"):
        print(f"из готового среза за {date_s} взято {res['reused']} ключей, "
              f"докачано {res.get('requested', 0)} — повторно не оплачивались")
    if res.get("balance", {}).get("needs_topup"):
        print(f"::warning::баланс xmlriver {res['balance'].get('balance_rub')} ₽ "
              f"— хватит примерно на {res['balance'].get('days_left_estimate')} "
              f"дн. сбора, нужно пополнение")
    # Полная докачка без единого вызова — успех, а не «все запросы упали».
    all_failed = (res.get("requested", 0) > 0
                  and res.get("failed") == res.get("requested"))
    return 1 if res.get("error") or all_failed else 0


if __name__ == "__main__":
    sys.exit(main())
