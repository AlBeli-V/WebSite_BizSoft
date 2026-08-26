#!/usr/bin/env python3
"""Карта измерений: разные сущности вместо ложного «единого определения визита».

Методическое исправление DATA-001 (19.08.2026). Прежняя постановка требовала свести
Вебмастер, Метрику и GA4 к одному определению визита. Это неверно: перечисленные
источники измеряют разные сущности на разных охватах, и приведение их к одному
числу означало бы потерю смысла, а не устранение ошибки.

Вместо этого фиксируются пять самостоятельных сущностей:

  Webmaster impressions — показы сайта в выдаче Яндекса по выборке запросов;
  Webmaster clicks      — переходы по той же выборке запросов;
  Metrika visits        — визиты на сайт из органического поиска (весь сайт);
  GA4 sessions          — сессии из органического поиска (весь сайт, своя модель);
  CRM leads             — обращения; источник не подключён.

Правило сравнимости: два показателя сравниваются напрямую только при совпадении
охвата (scope) и периода. Клики по выборке топ-100 запросов и визиты всего сайта
охват не разделяют, поэтому их отношение не является «расхождением источников».

Статус здоровья данных:
  verified — охваты и периоды сопоставлены;
  limited  — источники исправны, но охваты различаются;
  degraded — источник действительно сломан или сбор не прошёл.
"""

from __future__ import annotations

SCOPE_SAMPLE_QUERIES = "выборка топ-100 запросов"
SCOPE_SITEWIDE = "весь сайт"
SCOPE_NONE = "нет источника"


def _entry(source, metric, entity, scope, period, filters, coverage,
           comparable_with, difference_explanation, value=None, status="ok"):
    return {
        "source": source,
        "metric": metric,
        "entity": entity,
        "scope": scope,
        "period": period,
        "filters": filters,
        "coverage": coverage,
        "comparable_with": comparable_with,
        "difference_explanation": difference_explanation,
        "value": value,
        "status": status,
    }


def period_of(src: dict | None) -> str:
    if not src:
        return "нет данных"
    return f"{src.get('current_period_start')}–{src.get('current_period_end')}"


def build_map(snap: dict) -> list[dict]:
    """Пять сущностей измерения с явным охватом и правилами сравнимости."""
    yx = snap.get("yandex") or {}
    g = snap.get("google") or {}
    an = snap.get("analytics") or {}
    m = an.get("metrika") or {}
    ga = an.get("ga4") or {}
    crm = snap.get("crm") or {}

    yx_ok = yx.get("available")
    yx_src = yx.get("source") if yx_ok else None
    yx_tot = yx.get("totals") or {}

    # С дневной витриной показы и клики Яндекса — весь сайт: KPI единого
    # охвата с аналитикой. Выборка запросов остаётся инструментом раздела
    # возможностей и в карту KPI не входит.
    yx_daily = (snap.get("daily") or {}).get("yandex") or {}
    yx_from_daily = bool(yx_daily.get("complete"))
    if yx_from_daily:
        w = yx_daily["windows"]
        cur = w["impressions"]["current"]
        yx_scope = SCOPE_SITEWIDE
        yx_period = f"{cur['from']}–{cur['to']}"
        yx_coverage = "все запросы хоста, ряды по дням (дневная витрина)"
        yx_imp, yx_clk = cur["sum"], w["clicks"]["current"]["sum"]
        imp_note = ("Показы всего сайта по дням; окно равной длины строит отчёт. "
                    "С показами Google не складываются: разные поисковые системы.")
        clk_note = ("Все переходы из выдачи Яндекса; сопоставимы с визитами "
                    "Метрики по порядку величины, но визит и клик — разные "
                    "события и напрямую не равны.")
    else:
        yx_scope = SCOPE_SAMPLE_QUERIES
        yx_period = period_of(yx_src)
        yx_coverage = f"{yx_tot.get('queries_tracked')} запросов выборки"
        yx_imp, yx_clk = yx_tot.get("impressions"), yx_tot.get("clicks")
        imp_note = ("Показы и клики измерены на одной выборке запросов, поэтому их "
                    "отношение корректно как CTR выборки. С визитами и сессиями "
                    "охват не совпадает.")
        clk_note = ("Клики этой выборки — часть всех переходов из Яндекса, а не все "
                    "переходы. Сравнение с визитами всего сайта означало бы "
                    "сравнение части с целым.")

    rows = [
        _entry(
            "Яндекс.Вебмастер", "impressions", "показ сайта в выдаче",
            yx_scope, yx_period,
            "поиск Яндекса, регион не разделён",
            yx_coverage,
            ["Яндекс.Вебмастер · clicks"],
            imp_note,
            yx_imp, "ok" if yx_ok or yx_from_daily else "unavailable"),
        _entry(
            "Яндекс.Вебмастер", "clicks", "переход из выдачи",
            yx_scope, yx_period,
            "поиск Яндекса" + ("" if yx_from_daily else ", те же запросы"),
            yx_coverage,
            ["Яндекс.Вебмастер · impressions"],
            clk_note,
            yx_clk, "ok" if yx_ok or yx_from_daily else "unavailable"),
        _entry(
            "Google Search Console", "impressions", "показ страницы в выдаче",
            SCOPE_SITEWIDE, period_of(g.get("source")),
            "web-поиск, ресурс sc-domain",
            "все страницы ресурса",
            [],
            "Отдельная поисковая система: с числами Яндекса не складывается и "
            "не сравнивается.",
            (g.get("totals") or {}).get("impressions_window"),
            "ok" if g.get("available") else "unavailable"),
        _entry(
            "Яндекс.Метрика", "visits", "визит из органического поиска",
            SCOPE_SITEWIDE, period_of(m.get("source")),
            "источник трафика: органический",
            "все страницы сайта, все поисковые системы",
            ["GA4 · sessions"],
            "Визит объединяет действия пользователя с таймаутом 30 минут; охват — "
            "весь сайт и все поисковики, включая Google.",
            m.get("organic_visits"), "ok" if m.get("available") else "unavailable"),
        _entry(
            "GA4", "sessions", "сессия из органического поиска",
            SCOPE_SITEWIDE, period_of(ga.get("source")),
            "канал: Organic Search",
            "все страницы сайта, все поисковые системы",
            ["Яндекс.Метрика · visits"],
            "Модель сессии GA4 отличается от модели визита Метрики (граница суток, "
            "источник, таймаут), поэтому небольшое расхождение — норма, а не ошибка.",
            ga.get("organic_sessions"), "ok" if ga.get("available") else "unavailable"),
        _entry(
            "CRM", "leads", "обращение",
            SCOPE_NONE, "нет данных", "—", "нет данных", [],
            "Источник не подключён: связь визитов с обращениями и выручкой "
            "не измеряется.",
            None, "unavailable"),
    ]
    return rows


