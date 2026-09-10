#!/usr/bin/env python3
"""Сторож доменов: сроки, статусы и регистратор по RDAP.

Заведён 08.09.2026. Повод — постоянная блокировка аккаунта регистратора в
группе TurnCommerce: домен остаётся единственным активом проекта, потеря
которого необратима, а узнать о ней сегодня можно только вручную открыв
кабинет. Сторож смотрит на домен снаружи, поэтому видит и просрочку, и
блокировку со стороны регистратора, и смену регистратора — независимо от
того, пускают ли нас в панель.

Источник — RDAP (bootstrap IANA): протокол обязателен для gTLD, отвечает
структурой, а не текстом. Для зон без RDAP (в том числе .ru и .рф) шаг
честно пишет «нет RDAP-сервера для зоны» и помечает домен как непроверенный,
а не как исправный.

Список доменов и пороги — ops/accounts/registry.json, ключ domains.
Запуск: python3 scripts/ops/domain_watch.py [--registry PATH] [--today YYYY-MM-DD]
Код возврата 1 — есть находки; 0 — все домены проверены и в порядке.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "ops" / "accounts" / "registry.json"
BOOTSTRAP = "https://data.iana.org/rdap/dns.json"
TIMEOUT = 30

# Статусы, которые означают, что домен уже в пути к освобождению или
# заморожен реестром: их нельзя увидеть «в норме».
ALARM_STATUSES = {
    "pending delete", "redemption period", "pending restore",
    "client hold", "server hold", "pending transfer",
}
# Замки на трансфер — норма, а не находка: они защищают домен от угона.
LOCK_STATUSES = {"client transfer prohibited", "server transfer prohibited"}


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/rdap+json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def rdap_base(zone: str, bootstrap: dict) -> str | None:
    """Адрес RDAP-сервера зоны по служебному файлу IANA."""
    for zones, servers in bootstrap.get("services", []):
        if zone in (z.lower() for z in zones) and servers:
            return servers[0].rstrip("/")
    return None


def registrar_name(record: dict) -> str | None:
    for entity in record.get("entities", []) or []:
        if "registrar" not in (entity.get("roles") or []):
            continue
        vcard = entity.get("vcardArray") or []
        if len(vcard) > 1:
            for item in vcard[1]:
                if item and item[0] == "fn":
                    return item[3]
        if entity.get("handle"):
            return str(entity["handle"])
    return None


def expiry_date(record: dict) -> dt.date | None:
    for event in record.get("events", []) or []:
        if event.get("eventAction") == "expiration":
            raw = (event.get("eventDate") or "").replace("Z", "+00:00")
            try:
                return dt.datetime.fromisoformat(raw).date()
            except ValueError:
                return None
    return None


def check(domain: dict, bootstrap: dict, today: dt.date) -> tuple[list[str], bool]:
    """Строки отчёта по одному домену и признак находки."""
    name = domain["name"]
    zone = name.rsplit(".", 1)[-1].lower()
    lines: list[str] = []
    bad = False

    base = rdap_base(zone, bootstrap)
    if not base:
        # Не «порядок» и не «поломка сторожа»: зона просто не отдаёт RDAP.
        return [f"⚠️ {name}: нет RDAP-сервера для зоны .{zone} — проверять вручную"], True

    try:
        record = fetch(f"{base}/domain/{name}")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as err:
        return [f"❌ {name}: RDAP не ответил ({err})"], True

    expires = expiry_date(record)
    warn_days = int(domain.get("warn_days", 60))
    if expires is None:
        lines.append(f"❌ {name}: в ответе RDAP нет даты истечения")
        bad = True
    else:
        left = (expires - today).days
        if left < 0:
            lines.append(f"❌ {name}: срок истёк {expires.isoformat()} ({-left} дн. назад)")
            bad = True
        elif left <= warn_days:
            lines.append(f"❌ {name}: до истечения {left} дн. (порог {warn_days}), {expires.isoformat()}")
            bad = True
        else:
            lines.append(f"✅ {name}: до истечения {left} дн., {expires.isoformat()}")

    statuses = [str(s).lower() for s in (record.get("status") or [])]
    alarms = sorted(set(statuses) & ALARM_STATUSES)
    if alarms:
        lines.append(f"❌ {name}: статусы реестра — {', '.join(alarms)}")
        bad = True
    if not set(statuses) & LOCK_STATUSES:
        lines.append(f"⚠️ {name}: замок на трансфер снят — домен можно увести")
        bad = True

    actual = registrar_name(record)
    expected = domain.get("expected_registrar")
    if expected is None:
        lines.append(f"⚠️ {name}: регистратор — «{actual or 'не определён'}»; "
                     "занести в expected_registrar реестра, чтобы ловить смену")
        bad = True
    elif actual and actual.strip().lower() != str(expected).strip().lower():
        lines.append(f"❌ {name}: регистратор «{actual}», в реестре «{expected}»")
        bad = True
    else:
        lines.append(f"✅ {name}: регистратор «{actual}» совпадает с реестром")

    return lines, bad


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=str(REGISTRY))
    parser.add_argument("--today", default=None, help="дата отсчёта, по умолчанию сегодня (UTC)")
    args = parser.parse_args()

    registry = json.loads(pathlib.Path(args.registry).read_text(encoding="utf-8"))
    domains = registry.get("domains") or []
    if not domains:
        print("❌ в реестре нет ни одного домена — сторожу нечего проверять")
        return 1

    today = (dt.date.fromisoformat(args.today) if args.today
             else dt.datetime.now(dt.timezone.utc).date())
    bootstrap = fetch(BOOTSTRAP)

    report: list[str] = []
    found = False
    for domain in domains:
        lines, bad = check(domain, bootstrap, today)
        report.extend(lines)
        found = found or bad

    print("\n".join(report))
    print(f"\nПроверено доменов: {len(domains)}; находок: {'есть' if found else 'нет'}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
