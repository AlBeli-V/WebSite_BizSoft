#!/usr/bin/env python3
"""Проба веб-поиска Yandex Search API (SERP) существующим ключом Wordstat.

Wordstat-разведка уже работает через Yandex Cloud Search API
(searchapi.api.cloud.yandex.net, ключ WORDSTAT_API_KEY). Тот же сервис отдаёт
и веб-поиск /v2/web/search — наследник Яндекс.XML, то есть состав выдачи
(SERP) для детекторов вытеснения конкурентами и дрейфа интента.

Проба отвечает на один вопрос: работает ли существующий ключ для веб-поиска.
Делается РОВНО ОДИН запрос (веб-поиск тарифицируется поштучно); ответ — или
топ выдачи, или дословная ошибка прав/тарифа для решения руководителя.

Запуск (из workflow ops-serp-probe): python3 scripts/seo/serp_probe.py "запрос"
Секреты: WORDSTAT_API_KEY; опционально SEARCH_API_FOLDER_ID.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import xml.etree.ElementTree as ET

URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"
TOP_N = 10


def parse_serp(xml_text: str) -> dict:
    """Разбор XML-ответа веб-поиска: найдено, топ документов, ошибки.

    Формат — классический Яндекс.XML: ошибки сервиса приходят кодом 200
    с узлом <error>, поэтому разбор обязан отличать их от результатов.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return {"error": f"ответ не является XML: {e}",
                "raw_head": xml_text[:500]}
    err = root.find(".//error")
    if err is not None:
        return {"error": f"ошибка сервиса (code={err.get('code', '?')}): "
                         f"{(err.text or '').strip()}"}
    found = root.find(".//found")
    docs = []
    for doc in root.findall(".//group/doc")[:TOP_N]:
        docs.append({
            "domain": (doc.findtext("domain") or "").strip(),
            "url": (doc.findtext("url") or "").strip(),
            "title": "".join(doc.find("title").itertext()).strip()
                     if doc.find("title") is not None else "",
        })
    return {"found": int(found.text) if found is not None and found.text
                     and found.text.isdigit() else None,
            "docs": docs}


def main() -> int:
    key = os.environ.get("WORDSTAT_API_KEY", "").strip()
    if not key:
        print("секрет WORDSTAT_API_KEY не задан — пробовать нечем")
        return 1
    import requests

    query = (sys.argv[1] if len(sys.argv) > 1 else "купить figma").strip()
    folder = os.environ.get("SEARCH_API_FOLDER_ID", "").strip()
    body = {"query": {"searchType": "SEARCH_TYPE_RU", "queryText": query}}
    if folder:
        body["folderId"] = folder
    print(f"Проба веб-поиска: «{query}»"
          + (f", folderId={folder}" if folder else ", без folderId"))
    try:
        r = requests.post(URL, json=body, timeout=60,
                          headers={"Authorization": f"Api-Key {key}",
                                   "Content-Type": "application/json"})
    except requests.RequestException as e:
        print(f"сетевая ошибка: {type(e).__name__}: {e}")
        return 1
    print(f"HTTP {r.status_code}")
    if not r.ok:
        # Тело ошибки — главный результат пробы: оно называет недостающую
        # роль сервисного аккаунта или требование folderId.
        print("Ответ сервиса (диагностика прав и тарифа):")
        print(r.text[:2000])
        return 1
    try:
        data = r.json()
    except ValueError:
        print("Ответ 200 не является JSON:")
        print(r.text[:1000])
        return 1
    raw = data.get("rawData")
    if not raw:
        print("Ответ 200 без rawData:")
        print(json.dumps(data, ensure_ascii=False)[:1500])
        return 1
    parsed = parse_serp(base64.b64decode(raw).decode("utf-8", "replace"))
    if parsed.get("error"):
        print(parsed["error"])
        if parsed.get("raw_head"):
            print(parsed["raw_head"])
        return 1
    print(f"Веб-поиск РАБОТАЕТ существующим ключом. "
          f"Найдено документов: {parsed['found'] if parsed['found'] is not None else '?'}. "
          f"Топ-{len(parsed['docs'])}:")
    for i, d in enumerate(parsed["docs"], 1):
        print(f"  {i:>2}. {d['domain']:<28} {d['title'][:70]}")
        print(f"      {d['url'][:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
