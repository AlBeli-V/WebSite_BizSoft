#!/usr/bin/env python3
"""Клиент Wordstat API: кэш, дедупликация запросов, учёт стоимости, лимиты.

Ни один платный вызов не проходит мимо контроллера бюджета и ограничителя частоты.
Ключ кэша включает параметры запроса — прежняя версия ключа `{метод}|{фраза}`
молча возвращала данные, собранные для другого региона или другой глубины выдачи.

TTL раздельный: частотность обновляется помесячно, региональное распределение
меняется медленно и живёт дольше.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import sys

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config  # noqa: E402
import limiter as limiter_mod  # noqa: E402

BASE = "https://searchapi.api.cloud.yandex.net/v2/wordstat"
CACHE_DIR = pathlib.Path("reports/seo/wordstat/cache")

METHOD_PATH = {"getTop": "/topRequests", "getDynamics": "/dynamics",
               "getRegionsDistribution": "/regions", "getRegionsTree": "/getRegionsTree"}


class WordstatClient:
    def __init__(self, budget, cfg: dict | None = None, dry_run: bool = False,
                 rate_limiter=None, session=None):
        self.cfg = cfg or config.load()
        self.budget = budget
        self.dry_run = dry_run
        self.session = session or requests
        q = self.cfg["quota"]
        self.limiter = rate_limiter or limiter_mod.RateLimiter(
            q["requests_per_second"], q["requests_per_hour"])
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._headers = None
        self.planned: list[dict] = []          # для dry-run
        self.stopped_by: str | None = None

    # ── Авторизация ──────────────────────────────────────────────────────
    def headers(self) -> dict:
        if self._headers is None:
            token = os.environ.get("WORDSTAT_API_KEY", "").strip()
            if not token and not self.dry_run:
                raise SystemExit("WORDSTAT_API_KEY не задан")
            self._headers = {"Authorization": f"Api-Key {token}",
                             "Content-Type": "application/json"}
        return self._headers

    # ── Кэш ──────────────────────────────────────────────────────────────
    def cache_key(self, method: str, body: dict) -> str:
        """Ключ включает все параметры запроса, а не только фразу."""
        payload = json.dumps({"method": method, "body": body},
                             ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def _cache_path(self, key: str) -> pathlib.Path:
        return self.cache_dir / f"{key}.json"

    def ttl_days(self, method: str) -> int:
        c = self.cfg["collection"]
        return {"getTop": c["cache_ttl_days"],
                "getDynamics": c["dynamics_ttl_days"],
                "getRegionsDistribution": c["regions_ttl_days"]}.get(method, 30)

    def cache_get(self, method: str, body: dict, today: str) -> dict | None:
        path = self._cache_path(self.cache_key(method, body))
        if not path.exists():
            return None
        entry = json.loads(path.read_text(encoding="utf-8"))
        age = (dt.date.fromisoformat(today)
               - dt.date.fromisoformat(entry["fetched_at"][:10])).days
        if age > self.ttl_days(method):
            return None
        return entry

    def cache_put(self, method: str, body: dict, data: dict, status: str,
                  today: str) -> None:
        path = self._cache_path(self.cache_key(method, body))
        path.write_text(json.dumps({
            "method": method, "body": body, "status": status,
            "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "data": data,
        }, ensure_ascii=False), encoding="utf-8")

    # ── Вызов ────────────────────────────────────────────────────────────
    def call(self, method: str, body: dict, *, reason: str, cluster: str | None = None,
             phrase: str = "", today: str | None = None) -> dict:
        """Единственная точка обращения к API. Возвращает {status, data, cost, source}."""
        today = today or self.budget.today

        cached = self.cache_get(method, body, today)
        if cached is not None:
            self.budget.record(method=method, phrase=phrase, cluster=cluster,
                               reason=reason, cache_hit=True,
                               status=cached["status"])
            return {"status": cached["status"], "data": cached["data"],
                    "cost_rub": 0.0, "source": "cache"}

        allowed, why = self.budget.can_spend(method, reason)
        if not allowed:
            self.stopped_by = why
            return {"status": "budget_blocked", "data": None, "cost_rub": 0.0,
                    "source": "budget", "reason": why}

        if self.dry_run:
            self.planned.append({"method": method, "phrase": phrase, "reason": reason,
                                 "cluster": cluster,
                                 "cost_rub": config.price_of(method, today, self.cfg)})
            return {"status": "dry_run", "data": None,
                    "cost_rub": config.price_of(method, today, self.cfg),
                    "source": "dry_run"}

        path = METHOD_PATH[method]
        try:
            resp = limiter_mod.with_retry(
                lambda: self.session.post(BASE + path, json=body,
                                          headers=self.headers(), timeout=40),
                limiter=self.limiter)
        except limiter_mod.QuotaExhausted as e:
            self.stopped_by = f"часовая квота исчерпана: {str(e)[:120]}"
            return {"status": "quota_exceeded", "data": None, "cost_rub": 0.0,
                    "source": "quota"}
        except Exception as e:                                  # сеть не поднялась
            self.budget.record(method=method, phrase=phrase, cluster=cluster,
                               reason=reason, cache_hit=False,
                               status=f"network_error:{type(e).__name__}")
            return {"status": "network_error", "data": None,
                    "cost_rub": config.price_of(method, today, self.cfg),
                    "source": "error"}

        if resp.status_code != 200:
            self.budget.record(method=method, phrase=phrase, cluster=cluster,
                               reason=reason, cache_hit=False,
                               status=f"http_{resp.status_code}")
            return {"status": f"http_{resp.status_code}", "data": None,
                    "cost_rub": config.price_of(method, today, self.cfg),
                    "source": "error"}

        data = resp.json()
        status = "ok" if data else "below_threshold"
        self.cache_put(method, body, data, status, today)
        return {"status": status, "data": data,
                "cost_rub": config.price_of(method, today, self.cfg), "source": "api"}

    # ── Удобные обёртки ──────────────────────────────────────────────────
    def top(self, phrase: str, *, reason: str, cluster: str | None = None,
            num_phrases: int | None = None, region: str | None = None) -> dict:
        c = self.cfg["collection"]
        body = {"phrase": phrase,
                "numPhrases": num_phrases or c["num_phrases"],
                "regions": [region or c["region_id"]]}
        return self.call("getTop", body, reason=reason, cluster=cluster, phrase=phrase)

    def dynamics(self, phrase: str, *, reason: str, cluster: str | None = None,
                 days: int = 365, region: str | None = None,
                 today: str | None = None) -> dict:
        end = dt.date.fromisoformat(today or self.budget.today)
        start = end - dt.timedelta(days=days)
        body = {"phrase": phrase, "period": "PERIOD_MONTHLY",
                "regions": [region or self.cfg["collection"]["region_id"]],
                "fromDate": f"{start.isoformat()}T00:00:00Z",
                "toDate": f"{end.isoformat()}T00:00:00Z"}
        return self.call("getDynamics", body, reason=reason, cluster=cluster,
                         phrase=phrase)

    def regions(self, phrase: str, *, reason: str, cluster: str | None = None) -> dict:
        return self.call("getRegionsDistribution", {"phrase": phrase},
                         reason=reason, cluster=cluster, phrase=phrase)
