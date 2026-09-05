#!/usr/bin/env python3
"""Фиксированные окна экспериментов: активация по факту выката и выгрузка.

Перезапуск SEO-EXP-002 (решение руководителя 03.09.2026). Две команды:

  activate  — эксперимент со статусом `planned` становится `running` в тот
              день, когда живые страницы отдают новый вариант (title_marker
              из реестра): дата старта — факт выката, а не дата коммита.
              Окна baseline/experiment считаются от старта
              (experiment_stats.plan_windows) и записываются в реестр.
              Запускается из seo-site-check (доступ к проду есть у раннера).
  fetch     — для `running`-экспериментов с окнами выгружает из Вебмастера
              окно, чей последний день уже устоялся (лаг источника), в
              reports/seo/data/yandex-window-<from>_<to>.json полным
              постраничным обходом (без усечения до топ-100). Запускается
              из seo-data-collect (там есть токен Вебмастера). Файл, который
              уже есть, повторно не выгружается.
  validate  — правило руководителя 04.09.2026: новый эксперимент заводится
              только на кластере с экспозицией выше порога. Проверяются
              записи `planned` и `running`, заведённые с даты правила;
              возврат 1, если правило нарушено. Запускать перед отправкой
              реестра в seo-data.
  backfill  — проставляет фиксированное baseline-окно уже идущим
              экспериментам, заведённым до появления этого слоя (решение
              руководителя 04.09.2026). Их baseline брался из скользящей
              выгрузки, а у SEO-EXP-001 и CONTENT-001 — из усечённой (100
              запросов вместо полутора тысяч): вердикты на вехе 16.09
              опирались бы на тот же слабый базис, из-за которого
              SEO-EXP-002 не дал вывода. Окно «после» остаётся скользящим —
              его задним числом не построить, и сравнение честно помечается
              предварительным.

Оба режима идемпотентны и молчат, если делать нечего: контур работает на
автомате, без обращений к руководителю.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import experiment_stats as st  # noqa: E402

REGISTRY = pathlib.Path("reports/seo/intelligence/seo-experiments.json")
SITE = "https://biz-soft.pro"
DEFAULT_TITLE_MARKER = r"(оплат|купить)"


# ── Реестр ──────────────────────────────────────────────────────────────────

def load_registry(path: pathlib.Path = REGISTRY) -> dict:
    if not path.exists():
        return {"experiments": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_registry(reg: dict, path: pathlib.Path = REGISTRY) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")


# ── activate ────────────────────────────────────────────────────────────────

def fetch_title(url: str, timeout: int = 30) -> str | None:
    """<title> живой страницы; None — страница не отдалась."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310
            html = r.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        return None
    m = re.search(r"<title>([^<]*)</title>", html)
    return m.group(1) if m else ""


def pages_live(exp: dict, site: str = SITE,
               get_title=fetch_title) -> tuple[bool, list[dict]]:
    """Все ли страницы эксперимента отдают новый вариант (по title_marker)."""
    marker = re.compile(exp.get("title_marker") or DEFAULT_TITLE_MARKER, re.I)
    rows = []
    for page in exp.get("pages") or []:
        title = get_title(f"{site}{page}")
        rows.append({"page": page, "title": title,
                     "new_variant": bool(title and marker.search(title))})
    return bool(rows) and all(r["new_variant"] for r in rows), rows


def activate(reg: dict, today: dt.date, site: str = SITE,
             get_title=fetch_title) -> list[dict]:
    """planned → running для экспериментов, чьи страницы уже отдают новый вариант.

    Возвращает список активированных записей (для журнала прогона). Реестр
    меняется на месте; сохранение — на вызывающем.
    """
    activated = []
    for exp in reg.get("experiments", []):
        if exp.get("status") != "planned":
            continue
        ok, rows = pages_live(exp, site, get_title)
        if not ok:
            missing = [r["page"] for r in rows if not r["new_variant"]]
            print(f"{exp['id']}: новый вариант не на всех страницах "
                  f"({', '.join(missing) or 'страниц нет'}) — ждём")
            continue
        exp["status"] = "running"
        exp["start"] = today.isoformat()
        exp["windows"] = st.plan_windows(today)
        exp["activated"] = {"date": today.isoformat(), "pages": rows}
        activated.append(exp)
        print(f"{exp['id']}: активирован {today.isoformat()}, окна "
              f"{exp['windows']['baseline']['from']}–{exp['windows']['baseline']['to']} / "
              f"{exp['windows']['experiment']['from']}–{exp['windows']['experiment']['to']}")
    return activated


# ── fetch ───────────────────────────────────────────────────────────────────

