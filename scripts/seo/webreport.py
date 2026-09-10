#!/usr/bin/env python3
"""Публичный веб-отчёт: /daily/ГГГГ-ММ-ДД.

Письмо не должно вести руководителя в исходники репозитория. Веб-отчёт содержит
всё, что не поместилось в письмо: полный executive brief, таблицы запросов и
страниц, графики, историю экспериментов, журнал исполнения, ссылки на PR,
качество данных и методику.

Базовый адрес берётся из переменной окружения PUBLIC_REPORT_BASE_URL. Если она
не задана, письмо показывает GitHub как технический запасной вариант, а этот файл
всё равно генерируется — его можно выложить на любой статический хостинг.

Запуск: python3 scripts/seo/webreport.py [YYYY-MM-DD]
Результат: reports/seo/public/daily/<дата>/index.html
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "viz"))

import cannibalization as cannibal_mod  # noqa: E402
import daily_windows  # noqa: E402
import kpi_kit as kit  # noqa: E402
import lifecycle as lifecycle_mod  # noqa: E402
import mismatch as mismatch_mod  # noqa: E402
import opportunity as opp_mod    # noqa: E402
import quality as quality_mod    # noqa: E402
import serp_analysis as serp_mod  # noqa: E402
import snapshot as snapshot_mod  # noqa: E402
import technical                 # noqa: E402
import zero_impression as zero_mod  # noqa: E402
from report_v4 import (BLOB, BRANCH, PILL_LABEL, REPO, VERDICT_LABEL,  # noqa: E402
                       _exp_exposure_line, _exp_implementation_line,
                       _exp_interim_line, _exp_serp_line,
                       assemble, load_site_check)
from textfmt import counted, num, pct, ru_date, ru_date_full, signed  # noqa: E402

BASE = pathlib.Path("reports/seo/intelligence")
OUT = pathlib.Path("reports/seo/public/daily")


DEMAND_STATE = pathlib.Path("reports/seo/wordstat/intelligence-state.json")


IDEA_STATUS = {"new": ("новая", "positive"), "watch": ("наблюдаем", "warning"),
               "accepted": ("принята", "positive"), "done": ("сделано", "positive"),
               "dropped": ("отклонена", "danger")}


def _ideas_section(gi: dict) -> str:
    """Копилка идей бесплатного продвижения: полный список со статусами.

    В письме показываются только свежие идеи; здесь — все, с обоснованием,
    доказательством и датой. Статусы меняет руководитель (через сессию),
    история решений остаётся в файле.
    """
    if not gi.get("items"):
        return "<p class='muted'>Идей в копилке пока нет.</p>"
    rows = []
    for it in gi["items"]:
        label, cls = IDEA_STATUS.get(it.get("status", "new"), ("новая", "positive"))
        rows.append([f"<span class='chip {cls}'>{label}</span>",
                     f"<b>{it['title']}</b>", it.get("why", "—"),
                     it.get("evidence", "—"), it.get("added", "—")])
    return table(["Статус", "Идея", "Почему перспективно", "Доказательство", "Добавлена"], rows)


DIRECT_STATS = pathlib.Path("reports/seo/ppc/direct-stats.json")

ADS_TONE = {"grey": ("мало данных", "muted"), "ok": ("норма", "positive"),
            "warn": ("внимание", "warning"), "bad": ("проблема", "danger")}


def _ads_section(ads: dict) -> str:
    """Полный рекламный раздел: направления, все поисковые запросы, решения.

    Письмо показывает выжимку с маркерами; здесь — вся картина, включая
    каждый реальный поисковый запрос с расходом. Мусорные запросы помечены:
    это кандидаты в минус-слова, вносятся только после подтверждения
    руководителя (этап B — классификация и внесение через API).
    """
    if not ads.get("available"):
        return "<p class='muted'>Выгрузки Директа нет.</p>"
    head = (f"<p class='lede'>Кампания <b>{ads.get('campaign') or 'Директа'}</b>, данные за "
            f"{ru_date(ads['as_of'])}: за день {ads['day_spend']:.0f} ₽, "
            f"за 7 дней {ads['week']['spent']:.0f} из {num(ads['week']['limit'])} ₽ "
            f"недельного лимита, с запуска {ads['since_launch']['spent']:.0f} ₽ "
            f"({ads['since_launch']['days']} дн.)."
            + (f" Выгрузка отстаёт: ожидались данные за {ru_date(ads['expected_as_of'])}."
               if ads.get('stale') else "")
            + f" {ads.get('note', '')}</p>")
    rows = []
    for r in ads["rows"]:
        label, cls = ADS_TONE[r["verdict"]["tone"]]
        rows.append([f"<span class='chip {cls}'>{label}</span>",
                     f"<b>{r['label']}</b>",
                     f"{r['spend_day']:.0f} ₽", str(r["clicks_day"]),
                     f"{r['cpc']:.0f} ₽" if r["cpc"] else "—",
                     f"{r['spend_total']:.0f} ₽", str(r["clicks_total"]),
                     r["verdict"]["label"]])
    directions = table(["Оценка", "Направление", "Расход/день", "Клики/день",
                        "CPC", "Расход всего", "Клики всего", "Вердикт"], rows)
    decisions = "".join(
        f"<p><span class='chip {ADS_TONE[d['tone']][1]}'>требует решения</span> "
        f"{d['text']}</p>" for d in ads["decisions"])

    queries_html = "<p class='muted'>Запросов пока нет.</p>"
    if DIRECT_STATS.exists():
        stats = json.loads(DIRECT_STATS.read_text(encoding="utf-8"))
        junk_set = set(ads.get("junk", {}).get("queries", []))
        qrows = []
        for q in sorted(stats.get("queries", []),
                        key=lambda x: (-x["Cost"], -x["Clicks"], -x["Impressions"])):
            mark = ("<span class='chip danger'>минус-кандидат</span>"
                    if q["Query"] in junk_set else "")
            qrows.append([q["Date"], q["AdGroupName"], q["Query"],
                          str(q["Impressions"]), str(q["Clicks"]),
                          f"{q['Cost']:.2f} ₽", mark])
        queries_html = table(["Дата", "Группа", "Поисковый запрос", "Показы",
                              "Клики", "Расход", ""], qrows)
    return (f"{head}{directions}{decisions}"
            f"<h3>Реальные поисковые запросы</h3>{queries_html}")


def _evaluation_html(e: dict) -> str:
    """Полная оценка вердикт-движка эксперимента (задание 30.08.2026).

    Письмо показывает выжимку в контрольную дату; здесь — вся картина каждый
    день: окна, общие и matched-метрики, статистика, рекомендация и полный
    список страниц для расширения. Отсутствие оценки не ломает раздел.
    """
    ev = e.get("evaluation")
    if not ev:
        return ""
    vl = {"CONFIRMED": ("подтверждён", "positive"),
          "REJECTED": ("отвергнут: ухудшение", "danger"),
          "INCONCLUSIVE": ("вывод невозможен", "warning"),
          "INSUFFICIENT_DATA": ("мало данных", "")}
    label, cls = vl[ev["verdict"]]
    rl = {"EXPAND": "расширить", "REVERT": "откатить", "KEEP": "оставить",
          "EXTEND": "продлить наблюдение", "NEW_TEST": "новый тест"}
    rows = [["вердикт", f"<span class='chip {cls}'>{label}</span> — {ev['verdict_reason']}"],
            ["уверенность", {"HIGH": "высокая", "MEDIUM": "средняя",
                             "LOW": "низкая"}[ev["confidence"]]],
            ["рекомендация", f"{rl[ev['recommendation']]} — "
                             f"{ev['recommendation_detail'] or '—'}"]]
    if ev.get("summary_line"):
        # Оценки не-CTR типов (рост показов, запуск страниц) несут готовую
        # сводку: у них нет matched-набора и p-value по построению.
        rows.append(["сводка", ev["summary_line"]])
    w = ev.get("windows") or {}
    if w.get("experiment") and not w.get("baseline"):
        # impressions_growth / launch: baseline берётся из реестра или не
        # существует вовсе (новые страницы). Падение здесь было регрессией
        # #246 — ветка впервые исполнилась 02.09 на вердикте CONTENT-001.
        taint = " (захватывает день внедрения)" if w["experiment"].get("tainted") else ""
        rows.append(["окно после",
                     f"{w['experiment']['from']} — {w['experiment']['to']}{taint}"])
        base_reg = ((ev.get("metrics") or {}).get("baseline_registry") or {})
        if base_reg:
            rows.append(["база сравнения (реестр)",
                         f"{base_reg.get('impressions')} показов за "
                         f"{base_reg.get('days')} дн."])
        launch = ((ev.get("metrics") or {}).get("launch") or {})
        if launch:
            rows.append(["критерии запуска",
                         f"в выдаче {launch.get('pages_in_search')} из "
                         f"{launch.get('pages_total')} (нужно "
                         f"{launch.get('need_pages')}); "
                         f"{launch.get('weekly_impressions')} показов/нед "
                         f"(нужно {launch.get('need_weekly')})"])
    elif w.get("baseline"):
        mm, om = ev["matched_metrics"], ev["metrics"]
        stat = ev.get("statistical_result") or {}
        taint = " (захватывает день внедрения)" if w["experiment"].get("tainted") else ""
        fixed_b = " (фиксированное, полная выгрузка)" if w["baseline"].get("fixed") else ""
        fixed_e = " (фиксированное, полная выгрузка)" if w["experiment"].get("fixed") else ""
        rows += [
            ["окно до", f"{w['baseline']['from']} — {w['baseline']['to']}{fixed_b}"],
            ["окно после", f"{w['experiment']['from']} — {w['experiment']['to']}{taint}{fixed_e}"],
            ["кластер (все запросы)",
             f"до: {om['baseline']['impressions']} показов / {om['baseline']['clicks']} кликов; "
             f"после: {om['experiment']['impressions']} / {om['experiment']['clicks']}"],
            ["совпадающие запросы", str(mm["queries"])],
            ["CTR (matched)",
             f"{_p(stat.get('baseline_ctr'))} → {_p(stat.get('experiment_ctr'))} "
             f"(абс. {_p(stat.get('absolute_uplift'))}, "
             f"отн. {_p(stat.get('relative_uplift'), 0)})"],
            ["средняя позиция (matched), Δ",
             "—" if ev["position_delta"] is None else f"{ev['position_delta']:+.2f}"],
            ["p-value", "—" if stat.get("p_value") is None else f"{stat['p_value']:.4f}"],
        ]
        for pp in ev.get("per_page") or []:
            # Разбивка по страницам (перезапуск SEO-EXP-002): экспозиция и
            # CTR каждой страницы отдельно — страница без показов видна сразу.
            b, x = pp["baseline"], pp["experiment"]
            pos_b = "—" if b["avg_position"] is None else f"{b['avg_position']:.1f}"
            pos_x = "—" if x["avg_position"] is None else f"{x['avg_position']:.1f}"
            rows.append([f"страница {pp['page']}",
                         f"до: {b['impressions']} показов / {b['clicks']} кликов, "
                         f"CTR {_p(b['ctr'])}, позиция {pos_b}; "
                         f"после: {x['impressions']} / {x['clicks']}, CTR {_p(x['ctr'])}, "
                         f"позиция {pos_x}; совпадающих запросов {pp['matched_queries']}"])
    if ev.get("sample_quality"):
        rows.append(["качество выборки", "; ".join(ev["sample_quality"])])
    if ev.get("recommended_targets"):
        rows.append(["страницы для расширения", "<br>".join(ev["recommended_targets"])])
    if ev.get("requires_owner_decision"):
        rows.append(["статус", "<b>ТРЕБУЕТСЯ РЕШЕНИЕ ВЛАДЕЛЬЦА</b> — ответ в чате: "
                               f"KEEP/REVERT/EXPAND/EXTEND {ev['ticket']}"])
    return ("<h4>Оценка вердикт-движка (данные Яндекса)</h4>"
            + table(["Параметр", "Значение"], rows))


def _p(v, digits=2) -> str:
    return "—" if v is None else f"{v * 100:.{digits}f}%"


def _quality_groups(dq: dict) -> dict[str, list[dict]]:
    """Находки по классам: сбой / ограничение / правило (quality.CODE_KIND)."""
    groups: dict[str, list[dict]] = {"incident": [], "limit": [], "rule": []}
    for f in dq.get("findings") or []:
        groups.setdefault(quality_mod.finding_kind(f), []).append(f)
    return groups


def _quality_section(dq: dict) -> str:
    """Раздел «Качество данных» тремя блоками (решение руководителя 03.09.2026).

    Один список с одинаковым весом смешивал сбой дня, постоянное
    ограничение методики и правило подсчёта; из 16 строк за 03.09 сбоев
    было ноль. Теперь первый блок отвечает на вопрос «что сломалось
    сегодня», второй свёрнут и несёт дату и условие снятия, третий — про
    то, как считаются числа.
    """
    groups = _quality_groups(dq)
    inc = groups["incident"]

    def chip(level: str) -> str:
        cls = {"critical": "critical", "warning": "warning", "info": ""}[level]
        return f"<span class='chip {cls}'>{level}</span>"

    if inc:
        incidents = table(["Уровень", "Проверка", "Что обнаружено", "Следствие для отчёта"],
                          [[chip(f["level"]), f["title"], f["detail"],
                            f.get("effect_on_report") or "—"] for f in inc])
    else:
        incidents = ("<p class='callout'><b class='chip positive'>сбоев нет</b> "
                     "Все источники собраны, обновились и отдали данные; цели "
                     "заведены; выгрузки не отстали.</p>")
    limits = table(["Уровень", "Ограничение", "Что именно", "Следствие для отчёта",
                    "С какого дня", "Снимается, когда"],
                   [[chip(f["level"]), f["title"], f["detail"],
                     f.get("effect_on_report") or "—",
                     ru_date(f["since"]) if f.get("since") else "—",
                     f.get("lifted_when") or "—"] for f in groups["limit"]]) \
        if groups["limit"] else "<p class='muted'>Ограничений нет.</p>"
    rules = table(["Правило", "Как считается", "Следствие для отчёта"],
                  [[f["title"], f["detail"], f.get("effect_on_report") or "—"]
                   for f in groups["rule"]]) \
        if groups["rule"] else "<p class='muted'>Правил нет.</p>"
    n_inc, n_lim, n_rule = len(inc), len(groups["limit"]), len(groups["rule"])
    return (
        f"<p>Сбоев дня: <b>{n_inc}</b> · постоянных ограничений: <b>{n_lim}</b> · "
        f"правил подсчёта: <b>{n_rule}</b>. Статус данных отчёта считается "
        "только по сбоям.</p>"
        f"<h3>Сбои дня</h3>{incidents}"
        f"<details><summary><b>Постоянные ограничения методики ({n_lim})</b> — "
        "не сбои: у каждого названы дата и условие снятия</summary>"
        f"{limits}</details>"
        f"<details><summary><b>Правила подсчёта ({n_rule})</b> — как складываются "
        f"числа, чтобы их не сравнивали неверно</summary>{rules}</details>")


def _funnel_section(dq: dict) -> str:
    """Сводная воронка за общее окно — рядом с картой измерений."""
    fn = dq.get("funnel") or {}
    if not fn.get("available"):
        return ""
    cur, prev = fn.get("current") or {}, fn.get("previous") or {}
    rows = []
    for r in fn.get("rows") or []:
        d = r.get("delta")
        delta = "—" if d is None else (f"+{num(d)}" if d > 0 else num(d))
        rows.append([r["label"], r["source"], num(r["previous"]), num(r["current"]), delta])
    caveat = ("" if fn.get("complete") else
              "<p class='muted'>Окно неполное: нет дней " +
              ", ".join(fn.get("missing_dates") or []) + " — дельты не публикуются.</p>")
    return (f"<h3>Сводная воронка за общее окно {ru_date(cur.get('from'))}–"
            f"{ru_date(cur.get('to'))}</h3>"
            f"<p class='muted'>Против {ru_date(prev.get('from'))}–{ru_date(prev.get('to'))}. "
            f"{fn.get('note', '')}</p>{caveat}"
            + table(["Показатель", "Источник", "Было", "Стало", "Δ"], rows))


def _demand_section() -> str:
    """Покрытие спроса и разрывы: полные таблицы живут здесь, не в письме."""
    if not DEMAND_STATE.exists():
        return "<p class='muted'>Результатов исследования спроса нет.</p>"
    st = json.loads(DEMAND_STATE.read_text(encoding="utf-8"))
    cov, uni = st["coverage"], st["universe"]
    if not cov.get("available"):
        return "<p class='muted'>Спрос не измерен.</p>"
    meaning = {"page": "есть релевантная страница",
               "indexed": "страница участвует в поиске",
               "top10": "мы на первой странице выдачи",
               "clicks": "по запросу к нам приходят",
               "conversion_measured": "конверсия измеряется",
               "qualified_leads": "обращения подтверждены CRM"}
    levels = table(["Уровень", "Доля спроса", "Что означает"],
                   [[k, "нет данных" if v is None else f"{v:.1%}", meaning[k]]
                    for k, v in cov["levels"].items()])
    uncovered = table(["Кластер", "Спрос, показов/мес", "Класс", "Действие"],
                      [[u["cluster"], f"{u['demand']:,}".replace(",", " "),
                        f"<span class='chip'>{u['gap']}</span>", u["action"]]
                       for u in st["uncovered_top"]])
    opportunities = ""
    for o in st["opportunities"]:
        c = o["components"]
        opportunities += (
            f"<h3>{o['cluster']} — {o['recommended_action']}</h3>"
            f"<p>{o['gap_title']}. Спрос "
            f"{o['commercial_demand']:,} показов в месяц по {o['commercial_phrases']} "
            f"коммерческим фразам. Страница: {o['url'] or 'нет'}, "
            f"позиция {o['best_position'] or '—'}, тренд {o['trend']}.</p>"
            f"<p class='muted'>Балл {o['opportunity_score']} = спрос "
            f"{c['normalized_demand']} × интент {c['commercial_intent']} × разрыв "
            f"{c['coverage_gap']} × тренд {c['trend_factor']} × уверенность "
            f"{c['confidence']} / трудоёмкость {c['estimated_effort']}. "
            f"{o['confidence_note']}.</p>").replace(",", " ", 0)
    eff = st["efficiency"]
    q = st["quota"]
    economics = table(
        ["Показатель", "Значение"],
        [["вызовов всего", str(eff["calls_total"])],
         ["из них платных", str(eff["calls_paid"])],
         ["расход за месяц", f"{eff['cost_month_rub']:.2f} ₽"],
         ["остаток бюджета", f"{eff['remaining_budget_rub']:.2f} ₽"],
         ["попаданий в кэш", "—" if eff["cache_hit_rate"] is None
          else f"{eff['cache_hit_rate']:.1%}"],
         ["пустых ответов", "—" if eff["empty_response_rate"] is None
          else f"{eff['empty_response_rate']:.1%}"],
         ["стоимость 1000 уникальных фраз",
          f"{eff['cost_per_1000_unique_phrases_rub'] or '—'} ₽"],
         ["квота", f"{q['requests_per_hour']} запросов в час"],
         ["максимум расхода при этой квоте", f"{q['max_possible_spend_rub']:.0f} ₽/мес"],
         ["бюджет является ограничением",
          "да" if q["budget_is_binding"] else "нет — ограничивает квота"]])
    total = f"{uni['total_commercial_demand']:,}".replace(",", " ")
    return (f"<p>Измеренный покупательский спрос — {total} показов в месяц по "
            f"{uni['clusters']} кластерам. Считается по частотности коммерческих фраз, "
            f"а не по числу ключевых слов.</p>{levels}"
            f"<h3>Непокрытый коммерческий спрос</h3>{uncovered}"
            f"{_expansion_section(st)}"
            f"<h3>Возможности</h3>{opportunities}"
            f"<h3>Экономика исследования</h3>{economics}")


# Способ оплаты решает судьбу рекомендации: спрос без возможности заплатить
# картой сделкой не становится, поэтому колонка стоит рядом со спросом.
PAY_LABEL = {"card": "есть", "likely_card": "вероятно",
             "sales_only": "только через продажи", "unknown": "не определена",
             "unreachable": "сайт не открылся", "not_checked": "не проверялась"}


def _filter_rejected(exp: dict) -> dict:
    """Кандидаты, отклонённые руководителем, не показываются повторно (01.09)."""
    from report_v4 import rejected_vendor_brands
    import re as _re
    rej = rejected_vendor_brands()
    if not exp or not rej:
        return exp

    def norm(b):
        return " ".join(_re.findall(r"[a-zа-яё0-9]+", (b or "").lower()))
    out = dict(exp)
    out["items"] = [i for i in (exp.get("items") or []) if norm(i.get("brand")) not in rej]
    out["manual_check"] = [m for m in (exp.get("manual_check") or []) if norm(m) not in rej]
    return out


def _expansion_section(st: dict) -> str:
    """Каких вендоров добавить: спрос, оплата, трудоёмкость, готовая обвязка."""
    exp = _filter_rejected(st.get("vendor_expansion") or {})
    if not exp.get("available"):
        reason = exp.get("reason") or "данных пока нет"
        return (f"<h3>Каких вендоров добавить</h3>"
                f"<p class='muted'>{reason.capitalize()}.</p>")
    rows = [[r["brand"],
             "AI" if r["kind"] == "ai" else "классический",
             f"{r['commercial_demand']:,}".replace(",", " "),
             r.get("demand_confidence", "—"),
             PAY_LABEL.get(r["payment"]["verdict"], "—"),
             r["recommendation"], r["effort_note"],
             f"<code>{r['seo']['url']}</code>"]
            for r in exp["recommended"]]
    body = table(["Вендор", "Тип", "Спрос, показов/мес", "Достоверность",
                  "Оплата картой", "Рекомендация", "Трудоёмкость", "Адрес"], rows)
    notes = []
    if exp.get("low_confidence"):
        notes.append("Спрос требует ручного просмотра выдачи (имя бренда — "
                     "обычное английское слово): " + ", ".join(exp["low_confidence"]) + ".")
    if exp.get("needs_manual_check"):
        notes.append("Способ оплаты определить автоматически не удалось: "
                     + ", ".join(exp["needs_manual_check"]) + ".")
    note_html = "".join(f"<p class='muted'>{n}</p>" for n in notes)
    scaffold = ""
    for r in exp["recommended"][:3]:
        seo = r["seo"]
        scaffold += (
            f"<h4>{r['brand']} — <code>{seo['url']}</code></h4>"
            f"<p>{seo['title']}<br><span class='muted'>{seo['description']}</span></p>"
            f"<p class='muted'>Целевые запросы: "
            + ", ".join(f"«{ph['phrase']}» — {ph['frequency']}"
                        for ph in r["top_phrases"][:5])
            + f"<br>Разделы вопросов: " + "; ".join(seo["faq_topics"]) + "</p>")
    combined = f"{exp['combined_demand']:,}".replace(",", " ")
    return (f"<h3>Каких вендоров добавить</h3>"
            f"<p>Проверен спрос на {exp['candidates_measured']} зарубежных "
            f"разработчиков вне каталога; покупательский спрос подтверждён "
            f"у {exp['recommended_total']} — суммарно "
            f"{combined} показов в месяц. {exp['note']}</p>"
            + body + note_html
            + (f"<h4>SEO-обвязка для первых трёх</h4>{scaffold}" if scaffold else ""))


# ── Критичность разделов и оглавление ───────────────────────────────────────
#
# Разделы веб-отчёта сортируются по критичности: сначала то, что требует
# внимания сегодня, затем рабочие блоки, в конце справочные таблицы.
# Уровни: 3 — критично (сбой, просрочка, требуется решение), 2 — важно
# (есть находки или готовые возможности), 1 — рабочее, 0 — справочно.

SEVERITY_LABEL = {3: ("критично", "danger"), 2: ("важно", "warning"),
                  1: ("", ""), 0: ("справочно", "")}


def order_sections(sections: list[dict]) -> list[dict]:
    """Сортировка по критичности; внутри уровня сохраняется редакционный
    порядок (sorted устойчива)."""
    return sorted(sections, key=lambda s: -s["crit"])


def _navbar(sections: list[dict], date: str) -> str:
    """Липкая панель с меню разделов.

    Веб-отчёт — сотни килобайт: без постоянного доступа к списку разделов
    переход между ними означает прокрутку через все таблицы. Меню собрано на
    <details>, поэтому работает без скриптов и в почтовых просмотрщиках.
    """
    items = ""
    for s in sections:
        label, cls = SEVERITY_LABEL[s["crit"]]
        chip = f"<span class='chip {cls}'>{label}</span>" if label else ""
        items += f"<a href='#{s['id']}'>{s['title']}{chip}</a>"
    return (f"<div class='navbar'><div class='row'>"
            f"<span class='brand'>Growth Intelligence · {date}</span>"
            f"<details class='navmenu'><summary>Разделы</summary>"
            f"<div class='menu'><a href='#top'>В начало</a>{items}</div>"
            f"</details></div></div>")


def _toc(sections: list[dict]) -> str:
    items = ""
    for s in sections:
        label, cls = SEVERITY_LABEL[s["crit"]]
        chip = f" <span class='chip {cls}'>{label}</span>" if label else ""
        items += f"<li><a href='#{s['id']}'>{s['title']}</a>{chip}</li>"
    return (f"<nav class='toc'><h2>Содержание</h2>"
            f"<p class='muted desc'>Разделы отсортированы по критичности: "
            f"сверху — требующее внимания сегодня, ниже — рабочие и "
            f"справочные блоки.</p><ol>{items}</ol></nav>")


# Пороги ката. Крупный раздел развёрнутым в потоке вытесняет всё остальное:
# 20 000 знаков ≈ полсотни строк таблицы. Справочный сворачивается с меньшего
# объёма, но короткий блок под кат не прячется — экономить там нечего, а лишний
# клик раздражает.
CUT_CHARS = 20000
CUT_CHARS_REFERENCE = 6000

# Ядро отчёта: раздел не сворачивается независимо от объёма. Ради контроля
# экспериментов отчёт и открывают — прятать его за клик нельзя.
ALWAYS_OPEN = {"experiments"}


def _section_html(s: dict) -> str:
    """Раздел отчёта; объёмное и справочное содержимое — под катом.

    Развёрнутыми остаются разделы, требующие внимания сегодня, ядро отчёта и
    всё короткое. Под кат уходит объёмное — крупные таблицы и справочные блоки,
    которые читают выборочно. Заголовок, описание и пометка критичности видны
    всегда, поэтому оглавление и поиск по странице не страдают.
    """
    label, cls = SEVERITY_LABEL[s["crit"]]
    chip = f" <span class='chip {cls}'>{label}</span>" if label else ""
    head = (f"<section id=\"{s['id']}\"><h2>{s['title']}{chip}"
            f"<a class='backtop' href='#top'>наверх</a></h2>"
            f"<p class='muted desc'>{s['desc']}</p>")
    size = len(s["html"])
    big = size > CUT_CHARS
    reference = s["crit"] == 0 and size > CUT_CHARS_REFERENCE
    if s["id"] in ALWAYS_OPEN or not (big or reference):
        return head + s["html"] + "</section>"
    hint = "объёмный блок" if big else "справочный блок"
    return (head + f"<details class='cut'><summary>Показать раздел "
            f"<span class='hint'>— {hint}</span></summary>{s['html']}</details>"
            "</section>")


def _ru_num(value: float, digits: int = 1) -> str:
    """Дробное по-русски: запятой, как остальные числа отчёта."""
    return f"{value:.{digits}f}".replace(".", ",")


def _technical_section(tech: dict) -> str:
    """Таблица замеров и разбор просадок. Для веб-отчёта подробностей больше,
    чем в письме: здесь у читателя есть место и время."""
    if not tech.get("available"):
        tail = technical._no_data_tail(
            tech, "Последний удачный замер — {}.",
            "Последняя попытка {} не удалась.", "Замеров ещё не было.")
        # Причина — паспортная формулировка по коду; она идёт отдельной
        # фразой, иначе склеивается с соседним текстом в нечитаемую строку.
        why = tech.get("reason")
        why = f"Причина: {why}. " if why else ""
        return (f"<p><b>Данные недоступны.</b> {tail} {why}"
                f"Остальные разделы отчёта это не "
                f"затрагивает: скорость измеряется отдельным источником.</p>")

    label = {"green": "GREEN", "yellow": "YELLOW", "red": "RED"}[tech["level"]]
    rows = ""
    for p in tech.get("pages", []):
        lcp = f"{_ru_num(p['lcp_ms'] / 1000)} с" if p.get("lcp_ms") else "—"
        cls = _ru_num(p["cls"], 2) if p.get("cls") is not None else "—"
        field = p.get("field") or {}
        field_txt = (f"{_ru_num(field['lcp_ms'] / 1000)} с"
                     if field.get("lcp_ms") else "нет выборки")
        rows += (f"<tr><td>{p['page_type']}</td><td>{p['path']}</td>"
                 f"<td>{p.get('performance', '—')}</td><td>{lcp}</td><td>{cls}</td>"
                 f"<td>{p.get('seo', '—')}</td><td>{p.get('accessibility', '—')}</td>"
                 f"<td>{p.get('best_practices', '—')}</td><td>{field_txt}</td></tr>")

    # Первый замер сравнивать не с чем, и это надо сказать словами: строка
    # «сравнение с предыдущим замером нет» напечаталась 05.09.2026 в первом
    # же веб-отчёте контура.
    prev = tech.get("previous_date")
    compare = (f"сравнение с {prev}" if prev
               else "предыдущего замера для сравнения нет")
    head = (f"<p><b>{label}</b> · мобильная скорость главной "
            f"{tech.get('mobile_performance')}, худший балл выборки "
            f"{tech.get('worst_performance')}. Замер {tech.get('date')} "
            f"({'расширенный' if tech.get('mode') == 'weekly' else 'ежедневный'}), "
            f"{compare}.</p>")

    table = ("<div class='scroll'><table><tr><th>Тип</th><th>Адрес</th>"
             "<th>Скорость</th><th>LCP</th><th>CLS</th><th>SEO</th>"
             "<th>Доступность</th><th>Практики</th><th>Поле CrUX</th></tr>"
             + rows + "</table></div>")

    if tech.get("regressions"):
        problems = "".join(
            f"<li><b>{r['page_type']}</b> ({r['path']}): "
            f"{_technical_issue_text(r['issues'])}. Вероятная причина: "
            f"{r['cause']}. {r['priority']}.</li>"
            for r in tech["regressions"])
        table += f"<p><b>Что ухудшилось</b></p><ul>{problems}</ul>"
    else:
        table += "<p class='muted'>Значимых изменений к прошлому замеру нет.</p>"

    full = tech.get("last_full")
    if full:
        table += (f"<p class='muted'>Последняя расширенная проверка "
                  f"{full['date']}: {full['urls']} адресов — зелёных "
                  f"{full['green']}, жёлтых {full['yellow']}, красных "
                  f"{full['red']}.</p>")
    return head + table


def _technical_issue_text(issues: list[dict]) -> str:
    out = []
    for i in issues:
        if i["kind"] == "performance":
            out.append(f"скорость {i['was']} → {i['now']} ({i['delta']})")
        elif i["kind"] == "lcp":
            out.append(f"LCP {_ru_num(i['was'] / 1000)} с → "
                       f"{_ru_num(i['now'] / 1000)} с (+{i['delta_pct']} %)")
        elif i["kind"] == "cls":
            out.append(f"CLS {_ru_num(i['was'], 2)} → {_ru_num(i['now'], 2)}")
    return "; ".join(out)


def _loop_section(lh: dict) -> str:
    """Работа конвейера: каждый контур подтверждён артефактом с датой."""
    if not lh.get("available"):
        return "<p class='muted'>Реестра исполнения контуров нет (loop-health).</p>"
    rows = []
    for r in lh.get("contours", []):
        state = ("<span class='chip critical'>просрочен</span>" if r["overdue"]
                 else "<span class='chip positive'>в срок</span>")
        late = (f"{r['days_late']} дн." if r.get("days_late") else "—")
        rows.append([state, f"<b>{r['label']}</b>", r["cadence"],
                     r["last_run"] or "—", r["expected_since"],
                     late if r["overdue"] else "—",
                     r.get("note") or ""])
    return table(["Статус", "Контур", "Каденция", "Последний прогон",
                  "Ожидается не старше", "Просрочка", "Примечание"], rows)


def _money_section(mr: dict) -> str:
    """Money-запросы: коммерческий интент в полосе позиций 4–20."""
    if not mr.get("available"):
        return f"<p class='muted'>{mr.get('reason', 'Данных нет')}.</p>"
    rows = [[f"<b>{i['query']}</b>",
             "Яндекс" if i["engine"] == "yandex" else "Google",
             num(i["impressions"]), str(i["clicks"]),
             str(i["position"]), i["zone_label"], i["recommended_action"]]
            for i in mr["items"]]
    body = table(["Запрос", "Система", "Показы", "Клики", "Позиция",
                  "Зона", "Типовое действие"], rows)
    return (f"<p class='muted desc'>{mr.get('note', '')}. "
            f"Рассмотрено запросов: {mr.get('considered')}.</p>" + body)


def _cannibal_section(cb: dict) -> str:
    """Каннибализация: расщепление запроса между страницами и смены лидера."""
    if not cb.get("available"):
        return f"<p class='muted'>{cb.get('reason', 'Данных нет')}.</p>"
    if not cb.get("items"):
        return f"<p class='muted'>{cb.get('reason', 'Находок нет')}.</p>"
    rows = []
    for i in cb["items"]:
        pages = "<br>".join(
            f"{p['page']} — {p['share']:.0%}"
            + (f", позиция {p['avg_position']}" if p['avg_position'] else "")
            for p in i["pages"])
        chip = ("<span class='chip warning'>нестабильно</span>"
                if i["verdict"] == "unstable"
                else "<span class='chip'>расщепление</span>")
        rows.append([chip, f"<b>{i['query']}</b>", num(i["impressions"]),
                     pages, f"{i['leader_changes']} за {i['days_observed']} дн.",
                     i["recommended_action"]])
    body = table(["Вердикт", "Запрос", "Показы", "Страницы и доли",
                  "Смен лидера", "Предлагаемое действие"], rows)
    return (f"<p class='muted desc'>{cb.get('note', '')}. Выгрузка от "
            f"{ru_date(cb.get('as_of'))}.</p>" + body)


def _mismatch_section(mm: dict) -> str:
    """Mismatch: коммерческий запрос, который ведёт не на коммерческую страницу."""
    if not mm.get("available"):
        return f"<p class='muted'>{mm.get('reason', 'Данных нет')}.</p>"
    if not mm.get("items"):
        return f"<p class='muted'>{mm.get('reason', 'Находок нет')}.</p>"
    rows = [[f"<b>{i['query']}</b>", num(i["impressions"]),
             f"{i['page']} <span class='chip'>{i['page_type']}</span>",
             f"{i['share']:.0%}",
             str(i["avg_position"] or "—"),
             i["recommended_action"]]
            for i in mm["items"]]
    body = table(["Запрос", "Показы", "Куда ведёт", "Доля", "Позиция",
                  "Предлагаемое действие"], rows)
    return (f"<p class='muted desc'>{mm.get('note', '')}. Выгрузка от "
            f"{ru_date(mm.get('as_of'))}.</p>" + body)


def _zero_section(zi: dict, snap: dict) -> str:
    """Инвентарь и страницы без показов + Index Efficiency по системам.

    Две доли Google — «в индексе» (URL Inspection) и «с показами» (Search
    Analytics) — называются раздельно: до сенсора покрытия одна подменяла
    другую, и 3,9% страниц с показами читались как провал ранжирования, тогда
    как карточки Google просто не знал.
    """
    if not zi.get("available"):
        return f"<p class='muted'>{zi.get('reason', 'Данных нет')}.</p>"
    idx = (snap.get("yandex") or {}).get("indexation") or {}
    y_indexed = idx.get("indexed_urls")
    total = zi["inventory_total"]
    ig = zi.get("index_google") or {}
    iy = zi.get("index_yandex") or {}
    if ig.get("available"):
        g_txt = (f"Google — в индексе <b>{num(ig['indexed'])}</b> "
                 f"({ig['coverage_indexed']:.1%}), с показами "
                 f"<b>{zi['with_impressions']}</b> ({zi['coverage_google']:.1%})")
    else:
        g_txt = (f"Google — <b>{zi['with_impressions']}</b> страниц с показами "
                 f"({zi['coverage_google']:.1%}); индекс по страницам не измерен")
    if iy.get("available"):
        note = zero_mod.yandex_slice_note(iy, y_indexed)
        y_txt = (f"Яндекс — в поиске <b>{num(iy['in_search'])}</b> страниц "
                 f"инвентаря ({iy['coverage']:.1%})"
                 + (f", по сводке хоста {num(y_indexed)}" if y_indexed else "")
                 + (f" ({note})" if note else ""))
    elif y_indexed and total:
        y_txt = (f"Яндекс — <b>{num(y_indexed)}</b> страниц в поиске по сводке "
                 f"хоста ({y_indexed / total:.1%}); по страницам не измерено")
    else:
        y_txt = "Яндекс — число страниц в поиске не измерено"
    eff = (
        f"<p>Инвентарь sitemap: <b>{num(total)}</b> URL (выгрузка "
        f"{ru_date(zi['as_of'])}). Index Efficiency: {g_txt}; {y_txt}. "
        "Если каталог растёт быстрее этих долей — рост SKU превращается "
        "в SEO-инфляцию.</p>")
    causes = ""
    if ig.get("available") and zi.get("by_cause"):
        from inventory import GOOGLE_CLASS_LABEL
        parts = ", ".join(
            f"{GOOGLE_CLASS_LABEL.get(k, k)} — {v}"
            for k, v in sorted(zi["by_cause"].items(), key=lambda kv: -kv[1]))
        causes += (f"<p><b>Причины по Google</b> (URL Inspection от "
                   f"{ru_date(ig.get('as_of'))}): {parts}.</p>")
    if iy.get("available"):
        ex = iy.get("excluded_by_reason") or {}
        ex_txt = (", ".join(f"{k} — {v}" for k, v in sorted(
            ex.items(), key=lambda kv: -kv[1])) if ex else "нет")
        causes += (f"<p><b>Яндекс по страницам инвентаря</b> (выборки Вебмастера "
                   f"от {ru_date(iy.get('as_of'))}): в поиске "
                   f"{num(iy['in_search'])}, исключено — {ex_txt}, без "
                   f"зафиксированной причины — "
                   f"{(iy.get('by_status') or {}).get('absent', 0)}.</p>")
    types = ", ".join(f"{k}: {v}" for k, v in sorted(
        zi["by_type"].items(), key=lambda kv: -kv[1]))
    rows = [[f"<code>{i['path']}</code>",
             f"<span class='chip'>{i['page_type']}</span>",
             (f"≥{i['known_days']}" if i["known_days_is_floor"]
              else str(i["known_days"] if i["known_days"] is not None else "—"))
             + " дн.",
             f"G: {i['google_index']['label']}"
             + (f" (обход {i['google_index']['last_crawl']})"
                if i["google_index"].get("last_crawl") else "")
             + f" · Я: {i['yandex_index']['label']}",
             i["verdict"]]
            for i in zi["items"]]
    body = table(["Страница", "Тип", "В инвентаре", "Индекс", "Вердикт"], rows)
    more = ("" if zi["zero_total"] <= len(zi["items"]) else
            f"<p class='muted'>Показаны {len(zi['items'])} из "
            f"{zi['zero_total']}; полный разбор — партиями.</p>")
    return (eff + causes
            + f"<p class='muted desc'>Без показов: {num(zi['zero_total'])} "
              f"(по типам — {types}); молодых страниц пропущено: "
              f"{zi['young_skipped']}. {zi['note']}.</p>"
            + body + more)


def _lifecycle_section(lc: dict) -> str:
    """Жизненный цикл страниц: new / gaining / stable / declining."""
    if not lc.get("available"):
        return f"<p class='muted'>{lc.get('reason', 'Данных нет')}.</p>"
    if not lc.get("items"):
        return f"<p class='muted'>{lc.get('reason', 'Находок нет')}.</p>"
    counts = lc.get("counts") or {}
    summary = " · ".join(f"{STATUS_CHIP.get(k, k)}: {v}"
                         for k, v in sorted(counts.items()))
    chip_cls = {"declining": "danger", "gaining": "positive", "new": "",
                "stable": ""}
    rows = [[f"<span class='chip {chip_cls[i['status']]}'>"
             f"{STATUS_CHIP[i['status']]}</span>",
             f"<code>{i['page']}</code>",
             f"<span class='chip'>{i['page_type']}</span>",
             num(i["total"]), str(i["prev7"]), str(i["last7"]),
             ru_date(i["first_active"])]
            for i in lc["items"]]
    body = table(["Статус", "Страница", "Тип", "Показы за окно",
                  "Пред. неделя", "Эта неделя", "Первая активность"], rows)
    return (f"<p class='muted desc'>Страниц с показами: {lc['pages_total']} "
            f"({summary}). {lc.get('note', '')}.</p>" + body)


STATUS_CHIP = {"new": "новая", "gaining": "растёт", "stable": "стабильна",
               "declining": "снижается"}

SERP_KIND = {"ours": "мы", "competitor": "конкурент",
             "marketplace": "маркетплейс", "info": "форумы/медиа",
             "other": "прочие"}


def _serp_section(sp: dict) -> str:
    """SERP Яндекса: наша фактическая позиция, конкуренты, слабые выдачи."""
    if not sp.get("available"):
        return f"<p class='muted'>{sp.get('reason', 'Данных нет')}.</p>"
    head = (f"<p>Срез от {ru_date(sp['as_of'])}: {sp['queries_total']} "
            f"запросов ядра. Мы в топ-10 по <b>{sp['ours_in_top10']}</b>; "
            f"слабых выдач (лёгкая точка входа) — <b>{sp['weak_serps']}</b>."
            + (f" Сравнение с {ru_date(sp['prev_date'])}." if sp.get("prev_date")
               else " Предыдущего среза нет — сравнения нет.")
            + "</p>")
    doms = table(["Домен", "Появлений в топ-10", "Кто это"],
                 [[d["domain"], str(d["hits"]),
                   SERP_KIND.get(d["kind"], d["kind"])]
                  for d in sp["top_domains"]])
    rows = []
    for i in sp["items"][:25]:
        moves = ""
        if i["entered_top10"] or i["left_top10"]:
            moves = ("вошли: " + ", ".join(i["entered_top10"][:3])
                     if i["entered_top10"] else "")
            if i["left_top10"]:
                moves += ("; " if moves else "") + \
                         "выпали: " + ", ".join(i["left_top10"][:3])
        rows.append([
            f"<b>{i['query']}</b>",
            str(i["our_position"]) if i["our_position"] else "нет в топ-20",
            ("<span class='chip warning'>слабая</span>" if i["weak"]
             else f"{i['weak_share']:.0%}"),
            ", ".join(d["domain"] for d in i["top3"]),
            moves or "—"])
    body = table(["Запрос", "Наша позиция", "Слабость выдачи", "Топ-3",
                  "Движения в топ-10"], rows)
    return (head + f"<h3>Кто занимает топ по нашим запросам</h3>{doms}"
            + f"<h3>По запросам</h3>"
              f"<p class='muted desc'>{sp.get('note', '')}.</p>" + body)


def _gap_section(gap: dict) -> str:
    """Разрыв Яндекс ↔ Google по одному ядру: где Google нас не показывает."""
    if not gap.get("available"):
        return f"<p class='muted'>{gap.get('reason', 'Данных нет')}.</p>"
    ya_only = gap["yandex_top10_google_absent"]
    g_only = gap["google_top10_yandex_absent"]
    head = (f"<p>Сопоставлено {gap['queries_compared']} запросов ядра "
            f"(Яндекс от {ru_date(gap['as_of_yandex'])}, Google от "
            f"{ru_date(gap['as_of_google'])}). В топ-10 обеих систем — "
            f"<b>{gap['both_top10']}</b>; Яндекс топ-10, в Google нет — "
            f"<b>{len(ya_only)}</b>; Google топ-10, в Яндексе нет — "
            f"<b>{len(g_only)}</b> («нет» — нет в собранной выдаче: Google "
            f"глубиной {gap.get('google_depth', 10)}, Яндекс — 20).</p>"
            f"<p class='muted desc'>{gap.get('note', '')}. Первая группа — "
            f"главный вопрос по Google: страница релевантна (Яндекс её "
            f"ранжирует), значит дело в индексации, авторитете домена или "
            f"конкурентоспособности страницы именно в Google.</p>")
    body = ""
    if ya_only:
        body += "<h3>Яндекс топ-10, в Google нет</h3>" + table(
            ["Запрос", "Позиция в Яндексе", "Кто в топ-3 Google"],
            [[f"<b>{i['query']}</b>", str(i["yandex_position"]),
              ", ".join(d for d in i["google_top3"] if d)]
             for i in ya_only[:25]])
    if g_only:
        body += "<h3>Google топ-10, в Яндексе нет</h3>" + table(
            ["Запрос", "Позиция в Google", "Кто в топ-3 Яндекса"],
            [[f"<b>{i['query']}</b>", str(i["google_position"]),
              ", ".join(d for d in i["yandex_top3"] if d)]
             for i in g_only[:25]])
    return head + body


def embed_png(path: pathlib.Path) -> str:
    """PNG внутрь страницы: отчёт открывается по ссылке, а не только из репозитория."""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "<p class='muted'>Нет данных.</p>"
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<div class='scroll'><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>"


WINDOW = daily_windows.WINDOW_DAYS
KPI_SOURCE = {"yandex": "yandex", "google": "google", "traffic": "metrika",
              "commercial": "metrika"}
PILL_STATE = {
    "positive": "good", "mixed": "warn", "negative": "crit", "stable": "good",
    "verified": "good", "limited": "warn", "degraded": "crit", "none": "neutral",
    "required": "crit", "unknown": "neutral",
}


def _dates_from(start: str | None, n: int) -> list[str]:
    if not start:
        return [f"д{i + 1}" for i in range(n)]
    d0 = dt.date.fromisoformat(start)
    return [(d0 + dt.timedelta(days=i)).isoformat() for i in range(n)]


def _week_chart(kpi: dict, w: int = 620, h: int = 190) -> str:
    """Неделя к неделе по дням: текущее окно цветом источника, прошлое — серым."""
    tail = list(kpi.get("sparkline") or [])
    if len(tail) < WINDOW * 2:
        return ""
    prev, cur = tail[:WINDOW], tail[WINDOW:WINDOW * 2]
    start = kpi.get("sparkline_from")
    cur_dates = _dates_from(
        (dt.date.fromisoformat(start) + dt.timedelta(days=WINDOW)).isoformat() if start else None,
        WINDOW)
    labels = [ru_date(d) if start else d for d in cur_dates]
    colour = kit.series_color(KPI_SOURCE.get(kpi.get("key", ""), "yandex"))
    return kit.line_chart(
        [{"name": "эта неделя", "values": cur, "color": colour},
         {"name": "прошлая неделя", "values": prev, "context": True}],
        labels, w=w, h=h, ticks=4, area=True, title=kpi["label"])


def _kpi_panel(k: dict, snap: dict) -> str:
    """Углубление плитки: динамика по дням и топ сущностей показателя."""
    chart = _week_chart(k)
    left = (f"<div><h4>{k['label']}: динамика по дням</h4>"
            f"<p class='kit-hint'>{k['interpretation']}</p>"
            f"<p class='kit-hint'>{k['period']} · {k['source']} · серым — предыдущее окно</p>"
            + (chart or "<p class='kit-muted'>Дневного ряда для этого показателя нет — "
                        "витрина источника не заполнена.</p>") + "</div>")
    right = ""
    if k.get("key") == "yandex" and (snap["yandex"].get("entities") or []):
        ents = sorted(snap["yandex"]["entities"], key=lambda e: -e["impressions"])[:8]
        top = ents[0]["impressions"] or 1
        rows = [{"q": f"{e['entity_id']}", "imp": kit.bar_cell(e["impressions"], top),
                 "pos": kit.pos_cell(e.get("average_position"))} for e in ents]
        right = ("<div><h4>Запросы с наибольшими показами</h4>"
                 "<p class='kit-hint'>окно источника, выборка Вебмастера</p>"
                 + kit.dense_table([{"key": "q", "label": "Запрос"},
                                    {"key": "imp", "label": "Показы", "align": "right"},
                                    {"key": "pos", "label": "Позиция", "align": "right"}],
                                   rows, sortable=False) + "</div>")
    elif k.get("key") == "google" and (snap["google"].get("pages") or []):
        pages = sorted(snap["google"]["pages"], key=lambda e: -e["impressions"])[:8]
        top = pages[0]["impressions"] or 1
        rows = [{"p": e["entity_id"], "imp": kit.bar_cell(e["impressions"], top,
                                                           kit.series_color("google")),
                 "pos": kit.pos_cell(e.get("average_position"))} for e in pages]
        right = ("<div><h4>Страницы с наибольшими показами</h4>"
                 "<p class='kit-hint'>окно Search Console</p>"
                 + kit.dense_table([{"key": "p", "label": "Страница"},
                                    {"key": "imp", "label": "Показы", "align": "right"},
                                    {"key": "pos", "label": "Позиция", "align": "right"}],
                                   rows, sortable=False) + "</div>")
    else:
        right = (f"<div><h4>Как читать</h4><p class='kit-hint'>{k['interpretation']}</p>"
                 f"<p class='kit-hint'>достоверность: {k['confidence']}"
                 + (f" · {k['relative_note']}" if k.get("relative_note") else "") + "</p></div>")
    return left + right


def _owner_desk_html(b: dict) -> str:
    """Предложения на столе руководителя под строкой «От вас».

    Плашка шапки их считает («ОТ ВАС: 2 предложения»), а строка ниже говорила
    «Срочных решений нет» и на этом заканчивалась: 09.09.2026 страница
    противоречила сама себе в двух соседних строках. В письме этот блок есть
    с 31.08.2026, на странице его не было.
    """
    desk = b.get("owner_desk") or []
    if b.get("user_action_required") or not desk:
        return ""
    items = "".join(f"<li>{d}</li>" for d in desk)
    return (f"<div class='desk'><b>На вашем столе "
            f"{kit.esc(counted(len(desk), 'предложение', 'предложения', 'предложений'))}"
            f"</b><ul>{items}</ul></div>")


def _kpi_dashboard(b: dict, snap: dict) -> str:
    """Пульт: четыре плитки со спарклайнами, клик раскрывает углубление."""
    tiles, panels = [], []
    for i, k in enumerate(b["kpis"]):
        delta = k["delta"] or ""
        if k.get("relative"):
            delta = f"{delta} {k['relative']}".strip()
        colour = kit.series_color(KPI_SOURCE.get(k.get("key", ""), "yandex"))
        tiles.append(kit.stat_tile(
            k["label"], k["value"], k["unit"], delta or None, k.get("delta_dir"),
            spark=k.get("sparkline"), color=colour, note=k["interpretation"],
            meta=f"{k['period']} · {k['source']} · достоверность: {k['confidence']}",
            key=k["key"], active=(i == 0), muted=bool(k["muted"])))
        panels.append(kit.panel(k["key"], _kpi_panel(k, snap), active=(i == 0)))
    return kit.dash(kit.kpi_row(tiles), "".join(panels),
                    title="Четыре показателя руководителя",
                    period="клик по плитке раскрывает динамику и состав")


def _status_dashboard(b: dict) -> str:
    """Светофор контуров: статусы шапки письма и здоровье данных."""
    rows = [{"state": PILL_STATE.get(p["state"], "neutral"), "name": p["label"],
             "value": "", "comment": p["text"]} for p in b["pills"]]
    h = b["health"]
    rows.append({"state": {"positive": "good", "warning": "warn", "danger": "crit"}[h["colour"]],
                 "name": "ЗДОРОВЬЕ ДАННЫХ", "value": "",
                 "comment": f"<b>{PILL_LABEL[h['status']]}</b> — {h['detail']}"})
    body = kit.status_rows(rows, head=False)
    return kit.dash("", body, title="Состояние контуров", period=b["sources_line"])


def _daily_multiples(snap: dict) -> str:
    """Малые кратные: дневные ряды всех источников на одной оси времени."""
    daily = snap.get("daily") or {}
    cards, labels = [], None
    names = {("yandex", "impressions"): "Показы, Яндекс", ("yandex", "clicks"): "Клики, Яндекс",
             ("gsc", "impressions"): "Показы, Google", ("gsc", "clicks"): "Клики, Google",
             ("metrika", "visits_organic"): "Визиты из поиска",
             ("metrika", "goal_reaches_organic"): "Цели из поиска"}
    for (source, metric), title in names.items():
        blk = daily.get(source) or {}
        win = (blk.get("windows") or {}).get(metric)
        if not blk.get("available") or not win or len(win.get("tail") or []) < WINDOW * 2:
            continue
        tail = win["tail"]
        cur = tail[WINDOW:WINDOW * 2]
        if labels is None:
            labels = [ru_date(d) for d in _dates_from(win["current"]["from"], WINDOW)]
        cards.append({"title": title, "values": cur, "prev": tail[:WINDOW],
                      "color": kit.series_color(source),
                      "caption": f"неделя {num(win['current']['sum'])}"
                                 + (f" · {signed(win['delta'])}" if win.get("delta") is not None else "")})
    if not cards:
        return ""
    return kit.dash("", kit.small_multiples(cards, labels),
                    title="Динамика по дням: все источники",
                    period="текущее окно цветом источника, предыдущее — серым")


def _heat_dashboard(snap: dict, date: str) -> str:
    """Календарь-теплокарта показов за четыре недели: Яндекс из витрины, иначе Google."""
    end = dt.date.fromisoformat(date) - dt.timedelta(days=daily_windows.LAG_DAYS["yandex"])
    dates = [(end - dt.timedelta(days=27 - i)).isoformat() for i in range(28)]
    store = daily_windows.load_series("yandex")
    series = ((store or {}).get("series") or {}).get("impressions") or {}
    title, unit = "Показы в Яндексе по дням", "показов"
    if not series:
        g = {d["date"]: d.get("impressions") for d in (snap["google"].get("daily") or [])
             if d.get("date")}
        if not g:
            return ""
        series, title = g, "Показы в Google по дням"
    values = [series.get(d) for d in dates]
    if sum(v is not None for v in values) < 7:
        return ""
    return kit.dash("", kit.heatmap(dates, values, unit),
                    title=title, period=f"{ru_date(dates[0])} – {ru_date(dates[-1])} · "
                                        f"пустая клетка — день без данных")


def _live_charts(b: dict) -> str:
    """Графики письма в живом виде: тренд показателя и вклад драйверов."""
    parts = []
    for k in b["kpis"]:
        chart = _week_chart(k)
        if chart:
            parts.append(f"<h3>{k['label']} по дням</h3>{chart}")
            break
    for db in b["driver_blocks"]:
        if not db.get("available") or not db.get("rows"):
            continue
        rows = []
        for r in db["rows"]:
            try:
                d = float(str(r["delta"]).replace("−", "-").replace("+", "").replace("\u202f", ""))
            except ValueError:
                continue
            rows.append({"entity": r["entity"], "delta": d,
                         "share_of_total_delta": float(str(r["share"]).rstrip("%")) / 100})
        if rows:
            parts.append(f"<h3>Вклад страниц: {db['engine']}</h3>"
                         f"<p class='muted'>{db['window']}</p>{kit.delta_bars(rows)}")
    return "".join(parts)


def _entity_table(entities: list[dict], kind: str, colour: str, limit: int) -> str:
    """Таблица-дашборд запросов или страниц: бар показов, позиция, статус."""
    ents = sorted(entities or [], key=lambda e: -e["impressions"])[:limit]
    if not ents:
        return "<p class='muted'>Строк нет.</p>"
    top = ents[0]["impressions"] or 1
    rows = []
    for e in ents:
        rows.append({
            "e": e["entity_id"],
            "imp": kit.bar_cell(e["impressions"], top, colour),
            "clicks": {"html": num(e["clicks"]), "sort": e["clicks"]},
            "ctr": {"html": pct(e.get("ctr"), 2), "sort": e.get("ctr") or 0},
            "pos": kit.pos_cell(e.get("average_position")),
            "intent": kit.chip(e["intent"], "neutral") if e.get("intent") else "",
            "conf": kit.chip(e.get("confidence", ""), "good" if e.get("confidence") == "sufficient"
                             else "neutral") if e.get("confidence") else "",
        })
    cols = [{"key": "e", "label": kind},
            {"key": "imp", "label": "Показы", "align": "right"},
            {"key": "clicks", "label": "Клики", "align": "right"},
            {"key": "ctr", "label": "CTR", "align": "right"},
            {"key": "pos", "label": "Позиция", "align": "right"}]
    if any(r["intent"] for r in rows):
        cols.append({"key": "intent", "label": "Интент"})
    if any(r["conf"] for r in rows):
        cols.append({"key": "conf", "label": "Достоверность"})
    return kit.dense_table(cols, rows)


def build_html(b: dict, snap: dict, dq: dict, date: str) -> str:
    yx, g = snap["yandex"], snap["google"]

    # Таблицы-дашборды KPI-kit: бар показов, позиция, чипы интента и
    # достоверности, сортировка по любому столбцу.
    queries = _entity_table(yx.get("entities"), "Запрос", kit.series_color("yandex"), 100)
    pages = _entity_table(g.get("pages"), "Страница", kit.series_color("google"), 50)
    gq = _entity_table(g.get("entities"), "Запрос", kit.series_color("google"), 50)

    mmap = table(
        ["Источник", "Показатель", "Сущность", "Охват", "Период", "Сравнимо с", "Почему различается"],
        [[m["source"], m["metric"], m["entity"], m["scope"], m["period"],
          ", ".join(m["comparable_with"]) or "—", m["difference_explanation"]]
         for m in dq.get("measurement_map", [])])

    board = table(
        ["Задача", "Владелец", "Стадия", "Статус", "Срок", "Артефакт"],
        [[f"<a href='{r['artifact_url']}'>{r['task']}</a>", r["owner"], r["stage"],
          r["status"], r["due"], r.get("artifact") or "—"] for r in b["board"]])

    exps = ""
    for e in b["experiments"]:
        interim_line, interim_caveat = _exp_interim_line(e)
        exps += (
            f"<h3>{e['ticket']} · {e['id']}</h3>"
            f"<p><b>Гипотеза.</b> {e['hypothesis']}</p>"
            f"<p><b>Изменение.</b> {e['treatment']}</p>"
            f"<p><b>Совместное внедрение.</b> {e['combined_note']}</p>"
            + table(["Показатель", "Значение"], [
                ["запуск", ru_date_full(e["start"])],
                ["прошло дней", str(e["days_elapsed"])],
                ["минимальная экспозиция", e["minimum_exposure"]],
                ["страниц всего", str(e["pages_total"])],
                ["новый вариант на сайте", _exp_implementation_line(e)],
                ["обновление сниппета в выдаче", _exp_serp_line(e)],
                ["показов накоплено (оценка)", _exp_exposure_line(e)],
                ["переходов накоплено", num(e["clicks_since_deploy"])],
                ["старый → новый (предварительно)",
                 interim_line
                 + (f"; оговорки: {interim_caveat}" if interim_caveat else "")],
                ["целевой показатель", e["primary_metric"]],
                ["достоверность", e["confidence"]],
                ["следующая проверка", ru_date_full(e["next_review"]) if e.get("next_review") else "вехи пройдены"],
                ["вывод", f"{VERDICT_LABEL[e['verdict']]} — {e['verdict_reason']}"]]
               + ([["решение по эксперименту", e["owner_decision"]]]
                  if e.get("owner_decision") else []))
            + _evaluation_html(e))

    drivers = ""
    for db in b["driver_blocks"]:
        drivers += (f"<h3>{db['engine']}</h3><p class='muted'>{db['window']}</p>"
                    f"<p>{db['text']}</p>"
                    + table(["Адрес", "Изменение", "Доля изменения", "Состояние"],
                            [[r["entity"], r["delta"], r["share"], r["state"] or "—"]
                             for r in db["rows"]]))

    opp = table(
        ["Кластер", "Доказательство", "Потенциал", "Достоверность", "Действие", "Решение к"],
        [[o["cluster"], o["evidence"], o["potential"], o["confidence"],
          o["recommended_action"],
          ru_date_full(o["decision_date"]) if o.get("decision_date") else "срок не назначен"]
         for o in b["opportunities"]["items"]])
    held = (b["opportunities"].get("held_by_experiment") or [])
    if held:
        # Кластер под замером в радар не попадает: рекомендованная правка
        # обнулила бы чужой эксперимент. Молча его выкидывать нельзя —
        # отсутствие кластера читалось бы как отсутствие спроса.
        opp += ("<p class='muted'>Придержаны до вердикта эксперимента: "
                + ", ".join(f"{h['cluster']} ({h['experiment']})" for h in held)
                + ". Правка их страниц сейчас обнулит замер.</p>")

    # Графики письма — в живом виде (KPI-kit, наведение показывает значения);
    # таймлайн эксперимента остаётся картинкой письма.
    charts = _live_charts(b) + "".join(
        f"<figure><img src='{embed_png(BASE / 'charts' / f'{date}-{n}.png')}' alt='{c}'>"
        f"<figcaption>{c}</figcaption></figure>"
        for n, c in (("experiment", "Ход эксперимента"),)
        if (BASE / "charts" / f"{date}-{n}.png").exists())

    # Токены светлой темы объявлены на голом :root, тёмные — отдельно для
    # системной настройки и для явного выбора: у зрителя три состояния, и цвет,
    # объявленный только внутри media-блока, в неотмеченном состоянии не сработает.
    css = kit.kit_css() + """
    /* Токены страницы — псевдонимы палитры KPI-kit: одна тема на письмо,
       веб-отчёт и конкурентную разведку; тёмная тема приходит из kit. */
    :root{
      --ground:var(--kit-plane); --surface:var(--kit-surface); --ink:var(--kit-ink);
      --muted:var(--kit-muted); --line:var(--kit-hair); --line-strong:var(--kit-hair2);
      --brand:var(--kit-accent); --positive:var(--kit-good); --warning:var(--kit-warn);
      --warning-bg:var(--kit-warn-soft); --danger:var(--kit-crit); --info:var(--kit-s1);
      --chip:var(--kit-surface2);
    }
    *{box-sizing:border-box}
    body{
      margin:0; background:var(--ground); color:var(--ink);
      font:400 16px/1.6 'Raleway',system-ui,-apple-system,'Segoe UI',sans-serif;
      -webkit-font-smoothing:antialiased;
    }
    .wrap{max-width:1080px;margin:0 auto;padding:0 24px 96px}
    header{padding:40px 0 20px}
    h1{
      font-size:clamp(26px,3.4vw,36px); line-height:1.15; margin:0;
      letter-spacing:-.02em; text-wrap:balance;
    }
    .sub{color:var(--muted);font-size:14.5px;margin-top:6px}
    .desk{margin:10px 0 0;font-size:15px;line-height:1.55}
    .desk ul{margin:4px 0 0;padding-left:20px}
    .statusbar{
      position:sticky; top:0; z-index:5; background:var(--ground);
      border-bottom:1px solid var(--line); padding:12px 0; margin-bottom:8px;
      display:flex; flex-wrap:wrap; gap:8px; align-items:center;
    }
    .pill{
      font:500 12.5px/1 'Raleway',system-ui,sans-serif;
      letter-spacing:.04em; text-transform:uppercase;
      border:1px solid var(--line-strong); border-radius:999px; padding:6px 11px;
      color:var(--muted); white-space:nowrap;
    }
    .pill.positive{color:var(--positive);border-color:var(--positive)}
    .pill.warning{color:var(--warning);border-color:var(--warning)}
    .pill.danger{color:var(--danger);border-color:var(--danger)}
    .freshness{
      font:400 12.5px/1.5 'Raleway',system-ui,sans-serif;
      color:var(--muted); margin-left:auto;
    }
    section{padding:36px 0;border-top:1px solid var(--line)}
    section:first-of-type{border-top:0}
    h2{
      font-size:18px; font-weight:700; letter-spacing:-.01em;
      color:var(--ink); margin:0 0 14px;
    }
    h3{font-size:17px;margin:26px 0 10px;letter-spacing:-.01em}
    p{margin:0 0 12px;max-width:72ch}
    .lede{font-size:17px;line-height:1.65}
    .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));gap:14px}
    .card{
      background:var(--surface); border:1px solid var(--line);
      border-radius:14px; padding:18px 18px 16px;
    }
    .card .label{font-size:13px;color:var(--muted)}
    .card .value{
      font:600 30px/1.15 'Raleway',system-ui,sans-serif;
      font-variant-numeric:tabular-nums; margin-top:4px; letter-spacing:-.02em;
    }
    .card .unit{font-size:13.5px;color:var(--muted);font-weight:400}
    .card .delta{font-size:14px;font-weight:600}
    .card .delta.up{color:var(--positive)} .card .delta.down{color:var(--danger)}
    .card .note{font-size:14px;margin-top:8px;line-height:1.5}
    .card .meta{
      font:400 12px/1.5 'Raleway',system-ui,sans-serif;
      color:var(--muted); margin-top:10px;
    }
    .scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
    table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}
    th,td{text-align:left;padding:9px 12px 9px 0;border-bottom:1px solid var(--line);
      vertical-align:top}
    th{
      font:600 11.5px/1.4 'Raleway',system-ui,sans-serif;
      letter-spacing:.06em; text-transform:uppercase; color:var(--muted);
      border-bottom-color:var(--line-strong);
    }
    td:first-child{padding-left:0}
    .chip{
      display:inline-block; font:500 11.5px/1 'Raleway',system-ui,sans-serif;
      letter-spacing:.04em; text-transform:uppercase; padding:4px 8px;
      border-radius:5px; background:var(--chip); color:var(--muted);
    }
    .chip.critical{background:var(--danger);color:#fff}
    .chip.warning{color:var(--warning);background:var(--warning-bg)}
    .chip.positive{color:var(--positive)}
    .chip.danger{color:var(--danger)}
    .callout{
      background:var(--warning-bg); border-left:3px solid var(--warning);
      border-radius:0 10px 10px 0; padding:16px 18px; margin:0 0 16px;
    }
    .muted{color:var(--muted)}
    .desc{font-size:14px;max-width:80ch}
    nav.toc{padding:26px 0;border-top:1px solid var(--line)}
    nav.toc ol{margin:8px 0 0;padding-left:22px;columns:2;column-gap:36px}
    nav.toc li{padding:3px 0;break-inside:avoid;font-size:14.5px}
    @media (max-width:640px){nav.toc ol{columns:1}}
    /* Липкая навигация: отчёт длинный, и без неё переход между разделами —
       это прокрутка через сотни строк таблиц. Меню на <details>, без скриптов. */
    .navbar{
      position:sticky; top:0; z-index:100; margin:0 -24px; padding:0 24px;
      background:color-mix(in srgb,var(--ground) 94%,transparent);
      backdrop-filter:saturate(180%) blur(8px);
      border-bottom:1px solid var(--line);
    }
    .navbar .row{display:flex;align-items:center;gap:14px;padding:9px 0}
    .navbar .brand{
      font:600 12.5px/1 'Raleway',system-ui,sans-serif;
      letter-spacing:.04em; text-transform:uppercase; color:var(--muted);
      white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
    }
    .navmenu{margin-left:auto;position:relative}
    .navmenu>summary{
      list-style:none; cursor:pointer; user-select:none;
      font:500 13px/1 'Raleway',system-ui,sans-serif;
      padding:7px 12px; border:1px solid var(--line-strong); border-radius:8px;
      color:var(--ink); background:var(--surface); white-space:nowrap;
    }
    .navmenu>summary::-webkit-details-marker{display:none}
    .navmenu>summary::after{content:' ▾';color:var(--muted)}
    .navmenu[open]>summary::after{content:' ▴'}
    .navmenu .menu{
      position:absolute; right:0; top:calc(100% + 6px); z-index:30;
      min-width:290px; max-height:70vh; overflow:auto;
      background:var(--surface); border:1px solid var(--line-strong);
      border-radius:10px; padding:8px; box-shadow:0 12px 32px rgba(0,0,0,.16);
    }
    .navmenu .menu a{display:block;padding:7px 9px;border-radius:6px;
      font-size:14px;text-decoration:none;color:var(--ink)}
    .navmenu .menu a:hover{background:var(--chip)}
    .navmenu .menu .chip{margin-left:6px}
    @media (max-width:640px){
      .navbar{margin:0 -16px;padding:0 16px}
      .navmenu .menu{min-width:min(88vw,320px)}
    }
    /* Кат: справочные и объёмные разделы открываются по требованию —
       иначе страница на сотни килобайт листается вслепую. */
    details.cut{border-top:1px dashed var(--line-strong);margin-top:14px}
    details.cut>summary{
      list-style:none; cursor:pointer; user-select:none; padding:12px 0 2px;
      font:500 14px/1.4 'Raleway',system-ui,sans-serif; color:var(--brand);
    }
    details.cut>summary::-webkit-details-marker{display:none}
    details.cut>summary::before{content:'▸ ';color:var(--muted)}
    details.cut[open]>summary::before{content:'▾ '}
    details.cut>summary .hint{color:var(--muted);font-weight:400}
    .backtop{
      font:400 12.5px/1 'Raleway',system-ui,sans-serif;
      color:var(--muted); text-decoration:none; margin-left:10px;
      vertical-align:middle; white-space:nowrap;
    }
    section>h2{scroll-margin-top:64px}
    figure{margin:0 0 22px}
    img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:10px;
      background:#fff}
    figcaption{
      font:400 12.5px/1.5 'Raleway',system-ui,sans-serif;
      color:var(--muted); padding-top:7px;
    }
    a{color:var(--brand);text-underline-offset:2px}
    a:focus-visible{outline:2px solid var(--brand);outline-offset:2px;border-radius:3px}
    footer{padding:28px 0;border-top:1px solid var(--line);color:var(--muted);font-size:13.5px}
    @media (max-width:640px){
      .wrap{padding:0 16px 64px} header{padding:28px 0 14px}
      .freshness{margin-left:0;flex-basis:100%}
      section{padding:28px 0}
    }
    @media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
    """

    # Статусы шапки письма живут в светофоре пульта (_status_dashboard);
    # липкая панель оставляет только строку свежести источников.

    cards = ""
    for k in b["kpis"]:
        # delta_dir бывает None, когда у показателя нет дельты вовсе
        # (источник не обновился) — это не то же самое, что flat.
        dcls = {"up": "up", "down": "down"}.get(k.get("delta_dir") or "", "")
        delta = (f"<span class='delta {dcls}'>{k['delta']}</span>"
                 if k["delta"] else "")
        rel = f"<span class='unit'> {k['relative']}</span>" if k.get("relative") else ""
        cards += (
            f"<div class='card'><div class='label'>{k['label']}</div>"
            f"<div class='value'>{k['value']} <span class='unit'>{k['unit']}</span> "
            f"{delta}{rel}</div>"
            f"<div class='note'>{k['interpretation']}</div>"
            f"<div class='meta'>{k['period']} · {k['source']}<br>"
            f"достоверность: {k['confidence']}</div></div>")

    signals = ""
    for s_ in b["signals"]:
        tone = {"positive": "positive", "neutral": "", "negative": "danger"}[s_["tone"]]
        signals += (
            f"<tr><td><span class='chip {tone}'>{s_['tone']}</span></td>"
            f"<td><b>{s_['metric']}</b><div class='muted'>{s_['meaning']}</div></td>"
            f"<td>{s_['previous']}</td><td>{s_['current']}</td><td>{s_['delta']}</td>"
            f"<td class='muted'>{s_['confidence']}</td></tr>")

    findings = _quality_section(dq)

    health_cls = {"positive": "positive", "warning": "warning", "danger": "danger"}[
        b["health"]["colour"]]

    demand = _demand_section()
    ideas = _ideas_section(b.get("growth_ideas") or {})
    ads_data = b.get("ads") or {}
    ads = _ads_section(ads_data)
    lh = b.get("loop_health") or {}
    loop_html = _loop_section(lh)
    mr = opp_mod.money_radar(snap)
    money_html = _money_section(mr)
    cb = cannibal_mod.build(date)
    mm = mismatch_mod.build(date)
    zi = zero_mod.build(date)
    lc = lifecycle_mod.build(date)
    sp = serp_mod.build(date)
    spg = serp_mod.build(date, engine="google")
    gap = serp_mod.cross_engine_gap(date)

    signals_html = (
        f"<div class='scroll'><table><thead><tr>"
        f"<th>Тон</th><th>Показатель</th><th>Было</th><th>Стало</th><th>Δ</th>"
        f"<th>Достоверность</th></tr></thead><tbody>{signals}</tbody></table></div>")
    mmap_html = (
        f"<div class='callout'><b class='chip {health_cls}'>"
        f"{PILL_LABEL[b['health']['status']]}</b>"
        f"<p style='margin:10px 0 0'>{b['health']['detail']}</p></div>"
        f"<p>{b['measurement_summary']}</p>{mmap}{_funnel_section(dq)}")

    # Критичность каждого раздела — из его содержимого, не константой.
    # Качество данных: по сбоям дня, ограничения и правила статус не портят.
    dq_levels = {f["level"] for f in _quality_groups(dq)["incident"]}
    ads_tones = {d["tone"] for d in ads_data.get("decisions", [])}
    exp_verdicts = {e["verdict"] for e in b["experiments"]}
    sections = [
        {"id": "signals", "title": "Сигналы дня",
         "crit": 2 if any(s_["tone"] == "negative" for s_ in b["signals"]) else 1,
         "desc": "Три главных изменения за сутки против предыдущего замера: "
                 "положительное, нейтральное и отрицательное. Сигнал строится "
                 "только по источникам, доступным в оба дня.",
         "html": signals_html},
        {"id": "loop", "title": "Работа конвейера",
         "crit": 3 if lh.get("overdue") else 1,
         "desc": "Подтверждение, что каждый контур системы реально отработал: "
                 "по артефакту с датой, а не по расписанию. Просроченный контур "
                 "означает, что часть данных этого отчёта могла устареть.",
         "html": loop_html},
        {"id": "ads", "title": "Реклама — Яндекс.Директ",
         "crit": 3 if "bad" in ads_tones else (2 if ads_tones else 1),
         "desc": "Состояние платного трафика: расход, клики и вердикты по "
                 "направлениям, реальные поисковые запросы и кандидаты в "
                 "минус-слова. Решения по деньгам — только за руководителем.",
         "html": ads},
        {"id": "drivers", "title": "Что дало изменение",
         "crit": 1,
         "desc": "Разложение суточного изменения на конкретные страницы и "
                 "запросы. Правило методики: причина либо подтверждена "
                 "перечисленными адресами, либо не называется вовсе.",
         "html": drivers},
        {"id": "experiments", "title": "Контроль экспериментов",
         "crit": 2 if exp_verdicts & {"positive", "negative"} else 1,
         "desc": "Каждое изменение сайта живёт как эксперимент: гипотеза, "
                 "контрольная группа, минимальная экспозиция и вердикт. "
                 "До набора экспозиции вердикт честно «рано для вывода».",
         "html": exps},
        {"id": "money", "title": "Money-запросы (позиции 4–20)",
         "crit": 2 if mr.get("available") else 0,
         "desc": "Коммерческие запросы («купить», «цена», «лицензия»…), по "
                 "которым сайт уже ранжируется, но не в топ-3. Самая дешёвая "
                 "зона роста: страница есть, спрос есть, не хватает позиций "
                 "или сниппета.",
         "html": money_html},
        {"id": "cannibal", "title": "Каннибализация запросов",
         "crit": 2 if cb.get("unstable_count") else (1 if cb.get("items") else 0),
         "desc": "Запросы, показы которых расщеплены между несколькими "
                 "страницами сайта. Сам факт двух URL — не проблема; проблема "
                 "— нестабильность, когда выдача перебирает страницы день ото "
                 "дня. Детектор только наблюдает: canonical и склейка — "
                 "отдельные решения.",
         "html": _cannibal_section(cb)},
        {"id": "mismatch", "title": "Query-page mismatch",
         "crit": 2 if mm.get("items") else 0,
         "desc": "Коммерческие запросы («купить», «цена»…), по которым поиск "
                 "стабильно показывает некоммерческую страницу — статью, "
                 "служебный раздел или главную. Сигнал, что посадочная "
                 "отсутствует или недостаточно релевантна.",
         "html": _mismatch_section(mm)},
        {"id": "serp", "title": "SERP Яндекса: позиции и конкуренты",
         "crit": 2 if sp.get("available") else 0,
         "desc": "Реальная выдача Яндекса по ядру запросов (Search API, "
                 "Москва): фактическая позиция сайта, кто занимает топ, "
                 "«слабые» выдачи из маркетплейсов и форумов — лёгкие точки "
                 "входа, и движения доменов к прошлому срезу — ранний "
                 "детектор вытеснения.",
         "html": _serp_section(sp)},
        {"id": "serp-google", "title": "SERP Google (Россия): позиции и конкуренты",
         "crit": 2 if spg.get("available") else 0,
         "desc": "Реальная выдача Google по российскому местоположению "
                 "(xmlriver, еженедельный срез — тот же, что читает "
                 "конкурентная разведка): фактическая позиция сайта, кто "
                 "занимает топ, слабые выдачи и движения к прошлому срезу. "
                 "Позиции Яндекса и Google не сравниваются как равноточные.",
         "html": _serp_section(spg)},
        {"id": "serp-gap", "title": "Разрыв Яндекс ↔ Google по ядру запросов",
         "crit": 2 if (gap.get("available")
                       and gap.get("yandex_top10_google_absent")) else 0,
         "desc": "Запросы одного ядра, измеренные в обеих системах: где "
                 "Яндекс держит нас в топ-10, а в собранной выдаче Google "
                 "(глубина 10) нас нет, и наоборот. Разделяет проблему "
                 "индексации, авторитета и релевантности страницы для Google.",
         "html": _gap_section(gap)},
        {"id": "lifecycle", "title": "Жизненный цикл страниц (Google)",
         "crit": 2 if (lc.get("counts") or {}).get("declining")
                 else (1 if lc.get("available") else 0),
         "desc": "Статус каждой видимой страницы по дневным показам: новая → "
                 "растёт → стабильна → снижается. «Снижается» — ранний сигнал "
                 "увядания: страницу обновляют до того, как она выпадет из "
                 "выдачи, а не после −40% трафика.",
         "html": _lifecycle_section(lc)},
        {"id": "zero", "title": "Инвентарь и страницы без показов",
         "crit": 1 if zi.get("available") else 0,
         "desc": "Все URL сайта из sitemap против страниц с показами Google: "
                 "Index Efficiency по системам и список страниц, которые "
                 "существуют, но поиска не видят. Тексты туда вслепую не "
                 "генерируются — сначала разбор причины.",
         "html": _zero_section(zi, snap)},
        {"id": "board", "title": "Журнал исполнения",
         "crit": 2 if any(r["stage"] == "заблокировано" for r in b["board"]) else 1,
         "desc": "Задачи системы со сменой статуса, блокировкой или близким "
                 "сроком: кто ведёт, на какой стадии, каким PR подтверждено.",
         "html": board},
        {"id": "opportunities", "title": "Радар возможностей",
         "crit": 2 if b["opportunities"]["available"] else 0,
         "desc": "Приоритизированные точки роста по формуле «интент × спрос × "
                 "достоверность × эффект / трудоёмкость». Показы сайта здесь "
                 "не выдаются за рыночный спрос: источник каждого сигнала "
                 "назван явно.",
         "html": opp},
        {"id": "demand", "title": "Спрос и покрытие рынка",
         "crit": 1,
         "desc": "Измеренный покупательский спрос Вордстата, уровни покрытия "
                 "(страница → индекс → топ-10 → клики), непокрытые кластеры, "
                 "кандидаты в каталог и экономика исследования.",
         "html": demand},
        {"id": "ideas", "title": "Перспективные идеи бесплатного продвижения",
         "crit": 1 if (b.get("growth_ideas") or {}).get("fresh") else 0,
         "desc": "Копилка идей с обоснованием и статусами. Статус меняет "
                 "руководитель; принятые и отклонённые идеи остаются в "
                 "истории и повторно не предлагаются.",
         "html": ideas},
        {"id": "charts", "title": "Графики",
         "crit": 0,
         "desc": "Графики письма в полном размере и в живом виде: наведение "
                 "показывает значения по дням.",
         "html": charts or "<p class='muted'>Графиков нет.</p>"},
        {"id": "measurement", "title": "Карта измерений",
         "crit": 3 if b["health"]["colour"] == "danger"
                 else (2 if b["health"]["colour"] == "warning" else 1),
         "desc": "Что именно измеряет каждый источник, за какой период и с "
                 "чем его корректно сравнивать. Здесь же — текущий статус "
                 "здоровья данных и его причина.",
         "html": mmap_html},
        {"id": "technical", "title": "Техническое состояние сайта",
         # Критичность ведёт себя как у любого раздела: красный статус
         # поднимает его выше, зелёный оставляет среди рабочих блоков.
         "crit": {"red": 3, "yellow": 2}.get(
             (b.get("technical") or {}).get("level"), 1),
         "desc": "Скорость страниц по замеру PageSpeed Insights: мобильная "
                 "выдача как основной показатель, регрессии к прошлому замеру "
                 "и последняя расширенная проверка шаблонов. Балл SEO у "
                 "Lighthouse относится к технической вёрстке и не связан с "
                 "видимостью сайта в поиске.",
         "html": _technical_section(b.get("technical") or {})},
        {"id": "quality", "title": "Качество данных",
         "crit": 3 if "critical" in dq_levels
                 else (2 if "warning" in dq_levels else 1),
         "desc": "Сбои дня (что сломалось в сборе и источниках сегодня), "
                 "постоянные ограничения методики с условием снятия и правила "
                 "подсчёта. Статус данных отчёта считается только по сбоям.",
         "html": findings},
        {"id": "yandex-queries", "title": "Запросы Яндекса за окно источника",
         "crit": 0,
         "desc": "Полная таблица запросов Вебмастера с показами, кликами, "
                 "позицией и интентом за окно источника; окно плавает вслед "
                 "за задержкой Вебмастера и не совпадает с окном KPI.",
         "html": queries},
        {"id": "google-pages", "title": "Страницы в Google",
         "crit": 0,
         "desc": "Страницы сайта в Google Search Console по показам.",
         "html": pages},
        {"id": "google-queries", "title": "Запросы Google",
         "crit": 0,
         "desc": "Запросы Google Search Console по показам.",
         "html": gq},
    ]
    ordered = order_sections(sections)
    body_sections = "".join(_section_html(s) for s in ordered)

    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BIZSoft Growth Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Raleway:wght@400;500;600;700&display=swap">
<style>{css}</style></head><body id="top"><div class="wrap">
{_navbar(ordered, ru_date_full(date))}

<header>
  <h1>BIZSoft Growth Intelligence</h1>
  <div class="sub">Daily Search, Demand &amp; Experiment Control · {ru_date_full(date)}</div>
</header>

<div class="statusbar"><span class="freshness">{b['sources_line']}</span></div>

<section id="dash">
  <h2>Пульт</h2>
  <p class="lede"><b>От вас:</b> {b['user_action']}</p>
  {_owner_desk_html(b)}
  {_kpi_dashboard(b, snap)}
  {_status_dashboard(b)}
  {_daily_multiples(snap)}
  {_heat_dashboard(snap, date)}
</section>

{_toc(ordered)}

{body_sections}

<footer>
  Методика — <a href="{BLOB}/docs/seo/reporting-methodology.md">reporting-methodology.md</a>.
  Тикеты и журнал работ — <a href="{REPO}/tree/{BRANCH}/reports/seo/tasks">reports/seo/tasks</a>.
  Отчёт собран автоматически из данных Яндекс.Вебмастера, Google Search Console,
  Яндекс.Метрики и GA4; числа не редактируются вручную.
</footer>
</div><script>{kit.kit_js()}</script></body></html>"""


def build_markdown(b: dict, snap: dict, dq: dict, date: str) -> str:
    """Полный отчёт в Markdown.

    GitHub отображает Markdown как страницу, а HTML — как исходный текст. Ссылка
    в письме должна вести туда, где отчёт читается, а не в код. Приватная
    страница на claude.ai для получателя письма не открывается, поэтому основной
    адрес — файл в репозитории, к которому доступ уже есть.
    """
    cov = b["health"]
    L = [f"# BIZSoft Growth Intelligence — {ru_date_full(date)}", "",
         "Daily Search, Demand & Experiment Control", "",
         " · ".join(f"**{p['label']}:** {p['text']}" for p in b["pills"]), "",
         b["sources_line"], "",
         "---", "", "## Итог дня", "",
         f"**От вас:** {b['user_action']}", ""]
    if not b.get("user_action_required") and b.get("owner_desk"):
        # Плашка шапки считает предложения на столе, а строка «От вас» их не
        # называла: 09.09.2026 отчёт одновременно писал «ОТ ВАС: 2 предложения»
        # и «Срочных решений нет». Письмо перечисляет их с 31.08, страница — нет.
        L += [f"На вашем столе {counted(len(b['owner_desk']), 'предложение', 'предложения', 'предложений')}:", ""]
        L += [f"- {d}" for d in b["owner_desk"]]
        L.append("")
    L += [
         "| Показатель | Значение | Изменение | Период | Источник | Достоверность |",
         "|---|---|---|---|---|---|"]
    for k in b["kpis"]:
        L.append(f"| {k['label']} | {k['value']} {k['unit']} | {k['delta'] or '—'} | "
                 f"{k['period']} | {k['source']} | {k['confidence']} |")
    L += ["", *(f"- **{k['label']}.** {k['interpretation']}" for k in b["kpis"]), ""]

    L += ["## Сигналы дня", "",
          "| Показатель | Было | Стало | Изменение | Что это значит |",
          "|---|---|---|---|---|"]
    for s_ in b["signals"]:
        L.append(f"| {s_['metric']} | {s_['previous']} | {s_['current']} | "
                 f"{s_['delta']} | {s_['meaning']} |")
    L.append("")

    L += ["## Что дало изменение", ""]
    for db in b["driver_blocks"]:
        L += [f"### {db['engine']}", "", f"*{db['window']}*", "", db["text"], "",
              "| Изменение | Адрес | Доля | Состояние |", "|---|---|---|---|"]
        for r in db["rows"]:
            L.append(f"| {r['delta']} | {r['entity']} | {r['share']} | "
                     f"{r['state'] or '—'} |")
        L.append("")

    L += ["## Контроль экспериментов", ""]
    for e in b["experiments"]:
        L += [f"### {e['ticket']}", "",
              f"**Проверяем.** {e['hypothesis']}", "",
              f"**Что изменили.** {e['treatment']}", "",
              f"**Совместное внедрение.** {e['combined_note']}", "",
              "| Параметр | Значение |", "|---|---|",
              f"| запуск | {ru_date_full(e['start'])} |",
              f"| прошло дней | {e['days_elapsed']} |",
              f"| минимальная экспозиция | {e['minimum_exposure']} |",
              f"| страниц всего | {e['pages_total']} |",
              f"| новый вариант на сайте | {num(e['pages_live_with_treatment'])} |",
              f"| обновление сниппета в выдаче | {e['search_snippet_refresh']} |",
              f"| накоплено | {e['current_result']} |",
              f"| целевой показатель | {e['primary_metric']} |",
              f"| следующая проверка | {ru_date_full(e['next_review'])} |",
              f"| вывод | **{VERDICT_LABEL[e['verdict']]}** — {e['verdict_reason']} |"]
        if e.get("owner_decision"):
            L.append(f"| решение по эксперименту | {e['owner_decision']} |")
        L.append("")

    L += ["## Журнал исполнения", "",
          "| Задача | Владелец | Стадия | Статус | Срок | Артефакт |",
          "|---|---|---|---|---|---|"]
    for r in b["board"]:
        L.append(f"| [{r['task']}]({r['artifact_url']}) | {r['owner']} | {r['stage']} | "
                 f"{r['status']} | {r['due']} | {r.get('artifact') or '—'} |")
    L.append("")

    L += ["## Радар возможностей", ""]
    held_md = b["opportunities"].get("held_by_experiment") or []
    if held_md:
        L += ["Придержаны до вердикта эксперимента: "
              + ", ".join(f"{h['cluster']} ({h['experiment']})" for h in held_md)
              + ". Правка их страниц сейчас обнулит замер.", ""]
    L += ["| Кластер | Доказательство | Потенциал | Действие | Решение к |",
          "|---|---|---|---|---|"]
    for o in b["opportunities"]["items"]:
        L.append(f"| {o['cluster']} | {o['evidence']} | {o['potential']} | "
                 f"{o['recommended_action']} | "
                 f"{ru_date_full(o['decision_date']) if o.get('decision_date') else 'срок не назначен'} |")
    L.append("")

    mr = opp_mod.money_radar(snap)
    if mr.get("available"):
        L += ["## Money-запросы (позиции 4–20)", "",
              f"{mr.get('note', '')}.", "",
              "| Запрос | Система | Показы | Клики | Позиция | Действие |",
              "|---|---|---|---|---|---|"]
        for i in mr["items"]:
            L.append(f"| {i['query']} | {i['engine']} | {num(i['impressions'])} | "
                     f"{i['clicks']} | {i['position']} | {i['recommended_action']} |")
        L.append("")

    cb = cannibal_mod.build(date)
    if cb.get("available") and cb.get("items"):
        L += ["## Каннибализация запросов", "",
              "| Вердикт | Запрос | Показы | Смен лидера | Действие |",
              "|---|---|---|---|---|"]
        for i in cb["items"]:
            L.append(f"| {i['verdict_label']} | {i['query']} | "
                     f"{num(i['impressions'])} | {i['leader_changes']} | "
                     f"{i['recommended_action']} |")
        L.append("")

    mm = mismatch_mod.build(date)
    if mm.get("available") and mm.get("items"):
        L += ["## Query-page mismatch", "",
              "| Запрос | Показы | Куда ведёт | Тип | Действие |",
              "|---|---|---|---|---|"]
        for i in mm["items"]:
            L.append(f"| {i['query']} | {num(i['impressions'])} | {i['page']} | "
                     f"{i['page_type']} | {i['recommended_action']} |")
        L.append("")

    sp = serp_mod.build(date)
    if sp.get("available"):
        L += ["## SERP Яндекса: позиции и конкуренты", "",
              f"Срез {sp['as_of']}: {sp['queries_total']} запросов; мы в "
              f"топ-10 по {sp['ours_in_top10']}; слабых выдач: "
              f"{sp['weak_serps']}.", "",
              "| Домен | Топ-10 появлений | Кто |", "|---|---|---|"]
        for d in sp["top_domains"][:10]:
            L.append(f"| {d['domain']} | {d['hits']} | {d['kind']} |")
        L.append("")

    spg = serp_mod.build(date, engine="google")
    if spg.get("available"):
        L += ["## SERP Google (Россия): позиции и конкуренты", "",
              f"Срез {spg['as_of']} (xmlriver, местоположение Россия): "
              f"{spg['queries_total']} запросов; мы в топ-10 по "
              f"{spg['ours_in_top10']}; слабых выдач: {spg['weak_serps']}.", "",
              "| Домен | Топ-10 появлений | Кто |", "|---|---|---|"]
        for d in spg["top_domains"][:10]:
            L.append(f"| {d['domain']} | {d['hits']} | {d['kind']} |")
        L.append("")
    gap = serp_mod.cross_engine_gap(date)
    if gap.get("available"):
        ya_only = gap["yandex_top10_google_absent"]
        L += ["## Разрыв Яндекс ↔ Google по ядру запросов", "",
              f"Сопоставлено {gap['queries_compared']} запросов: в топ-10 "
              f"обеих систем {gap['both_top10']}; Яндекс топ-10, в Google "
              f"нет — {len(ya_only)}; Google топ-10, в Яндексе нет — "
              f"{len(gap['google_top10_yandex_absent'])} (глубина Google "
              f"{gap.get('google_depth', 10)}).", ""]
        if ya_only:
            L += ["| Запрос | Позиция в Яндексе | Топ-3 Google |", "|---|---|---|"]
            for i in ya_only[:15]:
                L.append(f"| {i['query']} | {i['yandex_position']} | "
                         f"{', '.join(d for d in i['google_top3'] if d)} |")
            L.append("")

    lc = lifecycle_mod.build(date)
    if lc.get("available") and lc.get("counts"):
        parts = " · ".join(f"{k}: {v}" for k, v in sorted(lc["counts"].items()))
        L += ["## Жизненный цикл страниц (Google)", "",
              f"Страниц с показами: {lc['pages_total']} ({parts}). "
              f"{lc.get('note', '')}", ""]
        declining = [i for i in lc["items"] if i["status"] == "declining"]
        if declining:
            L += ["| Страница | Пред. неделя | Эта неделя |", "|---|---|---|"]
            for i in declining:
                L.append(f"| {i['page']} | {i['prev7']} | {i['last7']} |")
            L.append("")

    zi = zero_mod.build(date)
    if zi.get("available"):
        types = ", ".join(f"{k}: {v}" for k, v in sorted(
            zi["by_type"].items(), key=lambda kv: -kv[1]))
        ig, iy = zi.get("index_google") or {}, zi.get("index_yandex") or {}
        L += ["## Инвентарь и страницы без показов", "",
              f"Инвентарь sitemap: {num(zi['inventory_total'])} URL; с показами "
              f"Google: {zi['with_impressions']} "
              f"({zi['coverage_google']:.1%}); без показов: "
              f"{num(zi['zero_total'])} ({types}). {zi['note']}", ""]
        if ig.get("available"):
            from inventory import GOOGLE_CLASS_LABEL
            parts = ", ".join(f"{GOOGLE_CLASS_LABEL.get(k, k)} — {v}"
                              for k, v in sorted(zi.get("by_cause", {}).items(),
                                                 key=lambda kv: -kv[1]))
            L += [f"В индексе Google: {num(ig['indexed'])} "
                  f"({ig['coverage_indexed']:.1%}). Причины отсутствия "
                  f"показов: {parts}.", ""]
        if iy.get("available"):
            ex = ", ".join(f"{k} — {v}" for k, v in sorted(
                (iy.get("excluded_by_reason") or {}).items(),
                key=lambda kv: -kv[1])) or "нет"
            host_indexed = ((snap.get("yandex") or {})
                            .get("indexation") or {}).get("indexed_urls")
            note = zero_mod.yandex_slice_note(iy, host_indexed)
            L += [f"Яндекс: в поиске {num(iy['in_search'])} страниц инвентаря "
                  f"({iy['coverage']:.1%}); исключено — {ex}."
                  + (f" {note[:1].upper()}{note[1:]}." if note else ""), ""]

    lh = b.get("loop_health") or {}
    if lh.get("available"):
        L += ["## Работа конвейера", "",
              f"Контуров в срок: {lh.get('ok_count')} из {lh.get('total')}.", "",
              "| Статус | Контур | Последний прогон | Ожидается не старше |",
              "|---|---|---|---|"]
        for r in lh.get("contours", []):
            L.append(f"| {'ПРОСРОЧЕН' if r['overdue'] else 'в срок'} | "
                     f"{r['label']} | {r['last_run'] or '—'} | "
                     f"{r['expected_since']} |")
        L.append("")

    if DEMAND_STATE.exists():
        st = json.loads(DEMAND_STATE.read_text(encoding="utf-8"))
        if st["coverage"].get("available"):
            uni, c = st["universe"], st["coverage"]
            total = f"{uni['total_commercial_demand']:,}".replace(",", " ")
            L += ["## Спрос и покрытие рынка", "",
                  f"Измеренный покупательский спрос — {total} показов в месяц по "
                  f"{uni['clusters']} кластерам. Считается по частотности "
                  f"коммерческих фраз, а не по числу ключевых слов.", "",
                  "| Уровень | Доля спроса |", "|---|---|"]
            for k, v in c["levels"].items():
                L.append(f"| {k} | {'нет данных' if v is None else f'{v:.1%}'} |")
            L += ["", "### Непокрытый коммерческий спрос", "",
                  "| Кластер | Спрос, показов/мес | Класс | Действие |",
                  "|---|---|---|---|"]
            for u in st["uncovered_top"]:
                L.append(f"| {u['cluster']} | {num(u['demand'])} | "
                         f"{u['gap']} | {u['action']} |")
            L.append("")
            exp = _filter_rejected(st.get("vendor_expansion") or {})
            L += ["### Каких вендоров добавить", ""]
            if not exp.get("available"):
                L += [(exp.get("reason") or "данных пока нет").capitalize() + ".", ""]
            else:
                combined = f"{exp['combined_demand']:,}".replace(",", " ")
                L += [f"Проверен спрос на {exp['candidates_measured']} зарубежных "
                      f"разработчиков вне каталога; покупательский спрос подтверждён "
                      f"у {exp['recommended_total']} — суммарно {combined} показов "
                      f"в месяц. {exp['note']}", "",
                      "| Вендор | Тип | Спрос | Достоверность | Оплата картой | "
                      "Рекомендация | Адрес |", "|---|---|---|---|---|---|---|"]
                for r in exp["recommended"]:
                    L.append(
                        f"| {r['brand']} | "
                        f"{'AI' if r['kind'] == 'ai' else 'классический'} | "
                        f"{num(r['commercial_demand'])} | "
                        f"{r.get('demand_confidence', '—')} | "
                        f"{PAY_LABEL.get(r['payment']['verdict'], '—')} | "
                        f"{r['recommendation']} | `{r['seo']['url']}` |")
                if exp.get("low_confidence"):
                    L += ["", "Спрос требует ручного просмотра выдачи (имя бренда — "
                          "обычное английское слово): "
                          + ", ".join(exp["low_confidence"]) + "."]
                if exp.get("needs_manual_check"):
                    L += ["", "Способ оплаты определить автоматически не удалось: "
                          + ", ".join(exp["needs_manual_check"]) + "."]
                L.append("")

    L += ["## Карта измерений", "", b["measurement_summary"], "",
          "| Источник | Показатель | Охват | Период | Сравнимо с |",
          "|---|---|---|---|---|"]
    for m in dq.get("measurement_map", []):
        L.append(f"| {m['source']} | {m['metric']} | {m['scope']} | {m['period']} | "
                 f"{', '.join(m['comparable_with']) or '—'} |")
    groups = _quality_groups(dq)
    L += ["", "## Качество данных", "",
          f"**{PILL_LABEL[cov['status']].capitalize()}:** {cov['reason']}. {cov['detail']}",
          "", f"Сбоев дня: {len(groups['incident'])} · постоянных ограничений: "
          f"{len(groups['limit'])} · правил подсчёта: {len(groups['rule'])}.", ""]
    for kind, title in (("incident", "Сбои дня"), ("limit", "Постоянные ограничения"),
                        ("rule", "Правила подсчёта")):
        L += [f"### {title}", ""]
        if not groups[kind]:
            L += ["Нет.", ""]
            continue
        L += ["| Уровень | Проверка | Что обнаружено | Снимается, когда |", "|---|---|---|---|"]
        for f in groups[kind]:
            L.append(f"| {f['level']} | {f['title']} | {f['detail']} | "
                     f"{f.get('lifted_when') or '—'} |")
        L.append("")

    yx = snap["yandex"]
    L += ["", "## Запросы Яндекса за окно источника", "",
          "| Запрос | Показы | Клики | Средняя позиция | Интент |", "|---|---|---|---|---|"]
    for e in sorted(yx.get("entities") or [], key=lambda e: -e["impressions"])[:50]:
        L.append(f"| {e['entity_id']} | {num(e['impressions'])} | {num(e['clicks'])} | "
                 f"{e['average_position']} | {e['intent']} |")

    g = snap["google"]
    L += ["", "## Страницы в Google", "",
          "| Страница | Показы | Клики | Средняя позиция |", "|---|---|---|---|"]
    for p_ in sorted(g.get("pages") or [], key=lambda p: -p["impressions"])[:30]:
        L.append(f"| {p_['entity_id']} | {num(p_['impressions'])} | "
                 f"{num(p_['clicks'])} | {p_['average_position']} |")

    L += ["", "---", "",
          f"Методика — [reporting-methodology.md]({BLOB}/docs/seo/reporting-methodology.md). "
          f"Тикеты — [reports/seo/tasks]({REPO}/tree/{BRANCH}/reports/seo/tasks). "
          "Отчёт собран автоматически; числа не редактируются вручную.", ""]
    return "\n".join(L)


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    snap = json.loads((BASE / "snapshots" / f"{date}.json").read_text(encoding="utf-8"))
    prev = snapshot_mod.prev_snapshot(date)
    dq = json.loads((BASE / "data-quality" / f"{date}.json").read_text(encoding="utf-8"))
    actions_cfg = json.loads((BASE / "actions.json").read_text(encoding="utf-8"))
    b = assemble(snap, prev, dq, actions_cfg, load_site_check(date))

    html = build_html(b, snap, dq, date)
    out = OUT / date
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / "README.md").write_text(build_markdown(b, snap, dq, date), encoding="utf-8")

    # Страница «последний отчёт» живёт по одному и тому же пути: ссылка в письме
    # не должна меняться каждый день, иначе вчерашняя ссылка ведёт в никуда.
    latest = OUT.parent / "latest.html"
    latest.write_text(html, encoding="utf-8")

    print(f"веб-отчёт: {out / 'index.html'}")
    print(f"markdown:  {out / 'README.md'}")
    print(f"последний: {latest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
