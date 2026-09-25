#!/usr/bin/env python3
"""Замер: какие запросы к Метрике проходят, а какие она отклоняет.

Отчёт Директа с 22.09.2026 теряет все разделы Метрики: запросы с фильтром
по кампании возвращают 400 «Query is too complicated». Две правки вслепую —
понижение точности и сокращение окна — отказ не сняли, значит причина не в
объёме периода и не в семплировании, а в чём-то другом.

Скрипт перебирает запросы по одному различию за раз и печатает по каждому
«прошёл» или текст отказа. Ничего не меняет: только чтение.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api-metrika.yandex.net/"
CAMPAIGN_START = "2026-08-28"


def get(path: str, params: dict, token: str) -> dict:
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"OAuth {token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def probe(label: str, token: str, counter: str, **params) -> dict | None:
    """Один запрос: печатает итог и возвращает ответ, если он получен."""
    full = {"ids": counter, "date1": CAMPAIGN_START, "date2": "today"}
    full.update(params)
    try:
        data = get("stat/v1/data", full, token)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"  ОТКАЗ {e.code} — {label}: {body[:400]}")
        return None
    except Exception as e:  # сеть, таймаут
        print(f"  ОТКАЗ — {label}: {e}")
        return None
    totals = data.get("totals") or []
    head = ", ".join(str(x) for x in totals[:4])
    print(f"  прошёл — {label}: итоги [{head}]"
          f" строк {len(data.get('data') or [])}"
          f" семплирование {data.get('sample_share')}"
          f" по выборке {data.get('sampled')}")
    return data


def main() -> None:
    token = os.environ.get("YANDEX_METRIKA_TOKEN", "")
    counter = os.environ.get("YANDEX_METRIKA_COUNTER_ID", "")
    if not token or not counter:
        raise SystemExit("YANDEX_METRIKA_TOKEN/YANDEX_METRIKA_COUNTER_ID не заданы")
    campaign = sys.argv[1] if len(sys.argv) > 1 else "bs-catalog-2026-09"
    week = (dt.date.today() - dt.timedelta(days=6)).isoformat()
    yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()

    print(f"== Счётчик {counter} ==")
    try:
        info = get(f"management/v1/counter/{counter}", {}, token).get("counter", {})
        print(f"  «{info.get('name')}» сайт {info.get('site')} "
              f"статус {info.get('status')} тип {info.get('type')}")
    except Exception as e:
        print(f"  (паспорт счётчика не прочитан: {e})")

    print("\n== Без фильтра ==")
    probe("итоги, весь период, full", token, counter, metrics="ym:s:visits")
    probe("итоги, весь период, low", token, counter,
          metrics="ym:s:visits", accuracy="low")
    probe("итоги, вчера, full", token, counter,
          metrics="ym:s:visits", date1=yesterday, date2=yesterday)
    probe("по дням, весь период, full", token, counter,
          dimensions="ym:s:date", metrics="ym:s:visits", limit=40)

    print("\n== Группировка вместо фильтра ==")
    probe("по метке utm_campaign, весь период", token, counter,
          dimensions="ym:s:UTMCampaign", metrics="ym:s:visits", limit=50)
    probe("по кампании Директа, весь период", token, counter,
          dimensions="ym:s:lastDirectClickOrder", metrics="ym:s:visits", limit=50)
    probe("по кампании Директа, имя, весь период", token, counter,
          dimensions="ym:s:lastDirectClickOrderName",
          metrics="ym:s:visits", limit=50)

    print(f"\n== Фильтр по кампании «{campaign}» ==")
    for label, flt in (
        ("utm_campaign ==", f"ym:s:UTMCampaign=='{campaign}'"),
        ("utm_campaign =@", f"ym:s:UTMCampaign=@'{campaign}'"),
        ("кампания Директа ==", f"ym:s:lastDirectClickOrder=='{campaign}'"),
        ("имя кампании Директа ==", f"ym:s:lastDirectClickOrderName=='{campaign}'"),
        ("источник — реклама", "ym:s:trafficSource=='ad'"),
    ):
        probe(f"{label}, весь период, full", token, counter,
              metrics="ym:s:visits", filters=flt)
        probe(f"{label}, неделя, full", token, counter,
              metrics="ym:s:visits", filters=flt, date1=week)
        probe(f"{label}, вчера, low", token, counter, metrics="ym:s:visits",
              filters=flt, date1=yesterday, date2=yesterday, accuracy="low")

    print("\n== Пустое окно до запуска счётчика ==")
    # Решающее различие. Если запрос за день, в котором данных заведомо нет,
    # отклонён так же, — дело не в объёме данных вообще, и подсказка про
    # интервал и семплирование к причине не относится.
    probe("один день 2020 года", token, counter,
          metrics="ym:s:visits", date1="2020-01-01", date2="2020-01-01")

    print("\n== Точность числом и предел строк ==")
    probe("accuracy=1", token, counter, metrics="ym:s:visits", accuracy="1")
    probe("accuracy=0.01", token, counter, metrics="ym:s:visits", accuracy="0.01")
    probe("limit=1", token, counter, metrics="ym:s:visits", limit=1)

    print("\n== Другая метрика и другая ручка ==")
    probe("метрика ym:s:users", token, counter, metrics="ym:s:users")
    try:
        data = get("stat/v1/data/bytime",
                   {"ids": counter, "metrics": "ym:s:visits",
                    "date1": yesterday, "date2": yesterday}, token)
        print(f"  прошёл — bytime за вчера: итоги {data.get('totals')}")
    except urllib.error.HTTPError as e:
        print(f"  ОТКАЗ {e.code} — bytime за вчера: {e.read().decode('utf-8')[:400]}")
    except Exception as e:
        print(f"  ОТКАЗ — bytime за вчера: {e}")

    print("\n== Что вообще видит токен ==")
    for path in ("management/v1/counters",
                 f"management/v1/counter/{counter}/goals"):
        try:
            data = get(path, {}, token)
        except urllib.error.HTTPError as e:
            print(f"  ОТКАЗ {e.code} — {path}: {e.read().decode('utf-8')[:300]}")
            continue
        except Exception as e:
            print(f"  ОТКАЗ — {path}: {e}")
            continue
        if "counters" in data:
            print(f"  прошёл — {path}: счётчиков {len(data['counters'])}: "
                  + ", ".join(f"{c.get('id')} {c.get('site')} "
                              f"[{c.get('status')}, права {c.get('permission')}]"
                              for c in data["counters"][:10]))
        else:
            print(f"  прошёл — {path}: целей {len(data.get('goals') or [])}")

    print("\n== Тяжёлые разрезы без фильтра ==")
    probe("посадочные, весь период", token, counter,
          dimensions="ym:s:startURL", metrics="ym:s:visits", limit=50)
    probe("устройства, весь период", token, counter,
          dimensions="ym:s:deviceCategory", metrics="ym:s:visits", limit=10)
    probe("поведение, весь период", token, counter,
          metrics="ym:s:visits,ym:s:bounceRate,ym:s:pageDepth,"
                  "ym:s:avgVisitDurationSeconds")


if __name__ == "__main__":
    main()
