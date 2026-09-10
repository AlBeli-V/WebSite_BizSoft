#!/usr/bin/env python3
"""Сторож регистраций на внешних площадках.

Поручение руководителя 10.09.2026: «раз в неделю проверяешь список
регистраций фактических и напоминаешь про те, где ещё не регистрировались».

Реестр `data/marketing/platform-accounts.json` заполняется руками, а руками
заполненный реестр расходится с жизнью молча: профиль заведён, а строка
осталась `not_registered` (так было с Яндекс Бизнесом и Дзеном — обе
площадки работали месяцами, пока реестр числил их незаведёнными), либо
наоборот — строка есть, а профиль удалён площадкой. Поэтому сторож не верит
полю `status` на слово, а дёргает записанный адрес живым запросом.

Три исхода на площадку:

* **записанное проверено** — профиль (или доказательство связки из
  `check_url`, как товарный фид Яндекс Бизнеса) отвечает кодом 200 и содержит
  ожидаемый маркер. Только это считается фактической регистрацией;
* **записанное не сходится** — адрес есть, а ответа нет: это находка, прогон
  краснеет, потому что молчащий профиль означает потерю, а не ожидание;
* **регистрации нет** — площадка ждёт человека. Это не сбой, а напоминание:
  прогон остаётся зелёным, а письмо руководителю перечисляет площадки по
  волнам со ссылками, где заводить профиль.

Площадки с `check: manual` (страницу рисует JavaScript, статический запрос
ничего не доказывает) сторож не дёргает и выносит отдельным списком: честнее
показать «сверять вручную», чем выдать пустой каркас за проверку.

Запуск:
  python3 scripts/ops/registrations_watch.py [--registry PATH]
                                             [--report PATH] [--json PATH]
Код возврата 1 — есть находки по записанным профилям; 0 — находок нет.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data" / "marketing" / "platform-accounts.json"
TIMEOUT = 25
# Часть площадок отдаёт роботу с пустым User-Agent заглушку или 403, поэтому
# представляемся честно и узнаваемо: это сторож проекта, а не аноним.
UA = "BIZSoft-registrations-watch/1.0 (+https://biz-soft.pro)"

# Статусы реестра, при которых площадка ждёт человека.
PENDING = {"not_registered"}
# Статусы, при которых напоминать не нужно: решение уже принято.
QUIET = {"deferred", "rejected"}
# Читаемые названия волн.
WAVES = {
    1: "Первая волна — заводить первыми",
    2: "Вторая волна — после первых публикаций",
    3: "Третья волна — брендовое присутствие",
}


def fetch(url: str) -> tuple[int | None, str]:
    """Код ответа и тело страницы; при сетевой ошибке код None и текст ошибки."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read(400_000).decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        # Тело ошибки читается намеренно: у наших же маршрутов там сказано,
        # почему закрыто («Фид не опубликован.»), и без этого еженедельная
        # тревога не отличает снятый по решению фид от сломанного маршрута.
        try:
            body = exc.read(2000).decode("utf-8", errors="replace").strip()
        except OSError:
            body = ""
        return exc.code, body
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return None, str(exc)


def check_account(acc: dict) -> dict:
    """Проверка одной записи реестра. Сеть трогается только здесь."""
    target = acc.get("check_url") or acc.get("url") or ""
    if acc.get("check") == "manual":
        why = ("адрес не записан, и страницу площадка рисует JavaScript"
               if not target else "страницу рисует JavaScript")
        return {"state": "manual", "target": target,
                "detail": f"{why} — сверять вручную"}
    if not target:
        return {"state": "no_address", "target": "",
                "detail": "адрес не записан — прислать, тогда сторож начнёт проверять"}

    code, body = fetch(target)
    if code is None:
        return {"state": "failed", "target": target, "detail": f"нет ответа: {body}"}
    if code == 403:
        # 403 — это «робота не пускают», а не «профиля нет»: выдавать такое
        # за пропажу профиля значит поднимать ложную тревогу каждую неделю.
        return {"state": "manual", "target": target,
                "detail": "площадка не пускает робота (403) — сверять вручную"}
    if code != 200:
        why = f": {body}" if body else ""
        return {"state": "failed", "target": target, "detail": f"код ответа {code}{why}"}

    marker = acc.get("check_marker") or ""
    if marker and marker.lower() not in body.lower():
        return {"state": "failed", "target": target,
                "detail": f"отвечает, но маркера «{marker}» на странице нет"}
    return {"state": "ok", "target": target,
            "detail": "отвечает" + (f", маркер «{marker}» на месте" if marker else "")}