def sample_ctr(snap: dict) -> dict | None:
    """CTR выборки запросов — корректная величина: показы и клики одного охвата."""
    yx = snap.get("yandex") or {}
    if not yx.get("available"):
        return None
    t = yx.get("totals") or {}
    imp, clicks = t.get("impressions"), t.get("clicks")
    if not imp:
        return None
    return {
        "value": clicks / imp,
        "impressions": imp,
        "clicks": clicks,
        "scope": SCOPE_SAMPLE_QUERIES,
        "label": "CTR выборки",
        "caveat": "только выборка топ-100 запросов, не CTR всего сайта",
    }


def scopes_comparable(snap: dict) -> bool:
    """Сопоставлены ли охваты поиска и аналитики.

    С дневной витриной показы и клики Яндекса считаются по всему сайту —
    KPI всех источников описывают один охват, и признак выполняется. Без
    витрины действует прежняя логика: выборка запросов и весь сайт
    несопоставимы по построению.
    """
    if ((snap.get("daily") or {}).get("yandex") or {}).get("complete"):
        return True
    yx = snap.get("yandex") or {}
    scope_note = (yx.get("totals") or {}).get("scope_note") or ""
    return "выборка" not in scope_note


def data_health(snap: dict, findings: list[dict]) -> dict:
    """verified | limited | degraded — по состоянию источников и охватов."""
    broken = [f for f in findings if f.get("level") == "critical"]
    sources = {
        "yandex": (snap.get("yandex") or {}).get("available"),
        "google": (snap.get("google") or {}).get("available"),
        "metrika": ((snap.get("analytics") or {}).get("metrika") or {}).get("available"),
        "ga4": ((snap.get("analytics") or {}).get("ga4") or {}).get("available"),
    }
    missing = [k for k, v in sources.items() if not v]
    if broken or missing:
        # «Сбой» называет конкретную причину: какой сбор не прошёл или какая
        # критическая находка сработала. Прежняя формулировка «источник отдаёт
        # некорректные данные» винила исправный источник в методических
        # расхождениях окон и читалась как поломка на ровном месте.
        titles = "; ".join(sorted({f.get("title") or f.get("code") or "" for f in broken}))
        return {
            "status": "degraded",
            "reason": ("сбор источника не прошёл: " + ", ".join(missing)) if missing
                      else f"критические находки качества: {titles}",
            "colour": "danger",
            "detail": "Показатели недоступных источников публикуются как "
                      "«нет данных», а не ноль; дельты и сравнения по ним не "
                      "считаются. Остальные блоки письма собраны из доступных "
                      "источников.",
        }
    if not scopes_comparable(snap):
        return {
            "status": "limited",
            "reason": "охваты источников различаются — ограничение методики, не сбой",
            "colour": "warning",
            "detail": "Поиск Яндекса отдаёт выборку запросов, аналитика — весь сайт. "
                      "Источники исправны; каждый показатель письма подписан своим "
                      "охватом, а напрямую сравниваются только числа одного охвата.",
        }
    return {
        "status": "verified",
        "reason": "охваты сопоставлены: KPI считаются по всему сайту",
        "colour": "positive",
        "detail": "Показы и клики Яндекса, показы Google, визиты Метрики и сессии "
                  "GA4 считаются по всему сайту за окна равной длины. Выборка "
                  "запросов используется только в разделе возможностей и на KPI "
                  "не влияет.",
    }
