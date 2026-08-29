#!/usr/bin/env python3
"""Discovery Engine: формирование seed-фраз и управляемое расширение.

Главное отличие от прежней реализации: вызов делается не потому, что фраза есть
в шаблоне, а потому что от него ожидается прирост информации. Аудит показал, что
37 % вызовов возвращали пустой ответ — шаблоны применялись ко всем вендорам
подряд, включая те, у которых частотности нет вовсе.

Ожидаемый прирост оценивается до вызова по трём признакам:
  сколько нового дали похожие seed этого же вендора;
  насколько шаблон вообще продуктивен по накопленной статистике;
  покрыт ли кластер сайтом (непокрытый ценнее).

Расширение ограничено глубиной, лимитами на вендора и кластер и остановкой seed
после нескольких подряд неинформативных ответов.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import normalize as N  # noqa: E402

VENDORS_TS = pathlib.Path("src/data/vendors.ts")
STATS_PATH = pathlib.Path("reports/seo/wordstat/pattern-stats.json")

# Шаблоны отсортированы по ожидаемой продуктивности; статистика уточняет её фактом.
# Формы шаблонов совпадают с теми, по которым есть замеры, иначе накопленная
# статистика продуктивности к ним не применима. Априорные оценки взяты из
# фактических долей непустых ответов на 270 вызовах (импорт 20.08.2026):
# {vendor} 100 %, купить 95 %, подписка 78 %, лицензия 69 %, оплата 54 %,
# тариф 38 %, «для юридических лиц» 5 % — последний шаблон почти всегда пуст,
# потому что вендорское имя вместе с «для юридических лиц» люди не набирают.
PATTERNS = [
    ("{vendor}", 1.00, "бренд целиком: даёт основную массу связанных фраз"),
    ("{vendor} купить", 0.95, "прямой покупательский интент"),
    ("{vendor} подписка", 0.78, "продление и подписка"),
    ("{vendor} лицензия", 0.69, "лицензионный интент"),
    ("{vendor} оплата", 0.54, "оплата из России — наша основная услуга"),
    ("{vendor} цена", 0.50, "ценовой интент, замеров пока нет"),
    ("{vendor} тариф", 0.38, "тарифные запросы, часто ниже порога"),
    # Слой «Аналоги X» (этап 2, 29.08.2026): спрос на замену измеряется до
    # создания страниц-аналогов — страница строится только по замеренному
    # кластеру, а не по списку из конкурентного анализа.
    ("{vendor} аналог", 0.50, "спрос на замену: очередь слоя страниц «аналоги X»"),
    ("{vendor} для юридических лиц", 0.05,
     "почти всегда пусто: вендорское имя с этой формулировкой не ищут"),
]
PRODUCT_NAMES = {
    "blackmagic": "davinci resolve", "marmoset": "marmoset toolbag",
    "unreal-engine": "unreal engine", "clip-studio-paint": "clip studio paint",
    "marvelous-designer": "marvelous designer", "native-instruments": "native instruments",
    "epidemic-sound": "epidemic sound", "astute-graphics": "astute graphics",
    "boris-fx": "boris fx", "topaz-labs": "topaz labs", "motion-array": "motion array",
}


SITE_CONFIG_TS = pathlib.Path("src/config/site.ts")
CANDIDATES_TS = pathlib.Path("reports/seo/wordstat/vendor-candidates.json")


def bespoke_landings() -> list[dict]:
    """Вендоры с отдельной страницей: их нет в vendors.ts, но они есть на сайте.

    Zoom, JetBrains, OpenAI и Figma живут в собственных .astro-страницах и
    перечислены только в site.ts. Без них система считала их «отсутствующими
    в каталоге» и предлагала завести заново.
    """
    if not SITE_CONFIG_TS.exists():
        return []
    text = SITE_CONFIG_TS.read_text(encoding="utf-8")
    start = text.find("export const vendorLandings")
    if start < 0:
        return []
    block = text[start:text.find("];", start)]
    out = []
    for m in re.finditer(r"\{\s*slug:\s*'([^']+)',\s*name:\s*'([^']+)'", block):
        slug, name = m.group(1), m.group(2)
        out.append({"slug": slug, "vendor": name, "category": "",
                    "anchor": PRODUCT_NAMES.get(slug, name.lower()),
                    "url": f"/vendors/{slug}"})
    return out


def site_vendors() -> list[dict]:
    """Вендоры каталога: источник seed-фраз и якорей релевантности."""
    if not VENDORS_TS.exists():
        return []
    text = VENDORS_TS.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(
            r"\{\s*slug:\s*'([^']+)',\s*vendor:\s*'([^']+)'.*?catLabel:\s*'([^']*)'",
            text, re.S):
        slug, name, category = m.group(1), m.group(2), m.group(3)
        out.append({"slug": slug, "vendor": name, "category": category,
                    "anchor": PRODUCT_NAMES.get(slug, name.lower()),
                    "url": f"/vendors/{slug}"})
    known = {v["slug"] for v in out}
    out.extend(v for v in bespoke_landings() if v["slug"] not in known)
    return out


def product_of() -> dict[str, str]:
    """Продукт → имя вендора каталога. Единый источник — конфиг кандидатов.

    Карта была только у проверки каталога, а связывание семантики со
    страницами о ней не знало. Из-за этого «claude купить», «gemini купить»
    и «microsoft 365 купить» попадали в непокрытый спрос: страницы вендоров
    существуют, но называются anthropic, google и microsoft, а кластер ищет
    страницу по имени продукта. Руководитель видел в отчёте предложение
    завести то, что заведено давно.
    """
    if not CANDIDATES_TS.exists():
        return {}
    try:
        data = json.loads(CANDIDATES_TS.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return {k.lower(): str(v).lower() for k, v in (data.get("product_of") or {}).items()}


def vendor_index(vendors: list[dict]) -> dict[str, str]:
    """Якорь → кластер: по нему фраза относится к вендору.

    Кроме собственного имени вендора в индекс попадают имена его продуктов:
    покупатель ищет «claude», а страница называется /vendors/anthropic.
    """
    index = {v["anchor"]: v["slug"] for v in vendors}
    by_name = {}
    for v in vendors:
        by_name[v["vendor"].lower()] = v["slug"]
        by_name[v["slug"].replace("-", " ").lower()] = v["slug"]
    for product, vendor in product_of().items():
        slug = by_name.get(vendor)
        if slug and product not in index:
            index[product] = slug
    return index


def vendor_urls(vendors: list[dict]) -> dict[str, str]:
    """Кластер → адрес страницы на сайте."""
    return {v["slug"]: v["url"] for v in vendors}


class PatternStats:
    """Накопленная продуктивность шаблонов: чем чаще пусто, тем ниже приоритет."""

    def __init__(self, path: pathlib.Path | None = None):
        self.path = path or STATS_PATH
        self.data = (json.loads(self.path.read_text(encoding="utf-8"))
                     if self.path.exists() else {})

    def record(self, pattern: str, *, ok: bool, unique_new: int) -> None:
        d = self.data.setdefault(pattern, {"calls": 0, "empty": 0, "unique_new": 0})
        d["calls"] += 1
        d["empty"] += 0 if ok else 1
        d["unique_new"] += unique_new

    def productivity(self, pattern: str, prior: float) -> float:
        """Доля непустых ответов; при малой статистике доверяем априорной оценке."""
        d = self.data.get(pattern)
        if not d or d["calls"] < 5:
            return prior
        observed = 1 - d["empty"] / d["calls"]
        weight = min(1.0, d["calls"] / 20)
        return round(prior * (1 - weight) + observed * weight, 3)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1),
                             encoding="utf-8")


def seed_phrase(pattern: str, vendor: dict) -> str:
    return pattern.format(vendor=vendor["anchor"])


def information_gain(*, pattern: str, vendor: dict, universe, stats: PatternStats,
                     prior: float, covered_clusters: set[str]) -> dict:
    """Ожидаемый прирост информации от вызова: до вызова, а не после.

    Оценка сознательно грубая — она нужна, чтобы не тратить слот квоты на заведомо
    пустой или дублирующий запрос, а не чтобы предсказать точное число фраз.
    """
    phrase = seed_phrase(pattern, vendor)
    productivity = stats.productivity(pattern, prior)

    # Сколько фраз этого вендора уже известно: чем больше, тем меньше нового.
    known = [r for r in universe.rows.values() if r.get("cluster") == vendor["slug"]]
    saturation = min(1.0, len(known) / 250)
    novelty = 1.0 - saturation

    # Уже собранный этим же seed запрос нового не даст.
    seen_seed = any(r.get("source_seed") == phrase for r in known)
    duplicate_probability = 0.9 if seen_seed else round(saturation * 0.6, 3)

    # Непокрытый сайтом кластер ценнее покрытого.
    coverage_bonus = 1.0 if vendor["slug"] not in covered_clusters else 0.7

    gain = round(productivity * novelty * coverage_bonus * (1 - duplicate_probability), 4)
    return {
        "phrase": phrase,
        "pattern": pattern,
        "expected_information_gain": gain,
        "productivity": productivity,
        "novelty": round(novelty, 3),
        "duplicate_probability": duplicate_probability,
        "coverage_bonus": coverage_bonus,
        "known_phrases": len(known),
    }


def build_seed_plan(vendors: list[dict], universe, stats: PatternStats,
                    covered_clusters: set[str], thresholds: dict) -> list[dict]:
    """План seed-вызовов, отсортированный по ожидаемому приросту информации."""
    plan = []
    for vendor in vendors:
        per_vendor = 0
        for pattern, prior, why in PATTERNS:
            if per_vendor >= thresholds["max_calls_per_vendor"]:
                break
            ig = information_gain(pattern=pattern, vendor=vendor, universe=universe,
                                  stats=stats, prior=prior,
                                  covered_clusters=covered_clusters)
            if ig["expected_information_gain"] < thresholds["min_information_gain"]:
                continue
            plan.append({**ig, "vendor": vendor["vendor"], "cluster": vendor["slug"],
                         "category": vendor["category"], "url": vendor["url"],
                         "rationale": why, "depth": 0})
            per_vendor += 1
    plan.sort(key=lambda p: -p["expected_information_gain"])
    return plan


def expansion_candidates(universe, covered_clusters: set[str], thresholds: dict,
                         limit: int = 50) -> list[dict]:
    """Найденные фразы, которые заслуживают стать новыми seed.

    Условия жёсткие: только коммерческий интент, заметная частотность, отсутствие
    покрытия сайтом и признак роста. Иначе расширение выродится в бесконечный обход.
    """
    out = []
    for row in universe.rows.values():
        if row.get("intent") != "commercial":
            continue
        freq = row.get("wordstat_frequency") or 0
        if freq < thresholds["min_frequency"] * 3:
            continue
        if row.get("page_exists"):
            continue
        trend = universe.trend(row["phrase"])
        growing = trend["direction"] == "growing"
        cluster_new = row.get("cluster") not in covered_clusters
        if not (growing or cluster_new):
            continue
        out.append({
            "phrase": row["phrase"],
            "cluster": row.get("cluster"),
            "frequency": freq,
            "commercial_intent": row.get("commercial_intent_score"),
            "trend": trend["direction"],
            "reason": "растущий спрос" if growing else "кластер не покрыт сайтом",
            "expected_information_gain": round(
                min(1.0, freq / 1000) * (row.get("commercial_intent_score") or 0), 4),
            "depth": 1,
        })
    out.sort(key=lambda r: -r["expected_information_gain"])
    return out[:limit]
