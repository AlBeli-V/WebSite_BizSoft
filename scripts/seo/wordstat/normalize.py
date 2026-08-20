#!/usr/bin/env python3
"""Нормализация, дедупликация, кластеризация и классификация интента.

Количество ключевых фраз бизнес-метрикой не является: 6 500 фраз, половина
которых — падежные варианты одной, не лучше 3 000 различимых. Поэтому фразы
приводятся к нормальной форме, склеиваются по смыслу и группируются в кластеры,
а считается спрос по частотности, а не по числу строк.

Морфология без внешних словарей: усечение известных русских окончаний. Это грубее
полноценного стеммера, но детерминированно, не требует зависимостей и покрывает
основной случай — падежные и числовые формы коммерческих фраз.
"""

from __future__ import annotations

import re
import unicodedata

# Окончания в порядке убывания длины: срезаем самое длинное подходящее.
ENDINGS = (
    "ами", "ями", "ого", "его", "ому", "ему", "ыми", "ими", "ой", "ей", "ов", "ев",
    "ам", "ям", "ах", "ях", "ую", "юю", "ые", "ие", "ый", "ий", "ая", "яя", "ое", "ее",
    "ом", "ем", "ах", "ии", "ей", "ью", "ю", "я", "ы", "и", "е", "а", "у", "о", "ь",
)
MIN_STEM = 4

STOPWORDS = {"в", "на", "для", "и", "с", "по", "от", "до", "за", "к", "у", "о", "об",
             "как", "что", "это", "the", "a", "of", "for", "to"}

COMMERCIAL = {
    "купить": 1.0, "покупк": 0.9, "оплат": 1.0, "заказ": 0.9, "цена": 0.9, "цен": 0.85,
    "стоимост": 0.85, "тариф": 0.8, "прайс": 0.85, "подписк": 0.7, "лицензи": 0.8,
    "продлить": 0.9, "продлен": 0.85, "счет": 0.9, "счёт": 0.9, "юрлиц": 1.0,
    "юридическ": 1.0, "безнал": 1.0, "договор": 0.85, "买": 0.0,
    "buy": 0.9, "price": 0.85, "pricing": 0.8, "license": 0.8, "subscription": 0.7,
}
INFORMATIONAL = {
    "как": 0.8, "что": 0.8, "почему": 0.8, "зачем": 0.8, "можно ли": 0.9, "чем": 0.6,
    "инструкц": 0.9, "обзор": 0.8, "сравнен": 0.7, "отзыв": 0.7, "бесплатн": 0.9,
    "скачать": 0.9, "торрент": 1.0, "кряк": 1.0, "взлом": 1.0, "crack": 1.0,
    "аналог": 0.6, "альтернатив": 0.6, "what": 0.8, "how": 0.8, "free": 0.9,
    "download": 0.9, "review": 0.7,
}
BRAND = ("bizsoft", "биз софт", "бизсофт", "biz-soft", "биз-софт")

# Проблемно-ориентированные формулировки: человек описывает ситуацию, а не товар.
PROBLEM = ("не работает", "заблокирова", "не принимает", "отказ", "санкц",
           "из россии", "в россии", "перестал", "не проходит", "не оплачива")


