"""Управленческие воздействия: что сделать, где, почему и как принять.

Правка 1.4.0 по замечанию руководителя. До неё пакет работ формулировал
направление («добавить коммерческий блок», «довести условия для юрлиц»), и
проверка первого же поручения показала, что оно неверно: в статье уже стояли
ссылки на карточки товаров, страницу вендора, документы и FAQ. Направление
выбиралось по типу страницы, а не по её содержимому, и поручить его было
нельзя — непонятно, что именно и где менять.

Теперь каждое действие обязано отвечать на четыре вопроса, иначе оно не
попадает в отчёт:

  ЧТО    — императив с конкретным объектом («дописать раздел под три запроса»),
  ГДЕ    — путь файла и поле, которое правит редактор,
  ПОЧЕМУ — данные: какие запросы, какие позиции, кто стоит выше,
  ПРИЁМКА — проверяемый признак, по которому работу можно принять.

Два правила, которые удерживают отчёт от вранья:

1. **Не советовать сделанное.** Если ссылка на карточку товара уже стоит, а
   FAQ уже есть, действие не предлагается — вместо него в отчёт идёт строка
   «проверено, уже сделано». Руководитель должен видеть, что система смотрела
   на страницу, а не гадала по её типу.
2. **Не советовать то, что нечем обосновать.** Внешние ссылки, поведенческие
   факторы, «улучшить оптимизацию» не появляются в рекомендациях вовсе: контур
   не измеряет ни ссылочный профиль, ни поведение. Такие меры вынесены в
   отдельный список «не рекомендуем сейчас» с указанием, каких данных не
   хватает, чтобы их вообще обсуждать.
"""
from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401
import re  # noqa: E402
from attack_engine import page_audit  # noqa: E402

# Где правится текст в зависимости от типа страницы. Правило проекта: мету и
# описания товаров правим только через файл в репозитории и workflow, руками
# в Directus — нельзя.
EDIT_ROUTE = {
    "blog": "правка md-файла статьи, обычный PR",
    "vendor": ("правка полей tagline/about в src/data/vendors.ts, обычный PR; "
               "карточки товаров на странице приходят из Directus"),
    "product": ("правка data/seo/product-descriptions.json и перенос в Directus "
                "через workflow ops-apply-descriptions (сначала apply=false — "
                "план, затем apply=true); руками в Directus не править"),
}

# Слова, которые не превращаются в правку текста, даже если их нет на
# странице. Список — прямой результат разбора первого выполненного объёма
# работ 01.09.2026: контур предлагал дописать в описание Postman слово
# «москва», а в описание Depositphotos — «недорого».
STOP_EVALUATIVE = {
    "недорого", "дешево", "дешевле", "выгодно", "выгодные", "лучший",
    "лучшие", "надежный", "быстро", "срочно", "бесплатно",
}
# Города: гео-запрос закрывается не словом в описании товара. Страница
# вендора не про Москву, и вписывать туда город — порча текста ради
# формального совпадения.
STOP_GEO = {
    "москва", "москве", "спб", "петербург", "екатеринбург", "новосибирск",
    "казань", "краснодар",
}

# Где лежит шаблон, из которого собирается видимая часть страницы. Нужен,
# чтобы предлагать одну правку на весь тип страниц вместо десятков одинаковых
# правок в данных.
TEMPLATE_OF = {
    "vendor": "src/components/VendorLanding.astro",
    "product": "src/pages/product/[slug].astro",
}
# Со скольких страниц одного типа нехватка одного и того же слова перестаёт
# быть текстовой правкой и становится правкой шаблона.
SYSTEMIC_THRESHOLD = 3

OWNER = {
    "системная": "разработчик + редактор",
    "проверка": "редактор",
    "текст": "редактор",
    "заголовки": "редактор",
    "перелинковка": "редактор",
    "мета": "SEO + редактор",
    "индексация": "SEO",
}


@dataclass
class Action:
    action_id: str
    kind: str
    what: str
    where: str
    why: str
    steps: list[str] = field(default_factory=list)
    check: str = ""
    effort: str = "S"
    owner: str = "редактор"


def plural(count: int, one: str, few: str, many: str) -> str:
    """Согласование числительного: 1 запрос, 2 запроса, 5 запросов.

    Мелочь, но отчёт читает руководитель, и «2 запросов» в поручении выглядит
    как машинный черновик, а не как задание.
    """
    tail100 = count % 100
    tail10 = count % 10
    if 11 <= tail100 <= 14:
        word = many
    elif tail10 == 1:
        word = one
    elif 2 <= tail10 <= 4:
        word = few
    else:
        word = many
    return f"{count} {word}"


