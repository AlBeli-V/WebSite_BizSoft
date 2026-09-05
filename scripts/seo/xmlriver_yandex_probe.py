#!/usr/bin/env python3
"""Проба выдачи Яндекса через xmlriver — ровно один платный запрос.

Зачем (решение руководителя 04.09.2026). Эталонный замер живой выдачи через
Chromium из GitHub Actions провалился: капча на 24 запросах из 26. Два
уцелевших замера дали важное — расхождение с ежедневным срезом есть при
НУЛЕВОЙ рекламе на странице:

    «оплата depositphotos в рублях»   срез 7  → живая выдача 6,  рекламы 0
    «оплата depositphotos из россии»  срез 9  → живая выдача 12, рекламы 0

Значит вопрос сместился: дело не только в рекламе, а в самом ранжировании
Search API. На такой вопрос может ответить второй независимый источник
выдачи, и xmlriver для Google в проекте уже работает с 03.09.

Что проба обязана выяснить, прежде чем строить на xmlriver контур:

  1. отвечает ли Яндекс-эндпоинт сервиса на наши учётные данные;
  2. приходит ли в ответе разметка типов блоков (`contentType`), и есть ли
     среди них рекламные — от этого зависит, можно ли вообще получить
     absolute_position и ads_before, ради которых всё затевалось;
  3. насколько выдача xmlriver совпадает с нашим ежедневным срезом по тому
     же запросу — если совпадает почти полностью, второй источник ничего
     нового не измеряет и платить за него незачем.

Эндпоинт Яндекса задаётся входом: точного адреса в проекте пока нет, и
угадывать молча нельзя. Неверный адрес проба покажет ошибкой с телом
ответа, а не пустым результатом.

Запуск: python3 scripts/seo/xmlriver_yandex_probe.py "запрос" [endpoint]
Тратит ОДИН платный запрос. Вывод — в журнал issue #22 через workflow
ops-xmlriver-yandex-probe.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import xmlriver  # noqa: E402

# Адреса, по которым сервис отдаёт выдачу Яндекса. Первый — основной по
# документации xmlriver, второй пробуется, если первый ответил не XML.
DEFAULT_ENDPOINTS = (
    "https://xmlriver.com/search_yandex/xml",
    "https://xmlriver.com/api/search_yandex/xml",
)
SEO_BRANCH = "seo-data"
REGION = "213"
OURS = "biz-soft.pro"


def daily_snapshot_top(query: str) -> list[str]:
    """Топ доменов по этому запросу из последнего ежедневного среза.

    Читается тем же способом, что и везде в проекте, — `git show` по ветке
    базового контура, только на чтение.
    """
    try:
        listing = subprocess.run(
            ["git", "ls-tree", "--full-tree", "--name-only",
             f"origin/{SEO_BRANCH}", "reports/seo/serp/"],
            capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return []
    files = sorted(p for p in listing.splitlines() if p.endswith("-serp.jsonl"))
    if not files:
        return []
    try:
        blob = subprocess.run(["git", "show", f"origin/{SEO_BRANCH}:{files[-1]}"],
                              capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return []
    needle = " ".join(query.lower().split())
    for line in blob.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("region") != REGION:
            continue
        if " ".join((row.get("query") or "").lower().split()) != needle:
            continue
        return [(d.get("domain") or "").lower().removeprefix("www.")
                for d in (row.get("top") or [])]
    return []


def parse_with_types(xml_text: str) -> dict:
    """Разбор ответа с сохранением ПОРЯДКА документов и типов блоков.

    Штатный разбор клиента выбрасывает неорганические документы — для сбора
    выдачи это правильно, но здесь выбрасывать нельзя: вопрос пробы ровно в
    том, приходят ли рекламные блоки и на каких местах они стоят.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return {"error": f"ответ не является XML: {e}", "raw_head": xml_text[:400]}
    err = root.find(".//error")
    if err is not None:
        return {"error": f"ошибка сервиса (code={err.get('code', '?')}): "
                         f"{(err.text or '').strip()}"}
    items = []
    for doc in root.findall(".//group/doc"):
        url = (doc.findtext("url") or "").strip()
        domain = ((doc.findtext("domain") or "").strip().lower().removeprefix("www.")
                  or xmlriver._domain_of(url))
        items.append({"domain": domain,
                      "type": (doc.findtext("contentType") or "").strip().lower()
                              or "organic"})
    return {"items": items}


