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
    (10 позиций на страницу, страницы нумеруются с единицы; `pages` в
    data/seo/xmlriver.json — сейчас 2, то есть топ-20);
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
from discovery import index_status, query_set, registry  # noqa: E402
from discovery import serp_source  # noqa: E402
from scoring import visibility  # noqa: E402

OURS = "biz-soft.pro"
YANDEX_REGION = "213"
MAX_GAP_ITEMS = 40
MAX_ATTACKS = 10
MAX_OUR_QUERIES = 20


def depth_of(rows) -> int:
    """Глубина собранной выдачи: 10 или 20 позиций по самой длинной строке
    (страница xmlriver — 10 позиций, число страниц задаёт конфиг сборщика)."""
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


def absence_profile(google_rows, yandex_rows, region: str) -> dict:
    """Чьё отсутствие мы видим: страницы или домена.

    Зачем нужно (разбор 10.09.2026). Отчёт называл разрыв «главным вопросом
    по Google», перечислял три гипотезы — индексация, авторитет домена,
    конкурентоспособность страницы — и на этом останавливался: гипотезы не
    ранжировались, проверка не предлагалась, поручений не выдавалось. Между
    тем данные для разведения гипотез уже собраны и лежат в том же срезе.

    Разводит их одна величина: встречается ли наша страница в Google-срезе
    хоть где-нибудь — по любому запросу, на любой позиции своей глубины.
    Страница, проигрывающая по релевантности, стоит на 11–20 месте и в срез
    попадает. Страница, которой в срезе нет ни разу, проигрывает не
    конкурентам — её там просто нет.

    Величина не доказывает отсутствие в индексе: страница может быть
    проиндексирована и стоять пятидесятой. Она отвечает на более узкий и
    более полезный вопрос — какую гипотезу проверять первой.
    """
    g = {query_set.normalize(r.query): r for r in google_rows
         if r.has_data and r.region == region}
    y = {query_set.normalize(r.query): r for r in yandex_rows
         if r.has_data and r.region == YANDEX_REGION}
    # Все наши URL, встреченные в Google-срезе где угодно: срез читается
    # целиком, а не по запросам разрыва — страница могла попасть в топ по
    # другому запросу, и это тоже присутствие.
    в_google = {(item.get("url") or "")
                for row in g.values() for item in row.top
                if serp_source.normalize_domain(item.get("domain", "")) == OURS}
    страницы: dict[str, dict] = {}
    for key in set(g) & set(y):
        ypos = _our_position(y[key].top)
        if not ypos or ypos > 10 or _our_position(g[key].top) is not None:
            continue
        url = next((item.get("url") or "" for item in y[key].top
                    if serp_source.normalize_domain(item.get("domain", ""))
                    == OURS), "")
        класс, дословно = index_status.state(url)
        скачан = index_status.crawled(url)
        запись = страницы.setdefault(url, {"url": url, "запросов": 0,
                                           "лучшая_позиция_яндекс": ypos,
                                           "есть_в_google_срезе": url in в_google,
                                           "индекс": класс,
                                           "индекс_дословно": дословно,
                                           "скачан_гуглом": скачан})
        запись["запросов"] += 1
        запись["лучшая_позиция_яндекс"] = min(запись["лучшая_позиция_яндекс"], ypos)
    ранжир = sorted(страницы.values(),
                    key=lambda p: (-p["запросов"], p["лучшая_позиция_яндекс"]))
    отсутствуют = [p for p in ранжир if not p["есть_в_google_срезе"]]
    по_индексу: dict[str, int] = {}
    for страница in ранжир:
        ключ = страница["индекс"]
        по_индексу[ключ] = по_индексу.get(ключ, 0) + 1
    return {
        "страниц_в_разрыве": len(ранжир),
        "страниц_есть_в_срезе": len(ранжир) - len(отсутствуют),
        "страниц_нет_в_срезе": len(отсутствуют),
        "наших_url_в_срезе_всего": len(в_google),
        # Разбивка по статусу индексации: она и разводит гипотезы,
        # причём по данным, которые базовый контур уже собрал.
        "по_индексу": по_индексу,
        "индекс_доступен": index_status.available(),
        "индекс_дата": index_status.snapshot_date(),
        # Сколько страниц разрыва Google вообще скачивал. Отличает
        # очередь обхода от приговора качеству: страницу, которую не
        # скачивали, бесполезно переписывать (разбор 10.09.2026).
        "не_скачано": sum(1 for p in ранжир if not p["скачан_гуглом"]),
        "обход_по_сайту": index_status.crawl_summary(),
        "первые": ранжир[:MAX_GAP_ITEMS],
        "_пояснение": (
            "страница считается присутствующей, если встречена в Google-срезе "
            "по любому запросу на любой позиции его глубины; отсутствие в "
            "срезе не доказывает отсутствия в индексе — страница может быть "
            "проиндексирована и стоять ниже собранной глубины"),
    }


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
        "профиль_отсутствия": absence_profile(rows, yandex_rows, region),
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
