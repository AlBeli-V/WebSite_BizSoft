#!/usr/bin/env python3
"""Контроль баланса Yandex Cloud под нужды Wordstat и SERP-анализа.

Поручение руководителя 30.08.2026: баланс пополнен на 10 000 ₽; следить за
остатком и при прогнозной нехватке заранее просить пополнение письмом.

Кабинет Яндекса реального остатка нашему API-ключу не отдаёт, поэтому
остаток — РАСЧЁТНЫЙ: базовая точка (пополнение) минус расход по нашим же
append-only журналам. Wordstat пишет фактические cost_rub; SERP-вызовы
оцениваются консервативно по дневному синхронному тарифу до сверки с
детализацией биллинга. Это честная оценка сверху: реальный остаток может
быть только больше расчётного (ночной тариф дешевле).

Запуск: python3 scripts/seo/cloud_budget.py [дата] [--notify]
Выход:  reports/seo/intelligence/cloud-budget.json;
        --notify — при needs_topup и отсутствии свежего уведомления шлёт
        письмо-запрос пополнения (SMTP из env, как у seo-report-email).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys

BASE = pathlib.Path("reports/seo")
BALANCE_FILE = BASE / "intelligence" / "cloud-balance.json"
BILLING_FILE = BASE / "intelligence" / "cloud-billing.json"
HISTORY_FILE = BASE / "intelligence" / "cloud-balance-history.jsonl"
OUT_FILE = BASE / "intelligence" / "cloud-budget.json"
NOTICE_FILE = BASE / "intelligence" / "cloud-budget-notice.txt"
WORDSTAT_LEDGER_DIR = BASE / "wordstat" / "ledger"
SERP_LEDGER_DIR = BASE / "serp" / "ledger"

BILLING_FRESH_DAYS = 2   # старше — факт биллинга устарел, живём на оценке

# Консервативная оценка стоимости SERP-запроса (дневной синхронный тариф,
# ≈122 000 ₽ / 250 000 запросов, НДС включён) — фолбэк, когда фактическая
# цена из прайса биллинга недоступна (см. serp_cost_from_skus).
SERP_COST_RUB = 0.49


def serp_cost_from_skus(skus: list[dict]) -> float | None:
    """Фактическая цена SERP-запроса из прайса биллинга.

    Урок выборки 30.08: широкий фильтр имён притянул чужой SKU (распознавание
    аудио, тариф за секунду) — цена запроса стала бессмысленной. Поэтому:
    только единица «за 1000 запросов», только текстовый поиск (deferred text
    requests / search), явные исключения (wordstat, audio, recognition,
    «web search tool» — инструмент для AI-ассистентов по 915 ₽/1000, не наш
    SERP). Сбор идёт ночным отложенным режимом — при наличии ночного SKU
    берётся он, иначе минимальный из подходящих.
    """
    candidates = []
    for s in skus or []:
        name = (s.get("name") or "").lower()
        if "1k" not in (s.get("unit") or ""):
            continue
        if any(x in name for x in ("wordstat", "audio", "recognition", "tool")):
            continue
        if not any(x in name for x in ("text request", "search", "поиск")):
            continue
        price = s.get("price_rub")
        if price is None or price <= 0:
            continue
        candidates.append((name, price / 1000.0))
    if not candidates:
        return None
    night = [p for n, p in candidates if "night" in n or "ноч" in n]
    best = min(night) if night else min(p for _, p in candidates)
    return round(best, 4)

RUNWAY_ALERT_DAYS = 14      # «нехватка через неделю» + лаг на пополнение
NOTICE_COOLDOWN_DAYS = 3    # не чаще одного письма в три дня
TREND_WINDOW_DAYS = 7


def _entry_date(e: dict) -> str | None:
    for key in ("at", "date", "ts", "when"):
        v = e.get(key)
        if isinstance(v, str) and len(v) >= 10:
            return v[:10]
    return None


def _iter_ledger(dir_: pathlib.Path):
    if not dir_.exists():
        return
    for p in sorted(dir_.glob("*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def spend_between(start: str, end: str,
                  serp_cost: float = SERP_COST_RUB) -> dict:
    """Расход [start; end] по журналам. Записи без даты считаются расходом
    (консервативно), если файл месяца не старше базовой точки."""
    ws = serp_n = 0.0
    for e in _iter_ledger(WORDSTAT_LEDGER_DIR):
        d = _entry_date(e)
        if d is None or start <= d <= end:
            ws += float(e.get("cost_rub") or 0)
    for e in _iter_ledger(SERP_LEDGER_DIR):
        d = _entry_date(e)
        if d is None or start <= d <= end:
            serp_n += 1
    return {"wordstat_rub": round(ws, 2),
            "serp_requests": int(serp_n),
            "serp_cost_rub_each": serp_cost,
            "serp_rub_estimate": round(serp_n * serp_cost, 2),
            "total_rub": round(ws + serp_n * serp_cost, 2)}


def load_balance() -> dict | None:
    if not BALANCE_FILE.exists():
        return None
    try:
        return json.loads(BALANCE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def billing_actual(date_s: str) -> dict | None:
    """Свежий факт из Billing API (yc_billing.py), иначе None."""
    if not BILLING_FILE.exists():
        return None
    try:
        data = json.loads(BILLING_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    fetched = (data.get("date") or data.get("fetched_at") or "")[:10]
    try:
        age = (dt.date.fromisoformat(date_s)
               - dt.date.fromisoformat(fetched)).days
    except ValueError:
        return None
    return data if 0 <= age <= BILLING_FRESH_DAYS else None


def history_daily_rate(date_s: str) -> float | None:
    """Фактический расход в день — по дельтам остатка из истории биллинга.

    Пополнение выглядит ростом остатка — такая дельта в расход не идёт.
    Нужны минимум две точки; окно — последние 8 точек (≈неделя).
    """
    if not HISTORY_FILE.exists():
        return None
    points = []
    for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            points.append((e["date"], float(e["balance"])))
        except (ValueError, KeyError, TypeError):
            continue
    points = sorted(dict(points).items())[-8:]
    if len(points) < 2:
        return None
    spent = days = 0.0
    for (d1, b1), (d2, b2) in zip(points, points[1:]):
        gap = (dt.date.fromisoformat(d2) - dt.date.fromisoformat(d1)).days
        if gap <= 0:
            continue
        delta = b1 - b2
        if delta > 0:           # рост остатка = пополнение, не расход
            spent += delta
            days += gap
    return round(spent / days, 2) if days > 0 else None


def build(date_s: str) -> dict:
    bal = load_balance()
    if not bal or not (bal.get("baseline") or {}).get("date"):
        return {"available": False,
                "reason": "базовая точка баланса не задана "
                          "(intelligence/cloud-balance.json)"}
    baseline = bal["baseline"]
    start = baseline["date"]
    amount = float(baseline.get("balance_rub") or 0)
    for t in bal.get("topups") or []:
        if (t.get("date") or "") >= start:
            amount += float(t.get("amount_rub") or 0)

    act = billing_actual(date_s)
    serp_cost = (serp_cost_from_skus((act or {}).get("skus"))
                 or SERP_COST_RUB)
    spent = spend_between(start, date_s, serp_cost)
    balance = round(amount - spent["total_rub"], 2)

    week_start = (dt.date.fromisoformat(date_s)
                  - dt.timedelta(days=TREND_WINDOW_DAYS - 1)).isoformat()
    week = spend_between(max(week_start, start), date_s, serp_cost)
    observed_days = min(
        TREND_WINDOW_DAYS,
        (dt.date.fromisoformat(date_s) - dt.date.fromisoformat(start)).days + 1)
    daily = week["total_rub"] / observed_days if observed_days > 0 else 0.0
    source = "estimate"
    assumptions = ("остаток расчётный: базовая точка минус журналы; "
                   f"SERP оценён по {SERP_COST_RUB} ₽/запрос "
                   "(дневной тариф, оценка сверху)")

    # Факт из Billing API главнее оценки: реальный остаток кабинета и
    # реальный расход по дельтам остатка (поручение 30.08.2026).
    if act and act.get("balance_rub") is not None:
        balance = float(act["balance_rub"])
        source = "billing_api"
        hist_rate = history_daily_rate(date_s)
        if hist_rate is not None:
            daily = hist_rate
        assumptions = ("остаток фактический (Billing API); расход в день — "
                       + ("по дельтам остатка кабинета"
                          if hist_rate is not None else
                          "по журналам вызовов (история остатка ещё коротка)"))

    runway = round(balance / daily, 1) if daily > 0 else None
    needs = balance <= 0 or (runway is not None and runway < RUNWAY_ALERT_DAYS)
    return {
        "available": True,
        "date": date_s,
        "baseline": baseline,
        "balance_source": source,
        "balance_estimate_rub": round(balance, 2),
        "spent_since_baseline": spent,
        "week_spend_rub": week["total_rub"],
        "daily_rate_rub": round(daily, 2),
        "runway_days": runway,
        "needs_topup": needs,
        "billing_skus": (act or {}).get("skus") or [],
        "assumptions": assumptions,
    }


def _notice_recent(date_s: str) -> bool:
    if not NOTICE_FILE.exists():
        return False
    last = NOTICE_FILE.read_text(encoding="utf-8").strip()[:10]
    try:
        gap = (dt.date.fromisoformat(date_s) - dt.date.fromisoformat(last)).days
    except ValueError:
        return False
    return gap < NOTICE_COOLDOWN_DAYS


def send_topup_request(res: dict) -> bool:
    """Письмо-запрос пополнения. SMTP — те же параметры, что у писем отчёта."""
    import smtplib
    import ssl
    from email.message import EmailMessage
    from email.utils import formatdate

    pw = os.environ.get("SMTP_PASS", "")
    if not pw:
        print("SMTP_PASS не задан — письмо о пополнении не отправлено")
        return False
    host = os.environ.get("SMTP_HOST", "mail.hosting.reg.ru")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USER", "hello@biz-soft.pro")
    to = os.environ.get("MAIL_TO", "avbelyaev@biz-soft.pro")
    msg = EmailMessage()
    msg["From"] = f"BIZSoft аналитика <{user}>"
    msg["To"] = to
    msg["Subject"] = (f"Yandex Cloud: расчётный остаток "
                      f"{res['balance_estimate_rub']:.0f} ₽ — нужно пополнение")
    msg["Date"] = formatdate(localtime=True)
    runway = (f"{res['runway_days']:.0f} дн." if res.get("runway_days")
              is not None else "не определён (расхода ещё нет)")
    msg.set_content(
        f"Расчётный остаток баланса Yandex Cloud: "
        f"{res['balance_estimate_rub']:.2f} ₽ на {res['date']}.\n"
        f"Средний расход за 7 дней: {res['daily_rate_rub']:.2f} ₽/день "
        f"(Wordstat {res['spent_since_baseline']['wordstat_rub']:.2f} ₽ и "
        f"{res['spent_since_baseline']['serp_requests']} SERP-запросов "
        f"с базовой точки).\n"
        f"Прогнозный запас: {runway} — меньше порога "
        f"{RUNWAY_ALERT_DAYS} дн.\n\n"
        f"Прошу пополнить баланс Yandex Cloud под нужды Wordstat и "
        f"SERP-анализа.\n\n"
        f"Как читать: остаток расчётный (базовая точка минус наши журналы "
        f"вызовов); точная сверка — консоль Yandex Cloud, Биллинг → "
        f"Детализация.\n\n— автоматический контроль бюджета Growth Engine")
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=ctx, timeout=60) as s:
        s.login(user, pw)
        s.send_message(msg)
    NOTICE_FILE.write_text(res["date"], encoding="utf-8")
    print(f"письмо-запрос пополнения отправлено на {to}")
    return True


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    notify = "--notify" in sys.argv
    date_s = args[0] if args else dt.datetime.now(
        dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    res = build(date_s)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(res, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if notify and res.get("available") and res["needs_topup"]:
        if _notice_recent(date_s):
            print("уведомление уже отправлялось недавно — повтор не шлём")
        else:
            send_topup_request(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
