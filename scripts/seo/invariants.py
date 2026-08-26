#!/usr/bin/env python3
"""Инварианты письма: правила, обязанные выполняться в каждом выпуске.

Сценарные тесты проверяют синтетические письма; этот модуль прогоняет те же
правила по фактическому письму дня — последним шагом сборки report_v4 и как
самостоятельная проверка. Нарушение не блокирует отправку (лучше письмо с
зафиксированным нарушением, чем молчание), но фиксируется в
<дата>-invariants.json и в выводе конвейера — это сигнал разбираться.

Правила:
  1. «Нет данных» не имеет дельты и процента.
  2. Знак дельты сигнала не противоречит его тону.
  3. Недоступный источник (в снимке или в findings) ⇒ пилюля ДАННЫЕ — «сбой».
  4. Недоказуемое «по-прежнему» в тексте письма не появляется.

Запуск: python3 scripts/seo/invariants.py [YYYY-MM-DD]
Результат: reports/seo/intelligence/<дата>-invariants.json; код выхода 1 при
нарушениях (для ручного прогона и шага конвейера).
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

BASE = pathlib.Path("reports/seo/intelligence")
MINUS = "−"     # знак минуса из textfmt.signed


def check(snap: dict, dq: dict, blocks: dict, html: str) -> list[str]:
    """Список нарушений; пустой список — письмо инвариантам соответствует."""
    v: list[str] = []

    for k in blocks.get("kpis") or []:
        if k.get("value") == "нет данных" and (k.get("delta") is not None
                                               or k.get("relative") is not None):
            v.append(f"KPI {k.get('key')}: дельта или процент при «нет данных»")

    for s in blocks.get("signals") or []:
        d = s.get("delta") or ""
        if d.startswith("+") and s.get("tone") == "negative":
            v.append(f"сигнал «{s.get('metric')}»: положительная дельта с тоном negative")
        if d.startswith(MINUS) and s.get("tone") == "positive":
            v.append(f"сигнал «{s.get('metric')}»: отрицательная дельта с тоном positive")

    an = snap.get("analytics") or {}
    sources = [snap.get("yandex") or {}, snap.get("google") or {},
               an.get("metrika") or {}, an.get("ga4") or {}]
    states = {p.get("label"): p.get("state") for p in blocks.get("pills") or []}
    unavailable = any(not s.get("available") for s in sources)
    flagged = any(f.get("code") == "SOURCE_UNAVAILABLE"
                  for f in dq.get("findings") or [])
    if (unavailable or flagged) and states.get("ДАННЫЕ") != "degraded":
        v.append("недоступный источник, а пилюля ДАННЫЕ не показывает сбой")

    if "по-прежнему" in (html or ""):
        v.append("недоказуемое «по-прежнему» в тексте письма")

    return v


def write_report(date: str, snap: dict, dq: dict, blocks: dict, html: str,
                 out_dir: pathlib.Path | None = None) -> dict:
    violations = check(snap, dq, blocks, html)
    out = {"date": date, "passed": not violations, "violations": violations}
    target = (out_dir or BASE) / f"{date}-invariants.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    snap = json.loads((BASE / "snapshots" / f"{date}.json").read_text(encoding="utf-8"))
    dq = json.loads((BASE / "data-quality" / f"{date}.json").read_text(encoding="utf-8"))
    blocks = json.loads((BASE / f"{date}-v4-blocks.json").read_text(encoding="utf-8"))
    html_path = BASE / f"{date}-v4.html"
    html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
    out = write_report(date, snap, dq, blocks, html)
    status = "ок" if out["passed"] else "НАРУШЕНЫ: " + "; ".join(out["violations"])
    print(f"инварианты: {status}")
    return 0 if out["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
