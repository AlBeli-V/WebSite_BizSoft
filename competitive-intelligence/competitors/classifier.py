"""Категоризация доменов из выдачи и B2B Confidence Score.

Два разных вопроса, которые нельзя смешивать:

  * **категория** (A–H, раздел 4 задания) — что это за сайт по типу бизнеса;
  * **B2B Confidence 0–100** (раздел 5) — насколько он умеет продавать
    юридическим лицам: счёт, договор, НДС, ЭДО, корпоративные лицензии.

Категория ставится по известным доменам и по признакам URL, Confidence — по
сигналам на страницах конкурента. Score обязан быть объяснимым: карточка
хранит сработавшие сигналы и evidence-URL, иначе доверять числу нельзя.

Seed-списки намеренно небольшие: discovery обязан находить новых игроков сам.
Урок среза 30.08 — унаследованный от базового контура список профильных
реселлеров (softline, allsoft, softkey) не встретился в топ-10 ни разу, а
реальное поле заняли платёжные посредники, которых в списке не было вовсе.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

VENDORS_TS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src", "data", "vendors.ts")

# --- seed-списки: только опорные точки, не исчерпывающий справочник --------

B2B_RESELLERS = {
    "syssoft.ru", "migsoft.ru", "legasoft.ru", "softline.ru", "store.softline.ru",
    "allsoft.ru", "softmagazin.ru", "softkey.ru", "1csoft.ru", "digitalsoft.ru",
    "softorg.ru", "itshop.ru", "windows-office.ru", "platipomiru.com",
}
PAYMENT_INTERMEDIARIES = {
    "raketapay.ru", "pipl.io", "finteka.io", "kartli.io", "aifory.pro",
    "card-open.ru", "remoney.ru", "dolphinpay.ru", "global-payments.ru",
    "yello-card.com", "payholder.ru", "payment.mts.ru", "oplata.guru",
}
B2C_MARKETPLACES = {
    "ggsel.net", "plati.market", "kupikod.com", "funpay.com", "avito.ru",
    "wildberries.ru", "ozon.ru", "market.yandex.ru", "megamarket.ru",
    "aliexpress.ru", "webduck.by",
}
INFORMATIONAL = {
    "dzen.ru", "vc.ru", "habr.com", "pikabu.ru", "klerk.ru", "companies.rbc.ru",
    "otzovik.com", "irecommend.ru", "youtube.com", "rutube.ru", "wikipedia.org",
    "ya.ru", "dtf.ru", "journal.tinkoff.ru",
}
# Официальные сайты вендоров: список открытый, поэтому дополняется правилом ниже
OFFICIAL_HINTS = {
    "figma.com", "adobe.com", "autodesk.com", "jetbrains.com", "canva.com",
    "openai.com", "anthropic.com", "github.com", "zoom.us", "microsoft.com",
    "google.com", "perplexity.ai", "unity.com", "docker.com",
}
OURS = "biz-soft.pro"

# Названия попадают в письмо и отчёт, которые читает руководитель, поэтому
# они на русском; латинские буквы категорий остаются как устойчивые коды.
CATEGORY_NAMES = {
    "A": "прямые B2B-реселлеры",
    "B": "малые B2B-реселлеры",
    "C": "крупные интеграторы",
    "D": "профильные реселлеры",
    "E": "B2C и маркетплейсы",
    "F": "официальные сайты вендоров",
    "G": "информационные площадки",
    "H": "платёжные посредники",
    "?": "не классифицировано",
}
# В основной конкурентный рейтинг не входят: B2C, информационные и официальные
# сайты вендоров — они конкурируют за клик, но не за нашу сделку.
MAIN_RANKING_CATEGORIES = {"A", "B", "C", "D", "H"}

# --- сигналы B2B: подстроки в тексте страницы -----------------------------

B2B_SIGNALS: dict[str, tuple[str, ...]] = {
    "оплата_по_счёту": ("оплата по счёту", "оплата по счету", "выставим счёт",
                        "выставим счет", "счёт на оплату", "счет на оплату"),
    "договор": ("договор", "по договору"),
    "закрывающие_документы": ("закрывающие документы", "акт выполненных",
                              "универсальный передаточный", "упд"),
    "ндс": ("ндс", "с ндс", "без ндс"),
    "эдо": ("эдо", "диадок", "электронный документооборот", "сбис"),
    "реквизиты_инн_огрн": ("инн", "огрн", "огрнип", "кпп"),
    "запрос_кп": ("коммерческое предложение", "запросить кп", "получить кп"),
    "корпоративное_лицензирование": ("корпоративная лицензия",
                                     "корпоративные лицензии", "лицензирование",
                                     "лицензия на компанию"),
    "тарифы_team_business_enterprise": ("team", "business", "enterprise"),
    # Падежи важнее предлога: «работаем с юридическими лицами» и «счёт для
    # юридических лиц» — один и тот же сигнал, и привязка к «для» его теряла.
    "для_юридических_лиц": ("юридическ", "юрлиц", "юр. лиц", "юр лиц",
                            "для организаций", "для компаний", "для бизнеса"),
    "безналичный_расчёт": ("безналичн", "по безналу", "б/н"),
    "персональный_менеджер": ("персональный менеджер", "личный менеджер"),
    "тендеры_закупки": ("тендер", "закупк", "44-фз", "223-фз"),
}


@dataclass
class B2BVerdict:
    """Объяснимый результат классификации: число плюс его основания."""
    confidence: int
    signals: list[str] = field(default_factory=list)
    evidence_urls: list[str] = field(default_factory=list)

    @property
    def in_main_pool(self) -> bool:
        return self.confidence >= 60


def vendor_domains(path: str = VENDORS_TS) -> set[str]:
    """Домены официальных сайтов вендоров из src/data/vendors.ts.

    Реестр вендоров — единственный источник правды по нашему ассортименту,
    поэтому официальные сайты берутся оттуда, а не поддерживаются вторым
    списком: добавили вендора на сайт — его домен сразу узнаётся в выдаче.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        return set()
    found = set()
    for raw in re.findall(r"site:\s*'([^']+)'", content):
        host = re.sub(r"^https?://", "", raw).split("/")[0].lower()
        found.add(host.removeprefix("www."))
    return found


