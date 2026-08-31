"""Блок «Реклама» ежедневного письма — Direct Control Report, этап A.

Правила вердиктов утверждены проектом 29.08.2026 (§3): маркер всегда
идёт со словом-причиной; до 10 накопленных кликов направление серое —
«мало данных», и никакие решения по нему не предлагаются. Заявки и CPA
подключаются этапом B (связка с Метрикой/CRM по yclid) — до этого колонка
CPA честно пустая, а вердикты строятся на кликах, вовлечении бюджета и
чистоте поисковых запросов.

Витрину reports/seo/ppc/direct-stats.json пишет scripts/ppc/direct_report.py.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

STATS = pathlib.Path("reports/seo/ppc/direct-stats.json")

WEEKLY_LIMIT_RUB = 4098  # 5000 ₽/нед пополнения минус НДС 22%
GREY_MIN_CLICKS = 10

# Направление ← имя группы в кабинете; стоп-порог кликов без вовлечения и
# допустимый CPA (≈25% прибыли сделки направления) — из спецификации v3.
GROUPS = [
    {"key": "k1", "label": "Claude", "match": "Claude — подписки",
     "stop_clicks": 40, "cpa_limit": 3000},
    {"key": "k2", "label": "Claude Code", "match": "Claude Code",
     "stop_clicks": 25, "cpa_limit": 3000},
    {"key": "k3", "label": "Midjourney", "match": "Midjourney",
     "stop_clicks": 25, "cpa_limit": 600},
    {"key": "k4", "label": "ChatGPT Business", "match": "ChatGPT",
     "stop_clicks": 12, "cpa_limit": 2500},
    # Расширение #210 (29.08): пороги предложены по аналогии — Cursor как
    # Claude Code (B2B-dev, сопоставимая подписка), Adobe консервативнее
    # (маржа ниже AI-подписок); уточняются решением руководителя.
    {"key": "k5", "label": "Cursor", "match": "Cursor",
     "stop_clicks": 25, "cpa_limit": 3000},
    {"key": "k6", "label": "Adobe", "match": "Adobe",
     "stop_clicks": 20, "cpa_limit": 1500},
]

# Маркеры нерелевантного интента в реальном поисковом запросе. Запрос,
# задевший маркер, считается мусорным: его расход суммируется, а слова идут
# в кандидаты минусов. Список консервативный — спорное мусором не считаем.
JUNK_MARKERS = [
    "бесплатно", "бесплатн", "скачать", "торрент", "взлом", "кряк", "crack",
    "apk", "апк", "что такое", "как пользоваться", "как работает", "отзыв",
    "вход", "войти", "регистрация", "личный кабинет", "промокод",
]

# Порог «требует решения» по мусору: столько ₽ суммарно можно потерять на
# нерелевантных запросах, прежде чем предложение минусов станет красным.
JUNK_DECISION_RUB = 300


def _campaign_day(date: str) -> dt.date:
    return dt.date.fromisoformat(date)


def _is_junk(query: str) -> bool:
    q = query.lower()
    return any(m in q for m in JUNK_MARKERS)


def build(date: str) -> dict:
    """Собрать блок за письмо от `date` (данные Директа — по date-1)."""
    if not STATS.exists():
        return {"available": False, "reason": "выгрузки Директа ещё нет"}
    data = json.loads(STATS.read_text(encoding="utf-8"))
    yesterday = (_campaign_day(date) - dt.timedelta(days=1)).isoformat()

    # Пейсинг — по ВСЕМ строкам витрины, а не по перечисленным направлениям:
    # расширение кампании (новая группа в кабинете) не должно молча занижать
    # недельный расход письма (инцидент #217, группы Cursor/Adobe из #210).
    total_spend_day = sum(r["Cost"] for r in data["groups"]
                          if r["Date"] == yesterday)
    total_spend_all = sum(r["Cost"] for r in data["groups"])

    rows = []
    matched_names: set[str] = set()
    for g in GROUPS:
        day = [r for r in data["groups"]
               if g["match"] in r["AdGroupName"] and r["Date"] == yesterday]
        alltime = [r for r in data["groups"] if g["match"] in r["AdGroupName"]]
        matched_names.update(r["AdGroupName"] for r in alltime)
        spend_day = sum(r["Cost"] for r in day)
        clicks_day = sum(r["Clicks"] for r in day)
        clicks_all = sum(r["Clicks"] for r in alltime)
        spend_all = sum(r["Cost"] for r in alltime)
        cpc = spend_day / clicks_day if clicks_day else None

        if clicks_all < GREY_MIN_CLICKS:
            verdict = {"tone": "grey", "label": f"мало данных ({clicks_all} кл.)"}
        elif clicks_all >= g["stop_clicks"]:
            # Вовлечение (secondary) подключается этапом B; до него порог
            # стоп-правила трактуем мягко: жёлтый сигнал «пора смотреть руками».
            verdict = {"tone": "warn",
                       "label": f"{clicks_all} кл. — пора оценить вовлечение"}
        else:
            verdict = {"tone": "ok", "label": "идёт набор статистики"}
        rows.append({"key": g["key"], "label": g["label"],
                     "spend_day": spend_day, "clicks_day": clicks_day,
                     "clicks_total": clicks_all, "spend_total": spend_all,
                     "cpc": cpc, "verdict": verdict})

    # Строки витрины, не попавшие ни под одно направление, — сигнал, что
    # кабинет ушёл вперёд списка GROUPS. Показываем их суммой и жёлтым
    # вердиктом, а не теряем: контроль не должен слепнуть от расширения.
    other = [r for r in data["groups"] if r["AdGroupName"] not in matched_names]
    if other:
        o_day = [r for r in other if r["Date"] == yesterday]
        spend_day = sum(r["Cost"] for r in o_day)
        clicks_day = sum(r["Clicks"] for r in o_day)
        clicks_all = sum(r["Clicks"] for r in other)
        names = sorted({r["AdGroupName"].split(" — ")[0] for r in other})
        rows.append({"key": "other", "label": "Прочие группы (" + ", ".join(names) + ")",
                     "spend_day": spend_day, "clicks_day": clicks_day,
                     "clicks_total": clicks_all,
                     "spend_total": sum(r["Cost"] for r in other),
                     "cpc": spend_day / clicks_day if clicks_day else None,
                     "verdict": {"tone": "warn",
                                 "label": "группа вне списка направлений — добавить в контроль"}})

    junk = [q for q in data["queries"] if _is_junk(q["Query"])]
    junk_cost = sum(q["Cost"] for q in junk)
    junk_queries = sorted({q["Query"] for q in junk if q["Clicks"] > 0} or
                          {q["Query"] for q in junk})

    decisions = []
    if junk_cost >= JUNK_DECISION_RUB:
        decisions.append({
            "tone": "bad",
            "text": (f"{junk_cost:.0f} ₽ ушло на нерелевантные запросы "
                     f"({len(junk_queries)} шт.) — предлагаю добавить минусы, "
                     "список в веб-отчёте"),
        })
    elif junk:
        decisions.append({
            "tone": "warn",
            "text": (f"замечены нерелевантные запросы ({len(junk_queries)} шт., "
                     f"{junk_cost:.0f} ₽) — наблюдаю, при росте предложу минусы"),
        })

    # Аномалия: рабочий день без показов — модерация, баланс или мониторинг.
    ydate = _campaign_day(yesterday)
    if ydate.weekday() < 5 and ydate >= _campaign_day(data["date_from"]):
        imp_yesterday = sum(r["Impressions"] for r in data["groups"]
                            if r["Date"] == yesterday)
        if imp_yesterday == 0:
            decisions.append({"tone": "bad",
                              "text": "в рабочий день не было ни одного показа — "
                                      "проверить модерацию, баланс и доступность сайта"})

    return {
        "available": True,
        "as_of": yesterday,
        "campaign": "bs-test-2026-09",
        "week": {"spent": total_spend_all, "limit": WEEKLY_LIMIT_RUB},
        "day_spend": total_spend_day,
        "rows": rows,
        "junk": {"cost": junk_cost, "queries": junk_queries[:12]},
        "decisions": decisions,
        "note": ("расход в деньгах кабинета (без НДС); заявки и CPA подключаются "
                 "связкой с Метрикой — этап B"),
    }