def queries_word(count: int) -> str:
    return plural(count, "запрос", "запроса", "запросов")


def _effort(count: int) -> str:
    return "S" if count <= 2 else ("M" if count <= 6 else "L")


def _rivals_phrase(package: dict) -> str:
    rivals = package.get("rivals") or []
    if not rivals:
        return "выше нас никого из отслеживаемых участников"
    return "выше нас " + ", ".join(rivals[:3])


def build(package: dict, page: page_audit.PageContent,
          geo: dict | None = None,
          template_words: set[str] | None = None
          ) -> tuple[list[Action], list[str], list[str]]:
    """Действия по пакету, список уже сделанного и список необоснованного."""
    queries = package.get("queries") or []
    audit = page_audit.audit(page, queries)
    absent = audit["по_степени"][page_audit.COVER_NONE]
    body_only = audit["по_степени"][page_audit.COVER_BODY]
    missing_words = audit["нет_слов"]

    url_short = (package.get("url") or "").replace("https://biz-soft.pro", "")
    route = EDIT_ROUTE.get(page.kind, "правка в репозитории")
    actions: list[Action] = []
    done: list[str] = []
    number = 0

    def add(kind, what, where, why, steps, check, effort):
        nonlocal number
        number += 1
        actions.append(Action(
            action_id=f"{package.get('package_id', 'WP')}-{number}",
            kind=kind, what=what, where=where, why=why, steps=steps,
            check=check, effort=effort, owner=OWNER.get(kind, "редактор")))

    if not page.available:
        # Отдельный тип: это не правка текста, а ручная проверка. Важно и для
        # цикла экспериментов — из такого действия нельзя вывести требование
        # «фраза должна появиться», потому что мы не знаем, чего на странице
        # нет: мы просто её не видим.
        add("проверка",
            (f"Проверить вручную, раскрыты ли на странице "
             f"{queries_word(len(queries))} пакета"),
            f"{url_short} — {page.edit_hint}",
            (f"содержимое страницы не хранится в репозитории, автоматическая "
             f"проверка невозможна: {page.scope_note}"),
            [f"«{q}»" for q in queries[:10]],
            "по каждой фразе видно, где именно она встречается на странице",
            _effort(len(queries)))
        return actions, done, not_recommended()

    # 1. Запросов нет на странице вовсе — самое дорогое упущение.
    # Часть недостающих слов дописывать нельзя: оценочные о себе запрещены
    # редполитикой, города не решают гео-задачу, а латинские слова на карточке
    # товара, скорее всего, уже стоят в названии из Directus, которого мы не
    # видим. Такие запросы уходят не в поручение, а в список «не рекомендуем».
    blocked: list[str] = []
    editable: list[str] = []
    template_words = template_words or set()
    for query in absent:
        words = missing_words.get(query) or []
        # Слова, которые закроет одна правка шаблона, не превращаются в
        # правку текста конкретной страницы: иначе одно и то же дописывается
        # в двадцать описаний вместо одного места.
        if words and all(w in template_words for w in words):
            done.append(f"«{query}» закрывается системной правкой шаблона — "
                        f"отдельная правка этой страницы не нужна")
            continue
        words = [w for w in words if w not in template_words]
        stop = [w for w in words if w in STOP_EVALUATIVE or w in STOP_GEO]
        blind = ([w for w in words
                  if page.kind == "product" and re.fullmatch(r"[a-z0-9]+", w)]
                 if page.kind == "product" else [])
        if stop:
            blocked.append(f"«{query}» — не дописываем: "
                           + ", ".join(f"«{w}»" for w in stop)
                           + (" оценочное слово о себе"
                              if any(w in STOP_EVALUATIVE for w in stop)
                              else " название города; гео-задача словом в "
                                   "тексте не решается"))
        elif blind:
            blocked.append(f"«{query}» — проверить, а не дописывать: "
                           + ", ".join(f"«{w}»" for w in blind)
                           + " может уже стоять в названии товара из Directus, "
                             "которого проверка не видит")
        else:
            editable.append(query)
    absent = editable
    skip_extra = blocked

    if absent:
        steps = []
        for query in absent[:8]:
            words = missing_words.get(query) or []
            tail = f" — не хватает слов: {', '.join(words)}" if words else ""
            steps.append(f"«{query}»{tail}")
        add("текст",
            (f"Дописать текст под {queries_word(len(absent))} "
             f"без единого вхождения на странице"),
            f"{url_short} — {page.edit_hint} ({route})",
            (f"по этим запросам мы на позициях "
             f"{package.get('position_best')}–{package.get('position_worst')}, "
             f"{_rivals_phrase(package)}; вхождений темы нет в тексте, который "
             f"мы контролируем в репозитории"
             + ("" if page.kind == "blog" else
                f" — {page.scope_note}, поэтому перед правкой убедитесь, что "
                f"фразы нет и в теле страницы из Directus")),
            steps,
            ("каждая фраза из списка встречается в тексте страницы хотя бы раз, "
             "в естественной формулировке, а не перечислением"),
            _effort(len(absent)))

    # 2. Тема есть в тексте, но не вынесена в заголовки.
    if body_only:
        add("заголовки",
            f"Вынести {queries_word(len(body_only))} в подзаголовки или вопросы FAQ",
            f"{url_short} — {page.edit_hint}",
            ("тема раскрыта в тексте, но не видна в структуре страницы: "
             "заголовки и вопросы FAQ поисковик сопоставляет с запросом "
             "в первую очередь"),
            [f"«{q}»" for q in body_only[:8]],
            "каждая фраза стоит в H2/H3 или в вопросе FAQ, а не только в абзаце",
            _effort(len(body_only)))

    # 3. FAQ под нераскрытые формулировки — только для статей блога, где FAQ
    #    задаётся во frontmatter и размечается штатным компонентом.
    if absent and page.kind == "blog":
        if page.faq_questions:
            add("заголовки",
                (f"Добавить {plural(min(len(absent), 4), 'вопрос', 'вопроса', 'вопросов')} "
                 f"в существующий FAQ"),
                f"{page.edit_hint}, блок faq во frontmatter",
                (f"FAQ на странице есть ({len(page.faq_questions)} вопросов), но "
                 f"нераскрытые формулировки запросов в него не попали"),
                [f"«{q}?»" for q in absent[:4]],
                "новые вопросы видны на странице и попадают в разметку FAQPage",
                "S")
        else:
            add("заголовки", "Добавить блок FAQ",
                f"{page.edit_hint}, блок faq во frontmatter",
                "у страницы нет FAQ, а запросы пакета сформулированы как вопросы",
                [f"«{q}?»" for q in absent[:5]],
                "FAQ выводится на странице и попадает в разметку FAQPage",
                "M")

    # 4. Коммерческая связка — только если её действительно нет.
    links = page.internal_links or []
    has_product = any(l.startswith("/product/") for l in links)
    has_vendor = any(l.startswith("/vendors/") for l in links)
    if page.kind == "blog":
        if has_product and has_vendor:
            done.append(
                f"коммерческая связка на месте: со страницы стоят ссылки на "
                f"карточки товара "
                f"({plural(sum(1 for l in links if l.startswith('/product/')), 'штуку', 'штуки', 'штук')}) "
                f"и на страницу вендора — добавлять нечего")
        else:
            missing_links = []
            if not has_product:
                missing_links.append("ссылку на карточку товара с ценой")
            if not has_vendor:
                missing_links.append("ссылку на страницу вендора")
            add("перелинковка",
                "Добавить коммерческий переход из статьи",
                f"{page.edit_hint}, блок related и текст статьи",
                ("статья отвечает на вопрос, но не ведёт к покупке: "
                 + " и ".join(missing_links) + " на странице нет"),
                missing_links,
                "из статьи есть переход на страницу, где можно оформить заказ",
                "S")
        if page.faq_questions:
            done.append(f"FAQ есть — "
                        f"{plural(len(page.faq_questions), 'вопрос', 'вопроса', 'вопросов')}, "
                        f"размечен штатным компонентом")

    # 5. Заголовок страницы под самый весомый запрос пакета.
    # Заголовок правим только там, где он наш: у статьи это поле title, у
    # карточки — meta_title в файле описаний. Заголовок вендорской страницы
    # собирается шаблоном src/pages/vendors/[slug].astro для всех вендоров
    # сразу, и правка «под один запрос» там означала бы правку всего шаблона —
    # это отдельное решение, а не пункт ТЗ по одной странице.
    top_query = queries[0] if queries else ""
    if top_query and page.title and page.kind in ("blog", "product"):
        words = page_audit.significant_words(top_query)
        title_norm = page_audit.normalize(page.title)
        lost = [w for w in words if w not in title_norm]
        if lost:
            add("мета",
                "Пересобрать заголовок страницы под ведущий запрос пакета",
                (f"{page.edit_hint} — поле title"
                 + (" и meta_title" if page.kind == "product" else "")),
                (f"в заголовке нет слов: {', '.join(lost)}; ведущий запрос "
                 f"пакета — «{top_query}»"),
                [f"уместить «{top_query}» в заголовок до 60 символов, "
                 f"не превращая его в перечисление ключей"],
                "заголовок уникален по сайту, до 60 символов, содержит фразу",
                "S")
        else:
            done.append("заголовок страницы уже содержит ведущий запрос пакета")

    # 6. Гео — только при измеренном разрыве между регионами.
    if geo and geo.get("разрыв_позиций"):
        add("текст",
            "Закрыть региональный разрыв по Санкт-Петербургу",
            f"{url_short} — {page.edit_hint}",
            (f"в Москве позиция {geo['москва']}, в Санкт-Петербурге "
             f"{geo['спб']}: разрыв {geo['разрыв_позиций']} позиций по одним и "
             f"тем же запросам"),
            ["проверить, нет ли в тексте привязки к одному городу",
             "убедиться, что условия оформления не выглядят московскими"],
            "разрыв позиций между регионами сократился при следующем замере",
            "M")

    # 7. Переобход — всегда последним и всегда с конкретным URL.
    if actions:
        add("индексация",
            "Отправить страницу на переобход после правок",
            "workflow ops-yandex-recrawl, запуск с main",
            ("правка вступает в силу для поиска только после переобхода; "
             "квота 150 URL в сутки, страница одна"),
            [f"urls = https://biz-soft.pro{url_short}"],
            "URL принят Вебмастером, результат в журнале issue #22",
            "S")

    return actions, done, not_recommended() + skip_extra


