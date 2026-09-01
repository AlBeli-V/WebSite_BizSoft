#!/usr/bin/env python3
"""Заявки и лиды: канал обращения и путь клиента до запроса.

Зачем модуль. До него отчёт знал о коммерческом результате ровно одно —
«CRM не подключена» (quality.NO_CRM): в письме стояли целевые события
Метрики, а настоящие заявки жили отдельно, в воронке Directus и в почте
менеджера. Связать их было нечем: письмо о заявке показывает канал по
метке браузера (`src/lib/quote-lead.ts`), где органика поисковика внешне
неотличима от перехода по ссылке — и то и другое выглядит как
«хост / referral». Отсюда вопрос руководителя 01.09.2026: «из каких
каналов приходили заявки — из рекламы, органики, фидов?»

Что делает модуль. Собирает из выгрузки заявок (`leads_collect.py`) блок
письма: заявки за прошедшие сутки, канал каждой и путь клиента к запросу.
Канал берётся из Метрики, когда визиты посетителя удалось поднять по
ym_client_id, и только при её молчании — из метки браузера. Основание
всегда названо: «Метрика» и «метка браузера» — разной силы утверждения,
и смешивать их в одну строку нельзя.

Числа и тексты в письмо попадают только отсюда: report_v4 форматирует
готовый блок и ничего не вычисляет.
"""

from __future__ import annotations

import datetime as dt

from textfmt import counted, num, ru_date

# Сколько заявок показывать в письме подробно. Остальные уходят строкой
# «ещё N» — письмо ограничено по объёму (uxlint), а разбор каждой заявки
# менеджер ведёт в воронке, не в отчёте.
DETAILED = 3

# Хвост для сводки: одна заявка в сутки — не ряд, и по ней не видно, какой
# канал работает. Неделя даёт минимальную опору, не превращая блок в отчёт
# по воронке.
SUMMARY_DAYS = 7

# Источник визита в терминах Метрики (ym:s:lastTrafficSource, поле id) —
# по-русски. Это единственная классификация каналов, которой мы доверяем:
# она учитывает и метки, и реферер, и переходы внутри сервисов Яндекса.
METRIKA_SOURCE = {
    "ad": "реклама",
    "organic": "поиск",
    "referral": "переход по ссылке",
    "direct": "прямой заход",
    "internal": "внутренний переход",
    "social": "соцсеть",
    "messenger": "мессенджер",
    "email": "письмо",
    "recommend": "рекомендательная система",
    "saved": "сохранённая страница",
    "undefined": "источник не определён",
}

# Хосты, по которым метка браузера узнаётся без Метрики. Важно: реферер
# поисковика означает «Яндекс» или «Google», но не отвечает, была это
# выдача или сервис (Карты, Бизнес, Почта) — поэтому формулировка
# намеренно двусмысленная, пока Метрика не уточнит.
TOUCH_HOSTS = [
    (("yandex.",), "yandex", "Яндекс — поиск или сервисы Яндекса"),
    (("google.",), "google", "Google — поиск или сервисы Google"),
    (("vk.com", "vk.ru", "ok.ru", "t.me", "telegram"), "social", "соцсеть или мессенджер"),
]

# Метки товарных фидов. Фиды на проде закрыты (404, docs/yandex-feeds.md),
# поэтому канал ожидаемо пуст — но классификатор обязан его различать:
# иначе первая же заявка после открытия фидов будет записана в «переходы
# по ссылкам» и решение об эффективности площадки будет принято по чужим
# числам.
FEED_MARKERS = ("market", "yml", "feed", "business", "products")

PAID_MEDIUMS = ("cpc", "ppc", "paid", "cpm", "banner")


def _host(touch: str) -> str:
    """Хост из строки канала вида «bitrix.informatic.ru / referral»."""
    return (touch or "").split("/")[0].strip().lower()


