"""Коммерческий и B2B-интент запроса — множители 0..1.

Базовый SEO-контур классифицирует интент бинарно (commercial /
informational / navigational, `scripts/seo/snapshot.py`). Для конкурентной
разведки этого мало по двум причинам:

  * нужна **градация**, а не флаг: «купить figma» и «купить figma
    юридическому лицу с НДС» — разные по ценности запросы, и Opportunity
    обязан их различать;
  * нужен **B2B-интент** отдельно от коммерческого. В базовом контуре его
    нет вовсе, а для нас это главное различение: продажа юрлицу по счёту с
    закрывающими документами — то, за что мы конкурируем.

Коммерческие маркеры взяты из базового контура (они уже проверены на живом
ядре), B2B-маркеры — свои.
"""
from __future__ import annotations

# Совместимо с COMMERCIAL_MARKERS базового контура, плюс несколько форм,
# которых там нет.
COMMERCIAL_MARKERS = (
    "купить", "оплат", "цен", "стоимост", "тариф", "подписк", "лицензи",
    "продл", "заказ", "счет", "счёт", "приобрест", "покупк", "buy", "price",
    "license", "pricing", "checkout",
)
INFO_MARKERS = ("как ", "что ", "почему ", "можно ли", "нужн", "чем ",
                "обзор", "отзыв", "сравнени", "аналог", "бесплатн", "взлом",
                "how ", "what ", "review")

# Признаки покупки юридическим лицом. Разделены по силе: одни почти
# однозначны (ЭДО, закрывающие документы), другие лишь намекают (business).
B2B_STRONG = (
    "юридическ", "юрлиц", "юр лиц", "юр. лиц", "по счёту", "по счету",
    "безнал", "ндс", "закрывающ", "эдо", "договор", "тендер", "44-фз",
    "223-фз", "для организаций", "корпоратив",
)
B2B_WEAK = (
    "для компании", "для бизнеса", "для команды", "team", "business",
    "enterprise", "корпоративн", "оптом", "для сотрудников", "рабочих мест",
)

BRAND_MARKERS = ("bizsoft", "biz-soft", "биз софт", "бизсофт")

# Сколько маркеров нужно для насыщения множителя. Два — сознательный выбор:
# один маркер уже задаёт интент, третий добавляет мало.
SATURATION = 2


def _saturating(hits: int) -> float:
    """0 → 0.0, 1 → 0.7, 2+ → 1.0. Первый маркер решает, второй подтверждает."""
    if hits <= 0:
        return 0.0
    if hits == 1:
        return 0.7
    return 1.0


def commercial_intent(query: str) -> float:
    """Насколько запрос про покупку, а не про изучение.

    Информационные маркеры не обнуляют коммерческий интент, а понижают его:
    «как купить figma для компании» — всё ещё покупательский запрос.
    """
    low = (query or "").lower()
    hits = sum(1 for m in COMMERCIAL_MARKERS if m in low)
    value = _saturating(hits)
    if any(low.startswith(m) or f" {m}" in low for m in INFO_MARKERS):
        value *= 0.6
    return round(value, 3)


def b2b_intent(query: str) -> float:
    """Насколько запрос про покупку юридическим лицом."""
    low = (query or "").lower()
    strong = sum(1 for m in B2B_STRONG if m in low)
    weak = sum(1 for m in B2B_WEAK if m in low)
    if strong:
        return round(_saturating(strong), 3)
    # Слабые маркеры сами по себе не дают полного B2B-интента: «business» в
    # запросе часто относится к названию тарифа, а не к покупателю.
    return round(0.5 * _saturating(weak), 3)


def is_branded(query: str) -> bool:
    """Бренд BIZSoft исключается из конкурентного Share (раздел 6 задания)."""
    low = (query or "").lower()
    return any(m in low for m in BRAND_MARKERS)


def describe(query: str) -> dict:
    """Разбор запроса для карточки атаки — число всегда с основанием."""
    low = (query or "").lower()
    return {
        "коммерческий": commercial_intent(query),
        "b2b": b2b_intent(query),
        "брендовый": is_branded(query),
        "маркеры_коммерческие": [m for m in COMMERCIAL_MARKERS if m in low],
        "маркеры_b2b": [m for m in (*B2B_STRONG, *B2B_WEAK) if m in low],
    }
