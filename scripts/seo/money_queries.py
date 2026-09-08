#!/usr/bin/env python3
"""Money Query Opportunity Model: где переходы дешевле всего при текущих показах.

Модель отвечает на один вопрос: какие кластеры запросов дают больше всего
недополученных переходов при уже занятых позициях, и что именно им мешает —
сниппет или позиция. Отбор по количеству показов не используется: показы без
коммерческого интента и без релевантной посадочной страницы деньгами не
становятся.

    opportunity = потерянные_клики × интент × ценность × релевантность × (1 − риск)

Слагаемые считаются раздельно и хранятся в бэклоге, чтобы решение можно было
перепроверить, а не принять на веру суммарной цифрой.

Источники (все — ветка seo-data, сессия ничего не запрашивает по сети):
  reports/seo/data/yandex-<дата>.json      — запросы Вебмастера (окно 12 дней);
  reports/seo/serp/<дата>-serp.jsonl       — срез выдачи: наш URL и конкуренты;
  reports/seo/intelligence/seo-experiments.json — занятость кластеров.

Запуск:
  python3 scripts/seo/money_queries.py --seo-data <путь к ветке seo-data> \
      [--date 2026-09-08] [--out reports/seo/yandex-money-backlog.json]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
from collections import defaultdict

# ─────────────────────────── Кривая CTR ───────────────────────────
#
# Опорная кривая — доля переходов по позиции органической выдачи Яндекса на
# коммерческом запросе. Числа не измерены нами: это отраслевой ориентир, и
# ниже он умножается на ATTAINABLE — долю, которую реально забрать на выдаче с
# рекламными блоками и колдунщиками над органикой. Прямое сравнение с «сырой»
# кривой завышало бы недобор в разы и делало бы приоритеты бессмысленными.
CTR_CURVE = {1: 0.280, 2: 0.160, 3: 0.110, 4: 0.078, 5: 0.058,
             6: 0.045, 7: 0.035, 8: 0.028, 9: 0.023, 10: 0.020}
CTR_TAIL = {15: 0.012, 20: 0.007, 100: 0.003}
ATTAINABLE = 0.5

# Наблюдаемый CTR полос на 08.09.2026 (окно 25.08–05.09): 1–3 — 4,87 %,
# 4–6 — 0,56 %, 7–10 — 0,19 %. Полоса 1–3 работает; аномалия — 4–10.
BANDS = [
    ("A", 0.0, 3.0, "1–3: позиция взята, вопрос к сниппету"),
    ("B", 3.0, 6.0, "4–6: первый экран выдачи, сниппет решает"),
    ("C", 6.0, 10.0, "7–10: низ первой страницы, нужны и сниппет, и позиция"),
    ("D", 10.0, 20.0, "11–20: вторая страница, вопрос к позиции"),
    ("E", 20.0, 1e9, "21+: вне зоны быстрых решений"),
]

# ─────────────────────────── Интент ───────────────────────────
#
# Вес интента — не «купить в запросе», а близость формулировки к сделке.
# «оплата X юридическим лицом» — покупатель с бухгалтерией и счётом;
# «X цена» — сравнение; «как оплатить X» — выбор способа; «X скачать» — не наш.
INTENT_RULES = [
    ("transactional_b2b", 1.00, [
        r"юридическ", r"юрлиц", r"юр\.?\s*лиц", r"на компани", r"для компани",
        r"для организаци", r"по счет", r"по счёт", r"безнал", r"счет на оплату",
        r"счёт на оплату", r"договор", r"эдо", r"закрывающ", r"для бизнеса",
        r"корпоративн", r"b2b",
    ]),
    ("transactional", 0.85, [
        r"купить", r"оплат", r"заказать", r"приобрест", r"оформить",
        r"продлить", r"подключить", r"buy", r"покупк",
    ]),
    ("commercial_research", 0.60, [
        r"цена", r"цены", r"стоимост", r"сколько стоит", r"тариф", r"прайс",
        r"подписк", r"лицензи", r"price", r"в рубл",
    ]),
    ("availability", 0.55, [
        r"в росси", r"из росси", r"для россиян", r"рф\b", r"работает ли",
        r"доступ",
    ]),
    ("informational", 0.25, [
        r"^как ", r"^что ", r"^почему ", r"^чем ", r"^зачем ", r"отличи",
        r"сравнен", r"vs\b", r"обзор", r"инструкц",
    ]),
    ("disqualified", 0.05, [
        r"скачать", r"торрент", r"torrent", r"кряк", r"crack", r"взлом",
        r"бесплатн", r"free\b", r"пиратск", r"активатор", r"кейген",
        r"урок", r"как рисовать", r"курс",
    ]),
]

BRAND_SELF = ("bizsoft", "биз софт", "бизсофт", "biz-soft", "биз-софт")


def intent_of(query: str) -> tuple[str, float]:
    low = query.lower()
    if any(b in low for b in BRAND_SELF):
        return "navigational_own", 0.10
    # Дисквалификация проверяется первой: «скачать X бесплатно» содержит и
    # «скачать», и, бывает, «купить» — деньгами такой запрос не становится.
    for name, weight, pats in INTENT_RULES:
        if name != "disqualified":
            continue
        if any(re.search(p, low) for p in pats):
            return name, weight
    for name, weight, pats in INTENT_RULES:
        if name == "disqualified":
            continue
        if any(re.search(p, low) for p in pats):
            return name, weight
    return "unknown", 0.35


def expected_ctr(position: float) -> float:
    """Достижимая доля переходов на позиции: опорная кривая × ATTAINABLE."""
    if position is None:
        return 0.0
    p = max(1.0, position)
    if p <= 10:
        lo, hi = int(p), min(10, int(p) + 1)
        frac = p - lo
        base = CTR_CURVE[lo] + (CTR_CURVE.get(hi, CTR_CURVE[10]) - CTR_CURVE[lo]) * frac
    else:
        base = CTR_TAIL[100]
        for edge in sorted(CTR_TAIL):
            if p <= edge:
                base = CTR_TAIL[edge]
                break
    return base * ATTAINABLE


def band_of(position: float | None) -> tuple[str, str]:
    if position is None:
        return "E", BANDS[-1][3]
    for code, lo, hi, label in BANDS:
        if lo < position <= hi:
            return code, label
    return "E", BANDS[-1][3]


# ─────────────────────── Кластеры и посадочные ───────────────────────
#
# Кластер — бренд, а не запрос: решение принимается по странице, а страница
# одна на бренд. Кириллические написания заведены только там, где они реально
# встречаются в запросах Вебмастера; список пополняется по факту, а не
# транслитерацией всех 105 вендоров впрок.
ALIASES: dict[str, list[str]] = {
    "openai": ["openai", "chatgpt", "chat gpt", "гпт", "чатгпт", "опенаи", "gpt-4", "gpt 4"],
    "zoom": ["zoom", "зум"],
    "jetbrains": ["jetbrains", "джетбрейнс", "intellij", "pycharm", "webstorm", "rider"],
    "figma": ["figma", "фигма"],
    "capture-one": ["capture one", "capture-one", "кэпчур", "капчур"],
    "foundry": ["foundry", "фаундри", "nuke", "modo"],
    "reallusion": ["reallusion", "character creator", "iclone"],
    "vegas": ["vegas pro", "вегас"],
    "gaea": ["gaea", "гаеа", "гея"],
    "hailuo": ["hailuo", "хайлуо", "минимакс", "minimax"],
    "maxon": ["maxon", "cinema 4d", "синема 4d", "zbrush", "збраш", "redshift"],
    "adobe": ["adobe", "адоб", "photoshop", "фотошоп", "illustrator", "иллюстратор",
              "premiere pro", "after effects", "афтер эффект", "lightroom", "лайтрум",
              "acrobat", "акробат", "creative cloud"],
    "anthropic": ["anthropic", "claude", "клод", "клауд", "cloude"],
    "artlist": ["artlist", "артлист", "art list"],
    "atlassian": ["atlassian", "атлассиан", "jira", "джира", "confluence", "конфлюенс"],
    "autodesk": ["autodesk", "автодеск", "autocad", "автокад", "3ds max", "fusion 360", "maya"],
    "blackmagic": ["blackmagic", "davinci", "давинчи", "резолв", "resolve"],
    "box": ["box", "бокс"],
    "browserstack": ["browserstack", "браузерстек"],
    "canva": ["canva", "канва"],
    "capcut": ["capcut", "капкат", "кап кат"],
    "clip-studio-paint": ["clip studio", "clipstudio", "клип студио", "клипстудио"],
    "cloudflare": ["cloudflare", "клаудфлар", "клаудфлаер"],
    "coreldraw": ["coreldraw", "corel draw", "корел", "корэл"],
    "cursor": ["cursor", "курсор ai", "cursor ai"],
    "deepl": ["deepl", "дипл"],
    "depositphotos": ["depositphotos", "депозитфотос", "депозит фото"],
    "descript": ["descript", "дескрипт"],
    "discord": ["discord", "дискорд"],
    "docker": ["docker", "докер"],
    "dropbox": ["dropbox", "дропбокс", "дроп бокс"],
    "elevenlabs": ["elevenlabs", "eleven labs", "элевенлабс", "илевенлабс"],
    "envato": ["envato", "энвато"],
    "epidemic-sound": ["epidemic sound", "эпидемик"],
    "fl-studio": ["fl studio", "фл студио", "фрути"],
    "framer": ["framer", "фреймер"],
    "freepik": ["freepik", "фрипик", "magnific", "магнифик"],
    "github": ["github", "гитхаб", "copilot", "копайлот"],
    "gitlab": ["gitlab", "гитлаб"],
    "google": ["google workspace", "гугл воркспейс", "gemini", "джемини", "гемини"],
    "grok": ["grok", "грок"],
    "heygen": ["heygen", "хейген", "хейджен"],
    "higgsfield": ["higgsfield", "хиггсфилд"],
    "houdini": ["houdini", "гудини", "худини"],
    "izotope": ["izotope", "изотоп"],
    "kling-ai": ["kling", "клинг"],
    "krea": ["krea", "креа"],
    "leonardo-ai": ["leonardo", "леонардо"],
    "lovable": ["lovable", "лавбл"],
    "microsoft": ["microsoft 365", "office 365", "майкрософт", "офис 365", "teams"],
    "midjourney": ["midjourney", "миджорни", "мидджорни"],
    "miro": ["miro", "миро"],
    "motion-array": ["motion array", "моушн эррей", "моушен эррей"],
    "n8n": ["n8n"],
    "native-instruments": ["native instruments", "kontakt", "контакт"],
    "notion": ["notion", "ноушен", "ноушн"],
    "openrouter": ["openrouter", "open router"],
    "parallels": ["parallels", "параллелс"],
    "perplexity": ["perplexity", "перплексити", "перплекс"],
    "postman": ["postman", "постман"],
    "procreate": ["procreate", "прокриейт", "прокриэйт", "прокреат"],
    "recraft": ["recraft", "рекрафт"],
    "runway": ["runway", "рунвей", "ранвей"],
    "sentry": ["sentry", "сентри"],
    "shutterstock": ["shutterstock", "шаттерсток"],
    "sketchup": ["sketchup", "скетчап"],
    "slack": ["slack", "слак", "слэк"],
    "solidworks": ["solidworks", "солидворкс"],
    "spine": ["spine 2d", "spine esoteric", "спайн"],
    "suno": ["suno", "суно"],
    "teamviewer": ["teamviewer", "тимвьювер"],
    "topaz-labs": ["topaz", "топаз"],
    "unity": ["unity", "юнити"],
    "unreal-engine": ["unreal", "анрил"],
    "windsurf": ["windsurf", "виндсерф", "винд серф"],
    "wondershare": ["wondershare", "filmora", "фильмора"],
    "zoho": ["zoho", "зохо"],
}

# Омонимы: слово встречается и вне нашего кластера. Запрос с этими словами в
# кластер не попадает, даже если совпал алиас.
CLUSTER_EXCLUDE: dict[str, list[str]] = {
    "box": ["xbox", "x box", "бизнес бокс", "коробк", "boxing", "бокс тайск",
            "бокс удар", "dropbox", "дропбокс"],
    "leonardo-ai": ["da vinci", "да винчи"],
    "github": ["microsoft copilot", "ms copilot", "video copilot"],
    "google": ["google play", "гугл плей"],
    "notion": ["notion press"],
    "cursor": ["курсор мыши", "курсор windows"],
}


# Небрендовые кластеры: запрос описывает саму услугу, а не продукт вендора.
# Это единственная группа, где обещание BIZSoft — предмет запроса, а не
# сопровождение к бренду, и где нет конкуренции с брендовыми страницами.
GENERIC_CLUSTERS: dict[str, list[str]] = {
    "generic-foreign-software": [
        r"зарубежн\w*\s+(по|софт|сервис|подписк|программ)",
        r"иностранн\w*\s+(по|софт|сервис|подписк|провайдер|облачн)",
        r"(оплат|купить|приобрест)\w*\s+зарубежн",
        r"закрывающ\w*\s+документ\w*\s+(от|для)\s+иностранн",
        r"корпоративн\w*\s+(подписк|ai-сервис|ai сервис|договор)",
    ],
}


def load_vendor_slugs(repo: pathlib.Path) -> set[str]:
    """Слаги всех vendor-страниц: и шаблонные из реестра, и bespoke-страницы.

    Zoom, JetBrains, OpenAI и Figma в реестре VENDORS отсутствуют — у них
    собственные .astro. Кластеризация по одному реестру их бы потеряла, а
    показы по ним есть.
    """
    slugs: set[str] = set()
    src = repo / "src" / "data" / "vendors.ts"
    if src.exists():
        slugs |= set(re.findall(r"\{\s*slug:\s*'([^']+)'", src.read_text(encoding="utf-8")))
    pages = repo / "src" / "pages" / "vendors"
    if pages.is_dir():
        slugs |= {p.stem for p in pages.iterdir()
                  if p.stem not in ("index", "[slug]") and not p.stem.startswith("[")}
    return slugs


def cluster_of(query: str, slugs: set[str]) -> str | None:
    """Кластер запроса: сначала бренд, затем небрендовый кросс-вендорный интент.

    Многословный алиас проверяется и по вхождению целиком, и по наличию всех
    слов в любом порядке: Яндекс отдаёт запросы в нормализованном виде, где
    порядок слов перемешан («capture оплата one лицом юридическим» — это
    Capture One), и подстрочный поиск такие запросы терял.
    """
    low = f" {query.lower()} "
    hits: list[tuple[int, str]] = []
    for slug, words in ALIASES.items():
        if any(x in low for x in CLUSTER_EXCLUDE.get(slug, ())):
            continue
        for w in words:
            if w in low:
                hits.append((len(w) + 1, slug))
            elif " " in w and all(re.search(rf"\b{re.escape(t)}", low) for t in w.split()):
                hits.append((len(w), slug))
    if hits:
        # Самый длинный алиас выигрывает: «motion array» точнее, чем «array».
        return max(hits)[1]
    for slug in slugs:
        if any(x in low for x in CLUSTER_EXCLUDE.get(slug, ())):
            continue
        if slug.replace("-", " ") in low or slug in low:
            return slug
    for name, pats in GENERIC_CLUSTERS.items():
        if any(re.search(p, low) for p in pats):
            return name
    return None



# ─────────────────────── Ценность и релевантность ───────────────────────
#
# Ценность кластера — не выручка (её в этих данных нет), а тип сделки, который
# кластер приводит: подписка на команду продлевается ежегодно и растёт числом
# мест, разовая лицензия платится один раз, подарочная карта — с наценкой ×3,
# но без продления. Веса заданы явно, чтобы их можно было оспорить.
VALUE_TIER = {
    "team_subscription": 1.00,   # места × год: Claude, Perplexity, GitHub, Atlassian
    "studio_license": 0.85,      # дорогая разовая или годовая: Autodesk, Unity, Houdini
    "content_subscription": 0.70,  # стоки и медиатеки: Artlist, Envato, Depositphotos
    "single_seat": 0.55,         # одно место, малая сумма: Procreate, WinRAR
}
CLUSTER_VALUE = {
    "anthropic": "team_subscription", "perplexity": "team_subscription",
    "github": "team_subscription", "gitlab": "team_subscription",
    "atlassian": "team_subscription", "microsoft": "team_subscription",
    "google": "team_subscription", "slack": "team_subscription",
    "notion": "team_subscription", "cloudflare": "team_subscription",
    "box": "team_subscription", "dropbox": "team_subscription",
    "docker": "team_subscription", "postman": "team_subscription",
    "browserstack": "team_subscription", "sentry": "team_subscription",
    "windsurf": "team_subscription", "cursor": "team_subscription",
    "zoho": "team_subscription", "teamviewer": "team_subscription",
    "openai": "team_subscription", "zoom": "team_subscription",
    "jetbrains": "team_subscription", "figma": "team_subscription",
    "generic-foreign-software": "team_subscription",
    "capture-one": "studio_license", "foundry": "studio_license",
    "reallusion": "studio_license", "vegas": "studio_license",
    "gaea": "studio_license", "maxon": "studio_license",
    "hailuo": "content_subscription", "grok": "team_subscription",
    "kling-ai": "content_subscription", "suno": "content_subscription",
    "autodesk": "studio_license", "unity": "studio_license",
    "unreal-engine": "studio_license", "houdini": "studio_license",
    "solidworks": "studio_license", "adobe": "studio_license",
    "blackmagic": "studio_license", "coreldraw": "studio_license",
    "spine": "studio_license", "sketchup": "studio_license",
    "artlist": "content_subscription", "motion-array": "content_subscription",
    "envato": "content_subscription", "depositphotos": "content_subscription",
    "shutterstock": "content_subscription", "freepik": "content_subscription",
    "epidemic-sound": "content_subscription", "canva": "content_subscription",
    "heygen": "content_subscription", "elevenlabs": "content_subscription",
    "runway": "content_subscription", "descript": "content_subscription",
    "midjourney": "content_subscription", "recraft": "content_subscription",
    "framer": "content_subscription", "miro": "content_subscription",
}

# Насколько тип страницы отвечает интенту запроса. Число входит в оценку
# множителем: страница не под интент обесценивает даже идеальную позицию.
RELEVANCE = {
    ("transactional_b2b", "/product/"): 1.00,
    ("transactional_b2b", "/vendors/"): 0.90,
    ("transactional_b2b", "/blog/"): 0.70,
    ("transactional", "/product/"): 0.95,
    ("transactional", "/vendors/"): 0.95,
    ("transactional", "/blog/"): 0.65,
    ("commercial_research", "/product/"): 0.90,
    ("commercial_research", "/vendors/"): 0.85,
    ("commercial_research", "/blog/"): 0.70,
    ("availability", "/blog/"): 0.90,
    ("availability", "/vendors/"): 0.80,
    ("availability", "/product/"): 0.60,
    ("informational", "/blog/"): 1.00,
    ("informational", "/vendors/"): 0.50,
    ("informational", "/product/"): 0.35,
}
DEFAULT_RELEVANCE = 0.60


def relevance_of(intent: str, url: str | None) -> float:
    if not url:
        return 0.40      # страницы в срезе выдачи нет — соответствие неизвестно
    for (i, prefix), value in RELEVANCE.items():
        if i == intent and prefix in url:
            return value
    if "/alternatives/" in url or "/compare/" in url:
        return 0.55 if intent.startswith("transaction") else 0.85
    if url.rstrip("/").endswith("biz-soft.pro") or "/catalog" in url:
        return 0.45
    return DEFAULT_RELEVANCE


# ─────────────────────────── Риск ───────────────────────────
#
# Риск — вероятность потерять то, что уже есть. Сниппет на странице в топ-3 с
# переходами трогать дороже, чем на странице в топ-10 без единого перехода:
# в первом случае теряется работающий результат, во втором терять нечего.
def risk_of(band: str, clicks: int, occupied: str | None, page_kind: str) -> tuple[float, str]:
    if occupied:
        return 0.90, f"кластер занят экспериментом {occupied} — правка ломает его атрибуцию"
    if band == "A" and clicks > 0:
        return 0.55, "топ-3 с переходами: правка сниппета рискует работающим результатом"
    if band == "A":
        return 0.20, "топ-3 без переходов: терять нечего, позиция уже взята"
    if band in ("B", "C"):
        base = 0.15 if page_kind in ("/vendors/", "/product/") else 0.25
        return base, "правка сниппета на первой странице: позиция от текста заголовка меняется слабо"
    if band == "D":
        return 0.35, "вторая страница: нужен контент, а он меняет и релевантность страницы"
    return 0.50, "вне зоны быстрых решений"


# ─────────────────────────── Форма спроса ───────────────────────────
#
# Разбор кластера Recraft (правило `docs/rules/snippet-experiments.md`) показал:
# в одном окне затухший всплеск и живой спрос выглядят одинаково. Поэтому
# кластер проверяется по ряду выгрузок, а не по последней: у живого спроса ряд
# монотонен или ровен, у всплеска — прыжок и откат.
#
# Признак искусственной серии дополняет ряд: у органического кластера показы
# распределены по степенному закону (один-два запроса держат заметную долю), у
# сгенерированного перебора фраз — почти поровну. Мера — коэффициент Джини.
BURST_VOLATILITY = 5.0     # max/min по ряду выгрузок
BURST_GINI = 0.50          # ниже — распределение подозрительно ровное
TREND_WINDOW = 8           # сколько последних выгрузок смотреть


def gini(values: list[int]) -> float:
    xs = sorted(values)
    n, total = len(xs), sum(xs)
    if n < 2 or total == 0:
        return 0.0
    return (2 * sum((i + 1) * x for i, x in enumerate(xs))) / (n * total) - (n + 1) / n


def demand_shape(series: list[float], absolute: list[int],
                 dispersion: float) -> tuple[str, str]:
    """Форма спроса кластера: растущий, устойчивый, затухающий или всплеск.

    На вход идёт доля кластера в показах сайта, а не абсолютные показы: 06.09
    выгрузка Вебмастера расширилась с ~1040 запросов до ~1530 (полный обход
    вместо усечения), показы сайта в ней выросли на 49 % за один день. По
    абсолютному ряду каждый второй кластер выглядел бы взрывным ростом.
    """
    live = [v for v in series if v is not None]
    if len(live) < 4:
        return "unknown", "ряда выгрузок не хватает для суждения о форме спроса"
    shown = [round(v * 100, 2) for v in live]
    lo, hi = min(live), max(live)
    volatility = hi / lo if lo > 0 else float("inf")
    up = all(b >= a * 0.8 for a, b in zip(live, live[1:]))
    down = all(b <= a * 1.25 for a, b in zip(live, live[1:]))
    flat = f" (Джини {dispersion:.2f})" if dispersion < BURST_GINI else ""
    # Затухание объявляется только когда падает и доля, и абсолютные показы:
    # доля кластера падает и просто потому, что сайт растёт в другом месте, и
    # ровный кластер в растущем сайте затухающим называть нельзя.
    abs_live = [v for v in absolute if v is not None]
    abs_down = bool(abs_live) and abs_live[-1] <= max(abs_live[0], 1) * 0.6
    if down and abs_down and live[-1] <= max(live[0], 1e-9) * 0.6:
        return "decaying", (f"доля кластера в показах сайта {shown} % при показах "
                            f"{abs_live} — спрос затухает, правка догоняет "
                            "уходящий интерес")
    if volatility >= BURST_VOLATILITY and not up:
        return "burst", (f"доля кластера в показах сайта {shown} %: разброс "
                         f"{volatility:.0f}× с откатом — всплеск, а не спрос{flat}")
    if dispersion < BURST_GINI and volatility >= BURST_VOLATILITY and len(live) >= 6:
        return "burst", (f"показы распределены почти поровну между запросами{flat} "
                         f"при разбросе доли {volatility:.0f}× — признак перебора "
                         "фраз, а не людей")
    if up and live[-1] >= max(live[0], 1e-9) * 1.5:
        return "growing", f"доля кластера в показах сайта {shown} % — спрос растёт"
    return "steady", (f"доля кластера в показах сайта {shown} % при показах "
                      f"{abs_live} — спрос держится ровно")



# ─────────────────────────── Загрузка данных ───────────────────────────

def load_queries(seo_data: pathlib.Path, date: str) -> tuple[list[dict], dict]:
    path = seo_data / "reports" / "seo" / "data" / f"yandex-{date}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    pq = raw["popular_queries"]
    rows = []
    for q in pq["queries"]:
        ind = q["indicators"]
        rows.append({
            "query": q["query_text"],
            "impressions": int(ind["TOTAL_SHOWS"] or 0),
            "clicks": int(ind["TOTAL_CLICKS"] or 0),
            "position": ind["AVG_SHOW_POSITION"],
        })
    window = {"from": pq["date_from"], "to": pq["date_to"], "source": path.name}
    return rows, window


def load_history(seo_data: pathlib.Path, date: str, slugs: set[str],
                 window: int = TREND_WINDOW) -> dict[str, dict[str, list]]:
    """Доля каждого кластера в показах сайта по последним выгрузкам.

    Окна выгрузок скользящие и перекрываются — ряд читается как форма спроса,
    а не как сумма периодов. Доля вместо абсолютных показов нужна потому, что
    полнота самой выгрузки менялась (06.09.2026 — переход на полный обход).
    """
    data_dir = seo_data / "reports" / "seo" / "data"
    files = sorted(p for p in data_dir.glob("yandex-2026-*.json") if p.stem[-10:] <= date)
    series: dict[str, dict[str, list]] = defaultdict(lambda: {"share": [], "impressions": []})
    for path in files[-window:]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows = (raw.get("popular_queries") or {}).get("queries") or []
        if not rows:
            continue
        total = sum(int(q["indicators"]["TOTAL_SHOWS"] or 0) for q in rows) or 1
        day: dict[str, int] = defaultdict(int)
        for q in rows:
            slug = cluster_of(q["query_text"], slugs)
            if slug:
                day[slug] += int(q["indicators"]["TOTAL_SHOWS"] or 0)
        for slug in set(day) | set(series):
            series[slug]["impressions"].append(day.get(slug, 0))
            series[slug]["share"].append(round(day.get(slug, 0) / total, 5))
    return dict(series)



def load_serp(seo_data: pathlib.Path, date: str) -> dict[str, dict]:
    path = seo_data / "reports" / "seo" / "serp" / f"{date}-serp.jsonl"
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        top = row.get("top") or []
        ours = next(((i + 1, t) for i, t in enumerate(top)
                     if t.get("domain") == "biz-soft.pro"), None)
        out[row["query"]] = {
            "serp_position": ours[0] if ours else None,
            "our_url": ours[1]["url"] if ours else None,
            "our_title": ours[1]["title"] if ours else None,
            "competitors": [{"pos": i + 1, "domain": t["domain"], "url": t["url"],
                             "title": t["title"]}
                            for i, t in enumerate(top[:5])],
        }
    return out


def code_occupancy(repo: pathlib.Path) -> dict[str, str]:
    """Слаги с действующим переопределением сниппета в коде.

    Реестр экспериментов и код разошлись: партия «snippets-10-expand» от
    02.09.2026 выкачена в src/data/seo-experiments.ts, но записи в
    reports/seo/intelligence/seo-experiments.json у неё нет. Занятость,
    посчитанная по одному реестру, отдала бы эти страницы под новую правку и
    затёрла бы чужой невыведенный эксперимент.
    """
    src = repo / "src" / "data" / "seo-experiments.ts"
    if not src.exists():
        return {}
    text = src.read_text(encoding="utf-8")
    body = text[text.index("export const SEO_EXPERIMENTS"):] if \
        "export const SEO_EXPERIMENTS" in text else text
    body = body.split("export const SEO_EXPERIMENT_LINKS")[0]
    keys = re.findall(r"^  '?([a-z0-9-]+)'?:\s*\{", body, re.M)
    return {k: "выкаченный сниппет в src/data/seo-experiments.ts (записи в реестре нет)" for k in keys}


def load_occupancy(seo_data: pathlib.Path, slugs: set[str]) -> dict[str, str]:
    """Кластер → id идущего эксперимента.

    Занятость считается по страницам эксперимента, а не по его маркерам:
    маркеры есть не у всех записей, а страницы есть у всех, и slug вендора в
    пути страницы однозначно указывает на кластер.
    """
    path = seo_data / "reports" / "seo" / "intelligence" / "seo-experiments.json"
    if not path.exists():
        return {}
    occupied: dict[str, str] = {}
    for exp in json.loads(path.read_text(encoding="utf-8"))["experiments"]:
        if exp.get("status") != "running":
            continue
        for page in exp.get("pages") or []:
            for slug in slugs:
                if f"/vendors/{slug}" == page or f"/alternatives/{slug}" == page:
                    occupied.setdefault(slug, exp["id"])
            for slug, words in ALIASES.items():
                if any(w.replace(" ", "-") in page.lower() for w in words):
                    occupied.setdefault(slug, exp["id"])
    return occupied


# ─────────────────────────── Расчёт ───────────────────────────

def build(rows: list[dict], serp: dict, occupied: dict[str, str],
          slugs: set[str], min_impressions: int,
          history: dict[str, dict[str, list]] | None = None,
          window_days: int = 12, batch: dict[str, str] | None = None) -> list[dict]:
    clusters: dict[str, dict] = defaultdict(
        lambda: {"queries": [], "impressions": 0, "clicks": 0, "lost_clicks": 0.0,
                 "weighted_position": 0.0, "intent_weight": 0.0, "pages": defaultdict(int)})

    for r in rows:
        slug = cluster_of(r["query"], slugs)
        if slug is None:
            continue
        intent, iw = intent_of(r["query"])
        if intent in ("disqualified", "navigational_own"):
            continue
        s = serp.get(r["query"], {})
        imp, pos = r["impressions"], r["position"]
        gap = max(0.0, expected_ctr(pos) - (r["clicks"] / imp if imp else 0.0))
        c = clusters[slug]
        c["queries"].append({
            "query": r["query"], "impressions": imp, "clicks": r["clicks"],
            "position": round(pos, 2) if pos else None,
            "intent": intent, "intent_weight": iw,
            "ctr": round(r["clicks"] / imp, 4) if imp else 0.0,
            "expected_ctr": round(expected_ctr(pos), 4),
            "lost_clicks": round(imp * gap, 2),
            "serp_position": s.get("serp_position"),
            "our_url": s.get("our_url"),
        })
        c["impressions"] += imp
        c["clicks"] += r["clicks"]
        c["lost_clicks"] += imp * gap
        c["weighted_position"] += (pos or 0) * imp
        c["intent_weight"] += iw * imp
        if s.get("our_url"):
            c["pages"][s["our_url"]] += imp

    out = []
    for slug, c in clusters.items():
        if c["impressions"] < min_impressions:
            continue
        pos = c["weighted_position"] / c["impressions"]
        intent_w = c["intent_weight"] / c["impressions"]
        band, band_label = band_of(pos)
        page = max(c["pages"].items(), key=lambda kv: kv[1])[0] if c["pages"] else None
        page_path = re.sub(r"^https?://[^/]+", "", page) if page else None
        kind = next((p for p in ("/product/", "/vendors/", "/blog/", "/alternatives/",
                                 "/compare/") if page_path and p in page_path), "—")
        # Интент кластера — доминирующий по показам, а не первый попавшийся.
        by_intent: dict[str, int] = defaultdict(int)
        for q in c["queries"]:
            by_intent[q["intent"]] += q["impressions"]
        top_intent = max(by_intent.items(), key=lambda kv: kv[1])[0]
        rel = relevance_of(top_intent, page_path)
        value = VALUE_TIER[CLUSTER_VALUE.get(slug, "single_seat")]
        occ = occupied.get(slug)
        hist = (history or {}).get(slug) or {"share": [], "impressions": []}
        dispersion = gini([q["impressions"] for q in c["queries"]])
        shape, shape_note = demand_shape(hist["share"], hist["impressions"], dispersion)
        batch_id = (batch or {}).get(slug)
        if batch_id:
            occ = batch_id
        risk, risk_note = risk_of(band, c["clicks"], None if batch_id else occ, kind)
        if shape == "decaying":
            risk = max(risk, 0.60)
            risk_note = f"{shape_note}"
        if shape == "burst":
            # Всплеск не переводится в переходы: правка на нём проверяет не
            # сниппет, а то, вернутся ли роботы. Кластер остаётся в бэклоге
            # видимым, но наверх не поднимается.
            risk = max(risk, 0.85)
            risk_note = f"{shape_note}; правка не даст вывода"
        score = c["lost_clicks"] * intent_w * value * rel * (1 - risk)
        out.append({
            "cluster": slug, "band": band, "band_label": band_label,
            "landing_page": page_path, "page_kind": kind,
            "impressions": c["impressions"], "clicks": c["clicks"],
            "ctr": round(c["clicks"] / c["impressions"], 4),
            "position": round(pos, 2),
            "expected_ctr": round(expected_ctr(pos), 4),
            "lost_clicks": round(c["lost_clicks"], 1),
            "intent": top_intent, "intent_weight": round(intent_w, 3),
            "value_tier": CLUSTER_VALUE.get(slug, "single_seat"), "value_weight": value,
            "relevance": rel, "risk": risk, "risk_note": risk_note,
            "occupied_by": occ, "batch_id": batch_id if (batch and slug in batch) else None,
            "demand_shape": shape, "demand_note": shape_note,
            "share_series": hist["share"], "impressions_series": hist["impressions"], "query_gini": round(dispersion, 2),
            "impressions_per_day": round(c["impressions"] / max(window_days, 1), 1),
            "exposure_gate": c["impressions"] / max(window_days, 1) >= 3.6,
            "opportunity_score": round(score, 2),
            "queries": sorted(c["queries"], key=lambda q: -q["impressions"])[:12],
            "query_count": len(c["queries"]),
        })
    out.sort(key=lambda c: -c["opportunity_score"])
    return out


# ─────────────────────────── Бэклог ───────────────────────────
#
# Бэклог — это решение по кластеру, а не его метрики: что именно мешает, что
# делать, какой программой это проверяется и когда смотреть результат. Полосы
# A–D разведены по типу проблемы, потому что лечатся они разным.

PROGRAM_A = "CTR / сниппет"        # меняется только выдачаемый текст
PROGRAM_B = "Ranking / контент"    # меняется страница и перелинковка


def diagnose(c: dict) -> dict:
    """Проблема кластера, действие и программа эксперимента."""
    band, pos, ctr = c["band"], c["position"], c["ctr"]
    if c.get("batch_id") and c["occupied_by"] == c["batch_id"]:
        return {"problem": f"позиция {pos}, CTR {ctr * 100:.2f} % — правка выкачена "
                           f"этой партией ({c['batch_id']})",
                "recommended_change": "снять метрику в контрольную дату; "
                                      "до неё страницу не трогать",
                "experiment_type": PROGRAM_A, "priority": "P0"}
    if c["occupied_by"]:
        return {"problem": f"кластер занят: {c['occupied_by']}",
                "recommended_change": "не трогать до вердикта идущего эксперимента; "
                                      "правка сейчас лишает его атрибуции",
                "experiment_type": "blocked", "priority": "hold"}
    if c["demand_shape"] == "burst":
        return {"problem": "показы не похожи на людей: " + c["demand_note"],
                "recommended_change": "дождаться второго окна выгрузки; при повторении "
                                      "формы — исключить кластер из планирования",
                "experiment_type": "observe", "priority": "hold"}
    if c["demand_shape"] == "decaying":
        return {"problem": "спрос кластера затухает: " + c["demand_note"],
                "recommended_change": "правку не заводить: она догоняет уходящий интерес",
                "experiment_type": "observe", "priority": "hold"}
    if not c["exposure_gate"]:
        return {"problem": f"экспозиция {c['impressions_per_day']} показа в день — "
                           "ниже порога 3,6, вывод не даст ни один срок наблюдения",
                "recommended_change": "копить экспозицию; включать только в сборную "
                                      "партию, где порог считается по всей партии",
                "experiment_type": "backlog", "priority": "P3"}
    if band == "A" and ctr == 0:
        return {"problem": f"позиция {pos} уже взята, переходов нет — вопрос "
                           "к тексту в выдаче, не к позиции",
                "recommended_change": "поставить точную формулировку запроса первой "
                                      "в title, description и первом вопросе FAQ",
                "experiment_type": PROGRAM_A, "priority": "P1"}
    if band in ("B", "C"):
        return {"problem": f"позиция {pos}: показы есть, переходов почти нет; "
                           "на коммерческой выдаче Яндекса это ниже первого экрана",
                "recommended_change": "сниппет под точную формулировку запроса — "
                                      "дёшево и обратимо; вывод о потолке полосы "
                                      "снимается на этой же партии",
                "experiment_type": PROGRAM_A, "priority": "P1" if band == "B" else "P2"}
    if band == "D":
        return {"problem": f"позиция {pos} — вторая страница выдачи, показы "
                           "почти не конвертируются",
                "recommended_change": "контент и перелинковка под кластер; "
                                      "сниппет на этой позиции ничего не решает",
                "experiment_type": PROGRAM_B, "priority": "P3"}
    return {"problem": f"позиция {pos} вне зоны быстрых решений",
            "recommended_change": "отдельная точка входа под кластер",
            "experiment_type": PROGRAM_B, "priority": "P4"}


def backlog(clusters: list[dict], generated: str, horizon_days: int = 28) -> list[dict]:
    check = (dt.date.fromisoformat(generated) + dt.timedelta(days=horizon_days)).isoformat()
    rows = []
    for c in clusters:
        d = diagnose(c)
        rows.append({
            "query_cluster": c["cluster"],
            "landing_page": c["landing_page"],
            "current_position": c["position"],
            "impressions": c["impressions"],
            "clicks": c["clicks"],
            "ctr": c["ctr"],
            "opportunity_score": c["opportunity_score"],
            "problem": d["problem"],
            "recommended_change": d["recommended_change"],
            "experiment_type": d["experiment_type"],
            "risk": c["risk"],
            "priority": d["priority"],
            "validation_date": check if d["priority"].startswith("P") else None,
            # Поля разбора: по ним решение перепроверяется, а не принимается на веру.
            "band": c["band"], "band_label": c["band_label"],
            "demand_shape": c["demand_shape"], "demand_note": c["demand_note"],
            "impressions_per_day": c["impressions_per_day"],
            "exposure_gate": c["exposure_gate"],
            "expected_ctr": c["expected_ctr"], "lost_clicks": c["lost_clicks"],
            "intent": c["intent"], "intent_weight": c["intent_weight"],
            "value_tier": c["value_tier"], "relevance": c["relevance"],
            "risk_note": c["risk_note"], "occupied_by": c["occupied_by"],
            "batch_id": c["batch_id"],
            "page_kind": c["page_kind"], "query_count": c["query_count"],
            "top_queries": c["queries"][:8],
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seo-data", required=True, type=pathlib.Path,
                    help="корень рабочей копии ветки seo-data")
    ap.add_argument("--repo", default=pathlib.Path("."), type=pathlib.Path)
    ap.add_argument("--date", default="2026-09-08")
    ap.add_argument("--min-impressions", type=int, default=20,
                    help="порог показов кластера за окно (12 дней)")
    ap.add_argument("--batch", default="",
                    help="слаги, правку по которым выкатила эта же сессия, в виде "
                         "«слаг=id-эксперимента» через запятую: занятость по коду "
                         "у них своя, не чужая")
    ap.add_argument("--out", type=pathlib.Path,
                    default=pathlib.Path("reports/seo/yandex-money-backlog.json"))
    args = ap.parse_args()

    slugs = load_vendor_slugs(args.repo)
    rows, window = load_queries(args.seo_data, args.date)
    serp = load_serp(args.seo_data, args.date)
    occupied = {**code_occupancy(args.repo),
                **load_occupancy(args.seo_data, slugs)}
    history = load_history(args.seo_data, args.date, slugs)
    window_days = ((dt.date.fromisoformat(window["to"])
                    - dt.date.fromisoformat(window["from"])).days + 1)
    batch = dict(pair.split("=", 1)
                 for pair in (x.strip() for x in args.batch.split(",")) if "=" in pair)
    clusters = build(rows, serp, occupied, slugs, args.min_impressions, history,
                     window_days, batch)

    totals = {
        "queries_total": len(rows),
        "impressions_total": sum(r["impressions"] for r in rows),
        "clicks_total": sum(r["clicks"] for r in rows),
        "clusters_scored": len(clusters),
        "impressions_clustered": sum(c["impressions"] for c in clusters),
        "lost_clicks_clustered": round(sum(c["lost_clicks"] for c in clusters), 1),
    }
    payload = {
        "generated": args.date, "window": {**window, "days": window_days}, "totals": totals,
        "method": {
            "formula": "opportunity = lost_clicks × intent × value × relevance × (1 − risk)",
            "ctr_curve": "отраслевая кривая позиции × коэффициент достижимости "
                         f"{ATTAINABLE} (выдача с рекламой над органикой)",
            "attainable_coefficient": ATTAINABLE,
            "note": "показы сайта — наша видимость, не рыночный спрос",
        },
        "occupied_clusters": occupied,
        "backlog": backlog(clusters, args.date),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"кластеров: {len(clusters)}; занято экспериментами: {len(occupied)}")
    print(f"записано: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
