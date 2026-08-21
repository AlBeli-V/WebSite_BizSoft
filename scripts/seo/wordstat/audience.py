"""Кому продаётся сервис: бизнесу или частному лицу.

BIZSoft оформляет лицензии на юридические лица по договору и счёту. Сервис,
который покупают физические лица для себя, в эту услугу не превращается,
сколько бы запросов он ни собирал: Spotify с его пятнадцатью тысячами
показов — не воронка, а шум в знаменателе.

Раньше такого разделения не было, и отчёт предлагал заводить YouTube Premium
рядом с Autodesk. Это не мелкая неточность подачи: рекомендация опирается на
спрос, а спрос мерился по всей аудитории, включая ту, которой мы не продаём.

Разделение хранится списками, а не угадывается: список короткий, ошибка в нём
видна сразу и правится одной строкой, тогда как эвристика по названию
ошибается молча.
"""
from __future__ import annotations

import json
import pathlib

DECISIONS_PATH = pathlib.Path("reports/seo/wordstat/decisions.json")

#: Сервисы, которые покупают себе, а не на компанию.
CONSUMER = {
    "spotify", "youtube premium", "youtube", "netflix", "apple music",
    "apple tv", "disney+", "hbo max", "amazon prime", "tidal", "deezer",
    "duolingo", "strava", "tinder", "twitch", "patreon", "onlyfans",
    "playstation", "xbox", "steam", "epic games", "nintendo", "roblox",
    "pinterest", "tiktok", "snapchat", "telegram premium", "vk музыка",
    "яндекс плюс", "кинопоиск", "okko", "ivi",
}

#: Сервисы с потребительским лицом, но реальным корпоративным тарифом.
#: Их не исключаем — помечаем, чтобы рекомендация шла с указанием, какой
#: именно тариф имеется в виду.
DUAL = {
    "capcut": "корпоративный тариф CapCut for Business",
    "canva": "Canva для команд",
    "figma": "Figma Organization",
    "notion": "Notion for Business",
    "dropbox": "Dropbox Business",
    "zoom": "Zoom Workplace Business",
    "grammarly": "Grammarly Business",
    "miro": "Miro Business",
}


def load_decisions() -> dict:
    """Решения руководителя. Отсутствие файла — не ошибка, а пустой реестр."""
    if not DECISIONS_PATH.exists():
        return {"rejected": [], "approved": []}
    try:
        data = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"rejected": [], "approved": []}
    return {"rejected": data.get("rejected") or [],
            "approved": data.get("approved") or []}


def rejected_brands() -> dict[str, str]:
    """Бренд → причина отказа. Такие в рекомендации не возвращаются."""
    return {str(r.get("brand", "")).lower(): str(r.get("reason", ""))
            for r in load_decisions()["rejected"] if r.get("brand")}


def approved_brands() -> set[str]:
    return {str(r.get("brand", "")).lower()
            for r in load_decisions()["approved"] if r.get("brand")}


#: Шаблонные слова seed-фразы. Кластер называется «spotify купить», а решение
#: руководителя записано на бренд — без нормализации фильтр молча промахивался.
_TEMPLATE_WORDS = {
    "купить", "цена", "цены", "стоимость", "подписка", "подписку", "лицензия",
    "лицензию", "тариф", "тарифы", "оплата", "оплатить", "для", "юридических",
    "лиц", "россии", "заказать", "приобрести", "аккаунт", "ключ",
}


def brand_of(cluster: str) -> str:
    """Имя бренда из имени кластера: «spotify купить» → «spotify»."""
    words = [w for w in (cluster or "").lower().replace("-", " ").split()
             if w and w not in _TEMPLATE_WORDS]
    return " ".join(words)


def audience_of(brand: str) -> str:
    """'consumer' | 'dual' | 'business'."""
    b = brand_of(brand)
    if b in CONSUMER:
        return "consumer"
    if b in DUAL:
        return "dual"
    return "business"


def business_note(brand: str) -> str | None:
    """Какой именно тариф имеется в виду у сервиса с двойным лицом."""
    return DUAL.get(brand_of(brand))


def skip_reason(brand: str) -> str | None:
    """Почему кандидат не попадает в рекомендации. None — попадает.

    Порядок важен: решение руководителя перекрывает любую классификацию,
    в том числе если он одобрил сервис, который список считает
    потребительским.
    """
    b = brand_of(brand)
    if b in approved_brands():
        return None
    rejected = rejected_brands()
    if b in rejected:
        return f"отклонён руководителем: {rejected[b]}" if rejected[b] else "отклонён руководителем"
    if audience_of(b) == "consumer":
        return "потребительский сервис: юрлицам не поставляем"
    return None
