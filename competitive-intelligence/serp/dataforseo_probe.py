#!/usr/bin/env python3
"""Проба DataForSEO SERP API: один платный запрос Google organic.

Проверяет: работают ли учётные данные, каков баланс, что возвращает выдача
Google по коммерческому запросу (регион Россия, язык русский, топ-20).
Аналог scripts/seo/serp_probe.py для Яндекса. Печатает результат в stdout —
workflow ci-serp-probe публикует его комментарием в issue #22.

Env:
  DATAFORSEO_LOGIN    — логин API (почта аккаунта DataForSEO)
  DATAFORSEO_PASSWORD — пароль API (из кабинета, не пароль от сайта)
  QUERY               — запрос (по умолчанию «купить figma»)
  LOCATION_CODE       — гео Google (2643 = Россия, 1011969 = Москва)
"""
import json
import os
import sys

import requests

API = "https://api.dataforseo.com/v3"
OUR_DOMAIN = "biz-soft.pro"


def main() -> int:
    login = os.environ.get("DATAFORSEO_LOGIN", "").strip()
    password = os.environ.get("DATAFORSEO_PASSWORD", "").strip()
    query = os.environ.get("QUERY", "купить figma").strip()
    location = int(os.environ.get("LOCATION_CODE", "2643") or "2643")

    if not login or not password:
        print("Секреты DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD не заданы — "
              "завести в Settings → Secrets and variables → Actions.")
        return 0

    auth = (login, password)

    # 1. Баланс и статус аккаунта (бесплатный вызов)
    try:
        r = requests.get(f"{API}/appendix/user_data", auth=auth, timeout=30)
        data = r.json()
        task = data["tasks"][0]["result"][0]
        money = task.get("money", {})
        print(f"Аккаунт: ок (HTTP {r.status_code})")
        print(f"Баланс: ${money.get('balance')}  ·  потрачено всего: ${money.get('total')}")
    except Exception as e:  # noqa: BLE001 — диагностика, печатаем всё
        print(f"Ошибка проверки аккаунта: {e}")
        try:
            print(json.dumps(data, ensure_ascii=False)[:800])
        except Exception:  # noqa: BLE001
            pass
        return 0

    # 2. Один платный запрос: Google organic, live/advanced
    body = [{
        "keyword": query,
        "location_code": location,
        "language_code": "ru",
        "device": "desktop",
        "depth": 20,
    }]
    print(f"\nПроба Google SERP: «{query}», location_code={location}, depth=20")
    try:
        r = requests.post(f"{API}/serp/google/organic/live/advanced",
                          auth=auth, json=body, timeout=90)
        data = r.json()
    except Exception as e:  # noqa: BLE001
        print(f"Сетевая ошибка: {e}")
        return 0

    status = data.get("status_code")
    task = (data.get("tasks") or [{}])[0]
    if status != 20000 or task.get("status_code") != 20000:
        print(f"Ошибка API: status={status}, task_status={task.get('status_code')}, "
              f"message={task.get('status_message')}")
        return 0

    cost = task.get("cost")
    result = (task.get("result") or [{}])[0]
    items = [i for i in (result.get("items") or []) if i.get("type") == "organic"]
    print(f"HTTP 200, стоимость запроса: ${cost}. Найдено organic-позиций: {len(items)}. Топ-10:")
    our = None
    for i in items[:10]:
        pos = i.get("rank_group")
        dom = (i.get("domain") or "").removeprefix("www.")
        title = (i.get("title") or "")[:60]
        print(f"  {pos:3d}. {dom:28s} {title}")
        print(f"       {i.get('url')}")
    for i in items:
        dom = (i.get("domain") or "").removeprefix("www.")
        if dom == OUR_DOMAIN and our is None:
            our = i.get("rank_group")
    print(f"\nПозиция {OUR_DOMAIN}: {our if our is not None else 'нет в топ-20'}")
    print("\nВывод: учётные данные РАБОТАЮТ, Google SERP доступен. "
          "Для регулярного сбора будет использоваться дешёвая очередь "
          "task_post/task_get (standard), live — только для проб.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