def not_recommended() -> list[str]:
    """Меры, которые контур не советует, потому что не измеряет их основание."""
    return [
        "внешние ссылки и их закупка: ссылочный профиль этим контуром не "
        "измеряется — предлагать бюджет под неизмеряемое нельзя",
        "поведенческие факторы: данные Метрики по этим страницам в контур не "
        "заведены, эффект правок проверить нечем",
        "общие формулировки вида «улучшить SEO» и «усилить контент»: их нельзя "
        "ни поручить, ни принять — они запрещены проверкой отчёта",
    ]


def headline(actions: list[Action], package: dict) -> str:
    """Заголовок пакета — первое действие, а не шаблон по типу страницы.

    Именно эта строка уходит в письмо как поручение дня, поэтому она обязана
    быть исполнимой сама по себе: глагол, объект, место.
    """
    if not actions:
        return package.get("action") or "действий по странице не найдено"
    # Без URL: адрес страницы печатается рядом отдельной строкой и в письме,
    # и в отчёте — дублировать его в самом поручении незачем.
    return actions[0].what


def order_by_effect(actions: list[Action],
                    effect_ranking: dict[str, float] | None) -> list[Action]:
    """Ставит вперёд типы действий, которые на опыте дают эффект.

    Пока по типу действия не накоплено достаточно оценённых экспериментов,
    его в ranking нет и порядок остаётся прежним: подстраивать очередь работ
    под два-три случайных исхода — способ закрепить случайность. Переобход
    всегда идёт последним: он не улучшение, а завершение работы.
    """
    if not effect_ranking:
        return actions
    def key(pair):
        index, action = pair
        if action.kind == "индексация":
            return (2, 0.0, index)
        effect = effect_ranking.get(action.kind)
        if effect is None:
            return (1, 0.0, index)   # неизученные — после изученных
        return (0, effect, index)    # меньше (сильнее выигрыш) — раньше
    return [a for _, a in sorted(enumerate(actions), key=key)]


