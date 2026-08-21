#!/usr/bin/env python3
"""Конфигурация Wordstat Intelligence: тарифы, квоты, бюджет, пороги.

Тарифы вынесены в конфигурацию с датой вступления в силу, а не зашиты в код:
цена меняется, и расчёты прошлых периодов должны считаться по действовавшему тарифу.

Ключевой факт, установленный аудитом 20.08.2026: при квоте 100 запросов в час
месячный расход упирается в 1 440–1 656 ₽, то есть бюджет 5 500 ₽ израсходовать
физически невозможно. Управляющее ограничение — квота и время, а не деньги.
Бюджет становится связывающим только при 500 запросов в час.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

CONFIG_PATH = pathlib.Path("reports/seo/wordstat/config.json")

DEFAULT = {
    "schema_version": "1.0.0",
    "currency": "RUB",
    "pricing": [
        {"method": "getTop", "api_path": "/topRequests",
         "price_per_1000": 20, "currency": "RUB", "effective_date": "2026-08-01"},
        {"method": "getDynamics", "api_path": "/dynamics",
         "price_per_1000": 20, "currency": "RUB", "effective_date": "2026-08-01"},
        {"method": "getRegionsDistribution", "api_path": "/regions",
         "price_per_1000": 50, "currency": "RUB", "effective_date": "2026-08-01"},
        {"method": "getRegionsTree", "api_path": "/getRegionsTree",
         "price_per_1000": 0, "currency": "RUB", "effective_date": "2026-08-01"},
    ],
    "quota": {
        "requests_per_second": 10,
        "requests_per_hour": 100,
        "requests_per_hour_target": 500,
        "confirmed_at": "2026-08-19",
        "source": "ответ сервиса: search-api.wordstatRequestsPerHour.rate "
                  "rate quota limit exceed: allowed 100 requests",
        "note": "Целевая квота 500/час не получена. Система готова к ней "
                "технически, но планирует расход по действующей.",
    },
    "budget": {
        "monthly_hard_cap_rub": 5500,
        "monthly_soft_stop_rub": 5000,
        "safety_reserve_rub": 500,
        "pilot_cap_rub": 500,
        "daily_cap_rub": 400,
    },
    "envelopes": {
        "discovery_gettop": 0.70,
        "dynamics": 0.20,
        "regions": 0.10,
        "note": "Ориентиры распределения, а не план обязательных расходов. "
                "Неизрасходованная доля не осваивается ради освоения.",
    },
    "collection": {
        "num_phrases": 300,
        "region_id": "225",
        "region_name": "Россия",
        "devices": "DEVICE_ALL",
        "match_type": "broad",
        "cache_ttl_days": 30,
        "dynamics_ttl_days": 30,
        "regions_ttl_days": 90,
    },
    "thresholds": {
        "min_frequency": 30,
        "empty_seed_streak_stop": 3,
        "duplicate_rate_stop": 0.85,
        "min_information_gain": 0.15,
        "max_expansion_depth": 2,
        "max_calls_per_vendor": 12,
        "max_calls_per_cluster": 8,
    },
    "tiers": {
        "A": {"max_items": 300, "dynamics_every_days": 7,
              "regions_every_days": 90},
        "B": {"max_items": 3000, "dynamics_every_days": 30, "regions_every_days": None},
        "C": {"max_items": None, "dynamics_every_days": None, "regions_every_days": None},
    },
}


def load() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(DEFAULT, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    return DEFAULT


def price_of(method: str, on_date: str | None = None, cfg: dict | None = None) -> float:
    """Цена одного вызова в рублях по тарифу, действовавшему на дату."""
    cfg = cfg or load()
    on_date = on_date or dt.date.today().isoformat()
    applicable = [p for p in cfg["pricing"]
                  if p["method"] == method and p["effective_date"] <= on_date]
    if not applicable:
        raise KeyError(f"нет тарифа для {method} на {on_date}")
    newest = max(applicable, key=lambda p: p["effective_date"])
    return newest["price_per_1000"] / 1000.0


def max_monthly_spend(cfg: dict | None = None, requests_per_hour: int | None = None,
                      mix: dict | None = None) -> float:
    """Сколько максимум можно потратить за 30 дней при заданной квоте.

    Показывает, является ли бюджет реальным ограничением. При 100 запросах в час
    ответ — нет: квота отсекает расход задолго до бюджета.
    """
    cfg = cfg or load()
    rph = requests_per_hour or cfg["quota"]["requests_per_hour"]
    mix = mix or {"getTop": cfg["envelopes"]["discovery_gettop"],
                  "getDynamics": cfg["envelopes"]["dynamics"],
                  "getRegionsDistribution": cfg["envelopes"]["regions"]}
    calls = rph * 24 * 30
    per_call = sum(share * price_of(method, cfg=cfg) for method, share in mix.items())
    return calls * per_call


def budget_is_binding(cfg: dict | None = None, requests_per_hour: int | None = None) -> bool:
    cfg = cfg or load()
    return max_monthly_spend(cfg, requests_per_hour) > cfg["budget"]["monthly_hard_cap_rub"]
