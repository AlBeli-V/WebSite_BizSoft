#!/usr/bin/env python3
"""Замер доминирования бренда для омонимичных имён.

Задача. У части вендоров имя — обычное слово: Zoom, Box, Unity, Spine, Rive.
Вордстат по такому имени отдаёт вперемешку лицензии и посторонний товар, и
голая фраза «<бренд> купить» не относится ни к тому, ни к другому однозначно.

Прежде выбор делался жёстко: фраза без признака софта выбрасывалась. Это
теряло головной коммерческий запрос вендора — «zoom купить» (7 960/мес) при
существующем лендинге /vendors/zoom. Обратное решение — засчитывать голую
фразу бренду — не лучше: замер 21.08.2026 показал, что в пространстве имени
«zoom» на 4 568 софтверных показов приходится 119 964 посторонних
(кроссовки Nike Air Zoom, отбеливание зубов), то есть 96 % чужие.

Поэтому решение не принимается на глаз, а измеряется. Для каждого омонима
считается доля софтверных показов среди тех фраз, где значение однозначно:

    dominance = софт / (софт + посторонние)

Бренд считается доминирующим при доле от `MIN_SHARE` и объёме от `MIN_SOFT`
показов — иначе голая фраза остаётся неатрибутируемой и в коммерческий спрос
не входит. Результат — данные, а не код: его видно в репозитории, его можно
пересчитать и оспорить.

Запуск: python3 scripts/seo/wordstat/brand_dominance.py
Результат: reports/seo/wordstat/brand-dominance.json
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import normalize as N  # noqa: E402

UNIVERSE = pathlib.Path("reports/seo/wordstat/semantic-universe.jsonl")
OUT = pathlib.Path("reports/seo/wordstat/brand-dominance.json")

MIN_SHARE = 0.70   # ниже — значение имени делят с посторонним товаром
MIN_SOFT = 200     # ниже — выборка слишком мала, чтобы делать вывод


def alien(phrase: str) -> bool:
    low = N.normalize(phrase)
    return any(x in low for x in N.FOREIGN_BRANDS + N.PHYSICAL_GOODS + N.DEVICE_LINES)


def measure(rows: list[dict]) -> dict:
    out = {}
    for brand in sorted(N.AMBIGUOUS_BRANDS):
        hits = [r for r in rows if brand in N._phrase_words(r["phrase"])]
        soft = sum(r.get("wordstat_frequency") or 0
                   for r in hits if N.has_software_marker(r["phrase"]))
        other = sum(r.get("wordstat_frequency") or 0 for r in hits if alien(r["phrase"]))
        total = soft + other
        share = round(soft / total, 4) if total else None
        out[brand] = {
            "phrases": len(hits),
            "software_impressions": soft,
            "alien_impressions": other,
            "dominance": share,
            "brand_dominant": bool(share is not None and share >= MIN_SHARE
                                   and soft >= MIN_SOFT),
        }
    return out


def main() -> int:
    if not UNIVERSE.exists():
        print(f"нет универсума {UNIVERSE}", file=sys.stderr)
        return 1
    rows = [json.loads(ln) for ln in UNIVERSE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    brands = measure(rows)
    dominant = sorted(b for b, v in brands.items() if v["brand_dominant"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "note": ("Доля софтверных показов в пространстве имени омонимичного бренда. "
                 "brand_dominant=true разрешает засчитать голую фразу «<бренд> купить» "
                 "этому бренду. false означает не «спроса нет», а «принадлежность "
                 "фразы не определена»: такой спрос считается отдельно и в решения "
                 "об ассортименте не входит."),
        "thresholds": {"min_share": MIN_SHARE, "min_software_impressions": MIN_SOFT},
        "measured_from": str(UNIVERSE),
        "dominant": dominant,
        "brands": brands,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"доминирующих брендов {len(dominant)}: {', '.join(dominant)}")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
