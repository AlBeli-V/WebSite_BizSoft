#!/usr/bin/env python3
"""Проба DataForSEO SERP API: диагностика локаций + один платный запрос Google.

Первая проба (31.08) показала: учётные данные работают, но location_code 2643
(Россия) отклонён — Google Ads удалил гео-таргетинг России, у DataForSEO её
может не быть в списке локаций. Эта версия:
  1) бесплатно проверяет баланс;
  2) бесплатно запрашивает список локаций России (/serp/google/locations/RU);
  3) если локации есть — платный запрос с первой из них (или LOCATION_CODE);
     если нет — платный запрос с русскоязычной выдачей google.ru:
     language_code=ru + se_domain=google.ru + нейтральная локация (Беларусь,
     2112) с пометкой, что региональная точность по РФ недоступна.

Печатает результат в stdout — workflow ci-serp-probe публикует его в issue #22.

Env:
  DATAFORSEO_LOGIN    — логин API (почта аккаунта DataForSEO)
  DATAFORSEO_PASSWORD — пароль API (из кабинета, не пароль от сайта)
  QUERY               — запрос (по умолчанию «купить figma»)
  LOCATION_CODE       — принудительный location_code (пусто = автоопределение)
"""
import json
import os
import sys

import requests

API = "https://api.dataforseo.com/v3"
OUR_DOMAIN = "biz-soft.pro"
NEUTRAL_LOCATION = 2112  # Belarus — нейтральное гео для выдачи google.ru на русском


def api_get(auth, path):
    r = requests.get(f"{API}{path}", auth=auth, timeout=30)
    return r.json()


def print_serp(task):
    cost = task.get("cost")
    result = (task.get("result") or [{}])[0]
    items = [i for i in (result.get("items") or []) if i.get("type") == "organic"]
    print(f"Стоимость запроса: ${cost}. Organic-позиций: {len(items)}. Топ-10:")
    our = None
    for i in items:
        dom = (i.get("domain") or "").removeprefix("www.")
        if dom == OUR_DOMAIN and our is None:
            our = i.get("rank_group")
    for i in items[:10]:
        pos = i.get("rank_group")
        dom = (i.get("domain") or "").removeprefix("www.")
        title = (i.get("title") or "")[:60]
        print(f"  {pos:3d}. {dom:28s} {title}")
        print(f"       {i.get('url')}")
    print(f"\nПозиция {OUR_DOMAIN}: {our if our is not None else 'нет в топ-20'}")


def main() -> int:
    login = os.environ.get("DATAFORSEO_LOGIN", "").strip()
    password = os.environ.get("DATAFORSEO_PASSWORD", "").strip()
    query = os.environ.get("QUERY", "купить figma").strip()
    forced_loc = os.environ.get("LOCATION_CODE", "").strip()

    if not login or not password:
        print("Секреты DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD не заданы — "
              "завести в Settings → Secrets and variables → Actions.")
        return 0
    auth = (login, password)

    # 1. Баланс (бесплатно)
    try:
        data = api_get(auth, "/appendix/user_data")
        money = data["tasks"][0]["result"][0].get("money", {})
        print(f"Аккаунт: ок. Баланс: ${money.get('balance')}")
    except Exception as e:  # noqa: BLE001 — диагностика
        print(f"Ошибка проверки аккаунта: {e}")
        return 0

    # 2. Локации России (бесплатно)
    ru_locations = []
    try:
        data = api_get(auth, "/serp/google/locations/RU")
        ru_locations = (data["tasks"][0].get("result") or [])
    except Exception as e:  # noqa: BLE001
        print(f"Ошибка запроса локаций RU: {e}")
    print(f"\nЛокаций России в справочнике Google у DataForSEO: {len(ru_locations)}")
    for loc in ru_locations[:8]:
        print(f"  {loc.get('location_code')}  {loc.get('location_name')}  ({loc.get('location_type')})")

    # 3. Платный запрос
    body_item = {"keyword": query, "language_code": "ru", "device": "desktop", "depth": 20}
    if forced_loc:
        body_item["location_code"] = int(forced_loc)
        mode = f"принудительный location_code={forced_loc}"
    elif ru_locations:
        code = ru_locations[0]["location_code"]
        body_item["location_code"] = code
        mode = f"location_code={code} ({ru_locations[0].get('location_name')})"
    else:
        body_item["location_code"] = NEUTRAL_LOCATION
        body_item["se_domain"] = "google.ru"
        mode = ("гео России у Google недоступно (geotarget удалён) → "
                f"google.ru, language=ru, нейтральная локация {NEUTRAL_LOCATION}; "
                "региональная точность по РФ в этом режиме отсутствует")
    print(f"\nПроба Google SERP: «{query}» · {mode}")
    try:
        r = requests.post(f"{API}/serp/google/organic/live/advanced",
                          auth=auth, json=[body_item], timeout=90)
        data = r.json()
    except Exception as e:  # noqa: BLE001
        print(f"Сетевая ошибка: {e}")
        return 0

    task = (data.get("tasks") or [{}])[0]
    if data.get("status_code") != 20000 or task.get("status_code") != 20000:
        print(f"Ошибка API: status={data.get('status_code')}, "
              f"task_status={task.get('status_code')}, message={task.get('status_message')}")
        print("Тело задачи для разбора:")
        print(json.dumps(body_item, ensure_ascii=False))
        return 0

    print_serp(task)
    print("\nВывод: доступ РАБОТАЕТ. Для регулярного сбора — дешёвая очередь "
          "task_post/task_get (standard), live — только для проб.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
