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

import report_v2  # noqa: E402
from report_v4 import (BLOB, BRANCH, PILL_LABEL, REPO, VERDICT_LABEL,  # noqa: E402
                       assemble, load_site_check)
from textfmt import num, pct, ru_date, ru_date_full, signed  # noqa: E402

BASE = pathlib.Path("reports/seo/intelligence")
OUT = pathlib.Path("reports/seo/public/daily")


DEMAND_STATE = pathlib.Path("reports/seo/wordstat/intelligence-state.json")


def _demand_section() -> str:
    """Покрытие спроса и разрывы: полные таблицы живут здесь, не в письме."""
    if not DEMAND_STATE.exists():
        return "<p class='muted'>Исследование спроса ещё не выполнялось.</p>"
    st = json.loads(DEMAND_STATE.read_text(encoding="utf-8"))
    cov, uni = st["coverage"], st["universe"]
    if not cov.get("available"):
        return "<p class='muted'>Спрос ещё не измерен.</p>"
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


def _expansion_section(st: dict) -> str:
    """Каких вендоров добавить: спрос, оплата, трудоёмкость, готовая обвязка."""
    exp = st.get("vendor_expansion") or {}
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


def embed_png(path: pathlib.Path) -> str:
    """PNG внутрь страницы: отчёт открывается по ссылке, а не только из репозитория."""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "<p class='muted'>Нет данных.</p>"
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<div class='scroll'><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>"