# Слабые признаки платёжного посредника в самом имени домена. Применяются
# последними и только когда домен не опознан списками: эвристика по имени
# ошибается, поэтому такие домены помечаются как требующие подтверждения.
PAYMENT_NAME_HINTS = ("pay", "oplata", "platezh", "card", "money", "finteka")


def categorize(domain: str, *, sample_urls: list[str] | None = None,
               vendor_hosts: set[str] | None = None) -> str:
    """Категория домена A–H. '?' — если правил не хватило: это не ошибка,
    а очередь на ручную проверку, и такой домен не попадает в рейтинг молча."""
    d = (domain or "").strip().lower().removeprefix("www.")
    if not d:
        return "?"
    if d == OURS:
        return "A"
    if d in PAYMENT_INTERMEDIARIES:
        return "H"
    if d in B2B_RESELLERS:
        return "A"
    if d in B2C_MARKETPLACES:
        return "E"
    if d in INFORMATIONAL:
        return "G"
    if d in OFFICIAL_HINTS or d in (vendor_hosts or set()):
        return "F"
    # Признаки в URL — слабее списков, поэтому проверяются после них
    for url in (sample_urls or []):
        if re.search(r"/(blog|news|article|post)/", url.lower()):
            return "G"
    # Самый слабый признак: имя домена. Ставит категорию, но такой домен
    # обязан пройти подтверждение B2B-классификатором на страницах.
    name = d.split(".")[0]
    if any(hint in name for hint in PAYMENT_NAME_HINTS):
        return "H"
    return "?"


def b2b_confidence(page_text: str, config: dict, *,
                   evidence_urls: list[str] | None = None) -> B2BVerdict:
    """B2B Confidence Score 0–100 по тексту страниц конкурента.

    Версия 1.1.0: сигналы нормируются по четырём группам с лимитом 25 баллов
    каждая. В 1.0.0 веса просто складывались (в сумме 128 с обрезкой до 100),
    и близкие признаки — счёт, безнал, реквизиты — быстро давали максимум:
    страница с несколькими похожими формулировками выглядела готовой к B2B
    сильнее, чем есть. Группировка отражает, что готовность к оплате,
    документальная готовность, лицензирование и процесс продажи — разные
    измерения, и сильная одна не заменяет остальные.
    """
    section = config["b2b_классификатор"]
    weights = section["сигналы"]
    groups = section.get("группы") or {}
    text = (page_text or "").lower()
    hit = [name for name, needles in B2B_SIGNALS.items()
           if any(n in text for n in needles) and name in weights]

    if not groups:
        # Совместимость со старой конфигурацией без групп.
        return B2BVerdict(confidence=min(100, sum(weights[n] for n in hit)),
                          signals=sorted(hit),
                          evidence_urls=list(evidence_urls or []))

    score = 0
    for group in groups.values():
        inside = [n for n in hit if n in group["сигналы"]]
        score += min(group["лимит"], sum(weights[n] for n in inside))
    return B2BVerdict(confidence=min(100, score), signals=sorted(hit),
                      evidence_urls=list(evidence_urls or []))


def in_main_ranking(category: str) -> bool:
    """Входит ли категория в основной конкурентный рейтинг.

    B2C, информационные и официальные сайты остаются в данных и в отчёте
    (они забирают клик), но не могут стать «главным конкурентом» — требование
    теста на ложные срабатывания из раздела 32 задания.
    """
    return category in MAIN_RANKING_CATEGORIES
