#!/usr/bin/env python3
"""Разбор разрыва Google ↔ Яндекс по инвентарю sitemap.

Зачем. Сенсоры контура отвечают на вопрос «сколько»: index_coverage.py
снимает статус каждой страницы в Google (URL Inspection) и в Яндексе
(Webmaster), zero_impression.py раскладывает страницы без показов. Ни один
не отвечает на вопрос «какие именно коммерческие страницы Яндекс уже
ранжирует, а Google даже не скачивал» — а именно этот срез нужен, чтобы
решать, куда тратить обход, которого у молодого домена мало.

Скрипт соединяет пять источников за одну дату и считает по каждому пути
инвентаря: состояние в Google (обойден / в индексе / известен), состояние в
Яндексе (в поиске / исключён с причиной), показы Google за 28 дней и
позицию в выдаче обоих поисковиков по контрольному ядру запросов.

Поверх этого — Google Index Priority Score (GIPS): грубая шкала 0–100,
которая отвечает на один вопрос — «если Google в сутки скачивает единицы
страниц, какие подать первыми». Веса и их обоснование — в docstring score().
Модель намеренно грубая: она ранжирует, а не предсказывает.

С 08.09.2026 в GIPS входят два фактора со стороны выдачи, которых по
инвентарю не видно (`google_authority.demand_by_path`): сколько запросов
коммерческого ядра страница держит в топ-10 Яндекса и насколько слаба по
ним выдача Google. Первый отвечает «сколько мы теряем, пока страницы нет
в Google», второй — «велик ли шанс войти». Прежний счёт сохраняется в
колонке gips_base: решение руководителя менять порядок подачи, а не
переписывать модель молча.

Пишет:
  reports/seo/google-indexation-gap.csv   — по каждому URL инвентаря
  reports/seo/google-url-priority.csv     — то же, отсортировано по GIPS
  reports/seo/internal-link-analysis.csv  — перелинковка по типам страниц

Запуск: python3 scripts/seo/google_gap.py [ГГГГ-ММ-ДД] [--data-dir DIR]
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import google_authority  # noqa: E402

DATA_DIR = pathlib.Path("reports/seo/data")
SERP_DIR = pathlib.Path("reports/seo/serp")
OUT_DIR = pathlib.Path("reports/seo")
LOOKBACK_DAYS = 7
SITE = "biz-soft.pro"

# Типы страниц — по маршрутам src/pages. Порядок важен: первое совпадение.
ROUTES: list[tuple[str, str]] = [
    ("/product/", "product"),
    ("/vendors/zoho/", "vendor_zoho_sub"),
    ("/vendors/", "vendor"),
    ("/catalog/", "category"),
    ("/blog/tag/", "blog_tag"),
    ("/blog/", "blog_post"),
    ("/solutions/", "solution"),
    ("/compare/", "compare"),
    ("/alternatives/", "alternative"),
    ("/docs/", "docs"),
]
HUBS = {"/": "homepage", "/catalog": "catalog_hub", "/blog": "blog_hub",
        "/vendors": "vendor_hub", "/solutions": "solution_hub", "/docs": "docs_hub"}
UTILITY = {"/pricing", "/how-we-work", "/documents", "/faq", "/cases",
           "/about", "/contacts", "/compliance", "/privacy"}

# Коммерческий вес типа страницы: сколько денег стоит её попадание в выдачу.
# Лендинг вендора — верх воронки бренда («купить X для юрлица»), карточка —
# конкретная лицензия, hub — навигация, статья — спрос без покупки сегодня.
COMMERCIAL = {
    "vendor": 1.0, "vendor_zoho_sub": 0.8, "category": 0.8, "catalog_hub": 0.8,
    "product": 0.7, "solution": 0.6, "alternative": 0.6, "compare": 0.5,
    "homepage": 1.0, "vendor_hub": 0.7, "blog_post": 0.4, "blog_hub": 0.3,
    "blog_tag": 0.2, "utility": 0.3, "docs": 0.2, "docs_hub": 0.2,
    "solution_hub": 0.5, "other": 0.3,
}


def page_type(path: str) -> str:
    if path in HUBS:
        return HUBS[path]
    if path in UTILITY:
        return "utility"
    for prefix, name in ROUTES:
        if path.startswith(prefix):
            return name
    return "other"


def _latest(directory: pathlib.Path, pattern: str, date_s: str) -> tuple[str, dict] | None:
    """Свежий файл вида pattern.format(date) не старше LOOKBACK_DAYS."""
    date = dt.date.fromisoformat(date_s)
    for back in range(LOOKBACK_DAYS + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        p = directory / pattern.format(date=d)
        if not p.exists():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(raw, dict) and raw.get("error"):
            continue
        return d, raw
    return None


def _latest_lines(directory: pathlib.Path, pattern: str, date_s: str):
    """Свежий JSONL-срез выдачи не старше LOOKBACK_DAYS."""
    date = dt.date.fromisoformat(date_s)
    for back in range(LOOKBACK_DAYS + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        p = directory / pattern.format(date=d)
        if not p.exists():
            continue
        rows = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
        if rows:
            return d, rows
    return None


def serp_positions(rows: list[dict]) -> dict[str, tuple[int, str]]:
    """Путь сайта → (лучшая позиция, запрос) по срезу выдачи."""
    best: dict[str, tuple[int, str]] = {}
    for r in rows:
        for i, item in enumerate(r.get("top") or [], 1):
            url = item.get("url") or ""
            if SITE not in (item.get("domain") or "") and SITE not in url:
                continue
            path = url.split(SITE, 1)[-1].split("?")[0].split("#")[0].rstrip("/") or "/"
            if path not in best or i < best[path][0]:
                best[path] = (i, r.get("query", ""))
    return best


def score(row: dict) -> tuple[int, int, str]:
    """Google Index Priority Score, 0–100. Ранжирует, а не предсказывает.

    Веса выбраны так, чтобы на первое место выходили страницы, по которым
    уже есть внешнее подтверждение спроса и релевантности, — а не те, что
    просто длиннее или новее.

      35  доказательство Яндексом: страница в поиске и стоит по контрольному
          запросу. Это единственный в проекте факт, полученный не от Google:
          он говорит, что страница отвечает на живой коммерческий запрос.
          TOP-3 весит больше TOP-10, TOP-10 — больше «просто в поиске».
      25  коммерческий вес типа страницы (таблица COMMERCIAL).
      15  текущие показы Google: страница уже участвует в выдаче, ей нужен
          не обход, а позиция — такие дешевле всего сдвинуть.
      15  состояние обхода: не скачанная страница получает максимум (это и
          есть очередь на подачу), уже проиндексированная — минимум.
      10  индексируемость в Яндексе как отрицательный сигнал качества:
          страница, исключённая Яндексом как малоценная, теряет эти баллы —
          подавать её в Google раньше остальных смысла нет.

    Сверх базовых 100 — надбавка до 20 за спрос со стороны выдачи. Она
    разводит страницы, у которых базовый счёт совпал:

      12  объём удерживаемого спроса: сколько запросов ядра страница держит
          в топ-10 Яндекса. Базовый счёт видит только лучшую позицию по
          одному запросу, поэтому страница на 32 запроса и страница на один
          получали поровну.
       8  слабость выдачи Google по этим запросам: там, где топ занят UGC и
          маркетплейсами вместо специализированных продавцов, шанс войти
          выше, и обход окупается быстрее.

    Возвращает (итоговый счёт, базовый счёт, тир). Базовый сохраняется в
    отчёте: без него нельзя проверить, что надбавка меняет порядок, а не
    подменяет модель.
    """
    s = 0.0
    yp = row["yandex_position"]
    if yp and yp <= 3:
        s += 35
    elif yp and yp <= 10:
        s += 28
    elif yp and yp <= 20:
        s += 18
    elif row["yandex_state"] == "in_search":
        s += 12
    s += 25 * COMMERCIAL.get(row["page_type"], 0.3)
    if row["google_impressions"] > 0:
        s += 15 if row["google_impressions"] >= 5 else 10
    if not row["google_crawled"]:
        s += 15
    elif not row["google_indexed"]:
        s += 10
    else:
        s += 4
    if row["yandex_state"] == "excluded":
        s += 0
    elif row["yandex_state"] == "in_search":
        s += 10
    else:
        s += 5
    base = max(0, min(100, round(s)))

    # Надбавка за спрос: логарифмическая по числу запросов — разница между
    # одним и десятью запросами важнее, чем между тридцатью и сорока.
    held = row.get("serp_queries_held") or 0
    weak = row.get("serp_weakness_avg") or 0
    bonus = 0.0
    if held:
        bonus += min(12.0, 4.0 * math.log2(1 + held))
    if weak:
        bonus += 8.0 * min(1.0, weak / 50.0)
    total = max(0, min(100, round(base + bonus)))

    tier = ("TIER 1" if total >= 75 else "TIER 2" if total >= 62 else
            "TIER 3" if total >= 50 else "TIER 4" if total >= 38 else "TIER 5")
    return total, base, tier


def cause(row: dict) -> str:
    """Категория причины по классификации этапа 3 (A–L)."""
    if row["google_state"] == "URL is unknown to Google":
        return "A: URL discovery"
    if row["google_state"].startswith("Discovered"):
        return "B: crawl scheduling"
    if row["google_state"].startswith("Crawled"):
        return "C: indexing/quality"
    if "noindex" in row["google_state"]:
        return "K: техническая (noindex)"
    if row["google_indexed"] and row["google_impressions"] == 0:
        return "H: authority/entity"
    if row["google_indexed"] and row["google_position"] and row["google_position"] > 20:
        return "H: authority/entity"
    if row["google_indexed"]:
        return "I: конкурентная выдача"
    return "L: недостаточно данных"


def build(date_s: str) -> list[dict]:
    sm = _latest(DATA_DIR, "sitemap-{date}.json", date_s)
    gi = _latest(DATA_DIR, "index-google-{date}.json", date_s)
    yi = _latest(DATA_DIR, "index-yandex-{date}.json", date_s)
    gsc = _latest(DATA_DIR, "gsc-{date}.json", date_s)
    if not sm:
        raise SystemExit("нет свежего инвентаря sitemap — сбор не отработал")
    gpages = (gi[1].get("pages") if gi else {}) or {}
    ya_in = set((yi[1].get("in_search") if yi else []) or [])
    ya_ex = (yi[1].get("excluded") if yi else {}) or {}
    imp: dict[str, dict] = {}
    if gsc:
        for r in ((gsc[1].get("analytics") or {}).get("page") or {}).get("rows", []):
            path = (r["keys"][0].split(SITE, 1)[-1] or "/").rstrip("/") or "/"
            imp[path] = r
    gserp = _latest_lines(SERP_DIR, "{date}-serp-google.jsonl", date_s)
    yserp = _latest_lines(SERP_DIR, "{date}-serp.jsonl", date_s)
    gpos = serp_positions(gserp[1]) if gserp else {}
    ypos = serp_positions(yserp[1]) if yserp else {}
    # Спрос со стороны выдачи. Пустой словарь — не сбой: без свежего
    # Google-среза приоритет считается по базовым факторам.
    demand = google_authority.demand_by_path(SERP_DIR, DATA_DIR, date_s)

    rows = []
    for u in sm[1]["urls"]:
        path = u["path"]
        g = gpages.get(path, {})
        state = g.get("coverage_state", "")
        row = {
            "path": path,
            "page_type": page_type(path),
            "lastmod": u.get("lastmod") or "",
            "google_state": state,
            "google_crawled": bool(g.get("last_crawl")),
            "google_last_crawl": (g.get("last_crawl") or "")[:10],
            "google_indexed": state == "Submitted and indexed",
            "google_impressions": (imp.get(path) or {}).get("impressions", 0),
            "google_clicks": (imp.get(path) or {}).get("clicks", 0),
            "google_position": round((imp.get(path) or {}).get("position", 0), 1) or None,
            "google_serp_position": gpos.get(path, (None, ""))[0],
            "yandex_state": ("in_search" if path in ya_in
                             else "excluded" if path in ya_ex else "unknown"),
            "yandex_excluded_reason": (ya_ex.get(path) or {}).get("status", ""),
            "yandex_position": ypos.get(path, (None, ""))[0],
            "yandex_query": ypos.get(path, (None, ""))[1],
            "serp_queries_held": (demand.get(path) or {}).get("queries_held", 0),
            "serp_weakness_avg": (demand.get(path) or {}).get("weakness_avg", 0),
        }
        row["likely_cause"] = cause(row)
        row["gips"], row["gips_base"], row["tier"] = score(row)
        rows.append(row)
    rows.sort(key=lambda r: (-r["gips"], r["path"]))
    return rows


FIELDS = ["path", "page_type", "tier", "gips", "gips_base",
          "serp_queries_held", "serp_weakness_avg", "likely_cause", "google_state",
          "google_crawled", "google_indexed", "google_last_crawl",
          "google_impressions", "google_clicks", "google_position",
          "google_serp_position", "yandex_state", "yandex_excluded_reason",
          "yandex_position", "yandex_query", "lastmod"]


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    date_s = args[0] if args else dt.date.today().isoformat()
    for a in sys.argv[1:]:
        if a.startswith("--data-dir="):
            globals()["DATA_DIR"] = pathlib.Path(a.split("=", 1)[1])
        if a.startswith("--serp-dir="):
            globals()["SERP_DIR"] = pathlib.Path(a.split("=", 1)[1])
        if a.startswith("--out-dir="):
            globals()["OUT_DIR"] = pathlib.Path(a.split("=", 1)[1])
    rows = build(date_s)
    write_csv(OUT_DIR / "google-url-priority.csv", rows)
    gap = [r for r in rows
           if r["yandex_state"] == "in_search"
           and not (r["google_indexed"] and r["google_impressions"] > 0)]
    write_csv(OUT_DIR / "google-indexation-gap.csv", gap)
    print(f"инвентарь {len(rows)} URL; разрыв Яндекс→Google {len(gap)} URL")
    for tier in ("TIER 1", "TIER 2", "TIER 3", "TIER 4", "TIER 5"):
        n = sum(1 for r in rows if r["tier"] == tier)
        crawled = sum(1 for r in rows if r["tier"] == tier and r["google_crawled"])
        print(f"  {tier}: {n:4d} URL, обойдено Google {crawled}")


if __name__ == "__main__":
    main()
