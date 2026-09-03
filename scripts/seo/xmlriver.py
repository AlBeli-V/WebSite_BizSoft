#!/usr/bin/env python3
"""Клиент xmlriver.com — российский Google SERP для базового SEO-контура.

Подключён руководителем 03.09.2026: DataForSEO локаций РФ не даёт (Google
удалил геотаргетинг России, см. docs/competitive/decisions-2026-08-31.md,
раздел 4), а xmlriver отдаёт выдачу Google по справочнику местоположений,
где Россия и её города есть. Тариф кабинета — 25 ₽ за 1000 запросов.

Ответ xmlriver — в формате Яндекс.XML (`<yandexsearch>`): ошибки сервиса
приходят кодом 200 с узлом `<error code="…">`, поэтому разбор обязан
отличать их от результатов; код 15 — «ничего не найдено», это пустая
выдача, а не сбой.

Учётные данные — только из окружения: XMLRIVER_USER (user_id) и
XMLRIVER_KEY. Все параметры запроса (местоположение, страна, язык,
устройство) передаются в URL явно из data/seo/xmlriver.json, чтобы сбор не
зависел от «настроек по умолчанию» в кабинете.

Страница выдачи Google у xmlriver — только 10 позиций («ТОП» в кабинете
даёт выбрать одно значение, 10; проверено 03.09.2026). Топ-20 — это две
страницы, параметр page (0 — первая, 1 — вторая), как в Yandex Search API,
на котором основано API сервиса. Платная галка «Кол-во результатов» число
позиций не меняет — она покупает точное «найдено N».

Проба: python3 scripts/seo/xmlriver.py probe "купить figma" [page]
       (баланс + РОВНО ОДИН платный запрос; вывод — в issue #22 через
       workflow ops-xmlriver-probe).
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

SEARCH_URL = "https://xmlriver.com/search/xml"
BALANCE_URL = "https://xmlriver.com/api/get_balance/"
CONFIG_PATH = pathlib.Path("data/seo/xmlriver.json")

# Код Яндекс.XML «искомая комбинация слов нигде не встречается»; xmlriver
# повторяет его для пустой выдачи Google.
NO_RESULTS_CODE = "15"
# Коды ошибок сервиса кодом 200, на которые он сам просит перезапрос:
# 500 — «Выполните перезапрос. Ответ от поисковой системы не получен»
# (проба 03.09.2026). Это помеха, а не вердикт, — повторяем как 5xx.
RETRY_SERVICE_CODES = {"500"}
# Типы блоков, которые считаем органикой. xmlriver помечает блоки узлом
# contentType (organic, ads, video, …); документ без пометки — органика.
ORGANIC_TYPES = {"", "organic"}
# Позиций на одной странице выдачи Google у xmlriver.
PAGE_SIZE = 10
RETRIES = 3
RETRY_PAUSE_S = 3.0
TIMEOUT_S = 60


def load_config(path: pathlib.Path = CONFIG_PATH) -> dict:
    """Настройки сбора; отсутствие файла — не сбой, действуют значения по
    умолчанию (Россия, десктоп, топ-20)."""
    defaults = {"enabled": True, "price_rub_per_1000": 25.0,
                "cadence": "weekly", "weekday": 1,
                "daily_cap": 1100, "monthly_cap": 15000,
                "core_cap": 500, "top_n": 20, "pages": 2,
                "query": {"loc": 2643, "country": 2643, "lr": "RU",
                          "device": "desktop"},
                "balance_warn_days": 14}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaults
    merged = {**defaults, **{k: v for k, v in data.items()
                             if not k.startswith("_")}}
    merged["query"] = {k: v for k, v in (merged.get("query") or {}).items()
                       if not k.startswith("_") and v not in (None, "")}
    return merged


def credentials() -> tuple[str, str]:
    return (os.environ.get("XMLRIVER_USER", "").strip(),
            os.environ.get("XMLRIVER_KEY", "").strip())


def build_params(user: str, key: str, query: str,
                 query_cfg: dict | None = None, page: int = 0) -> dict:
    """Параметры запроса Google: учётные данные + настройки из конфига.

    Передаются только заданные настройки: `null` в конфиге означает
    «действует настройка кабинета» (домен Google). Первая страница идёт
    без page — ровно тот запрос, что проверен пробой.
    """
    params = {"user": user, "key": key, "query": query}
    for k, v in (query_cfg or {}).items():
        if v in (None, ""):
            continue
        params[k] = v
    if page:
        params["page"] = page
    return params


def _domain_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host.removeprefix("www.")


def parse_google_xml(xml_text: str, top_n: int = 20) -> dict:
    """Разбор ответа xmlriver: органика топ-N, число найденного, ошибки.

    Возвращает {"found", "top", "blocks"} либо {"error"}. Домен берётся из
    узла <domain>, а при его отсутствии — из URL (xmlriver отдаёт не всегда).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return {"error": f"ответ не является XML: {e}",
                "raw_head": xml_text[:500]}
    err = root.find(".//error")
    if err is not None:
        code = (err.get("code") or "").strip()
        text = (err.text or "").strip()
        if code == NO_RESULTS_CODE:
            return {"found": 0, "top": [], "blocks": {}}
        return {"error": f"ошибка сервиса (code={code or '?'}): {text}",
                "code": code}
    found_node = root.find(".//found")
    found = None
    if found_node is not None and (found_node.text or "").strip().isdigit():
        found = int(found_node.text.strip())
    top: list[dict] = []
    blocks: dict[str, int] = {}
    for doc in root.findall(".//group/doc"):
        ctype = (doc.findtext("contentType") or "").strip().lower()
        blocks[ctype or "organic"] = blocks.get(ctype or "organic", 0) + 1
        if ctype not in ORGANIC_TYPES:
            continue
        if len(top) >= top_n:
            continue
        url = (doc.findtext("url") or "").strip()
        title_node = doc.find("title")
        title = ("".join(title_node.itertext()).strip()
                 if title_node is not None else "")
        domain = (doc.findtext("domain") or "").strip().lower() \
            .removeprefix("www.") or _domain_of(url)
        top.append({"domain": domain, "url": url, "title": title})
    return {"found": found, "top": top, "blocks": blocks}