def channel_from_touch(lead: dict) -> dict:
    """Канал по метке браузера — запасной путь, когда Метрика молчит.

    Порядок разбора повторяет `attributionFields` на сайте: сначала явные
    признаки рекламы (yclid/gclid/utm_medium), потом фид, потом реферер.
    Иначе платный клик, пришедший с меткой и с реферером поисковика,
    был бы записан в органику.
    """
    if lead.get("yclid"):
        return {"key": "ad_direct", "label": "реклама — Яндекс.Директ",
                "evidence": "в ссылке был yclid"}
    if lead.get("gclid"):
        return {"key": "ad_google", "label": "реклама — Google Ads",
                "evidence": "в ссылке был gclid"}
    source = (lead.get("utm_source") or "").lower()
    medium = (lead.get("utm_medium") or "").lower()
    if medium in PAID_MEDIUMS:
        return {"key": "ad_other", "label": f"реклама — {source or 'метка без источника'}",
                "evidence": f"utm_medium={medium}"}
    if source and any(m in source for m in FEED_MARKERS):
        return {"key": "feed", "label": f"товарный фид — {source}",
                "evidence": f"utm_source={source}"}
    if source:
        return {"key": f"utm:{source}", "label": f"метка {source}",
                "evidence": f"utm_source={source}"}
    host = _host(lead.get("last_touch_source") or "")
    if host:
        for hosts, key, label in TOUCH_HOSTS:
            if any(h in host for h in hosts):
                return {"key": key, "label": label, "evidence": f"переход с {host}"}
        return {"key": "referral", "label": f"переход по ссылке — {host}",
                "evidence": f"переход с {host}"}
    return {"key": "unknown", "label": "источник не определён",
            "evidence": "меток и реферера в браузере не было"}


# Поисковые системы по-русски и в родительном падеже: «поиск Яндекса»
# читается, «поиск Yandex» — нет. Незнакомая система остаётся как есть:
# выдумывать склонение для неизвестного имени хуже, чем оставить латиницу.
ENGINE_RU = {"yandex": "Яндекса", "google": "Google", "mail.ru": "Mail.ru",
             "bing": "Bing", "duckduckgo": "DuckDuckGo", "rambler": "Рамблера"}


def _engine(step: dict) -> str:
    """Поисковая система шага пути — как её назвала Метрика."""
    raw = (step.get("engine") or "").strip()
    return ENGINE_RU.get(raw.lower(), raw)


def channel_from_metrika(lead: dict) -> dict | None:
    """Канал по визитам Метрики: источник последнего визита перед заявкой.

    Последнего, а не первого: вопрос «что привело к запросу сейчас»
    отвечает именно он. Первое касание показывается отдельной строкой пути
    и в B2B-цикле длиной в недели значит не меньше, но это другой вопрос.
    """
    journey = lead.get("journey") or {}
    steps = journey.get("steps") or []
    if not journey.get("available") or not steps:
        return None
    last = steps[-1]
    src = (last.get("source") or "undefined").lower()
    label = METRIKA_SOURCE.get(src, src)
    engine = _engine(last)
    if src == "organic" and engine:
        label = f"поиск {engine}"
    elif src == "ad":
        label = "реклама — Яндекс.Директ" if (engine or "").lower().startswith("yandex") \
            else "реклама"
    elif src == "referral":
        # Метрика называет источник, но не сайт-донор: в запросе визитов его
        # нет. Хост при этом известен из метки браузера, и без него строка
        # «переход по ссылке» не отвечает на вопрос «откуда» — ровно тот, ради
        # которого блок и заведён (заявка ООО «ИНФОРМАТИК» 31.08.2026 пришла
        # с корпоративного портала клиента, и это видно только по хосту).
        host = last.get("referer_host") or _host(lead.get("last_touch_source") or "")
        if host:
            label = f"переход по ссылке — {host}"
    return {"key": src, "label": label,
            "evidence": f"визит {ru_date(last.get('date'))}"}


def channel_of(lead: dict) -> dict:
    """Канал заявки с указанием основания.

    Метрика сильнее метки браузера и потому идёт первой: метка знает только
    реферер, а он не отличает выдачу поисковика от его же сервисов и теряется
    вместе с localStorage. Но если посетителя в счётчике поднять не удалось
    (нет ym_client_id, блокировщик, письмо вместо формы), молчать нельзя —
    тогда канал называется по метке, и это сказано прямо.
    """
    from_metrika = channel_from_metrika(lead)
    if from_metrika:
        return {**from_metrika, "basis": "Метрика"}
    touch = channel_from_touch(lead)
    return {**touch, "basis": "метка браузера"}