def backfill(reg: dict, today: dt.date) -> list[dict]:
    """Фиксированное baseline-окно для идущих экспериментов без окон.

    Ставится только baseline: окно до старта целиком в прошлом, и Вебмастер
    отдаёт его полным обходом по произвольным датам. Экспериментам, у которых
    окна уже заданы (заведены через activate), ничего не меняется — задним
    числом переписывать измеритель идущего эксперимента нельзя.
    """
    done = []
    for exp in reg.get("experiments", []):
        if exp.get("status") not in ("running", "observing"):
            continue
        if (exp.get("windows") or {}).get("baseline"):
            continue
        if not exp.get("start"):
            continue
        planned = st.plan_windows(dt.date.fromisoformat(exp["start"]))
        exp["windows"] = {"days": planned["days"],
                          "baseline": planned["baseline"],
                          "experiment": None}
        exp["windows_backfilled"] = today.isoformat()
        done.append(exp)
        w = planned["baseline"]
        print(f"{exp['id']}: baseline {w['from']}–{w['to']} "
              f"(старт {exp['start']}), окно после остаётся скользящим")
    return done


def windows_due(reg: dict, today: dt.date) -> list[tuple[dict, str, dict]]:
    """Окна, которые пора выгрузить: (эксперимент, роль окна, окно)."""
    due = []
    for exp in reg.get("experiments", []):
        if exp.get("status") not in ("running", "observing"):
            continue
        windows = exp.get("windows") or {}
        for role in ("baseline", "experiment"):
            w = windows.get(role)
            if not w:
                continue
            if st.window_path(w["from"], w["to"]).exists():
                continue
            if st.window_ready(w, today):
                due.append((exp, role, w))
    return due


def fetch_window(w: dict, today: dt.date, fetcher) -> pathlib.Path:
    """Выгрузить окно в файл; fetcher(date_from, date_to) → popular_queries."""
    pq = fetcher(dt.date.fromisoformat(w["from"]), dt.date.fromisoformat(w["to"]))
    out = {"date": today.isoformat(), "window_kind": "fixed",
           "window": {"from": w["from"], "to": w["to"]},
           "popular_queries": {"date_from": w["from"], "date_to": w["to"], **pq}}
    path = st.window_path(w["from"], w["to"])
    path.parent.mkdir(parents=True, exist_ok=True)
    if pq.get("error") or not pq.get("queries"):
        # Файл с ошибкой не пишем: пустой файл выглядел бы как выгруженное
        # окно и навсегда снял бы его с очереди.
        raise RuntimeError(f"окно {w['from']}–{w['to']}: "
                           f"{pq.get('error') or 'пустой ответ'}")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def webmaster_fetcher():
    """Выгрузка через сборщик collect.py (токен — YANDEX_WEBMASTER_TOKEN)."""
    import collect
    headers = collect.webmaster_headers()
    host, err = collect.resolve_host(headers)
    if err:
        raise RuntimeError(err)

    def fetcher(date_from: dt.date, date_to: dt.date) -> dict:
        return collect.fetch_popular_queries(
            headers, host["uid"], host["host_id"], date_from, date_to)
    return fetcher


def fetch(reg: dict, today: dt.date, fetcher=None) -> list[pathlib.Path]:
    due = windows_due(reg, today)
    if not due:
        print("окон к выгрузке нет")
        return []
    fetcher = fetcher or webmaster_fetcher()
    written = []
    for exp, role, w in due:
        try:
            path = fetch_window(w, today, fetcher)
        except RuntimeError as err:
            print(f"{exp['id']} ({role}): {err}", file=sys.stderr)
            continue
        written.append(path)
        print(f"{exp['id']} ({role}): {path}")
    return written


# ── CLI ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("command",
                    choices=("activate", "fetch", "backfill", "validate"))
    ap.add_argument("--date", default=dt.date.today().isoformat(),
                    help="дата прогона (ISO), по умолчанию сегодня")
    ap.add_argument("--registry", default=str(REGISTRY))
    ap.add_argument("--site", default=SITE)
    args = ap.parse_args(argv)
    today = dt.date.fromisoformat(args.date)
    path = pathlib.Path(args.registry)
    reg = load_registry(path)
    if args.command == "activate":
        if activate(reg, today, args.site):
            save_registry(reg, path)
        return 0
    if args.command == "validate":
        import experiments
        experiments.REGISTRY = path
        issues = experiments.registry_issues(args.date)
        for line in issues:
            print(line)
        if not issues:
            print("реестр в порядке: правило порога экспозиции соблюдено")
        return 1 if issues else 0
    if args.command == "backfill":
        if backfill(reg, today):
            save_registry(reg, path)
        else:
            print("экспериментов без фиксированного baseline нет")
        return 0
    fetch(reg, today)
    return 0


if __name__ == "__main__":
    sys.exit(main())