def normalize(phrase: str) -> str:
    """Регистр, пробелы, «ё», знаки — к одному виду."""
    s = unicodedata.normalize("NFKC", phrase).lower().replace("ё", "е")
    s = re.sub(r"[^\w\s+-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def stem(word: str) -> str:
    if len(word) <= MIN_STEM or not re.search(r"[а-я]", word):
        return word
    for end in ENDINGS:
        if word.endswith(end) and len(word) - len(end) >= MIN_STEM:
            return word[: -len(end)]
    return word


def morph_key(phrase: str) -> str:
    """Ключ смысловой одинаковости: стемминг, отбрасывание стоп-слов, сортировка.

    «купить корел» и «корела купить» дают один ключ — это одна потребность,
    а не две, и платить за неё дважды не нужно.
    """
    words = [w for w in normalize(phrase).split() if w not in STOPWORDS]
    return " ".join(sorted(stem(w) for w in words))


def intent_scores(phrase: str) -> tuple[float, float]:
    """Коммерческий и информационный интент как две независимые величины."""
    low = normalize(phrase)
    commercial = max((v for k, v in COMMERCIAL.items() if k in low), default=0.0)
    informational = max((v for k, v in INFORMATIONAL.items() if k in low), default=0.0)
    if any(p in low for p in PROBLEM):
        commercial = max(commercial, 0.6)
    return round(commercial, 3), round(informational, 3)


def classify_intent(phrase: str) -> str:
    if is_branded(phrase):
        return "navigational"
    c, i = intent_scores(phrase)
    if c >= 0.7 and c > i:
        return "commercial"
    if i >= 0.7 and i > c:
        return "informational"
    if c > 0 and c >= i:
        return "commercial"
    if i > 0:
        return "informational"
    return "unknown"


def is_branded(phrase: str) -> bool:
    low = normalize(phrase)
    return any(b in low for b in BRAND)


def phrase_type(phrase: str) -> str:
    """vendor / product / problem / generic — по форме запроса, не по интенту."""
    low = normalize(phrase)
    if any(p in low for p in PROBLEM):
        return "problem"
    if re.search(r"\b(pro|business|enterprise|team|studio|premium|plus|max)\b", low):
        return "product"
    return "generic"


def dedupe(rows: list[dict], key: str = "phrase") -> list[dict]:
    """Схлопывание морфологических вариантов: остаётся самый частотный."""
    best: dict[str, dict] = {}
    for r in rows:
        k = morph_key(r[key])
        prev = best.get(k)
        if prev is None or (r.get("frequency") or 0) > (prev.get("frequency") or 0):
            if prev is not None:
                r = dict(r)
                r["variants"] = prev.get("variants", 0) + 1
            best[k] = r
        else:
            prev["variants"] = prev.get("variants", 0) + 1
    return sorted(best.values(), key=lambda r: -(r.get("frequency") or 0))


# Чужой интент: BIZSoft продаёт лицензии на ПО юридическим лицам. Запросы про
# платёжные карты, кэшбэк и переводы для физлиц имеют большую частотность, но
# к услуге отношения не имеют — на замере 20.08.2026 кластер «оплата зарубежных
# сервисов» на 4 из 5 верхних фраз состоял именно из них.
OUT_OF_SCOPE = (
    "карта", "карту", "картой", "карты", "кэшбэк", "кешбэк", "физическ", "физлиц",
    "перевод денег", "банк", "сим-карт", "виртуальн карт", "мтс", "озон банк",
    "тинькофф", "сбербанк", "юmoney", "юмани", "криптовалют", "стим", "steam",
)


# Бренды, чьё имя — обычное английское слово. Вордстат по ним отдаёт запросы про
# совсем другие товары: «box купить» — это TV-боксы Xiaomi и Honda N-Box, «zoom
# купить» — кроссовки Nike Zoom и отбеливание зубов. На замере 20.08.2026 такой
# мусор дал 104 291 и 30 599 показов «спроса» и вывел «box» в первую строку
# приоритетов. Для этих брендов недостаточно, что фраза содержит имя: нужен
# признак софта или подписки, иначе фраза не засчитывается.
AMBIGUOUS_BRANDS = {
    "box", "linear", "cursor", "zoom", "framer", "notion", "arc", "bolt",
    "craft", "loom", "origin", "pitch", "frame", "gamma", "runway", "flux",
    "luma", "canvas", "sketch", "unity", "spark", "wave", "vector",
    # Вендоры каталога с именем-обычным словом: «rive» — парфюм La Rive,
    # «avid» — английское слово, «spine» — обувь, «foundry» и «photon» — общие
    # технические термины. Замер 20.08.2026 показал их спрос завышенным.
    "rive", "avid", "spine", "foundry", "photon",
}

# Признаки того, что запрос всё-таки про программу или подписку.
SOFTWARE_MARKERS = (
    "подписк", "лицензи", "тариф", "аккаунт", "план", "ключ", "активаци",
    "продлen", "продлени", "pro", "premium", "plus", "business", "enterprise",
    "team", "cloud", "облак", "ai", "api", "app", "софт", "программ",
    "для юридических", "юрлиц", "юр лиц", "корпоратив", "организаци",
)


# Служебные слова шаблонов seed-фраз: их отбрасывают, чтобы найти имя бренда.
SEED_TEMPLATE_WORDS = {
    "купить", "цена", "цены", "стоимость", "подписка", "подписку", "лицензия",
    "лицензию", "тариф", "тарифы", "оплата", "оплатить", "для", "юридических",
    "лиц", "россии", "заказать", "приобрести",
}


def relevant_to_seed(phrase: str, seed: str | None) -> bool:
    """Относится ли фраза к тому вендору, ради которого делался запрос.

    Правило применяется только к брендам-омонимам. Для остальных имя бренда
    в запросе — достаточная привязка.
    """
    if not seed:
        return True
    # Seed бывает и голым именем бренда, и шаблоном «{бренд} купить»,
    # «лицензия {бренд}», «{бренд} подписка». Отбрасываем служебные слова
    # шаблона и смотрим, что осталось.
    words = [w for w in _phrase_words(seed) if w not in SEED_TEMPLATE_WORDS]
    brand = " ".join(words)
    if brand not in AMBIGUOUS_BRANDS:
        return True
    low = normalize(phrase)
    return any(m in low for m in SOFTWARE_MARKERS)


# Физические товары и игры: у брендов ПО есть тёзки в обуви, парфюмерии и
# мототехнике. Такие запросы к продаже лицензий отношения не имеют независимо
# от того, чьё имя в них стоит: «spine кроссовки», «la rive» (парфюм),
# «assassins creed unity» (игра), «road glide» (мотоцикл).
PHYSICAL_GOODS = (
    "кроссовк", "ботинк", "обув", "кед", "сандал", "парфюм", "туалетн вод",
    "духи", "одеколон", "крем", "шампун", "сумк", "рюкзак", "часы", "велосипед",
    "мотоцикл", "харлей", "harley", "davidson", "шин", "диск колес", "автомобил",
    "телевизор", "приставк", "смартфон", "наушник", "холодильник", "пылесос",
    "assassins creed", "игру", "игра для", "диск с игрой", "футболк", "куртк",
    "тревел", "тур в", "путёвк", "путевк", "водк", "пион", "цвет",
)


def in_scope(phrase: str) -> bool:
    """Относится ли запрос к продаже лицензий на ПО юридическим лицам."""
    low = normalize(phrase)
    if "карт" in low and any(k in low for k in ("оплат", "виртуальн", "выпуст", "банк")):
        return False
    if any(k in low for k in PHYSICAL_GOODS):
        return False
    return not any(k in low for k in OUT_OF_SCOPE)


def _phrase_words(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9\u0430-\u044f]+", normalize(text)) if w]


def _has_run(words: list[str], run: list[str]) -> bool:
    n = len(run)
    return n > 0 and any(words[i:i + n] == run for i in range(len(words) - n + 1))


def cluster_of(phrase: str, vendors: dict[str, str], seed: str | None = None) -> str | None:
    """Кластер по якорю вендора; иначе — по seed-фразе, а не по обрубку слова.

    Якорь сравнивается по целым словам. Подстрока врёт: «avid» сидит внутри
    «davidson» и приписывала Harley-Davidson к Avid, «rive» внутри «la rive»
    приводила парфюмерию в кластер Rive. Обрубок («зарубежных», «виртуальн»)
    именем кластера быть не может: по нему нельзя понять ни тему, ни страницу.
    """
    words = _phrase_words(phrase)
    for token, cluster in vendors.items():
        if _has_run(words, _phrase_words(token)):
            return cluster
    low = normalize(phrase)
    if seed:
        return normalize(seed)
    words = [w for w in low.split() if w not in STOPWORDS and len(w) > 4]
    return " ".join(words[:3]) if words else None


def subcluster_of(phrase: str) -> str:
    """Подкластер по типу потребности — он определяет, какая страница нужна."""
    low = normalize(phrase)
    if any(k in low for k in ("юрлиц", "юридическ", "счет", "счёт", "безнал", "договор")):
        return "покупка на юрлицо"
    if any(k in low for k in ("оплат", "оплатить", "платеж")):
        return "оплата"
    if any(k in low for k in ("тариф", "цена", "цен", "стоимост", "прайс")):
        return "цены и тарифы"
    if any(k in low for k in ("купить", "покупк", "заказ", "приобрест")):
        return "покупка"
    if any(k in low for k in ("подписк", "продлить", "продлен")):
        return "подписка и продление"
    if any(k in low for k in ("лицензи",)):
        return "лицензирование"
    if any(k in low for k in ("бесплатн", "скачать", "торрент", "кряк", "crack")):
        return "бесплатно и пиратское"
    return "прочее"
