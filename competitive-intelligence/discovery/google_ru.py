"""Google RU в снимке дня: блок по российской выдаче Google из среза xmlriver.

С 03.09.2026 у контура впервые есть настоящая российская Google-выдача
(xmlriver, местоположение 2643 — Россия), а не прокси-гео. Блок строится
из того же среза, что читает базовый SEO-контур (правило «один сбор — все
потребители»): собственных запросов к xmlriver здесь нет и быть не должно.

Что считается:
  * карточки доменов и наша доля взвешенной видимости — той же CTR-кривой и
    тем же классификатором, что для Яндекса (registry.build с engine="google");
  * покрытие, возраст и глубина среза — Google собирается раз в неделю, и
    блок честно говорит, за какую дату он и сколько позиций в нём есть
    (xmlriver отдаёт 10: параметр page сервис игнорирует, проверено
    03.09.2026);
  * разрыв с Яндексом по одному ядру: запросы, где Яндекс держит нас в
    топ-10, а в собранной выдаче Google нас нет, и наоборот. Это главный
    управленческий вопрос по Google — страница релевантна (Яндекс её
    ранжирует), значит дело в индексации, авторитете или конкурентоспособности
    страницы именно там;
  * точки атаки в Google — тем же Strike List, отдельным списком.

Чего здесь нет намеренно: единой цифры «Яндекс + Google» и динамики. Серия
google_ru начинается с первого среза; сводная видимость и тренд появятся,
когда накопится хотя бы месяц базовой линии (архитектурное решение
03.09.2026, docs/competitive/decisions-2026-09-03.md).
"""
from __future__ import annotations

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401
from discovery import query_set, registry, serp_source  # noqa: E402
from scoring import visibility  # noqa: E402

OURS = "biz-soft.pro"
YANDEX_REGION = "213"
MAX_GAP_ITEMS = 40
MAX_ATTACKS = 10
MAX_OUR_QUERIES = 20


def depth_of(rows) -> int:
    """Глубина собранной выдачи: 10 или 20 позиций по самой длинной строке.
    xmlriver отдаёт 10 (page игнорирует); при включении страниц станет 20."""
    longest = max((len(r.top) for r in rows if r.has_data), default=0)
    return 20 if longest > 10 else 10


def geo(config: dict) -> dict:
    g = (config.get("гео") or {}).get("google") or {}
    return {"провайдер": g.get("провайдер", "xmlriver"),
            "серия": g.get("серия", "google_ru"),
            "локация": g.get("локация", 2643),
            "название": g.get("название", "Россия"),
            "регион": str(g.get("регион", "2643")),
            "свежесть_дней": int(g.get("свежесть_дней", 8))}


def unavailable(reason: str, config: dict) -> dict:
    return {"доступен": False, "причина": reason, **geo(config)}


def _our_position(top: list[dict]) -> int | None:
    for index, item in enumerate(top, start=1):
        if serp_source.normalize_domain(item.get("domain", "")) == OURS:
            return index
    return None


def cross_engine_gap(google_rows, yandex_rows, region: str) -> dict:
    """Разрыв присутствия в топе между системами по общим запросам.

    Сравнивается присутствие, а не позиции: системы разные, и «5-е место в
    Яндексе против 12-го в Google» ничего не измеряет. «В Google нет» —
    нет в собранной выдаче (её глубина — поле «глубина_google»).
    """
    g = {query_set.normalize(r.query): r for r in google_rows
         if r.has_data and r.region == region}
    y = {query_set.normalize(r.query): r for r in yandex_rows
         if r.has_data and r.region == YANDEX_REGION}
    common = sorted(set(g) & set(y))
    both = 0
    ya_only: list[dict] = []
    g_only: list[dict] = []
    for key in common:
        ypos = _our_position(y[key].top)
        gpos = _our_position(g[key].top)
        if ypos and ypos <= 10 and gpos and gpos <= 10:
            both += 1
        elif ypos and ypos <= 10 and gpos is None:
            ya_only.append({
                "запрос": y[key].query, "позиция_яндекс": ypos,
                "google_топ3": [serp_source.normalize_domain(d.get("domain", ""))
                                for d in g[key].top[:3]]})
        elif gpos and gpos <= 10 and ypos is None:
            g_only.append({
                "запрос": g[key].query, "позиция_google": gpos,
                "яндекс_топ3": [serp_source.normalize_domain(d.get("domain", ""))
                                for d in y[key].top[:3]]})
    ya_only.sort(key=lambda i: i["позиция_яндекс"])
    g_only.sort(key=lambda i: i["позиция_google"])
    return {
        "сопоставлено": len(common),
        "в_обеих_топ10": both,
        "глубина_google": depth_of(google_rows),
        "глубина_яндекс": depth_of(yandex_rows),
        "яндекс_топ10_google_нет": ya_only[:MAX_GAP_ITEMS],
        "яндекс_топ10_google_нет_всего": len(ya_only),
        "google_топ10_яндекс_нет": g_only[:MAX_GAP_ITEMS],
        "google_топ10_яндекс_нет_всего": len(g_only),
        "_пояснение": ("запросы одного ядра, измеренные в обеих системах; "
                       "сравнивается присутствие в собранной выдаче, не "
                       "позиции; «нет» — нет в выдаче своей глубины"),
    }


