#!/usr/bin/env python3
"""Gap-анализ семантики: рыночный спрос (Вордстат) против нашей видимости (Вебмастер).

Читает reports/seo/semantics/core-<дата>.json и reports/seo/intelligence/snapshots/<дата>.json,
пишет reports/seo/semantics/gap-<дата>.md.

Ограничение, зафиксированное в методике: наша видимость известна только по выборке
топ-100 запросов Вебмастера, поэтому «запроса нет в выборке» не равно «запроса нет
совсем». Отношение «наши показы / показы Вордстата» не считается до закрытия DATA-001:
источники не сверены по охвату и периодам.

Запуск: python3 scripts/seo/semantics.py [YYYY-MM-DD]
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

SEM_DIR = pathlib.Path("reports/seo/semantics")
SNAP_DIR = pathlib.Path("reports/seo/intelligence/snapshots")
MIN_DEMAND = 30      # ниже — сигнал слабый, в выводы не идёт
TOP_GAPS = 8         # сколько разрывов показывать на кластер


def our_queries(date: str) -> tuple[list[str], str]:
    path = SNAP_DIR / f"{date}.json"
    if not path.exists():
        return [], "snapshot отсутствует"
    snap = json.loads(path.read_text(encoding="utf-8"))
    yandex = snap.get("yandex") or {}
    entities = [e for e in (yandex.get("entities") or []) if e.get("entity_type") == "query"]
    scope = (yandex.get("totals") or {}).get("scope_note", "охват выборки не указан")
    return [e["entity_id"].lower() for e in entities], scope


def gaps(cluster: dict, seen: list[str]) -> list[dict]:
    out = []
    for p in cluster.get("phrases", []):
        if p["intent"] != "commercial":
            continue
        if (p["impressions_wordstat"] or 0) < MIN_DEMAND:
            continue
        if any(p["phrase"].lower() == q for q in seen):
            continue
        out.append(p)
    out.sort(key=lambda p: -(p["impressions_wordstat"] or 0))
    return out[:TOP_GAPS]


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    core_path = SEM_DIR / f"core-{date}.json"
    if not core_path.exists():
        print(f"нет данных Вордстата: {core_path}", file=sys.stderr)
        return 1
    core = json.loads(core_path.read_text(encoding="utf-8"))
    seen, scope = our_queries(date)
    src = core["source"]

    lines: list[str] = []
    a = lines.append
    a(f"# Спрос и разрывы семантики — {date}")
    a("")
    a(f"**Источник спроса:** Вордстат, регион {src['region_name']} ({src['region_id']}), "
      f"{src['window']}, соответствие широкое, устройства все. "
      f"Единица — {src['unit']}.")
    a(f"**Источник нашей видимости:** Яндекс.Вебмастер, {scope}.")
    a("")
    a("ФАКТ — числа обоих источников. ИНТЕРПРЕТАЦИЯ — вывод о разрыве. "
      "Показы Вордстата не переносятся на Google и не равны заявкам или выручке. "
      "Доля голоса (наши показы к рыночным) не рассчитывается: охват и периоды "
      "источников не сверены (DATA-001).")
    a("")

    a("## Спрос по кластерам")
    a("")
    a("| Кластер | Наша страница | Спрос, показы/мес | Коммерческих фраз | Статус |")
    a("|---|---|---|---|---|")
    for c in core["clusters"]:
        demand = c.get("total_impressions")
        demand_txt = f"{demand:,}".replace(",", " ") if demand is not None else "нет данных"
        page = c.get("page") or "—"
        status = {"ok": "измерено",
                  "below_threshold": "ниже порога выдачи",
                  "quota_exceeded": "квота исчерпана"}.get(c["status"], c["status"])
        a(f"| {c['cluster']} | {page} | {demand_txt} | "
          f"{c.get('commercial_phrases', 0)} | {status} |")
    a("")

    a("## Разрывы: спрос есть, запроса нет в нашей выборке")
    a("")
    a(f"Коммерческие фразы с частотностью от {MIN_DEMAND} показов, которых нет "
      "в выборке топ-100 запросов Вебмастера. Отсутствие в выборке не доказывает "
      "нулевую видимость — это список кандидатов на проверку и доработку страницы.")
    a("")
    any_gap = False
    for c in core["clusters"]:
        if c["status"] != "ok" or not c.get("page"):
            continue
        rows = gaps(c, seen)
        if not rows:
            continue
        any_gap = True
        a(f"### {c['cluster']} → {c['page']}")
        a("")
        a("| Фраза | Показы/мес |")
        a("|---|---|")
        for p in rows:
            a(f"| {p['phrase']} | {p['impressions_wordstat']} |")
        a("")
    if not any_gap:
        a("Разрывов выше порога не обнаружено.")
        a("")

    a("## Кандидаты на новые страницы")
    a("")
    a("Кластеры с измеренным спросом, под которые своей страницы нет.")
    a("")
    cands = [c for c in core["clusters"]
             if not c.get("page") and c["status"] == "ok"
             and (c.get("total_impressions") or 0) >= MIN_DEMAND]
    if cands:
        a("| Кластер | Спрос, показы/мес | Топ коммерческих фраз |")
        a("|---|---|---|")
        for c in sorted(cands, key=lambda x: -(x["total_impressions"] or 0)):
            top = [p for p in c["phrases"] if p["intent"] == "commercial"][:3]
            txt = "; ".join(f"{p['phrase']} — {p['impressions_wordstat']}" for p in top) or "—"
            a(f"| {c['cluster']} | {c['total_impressions']} | {txt} |")
    else:
        a("Кандидатов выше порога нет.")
    a("")

    a("## Ограничения")
    a("")
    a("- Вордстат измеряет показы в поиске Яндекса за 30 дней; это спрос, а не продажи.")
    a("- Частотность зависит от региона, типа соответствия и сезона; здесь зафиксированы "
      f"регион {src['region_name']}, широкое соответствие, все устройства.")
    a("- Данные Яндекса не переносятся на Google.")
    a("- Пустой ответ API означает частотность ниже порога выдачи, а не ноль.")
    a("")

    SEM_DIR.mkdir(parents=True, exist_ok=True)
    out = SEM_DIR / f"gap-{date}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"gap-анализ: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