def journey_line(lead: dict) -> str:
    """Путь клиента к запросу одной строкой.

    Читается как рассказ: откуда узнали, сколько раз возвращались, с чего
    начали и чем закончили. Когда визитов в Метрике нет, строка говорит,
    что именно неизвестно, — пустое место в письме читатель достроит сам,
    и достроит неверно.
    """
    journey = lead.get("journey") or {}
    steps = journey.get("steps") or []
    if journey.get("available") and steps:
        first = steps[0]
        parts = [f"первый визит {ru_date(first.get('date'))} — "
                 f"{_step_text(first, lead)}"]
        if first.get("landing"):
            parts[0] += f", вход {first['landing']}"
        visits = journey.get("visits") or len(steps)
        if len(steps) > 1:
            middle = ", ".join(_step_text(s, lead) for s in steps[1:-1][:2])
            last = steps[-1]
            parts.append(f"{counted(visits, 'визит', 'визита', 'визитов')} до заявки"
                         + (f" ({middle})" if middle else ""))
            parts.append(f"заявка после визита {ru_date(last.get('date'))} — "
                         f"{_step_text(last, lead)}")
        else:
            parts.append(f"{counted(visits, 'визит', 'визита', 'визитов')} до заявки")
        return "; ".join(parts)

    # Метрики нет — рассказываем то, что известно из самой заявки.
    parts = []
    first_touch = lead.get("first_touch_source")
    last_touch = lead.get("last_touch_source")
    if first_touch and first_touch != last_touch:
        parts.append(f"первое касание — {first_touch}")
    if last_touch:
        parts.append(f"перед заявкой — {last_touch}")
    if lead.get("landing_path"):
        parts.append(f"вход {lead['landing_path']}")
    parts.append(_journey_gap(lead))
    return "; ".join(p for p in parts if p)


def _journey_gap(lead: dict) -> str:
    """Почему пути из Метрики нет — причина, а не многоточие."""
    journey = lead.get("journey") or {}
    if journey.get("error"):
        return f"визиты в Метрике не подняты: {journey['error']}"
    if not lead.get("ym_client_id"):
        return ("посетитель в счётчике не опознан — заявка пришла без "
                "идентификатора Метрики")
    return "визитов по этому посетителю Метрика не вернула"


def _step_text(step: dict, lead: dict | None = None) -> str:
    """Один шаг пути: источник, поисковик и фраза, если она известна.

    Заявка передаётся, чтобы шаг-переход мог назвать сайт-донор из метки
    браузера: в визитах Метрики домена реферера нет.
    """
    src = (step.get("source") or "undefined").lower()
    text = METRIKA_SOURCE.get(src, src)
    engine = _engine(step)
    if src == "organic" and engine:
        text = f"поиск {engine}"
    elif src == "referral":
        host = step.get("referer_host") or _host((lead or {}).get("last_touch_source") or "")
        text = f"переход с {host}" if host else "переход по ссылке"
    elif src == "ad":
        text = "реклама"
    if step.get("phrase"):
        text += f" по запросу «{step['phrase']}»"
    return text


def request_line(lead: dict) -> str:
    """Что именно запросили: состав, сумма и номер КП, если оно ушло."""
    parts = []
    if lead.get("product_ref"):
        parts.append(str(lead["product_ref"]))
    amount = lead.get("amount")
    if amount:
        parts.append(f"{num(amount)} ₽")
    if lead.get("quote_no"):
        parts.append(f"КП № {lead['quote_no']}")
    return " · ".join(parts) or "без указанного состава"


FORM_LABEL = {
    "pricing": "форма «узнать цену»",
    "question": "форма вопроса",
    "quote": "скачивание КП",
    "cart": "корзина",
    "contact": "форма обратной связи",
}


def form_label(lead: dict) -> str:
    key = (lead.get("form_source") or lead.get("source") or "").lower()
    return FORM_LABEL.get(key, f"форма {key}" if key else "источник формы не указан")


def _day_bounds(date: str) -> str:
    """Сутки, за которые письмо отчитывается: предыдущий календарный день.

    Письмо уходит утром и рассказывает про вчера — по Москве (правило
    проекта о часовом поясе). Заявки сегодняшнего утра попадут в завтрашнее
    письмо, иначе одна и та же заявка была бы показана дважды.
    """
    return (dt.date.fromisoformat(date) - dt.timedelta(days=1)).isoformat()