def search_google(session, user: str, key: str, query: str,
                  query_cfg: dict | None = None, top_n: int = 20,
                  page: int = 0) -> dict:
    """Один запрос Google через xmlriver с повторами на сетевые сбои и 5xx.

    Ошибки сервиса кодом 200 (<error>) не повторяются: это вердикт по
    учётным данным, балансу или запросу, а не помеха. Исключение —
    RETRY_SERVICE_CODES, где сервис сам просит перезапрос.
    """
    params = build_params(user, key, query, query_cfg, page)
    last = ""
    for attempt in range(1, RETRIES + 1):
        try:
            r = session.get(SEARCH_URL, params=params, timeout=TIMEOUT_S)
        except Exception as e:  # noqa: BLE001 — сеть: повторяем
            last = f"{type(e).__name__}: {e}"
        else:
            if r.status_code >= 500:
                last = f"HTTP {r.status_code}: {r.text[:200]}"
            elif not r.ok:
                return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}
            else:
                parsed = parse_google_xml(r.text, top_n)
                if parsed.get("code") not in RETRY_SERVICE_CODES:
                    return parsed
                last = parsed["error"]
        if attempt < RETRIES:
            time.sleep(RETRY_PAUSE_S)
    return {"error": f"сбой после {RETRIES} попыток: {last}"}


def get_balance(session, user: str, key: str) -> dict:
    """Остаток на балансе кабинета, ₽. Ответ — число текстом; всё иное
    возвращается дословно как ошибка."""
    try:
        r = session.get(BALANCE_URL, params={"user": user, "key": key},
                        timeout=TIMEOUT_S)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}
    text = (r.text or "").strip()
    if not r.ok:
        return {"error": f"HTTP {r.status_code}: {text[:300]}"}
    try:
        return {"balance_rub": float(text.replace(",", "."))}
    except ValueError:
        return {"error": f"баланс не является числом: {text[:300]}"}


def probe(query: str, page: int = 0) -> int:
    """Проба: баланс + ровно один платный запрос, вывод для issue #22."""
    user, key = credentials()
    if not user or not key:
        print("секреты XMLRIVER_USER / XMLRIVER_KEY не заданы — пробовать нечем")
        return 1
    import requests
    cfg = load_config()
    session = requests.Session()
    bal = get_balance(session, user, key)
    if "error" in bal:
        print(f"Баланс: ошибка — {bal['error']}")
    else:
        print(f"Баланс xmlriver: {bal['balance_rub']:.2f} ₽ "
              f"(≈{bal['balance_rub'] / cfg['price_rub_per_1000'] * 1000:.0f} "
              f"запросов по {cfg['price_rub_per_1000']} ₽/1000)")
    shown = {k: v for k, v in build_params("…", "…", query,
                                            cfg["query"], page).items()
             if k not in ("user", "key")}
    print(f"Проба Google SERP: {json.dumps(shown, ensure_ascii=False)}")
    res = search_google(session, user, key, query, cfg["query"],
                        cfg["top_n"], page)
    if "error" in res:
        print(f"Ошибка: {res['error']}")
        if res.get("raw_head"):
            print(res["raw_head"])
        return 1
    print(f"Google SERP РАБОТАЕТ. Найдено: "
          f"{res['found'] if res['found'] is not None else '?'}. "
          f"Блоки: {json.dumps(res['blocks'], ensure_ascii=False)}. "
          f"Органика топ-{len(res['top'])}:")
    ours = None
    offset = page * PAGE_SIZE
    for i, d in enumerate(res["top"], 1 + offset):
        if d["domain"] == "biz-soft.pro" and ours is None:
            ours = i
        print(f"  {i:>2}. {d['domain']:<28} {d['title'][:70]}")
        print(f"      {d['url'][:100]}")
    print(f"Позиция biz-soft.pro: {ours if ours else 'нет в топе'}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 1 and argv[0] == "probe":
        rest = argv[1:]
        page = 0
        if rest and rest[-1].isdigit():
            page = int(rest[-1])
            rest = rest[:-1]
        return probe(" ".join(rest).strip() or "купить figma", page)
    print("использование: xmlriver.py probe \"запрос\" [page]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
