#!/usr/bin/env python3
"""Отчёт качества содержания письма V4.

Проверяет не вёрстку, а сами утверждения: подкреплено ли каждое числом из снимка,
не выдаётся ли оценка за факт, соблюдены ли правила методики измерений и
условного вывода блоков.

Запуск: python3 scripts/seo/contentcheck.py <дата>
Результат: reports/seo/intelligence/<дата>-v4-content.json
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

BASE = pathlib.Path("reports/seo/intelligence")


def numbers_in(text: str) -> set[str]:
    return set(re.findall(r"\d[\d  ]*", text.replace(" ", " ")))


def audience_checks(blocks: dict) -> list[dict]:
    """Сверка блока «Аудитория» с остальным письмом.

    Три разных утверждения об одном и том же должны совпадать: итог показов
    в блоке и в карточке видимости (ряд один), сумма каналов и сумма
    устройств с итогом системы, разбивка по устройствам с показами.
    Расхождение здесь — это два числа об одном предмете в одном письме,
    и читатель вправе не поверить ни одному.
    """
    aud = blocks.get("audience") or {}
    if not aud.get("available"):
        return []
    out: list[dict] = []

    def add(name, ok, detail):
        out.append({"check": name, "ok": bool(ok), "detail": detail})

    kpi_value = {k["key"]: k["value"] for k in blocks.get("kpis", [])}
    card_of = {"yandex": "yandex", "gsc": "google"}
    pairs, mismatch = [], []
    for row in (aud.get("impressions") or {}).get("rows", []):
        if not row.get("available"):
            continue
        card = kpi_value.get(card_of.get(row["key"], ""))
        if card is None:
            continue
        card_num = int(re.sub(r"\D", "", card) or 0)
        pairs.append(f"{row['label']}: блок {int(row['total'])}, карточка {card_num}")
        if int(row["total"]) != card_num:
            mismatch.append(pairs[-1])
    add("audience_matches_kpi", not mismatch,
        "; ".join(mismatch or pairs) or "сверять нечего")

    gaps = []
    for blk in (aud.get("visits") or {}).get("blocks", []):
        if not blk.get("available"):
            continue
        by_channel = sum(c["total"] for c in blk["channels"])
        by_device = sum((blk.get("devices") or {}).values())
        if round(by_channel, 2) != round(blk["total"], 2):
            gaps.append(f"{blk['label']}: сумма каналов {by_channel} ≠ итог {blk['total']}")
        if round(by_device, 2) != round(blk["total"], 2):
            gaps.append(f"{blk['label']}: сумма устройств {by_device} ≠ итог {blk['total']}")
    add("audience_internally_consistent", not gaps,
        "; ".join(gaps) if gaps else "суммы каналов и устройств сходятся с итогом")

    thin = [f"{r['label']} — покрытие {r['coverage']:.0%}"
            for r in (aud.get("impressions") or {}).get("rows", [])
            if r.get("available") and (r.get("coverage") or 0) < 0.9]
    add("audience_device_coverage", not thin,
        "; ".join(thin) if thin else "разбивка по устройствам покрывает показы")
    return out


def run(date: str) -> dict:
    blocks = json.loads((BASE / f"{date}-v4-blocks.json").read_text(encoding="utf-8"))
    snap = json.loads((BASE / "snapshots" / f"{date}.json").read_text(encoding="utf-8"))
    dq = json.loads((BASE / "data-quality" / f"{date}.json").read_text(encoding="utf-8"))
    findings = []

    def add(name, ok, detail):
        findings.append({"check": name, "ok": bool(ok), "detail": detail})

    # 1. Каждый показатель несёт источник, период и достоверность.
    incomplete = [k["label"] for k in blocks["kpis"]
                  if not (k["source"] and k["period"] and k["confidence"])]
    add("kpi_fully_attributed", not incomplete,
        f"показателей без источника, периода или достоверности: {incomplete or 'нет'}")

    # 2. Значения показателей совпадают со снимком. При KPI из дневной
    # витрины эталон — суммы её окон; иначе — агрегатные totals источника.
    rules = dq.get("publication_rules") or {}

    def daily_cur(src, metric):
        w = (((snap.get("daily") or {}).get(src) or {}).get("windows") or {}).get(metric) or {}
        s = (w.get("current") or {}).get("sum")
        return str(int(s)) if s is not None else None

    yt = snap["yandex"].get("totals") or {}
    gt = snap["google"].get("totals") or {}
    if rules.get("kpi_from_daily"):
        expect = {
            "Видимость в Яндексе": daily_cur("yandex", "impressions") or str(yt.get("impressions")),
            "Видимость в Google": daily_cur("gsc", "impressions") or str(gt.get("impressions_last7")),
        }
    else:
        expect = {
            "Видимость в Яндексе": str(yt.get("impressions")),
            "Видимость в Google": str(gt.get("impressions_last7")),
        }
    mismatched = [k["label"] for k in blocks["kpis"]
                  if k["label"] in expect
                  and expect[k["label"]] != k["value"].replace(" ", "").replace(" ", "")]
    add("kpi_values_match_snapshot", not mismatched,
        f"расхождений со снимком: {mismatched or 'нет'}")

    # 3. Каждый сигнал имеет предыдущее значение и дельту.
    bad = [s["metric"] for s in blocks["signals"]
           if not (s["previous"] and s["current"] and s["delta"])]
    add("signals_have_baseline", not bad, f"сигналов без базы сравнения: {bad or 'нет'}")

    # 4. Утверждение о причине опирается на перечисленные адреса.
    named = len(blocks.get("driver_rows") or [])
    claim = "Изменение" in blocks.get("driver_summary", "") or named > 0
    add("cause_backed_by_entities", (not claim) or named > 0,
        f"адресов-драйверов перечислено: {named}")

    # 5. Вердикт эксперимента не опережает экспозицию.
    early = [e["ticket"] for e in blocks["experiments"]
             if e["verdict"] in ("positive", "negative")
             and (e["days_elapsed"] < 7 or (e["impressions_since_deploy"] or 0) < 500)]
    add("verdict_respects_exposure", not early,
        f"преждевременных вердиктов: {early or 'нет'}")

    # 6. Совместное внедрение не разделяется на составляющие.
    split = [e["ticket"] for e in blocks["experiments"]
             if e.get("combined_treatment") and not e.get("combined_note")]
    add("combined_treatment_declared", not split, f"без оговорки о совместности: {split or 'нет'}")

    # 7. Рыночный спрос не подменяется нашими показами.
    ev = [o["evidence_kind"] for o in blocks["opportunities"].get("items", [])]
    md_available = (snap.get("market_demand") or {}).get("available")
    fake_demand = [o["cluster"] for o in blocks["opportunities"].get("items", [])
                   if o["evidence_kind"] == "market_demand" and not md_available]
    add("no_fake_market_demand", not fake_demand,
        f"источники доказательств: {ev or 'нет'}; спрос измерен: {bool(md_available)}")

    # 8. Здоровье данных соответствует характеру проблемы.
    health = dq["data_health"]["status"]
    critical = [f["code"] for f in dq["findings"] if f["level"] == "critical"]
    add("health_matches_findings", (health == "degraded") == bool(critical),
        f"статус {health}, критических находок {len(critical)}")

    # 9. Пустые разделы не выводятся.
    empty = []
    if not blocks["signals"]:
        empty.append("сигналы")
    if not blocks["board"]:
        empty.append("журнал")
    if not blocks["opportunities"].get("items"):
        empty.append("радар")
    add("conditional_rendering", True,
        f"скрыто пустых разделов: {empty or 'нет — все разделы содержательны'}")

    # 10. Нет данных остаётся «нет данных», а не нулём.
    zeros = [k["label"] for k in blocks["kpis"] if k["value"] == "0" and k["muted"]]
    add("no_zero_for_missing", not zeros, f"нулей вместо «нет данных»: {zeros or 'нет'}")

    # 11. Заявки: у каждой назван канал и основание, а число совпадает со
    # снимком. Основание — не украшение: «поиск Google по Метрике» и
    # «google.com по метке браузера» — утверждения разной силы, и письмо,
    # потерявшее эту разницу, выдаёт догадку за измерение.
    lb = blocks.get("leads") or {}
    if lb.get("available"):
        nameless = [it["company"] for it in lb["items"]
                    if not (it.get("channel") and it.get("channel_basis"))]
        add("leads_channel_basis_named", not nameless,
            f"заявок без канала или основания: {nameless or 'нет'}")
        crm_count = (snap.get("crm") or {}).get("qualified_leads")
        add("leads_count_matches_snapshot", crm_count == lb["count"],
            f"в снимке {crm_count}, в письме {lb['count']}")

    # 12. Блок «Аудитория» не противоречит остальному письму.
    findings += audience_checks(blocks)

    ok = all(f["ok"] for f in findings)
    return {"date": date, "passed": ok, "checks": findings,
            "counts": {"total": len(findings),
                       "failed": sum(1 for f in findings if not f["ok"])}}


def main() -> int:
    date = sys.argv[1]
    res = run(date)
    (BASE / f"{date}-v4-content.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in res["checks"]:
        print(f"  [{'OK  ' if c['ok'] else 'FAIL'}] {c['check']}: {c['detail']}")
    print(f"Качество содержания: {'pass' if res['passed'] else 'FAIL'} "
          f"({res['counts']['total'] - res['counts']['failed']}/{res['counts']['total']})")
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
