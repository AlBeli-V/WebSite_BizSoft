#!/usr/bin/env python3
"""Фактический биллинг Yandex Cloud: остаток, тарифы Search API, история.

Поручение руководителя 30.08.2026: анализировать тарифы, расходы и остатки
через API, а не расчётной оценкой.

Авторизация: авторизованный ключ сервисного аккаунта (JSON) в секрете
YC_BILLING_SA_KEY → JWT (PS256) → IAM-токен → Billing API. Сервисному
аккаунту нужна роль `billing.accounts.viewer` НА БИЛЛИНГ-АККАУНТЕ
(консоль → Биллинг → Права доступа), иначе список аккаунтов придёт пустым —
это диагностируется и печатается.

Пишет:
  intelligence/cloud-billing.json         — остаток, аккаунт, SKU Search API;
  intelligence/cloud-balance-history.jsonl — точка «дата → остаток» в день
                                            (фактический расход = дельта).

Без секрета шаг тихо пропускается (exit 0): контроль бюджета продолжает
жить на расчётной оценке cloud_budget.py.

Запуск: python3 scripts/seo/yc_billing.py  (env YC_BILLING_SA_KEY)
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import time

IAM_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
BILLING_URL = "https://billing.api.cloud.yandex.net/billing/v1"

BASE = pathlib.Path("reports/seo/intelligence")
OUT_FILE = BASE / "cloud-billing.json"
HISTORY_FILE = BASE / "cloud-balance-history.jsonl"

SKU_MARKERS = ("search api", "searchapi", "wordstat")


def iam_token(sa_key: dict) -> str:
    """Обмен авторизованного ключа СА на IAM-токен (JWT PS256, срок 6 мин)."""
    import jwt  # pyjwt[crypto]; ставится в workflow, в сессии не требуется
    import requests

    now = int(time.time())
    payload = {"aud": IAM_URL, "iss": sa_key["service_account_id"],
               "iat": now, "exp": now + 360}
    signed = jwt.encode(payload, sa_key["private_key"], algorithm="PS256",
                        headers={"kid": sa_key["id"]})
    r = requests.post(IAM_URL, json={"jwt": signed}, timeout=30)
    r.raise_for_status()
    return r.json()["iamToken"]


def _get(url: str, token: str, params: dict | None = None) -> dict:
    import requests
    r = requests.get(url, timeout=30, params=params or {},
                     headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()


def pick_account(accounts: list[dict]) -> dict | None:
    """Активный биллинг-аккаунт; при нескольких — первый активный."""
    active = [a for a in accounts if a.get("active")]
    return (active or accounts or [None])[0]


def sku_price(sku: dict) -> float | None:
    """Цена за единицу из последней версии тарифа SKU."""
    try:
        versions = sku.get("pricingVersions") or []
        rates = (versions[-1].get("pricingExpressions") or [{}])[0].get("rates") or []
        return float(rates[0]["unitPrice"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def relevant_skus(skus: list[dict]) -> list[dict]:
    """SKU наших сервисов: Search API (веб-поиск и Wordstat)."""
    out = []
    for s in skus:
        name = (s.get("name") or "").lower()
        if any(m in name for m in SKU_MARKERS):
            out.append({"id": s.get("id"), "name": s.get("name"),
                        "unit": s.get("pricingUnit"),
                        "price_rub": sku_price(s)})
    return out


def fetch_all_skus(token: str, account_id: str | None) -> list[dict]:
    skus, page_token = [], None
    for _ in range(30):     # страховка от бесконечного листинга
        params = {"currency": "RUB", "pageSize": "1000"}
        if account_id:
            params["billingAccountId"] = account_id
        if page_token:
            params["pageToken"] = page_token
        data = _get(f"{BILLING_URL}/skus", token, params)
        skus += data.get("skus") or []
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return skus


def append_history(date_s: str, balance: float):
    """Точка остатка — не чаще одной на дату (перезапуски не дублируют)."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if HISTORY_FILE.exists():
        for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
            try:
                if json.loads(line).get("date") == date_s:
                    return
            except ValueError:
                continue
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"date": date_s, "balance": balance}) + "\n")


def main() -> int:
    raw = os.environ.get("YC_BILLING_SA_KEY", "").strip()
    if not raw:
        print("YC_BILLING_SA_KEY не задан — фактический биллинг пропущен, "
              "бюджет живёт на расчётной оценке (как открыть доступ — "
              "docs/seo/growth-loop-audit-2026-08-30.md, этап 2d)")
        return 0
    try:
        sa_key = json.loads(raw)
        token = iam_token(sa_key)
    except Exception as e:  # noqa: BLE001
        print(f"не удалось получить IAM-токен: {type(e).__name__}: {e}")
        return 1
    try:
        accounts = _get(f"{BILLING_URL}/billingAccounts", token).get(
            "billingAccounts") or []
    except Exception as e:  # noqa: BLE001
        print(f"Billing API недоступен: {type(e).__name__}: {e}")
        return 1
    acc = pick_account(accounts)
    if not acc:
        print("список биллинг-аккаунтов пуст: сервисному аккаунту не выдана "
              "роль billing.accounts.viewer на биллинг-аккаунте "
              "(консоль → Биллинг → Права доступа)")
        return 1
    balance = float(acc.get("balance") or 0)
    date_s = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    try:
        skus = relevant_skus(fetch_all_skus(token, acc.get("id")))
    except Exception as e:  # noqa: BLE001
        skus = []
        print(f"тарифы SKU не прочитаны (не критично): {type(e).__name__}: {e}")
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps({
        "fetched_at": dt.datetime.now(dt.timezone.utc)
                        .isoformat(timespec="seconds"),
        "date": date_s,
        "account_id": acc.get("id"),
        "account_name": acc.get("name"),
        "currency": acc.get("currency"),
        "balance_rub": balance,
        "skus": skus,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    append_history(date_s, balance)
    print(f"биллинг: аккаунт {acc.get('id')}, остаток {balance:.2f} "
          f"{acc.get('currency', 'RUB')}, SKU наших сервисов: {len(skus)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
