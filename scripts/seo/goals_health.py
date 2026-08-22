#!/usr/bin/env python3
"""Приёмка измерения конверсий после заведения целей.

Отвечает на один вопрос: начали ли цели собирать данные — и сообщает ответ
письмом руководителю. Живёт отдельно от ежедневного отчёта, потому что
отвечает на временный вопрос: первую неделю после границы измерения важно
знать, что счётчик действительно пишет, а дальше это становится рутиной.

Главное правило здесь то же, что во всей отчётности: ноль достижений — это
не «обращений не было». При трафике около семи визитов в день отсутствие
конверсий за сутки ожидаемо, и подавать его как провал нельзя.

Запуск: python3 scripts/seo/goals_health.py
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formatdate

import requests

LIMITS = pathlib.Path("reports/seo/measurement-limits.json")
REGISTRY = pathlib.Path("src/lib/analytics.ts")
MSK = dt.timezone(dt.timedelta(hours=3))
MAIL_WINDOW_DAYS = 7
API = "https://api-metrika.yandex.net"


def boundary() -> str | None:
    """Дата границы измерения из реестра пределов, а не из константы в коде."""
    try:
        limits = json.loads(LIMITS.read_text(encoding="utf-8"))["limits"]
    except (OSError, ValueError, KeyError):
        return None
    for lim in limits:
        if lim.get("metric") == "metrika.goal_events" and lim.get("resolved_on"):
            return lim["resolved_on"]
    return None


def key_goals() -> list[str]:
    """Конверсии из реестра целей: те, у кого key: true."""
    import re
    try:
        src = REGISTRY.read_text(encoding="utf-8")
    except OSError:
        return []
    return [m.group(1) for m in
            re.finditer(r"^\s{2}([a-z0-9_]+):\s*\{\s*ga4:\s*'[^']*',\s*key:\s*true", src, re.M)]


def fetch(counter: str, headers: dict) -> tuple[list[dict], dict]:
    """Список целей счётчика и достижения по ним за последние 7 дней."""
    r = requests.get(f"{API}/management/v1/counter/{counter}/goals",
                     headers=headers, timeout=30)
    if not r.ok:
        raise RuntimeError(f"не удалось прочитать цели: HTTP {r.status_code} {r.text[:200]}")
    goals = r.json().get("goals", [])

    by_event = {}
    for g in goals:
        for cond in g.get("conditions") or []:
            if cond.get("type") == "exact":
                by_event[cond.get("url", "")] = g

    reaches: dict[str, float] = {}
    if by_event:
        end = dt.datetime.now(MSK).date() - dt.timedelta(days=1)
        start = end - dt.timedelta(days=6)
        metrics = ",".join(f"ym:s:goal{g['id']}reaches" for g in by_event.values())
        r = requests.get(f"{API}/stat/v1/data", headers=headers, timeout=30, params={
            "ids": counter, "metrics": metrics, "accuracy": "full",
            "date1": start.isoformat(), "date2": end.isoformat(),
        })
        if r.ok:
            totals = r.json().get("totals") or []
            for (name, _), value in zip(by_event.items(), totals):
                reaches[name] = value
    return goals, reaches


def compose(goals: list[dict], reaches: dict, edge: str | None) -> tuple[str, str]:
    events = {c.get("url") for g in goals for c in (g.get("conditions") or [])
              if c.get("type") == "exact"}
    key = [g for g in key_goals()]
    live = {n: v for n, v in reaches.items() if v}
    working = bool(events)

    lines = [
        f"Проверка измерения конверсий за {dt.datetime.now(MSK):%d.%m.%Y}.",
        "",
    ]
    if not working:
        lines += ["Цели по событиям в счётчике не найдены — измерение не работает.",
                  "Это требует разбора: сайт события отправляет, счётчик их не принимает."]
        return "Цели Метрики: измерение не работает", "\n".join(lines)

    def plural(n: int, one: str, few: str, many: str) -> str:
        if n % 10 == 1 and n % 100 != 11:
            return one
        if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            return few
        return many

    lines += [f"Цели заведены и счётчик их принимает: {len(events)} "
              f"{plural(len(events), 'цель', 'цели', 'целей')} по событиям "
              f"из {len(goals)} всего.", ""]

    if live:
        lines += ["Уже зафиксировано за последние 7 дней:"]
        for name, value in sorted(live.items(), key=lambda kv: -kv[1]):
            mark = " (конверсия)" if name in key else ""
            lines.append(f"  — {name}{mark}: {value:.0f}")
    else:
        lines += ["Достижений по целям пока нет.",
                  "",
                  "Это ожидаемо и не является плохой новостью: при трафике около семи "
                  "визитов в день несколько суток без конверсий — обычное дело. "
                  "Важно другое: счётчик готов принимать события, чего до 21.08 не было."]

    lines += [
        "",
        "── Как читать эти числа ──",
        "",
        f"Граница сопоставимости — {edge or 'не задана'}. Сравнивать конверсии через "
        "эту дату нельзя ни в каком виде.",
        "",
        "Появление целевых событий после неё означает восстановление измерения, "
        "а не результат работ по продвижению: до этой даты сайт отправлял события "
        "в счётчик, который их отбрасывал.",
        "",
        "Историю обращений за прошлое брать из воронки заявок и скачиваний "
        "коммерческих предложений — там ноля никогда не было.",
        "",
        "Первую неделю числа считать предварительными: цели набирают статистику с нуля.",
    ]
    status = "данные пошли" if live else "счётчик готов, достижений пока нет"
    return f"Цели Метрики — {status}", "\n".join(lines)


def send(subject: str, body: str) -> None:
    host, port = os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])
    msg = EmailMessage()
    msg["From"] = f'BIZSoft аналитика <{os.environ["SMTP_USER"]}>'
    msg["To"] = os.environ["MAIL_TO"]
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=60) as sm:
            sm.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            sm.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        print(f"465/SSL не сработал ({e}), пробую 587/STARTTLS")
        with smtplib.SMTP(host, 587, timeout=60) as sm:
            sm.starttls(context=ssl.create_default_context())
            sm.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            sm.send_message(msg)


def main() -> int:
    token = os.environ.get("YANDEX_METRIKA_TOKEN", "").strip()
    counter = os.environ.get("YANDEX_METRIKA_COUNTER_ID", "").strip()
    if not token or not counter:
        print("нет YANDEX_METRIKA_TOKEN или YANDEX_METRIKA_COUNTER_ID", file=sys.stderr)
        return 1

    edge = boundary()
    goals, reaches = fetch(counter, {"Authorization": f"OAuth {token}"})
    subject, body = compose(goals, reaches, edge)
    print(subject, "\n\n", body, sep="")

    # Письмо — только в течение недели после границы, иначе ежедневное
    # подтверждение штатной работы превращается в шум, который перестают читать.
    force = os.environ.get("FORCE_MAIL") == "true"
    fresh = False
    if edge:
        age = (dt.datetime.now(MSK).date() - dt.date.fromisoformat(edge)).days
        fresh = 0 <= age <= MAIL_WINDOW_DAYS
    if not (force or fresh):
        print(f"\nПисьмо не отправляется: прошло больше {MAIL_WINDOW_DAYS} дней после границы.")
        return 0
    if not os.environ.get("SMTP_PASS"):
        print("SMTP_PASS не задан — письмо не отправлено", file=sys.stderr)
        return 1
    send(subject, body)
    print(f"\nПисьмо отправлено на {os.environ['MAIL_TO']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