def build_html(b: dict, snap: dict, dq: dict, date: str) -> str:
    yx, g = snap["yandex"], snap["google"]

    queries = table(
        ["Запрос", "Показы", "Клики", "CTR", "Средняя позиция", "Интент", "Достоверность"],
        [[e["entity_id"], num(e["impressions"]), num(e["clicks"]), pct(e["ctr"], 2),
          e["average_position"], e["intent"], e["confidence"]]
         for e in sorted(yx.get("entities") or [], key=lambda e: -e["impressions"])[:100]])

    pages = table(
        ["Страница", "Показы", "Клики", "Средняя позиция"],
        [[p["entity_id"], num(p["impressions"]), num(p["clicks"]), p["average_position"]]
         for p in sorted(g.get("pages") or [], key=lambda p: -p["impressions"])[:50]])

    gq = table(
        ["Запрос", "Показы", "Клики", "Средняя позиция"],
        [[e["entity_id"], num(e["impressions"]), num(e["clicks"]), e["average_position"]]
         for e in sorted(g.get("entities") or [], key=lambda e: -e["impressions"])[:50]])

    mmap = table(
        ["Источник", "Показатель", "Сущность", "Охват", "Период", "Сравнимо с", "Почему различается"],
        [[m["source"], m["metric"], m["entity"], m["scope"], m["period"],
          ", ".join(m["comparable_with"]) or "—", m["difference_explanation"]]
         for m in dq.get("measurement_map", [])])

    findings = table(
        ["Уровень", "Проверка", "Что обнаружено", "Следствие для отчёта"],
        [[f["level"], f["title"], f["detail"], f.get("effect_on_report") or "—"]
         for f in dq["findings"]])

    board = table(
        ["Задача", "Владелец", "Стадия", "Статус", "Срок", "Артефакт"],
        [[f"<a href='{r['artifact_url']}'>{r['task']}</a>", r["owner"], r["stage"],
          r["status"], r["due"], r.get("artifact") or "—"] for r in b["board"]])

    exps = ""
    for e in b["experiments"]:
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
                ["новый вариант на сайте", num(e["pages_live_with_treatment"])],
                ["обновление сниппета в выдаче", e["search_snippet_refresh"]],
                ["показов накоплено (оценка)", num(e["impressions_since_deploy"])],
                ["переходов накоплено", num(e["clicks_since_deploy"])],
                ["целевой показатель", e["primary_metric"]],
                ["достоверность", e["confidence"]],
                ["следующая проверка", ru_date_full(e["next_review"])],
                ["вывод", f"{VERDICT_LABEL[e['verdict']]} — {e['verdict_reason']}"]]))

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
          o["recommended_action"], ru_date_full(o["decision_date"])]
         for o in b["opportunities"]["items"]])

    charts = "".join(
        f"<figure><img src='{embed_png(BASE / 'charts' / f'{date}-{n}.png')}' alt='{c}'>"
        f"<figcaption>{c}</figcaption></figure>"
        for n, c in (("kpi-slope", "Показы Google неделя к неделе"),
                     ("drivers", "Вклад страниц в изменение показов"),
                     ("experiment", "Ход эксперимента"))
        if (BASE / "charts" / f"{date}-{n}.png").exists())

    # Токены светлой темы объявлены на голом :root, тёмные — отдельно для
    # системной настройки и для явного выбора: у зрителя три состояния, и цвет,
    # объявленный только внутри media-блока, в неотмеченном состоянии не сработает.
    css = """
    :root{
      --ground:#F6F8FB; --surface:#FFFFFF; --ink:#101828; --muted:#667085;
      --line:#EAECF0; --line-strong:#D8DDE5; --brand:#F4511E;
      --positive:#12B76A; --warning:#B54708; --warning-bg:#FFFAEB;
      --danger:#D92D20; --info:#2E90FA; --chip:#F2F4F7;
    }
    @media (prefers-color-scheme: dark){
      :root:not([data-theme="light"]){
        --ground:#0C111D; --surface:#161B26; --ink:#ECEFF3; --muted:#94A3B8;
        --line:#1F2733; --line-strong:#2A3444; --brand:#FF7A45;
        --positive:#3DDC97; --warning:#F5A524; --warning-bg:#231A0B;
        --danger:#FF6B60; --info:#5BA8FF; --chip:#1C2431;
      }
    }
    :root[data-theme="dark"]{
      --ground:#0C111D; --surface:#161B26; --ink:#ECEFF3; --muted:#94A3B8;
      --line:#1F2733; --line-strong:#2A3444; --brand:#FF7A45;
      --positive:#3DDC97; --warning:#F5A524; --warning-bg:#231A0B;
      --danger:#FF6B60; --info:#5BA8FF; --chip:#1C2431;
    }
    *{box-sizing:border-box}
    body{
      margin:0; background:var(--ground); color:var(--ink);
      font:400 16px/1.6 'IBM Plex Sans','Segoe UI',system-ui,-apple-system,sans-serif;
      -webkit-font-smoothing:antialiased;
    }
    .wrap{max-width:1080px;margin:0 auto;padding:0 24px 96px}
    header{padding:40px 0 20px}
    h1{
      font-size:clamp(26px,3.4vw,36px); line-height:1.15; margin:0;
      letter-spacing:-.02em; text-wrap:balance;
    }
    .sub{color:var(--muted);font-size:14.5px;margin-top:6px}
    .statusbar{
      position:sticky; top:0; z-index:5; background:var(--ground);
      border-bottom:1px solid var(--line); padding:12px 0; margin-bottom:8px;
      display:flex; flex-wrap:wrap; gap:8px; align-items:center;
    }
    .pill{
      font:500 12.5px/1 'IBM Plex Mono',ui-monospace,monospace;
      letter-spacing:.04em; text-transform:uppercase;
      border:1px solid var(--line-strong); border-radius:999px; padding:6px 11px;
      color:var(--muted); white-space:nowrap;
    }
    .pill.positive{color:var(--positive);border-color:var(--positive)}
    .pill.warning{color:var(--warning);border-color:var(--warning)}
    .pill.danger{color:var(--danger);border-color:var(--danger)}
    .freshness{
      font:400 12.5px/1.5 'IBM Plex Mono',ui-monospace,monospace;
      color:var(--muted); margin-left:auto;
    }
    section{padding:36px 0;border-top:1px solid var(--line)}
    section:first-of-type{border-top:0}
    h2{
      font-size:13px; font-weight:600; letter-spacing:.09em; text-transform:uppercase;
      color:var(--muted); margin:0 0 18px;
      font-family:'IBM Plex Mono',ui-monospace,monospace;
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
      font:600 30px/1.15 'IBM Plex Sans',sans-serif;
      font-variant-numeric:tabular-nums; margin-top:4px; letter-spacing:-.02em;
    }
    .card .unit{font-size:13.5px;color:var(--muted);font-weight:400}
    .card .delta{font-size:14px;font-weight:600}
    .card .delta.up{color:var(--positive)} .card .delta.down{color:var(--danger)}
    .card .note{font-size:14px;margin-top:8px;line-height:1.5}
    .card .meta{
      font:400 12px/1.5 'IBM Plex Mono',ui-monospace,monospace;
      color:var(--muted); margin-top:10px;
    }
    .scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
    table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}
    th,td{text-align:left;padding:9px 12px 9px 0;border-bottom:1px solid var(--line);
      vertical-align:top}
    th{
      font:600 11.5px/1.4 'IBM Plex Mono',ui-monospace,monospace;
      letter-spacing:.06em; text-transform:uppercase; color:var(--muted);
      border-bottom-color:var(--line-strong);
    }
    td:first-child{padding-left:0}
    .chip{
      display:inline-block; font:500 11.5px/1 'IBM Plex Mono',ui-monospace,monospace;
      letter-spacing:.04em; text-transform:uppercase; padding:4px 8px;
      border-radius:5px; background:var(--chip); color:var(--muted);
    }
    .chip.critical{background:var(--danger);color:#fff}
    .chip.warning{color:var(--warning);background:var(--warning-bg)}
    .callout{
      background:var(--warning-bg); border-left:3px solid var(--warning);
      border-radius:0 10px 10px 0; padding:16px 18px; margin:0 0 16px;
    }
    .muted{color:var(--muted)}
    figure{margin:0 0 22px}
    img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:10px;
      background:#fff}
    figcaption{
      font:400 12.5px/1.5 'IBM Plex Mono',ui-monospace,monospace;
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

    pill_class = {"positive": "positive", "mixed": "warning", "negative": "danger",
                  "stable": "", "verified": "positive", "limited": "warning",
                  "degraded": "danger", "none": "", "required": "warning"}
    pills = "".join(
        f"<span class='pill {pill_class.get(p['state'], '')}'>{p['label']}: {p['text']}</span>"
        for p in b["pills"])

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

    findings_rows = []
    for f in dq["findings"]:
        cls = {"critical": "critical", "warning": "warning", "info": ""}[f["level"]]
        findings_rows.append([f"<span class='chip {cls}'>{f['level']}</span>",
                              f["title"], f["detail"], f.get("effect_on_report") or "—"])
    findings = table(["Уровень", "Проверка", "Что обнаружено", "Следствие для отчёта"],
                     findings_rows)

    health_cls = {"positive": "positive", "warning": "warning", "danger": "danger"}[
        b["health"]["colour"]]

    demand = _demand_section()

    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BIZSoft Growth Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{css}</style></head><body><div class="wrap">

<header>
  <h1>BIZSoft Growth Intelligence</h1>
  <div class="sub">Daily Search, Demand &amp; Experiment Control · {ru_date_full(date)}</div>
</header>

<div class="statusbar">{pills}<span class="freshness">{b['sources_line']}</span></div>

<section>
  <h2>Итог дня</h2>
  <p class="lede"><b>От вас:</b> {b['user_action']}</p>
  <div class="cards">{cards}</div>
</section>

<section>
  <h2>Сигналы дня</h2>
  <div class="scroll"><table><thead><tr>
    <th>Тон</th><th>Показатель</th><th>Было</th><th>Стало</th><th>Δ</th><th>Достоверность</th>
  </tr></thead><tbody>{signals}</tbody></table></div>
</section>

<section><h2>Что дало изменение</h2>{drivers}</section>

<section><h2>Контроль экспериментов</h2>{exps}</section>

<section><h2>Журнал исполнения</h2>{board}</section>

<section><h2>Радар возможностей</h2>{opp}</section>

<section><h2>Спрос и покрытие рынка</h2>{demand}</section>

<section><h2>Графики</h2>{charts or "<p class='muted'>Графиков нет.</p>"}</section>

<section>
  <h2>Карта измерений</h2>
  <div class="callout"><b class="chip {health_cls}">{PILL_LABEL[b['health']['status']]}</b>
    <p style="margin:10px 0 0">{b['health']['detail']}</p></div>
  <p>{b['measurement_summary']}</p>
  {mmap}
</section>

<section><h2>Качество данных</h2>{findings}</section>

<section><h2>Запросы Яндекса — выборка топ-100</h2>{queries}</section>
<section><h2>Страницы в Google</h2>{pages}</section>
<section><h2>Запросы Google</h2>{gq}</section>

<footer>
  Методика — <a href="{BLOB}/docs/seo/reporting-methodology.md">reporting-methodology.md</a>.
  Тикеты и журнал работ — <a href="{REPO}/tree/{BRANCH}/reports/seo/tasks">reports/seo/tasks</a>.
  Отчёт собран автоматически из данных Яндекс.Вебмастера, Google Search Console,
  Яндекс.Метрики и GA4; числа не редактируются вручную.
</footer>
</div></body></html>"""


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
         f"**От вас:** {b['user_action']}", "",
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
              f"| вывод | **{VERDICT_LABEL[e['verdict']]}** — {e['verdict_reason']} |", ""]

    L += ["## Журнал исполнения", "",
          "| Задача | Владелец | Стадия | Статус | Срок | Артефакт |",
          "|---|---|---|---|---|---|"]
    for r in b["board"]:
        L.append(f"| [{r['task']}]({r['artifact_url']}) | {r['owner']} | {r['stage']} | "
                 f"{r['status']} | {r['due']} | {r.get('artifact') or '—'} |")
    L.append("")

    L += ["## Радар возможностей", "",
          "| Кластер | Доказательство | Потенциал | Действие | Решение к |",
          "|---|---|---|---|---|"]
    for o in b["opportunities"]["items"]:
        L.append(f"| {o['cluster']} | {o['evidence']} | {o['potential']} | "
                 f"{o['recommended_action']} | {ru_date_full(o['decision_date'])} |")
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
            exp = st.get("vendor_expansion") or {}
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
    L += ["", "## Качество данных", "",
          f"**{PILL_LABEL[cov['status']].capitalize()}:** {cov['reason']}. {cov['detail']}",
          "", "| Уровень | Проверка | Что обнаружено |", "|---|---|---|"]
    for f in dq["findings"]:
        L.append(f"| {f['level']} | {f['title']} | {f['detail']} |")

    yx = snap["yandex"]
    L += ["", "## Запросы Яндекса — выборка топ-100", "",
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
    prev = report_v2.prev_snapshot(date)
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
