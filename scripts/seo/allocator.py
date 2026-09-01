#!/usr/bin/env python3
"""Allocator: ≤5 действий следующей недели по ожидаемому эффекту (механика §7.9).

Каждый детектор Growth Engine видит свой срез; allocator сводит их кандидатов
к одному списку с единым скорингом

    score = сигнал_спроса × интент × вероятность × ценность / трудоёмкость

и отбирает не больше пяти. Ценность — коэффициент типа страницы/действия,
а не выдуманные деньги: чека сделки в данных нет (NO_CRM), и подставлять
его нельзя. Кандидаты, по которым действие уже открыто (actions.json)
или гипотеза уже отклонена (negative-knowledge), в список не попадают —
комитет не должен предлагать одно и то же дважды.

Запуск: python3 scripts/seo/allocator.py [YYYY-MM-DD]
Выход:  reports/seo/intelligence/allocator-<дата>.json
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

BASE = pathlib.Path("reports/seo")
OUT_DIR = BASE / "intelligence"
ACTIONS = OUT_DIR / "actions.json"
NEGATIVE = OUT_DIR / "negative-knowledge.json"
SNAPSHOTS = OUT_DIR / "snapshots"

LIMIT = 5
MAX_PER_SOURCE = 3             # один детектор не забирает всю неделю
MOMENTUM_MAX_AGE_DAYS = 8      # momentum еженедельный: старше недели — не сигнал
MOMENTUM_MIN_RECENT = 50       # ниже — малая база, «в разы» растёт шум

# Ценность по типу страницы: коммерческие точки продаж выше витрин и статей.
VALUE_BY_PAGE_TYPE = {"product": 1.0, "vendor": 1.0, "catalog": 0.7,
                      "alternatives": 0.8, "info": 0.4, "other": 0.5}


def _load_snapshot(date_s: str) -> dict:
    for back in range(0, 3):
        d = (dt.date.fromisoformat(date_s) - dt.timedelta(days=back)).isoformat()
        p = SNAPSHOTS / f"{d}.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
    return {}


def _active_keys() -> set[str]:
    """Кластеры и заголовки уже открытых действий — их не предлагаем заново."""
    keys: set[str] = set()
    if not ACTIONS.exists():
        return keys
    try:
        acts = json.loads(ACTIONS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return keys
    for a in acts if isinstance(acts, list) else acts.get("actions", []):
        if a.get("status") in ("done", "rejected", "cancelled"):
            continue
        for c in a.get("demand_clusters") or []:
            keys.add(str(c).lower())
        if a.get("title"):
            keys.add(a["title"].lower())
    return keys


def _negative_keys() -> set[str]:
    """Ключи отклонённых гипотез: не повторять доказанно не работающее."""
    if not NEGATIVE.exists():
        return set()
    try:
        data = json.loads(NEGATIVE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return {str(e.get("key", "")).lower()
            for e in data.get("entries", []) if e.get("key")}


def _page_type(path: str) -> str:
    p = (path or "").lower()
    if p.startswith("/product/"):
        return "product"
    if p.startswith("/vendors/"):
        return "vendor"
    if p.startswith("/alternatives/"):
        return "alternatives"
    if p.startswith("/catalog"):
        return "catalog"
    if p.startswith(("/blog", "/info", "/help", "/faq")):
        return "info"
    return "other"


def _norm(value: float, scale: float) -> float:
    return min(1.0, value / scale) if scale else 0.0


# ── Кандидаты из детекторов ─────────────────────────────────────────────────
# Каждый кандидат: key (дедуп), title, action, evidence, source, score-факторы.

def _from_radar(snap: dict, date_s: str) -> list[dict]:
    import opportunity
    res = opportunity.build(snap, date_s, limit=10)
    out = []
    for i in res.get("items") or []:
        out.append({
            "key": i["cluster"].lower(),
            "title": f"Запрос «{i['cluster']}»",
            "action": i["recommended_action"],
            "evidence": i["evidence"],
            "source": "радар возможностей",
            "score": i["score"],
            "confidence": i.get("confidence", "unknown"),
            "effort": i.get("effort", 2),
        })
    return out


def _from_cannibalization(date_s: str) -> list[dict]:
    import cannibalization
    res = cannibalization.build(date_s)
    if not res.get("available"):
        return []
    out, scale = [], max((i.get("impressions") or 0)
                         for i in res["items"]) if res["items"] else 0
    for i in res["items"]:
        imp = i.get("impressions") or 0
        out.append({
            "key": i["query"].lower(),
            "title": f"Каннибализация «{i['query']}»",
            "action": "выбрать каноническую страницу запроса и снять расщепление "
                      "(перелинковка, заголовки)",
            "evidence": f"{imp} показов делят {len(i.get('pages') or [])} страницы; "
                        f"вердикт: {i.get('verdict')}",
            "source": "детектор каннибализации",
            "score": round(_norm(imp, scale) * 0.8 * 0.7 / 2, 4),
            "confidence": "low",
            "effort": 2,
        })
    return out


def _from_mismatch(date_s: str) -> list[dict]:
    import mismatch
    res = mismatch.build(date_s)
    if not res.get("available"):
        return []
    out = []
    scale = max((i.get("impressions") or 0) for i in res["items"]) \
        if res["items"] else 0
    for i in res["items"]:
        imp = i.get("impressions") or 0
        out.append({
            "key": i["query"].lower(),
            "title": f"Query-page mismatch «{i['query']}»",
            "action": i.get("recommendation")
                      or "передать запрос профильной коммерческой странице",
            "evidence": f"коммерческий запрос ({imp} показов) стабильно ведёт "
                        f"на {i.get('page')} ({i.get('page_type')})",
            "source": "детектор mismatch",
            "score": round(_norm(imp, scale) * 1.0 * 0.7 / 2, 4),
            "confidence": "low",
            "effort": 2,
        })
    return out


def _from_lifecycle(date_s: str) -> list[dict]:
    import lifecycle
    res = lifecycle.build(date_s)
    if not res.get("available"):
        return []
    out = []
    declining = [i for i in res["items"] if i.get("status") == "declining"]
    scale = max((i.get("prev7") or 0) for i in declining) if declining else 0
    for i in declining:
        value = VALUE_BY_PAGE_TYPE.get(i.get("page_type") or "other", 0.5)
        out.append({
            "key": i["page"].lower(),
            "title": f"Страница увядает: {i['page']}",
            "action": "разобрать причину спада и обновить страницу "
                      "(контент, сниппет, внутренние ссылки)",
            "evidence": f"показы за 7 дн.: {i.get('last7')} против "
                        f"{i.get('prev7')} неделей раньше",
            "source": "жизненный цикл страниц",
            "score": round(_norm(i.get("prev7") or 0, scale) * 0.8 * 0.6
                           * value / 2, 4),
            "confidence": "low",
            "effort": 2,
        })
    return out


def _from_zero_impressions(date_s: str) -> list[dict]:
    import zero_impression
    res = zero_impression.build(date_s)
    if not res.get("available"):
        return []
    out = []
    for i in res["items"]:
        # молодым страницам показы ещё не положены; некоммерческие типы —
        # не дело недельного комитета
        if i.get("page_type") not in ("product", "vendor", "alternatives"):
            continue
        if (i.get("known_days") or 0) < 30:
            continue
        value = VALUE_BY_PAGE_TYPE.get(i.get("page_type"), 0.5)
        out.append({
            "key": i["path"].lower(),
            "title": f"Без показов: {i['path']}",
            "action": "проверить индексацию и качество страницы; при мёртвом "
                      "спросе — решить судьбу страницы",
            "evidence": f"коммерческая страница без показов Google минимум "
                        f"{i.get('known_days')} дн.",
            "source": "инвентарь без показов",
            "score": round(0.3 * 1.0 * 0.5 * value / 1, 4),
            "confidence": "low",
            "effort": 1,
        })
    return out


def _from_momentum(date_s: str) -> list[dict]:
    """Ускоряющийся спрос Вордстата — подготовить/усилить посадочную."""
    date = dt.date.fromisoformat(date_s)
    latest = None
    for p in sorted((BASE / "wordstat").glob("momentum-2*.json")):
        try:
            file_date = dt.date.fromisoformat(p.stem.replace("momentum-", ""))
        except ValueError:
            continue
        if 0 <= (date - file_date).days <= MOMENTUM_MAX_AGE_DAYS:
            latest = p
    if not latest:
        return []
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    items = [i for i in data.get("items") or []
             if i.get("trend") == "accelerating"
             and (i.get("recent_avg") or 0) >= MOMENTUM_MIN_RECENT]
    scale = max((i.get("recent_avg") or 0) for i in items) if items else 0
    for i in items:
        out.append({
            "key": i["phrase"].lower(),
            "title": f"Спрос ускоряется: «{i['phrase']}»",
            "action": "проверить, какая страница отвечает на запрос, и усилить "
                      "её (или подготовить посадочную)",
            "evidence": f"рыночный спрос (Вордстат): {i.get('prior_avg')} → "
                        f"{i.get('recent_avg')} показов/мес",
            "source": "momentum Вордстата",
            "score": round(_norm(i.get("recent_avg") or 0, scale)
                           * 1.0 * 0.6 * 0.8 / 2, 4),
            "confidence": "sufficient",
            "effort": 2,
        })
    return out


def _from_weak_serps(date_s: str) -> list[dict]:
    """Слабые выдачи (маркетплейсы и форумы в топе) без нас — лёгкий вход."""
    import serp_analysis
    res = serp_analysis.build(date_s)
    if not res.get("available"):
        return []
    out = []
    weak = [i for i in res["items"]
            if i.get("weak") and (i.get("our_position") is None
                                  or i["our_position"] > 10)]
    for i in weak:
        out.append({
            "key": i["query"].lower(),
            "title": f"Слабая выдача «{i['query']}»",
            "action": "усилить (или создать) страницу под запрос: "
                      "специализированных конкурентов в топе нет",
            "evidence": f"{int(i.get('weak_share', 0) * 100)}% топ-10 — "
                        "маркетплейсы и форумы; наша позиция: "
                        f"{i.get('our_position') or 'вне топ-20'}",
            "source": "SERP-срез (слабые выдачи)",
            "score": round(0.6 * 1.0 * 0.7 * 0.8 / 2, 4),
            "confidence": "sufficient",
            "effort": 2,
        })
    return out


# ── Сборка ──────────────────────────────────────────────────────────────────

def select(candidates: list[dict], active: set[str],
           negative: set[str]) -> tuple[list[dict], int, int]:
    """Отбор ≤LIMIT: по score, с дедупом, исключениями и разнообразием."""
    seen: set[str] = set()
    per_source: dict[str, int] = {}
    picked, skipped_active, skipped_negative = [], 0, 0
    for c in sorted(candidates, key=lambda x: -x["score"]):
        key = c["key"]
        if key in seen:
            continue
        seen.add(key)
        if key in negative or any(key in a or a in key for a in negative):
            skipped_negative += 1
            continue
        if key in active or any(key in a for a in active):
            skipped_active += 1
            continue
        # Разнообразие: один детектор не забивает всю неделю — иначе сильный
        # источник (радар) вечно вытесняет momentum и слабые выдачи.
        if per_source.get(c["source"], 0) >= MAX_PER_SOURCE:
            continue
        per_source[c["source"]] = per_source.get(c["source"], 0) + 1
        picked.append(c)
        if len(picked) >= LIMIT:
            break
    for rank, c in enumerate(picked, 1):
        c["rank"] = rank
    return picked, skipped_active, skipped_negative


def build(date_s: str) -> dict:
    snap = _load_snapshot(date_s)
    candidates = (_from_radar(snap, date_s)
                  + _from_cannibalization(date_s)
                  + _from_mismatch(date_s)
                  + _from_lifecycle(date_s)
                  + _from_zero_impressions(date_s)
                  + _from_momentum(date_s)
                  + _from_weak_serps(date_s))
    picked, skipped_active, skipped_negative = select(
        candidates, _active_keys(), _negative_keys())
    return {
        "available": bool(picked),
        "date": date_s,
        "items": picked,
        "considered": len(candidates),
        "skipped_active": skipped_active,
        "skipped_negative": skipped_negative,
        "note": ("≤5 действий недели по единому скорингу всех детекторов; "
                 "ценность — коэффициент типа страницы, не деньги (чека "
                 "сделки в данных нет); открытые и отклонённые ранее "
                 "кандидаты исключены"),
    }


def write(date_s: str) -> dict:
    res = build(date_s)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"allocator-{date_s}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return res


def main() -> int:
    date_s = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(
        dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    res = write(date_s)
    for i in res["items"]:
        print(f"  {i['rank']}. [{i['score']}] {i['title']} — {i['action']}"
              f" ({i['source']})")
    print(f"allocator: {len(res['items'])} из {res['considered']} кандидатов; "
          f"пропущено открытых {res['skipped_active']}, "
          f"отклонённых {res['skipped_negative']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
