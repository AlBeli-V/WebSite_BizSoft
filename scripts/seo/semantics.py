#!/usr/bin/env python3
"""Gap-анализ семантики: рыночный спрос (Вордстат) против нашей видимости (Вебмастер).

Читает reports/seo/semantics/core-<дата>.json и reports/seo/intelligence/snapshots/<дата>.json,
пишет reports/seo/semantics/gap-<дата>.md и brief-<дата>.json — компактную выжимку
для приложения к письму.

Ограничение методики: наша видимость известна только по выборке топ-100 запросов
Вебмастера, поэтому «запроса нет в выборке» не равно «запроса нет совсем».
Доля голоса (наши показы к рыночным) не считается до закрытия DATA-001.

Запуск: python3 scripts/seo/semantics.py [YYYY-MM-DD]
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

SEM_DIR = pathlib.Path("reports/seo/semantics")
SNAP_DIR = pathlib.Path("reports/seo/intelligence/snapshots")
MIN_DEMAND = 30
TOP_GAPS = 10
TOP_CLUSTERS = 25


def fmt(n) -> str:
    if n is None:
        return "нет данных"
    return f"{n:,}".replace(",", " ")


def our_queries(date: str) -> tuple[set[str], str]:
    path = SNAP_DIR / f"{date}.json"
    if not path.exists():
        return set(), "snapshot отсутствует"
    snap = json.loads(path.read_text(encoding="utf-8"))
    yandex = snap.get("yandex") or {}
    queries = {e["entity_id"].lower() for e in (yandex.get("entities") or [])
               if e.get("entity_type") == "query"}
    scope = (yandex.get("totals") or {}).get("scope_note", "охват выборки не указан")
    return queries, scope


def gaps(cluster: dict, seen: set[str]) -> list[dict]:
    out = [p for p in cluster.get("phrases", [])
           if p["intent"] == "commercial"
           and (p["impressions_wordstat"] or 0) >= MIN_DEMAND
           and p["phrase"].lower() not in seen]
    return out[:TOP_GAPS]


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    core_path = SEM_DIR / f"core-{date}.json"
    if not core_path.exists():
        print(f"нет данных Вордстата: {core_path}", file=sys.stderr)
        return 1
    core = json.loads(core_path.read_text(encoding="utf-8"))
    seen, scope = our_queries(date)
    src, quota = core["source"], core["quota"]

    lines: list[str] = []
    a = lines.append
    a(f"# Спрос и разрывы семантики — {date}")
    a("")
    a(f"**Источник спроса:** Вордстат, регион {src['region_name']} ({src['region_id']}), "
      f"{src['window']}, соответствие широкое, устройства все. Единица — {src['unit']}.")
    a(f"**Источник нашей видимости:** Яндекс.Вебмастер, {scope}.")
    a(f"**Расход API:** {quota['requests_made']} запросов за прогон "
      f"(потолок прогона {quota['run_cap']}, месячный бюджет {quota['monthly_budget']}), "
      f"ошибок {quota['failures']}.")
    a("")
    a("ФАКТ — числа обоих источников. ИНТЕРПРЕТАЦИЯ — вывод о разрыве. Показы Вордстата "
      "не переносятся на Google и не равны заявкам или выручке. Доля голоса не "
      "рассчитывается: охват и периоды источников не сверены (DATA-001).")
    a("")

    measured = [c for c in core["clusters"] if c["status"] == "ok"]
    ranked = sorted(measured, key=lambda c: -(c.get("commercial_impressions") or 0))

    a("## Коммерческий спрос по карточкам товара")
    a("")
    a("Отсортировано по сумме показов коммерческих фраз — это и есть покупательский "
      "спрос, в отличие от общей частотности бренда.")
    a("")
    a("| Карточка | Коммерческий спрос | Общий спрос по бренду | Коммерческих фраз |")
    a("|---|---|---|---|")
    for c in ranked[:TOP_CLUSTERS]:
        page = c.get("page") or "страницы нет"
        a(f"| {c['cluster']} ({page}) | {fmt(c.get('commercial_impressions'))} | "
          f"{fmt(c.get('seed_impressions'))} | {c.get('commercial_phrases', 0)} |")
    a("")

    a("## Разрывы: спрос есть, запроса нет в нашей выборке")
    a("")
    a(f"Коммерческие фразы от {MIN_DEMAND} показов в месяц, которых нет в выборке "
      "топ-100 запросов Вебмастера. Отсутствие в выборке не доказывает нулевую "
      "видимость — это список кандидатов на доработку страницы.")
    a("")
    gap_index: dict[str, list[dict]] = {}
    for c in ranked:
        if not c.get("page"):
            continue
        rows = gaps(c, seen)
        if not rows:
            continue
        gap_index[c["cluster"]] = rows
        a(f"### {c['cluster']} → {c['page']}")
        a("")
        a("| Фраза | Показы/мес |")
        a("|---|---|")
        for p in rows:
            a(f"| {p['phrase']} | {fmt(p['impressions_wordstat'])} |")
        a("")
    if not gap_index:
        a("Разрывов выше порога не обнаружено.")
        a("")

    disc = [d for d in core.get("discovery", [])
            if d["status"] == "ok" and (d.get("demand") or 0) >= MIN_DEMAND]
    a("## Разведка рынка: товары, которых у нас нет")
    a("")
    a("Бренды вне каталога с измеренным спросом на покупку для юрлица.")
    a("")
    if disc:
        a("| Бренд | Спрос по фразе покупки | Топ коммерческих формулировок |")
        a("|---|---|---|")
        for d in sorted(disc, key=lambda x: -(x["demand"] or 0))[:30]:
            top = "; ".join(f"{p['phrase']} — {fmt(p['impressions_wordstat'])}"
                            for p in (d.get("top_commercial") or [])[:3]) or "—"
            a(f"| {d['brand']} | {fmt(d['demand'])} | {top} |")
    else:
        a("Кандидатов выше порога нет.")
    a("")

    seasons = [s for s in core.get("seasonality", []) if s["status"] == "ok"]
    a("## Сезонность и география")
    a("")
    a(f"Помесячная динамика собрана по {len(seasons)} кластерам, "
      f"региональный срез — по {len([g for g in core.get('geography', []) if g['status'] == 'ok'])}. "
      "Данные лежат в core-файле и используются для выбора момента правок, "
      "а не для выводов о росте: месяц к месяцу сравнивается только с поправкой на сезон.")
    a("")

    a("## Ограничения")
    a("")
    a("- Вордстат измеряет показы в поиске Яндекса за 30 дней: это спрос, не продажи.")
    a("- Частотность зависит от региона, типа соответствия и сезона; зафиксированы "
      f"регион {src['region_name']}, широкое соответствие, все устройства.")
    a("- Данные Яндекса не переносятся на Google.")
    a("- Пустой ответ API означает частотность ниже порога выдачи, а не ноль.")
    a("- Высокий общий спрос по бренду не означает покупательский интент: проверяйте "
      "колонку коммерческого спроса.")
    a("")

    SEM_DIR.mkdir(parents=True, exist_ok=True)
    (SEM_DIR / f"gap-{date}.md").write_text("\n".join(lines), encoding="utf-8")

    brief = {
        "report_date": date,
        "region": src["region_name"],
        "requests_made": quota["requests_made"],
        "clusters_measured": len(measured),
        "top_commercial": [
            {"cluster": c["cluster"], "page": c.get("page"),
             "commercial_impressions": c.get("commercial_impressions"),
             "seed_impressions": c.get("seed_impressions")}
            for c in ranked[:10]],
        "gaps": {k: [{"phrase": p["phrase"], "impressions": p["impressions_wordstat"]}
                     for p in v] for k, v in gap_index.items()},
        "discovery": [{"brand": d["brand"], "demand": d["demand"]}
                      for d in sorted(disc, key=lambda x: -(x["demand"] or 0))[:15]],
    }
    (SEM_DIR / f"brief-{date}.json").write_text(
        json.dumps(brief, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"gap-анализ: {SEM_DIR}/gap-{date}.md; выжимка: brief-{date}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
