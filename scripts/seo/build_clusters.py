#!/usr/bin/env python3
"""Сборка плана запросов к Вордстату из каталога вендоров сайта.

Читает src/data/vendors.ts (slug, vendor) и reports/seo/semantics/clusters.json
(ручные кластеры и приоритеты), пишет план запросов: seed-фраза + коммерческие
модификаторы на каждую карточку товара.

Запуск: python3 scripts/seo/build_clusters.py [--limit N]
Результат: reports/seo/semantics/plan.json
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

VENDORS_TS = pathlib.Path("src/data/vendors.ts")
MANUAL = pathlib.Path("reports/seo/semantics/clusters.json")
OUT = pathlib.Path("reports/seo/semantics/plan.json")

# Модификаторы коммерческого интента: то, что ищет покупатель на юрлицо.
MODIFIERS = [
    "купить",
    "оплата",
    "для юридических лиц",
    "тариф",
    "подписка",
    "лицензия",
]

# Латиница бренда как якорь релевантности: русские транслитерации («корел»,
# «корал») тянут омонимы — «корал тревел», «пионы корал шарм», «корела водка».
# Проверено на замере 19.08.2026, поэтому транслитерации не используются.
# Исключение — продуктовые названия, под которыми товар реально ищут.
PRODUCT_NAMES = {
    "blackmagic": "davinci resolve",
    "marmoset": "marmoset toolbag",
    "unreal-engine": "unreal engine",
    "clip-studio-paint": "clip studio paint",
    "marvelous-designer": "marvelous designer",
    "native-instruments": "native instruments",
    "epidemic-sound": "epidemic sound",
    "astute-graphics": "astute graphics",
    "boris-fx": "boris fx",
    "topaz-labs": "topaz labs",
    "motion-array": "motion array",
}


def vendors() -> list[dict]:
    text = VENDORS_TS.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"\{\s*slug:\s*'([^']+)',\s*vendor:\s*'([^']+)'", text):
        out.append({"slug": m.group(1), "vendor": m.group(2)})
    return out


def main() -> int:
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    manual = json.loads(MANUAL.read_text(encoding="utf-8"))
    priority = {c["cluster"]: c.get("priority", 9) for c in manual["clusters"]}
    seeds = {c["cluster"]: c["seed"] for c in manual["clusters"]}

    plan: list[dict] = []
    for v in vendors():
        slug, name = v["slug"], v["vendor"]
        base = PRODUCT_NAMES.get(slug) or seeds.get(slug) or name.lower()
        phrases = [base] + [f"{base} {mod}" for mod in MODIFIERS]
        plan.append({
            "cluster": slug,
            "vendor": name,
            "page": f"/vendors/{slug}",
            "priority": priority.get(slug, 3),
            "relevance_token": base.split()[0],
            "phrases": phrases,
        })

    # Ручные тематические кластеры без карточки товара.
    for c in manual["clusters"]:
        if c.get("page") is None:
            plan.append({
                "cluster": c["cluster"],
                "vendor": None,
                "page": None,
                "priority": c.get("priority", 3),
                "relevance_token": c["seed"].split()[0],
                "phrases": [c["seed"]] + [f"{c['seed']} {m}" for m in MODIFIERS[:3]],
            })

    plan.sort(key=lambda c: (c["priority"], c["cluster"]))
    if limit:
        plan = plan[:limit]

    total = sum(len(c["phrases"]) for c in plan)
    OUT.write_text(json.dumps({
        "schema_version": "1.0.0",
        "region_id": manual.get("region_id", "225"),
        "region_name": manual.get("region_name", "Россия"),
        "modifiers": MODIFIERS,
        "clusters": plan,
        "planned_requests": total,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"план: {OUT} — кластеров {len(plan)}, запросов {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
