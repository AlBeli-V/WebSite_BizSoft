#!/usr/bin/env python3
"""Контроллер бюджета Вордстата: журнал вызовов, лимиты, предохранители.

Каждый платный вызов записывается с причиной, стоимостью и отдачей. Без записи
в журнал вызов не выполняется — иначе на вопрос «сколько стоило исследование»
ответить нечем.

Предохранители:
  мягкая остановка на 5 000 ₽ — разрешены только вызовы, необходимые для уже
  принятого решения или для проверки существующей гипотезы;
  жёсткая остановка на 5 500 ₽ — платные вызовы запрещены полностью;
  суточный потолок — защита от расхода месяца за один день;
  потолок пилота — отдельный лимит на первый прогон.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config  # noqa: E402

LEDGER_DIR = pathlib.Path("reports/seo/wordstat/ledger")

# Причины, которые остаются разрешёнными после мягкой остановки: без них уже
# принятое решение нельзя проверить, и остановка навредит больше, чем расход.
CRITICAL_REASONS = {"decision_validation", "experiment_check", "quota_probe"}


class BudgetExceeded(RuntimeError):
    pass


class BudgetController:
    def __init__(self, cfg: dict | None = None, today: str | None = None,
                 pilot: bool = False):
        self.cfg = cfg or config.load()
        self.today = today or dt.date.today().isoformat()
        self.month = self.today[:7]
        self.pilot = pilot
        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        self.path = LEDGER_DIR / f"{self.month}.jsonl"
        self.entries = self._load()

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in
                self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    # ── Суммы ────────────────────────────────────────────────────────────
    def cost_month(self) -> float:
        return round(sum(e["cost_rub"] for e in self.entries), 4)

    def cost_today(self) -> float:
        return round(sum(e["cost_rub"] for e in self.entries
                         if e["timestamp"][:10] == self.today), 4)

    def cost_pilot(self) -> float:
        return round(sum(e["cost_rub"] for e in self.entries if e.get("pilot")), 4)

    def remaining(self) -> float:
        return round(self.cfg["budget"]["monthly_hard_cap_rub"] - self.cost_month(), 4)

    def forecast_month_end(self) -> float:
        """Прогноз по фактическому темпу с начала месяца."""
        day = int(self.today[8:10])
        if day < 1 or not self.entries:
            return self.cost_month()
        days_in_month = 31 if self.month[-2:] in ("01", "03", "05", "07", "08", "10", "12") \
            else (29 if self.month[-2:] == "02" else 30)
        return round(self.cost_month() / day * days_in_month, 2)

    # ── Предохранители ───────────────────────────────────────────────────
    def state(self) -> str:
        cost = self.cost_month()
        b = self.cfg["budget"]
        if cost >= b["monthly_hard_cap_rub"]:
            return "hard_stop"
        # Мягкая остановка срабатывает на границе рабочей части бюджета:
        # резерв контроля предназначен для проверки решений, а не для
        # продолжения массового исследования.
        working_cap = b.get("working_cap_rub", b["monthly_soft_stop_rub"])
        if cost >= min(working_cap, b["monthly_soft_stop_rub"]):
            return "soft_stop"
        if self.pilot and self.cost_pilot() >= b["pilot_cap_rub"]:
            return "pilot_stop"
        if self.cost_today() >= b["daily_cap_rub"]:
            return "daily_stop"
        return "open"

    def can_spend(self, method: str, reason: str) -> tuple[bool, str]:
        """Разрешён ли платный вызов. Возвращает решение и его причину."""
        price = config.price_of(method, self.today, self.cfg)
        if price == 0:
            return True, "метод бесплатный"
        st = self.state()
        if st == "hard_stop":
            return False, "жёсткая остановка: месячный потолок исчерпан"
        if st == "daily_stop":
            return False, "суточный потолок исчерпан"
        if st == "pilot_stop":
            return False, "потолок пилота исчерпан"
        if st == "soft_stop" and reason not in CRITICAL_REASONS:
            return False, ("мягкая остановка: разрешены только вызовы, необходимые "
                           "для уже принятого решения")
        if self.cost_month() + price > self.cfg["budget"]["monthly_hard_cap_rub"]:
            return False, "вызов вывел бы расход за месячный потолок"
        return True, "в пределах бюджета"

    # ── Журнал ───────────────────────────────────────────────────────────
    def record(self, *, method: str, phrase: str, cluster: str | None, reason: str,
               cache_hit: bool, result_count: int = 0, unique_result_count: int = 0,
               new_commercial_phrases: int = 0, new_clusters: int = 0,
               status: str = "ok") -> dict:
        price = 0.0 if cache_hit else config.price_of(method, self.today, self.cfg)
        entry = {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "method": method,
            "phrase": phrase,
            "cluster": cluster,
            "reason": reason,
            "cache_hit": cache_hit,
            "cost_rub": round(price, 6),
            "result_count": result_count,
            "unique_result_count": unique_result_count,
            "new_commercial_phrases": new_commercial_phrases,
            "new_clusters": new_clusters,
            "status": status,
            "pilot": self.pilot,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.entries.append(entry)
        return entry

    # ── Эффективность ────────────────────────────────────────────────────
    def efficiency(self) -> dict:
        paid = [e for e in self.entries if not e["cache_hit"]]
        cost = sum(e["cost_rub"] for e in paid) or 0.0
        uniq = sum(e["unique_result_count"] for e in self.entries)
        comm = sum(e["new_commercial_phrases"] for e in self.entries)
        clusters = sum(e["new_clusters"] for e in self.entries)
        raw = sum(e["result_count"] for e in self.entries)
        hits = sum(1 for e in self.entries if e["cache_hit"])

        def per(n):
            return round(cost / n * 1000, 3) if n else None

        return {
            "calls_total": len(self.entries),
            "calls_paid": len(paid),
            "cost_month_rub": round(cost, 4),
            "cost_today_rub": self.cost_today(),
            "remaining_budget_rub": self.remaining(),
            "forecast_month_end_rub": self.forecast_month_end(),
            "state": self.state(),
            "cache_hit_rate": round(hits / len(self.entries), 4) if self.entries else None,
            "duplicate_rate": round(1 - uniq / raw, 4) if raw else None,
            "unique_phrases": uniq,
            "new_commercial_phrases": comm,
            "new_clusters": clusters,
            "cost_per_1000_unique_phrases_rub": per(uniq),
            "cost_per_1000_commercial_phrases_rub": per(comm),
            "cost_per_new_cluster_rub": round(cost / clusters, 4) if clusters else None,
            "empty_response_rate": (
                round(sum(1 for e in self.entries if e["status"] == "below_threshold")
                      / len(self.entries), 4) if self.entries else None),
        }