def _in_window(created: str, first_day: str, last_day: str) -> bool:
    day = (created or "")[:10]
    return bool(day) and first_day <= day <= last_day


def build(raw: dict | None, date: str) -> dict:
    """Блок «Заявки и лиды» для письма.

    Пустой день — не отсутствие данных: если выгрузка есть, а заявок за
    сутки нет, так и сказано. Это разные состояния, и путать их нельзя:
    первое требует чинить сбор, второе — работать со спросом.
    """
    if not raw or not raw.get("leads_available", True):
        return {"available": False,
                "reason": (raw or {}).get("reason")
                or "выгрузка заявок не выполнялась — блок появится после "
                   "первого прогона ops-leads-collect"}

    day = _day_bounds(date)
    week_start = (dt.date.fromisoformat(day) - dt.timedelta(days=SUMMARY_DAYS - 1)).isoformat()
    leads = sorted((raw.get("leads") or []), key=lambda l: l.get("created_at") or "")
    # Мусор в воронке заявкой не считается — ни в списке, ни в сводке.
    leads = [l for l in leads if (l.get("status") or "new") != "spam"]

    day_leads = [l for l in leads if _in_window(l.get("created_at"), day, day)]
    week_leads = [l for l in leads if _in_window(l.get("created_at"), week_start, day)]

    items = []
    for lead in day_leads:
        channel = channel_of(lead)
        items.append({
            "time": (lead.get("created_at") or "")[11:16],
            "company": lead.get("company") or "компания не указана",
            "inn": lead.get("inn") or "",
            "form": form_label(lead),
            "request": request_line(lead),
            "amount": lead.get("amount") or 0,
            "channel": channel["label"],
            "channel_key": channel["key"],
            "channel_basis": channel["basis"],
            "channel_evidence": channel.get("evidence", ""),
            "journey": journey_line(lead),
            "status": lead.get("status") or "new",
        })

    by_channel: dict[str, int] = {}
    for lead in week_leads:
        by_channel[channel_of(lead)["label"]] = by_channel.get(
            channel_of(lead)["label"], 0) + 1
    channels = sorted(by_channel.items(), key=lambda kv: (-kv[1], kv[0]))

    metrika = raw.get("metrika") or {}
    unresolved = sum(1 for l in day_leads if not (l.get("journey") or {}).get("available"))

    return {
        "available": True,
        "day": day,
        "window": {"from": week_start, "to": day},
        "count": len(day_leads),
        "week_count": len(week_leads),
        "amount": sum(int(l.get("amount") or 0) for l in day_leads),
        "items": items[:DETAILED],
        "more": max(0, len(items) - DETAILED),
        "channels": [{"label": label, "count": n} for label, n in channels],
        "unresolved": unresolved,
        "note": _note(metrika, unresolved, len(day_leads)),
        "empty_text": ("За сутки заявок не поступило." if not day_leads else ""),
    }


def _note(metrika: dict, unresolved: int, day_count: int) -> str:
    """Подпись блока: чем измерено и где измерение слабое."""
    base = ("канал определяется по визитам Метрики (ym:s:clientID); "
            "при отсутствии визитов — по метке источника в браузере, "
            "и тогда выдача поисковика неотличима от его сервисов")
    if metrika.get("error"):
        return f"{base}. Визиты за этот прогон не поднялись: {metrika['error']}"
    if day_count and unresolved:
        return (f"{base}. Без визитов в Метрике: "
                f"{counted(unresolved, 'заявка', 'заявки', 'заявок')}")
    return base


def summary_line(block: dict) -> str:
    """Одна строка для сводки писем и для карточки показателя."""
    if not block.get("available"):
        return "Заявки не выгружаются."
    if not block["count"]:
        return (f"За сутки заявок не поступило; за "
                f"{counted(SUMMARY_DAYS, 'день', 'дня', 'дней')} — "
                f"{counted(block['week_count'], 'заявка', 'заявки', 'заявок')}.")
    channels = ", ".join(f"{c['label']}: {c['count']}" for c in block["channels"][:3])
    return (f"{counted(block['count'], 'заявка', 'заявки', 'заявок')} за сутки"
            + (f" на {num(block['amount'])} ₽" if block["amount"] else "")
            + (f"; за {SUMMARY_DAYS} дней по каналам: {channels}" if channels else "")
            + ".")
