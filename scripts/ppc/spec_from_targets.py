#!/usr/bin/env python3
"""Спецификация расширения кампании из отобранных фраз.

Отбор (`scripts/seo/wordstat/ad_targets.py --intent commercial`) отдаёт
фразы, которые прошли все условия: покупательский интент, спрос выше
порога, привязка к карточке каталога, замеренная позиция и мы не в первой
тройке. Собрать из сотни таких фраз спецификацию руками — работа, в
которой ошибка тихая: лимит заголовка Директа превышается на один символ,
и прогон падает на середине.

Группа — одна посадочная. Карточка товара даёт группу под карточку, бренд
с линейкой — группу под вендора; так объявление обещает ровно то, что
человек увидит на странице.

Тексты собираются по образцу раунда 5 (он прошёл модерацию) с подстановкой
имени и проверкой лимитов Директа: Title ≤ 56, Title2 ≤ 30, их сумма ≤ 52,
Text ≤ 81. Имя, которое в лимит не влезает, заменяется именем вендора —
молча обрезать название продукта в объявлении нельзя.

Запуск: python3 scripts/ppc/spec_from_targets.py > round6-spec.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "seo" / "wordstat"))

TARGETS = pathlib.Path("reports/seo/wordstat/ad-targets.json")
SITE = "https://biz-soft.pro"
LIMITS = {"Title": 56, "Title2": 30, "Text": 81, "TitleSum": 52}
MAX_KEYWORDS_PER_GROUP = 50


def fits(title1: str, title2: str, text: str) -> bool:
    return (len(title1) <= LIMITS["Title"] and len(title2) <= LIMITS["Title2"]
            and len(title1) + len(title2) <= LIMITS["TitleSum"]
            and len(text) <= LIMITS["Text"])


def ads_for(name: str, fallback: str) -> list[dict]:
    """Два объявления по образцу раунда 5.

    Имя продукта — то, что человек ищет, и укорачивать его нельзя. Поэтому
    при нехватке места первым уступает текст, а не название: у «DaVinci
    Resolve Studio» полная формулировка выходила за 81 символ, и объявление
    молча откатывалось на слаг «bmd».
    """
    # Лимит Директа на сумму заголовков — 52 символа, и длинное имя съедает
    # его целиком. Поэтому вариантов несколько, от развёрнутого к сжатому:
    # уступают текст и подзаголовок, имя продукта остаётся как есть.
    first_titles = [("{n} для юрлиц", "Договор и счёт"), ("{n} для юрлиц", "Счёт и НДС"),
                    ("{n}", "Счёт юрлицу")]
    second_titles = [("Купить {n} в России", "Оплата от юрлица"),
                     ("{n} купить", "Оплата от юрлица"), ("{n} купить", "Счёт юрлицу")]
    texts = [
        ("{n} на организацию: лицензия, счёт, акты, НДС. Подберём тариф.",
         "Оплачиваем {n} из России на ваше юрлицо. Закрывающие документы."),
        ("{n} на организацию: счёт, акты, НДС. Подберём тариф.",
         "Оплачиваем {n} на ваше юрлицо. Закрывающие документы."),
        ("{n} на юрлицо: счёт, акты, НДС.", "Оплачиваем {n} на юрлицо."),
    ]
    for candidate in (name, fallback):
        for (t1, s1), (t2, s2), (x1, x2) in zip(first_titles, second_titles, texts):
            first = {"title1": t1.format(n=candidate), "title2": s1,
                     "text": x1.format(n=candidate)}
            second = {"title1": t2.format(n=candidate), "title2": s2,
                      "text": x2.format(n=candidate)}
            if all(fits(a["title1"], a["title2"], a["text"]) for a in (first, second)):
                return [first, second]
    raise SystemExit(f"ни «{name}», ни «{fallback}» не укладываются в лимиты Директа")


def slug_of(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def pretty_name(url: str, vendor: str, titles: dict[str, str],
                vendors: dict[str, str] | None = None) -> str:
    """Имя для объявления — как его пишет человек, а не как в слаге.

    Вендор приходит слагом (`clip-studio-paint`), а название карточки бывает
    предложением («Корпоративный Google Workspace с Gemini: ...»). В заголовок
    объявления идёт имя из реестра вендоров, а для карточки — продуктовая
    часть названия, начиная с имени вендора и до первого двоеточия или
    предлога.
    """
    # Имя в реестре бывает составным — «Magnific (Freepik)». В заголовок
    # объявления идёт первая часть: скобки в рекламе читаются как опечатка.
    human = (vendors or {}).get(vendor, vendor).split("(")[0].strip()
    if url.startswith("/product/"):
        title = (titles.get(slug_of(url)) or "").strip()
        if title:
            low, needle = title.lower(), human.lower()
            if needle and needle in low:
                title = title[low.index(needle):]
            head = re.split(r"\s*[:(]|\s+(?:для|с|на|по|от)\s+", title)[0].strip()
            if head and len(head) <= 40:
                return head
    return human


def live_paths(sitemap: pathlib.Path | None = None) -> set[str]:
    """Пути, которые сайт действительно отдаёт, — по карте сайта."""
    if sitemap is None:
        files = sorted(pathlib.Path("reports/seo/data").glob("sitemap-*.json"))
        if not files:
            return set()
        sitemap = files[-1]
    data = json.loads(sitemap.read_text(encoding="utf-8"))
    return {u["path"] for u in data.get("urls", []) if u.get("path")}


def build(targets: dict, campaign: str, titles: dict[str, str],
          exclude: set[str], max_groups: int | None = None,
          vendors: dict[str, str] | None = None,
          paths: set[str] | None = None) -> dict:
    # Посадочная, которой нет в карте сайта, — это оплаченный клик в 404.
    # Так вышло с ManageEngine: привязка собрала карточки под слаг «me»,
    # а страницы /vendors/me не существует.
    live = paths if paths is not None else live_paths()
    dropped: list[dict] = []
    groups: dict[str, dict] = {}
    for row in targets.get("ready") or []:
        phrase = row["phrase"].strip().lower()
        if phrase in exclude:
            continue
        url = row.get("url")
        if not url:
            continue
        if live and url not in live:
            dropped.append({"phrase": row["phrase"], "url": url,
                            "why": "страницы нет в карте сайта"})
            continue
        vendor = (row.get("vendor") or "").strip() or slug_of(url)
        key = url
        g = groups.setdefault(key, {
            "id": f"r6-{slug_of(url)}"[:40],
            "title": f"{pretty_name(url, vendor, titles, vendors)} — покупка на юрлицо",
            "landing": SITE + url,
            "vendor": vendor,
            "why": "",
            "keywords": [],
        })
        if len(g["keywords"]) < MAX_KEYWORDS_PER_GROUP:
            g["keywords"].append({
                "keyword": f'"{phrase}"',
                "wordstat_frequency": row.get("frequency") or 0,
                "our_position": row.get("position"),
            })
    out = []
    for g in sorted(groups.values(), key=lambda g: -sum(k["wordstat_frequency"] for k in g["keywords"])):
        demand = sum(k["wordstat_frequency"] for k in g["keywords"])
        measured = [k for k in g["keywords"] if k["our_position"] is not None]
        g["why"] = (f"{len(g['keywords'])} фраз, {demand} запросов в месяц; "
                    + ("нас нет в выдаче ни по одной"
                       if not measured else
                       f"лучшая наша позиция — {min(k['our_position'] for k in measured):.0f}"))
        name = pretty_name(g["landing"].replace(SITE, ""), g["vendor"], titles, vendors)
        g["ads"] = ads_for(name, (vendors or {}).get(g["vendor"], g["vendor"]))
        g.pop("vendor")
        out.append(g)
    if max_groups:
        out = out[:max_groups]
    return {
        "schema_version": 1,
        "spec_version": f"round6-{dt.date.today().isoformat()}",
        "date": dt.date.today().isoformat(),
        "plan_kind": "extend_campaign",
        "status": "ready",
        "provenance": {
            "targets": str(TARGETS),
            "intent": targets.get("intent"),
            "min_frequency": targets.get("min_frequency"),
            "serp_source": targets.get("serp_source"),
            "webmaster_source": targets.get("webmaster_source"),
        },
        "rationale": (
            "Расширение кампании на коммерческий спрос, привязанный к карточкам "
            "каталога. Каждая фраза прошла четыре условия: покупательский интент, "
            "спрос от порога, есть что продать и позиция замерена, а мы не в "
            "первой тройке. Бюджет не меняется — «максимум кликов» распределит "
            "показы сам."),
        "campaign": {
            "name": campaign,
            "action": "существующая кампания; раунд 6 добавляет группы",
            "autotargeting": "off",
        },
        "pause": [],
        "keep": [],
        "dropped": dropped,
        "groups": out,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", default="bs-catalog-2026-09")
    ap.add_argument("--targets", default=str(TARGETS))
    ap.add_argument("--exclude-spec", default=None,
                    help="спецификация, чьи фразы уже в кампании")
    ap.add_argument("--max-groups", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    import catalog_match
    titles = catalog_match.load_titles()
    vendors = catalog_match.load_vendors()
    targets = json.loads(pathlib.Path(args.targets).read_text(encoding="utf-8"))
    exclude: set[str] = set()
    if args.exclude_spec:
        prev = json.loads(pathlib.Path(args.exclude_spec).read_text(encoding="utf-8"))
        for g in prev.get("groups") or []:
            for k in g.get("keywords") or []:
                exclude.add(k["keyword"].strip('"').lower())
    spec = build(targets, args.campaign, titles, exclude, args.max_groups, vendors)
    if spec["dropped"]:
        print(f"отброшено фраз без живой посадочной: {len(spec['dropped'])}", file=sys.stderr)
        for d in spec["dropped"][:5]:
            print(f"  {d['phrase']} → {d['url']}", file=sys.stderr)
    text = json.dumps(spec, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        pathlib.Path(args.out).write_text(text, encoding="utf-8")
        total = sum(len(g["keywords"]) for g in spec["groups"])
        print(f"групп: {len(spec['groups'])}, фраз: {total}; исключено из раунда 5: {len(exclude)}")
    else:
        print(text)


if __name__ == "__main__":
    main()