def systemic_actions(packages: list[dict],
                     pages: dict[str, page_audit.PageContent]
                     ) -> tuple[list[Action], dict[str, set[str]]]:
    """Одна правка шаблона вместо десятков одинаковых правок в данных.

    Главный урок разбора 01.09.2026. Из 32 пакетов 21 закрылся двумя правками
    шаблонов: на карточке товара не было слова «купить», на лендинге вендора —
    «аккаунт» и «подписка». Контур предлагал дописать их в каждое описание
    по отдельности, то есть двадцать раз решить одну задачу и двадцать раз
    рискнуть испортить текст.

    Правило: если одного и того же слова не хватает на трёх и более страницах
    одного типа, это не текст страницы, а шаблон. Такие слова уходят в одно
    системное действие, а из индивидуальных поручений исключаются.
    """
    counts: dict[tuple[str, str], list[str]] = {}
    for package in packages:
        page = pages.get(package.get("url", ""))
        if page is None or not page.available or page.kind not in TEMPLATE_OF:
            continue
        audit = page_audit.audit(page, package.get("queries") or [])
        for words in audit["нет_слов"].values():
            for word in words:
                if word in STOP_EVALUATIVE or word in STOP_GEO:
                    continue
                counts.setdefault((page.kind, word), []).append(package["url"])

    actions: list[Action] = []
    by_kind: dict[str, set[str]] = {}
    grouped: dict[str, dict[str, list[str]]] = {}
    for (kind, word), urls in counts.items():
        if len(set(urls)) < SYSTEMIC_THRESHOLD:
            continue
        grouped.setdefault(kind, {})[word] = sorted(set(urls))
        by_kind.setdefault(kind, set()).add(word)

    for number, (kind, words) in enumerate(sorted(grouped.items()), start=1):
        pages_count = len({u for urls in words.values() for u in urls})
        actions.append(Action(
            action_id=f"S-{number:02d}",
            kind="системная",
            what=(f"Добавить в шаблон страниц типа «{kind}» упоминания: "
                  + ", ".join(f"«{w}»" for w in sorted(words))),
            where=TEMPLATE_OF[kind],
            why=(f"этих слов нет сразу на {pages_count} страницах этого типа — "
                 f"значит дело не в тексте конкретной страницы, а в шаблоне; "
                 f"одна правка закрывает все"),
            steps=[f"«{word}» — не хватает на {len(urls)} страницах, например "
                   + ", ".join(u.replace("https://biz-soft.pro", "")
                               for u in urls[:3])
                   for word, urls in sorted(words.items())],
            check=("формулировки читаются естественно и уместны на любой "
                   "странице этого типа, вёрстка не изменилась"),
            effort="M", owner=OWNER["системная"]))
    return actions, by_kind


