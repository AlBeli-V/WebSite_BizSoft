#!/usr/bin/env python3
"""CLI интеграции Yandex Direct — этап 1, только чтение.

Пока единственный режим — `--check`: диагностика подключения к кабинету
(наличие секретов, авторизация, доступ к списку кампаний, остаток баллов).
Сеть к Яндексу есть только у раннера GitHub Actions (workflow seo-direct.yml,
результат — комментарием в issue #22); из контейнера сессии egress закрыт.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent


def _load(name: str):
    """Импорт соседнего модуля по пути: имена вроде `client` слишком общие,
    чтобы полагаться на sys.path (рядом живёт scripts/seo/wordstat/client.py)."""
    spec = importlib.util.spec_from_file_location(f"seo_direct_{name}", _HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


client_mod = _load("client")


def _describe(res: dict) -> str:
    if res["status"] == "api_error":
        return f"код {res.get('error_code')}: {res.get('error') or 'без описания'}"
    return f"{res['status']}: {res.get('error', '')}".strip(": ")


def _fmt_campaign(c: dict) -> str:
    return (f"    - [{c.get('Id')}] {c.get('Name', '(без названия)')}"
            f" · {c.get('Type', '?')} · {c.get('State', '?')}/{c.get('Status', '?')}")


def check(session=None, sandbox: bool = False) -> tuple[str, bool]:
    """Диагностика подключения. Возвращает (текст отчёта, успех).

    Сначала боевой контур; при отказе авторизации пробуется песочница
    (по SEM-001 полный доступ к API может быть ещё не выдан).
    """
    lines = ["Yandex Direct API",
             "Mode: READ ONLY (запись заблокирована на уровне клиента)"]
    token, _ = client_mod.token_source()
    for name in client_mod.TOKEN_ENV_NAMES:
        state = "задан" if os.environ.get(name, "").strip() else "не задан"
        lines.append(f"Секрет {name}: {state}")
    login_env = os.environ.get(client_mod.CLIENT_LOGIN_ENV, "").strip()
    lines.append(f"Секрет {client_mod.CLIENT_LOGIN_ENV}: "
                 + ("задан" if login_env
                    else "не задан (для прямого рекламодателя не обязателен)"))

    if not token:
        lines.append("Authentication: НЕВОЗМОЖНА — токен не задан")
        lines.append("Итог: доступ НЕ подтверждён")
        return "\n".join(lines), False

    contours = [("песочница", True)] if sandbox else [("боевой", False),
                                                      ("песочница", True)]
    ok = False
    for label, is_sandbox in contours:
        cli = client_mod.DirectClient(sandbox=is_sandbox, session=session)
        host = cli.base.split("/")[2]
        lines.append(f"— Контур: {label} ({host})")

        acc = cli.account()
        if acc["status"] != "ok":
            lines.append(f"  Authentication: ошибка — {_describe(acc)}")
            continue                        # контур не пустил — пробуем следующий

        clients_list = (acc.get("data") or {}).get("Clients") or []
        first = clients_list[0] if clients_list else {}
        lines.append("  Authentication: OK")
        lines.append(f"  Account: {first.get('Login') or 'логин не возвращён'}"
                     f" (ClientId: {first.get('ClientId')})")

        camps = cli.campaigns()
        if camps["status"] != "ok":
            lines.append(f"  Campaign access: ошибка — {_describe(camps)}")
        else:
            items = (camps.get("data") or {}).get("Campaigns") or []
            if items:
                lines.append(f"  Campaign access: OK — кампаний: {len(items)}")
                lines.extend(_fmt_campaign(c) for c in items[:10])
                if len(items) > 10:
                    lines.append(f"    … и ещё {len(items) - 10}")
            else:
                lines.append("  Campaign access: OK — кабинет пуст (кампаний нет)")
            ok = True
        if cli.last_units:
            lines.append("  Units (израсходовано/доступно/суточный лимит): "
                         f"{cli.last_units}")
        break                               # авторизация прошла — дальше не пробуем

    lines.append("Итог: доступ подтверждён" if ok else "Итог: доступ НЕ подтверждён")
    return "\n".join(lines), ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Yandex Direct — этап 1, только чтение")
    ap.add_argument("--check", action="store_true", help="диагностика подключения")
    ap.add_argument("--sandbox", action="store_true",
                    help="проверять только песочницу (api-sandbox)")
    args = ap.parse_args()
    if args.check:
        sandbox = args.sandbox or bool(os.environ.get("DIRECT_SANDBOX", "").strip())
        text, ok = check(sandbox=sandbox)
        print(text)
        return 0 if ok else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
