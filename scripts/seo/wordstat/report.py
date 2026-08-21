#!/usr/bin/env python3
"""Отчётность Wordstat Intelligence.

Три адресата, три уровня детализации:
  письмо руководителю — блок «Спрос и направления развития», без технических цифр;
  веб-отчёт и приложение — покрытие, разрывы, возможности, эффективность вызовов;
  файл состояния — машинная сводка для генератора письма.

Запуск: python3 scripts/seo/wordstat/report.py [YYYY-MM-DD]
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import budget as budget_mod      # noqa: E402
import config                    # noqa: E402
import coverage as cov_mod       # noqa: E402
import discovery as D            # noqa: E402
import opportunity as opp_mod    # noqa: E402
import tiers as tiers_mod        # noqa: E402
import universe as universe_mod  # noqa: E402
import vendor_expansion as vx    # noqa: E402

OUT = pathlib.Path("reports/seo/wordstat")
SNAP_DIR = pathlib.Path("reports/seo/intelligence/snapshots")
STATE_OUT = OUT / "intelligence-state.json"


def build_state(date: str) -> dict:
    cfg = config.load()
    uni = universe_mod.Universe()
    vendors = D.site_vendors()
    snap_path = SNAP_DIR / f"{date}.json"
    if not snap_path.exists():
        candidates = sorted(SNAP_DIR.glob("*.json"))
        snap_path = candidates[-1] if candidates else None
    snap = json.loads(snap_path.read_text(encoding="utf-8")) if snap_path else {}
    if snap:
        cov_mod.enrich_universe(uni, snap, {v["slug"]: v["url"] for v in vendors})

    clusters = cov_mod.clusters_of(uni)
    tiers = tiers_mod.assign(clusters, cfg)
    coverage = cov_mod.demand_coverage(clusters, conversion_clusters=set())
    gaps = cov_mod.gap_analysis(uni, clusters, conversion_clusters=set())
    top = opp_mod.rank(gaps, 5)
    bud = budget_mod.BudgetController(cfg, today=date)

    uncovered = [g for g in gaps if not g["page_exists"]]
    return {
        "date": date,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "measured_at": max((r.get("last_seen") or "") for r in uni.rows.values())
                       if uni.rows else None,
        "universe": uni.stats(),
        "coverage": coverage,
        "coverage_by_category": cov_mod.coverage_by(clusters, "category"),
        "tiers": {t: sum(1 for v in tiers.values() if v == t) for t in ("A", "B", "C")},
        "gaps_by_class": {k: sum(1 for g in gaps if g["gap"] == k)
                          for k in sorted({g["gap"] for g in gaps})},
        "uncovered_top": [
            {"cluster": g["cluster"], "demand": g["commercial_demand"],
             "gap": g["gap"], "action": g["recommended_action"],
             "top_phrase": g["top_phrases"][0]["phrase"] if g["top_phrases"] else None}
            for g in uncovered[:10]],
        "opportunities": top,
        "vendor_expansion": vx.build(uni, vendors),
        "efficiency": bud.efficiency(),
        "quota": {
            "requests_per_hour": cfg["quota"]["requests_per_hour"],
            "target": cfg["quota"]["requests_per_hour_target"],
            "budget_is_binding": config.budget_is_binding(cfg),
            "max_possible_spend_rub": round(config.max_monthly_spend(cfg), 0),
        },
    }


def executive_block(state: dict) -> dict:
    """Блок для письма: смысл без техники. Числа API сюда не попадают."""
    cov = state["coverage"]
    uni = state["universe"]
    opps = state["opportunities"]
    if not cov.get("available"):
        return {"available": False,
                "reason": "замер спроса ещё не собран"}

    levels = cov["levels"]
    lead = opps[0] if opps else None
    uncovered_demand = sum(u["demand"] for u in state["uncovered_top"])

    def spaced(n):
        return f"{int(n):,}".replace(",", " ")

    lines = [
        f"Мы видим {spaced(uni['total_commercial_demand'])} покупательских запросов "
        f"в месяц по {uni['clusters']} направлениям каталога.",
        f"Своя страница есть под {levels['page']:.0%} этого спроса, "
        f"в поиске находится {levels['indexed']:.0%}, "
        f"на первой странице — {levels['top10']:.0%}.",
    ]
    if uncovered_demand:
        lines.append(
            f"Без страницы остаётся {spaced(uncovered_demand)} запросов в месяц — "
            "это направления, где спрос есть, а нас в выдаче нет.")
    exp = state.get("vendor_expansion") or {}
    expansion = None
    if exp.get("available"):
        ready = [r for r in exp["recommended"]
                 if r["payment"]["verdict"] in ("card", "likely_card")][:3]
        manual = exp.get("needs_manual_check") or []
        # Письмо ограничено по объёму, поэтому сводка держится в двух фразах:
        # сколько подтверждено и сколько из них готово к заведению. Разбор по
        # ручной проверке и сомнительным названиям — в веб-отчёте.
        weak = exp.get("low_confidence") or []
        summary = (
            f"Проверили спрос на {exp['candidates_measured']} зарубежных "
            f"разработчиков вне каталога: у {exp['recommended_total']} он подтверждён, "
            f"суммарно {spaced(exp['combined_demand'])} запросов в месяц.")
        tail = []
        if ready:
            tail.append(f"{len(ready)} с оплатой картой можно заводить сразу")
        if manual:
            tail.append(f"{len(manual)} требуют ручной проверки оплаты")
        if weak:
            tail.append(f"{len(weak)} — с именем-обычным словом, спрос сверить вручную")
        if tail:
            summary += " Из них: " + ", ".join(tail) + "."
        expansion = {
            "title": "Каких вендоров добавить",
            "summary": summary,
            "items": [{"brand": r["brand"], "demand": r["commercial_demand"],
                       "kind": "AI-сервис" if r["kind"] == "ai" else "классический",
                       "payment": r["payment"]["verdict"],
                       "recommendation": r["recommendation"],
                       "effort": r["effort_note"], "url": r["seo"]["url"],
                       "confidence": r.get("demand_confidence"),
                       "confidence_note": r.get("demand_confidence_note")}
                      for r in (ready or exp["recommended"])[:2]],
            "manual_check": manual[:5],
            "note": exp["note"],
        }

    return {
        "available": True,
        "title": "Спрос и направления развития",
        "expansion": expansion,
        "summary": " ".join(lines),
        "coverage": {"page": levels["page"], "indexed": levels["indexed"],
                     "top10": levels["top10"]},
        "lead_opportunity": {
            "cluster": lead["cluster"],
            "demand": lead["commercial_demand"],
            "action": lead["recommended_action"],
            "why": lead["gap_title"],
            "confidence": lead["confidence_note"],
        } if lead else None,
        "measured_at": state["measured_at"],
    }


def write_markdown(state: dict, path: pathlib.Path) -> None:
    cov, uni = state["coverage"], state["universe"]
    eff = state["efficiency"]
    L = [f"# Спрос, покрытие и возможности — {state['date']}", "",
         f"Замер семантики: {state['measured_at']}. "
         f"Источник — Вордстат, регион Россия, окно 30 дней.", "",
         "## Покрытие спроса", "",
         f"Считается по частотности коммерческих фраз, а не по числу ключевых слов. "
         f"Всего измеренного покупательского спроса — "
         f"{cov['total_commercial_demand']:,} показов в месяц.".replace(",", " "), "",
         "| Уровень | Доля спроса | Что означает |", "|---|---|---|"]
    meaning = {
        "page": "есть релевантная страница",
        "indexed": "страница участвует в поиске",
        "top10": "мы на первой странице выдачи",
        "clicks": "по запросу к нам приходят",
        "conversion_measured": "конверсия измеряется",
        "qualified_leads": "обращения подтверждены CRM",
    }
    for k, v in cov["levels"].items():
        L.append(f"| {k} | {'нет данных' if v is None else f'{v:.1%}'} | {meaning[k]} |")
    L += ["", "Уровень «клики» считается только по пересечению нашей семантики "
          "с выборкой топ-100 запросов Вебмастера: за её пределами переходы "
          "по конкретной фразе не наблюдаются.", "",
          "## Разрывы", "", "| Класс | Смысл | Кластеров |", "|---|---|---|"]
    for gap, n in state["gaps_by_class"].items():
        title, action = cov_mod.GAP_ACTIONS[gap]
        L.append(f"| {gap} | {title} → {action} | {n} |")
    L += ["", "## Непокрытый коммерческий спрос", "",
          "| Кластер | Спрос, показов/мес | Класс | Действие |", "|---|---|---|---|"]
    for u in state["uncovered_top"]:
        L.append(f"| {u['cluster']} | {u['demand']:,} | {u['gap']} | {u['action']} |"
                 .replace(",", " "))
    exp = state.get("vendor_expansion") or {}
    if exp.get("available"):
        L += ["", "## Каких вендоров добавить в каталог", "",
              f"Проверен спрос на {exp['candidates_measured']} зарубежных "
              f"разработчиков вне каталога; покупательский спрос подтверждён "
              f"у {exp['recommended_total']}. {exp['note']}", "",
              "Приоритет — по покупательскому спросу с поправкой на трудоёмкость "
              "запуска: карточка одного продукта дешевле линейки тарифов.", "",
              "| Вендор | Тип | Спрос | Достоверность | Оплата картой | "
              "Рекомендация | Трудоёмкость | Адрес |",
              "|---|---|---|---|---|---|---|---|"]
        pay_label = {"card": "есть", "likely_card": "вероятно",
                     "sales_only": "только через продажи", "unknown": "не определена",
                     "unreachable": "сайт не открылся", "not_checked": "не проверялась"}
        for r in exp["recommended"]:
            kind = "AI" if r["kind"] == "ai" else "классический"
            L.append(f"| {r['brand']} | {kind} | "
                     f"{format(r['commercial_demand'], ',').replace(',', ' ')} | "
                     f"{r.get('demand_confidence', '—')} | "
                     f"{pay_label.get(r['payment']['verdict'], '—')} | "
                     f"{r['recommendation']} | {r['effort_note']} | "
                     f"`{r['seo']['url']}` |")
        if exp.get("by_payment"):
            L += ["", "Распределение по способу оплаты: "
                  + ", ".join(f"{pay_label.get(k, k)} — {v}"
                              for k, v in exp["by_payment"].items()) + ".", ""]
        if exp.get("low_confidence"):
            L += ["**Спрос требует проверки выдачи** — имя бренда совпадает с "
                  "обычным английским словом, и в замер попадают чужие товары: "
                  + ", ".join(exp["low_confidence"]) + ". Решение по ним "
                  "принимать только после ручного просмотра выдачи.", ""]
        if exp.get("needs_manual_check"):
            L += ["**Требуют ручной проверки** — спрос есть, способ оплаты "
                  "автоматически определить не удалось: "
                  + ", ".join(exp["needs_manual_check"]) + ".", ""]
        L += ["", "### SEO-обвязка для первых трёх", "",
              "Заготовки для создания страниц: адрес, заголовок, описание, "
              "темы вопросов и целевые запросы.", ""]
        for r in exp["recommended"][:3]:
            seo = r["seo"]
            L += [f"**{r['brand']}** — `{seo['url']}` "
                  f"({'AI-сервис' if r['kind'] == 'ai' else 'классический'}, "
                  f"оплата: {r['payment']['note'] or '—'})", "",
                  f"- заголовок: {seo['title']}",
                  f"- описание: {seo['description']}",
                  f"- H1: {seo['h1']}",
                  f"- целевые запросы: " + ", ".join(
                      f"«{p['phrase']}» — {p['frequency']}" for p in r["top_phrases"][:5]),
                  f"- разделы вопросов: " + "; ".join(seo["faq_topics"]),
                  f"- нужные подкластеры: " + ", ".join(seo["needed_subclusters"]),
                  f"- перелинковка: " + ", ".join(seo["internal_links"]), ""]

    L += ["", "## Возможности", ""]
    for o in state["opportunities"]:
        c = o["components"]
        L += [f"### {o['cluster']} — {o['recommended_action']}", "",
              f"- спрос: {o['commercial_demand']:,} показов в месяц по "
              f"{o['commercial_phrases']} коммерческим фразам".replace(",", " "),
              f"- страница: {o['url'] or 'нет'} · позиция: {o['best_position'] or '—'} "
              f"· тренд: {o['trend']}",
              f"- балл {o['opportunity_score']}: спрос {c['normalized_demand']} × "
              f"интент {c['commercial_intent']} × разрыв {c['coverage_gap']} × "
              f"тренд {c['trend_factor']} × уверенность {c['confidence']} / "
              f"трудоёмкость {c['estimated_effort']}",
              f"- достоверность: {o['confidence_note']}",
              f"- запросы: " + ", ".join(f"«{p['phrase']}» — {p['frequency']}"
                                         for p in o["top_phrases"][:3]), ""]
    def share(value):
        return "—" if value is None else f"{value:.1%}"

    L += ["## Эффективность обращений к API", "",
          "| Показатель | Значение |", "|---|---|",
          f"| вызовов всего | {eff['calls_total']} |",
          f"| из них платных | {eff['calls_paid']} |",
          f"| расход за месяц | {eff['cost_month_rub']:.2f} ₽ |",
          f"| остаток бюджета | {eff['remaining_budget_rub']:.2f} ₽ |",
          f"| прогноз на конец месяца | {eff['forecast_month_end_rub']:.2f} ₽ |",
          f"| попаданий в кэш | {share(eff['cache_hit_rate'])} |",
          f"| дублирование | {share(eff['duplicate_rate'])} |",
          f"| пустых ответов | {share(eff['empty_response_rate'])} |",
          f"| стоимость 1000 уникальных фраз | "
          f"{eff['cost_per_1000_unique_phrases_rub'] or '—'} ₽ |",
          f"| стоимость 1000 коммерческих фраз | "
          f"{eff['cost_per_1000_commercial_phrases_rub'] or '—'} ₽ |",
          f"| состояние бюджета | {eff['state']} |", "",
          f"Квота {state['quota']['requests_per_hour']} запросов в час позволяет "
          f"потратить не более {state['quota']['max_possible_spend_rub']:.0f} ₽ в месяц. "
          f"Бюджет является ограничением: "
          f"{'да' if state['quota']['budget_is_binding'] else 'нет — ограничивает квота'}.",
          ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    state = build_state(date)
    state["executive_block"] = executive_block(state)
    STATE_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATE_OUT.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    write_markdown(state, OUT / f"{date}-demand-report.md")
    print(f"состояние: {STATE_OUT}")
    print(f"отчёт: {OUT / f'{date}-demand-report.md'}")
    print(f"покрытие: страница {state['coverage']['levels']['page']:.1%}, "
          f"индексация {state['coverage']['levels']['indexed']:.1%}, "
          f"топ-10 {state['coverage']['levels']['top10']:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
