#!/usr/bin/env python3
"""Прогон discovery: построить реестр конкурентов за дату и сохранить снимок.

Читает срез выдачи Яндекса из хранилища базового контура (read-only, повторно
не покупается), строит карточки доменов и пишет два артефакта:

  * append-only запись в data/competitive/competitors/registry.jsonl;
  * снимок дня data/competitive/snapshots/<дата>-discovery.json — он станет
    единственным источником цифр для письма и отчёта.

Запуск: python3 competitive-intelligence/discovery/run_discovery.py [дата]
Без аргумента берётся последняя доступная дата среза.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402
from discovery import demand_source, query_set, registry, serp_source  # noqa: E402
from scoring import visibility  # noqa: E402

MSK = timezone(timedelta(hours=3))
OURS = "biz-soft.pro"
REGION = "213"  # тот же регион, по которому строятся карточки доменов


def config_hash(config: dict) -> str:
    """Отпечаток конфигурации скоринга.

    Любая правка весов, кривой CTR или точек насыщения меняет отпечаток, и по
    нему видно, что вчерашние и сегодняшние оценки считались разными
    моделями. Без этого «изменение оценки» и «изменение модели» неотличимы.
    """
    canonical = json.dumps(config, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def per_query_visibility(rows, config: dict, region: str = REGION) -> dict:
    """Взвешенная видимость по каждому запросу: наша и всего поля.

    Хранится в снимке, чтобы долю можно было пересчитать по любому
    подмножеству запросов — прежде всего по пересечению ядер разных дней.
    Без этих чисел «сравнимая доля» была бы невычислима задним числом, и
    единственным способом сравнения оставалось бы полное совпадение состава
    ядра.
    """
    result: dict[str, dict] = {}
    for row in rows:
        if not row.has_data or row.region != region:
            continue
        key = query_set.normalize(row.query)
        if not key:
            continue
        bucket = result.setdefault(key, {"наша": 0.0, "поле": 0.0,
                                          "позиция": None, "наш_url": None})
        for index, item in enumerate(row.top, start=1):
            domain = serp_source.normalize_domain(item.get("domain", ""))
            if not domain:
                continue
            value = visibility.query_visibility(index, config)
            bucket["поле"] += value
            if domain == OURS:
                bucket["наша"] += value
                # Позиция нужна для оценки экспериментов «было → стало»:
                # видимость отвечает на вопрос «сколько весим», позиция — на
                # вопрос «сдвинулись ли», и подменять одно другим нельзя.
                if bucket["позиция"] is None or index < bucket["позиция"]:
                    bucket["позиция"] = index
                    # Адрес нашей страницы нужен, чтобы строить контрольную
                    # группу экспериментов: правка шаблона задевает все
                    # страницы своего типа, и такие запросы контролем быть
                    # не могут.
                    bucket["наш_url"] = item.get("url")
    return {q: {"наша": round(v["наша"], 6), "поле": round(v["поле"], 6),
                "позиция": v["позиция"], "наш_url": v["наш_url"]}
            for q, v in result.items()}


def demand_coverage(rows, region: str = REGION) -> tuple[dict, dict]:
    """Взвешенное покрытие ядра и состав источников спроса.

    Покрытие по числу запросов и покрытие по спросу — разные величины: можно
    собрать 90% запросов и потерять при этом самый частотный. Второй гейт
    считается отдельно по каждому источнику спроса: складывать частотность
    Wordstat с показами Вебмастера нельзя даже в знаменателе покрытия.
    """
    total: dict[str, int] = {}
    collected: dict[str, int] = {}
    mix: dict[str, int] = {}
    for row in rows:
        if row.region != region:
            continue
        value, source = demand_source.demand(row.query)
        mix[source] = mix.get(source, 0) + 1
        if source == "none" or not value:
            continue
        total[source] = total.get(source, 0) + value
        if row.has_data:
            collected[source] = collected.get(source, 0) + value
    weighted = {source: round(collected.get(source, 0) / amount, 4)
                for source, amount in total.items() if amount > 0}
    return weighted, mix


GOOGLE_DEPTH = 10   # глубина выдачи xmlriver: позиции 11–20 сервис не отдаёт


def google_summary(google_rows: list, config: dict,
                   snapshot_date: str | None = None) -> dict | None:
    """Блок Google для снимка дня: наша доля, лидеры, покрытие.

    Считается тем же реестром доменов, что и Яндекс (registry.build), но по
    своему движку и региону — доля живёт внутри Google-поля и с долей в
    Яндексе не суммируется. Глубина выдачи — 10 позиций (xmlriver,
    проверено 03.09.2026): сравнивать «топ-10 из N» с Яндексом, где
    глубина 20, допустимо, доли — только внутри одного движка.
    """
    if not google_rows:
        return None
    region = next((r.region for r in google_rows if r.region), "")
    cards = registry.build(google_rows, config, engine="google",
                           region=region, date=snapshot_date)
    usable = [r for r in google_rows if r.has_data and r.region == region]
    ours = next((c for c in cards if c.domain == OURS), None)
    rivals = [c for c in cards if c.domain != OURS]
    leaders = [{"домен": c.domain, "категория": c.category,
                "доля": c.share, "топ3": c.top3, "топ10": c.top10,
                "лучшая_позиция": c.best_position}
               for c in rivals[:10]]
    our_queries = []
    for row in usable:
        position = next((i for i, item in enumerate(row.top, start=1)
                         if serp_source.normalize_domain(item.get("domain", ""))
                         == OURS), None)
        if position is not None:
            our_queries.append({"запрос": row.query, "позиция": position})
    return {
        "дата_среза": snapshot_date or (usable[0].date if usable else None),
        "источник": "xmlriver",
        "гео": f"Россия (loc {region})" if region else "Россия",
        "глубина": GOOGLE_DEPTH,
        "запросов_всего": len(google_rows),
        "запросов_с_данными": len(usable),
        "наша_доля_видимости": ours.share if ours else (0.0 if usable else None),
        "наша_взвешенная_видимость": ours.weighted_visibility if ours else 0.0,
        "топ3": ours.top3 if ours else 0,
        "топ10": ours.top10 if ours else 0,
        "лучшая_позиция": ours.best_position if ours else None,
        "наши_запросы": sorted(our_queries, key=lambda q: q["позиция"])[:20],
        "лидеры": leaders,
        "_пометка": ("глубина выдачи 10 позиций; доля считается внутри "
                     "Google-поля и с Яндексом не складывается"),
    }


def build_snapshot(date: str, cards: list, rows: list, config: dict,
                   query_sets_path: str | None = None,
                   google_rows: list | None = None,
                   google_date: str | None = None) -> dict:
    """Канонический снимок дня: цифры письма берутся только отсюда."""
    # Наш домен исключается из всех конкурентных срезов: он не конкурент сам
    # себе. Раньше biz-soft.pro попадал и в перечень «кто держит выдачу», и в
    # карточки конкурентов, а его доля вливалась в категорию «прямые
    # B2B-реселлеры» — из-за чего вес конкурентов в этой категории выглядел
    # больше, чем есть. Наша доля живёт отдельно, в «наши_показатели».
    rivals = [c for c in cards if c.domain != OURS]
    main = [c for c in rivals if c.in_main_ranking]
    ours = next((c for c in cards if c.domain == OURS), None)
    by_category: dict[str, float] = {}
    for card in rivals:
        by_category[card.category] = round(
            by_category.get(card.category, 0.0) + (card.share or 0.0), 6)

    usable = [r for r in rows if r.has_data]
    failed = [r for r in rows if not r.has_data]

    # Состав ядра фиксируется по всем запросам среза, а не по успешно
    # собранным: ядро — это то, что мы намерены мерить, а сбой сбора отдельного
    # запроса описывается покрытием. Иначе хеш ядра менялся бы от каждой
    # сетевой ошибки, и сравнимых дней не осталось бы вовсе.
    core = query_set.describe([r.query for r in rows], date, query_sets_path)
    per_query = per_query_visibility(rows, config)
    weighted_coverage, demand_mix = demand_coverage(rows)
    google = google_summary(google_rows or [], config, google_date)

    return {
        "дата": date,
        "собран": datetime.now(MSK).isoformat(),
        "версия_модели": config.get("версия"),
        "версия_конфига": config.get("версия"),
        "зрелость_скоринга": "базовый",
        # Блок метаданных: всё, что нужно, чтобы понять, каким инструментом
        # получены цифры этого дня и с какими другими днями их вообще
        # допустимо сравнивать. Введён в 1.3.0 по требованию внешнего аудита.
        "метаданные": {
            "версия_методики": config.get("версия"),
            "хеш_конфига": config_hash(config),
            "ядро_версия": core["версия"],
            "ядро_хеш": core["хеш"],
            "запросов_в_ядре": core["запросов"],
            "покрытие_запросов": (round(len(usable) / len(rows), 4)
                                  if rows else 0.0),
            "взвешенное_покрытие": weighted_coverage,
            "состав_источников_спроса": demand_mix,
            "opportunity_режим": "degraded",
            "opportunity_недоступные_факторы": ["vulnerability"],
            "threat_режим": "base_0_70",
            "_правило_сравнимости": (
                "сравнивать значения между датами допустимо только при "
                "совпадении версии методики, хеша конфига и хеша ядра; при "
                "различии ядра используется сравнимая доля, считаемая по "
                "пересечению составов (блок «по_запросам»)"),
        },
        # Состав зрелости оставлен отдельным блоком: письмо и отчёт читают
        # его напрямую, а метаданные адресованы аудиту и хранилищу.
        "состояние_зрелости": {
            "opportunity_режим": "degraded",
            "opportunity_недоступные_факторы": ["vulnerability"],
            "threat_режим": "base_0_70",
            "google_собирается": google is not None,
            "b2b_confidence_измеряется": False,
            "_правило_сравнимости": (
                "оценки сравнимы между датами только при одинаковой версии "
                "модели и одинаковом режиме доступности факторов; при "
                "включении ранее недоступного фактора начинается новая "
                "базовая линия, и изменение оценки через границу режима не "
                "интерпретируется как изменение самой возможности"),
        },
        "_зрелость_пояснение": (
            "Vulnerability недоступен до обхода страниц конкурентов, вес "
            "распределён пропорционально; Confidence рекомендаций не выше MEDIUM"),
        "ядро_запросов": core,
        # Видимость по запросам — основа сравнимой доли. Наши числа и поле
        # целиком; по этим двум рядам доля пересчитывается на любом
        # подмножестве запросов.
        "по_запросам": per_query,
        "покрытие": {
            "яндекс_запросов_всего": len(rows),
            "яндекс_запросов_с_данными": len(usable),
            "яндекс_ошибок": len(failed),
            "взвешенное_покрытие": weighted_coverage,
            # Поле google в покрытии читает kpi.build_kpi как нашу долю в
            # Google (share_google): None — NO DATA, число — доля внутри
            # Google-поля.
            "google": google["наша_доля_видимости"] if google else None,
            "google_запросов_с_данными": (google["запросов_с_данными"]
                                          if google else None),
            "_google_пояснение": (
                f"Google (xmlriver, {google['гео']}, глубина "
                f"{google['глубина']}): {google['запросов_с_данными']} "
                f"запросов с данными, срез за {google['дата_среза']}"
                if google else
                "NO DATA: Google-среза за эту дату нет (сбор еженедельный, "
                "ночь на понедельник)"),
        },
        "google": google,
        "наши_показатели": {
            "взвешенная_видимость": ours.weighted_visibility if ours else None,
            "доля_видимости": ours.share if ours else None,
            "топ3": ours.top3 if ours else None,
            "топ10": ours.top10 if ours else None,
            "запросов_в_поле": len(usable),
        } if ours else {"_нет_данных": "домен не найден в срезе"},
        "доли_по_категориям": by_category,
        "_доли_по_категориям_пояснение": (
            "доли конкурентов без BIZSoft; наша доля — в «наши_показатели», "
            "поэтому сумма меньше 100%"),
        "конкурентов_в_основном_рейтинге": len(main),
        "не_классифицировано": sum(1 for c in cards if c.category == "?"),
        "лидеры": [
            {"домен": c.domain, "категория": c.category, "доля": c.share,
             "топ3": c.top3, "топ10": c.top10}
            for c in main[:10]
        ],
    }


def main(argv: list[str]) -> int:
    dates = serp_source.available_dates()
    if not dates:
        print("Срезов выдачи в хранилище базового контура нет — нечего обрабатывать")
        return 1
    date = argv[1] if len(argv) > 1 else dates[-1]
    if date not in dates:
        print(f"Среза за {date} нет. Доступны: {', '.join(dates)}")
        return 1

    rows = serp_source.read_snapshot(date)
    config = visibility.load_config()
    cards = registry.build(rows, config, date=date)
    if not cards:
        print(f"Срез {date} не дал ни одного домена — прогон остановлен")
        return 1

    registry_path = registry.append(cards)
    snapshot = build_snapshot(date, cards, rows, config)
    os.makedirs(paths.SNAPSHOTS_DIR, exist_ok=True)
    snapshot_path = os.path.join(paths.SNAPSHOTS_DIR, f"{date}-discovery.json")
    with open(snapshot_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2)

    ours = snapshot["наши_показатели"]
    print(f"Дата среза: {date}")
    print(f"Доменов в поле: {len(cards)}, в основном рейтинге: "
          f"{snapshot['конкурентов_в_основном_рейтинге']}, "
          f"не классифицировано: {snapshot['не_классифицировано']}")
    if ours.get("доля_видимости") is not None:
        print(f"BIZSoft: доля {100 * ours['доля_видимости']:.2f}%, "
              f"топ-3 {ours['топ3']}, топ-10 {ours['топ10']}")
    print(f"Реестр: {registry_path}")
    print(f"Снимок: {snapshot_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
