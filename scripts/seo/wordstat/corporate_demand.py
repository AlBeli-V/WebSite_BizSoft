#!/usr/bin/env python3
"""Целевой замер корпоративного спроса по вендорам каталога.

Решение руководителя 21.09.2026: рекламировать только те формулировки, по
которым к нам приходят заявки. Формулировки известны из запросов
Вебмастера — «оплата <вендор> юридическим лицом», «купить <вендор> для
компании», «корпоративная подписка <вендор>». Неизвестно другое: у каких
вендоров такой спрос вообще есть и насколько он велик.

Почему отдельный прогон, а не обычный сбор. Планировщик обычного сбора
оптимизирует прирост числа фраз: gain = продуктивность × новизна ×
(1 − вероятность дубля), где новизна падает до нуля, когда по вендору уже
известно много фраз. Для крупных вендоров это и произошло — прогон 21.09
сделал 114 вызовов и не добавил ни одной фразы, а новые корпоративные
формы до плана не дошли вовсе. Здесь вопрос другой: не «сколько фраз
прибавится», а «есть ли спрос по этой конкретной форме», и насыщенность
вендора ему не помеха.

Прогон дешёвый: три вызова на вендора, кэш общий с основным сбором,
бюджет и ограничитель частоты — те же.

Запуск: python3 scripts/seo/wordstat/corporate_demand.py [--limit N]
        [--dry-run] [--min-frequency N]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import budget as budget_mod  # noqa: E402
import client as client_mod  # noqa: E402
import config  # noqa: E402
import discovery as D  # noqa: E402

OUT = pathlib.Path("reports/seo/wordstat/corporate-demand.json")
# Формы взяты из запросов Вебмастера, по которым к нам приходили заявки.
FORMS = [
    "оплата {vendor} юридическим лицом",
    "купить {vendor} для компании",
    "корпоративная подписка {vendor}",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="сколько вендоров взять (0 — все)")
    ap.add_argument("--min-frequency", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = config.load()
    date = config.today_msk()
    # Вендоры сайта плюс те, у кого своя страница: список тот же, что у
    # основного сбора, иначе замер разойдётся с каталогом.
    vendors = D.site_vendors() + D.bespoke_landings()
    if args.limit:
        vendors = vendors[:args.limit]
    print(f"Вендоров: {len(vendors)}; форм: {len(FORMS)}; вызовов: {len(vendors) * len(FORMS)}")
    if args.dry_run:
        for v in vendors[:5]:
            for f in FORMS:
                print("  " + f.format(vendor=v["anchor"]))
        print("  …")
        return 0

    # Результат кладётся в свой файл, а не в общую базу семантики. Проба
    # показала, почему: кластер там определяется по совпадению с якорем
    # вендора, и фраза «оплата capture one юридическим лицом» заводит
    # собственный кластер вместо capture-one. Триста таких записей засорили
    # бы семантику SEO-контура ради задачи рекламы. Отбор целей читает оба
    # источника сам.
    budget = budget_mod.BudgetController(cfg, today=date)
    client = client_mod.WordstatClient(budget, cfg)

    found, empty, calls = [], 0, 0
    for vendor in vendors:
        for form in FORMS:
            phrase = form.format(vendor=vendor["anchor"])
            res = client.top(phrase, reason="decision_validation", cluster=vendor["slug"])
            calls += 1
            rows = ((res.get("data") or {}).get("topRequests") or []) if res.get("data") else []
            if not rows:
                empty += 1
                continue
            for row in rows:
                text = (row.get("phrase") or "").strip()
                freq = int(row.get("count") or 0)
                if not text or freq < args.min_frequency:
                    continue
                found.append({"phrase": text, "frequency": freq, "form": form,
                              "vendor": vendor["vendor"], "slug": vendor["slug"],
                              "category": vendor.get("category"),
                              "url": vendor.get("url")})

    found.sort(key=lambda r: -r["frequency"])
    by_vendor: dict[str, int] = {}
    for r in found:
        by_vendor[r["vendor"]] = by_vendor.get(r["vendor"], 0) + r["frequency"]

    print(f"\nВызовов: {calls}; пустых ответов: {empty}; найдено фраз: {len(found)}")
    print(f"Суммарный корпоративный спрос: {sum(r['frequency'] for r in found)} в месяц\n")
    print("== Вендоры с корпоративным спросом ==")
    for vendor, total in sorted(by_vendor.items(), key=lambda kv: -kv[1])[:25]:
        top = [r for r in found if r["vendor"] == vendor][:3]
        print(f"  {vendor:24} {total:6} в месяц")
        for r in top:
            print(f"      {r['frequency']:5}  {r['phrase']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "date": date, "forms": FORMS, "calls": calls, "empty": empty,
        "phrases": found,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nСохранено: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