def collect(registry: pathlib.Path) -> dict:
    data = json.loads(registry.read_text(encoding="utf-8"))
    checked, failed, manual, no_address, pending, quiet = [], [], [], [], [], []
    for acc in data.get("accounts", []):
        status = acc.get("status", "")
        if status in QUIET:
            quiet.append(acc)
            continue
        if status in PENDING:
            pending.append(acc)
            continue
        result = check_account(acc)
        row = {**acc, **result}
        {"ok": checked, "failed": failed,
         "manual": manual, "no_address": no_address}[result["state"]].append(row)
    return {"checked": checked, "failed": failed, "manual": manual,
            "no_address": no_address, "pending": pending, "quiet": quiet}


def wave_title(wave) -> str:
    return WAVES.get(wave, "Без волны")


def render(res: dict) -> str:
    out: list[str] = []
    add = out.append

    add("Фактические регистрации на внешних площадках")
    add("")
    if res["checked"]:
        add(f"Проверено живым запросом — {len(res['checked'])}:")
        for a in res["checked"]:
            add(f"  ✓ {a['platform']} — {a['target']} ({a['detail']})")
        add("")
    if res["failed"]:
        add(f"НЕ СХОДИТСЯ — {len(res['failed'])}:")
        for a in res["failed"]:
            add(f"  ✗ {a['platform']} — {a['target']}: {a['detail']}")
        add("")
    if res["manual"]:
        add(f"Сверять вручную — {len(res['manual'])}:")
        for a in res["manual"]:
            add(f"  · {a['platform']} — {a['detail']}")
        add("")
    if res["no_address"]:
        add(f"Зарегистрированы, но адрес профиля не записан — {len(res['no_address'])}:")
        for a in res["no_address"]:
            add(f"  · {a['platform']} — прислать адрес, он нужен для sameAs разметки")
        add("")

    if res["pending"]:
        add(f"Регистрации ещё нет — {len(res['pending'])}:")
        for wave in sorted({a.get("wave") for a in res["pending"]},
                           key=lambda w: (w is None, w)):
            add("")
            add(f"  {wave_title(wave)}")
            for a in [x for x in res["pending"] if x.get("wave") == wave]:
                add(f"    {a['platform']} — {a.get('signup_url') or 'адрес регистрации не записан'}")
                add(f"      зачем: {a.get('purpose', '')}")
        add("")
    else:
        add("Площадок без регистрации не осталось.")
        add("")

    if res["quiet"]:
        names = ", ".join(a["platform"] for a in res["quiet"])
        add(f"Не напоминаем (решение принято): {names}")
        add("")

    add("Реестр — data/marketing/platform-accounts.json, "
        "данные для профилей — docs/marketing/external/platform-registry.md.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", type=pathlib.Path, default=REGISTRY)
    ap.add_argument("--report", type=pathlib.Path,
                    help="куда записать отчёт (по умолчанию только stdout)")
    ap.add_argument("--json", dest="json_out", type=pathlib.Path,
                    help="куда записать машинную сводку для workflow")
    args = ap.parse_args()

    res = collect(args.registry)
    report = render(res)
    print(report)
    if args.report:
        args.report.write_text(report + "\n", encoding="utf-8")
    if args.json_out:
        args.json_out.write_text(json.dumps({
            "checked": len(res["checked"]),
            "failed": len(res["failed"]),
            "manual": len(res["manual"]),
            "no_address": len(res["no_address"]),
            "pending": len(res["pending"]),
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if res["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
