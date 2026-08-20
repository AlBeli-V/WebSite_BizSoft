#!/usr/bin/env python3
"""Проверка возможности оплаты картой на сайте вендора.

Зачем: BIZSoft оплачивает подписки за клиента. Если вендор принимает карту
на своём сайте — сделка выполнима сразу. Если продаёт только через отдел
продаж и договор — это другая модель работы, её нужно решать отдельно.
Поэтому рекомендация «добавить вендора» без ответа на этот вопрос неполна.

Как: запрашивается страница тарифов и в её разметке ищутся признаки
самостоятельной покупки — платёжные системы, формы оплаты, кнопки покупки,
цены. Отдельно распознаётся модель «только через отдел продаж».

Это эвристика, а не доказательство. Вердикт «карта» означает, что признаки
найдены; подтверждение — при первой сделке. Отсутствие признаков не означает
отказ: страница могла не открыться или прятать оплату за входом.

Проверяются только вендоры, которых на сайте ещё нет. Каталог собран
руководителем, каналы закупки по нему уже отработаны — вопрос «принимают ли
карту» к ним не относится. Для существующих карточек Вордстат работает на
другую задачу: усиление семантики и рост в выдаче.

Запускается на раннере: сайты вендоров недоступны из среды мониторинга.
Запуск: python3 scripts/seo/wordstat/payment_check.py [--limit N]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import time

import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import discovery as D  # noqa: E402
import vendor_expansion as VX  # noqa: E402

CANDIDATES = pathlib.Path("reports/seo/wordstat/vendor-candidates.json")
CACHE = pathlib.Path("reports/seo/wordstat/payment-check.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 15
PAUSE = 0.5

# Признаки самостоятельной оплаты картой.
CARD_MARKERS = [
    "visa", "mastercard", "american express", "credit card", "debit card",
    "card number", "pay with card", "оплата картой",
    "stripe", "paddle", "fastspring", "braintree", "chargebee", "recurly",
    "js.stripe.com", "checkout.stripe", "checkout.paddle",
]
BUY_MARKERS = [
    "buy now", "subscribe now", "get started", "start free trial", "upgrade now",
    "add to cart", "/checkout", "purchase", "choose plan", "select plan",
]
PRICE_PATTERN = re.compile(
    r"(\$\s?\d|\d+\s?(usd|eur|€)|per\s+(month|user|seat)|/\s?(mo|month|user))", re.I)
SALES_ONLY = [
    "contact sales", "talk to sales", "request a quote", "request pricing",
    "contact us for pricing", "get a demo", "book a demo",
]
GUESS_PATHS = ("/pricing", "/plans", "/pricing/", "/plans-and-pricing", "/buy")
# Домен угадывается не только в зоне .com: у части сервисов основной адрес в
# .app, .ai или .io. Без www часть сайтов отвечает отказом на уровне DNS,
# поэтому проверяются оба варианта.
GUESS_HOSTS = ("www.{slug}.com", "{slug}.com", "{slug}.app", "{slug}.ai", "{slug}.io")


def guess_urls(brand: str, explicit: str | None) -> list[str]:
    """Адреса-кандидаты. Явный адрес идёт первым, но не отменяет запасные.

    Явный адрес может устареть или закрыться защитой от ботов; тогда проверка
    продолжается по угаданным, а не сдаётся с вердиктом «сайт не открылся».
    """
    slug = re.sub(r"[^a-z0-9]+", "", brand.lower())
    urls = [explicit] if explicit else []
    for host in GUESS_HOSTS:
        for path in GUESS_PATHS[:2]:
            urls.append(f"https://{host.format(slug=slug)}{path}")
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out[:8]


def fetch(url: str) -> tuple[str | None, int | None, str | None]:
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en"},
                         timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as e:
        return None, None, f"{type(e).__name__}"
    if r.status_code != 200:
        return None, r.status_code, f"http_{r.status_code}"
    return r.text.lower(), r.status_code, None


def classify(html: str) -> dict:
    card = sorted({m for m in CARD_MARKERS if m in html})
    buy = sorted({m for m in BUY_MARKERS if m in html})
    sales = sorted({m for m in SALES_ONLY if m in html})
    has_price = bool(PRICE_PATTERN.search(html))

    if card and (buy or has_price):
        verdict, note = "card", "найдены признаки самостоятельной оплаты картой"
    elif buy and has_price:
        verdict, note = ("likely_card",
                         "есть цены и кнопки покупки, платёжная система не опознана")
    elif sales and not has_price:
        verdict, note = "sales_only", "покупка только через отдел продаж"
    else:
        verdict, note = "unknown", "признаков оплаты на странице не найдено"

    return {"verdict": verdict, "note": note, "card_markers": card[:6],
            "buy_markers": buy[:4], "sales_markers": sales[:3],
            "has_prices": has_price}


def check(brand: str, explicit: str | None) -> dict:
    for url in guess_urls(brand, explicit):
        html, code, err = fetch(url)
        time.sleep(PAUSE)
        if html is None:
            continue
        result = classify(html)
        return {**result, "url": url, "http_status": code,
                "checked_at": dt.date.today().isoformat()}
    return {"verdict": "unreachable", "note": "страница тарифов не открылась",
            "url": (explicit or guess_urls(brand, None)[0]), "http_status": None,
            "card_markers": [], "buy_markers": [], "sales_markers": [],
            "has_prices": False, "checked_at": dt.date.today().isoformat()}


def load_cache() -> dict:
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


# Неудачная проверка живёт в кэше недолго: «сайт не открылся» — это отсутствие
# ответа, а не ответ. Держать такой вердикт месяц значит месяц не знать правды,
# тогда как адрес мог быть уточнён или защита от ботов снята.
RETRY_TTL_DAYS = 3
RETRY_VERDICTS = ("unreachable", "unknown")


def fresh(entry: dict, ttl_days: int) -> bool:
    try:
        age = (dt.date.today() - dt.date.fromisoformat(entry["checked_at"])).days
    except (KeyError, ValueError):
        return False
    if entry.get("verdict") in RETRY_VERDICTS:
        return age <= RETRY_TTL_DAYS
    return age <= ttl_days


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--only", default="", help="проверить только эти бренды, через запятую")
    args = ap.parse_args()

    cfg = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    ttl = cfg.get("payment_check", {}).get("cache_ttl_days", 30)
    cache = load_cache()
    only = {b.strip().lower() for b in args.only.split(",") if b.strip()}

    # Вендоры каталога из проверки исключены: их выбрали и завели осознанно,
    # канал покупки по ним уже есть. Проверка отвечает на вопрос только по тем,
    # кого на сайте нет и кого предлагается добавить.
    site = D.site_vendors()
    russian = cfg.get("russian_vendors", [])
    in_catalogue = [item["brand"] for item in cfg["candidates"]
                    if VX.already_in_catalogue(item["brand"], site)
                    or VX.is_russian(item["brand"], russian)]
    for brand in in_catalogue:
        cache.pop(brand, None)
    if in_catalogue:
        print(f"вне проверки — уже в каталоге: {len(in_catalogue)}")

    checked = skipped = 0
    for item in cfg["candidates"]:
        if checked >= args.limit:
            break
        brand = item["brand"]
        if brand in in_catalogue:
            continue
        if only and brand.lower() not in only:
            continue
        entry = cache.get(brand)
        if entry and fresh(entry, ttl):
            skipped += 1
            continue
        result = check(brand, item.get("pricing_url"))
        cache[brand] = {**result, "kind": item.get("kind")}
        checked += 1
        print(f"  {brand[:28]:30} {result['verdict']:14} {result['note']}")

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    counts: dict[str, int] = {}
    for v in cache.values():
        counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
    print(f"\nпроверено сейчас: {checked}, из кэша: {skipped}, всего в кэше: {len(cache)}")
    print(f"итоги: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
