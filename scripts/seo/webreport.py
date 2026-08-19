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

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import report_v2  # noqa: E402
from report_v4 import (BLOB, REPO, T, VERDICT_LABEL, PILL_LABEL,  # noqa: E402
                       assemble, load_site_check)
from textfmt import num, pct, ru_date, ru_date_full, signed  # noqa: E402

BASE = pathlib.Path("reports/seo/intelligence")
OUT = pathlib.Path("reports/seo/public/daily")


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
        f"<figure><img src='../../charts/{date}-{n}.png' alt='{n}'>"
        f"<figcaption>{c}</figcaption></figure>"
        for n, c in (("kpi-slope", "Показы Google неделя к неделе"),
                     ("drivers", "Вклад страниц в изменение показов"),
                     ("experiment", "Ход эксперимента"))
        if (BASE / "charts" / f"{date}-{n}.png").exists())

    css = f"""
    :root{{--bg:{T['background']};--surface:{T['surface']};--ink:{T['text_primary']};
      --muted:{T['text_secondary']};--line:{T['border']};--brand:{T['brand']};}}
    *{{box-sizing:border-box}}
    body{{margin:0;background:var(--bg);color:var(--ink);
      font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;}}
    .wrap{{max-width:1040px;margin:0 auto;padding:32px 20px 64px;}}
    header{{padding-bottom:16px;border-bottom:1px solid var(--line);}}
    h1{{font-size:28px;margin:0;}} h2{{font-size:20px;margin:32px 0 8px;}}
    h3{{font-size:17px;margin:24px 0 8px;}}
    .sub{{color:var(--muted);font-size:14px;}}
    .pills span{{display:inline-block;border:1px solid var(--muted);border-radius:999px;
      padding:3px 10px;margin:8px 8px 0 0;font-size:13px;color:var(--muted);}}
    section{{background:var(--surface);border:1px solid var(--line);border-radius:14px;
      padding:20px 24px;margin-top:20px;}}
    table{{border-collapse:collapse;width:100%;font-size:14px;}}
    th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);
      vertical-align:top;}}
    th{{color:var(--muted);font-weight:600;font-size:13px;}}
    .scroll{{overflow-x:auto;}}
    .muted{{color:var(--muted);}}
    figure{{margin:16px 0;}} img{{max-width:100%;height:auto;border:1px solid var(--line);
      border-radius:10px;}}
    figcaption{{color:var(--muted);font-size:13px;padding-top:6px;}}
    a{{color:var(--brand);}}
    @media(max-width:640px){{.wrap{{padding:20px 14px 48px}} h1{{font-size:23px}}}}
    """

    kpi_rows = [[k["label"], f"{k['value']} {k['unit']}", k["delta"] or "—",
                 k["period"], k["source"], k["confidence"], k["interpretation"]]
                for k in b["kpis"]]

    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BIZSoft Growth Intelligence — {ru_date_full(date)}</title>
<style>{css}</style></head><body><div class="wrap">
<header><h1>BIZSoft Growth Intelligence</h1>
<div class="sub">Daily Search, Demand &amp; Experiment Control · {ru_date_full(date)}</div>
<div class="pills">{''.join(f"<span>{p['label']}: {p['text']}</span>" for p in b['pills'])}</div>
<div class="sub">{b['sources_line']}</div></header>

<section><h2>Итог дня</h2>
<p><b>От вас:</b> {b['user_action']}</p>
{table(["Показатель", "Значение", "Изменение", "Период", "Источник", "Достоверность", "Что это значит"], kpi_rows)}
</section>

<section><h2>Сигналы дня</h2>
{table(["Показатель", "Было", "Стало", "Изменение", "Достоверность", "Что это значит"],
       [[s['metric'], s['previous'], s['current'], s['delta'], s['confidence'], s['meaning']]
        for s in b['signals']])}</section>

<section><h2>Что дало изменение</h2>{drivers}</section>

<section><h2>Контроль экспериментов</h2>{exps}</section>

<section><h2>Журнал исполнения</h2>{board}</section>

<section><h2>Радар возможностей</h2>{opp}</section>

<section><h2>Графики</h2>{charts or "<p class='muted'>Графиков нет.</p>"}</section>

<section><h2>Карта измерений</h2>
<p>{b['measurement_summary']}</p>
{mmap}</section>

<section><h2>Качество данных</h2>
<p><b>{PILL_LABEL[b['health']['status']].capitalize()}:</b> {b['health']['reason']}. {b['health']['detail']}</p>
{findings}</section>

<section><h2>Запросы Яндекса (выборка топ-100)</h2>{queries}</section>
<section><h2>Страницы в Google</h2>{pages}</section>
<section><h2>Запросы Google</h2>{gq}</section>

<section><h2>Методика</h2>
<p>Полное описание — <a href="{BLOB}/docs/seo/reporting-methodology.md">reporting-methodology.md</a>.
Тикеты и журнал работ — <a href="{REPO}/tree/{b['links']['web'] and 'claude/biz-soft-rating-tracking-5rf03g'}/reports/seo/tasks">reports/seo/tasks</a>.</p>
</section>
</div></body></html>"""


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    snap = json.loads((BASE / "snapshots" / f"{date}.json").read_text(encoding="utf-8"))
    prev = report_v2.prev_snapshot(date)
    dq = json.loads((BASE / "data-quality" / f"{date}.json").read_text(encoding="utf-8"))
    actions_cfg = json.loads((BASE / "actions.json").read_text(encoding="utf-8"))
    b = assemble(snap, prev, dq, actions_cfg, load_site_check(date))

    out = OUT / date
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(build_html(b, snap, dq, date), encoding="utf-8")
    print(f"веб-отчёт: {out / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