def build_block(date: str, google_date: str | None, google_rows,
                yandex_rows, config: dict, attacks: list[dict] | None = None
                ) -> dict:
    """Блок Google RU для снимка дня. Без свежего среза — «недоступен»."""
    g = geo(config)
    if not google_date or not google_rows:
        return unavailable("свежего среза Google нет (сбор еженедельный, "
                           f"окно {g['свежесть_дней']} дней)", config)
    region = g["регион"]
    rows = [r for r in google_rows if r.region == region]
    usable = [r for r in rows if r.has_data]
    if not usable:
        return unavailable(f"в срезе {google_date} нет пригодных строк по "
                           f"региону {region}", config)

    cards = registry.build(rows, config, engine="google", region=region,
                           date=google_date)
    rivals = [c for c in cards if c.domain != OURS]
    main = [c for c in rivals if c.in_main_ranking]
    ours = next((c for c in cards if c.domain == OURS), None)
    by_category: dict[str, float] = {}
    for card in rivals:
        by_category[card.category] = round(
            by_category.get(card.category, 0.0) + (card.share or 0.0), 6)

    # По-запросная видимость — тем же способом, что для Яндекса, чтобы
    # сравнимая доля по пересечению ядер считалась и здесь.
    from discovery import run_discovery
    per_query = run_discovery.per_query_visibility(rows, config, region=region)
    depth = depth_of(rows)
    our_queries = sorted(
        ({"запрос": q, "позиция": v["позиция"]}
         for q, v in per_query.items() if v.get("позиция")),
        key=lambda item: item["позиция"])

    age = (dt.date.fromisoformat(date) - dt.date.fromisoformat(google_date)).days
    attacks = attacks or []
    return {
        "доступен": True,
        **g,
        "дата_среза": google_date,
        "возраст_дней": age,
        "глубина": depth,
        "покрытие": {
            "запросов_всего": len(rows),
            "запросов_с_данными": len(usable),
            "ошибок": len(rows) - len(usable),
            "покрытие_запросов": round(len(usable) / len(rows), 4) if rows else 0.0,
        },
        "наши_показатели": ({
            "взвешенная_видимость": ours.weighted_visibility,
            "доля_видимости": ours.share,
            "топ3": ours.top3,
            "топ10": ours.top10,
            "в_выдаче": len(our_queries),
            "лучшая_позиция": ours.best_position,
            "запросов_в_поле": len(usable),
        } if ours else {
            "взвешенная_видимость": 0.0, "доля_видимости": 0.0,
            "топ3": 0, "топ10": 0, "в_выдаче": 0, "лучшая_позиция": None,
            "запросов_в_поле": len(usable),
            "_пояснение": "домен не найден ни в одной выдаче среза: это "
                          "измеренный ноль, а не отсутствие данных",
        }),
        "наши_запросы": our_queries[:MAX_OUR_QUERIES],
        "по_запросам": per_query,
        "доли_по_категориям": by_category,
        "конкурентов_в_основном_рейтинге": len(main),
        "лидеры": [
            {"домен": c.domain, "категория": c.category, "доля": c.share,
             "топ3": c.top3, "топ10": c.top10}
            for c in main[:10]
        ],
        "разрыв_с_яндексом": cross_engine_gap(rows, yandex_rows, region),
        "точки_атаки": {
            "всего": len(attacks),
            "первые": [
                {"запрос": a["query"], "наша_позиция": a["our_position"],
                 "соперник": a["rival_domain"],
                 "позиция_соперника": a["rival_position"],
                 "вид": a.get("competition_kind"),
                 "opportunity": a.get("opportunity")}
                for a in attacks[:MAX_ATTACKS]
            ],
        },
        "_правило_сравнимости": (
            "серия google_ru начинается с первого среза; сводной цифры с "
            "Яндексом и динамики нет до накопления базовой линии; доли "
            "считаются внутри Google-поля глубиной «глубина» позиций и с "
            "Яндексом не складываются; позиции двух систем не сравниваются "
            "как равноточные"),
    }


def share(block: dict | None) -> float | None:
    """Наша доля в Google из блока; NO DATA, если блока или среза нет."""
    if not block or not block.get("доступен"):
        return None
    return (block.get("наши_показатели") or {}).get("доля_видимости")
