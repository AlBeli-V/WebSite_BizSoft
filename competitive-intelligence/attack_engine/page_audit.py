"""Что на нашей странице есть на самом деле — а не что должно быть по её типу.

Зачем модуль появился (правка 1.4.0). До него рекомендация выбиралась по типу
страницы: блог → «добавить коммерческий блок», карточка → «довести условия
для юрлиц». Руководитель проверил первое же поручение и увидел, что оно
неверно: в статье про Depositphotos уже стояли ссылки на три карточки товара,
на страницу вендора, на документы и FAQ из шести вопросов. Система советовала
сделать сделанное, потому что в саму страницу не заглядывала.

Теперь заглядывает. Источник — репозиторий, то есть ровно то, что редактор
правит руками:

  * статья блога   — src/content/blog/<slug>.md: заголовки, текст, FAQ, ссылки;
  * вендор         — src/data/vendors.ts (tagline и about) плюс bespoke-страница
                     src/pages/vendors/<slug>.astro, если она есть;
  * карточка товара — data/seo/product-descriptions.json: описание и мета.

**Границы проверки названы явно.** Тело вендорской страницы и карточки товара
формируется из Directus, и в репозитории его нет. Поэтому по таким страницам
модуль честно сообщает, что проверил только редакторскую обвязку: рекомендация
получает пометку, а не притворяется полной. Утверждать «фразы нет на странице»,
не видя страницы целиком, нельзя — можно лишь утверждать «фразы нет в тексте,
который мы контролируем в репозитории».
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402

REPO = paths.REPO_ROOT
BLOG_DIR = os.path.join(REPO, "src", "content", "blog")
VENDORS_TS = os.path.join(REPO, "src", "data", "vendors.ts")
VENDOR_PAGES = os.path.join(REPO, "src", "pages", "vendors")
PRODUCT_META = os.path.join(REPO, "data", "seo", "product-descriptions.json")
# Шаблоны, из которых собирается видимая часть страницы. Значительная доля
# текста живёт именно здесь, а не в данных: заголовки «Как купить … через
# BIZSoft», «Тарифы и продукты …», блоки про оплату в рублях и закрывающие
# документы. Без них проверка врала в опасную сторону — советовала дописать
# слова, которые на странице уже стоят в H1 и H2.
VENDOR_TEMPLATE = os.path.join(REPO, "src", "components", "VendorLanding.astro")
PRODUCT_TEMPLATE = os.path.join(REPO, "src", "pages", "product", "[slug].astro")

# Слова, которые не несут темы и не должны требовать присутствия в тексте:
# по ним нельзя судить, раскрыт запрос или нет.
STOPWORDS = {
    "как", "где", "что", "чем", "для", "или", "это", "так", "уже", "ещё",
    "если", "при", "над", "под", "без", "про", "мне", "нам", "вам", "быть",
    "можно", "нужно", "сейчас", "лучше", "самый", "самому",
}
MIN_WORD = 3


@dataclass
class PageContent:
    """Содержимое страницы в том виде, в каком его правит редактор."""
    url: str
    kind: str
    available: bool
    source_path: str = ""
    edit_hint: str = ""      # где именно править
    title: str = ""
    headings: list[str] = field(default_factory=list)
    faq_questions: list[str] = field(default_factory=list)
    body: str = ""
    internal_links: list[str] = field(default_factory=list)
    scope_note: str = ""     # что именно проверено, а что нет

    @property
    def haystack(self) -> str:
        parts = [self.title, " ".join(self.headings),
                 " ".join(self.faq_questions), self.body]
        return normalize(" ".join(parts))

    @property
    def prominent(self) -> str:
        """Заголовки, title и вопросы FAQ — то, что видно поисковику сразу."""
        return normalize(" ".join([self.title, " ".join(self.headings),
                                   " ".join(self.faq_questions)]))


def normalize(text: str) -> str:
    """Сравнимая форма: нижний регистр, без пунктуации, одиночные пробелы."""
    lowered = (text or "").lower().replace("ё", "е")
    cleaned = re.sub(r"[^0-9a-zа-я]+", " ", lowered)
    return " ".join(cleaned.split())


def stem(word: str) -> str:
    """Грубая основа слова: отсечение двух последних букв у длинных слов.

    Полноценной морфологии в контуре нет и заводить её ради проверки вхождений
    незачем. Задача другая: «оплата» и «оплаты» — одно и то же для читателя и
    для поиска, и считать их разными словами значит советовать дописать то,
    что на странице уже есть. Короткие слова не режутся: у них отсечение
    сливает разные корни.
    """
    word = word or ""
    return word if len(word) <= 4 else word[:max(4, len(word) - 2)]


def significant_words(query: str) -> list[str]:
    """Слова запроса, по которым судим о раскрытии темы."""
    return [w for w in normalize(query).split()
            if len(w) >= MIN_WORD and w not in STOPWORDS]


def slug_of(url: str) -> str:
    return (url or "").rstrip("/").rsplit("/", 1)[-1]


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def template_content(path: str) -> tuple[list[str], str]:
    """Видимый текст шаблона: заголовки и всё остальное без разметки.

    Выражения вида {entry.about} вырезаются: их содержимое приходит из данных
    и проверяется отдельно. Остаётся то, что видит любой посетитель страницы
    независимо от вендора или товара.
    """
    raw = _read(path)
    if not raw:
        return [], ""
    # Служебная часть .astro-файла тоже содержит видимый текст: вопросы FAQ,
    # подписи, готовые формулировки. Отбрасывать её целиком значит не видеть
    # половину страницы — на этом проверка один раз уже ошиблась, потребовав
    # дописать слово, стоявшее в вопросе FAQ. Берём из неё строковые литералы
    # с кириллицей длиной от двадцати символов: короткие строки — это ключи и
    # имена полей, длинные — текст для читателя.
    head = re.match(r"^---(.*?)---", raw, flags=re.S)
    visible_strings = []
    if head:
        for quoted in re.findall(r"'([^']{20,})'|\"([^\"]{20,})\"|`([^`]{20,})`",
                                 head.group(1), flags=re.S):
            text = next((t for t in quoted if t), "")
            if re.search(r"[а-яА-ЯёЁ]", text):
                visible_strings.append(text)
    body = re.sub(r"^---.*?---", " ", raw, count=1, flags=re.S)   # frontmatter
    body = re.sub(r"<style[^>]*>.*?</style>", " ", body, flags=re.S)
    body = re.sub(r"<script[^>]*>.*?</script>", " ", body, flags=re.S)
    headings = [re.sub(r"[{][^}]*[}]", " ", h)
                for h in re.findall(r"<h[123][^>]*>(.*?)</h[123]>", body, re.S)]
    headings = [re.sub(r"<[^>]+>", " ", h).strip() for h in headings]
    text = re.sub(r"[{][^}]*[}]", " ", body)
    text = re.sub(r"<[^>]+>", " ", text)
    return [h for h in headings if h], text + " " + " ".join(visible_strings)


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    return (parts[1], parts[2]) if len(parts) >= 3 else ("", text)


def load_blog(url: str) -> PageContent:
    slug = slug_of(url)
    path = os.path.join(BLOG_DIR, f"{slug}.md")
    raw = _read(path)
    page = PageContent(url=url, kind="blog", available=bool(raw),
                       source_path=os.path.relpath(path, REPO) if raw else "",
                       edit_hint=f"src/content/blog/{slug}.md")
    if not raw:
        page.scope_note = ("файл статьи не найден в репозитории — содержимое "
                           "не проверялось")
        return page
    front, body = _split_frontmatter(raw)
    title = re.search(r'^title:\s*"?([^"\n]+)"?', front, re.M)
    page.title = title.group(1).strip() if title else ""
    page.headings = re.findall(r"^#{2,3}\s+(.+)$", body, re.M)
    page.faq_questions = [q.strip().strip('"')
                          for q in re.findall(r'^\s*-?\s*q:\s*"?([^"\n]+)"?',
                                              front, re.M)]
    summary = re.search(r'^summaryAnswer:\s*"?([^"\n]+)"?', front, re.M)
    description = re.search(r'^description:\s*"?([^"\n]+)"?', front, re.M)
    page.body = " ".join(filter(None, [
        body, front,
        summary.group(1) if summary else "",
        description.group(1) if description else ""]))
    page.internal_links = sorted(set(re.findall(r"\]\((/[^)\s]*)\)", raw)))
    page.scope_note = "проверен полный текст статьи: заголовки, тело, FAQ, ссылки"
    return page


def load_vendor(url: str) -> PageContent:
    slug = slug_of(url)
    source = _read(VENDORS_TS)
    page = PageContent(url=url, kind="vendor", available=False,
                       edit_hint=f"src/data/vendors.ts, запись slug: '{slug}'")
    entry = re.search(r"\{\s*slug:\s*'" + re.escape(slug) + r"'.*?\}\s*,\s*\n",
                      source, re.S)
    if entry:
        block = entry.group(0)
        page.available = True
        page.source_path = "src/data/vendors.ts"
        for field_name in ("title", "vendor"):
            found = re.search(field_name + r":\s*'([^']+)'", block)
            if found:
                page.title = found.group(1)
                break
        texts = []
        for field_name in ("tagline", "about"):
            found = re.search(field_name + r":\s*'((?:[^'\\]|\\.)*)'", block)
            if found:
                texts.append(found.group(1))
        page.body = " ".join(texts)

    bespoke = os.path.join(VENDOR_PAGES, f"{slug}.astro")
    raw = _read(bespoke)
    if raw:
        page.available = True
        page.source_path = f"src/pages/vendors/{slug}.astro"
        page.edit_hint = page.source_path
        page.headings += re.findall(r"<h[23][^>]*>(.*?)</h[23]>", raw, re.S)
        page.faq_questions += re.findall(r"q:\s*'([^']+)'", raw)
        page.body += " " + re.sub(r"<[^>]+>", " ", raw)
        page.internal_links = sorted(set(re.findall(r'href="(/[^"]*)"', raw)))
        page.scope_note = ("проверена bespoke-страница вендора целиком; "
                           "карточки товаров подтягиваются из Directus")
    elif page.available:
        # Типовой лендинг: к редакторским полям добавляется текст шаблона —
        # заголовки и блоки, которые видит посетитель на каждой такой странице.
        tpl_headings, tpl_text = template_content(VENDOR_TEMPLATE)
        page.headings += tpl_headings
        page.body += " " + tpl_text
        page.scope_note = ("проверены редакторские tagline и about из "
                           "src/data/vendors.ts плюс текст типового лендинга "
                           "(заголовки и блоки шаблона); карточки товаров "
                           "приходят из Directus и в проверку не входят")
    else:
        page.scope_note = "запись вендора не найдена — содержимое не проверялось"
    return page


def load_product(url: str) -> PageContent:
    slug = slug_of(url)
    page = PageContent(url=url, kind="product", available=False,
                       edit_hint=(f"data/seo/product-descriptions.json, ключ "
                                  f"«{slug}» + workflow ops-apply-descriptions"))
    # Текст шаблона карточки виден на каждой странице товара независимо от
    # того, заведено ли для него описание в репозитории.
    tpl_headings, tpl_text = template_content(PRODUCT_TEMPLATE)
    page.headings = tpl_headings
    # Название товара в репозитории не хранится; slug даёт его приближение и
    # закрывает запросы, где бренд написан так же, как в адресе.
    page.body = " ".join([tpl_text, slug.replace("-", " ")])
    page.available = bool(tpl_text)
    page.source_path = "src/pages/product/[slug].astro"
    page.scope_note = ("проверён текст шаблона карточки и slug товара; "
                       "название, описание и характеристики приходят из "
                       "Directus и в проверку не входят")

    raw = _read(PRODUCT_META)
    if not raw:
        return page
    try:
        data = json.loads(raw).get("products") or {}
    except json.JSONDecodeError:
        return page
    entry = data.get(slug)
    if not entry:
        return page
    page.title = entry.get("meta_title") or entry.get("title") or ""
    page.body += " " + " ".join(filter(None, [entry.get("description"),
                                              entry.get("meta_description"),
                                              page.title]))
    page.source_path = "data/seo/product-descriptions.json"
    page.scope_note = ("проверены текст шаблона карточки, описание и мета из "
                       "data/seo/product-descriptions.json; остальное тело "
                       "карточки приходит из Directus")
    return page


def load(url: str, kind: str) -> PageContent:
    """Содержимое страницы по её типу. Неизвестный тип — пустая проверка."""
    if kind == "blog":
        return load_blog(url)
    if kind == "vendor":
        return load_vendor(url)
    if kind == "product":
        return load_product(url)
    return PageContent(url=url, kind=kind, available=False,
                       scope_note="тип страницы не поддержан проверкой")


# Степени раскрытия запроса на странице.
COVER_PROMINENT = "в заголовке"   # есть в title, H2/H3 или вопросе FAQ
COVER_BODY = "в тексте"           # есть в теле, но не вынесен в заголовки
COVER_NONE = "нет"                # значимых слов запроса на странице нет


def coverage(page: PageContent, query: str) -> tuple[str, list[str]]:
    """Раскрыт ли запрос на странице и каких слов не хватает.

    Возвращает степень раскрытия и список отсутствующих значимых слов —
    именно они превращаются в конкретное «что дописать».
    """
    words = significant_words(query)
    if not words or not page.available:
        return COVER_NONE, words
    missing = [w for w in words if stem(w) not in page.haystack]
    if missing:
        return COVER_NONE, missing
    if all(stem(w) in page.prominent for w in words):
        return COVER_PROMINENT, []
    return COVER_BODY, []


def audit(page: PageContent, queries: list[str]) -> dict:
    """Разбор пакета запросов по степени раскрытия."""
    result = {COVER_PROMINENT: [], COVER_BODY: [], COVER_NONE: []}
    missing_words: dict[str, list[str]] = {}
    for query in queries:
        state, missing = coverage(page, query)
        result[state].append(query)
        if state == COVER_NONE and missing:
            missing_words[query] = missing
    return {"по_степени": result, "нет_слов": missing_words}