def enrich(packages: list[dict], geo_by_query: dict | None = None,
           effect_ranking: dict[str, float] | None = None) -> list[Action]:
    """Дописывает в каждый пакет конкретные действия и то, что уже сделано.

    Работает поверх готовых пакетов: скоринг и порядок пакетов не трогает,
    добавляет только исполнительную часть. Порядок действий внутри пакета
    может подстраиваться под накопленный опыт — см. order_by_effect.

    Возвращает системные правки — то, что нужно поправить один раз в шаблоне
    вместо десятков одинаковых правок в данных.
    """
    geo_by_query = geo_by_query or {}
    pages = {p.get("url", ""): page_audit.load(p.get("url", ""),
                                               p.get("page_kind", ""))
             for p in packages}
    systemic, template_words = systemic_actions(packages, pages)
    for package in packages:
        page = pages[package.get("url", "")]
        geo = geo_gap(package.get("queries") or [], geo_by_query)
        actions, done, skip = build(package, page, geo,
                                    template_words.get(page.kind, set()))
        actions = order_by_effect(actions, effect_ranking)
        package["действия"] = to_dicts(actions)
        package["порядок_по_опыту"] = bool(effect_ranking)
        package["уже_сделано"] = done
        package["не_рекомендуем"] = skip
        # Слова, закрываемые правкой шаблона: по ним эксперимент поймёт, что
        # правка затронула все страницы типа, и исключит их из контроля.
        package["системные_слова"] = sorted(template_words.get(page.kind, set()))
        package["проверено_по"] = page.scope_note
        package["источник_текста"] = page.source_path or page.edit_hint
        package["action"] = headline(actions, package)
    return systemic


def geo_gap(queries: list[str], geo_by_query: dict) -> dict | None:
    """Разрыв позиций между Москвой и Санкт-Петербургом по запросам пакета.

    Считается только по запросам, измеренным в обоих регионах: сравнивать
    позицию в Москве с отсутствием замера в Петербурге бессмысленно.
    """
    pairs = [geo_by_query[key] for key in
             (page_audit.normalize(q) for q in queries) if key in geo_by_query]
    both = [(m, s) for m, s in pairs if m is not None and s is not None]
    if not both:
        return None
    moscow = sum(m for m, _ in both) / len(both)
    spb = sum(s for _, s in both) / len(both)
    gap = round(spb - moscow, 1)
    if gap < 2:
        return None
    return {"москва": round(moscow, 1), "спб": round(spb, 1),
            "разрыв_позиций": gap, "запросов": len(both)}


def to_dicts(actions: list[Action]) -> list[dict]:
    return [asdict(a) for a in actions]
