#!/usr/bin/env python3
"""Инварианты письма: правила, обязанные выполняться в каждом выпуске.

Сценарные тесты проверяют синтетические письма; этот модуль прогоняет те же
правила по фактическому письму дня — последним шагом сборки report_v4 и как
самостоятельная проверка. Результат — <дата>-invariants.json.

Два уровня (решение руководителя 03.09.2026, аудит достоверности):

БЛОКИРУЮЩИЕ — ложь о дате или причине. Письмо с таким нарушением не
собирается в файл для отправки; уходит уведомление о сбое сборки с
перечнем нарушений (report_v4.main, seo-report-email.yml).
  B1. Недоступный блок без кода причины или с текстом причины не из
      словаря (passport.REASONS) — «причина, которую код не проверял».
  B2. Данные старше ожидаемой даты без пометки stale, и наоборот.
  B3. Недоступный источник (в снимке или в findings), а пилюля ДАННЫЕ не
      показывает сбой.
  B4. «Следующая проверка» датирована днём письма — проверка уже прошла.

МЯГКИЕ — форма и подача; письмо уходит, нарушение остаётся в JSON.
  S1. «Нет данных» не имеет дельты и процента.
  S2. Знак дельты сигнала не противоречит его тону.
  S3. Недоказуемое «по-прежнему» в тексте письма не появляется.
  S4. Экспозиция «порог пройден» при вердикте «мало данных» — два
      определения экспозиции в одном блоке (методика, этап 4 аудита).

Запуск: python3 scripts/seo/invariants.py [YYYY-MM-DD]
Код выхода 1 при любом нарушении (для ручного прогона).
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import passport  # noqa: E402
from textfmt import ru_date  # noqa: E402

BASE = pathlib.Path("reports/seo/intelligence")
MINUS = "−"     # знак минуса из textfmt.signed


def blocking(snap: dict, dq: dict, blocks: dict) -> list[str]:
    v: list[str] = []

    # B1, B2 — контракт паспорта по всем блокам письма.
    v += passport.check_all(blocks)

    # B3 — сбой источника виден в пилюле.
    an = snap.get("analytics") or {}
    sources = [snap.get("yandex") or {}, snap.get("google") or {},
               an.get("metrika") or {}, an.get("ga4") or {}]
    states = {p.get("label"): p.get("state") for p in blocks.get("pills") or []}
    unavailable = any(not s.get("available") for s in sources)
    flagged = any(f.get("code") == "SOURCE_UNAVAILABLE"
                  for f in dq.get("findings") or [])
    if (unavailable or flagged) and states.get("ДАННЫЕ") != "degraded":
        v.append("недоступный источник, а пилюля ДАННЫЕ не показывает сбой")

    # B4 — проверка, датированная днём письма, не «следующая».
    today = ru_date(blocks.get("date")) if blocks.get("date") else None
    for c in blocks.get("checkpoints") or []:
        if today and c.get("date") == today:
            v.append(f"«следующая проверка» датирована днём письма: {c.get('what')}")
    return v


def soft(blocks: dict, html: str) -> list[str]:
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

    if "по-прежнему" in (html or ""):
        v.append("недоказуемое «по-прежнему» в тексте письма")

    for e in blocks.get("experiments") or []:
        # Вердикт движка лежит в evaluation.verdict; поле verdict самого
        # эксперимента — стадия наблюдения («observing», «too_early»), строка.
        # Прежняя редакция читала стадию как словарь и на реальном блоке
        # роняла сборку письма (AttributeError), а на фикстурах молчала:
        # у них форма другая. Заодно инвариант начал проверять то, что
        # заявлен проверять, — до этого он не срабатывал ни разу.
        ev = e.get("evaluation") or {}
        verdict = ev.get("verdict")
        # Противоречие — это «порог пройден» на ТОМ ЖЕ наборе, по которому
        # вынесен вердикт (решение 04.09.2026). Пока окно источника захватывает
        # период до внедрения, matched-набора не существует: экспозиция
        # кластера набрана, а сравнивать не с чем — это законная стадия, и
        # строка письма называет дату чистого окна.
        if (e.get("exposure_ok") and verdict == "INSUFFICIENT_DATA"
                and e.get("exposure_basis") == "matched"):
            v.append(f"{e.get('ticket')}: «порог пройден» при вердикте «мало данных»")
    return v


def check_tiers(snap: dict, dq: dict, blocks: dict, html: str) -> dict:
    return {"blocking": blocking(snap, dq, blocks), "soft": soft(blocks, html)}


def check(snap: dict, dq: dict, blocks: dict, html: str) -> list[str]:
    """Все нарушения одним списком (совместимость с прежними вызовами)."""
    t = check_tiers(snap, dq, blocks, html)
    return t["blocking"] + t["soft"]


def write_report(date: str, snap: dict, dq: dict, blocks: dict, html: str,
                 out_dir: pathlib.Path | None = None) -> dict:
    t = check_tiers(snap, dq, blocks, html)
    out = {"date": date, "passed": not (t["blocking"] or t["soft"]),
           "blocked": bool(t["blocking"]),
           "blocking": t["blocking"], "soft": t["soft"],
           "violations": t["blocking"] + t["soft"]}
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
    for kind in ("blocking", "soft"):
        for line in out[kind]:
            print(f"[{kind}] {line}")
    print("ок" if out["passed"] else
          f"нарушений: блокирующих {len(out['blocking'])}, мягких {len(out['soft'])}")
    return 0 if out["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