def main(argv: list[str]) -> int:
    user, key = xmlriver.credentials()
    if not user or not key:
        print("секреты XMLRIVER_USER / XMLRIVER_KEY не заданы — пробовать нечем")
        return 1
    import requests

    query = (argv[1] if len(argv) > 1 else "оплата depositphotos из россии").strip()
    endpoints = [argv[2]] if len(argv) > 2 else list(DEFAULT_ENDPOINTS)
    config = json.loads(pathlib.Path("data/seo/xmlriver.json").read_text("utf-8"))

    # Регион задаётся так же, как в ежедневном срезе: Москва. Прочие
    # параметры — из конфига Google-сбора, кроме тех, что относятся только
    # к Google (домен выдачи).
    params = {"user": user, "key": key, "query": query, "loc": REGION}
    for name in ("lr", "device"):
        value = (config.get("query") or {}).get(name)
        if value:
            params[name] = value

    print(f"Проба выдачи Яндекса через xmlriver: «{query}», регион {REGION}")
    print(f"Параметры (без ключа): "
          f"{ {k: v for k, v in params.items() if k != 'key'} }\n")

    parsed = None
    used = None
    for endpoint in endpoints:
        print(f"Эндпоинт {endpoint}")
        try:
            r = requests.get(endpoint, params=params, timeout=60)
        except requests.RequestException as e:
            print(f"  сетевая ошибка: {type(e).__name__}: {e}")
            continue
        print(f"  HTTP {r.status_code}, тело {len(r.text)} символов")
        if not r.ok:
            print(f"  ответ сервиса: {r.text[:400]}")
            continue
        result = parse_with_types(r.text)
        if result.get("error"):
            print(f"  {result['error']}")
            if result.get("raw_head"):
                print(f"  начало ответа: {result['raw_head']}")
            continue
        parsed, used = result, endpoint
        break

    if parsed is None:
        print("\nВЫВОД: выдачу Яндекса через xmlriver получить не удалось. "
              "Ни один известный адрес не ответил разбираемым XML — адрес "
              "эндпоинта нужно уточнить в поддержке сервиса. Строить контур "
              "на догадке нельзя.")
        return 1

    items = parsed["items"]
    types: dict[str, int] = {}
    for item in items:
        types[item["type"]] = types.get(item["type"], 0) + 1
    ads = [i for i, item in enumerate(items, start=1) if item["type"] != "organic"]

    print(f"\nПолучено {len(items)} документов, адрес {used}")
    print(f"Типы блоков: {types}")
    print("Первые 10 позиций (позиция · тип · домен):")
    for index, item in enumerate(items[:10], start=1):
        mark = "органика" if item["type"] == "organic" else item["type"].upper()
        star = " ←── мы" if item["domain"] == OURS else ""
        print(f"  {index:2}. {mark:10} {item['domain']}{star}")

    daily = daily_snapshot_top(query)
    if daily:
        organic = [i["domain"] for i in items if i["type"] == "organic"]
        common = len(set(organic[:10]) & set(daily[:10]))
        our_x = next((i + 1 for i, d in enumerate(organic) if d == OURS), None)
        our_d = next((i + 1 for i, d in enumerate(daily) if d == OURS), None)
        print(f"\nСверка с ежедневным срезом Search API:")
        print(f"  общих доменов в топ-10: {common} из 10")
        print(f"  наша органическая позиция: xmlriver {our_x or '—'}, "
              f"срез {our_d or '—'}")
    else:
        print("\nСверка с ежедневным срезом невозможна: запроса нет в "
              "последнем срезе.")

    print("\nВЫВОД ПО ГЛАВНОМУ ВОПРОСУ")
    if ads:
        print(f"  Рекламные блоки в ответе ЕСТЬ (позиции {ads}). Значит через "
              f"xmlriver можно получить absolute_position и ads_before — то, "
              f"чего Search API не отдаёт вовсе.")
    else:
        print("  Рекламных блоков в ответе НЕТ. Либо их не было в этой выдаче, "
              "либо сервис их не отдаёт — по одному запросу не различить. "
              "Повторить пробу на запросе, где реклама заведомо есть; если и "
              "там пусто, absolute_position через xmlriver недостижим, и "
              "остаётся сравнивать только ранжирование.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
