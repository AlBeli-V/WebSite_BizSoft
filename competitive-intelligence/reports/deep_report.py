#!/usr/bin/env python3
"""Deep Competitive Report — то, что письмо объясняет ссылкой.

Разделение из раздела 33 задания: EMAIL = решение, DEEP REPORT = объяснение,
COMPETITOR PAGE = разведка, ATTACK PAGE = план, EVIDENCE = доказательства.
Письмо намеренно короткое (лимит 1000 символов), вся детализация — здесь.

Уровни (раздел 25):
  L1 Executive Dashboard — куда мы движемся и кто давит;
  L2 Competitor Leaderboard — полная таблица конкурентов с метриками;
  L3 Competitor Page — карточка каждого конкурента: след, запросы, страницы;
  L4 Attack Detail — Strike List целиком и разбор каждой точки атаки;
  L5 Raw Evidence — исходные строки выдачи, на которых всё построено.
  L6 Experiments — судьба выданных поручений: внедрение, мораторий, эффект.

Отчёт статический: один самодостаточный HTML без внешних зависимостей, чтобы
открывался с телефона и не зависел от CDN.
"""
from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402
from competitors import classifier  # noqa: E402
from scoring import threat as threat_mod  # noqa: E402

MSK = timezone(timedelta(hours=3))
OURS = "biz-soft.pro"


def esc(value) -> str:
    return html.escape(str(value if value is not None else "—"))


def pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "н/д"
    return f"{100 * value:.{digits}f}".replace(".", ",") + "%"


def _styles() -> str:
    return """
:root{--ink:#101828;--muted:#667085;--line:#EAECF0;--bg:#F9FAFB;
      --ok:#12B76A;--bad:#D92D20;--brand:#F4511E;--accent:#175CD3;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
     font:15px/1.55 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Arial,sans-serif;}
.wrap{max-width:1120px;margin:0 auto;padding:24px 16px 64px;}
h1{font-size:24px;margin:0 0 6px;letter-spacing:-.01em}
h2{font-size:19px;margin:36px 0 6px;padding-top:18px;border-top:2px solid var(--line);}
h3{font-size:15px;margin:22px 0 8px}
.sub{color:var(--muted);font-size:13px}
.lead{font-size:15px;color:var(--muted);margin:6px 0 0;max-width:70ch}
nav{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:18px 0}
nav a{color:var(--accent);text-decoration:none;margin-right:18px;font-size:13px;white-space:nowrap}
nav a:hover{text-decoration:underline}
.cards{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}
.card{flex:1 1 160px;background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px}
.card .k{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.card .v{font-size:26px;font-weight:700;line-height:1.2;margin-top:2px}
.card .d{font-size:12px;color:var(--muted);margin-top:2px}
.scroll{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:10px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;
   text-align:left;padding:10px;border-bottom:1px solid var(--line);white-space:nowrap;
   position:sticky;top:0;background:#fff}
td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
tr:hover td{background:#FCFCFD}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.us td{background:#FFF7ED!important;font-weight:600}
.tag{display:inline-block;font-size:11px;padding:2px 8px;border-radius:20px;
     border:1px solid var(--line);color:var(--muted);white-space:nowrap}
.tag.H{background:#FEF3F2;color:#B42318;border-color:#FECDCA}
.tag.A,.tag.B{background:#EFF8FF;color:#175CD3;border-color:#B2DDFF}
.tag.E,.tag.G,.tag.F{background:#F8F9FC}
.bar{height:8px;border-radius:4px;background:var(--line);overflow:hidden;min-width:60px}
.bar i{display:block;height:100%;background:var(--brand)}
.note{background:#FFFAEB;border:1px solid #FEDF89;border-radius:10px;
      padding:12px 14px;font-size:13px;color:#93370D;margin:14px 0}
.ok{background:#ECFDF3;border-color:#A6F4C5;color:#05603A}
.lbl{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.05em;
     padding:2px 6px;border-radius:4px;margin-right:6px;vertical-align:1px}
.fact{background:#ECFDF3;color:#067647}.likely{background:#FFFAEB;color:#B54708}
.hypo{background:#F4F3FF;color:#5925DC}.act{background:#EFF8FF;color:#175CD3}
.wp-act{border-left:3px solid #175CD3;padding:6px 0 6px 12px;margin:0 0 14px}
.wp-act>b{display:block;font-size:14px;line-height:1.35;margin-bottom:4px}
details{background:#fff;border:1px solid var(--line);border-radius:10px;
        padding:12px 16px;margin:10px 0}
summary{cursor:pointer;font-weight:600;font-size:14px}
summary::marker{color:var(--muted)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
.q{font-size:12px;color:var(--muted);word-break:break-word}
footer{margin-top:48px;padding-top:16px;border-top:1px solid var(--line);
       font-size:12px;color:var(--muted)}
a{color:var(--accent)}
@media(max-width:640px){.wrap{padding:16px 10px 48px}h1{font-size:20px}
  .card .v{font-size:22px}}
"""


def _kpi_cards(snapshot: dict, previous: dict | None, attacks: list[dict]) -> str:
    ours = snapshot.get("наши_показатели") or {}
    prev = (previous or {}).get("наши_показатели") or {}
    # Дельта считается тем же способом, что и в письме: по пересечению
    # составов ядра. Прямая разность долей двух дней сравнивала бы величины,
    # посчитанные в разных полях, — и расширение ядра выглядело бы падением
    # видимости. 01.09 отчёт из-за этого показывал −2,39 п.п. там, где
    # сравнимая дельта была +0,55.
    from decision_engine import kpi as kpi_mod
    delta = "сравнимого дня нет"
    if previous:
        measure = kpi_mod.build_kpi(snapshot, previous)
        if measure.share_delta_pp is not None:
            basis = ("" if not measure.core_changed
                     else f", {measure.comparable_core} общих запросов")
            number = f"{measure.share_delta_pp:+.2f}".replace(".", ",")
            delta = f"{number} п.п. к {previous.get('дата')}{basis}"

    cards = [
        ("B2B Share · Яндекс", pct(ours.get("доля_видимости")), delta),
        ("B2B Share · Google", "NO DATA", "еженедельный сбор ещё не запущен"),
        ("Запросов в ТОП-3", f"{ours.get('топ3', '—')}", f"из {ours.get('запросов_в_поле', '—')}"),
        ("Запросов в ТОП-10", f"{ours.get('топ10', '—')}", f"из {ours.get('запросов_в_поле', '—')}"),
        ("Точек атаки", str(len(attacks)), "мы на 4–20, выше конкурент"),
    ]
    return '<div class="cards">' + "".join(
        f'<div class="card"><div class="k">{esc(k)}</div>'
        f'<div class="v">{esc(v)}</div><div class="d">{esc(d)}</div></div>'
        for k, v, d in cards) + "</div>"


def _category_table(snapshot: dict) -> str:
    shares = snapshot.get("доли_по_категориям") or {}
    leaders = snapshot.get("лидеры") or []
    rows = []
    for cat, share in sorted(shares.items(), key=lambda kv: kv[1], reverse=True):
        name = classifier.CATEGORY_NAMES.get(cat, cat)
        in_rank = classifier.in_main_ranking(cat)
        top = [d["домен"] for d in leaders if d.get("категория") == cat][:3]
        width = min(100, 100 * share / max(shares.values()))
        rows.append(
            f'<tr><td><span class="tag {esc(cat)}">{esc(cat)}</span> {esc(name)}</td>'
            f'<td class="num">{pct(share)}</td>'
            f'<td style="width:140px"><div class="bar"><i style="width:{width:.0f}%"></i></div></td>'
            f'<td class="q">{esc(", ".join(top)) if top else "—"}</td>'
            f'<td>{"да" if in_rank else "нет"}</td></tr>')
    return ('<div class="scroll"><table><tr><th>Категория</th>'
            '<th class="num">Доля видимости</th><th></th><th>Кто внутри</th>'
            '<th>В рейтинге</th></tr>' + "".join(rows) + "</table></div>")


def _leaderboard(cards: list[dict], usable: int,
                 histories: dict[str, list[float]] | None = None) -> str:
    ranked = threat_mod.rank([c for c in cards if c["домен"] != OURS],
                             histories=histories or {}, queries_total=usable)
    rows = []
    for position, (card, t) in enumerate(ranked, start=1):
        cat = card.get("категория", "?")
        rows.append(
            f'<tr><td class="num">{position}</td>'
            f'<td><b>{esc(card["домен"])}</b></td>'
            f'<td><span class="tag {esc(cat)}">{esc(classifier.CATEGORY_NAMES.get(cat, cat))}</span></td>'
            f'<td class="num">{pct(card.get("доля"))}</td>'
            f'<td class="num">{esc(card.get("топ3"))}</td>'
            f'<td class="num">{esc(card.get("топ10"))}</td>'
            f'<td class="num"><b>{t.score}</b></td>'
            f'<td class="q">{esc(t.confidence)} · {esc(t.explanation)}</td></tr>')
    return ('<div class="scroll"><table><tr><th class="num">#</th><th>Домен</th>'
            '<th>Категория</th><th class="num">Доля</th><th class="num">ТОП-3</th>'
            '<th class="num">ТОП-10</th><th class="num">Threat</th>'
            '<th>Уверенность и основание</th></tr>' + "".join(rows) + "</table></div>")


def _strike_table(attacks: list[dict]) -> str:
    rows = []
    for a in attacks:
        rows.append(
            f'<tr><td>{esc(a["attack_id"])}</td>'
            f'<td class="num"><b>{a["opportunity"]}</b></td>'
            f'<td>{esc(a["confidence"])}</td>'
            f'<td class="q">{esc(a["query"])}</td>'
            f'<td class="num">{a["our_position"]}</td>'
            f'<td>{esc(a["rival_domain"])} <span class="sub">#{a["rival_position"]}</span></td>'
            f'<td class="num">{esc(a["demand"])}</td>'
            f'<td class="q">{esc(a["demand_source"])}</td>'
            f'<td class="num">{a["commercial_intent"]:.2f}</td>'
            f'<td class="num">{a["b2b_intent"]:.2f}</td></tr>')
    return ('<div class="scroll"><table><tr><th>ID</th><th class="num">Opp.</th>'
            '<th>Увер.</th><th>Запрос</th><th class="num">Наша</th><th>Конкурент</th>'
            '<th class="num">Спрос</th><th>Источник</th><th class="num">Комм.</th>'
            '<th class="num">B2B</th></tr>' + "".join(rows) + "</table></div>")


def _attack_details(attacks: list[dict], limit: int = 10) -> str:
    blocks = []
    for a in attacks[:limit]:
        breakdown = " · ".join(f"{k} {v}" for k, v in (a.get("breakdown") or {}).items())
        notes = "".join(f"<li>{esc(n)}</li>" for n in (a.get("notes") or []))
        our_url = a.get("our_url") or "страницы нет в выдаче"
        blocks.append(f"""
<details><summary>{esc(a['attack_id'])} · Opportunity {a['opportunity']} ·
  «{esc(a['query'])}»</summary>
  <p><span class="lbl fact">ФАКТ</span>BIZSoft на {a['our_position']}-м месте
     ({esc(our_url)}); выше — {esc(a['rival_domain'])} на {a['rival_position']}-м.
     Спрос {esc(a['demand'])} ({esc(a['demand_source'])}), коммерческий интент
     {a['commercial_intent']:.2f}, B2B-интент {a['b2b_intent']:.2f}.</p>
  <p><span class="lbl fact">РАСЧЁТ</span><span class="q">{esc(breakdown)}</span></p>
  <p><span class="lbl likely">ВЕРОЯТНО</span>Конкурент отвечает на тот же
     коммерческий интент, но глубина B2B-содержания его страницы не проверена —
     проверка появится с краулингом конкурентов (Phase 4).</p>
  <p><span class="lbl act">ЧТО СДЕЛАТЬ</span>Усилить нашу страницу под этот
     запрос: явный блок оплаты по счёту для юрлиц, условия лицензирования,
     закрывающие документы и ЭДО, FAQ по покупке на компанию.
     Контроль: 14 / 30 / 60 дней по позиции и кликам Вебмастера.</p>
  <ul class="q">{notes}</ul>
</details>""")
    return "".join(blocks)


def _competitor_pages(cards: list[dict], full_cards: list[dict], limit: int = 8) -> str:
    by_domain = {c["domain"]: c for c in full_cards}
    blocks = []
    # Наш домен в карточки конкурентов не попадает ни при каких условиях.
    for card in [c for c in cards if c["домен"] != OURS][:limit]:
        domain = card["домен"]
        full = by_domain.get(domain, {})
        queries = "".join(f"<li>{esc(q)}</li>"
                          for q in (full.get("query_examples") or [])[:5])
        urls = "".join(f'<li><a href="{esc(u)}" rel="noreferrer nofollow">{esc(u[:90])}</a></li>'
                       for u in (full.get("evidence_urls") or [])[:3])
        cat = card.get("категория", "?")
        blocks.append(f"""
<details><summary>{esc(domain)} — доля {pct(card.get('доля'))},
  ТОП-3 по {esc(card.get('топ3'))} запросам</summary>
  <div class="grid2">
    <div><h3>Кто это</h3>
      <p class="q">Категория: {esc(classifier.CATEGORY_NAMES.get(cat, cat))}.
      B2B Confidence: {esc(full.get('b2b_confidence'))} —
      {'проверка страниц появится в Phase 4' if full.get('b2b_confidence') is None else 'по сигналам страниц'}.
      Лучшая позиция: {esc(full.get('best_position'))}.
      Появлений в выдаче: {esc(full.get('appearances'))}.</p></div>
    <div><h3>По каким запросам виден</h3><ul class="q">{queries}</ul></div>
    <div><h3>Страницы, которыми ранжируется</h3><ul class="q">{urls}</ul></div>
  </div>
</details>""")
    return "".join(blocks)


def _packages_block(packages: list[dict]) -> str:
    """План работ: что поручить, где править, почему и как принять.

    До версии 1.4.0 здесь печаталось описание проблемы и общий чеклист по типу
    страницы. Руководитель проверил первое поручение и увидел, что поручить его
    нельзя: непонятно, что именно и в каком файле менять, а часть советов
    относилась к тому, что на странице уже сделано. Теперь блок печатает
    исполнимое ТЗ, а обоснование приоритета уходит на второй план — оно нужно
    для решения «делать или нет», а не для исполнения.
    """
    if not packages:
        return '<p class="lead">Пакетов работ нет: нет точек атаки.</p>'
    blocks = []
    for pkg in packages:
        queries = "".join(f"<li>{esc(q)}</li>" for q in (pkg.get("queries") or []))
        url_short = pkg["url"].replace("https://biz-soft.pro", "")
        # Каждое действие отвечает на четыре вопроса: что, где, почему и как
        # принять. Без любого из них работу нельзя ни поручить, ни принять.
        actions = "".join(
            f"""
      <div class="wp-act"><b>{esc(a['action_id'])}. {esc(a['what'])}</b>
        <span class="lbl">{esc(a['effort'])} · {esc(a['owner'])}</span>
        <p class="q"><b>Где:</b> {esc(a['where'])}<br>
        <b>Почему:</b> {esc(a['why'])}</p>
        <ul class="q">{"".join(f"<li>{esc(step)}</li>" for step in (a.get('steps') or []))}</ul>
        <p class="q"><b>Приёмка:</b> {esc(a['check'])}</p></div>"""
            for a in (pkg.get("действия") or []))
        if not actions:
            actions = ('<p class="q">действий не сформировано: содержимое '
                       'страницы проверить не удалось</p>')
        done_items = "".join(f"<li>{esc(d)}</li>"
                             for d in (pkg.get("уже_сделано") or []))
        done = (f'<ul class="q">{done_items}</ul>' if done_items else
                '<p class="q">по этой странице ничего из проверяемого '
                'не сделано</p>')
        skip_items = "".join(f"<li>{esc(d)}</li>"
                             for d in (pkg.get("не_рекомендуем") or []))
        skip = f'<ul class="q">{skip_items}</ul>' if skip_items else '<p class="q">—</p>'
        demand = esc("; ".join(
            f"{v} {k} по {pkg.get('demand_queries_by_source', {}).get(k, 0)} запр."
            for k, v in (pkg.get('demand_by_source') or {}).items()) or "не измерен")
        index_text = (("%.3f" % pkg['potential_index'])
                      if pkg.get('potential_index') is not None else "не считается")
        upside = (("Прирост переходов: ≈ +%.0f. " % pkg['traffic_upside'])
                  if pkg.get('traffic_upside') is not None else "")
        blocks.append(f"""
<details><summary>{esc(pkg['package_id'])} · {esc(pkg['action'])} ·
  {pkg['queries_count']} запросов · потенциал {esc(pkg['potential_label'])}</summary>
  <div class="grid2">
    <div><h3>Что сделать</h3>{actions}</div>
    <div><h3>Уже сделано — проверено, работ не требует</h3>{done}
      <h3>Не рекомендуем сейчас</h3>{skip}</div>
    <div><h3>Чем обоснован приоритет</h3>
      <p class="q">Страница: <b>{esc(url_short)}</b> ({esc(pkg['page_kind'])}),
      сейчас позиции {pkg['position_best']}–{pkg['position_worst']}.<br>
      Выше нас: {esc(", ".join(pkg['rivals']))}.<br>
      Спрос по источникам (не суммируется — величины разной природы): {demand}.<br>
      <span class="lbl likely">ОЦЕНКА</span>Индекс потенциала {index_text}
      ({esc(pkg['potential_label'])}) — безразмерная величина для сравнения
      пакетов между собой: прирост веса позиции, умноженный на нормированный
      спрос. Спрос измерен по {esc(pkg.get('demand_coverage', '0/0'))} запросам
      пакета.<br>
      {upside}{esc(pkg['upside_note'])}<br>
      Уверенность оценки: {esc(pkg['confidence'])}.<br>
      <b>Что именно проверено:</b> {esc(pkg.get('проверено_по', 'проверка не проводилась'))}
      (источник: {esc(pkg.get('источник_текста', '—'))}).<br>
      Любая оценка реализуется только если правка действительно поднимет
      страницу.</p></div>
    <div><h3>Какие запросы закрывает</h3><ul class="q">{queries}</ul></div>
  </div>
</details>""")
    return "".join(blocks)


def _experiments_block(experiments: list | None, config: dict | None,
                       on_watch: list[dict] | None) -> str:
    """Уровень 6: что из поручений внедрено и что из этого вышло.

    Раздел закрывает разрыв, из-за которого контур оставался генератором
    предложений: раньше он не знал судьбы своих же рекомендаций, предлагал
    одно и то же и ничему не учился. Здесь три части: страницы под мораторием
    (правка внесена, идёт замер), таблица «было → стало» по завершённым
    экспериментам и вывод по типам действий.
    """
    from experiments import journal as jr
    from experiments import learning as lr

    experiments = experiments or []
    on_watch = on_watch or []
    if not experiments and not on_watch:
        return ('<p class="q">Журнал экспериментов пуст: цикл проверки только '
                'запускается. Первые выводы появятся после того, как поручения '
                'будут внедрены и отстоят срок наблюдения.</p>')

    data = lr.funnel(experiments)
    states = data["по_состояниям"]
    verdicts = data["исходы"]

    watch_rows = "".join(f"""
<tr><td>{esc(e.id)}</td><td>{esc(e.url.replace('https://biz-soft.pro', ''))}</td>
<td>{esc(e.implemented_at)}</td><td>{esc(e.watch_until)}</td>
<td>{esc(str(e.baseline.get('медиана_позиций', '—')))}</td>
<td>{esc(str(len(e.queries)))}</td></tr>"""
        for e in experiments if e.state == jr.STATE_WATCH)
    watch_table = (f"""
<table><thead><tr><th>Опыт</th><th>Страница</th><th>Внедрено</th>
<th>Замер до</th><th>Позиция до</th><th>Запросов</th></tr></thead>
<tbody>{watch_rows}</tbody></table>""" if watch_rows else
        '<p class="q">Под мораторием сейчас никого: внедрённых правок, '
        'ожидающих замера, нет.</p>')

    done_rows = "".join(f"""
<tr><td>{esc(e.id)}</td><td>{esc(e.url.replace('https://biz-soft.pro', ''))}</td>
<td>{esc(", ".join(e.action_kinds))}</td>
<td>{esc(str(e.outcome.get('медиана_до', '—')))}</td>
<td>{esc(str(e.outcome.get('медиана_после', '—')))}</td>
<td>{esc(str(e.outcome.get('контроль_дельта', '—')))}</td>
<td><b>{esc(str(e.outcome.get('чистый_эффект', '—')))}</b></td>
<td>{esc(str(e.outcome.get('вердикт', '—')))}</td>
<td>{esc(str(e.outcome.get('достоверность', '—')))}</td></tr>"""
        for e in experiments if e.state == jr.STATE_DONE)
    done_table = (f"""
<table><thead><tr><th>Опыт</th><th>Страница</th><th>Что делали</th>
<th>Позиция до</th><th>После</th><th>Сдвиг выдачи</th>
<th>Чистый эффект</th><th>Вердикт</th><th>Достоверность</th></tr></thead>
<tbody>{done_rows}</tbody></table>""" if done_rows else
        '<p class="q">Завершённых экспериментов пока нет: ни одно окно '
        'наблюдения ещё не истекло.</p>')

    lesson_rows = "".join(f"""
<tr><td>{esc(row['тип'])}</td><td>{row['наблюдений']}</td>
<td>{row['медианный_эффект_позиций']}</td><td>{row['улучшений']}</td>
<td>{esc(row['вывод'])}</td></tr>"""
        for row in lr.by_action_kind(experiments, config))
    lessons = (f"""
<table><thead><tr><th>Тип действия</th><th>Наблюдений</th>
<th>Медианный эффект, позиций</th><th>Улучшений</th><th>Вывод</th></tr></thead>
<tbody>{lesson_rows}</tbody></table>""" if lesson_rows else
        '<p class="q">Выводов по типам действий пока нет: ни один эксперимент '
        'не доведён до оценки.</p>')

    return f"""
<p class="lead">Предложено {states.get(jr.STATE_PROPOSED, 0)} ·
на наблюдении {states.get(jr.STATE_WATCH, 0)} ·
оценено {states.get(jr.STATE_DONE, 0)} ·
из оценённых улучшение у {verdicts[jr.VERDICT_BETTER]},
без изменений {verdicts[jr.VERDICT_FLAT]},
ухудшение {verdicts[jr.VERDICT_WORSE]}.</p>

<h3>Под мораторием: правка внесена, идёт замер</h3>
<p class="q">Эти страницы намеренно исключены из сегодняшних поручений. Если
предлагать по ним новую работу, измерить эффект уже внесённой правки будет
нельзя: непонятно, какая из двух что сдвинула.</p>
{watch_table}

<h3>Было → стало по завершённым экспериментам</h3>
<p class="q"><b>Как считается эффект.</b> Берётся изменение медианной позиции
по запросам эксперимента и — за тот же период — изменение по всем прочим
запросам ядра, где мы ничего не трогали. Эффектом считается разница между
ними: так общий сдвиг выдачи (апдейт алгоритма, сезонность, уход конкурента)
не записывается в заслугу правки. Отрицательное значение — позиции выросли.
Отсутствие в ТОП-20 считается позицией 21, иначе выпадение из выдачи улучшало
бы среднее. <b>Это наблюдение, а не доказательство:</b> A/B-теста на поисковой
выдаче не существует, и влияние других причин исключить нельзя.</p>
{done_table}

<h3>Чему это учит: какие правки работают</h3>
<p class="q">Пока по типу действия накоплено меньше пяти оценённых
экспериментов, вывода нет и порядок поручений не меняется: подстраивать
приоритет работ под три случайных наблюдения — способ закрепить случайность
в методике.</p>
{lessons}"""


def _meta(snapshot: dict, key: str):
    """Значение из блока метаданных снимка. «н/д» — снимок старого формата."""
    return (snapshot.get("метаданные") or {}).get(key, "н/д")


def build(date: str, snapshot: dict, previous: dict | None,
          attacks: list[dict], full_cards: list[dict], rows,
          packages: list[dict] | None = None,
          histories: dict[str, list[float]] | None = None,
          experiments: list | None = None, config: dict | None = None,
          on_watch: list[dict] | None = None) -> str:
    """Собирает самодостаточный HTML-отчёт."""
    ours = snapshot.get("наши_показатели") or {}
    coverage = snapshot.get("покрытие") or {}
    usable = coverage.get("яндекс_запросов_с_данными") or 0
    leaders = [d for d in (snapshot.get("лидеры") or [])]
    stale = snapshot.get("предупреждение_о_свежести")

    warn = ""
    if stale:
        warn = f'<div class="note">Внимание: {esc(stale)}.</div>'

    maturity = (
        '<div class="note">Зрелость расчёта: <b>базовый</b>. Vulnerability '
        '(насколько позицию конкурента реально отобрать) требует краулинга '
        'страниц конкурентов и появится в Phase 4 — до тех пор его вес '
        'перераспределён на измеримые факторы, а уверенность рекомендаций не '
        'поднимается выше MEDIUM. Экономический фактор в модели отсутствует '
        'вовсе: измеренной выручки по запросам нет, а её оценка через спрос и '
        'интент дублировала бы эти факторы (убрана в версии 1.1.0). Судьба '
        'выданных поручений отслеживается с 01.09.2026 — раздел 6.</div>')

    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Конкурентная разведка · {esc(date)}</title>
<style>{_styles()}</style></head>
<body><div class="wrap">

<h1>Конкурентная разведка BIZSoft</h1>
<div class="sub">Срез за {esc(date)} · Яндекс, Москва (регион 213) ·
  {esc(usable)} запросов · собран {esc(snapshot.get('собран', '')[:16])}</div>
<p class="lead">Отчёт отвечает на пять вопросов: усиливаемся ли мы, кто забирает
наш спрос, на каких запросах, где конкурент уязвим и что даст наибольший
эффект. Письмо содержит только вывод — здесь основания.</p>
{warn}

<nav>
  <a href="#l1">1 · Итоги дня</a>
  <a href="#l2">2 · Конкуренты</a>
  <a href="#l3">3 · Карточки конкурентов</a>
  <a href="#plan">4 · План работ</a>
  <a href="#l4">5 · Точки атаки</a>
  <a href="#exp">6 · Эксперименты</a>
  <a href="#l5">7 · Исходные данные</a>
  <a href="#method">Методика</a>
</nav>

<h2 id="l1">1 · Итоги дня</h2>
{_kpi_cards(snapshot, previous, attacks)}
{maturity}

<h3>Кто держит коммерческую выдачу</h3>
<p class="lead">Доля взвешенной видимости: позиция каждого домена умножается на
вес клика по этой позиции. Категории «B2C и маркетплейсы», «информационные
площадки» и «официальные сайты вендоров» присутствуют в выдаче и забирают
клики, но не конкурируют с нами за сделку, поэтому в основной рейтинг не
входят.</p>
{_category_table(snapshot)}

<h2 id="l2">2 · Конкуренты по уровню угрозы</h2>
<p class="lead">Threat 0–100 — насколько конкурент опасен сейчас: доля
видимости, присутствие в ТОП-3 и ТОП-10 плюс динамика, когда есть с чем
сравнивать. Пока истории меньше двух дней, динамическая часть недоступна,
и уверенность честно понижена.</p>
{_leaderboard(leaders, usable, histories)}

<h2 id="l3">3 · Карточки конкурентов</h2>
<p class="lead">По каждому — на каких запросах он виден и какими страницами
ранжируется. Это и есть материал для разбора: что у них на странице такого,
чего нет у нас.</p>
{_competitor_pages(leaders, full_cards)}

<h2 id="plan">4 · План работ — {len(packages or [])} пакетов</h2>
<p class="lead">Точки атаки, сведённые в поручения. Единица работы — страница:
одна доработка закрывает сразу несколько запросов, и именно её можно поручить
и принять. Порядок — по ожидаемому приросту переходов; суммарная оценка по
пакетам с сопоставимым спросом: +{sum(p['traffic_upside'] or 0 for p in (packages or [])):.0f}
переходов при выходе в ТОП-3 — там, где спрос измерен сопоставимой шкалой.</p>
{_packages_block(packages or [])}

<h2 id="l4">5 · Точки атаки — {len(attacks)} кандидатов</h2>
<p class="lead">Кандидат — запрос, где мы на 4–20 позиции, а выше стоит
конкурент из основного рейтинга. Где мы уже в ТОП-3, отбирать нечего; где
выше только маркетплейсы, мы не конкурируем за сделку. Opportunity 0–100
взвешивает выручку, интент, близость позиции, спрос и запас улучшения
страницы.</p>
{_strike_table(attacks)}

<h3>Разбор первых десяти</h3>
{_attack_details(attacks)}

<h2 id="exp">6 · Эксперименты: что внедрено и что из этого вышло</h2>
<p class="lead">Раздел закрывает петлю обратной связи: поручение → внедрение →
мораторий на время замера → оценка эффекта → вывод для будущих рекомендаций.
Без него контур остаётся генератором предложений, который не знает судьбы
собственных советов.</p>
{_experiments_block(experiments, config, on_watch)}

<h2 id="l5">7 · Исходные данные</h2>
<p class="lead">Всё выше построено на этих строках выдачи. Каждая — запрос,
регион и TOP-20 доменов с URL на момент съёма.</p>
<details><summary>Показать выдачу по первым 20 запросам</summary>
<div class="scroll"><table><tr><th>Запрос</th><th>ТОП-10 доменов</th></tr>
{"".join(f'<tr><td class="q">{esc(r.query)}</td><td class="q">'
         + ", ".join(f"<b>{esc(d.get('domain'))}</b>" if OURS in (d.get('domain') or '')
                     else esc(d.get('domain')) for d in r.top[:10])
         + "</td></tr>" for r in [x for x in rows if x.has_data][:20])}
</table></div></details>

<h2 id="method">Методика и границы</h2>
<div class="grid2">
<details><summary>Как считается доля видимости</summary>
<p class="q">Вес позиции берётся из зафиксированной кривой CTR (1-е место —
0,28, 10-е — 0,018, вне ТОП-20 — ноль); кривая лежит в конфиге и подлежит
калибровке по фактическим показам и кликам. Доля домена — его суммарный вес,
делённый на вес всего поля. Это не доля рынка и не доля трафика, а доля
взвешенной поисковой видимости внутри контролируемого набора запросов.</p></details>
<details><summary>Откуда берутся данные</summary>
<p class="q">Срезы выдачи Яндекса собирает базовый SEO-контур; конкурентная
разведка читает их только на чтение и повторно не покупает. Спрос — частотность
Wordstat, а где её нет — показы Яндекс.Вебмастера (источник указан в таблице
атак, шкалы нормируются раздельно). Google собирается отдельно и еженедельно;
у Google нет геотаргетинга России, поэтому его данные снимаются через
прокси-локацию и не сравнимы с яндексовыми как равноточные.</p></details>
<details><summary>Чего этот отчёт пока не делает</summary>
<p class="q">Не оценивает уязвимость конкретных страниц конкурентов (нужен
краулинг — Phase 4), не измеряет выручку по запросам (нужна привязка к
конверсиям — Phase 5), не отслеживает историю решений и результат внедрений
(уязвимость страниц конкурентов — Phase 4). Отсутствие данных нигде не
показывается как ноль. Судьба поручений с 01.09.2026 отслеживается — см.
раздел 6.</p></details>
</div>

<details><summary>Условия расчёта: чем и по какому полю посчитан этот день</summary>
<p class="q">Версия методики {esc(str(_meta(snapshot, "версия_методики")))} ·
отпечаток конфигурации {esc(str(_meta(snapshot, "хеш_конфига")))} ·
ядро запросов {esc(str(_meta(snapshot, "ядро_версия")))}
({esc(str(_meta(snapshot, "ядро_хеш")))}, {esc(str(_meta(snapshot, "запросов_в_ядре")))} запросов) ·
покрытие по запросам {esc(str(_meta(snapshot, "покрытие_запросов")))} ·
покрытие по спросу {esc(str(_meta(snapshot, "взвешенное_покрытие")))} ·
источники спроса {esc(str(_meta(snapshot, "состав_источников_спроса")))}.<br>
Сравнивать цифры этого дня с другими днями допустимо только при совпадении
версии методики, отпечатка конфигурации и отпечатка ядра; при различии ядра
динамика считается по пересечению составов запросов, а не по полям целиком.
Оценки, полученные в разных режимах зрелости модели, между собой не
сравниваются.</p></details>

<footer>
BIZSoft Competitive Intelligence · отчёт за {esc(date)} ·
методика {esc(str(_meta(snapshot, "версия_методики")))} ·
ядро {esc(str(_meta(snapshot, "ядро_версия")))} ·
собран {esc(datetime.now(MSK).strftime('%d.%m.%Y %H:%M'))} МСК ·
страница не индексируется и не имеет ссылок с сайта
</footer>
</div></body></html>"""


def main(argv: list[str]) -> int:
    sys.path.insert(0, paths.ROOT)
    from decision_engine import kpi as kpi_mod
    from discovery import registry, serp_source
    from scoring import visibility

    dates = kpi_mod.available_snapshots()
    if not dates:
        print("Снимков нет — сначала нужен прогон discovery")
        return 1
    date = argv[1] if len(argv) > 1 else dates[-1]
    snapshot = kpi_mod.load_snapshot(date)
    if snapshot is None:
        print(f"Снимка за {date} нет")
        return 1
    earlier = [d for d in dates if d < date]
    previous = kpi_mod.load_snapshot(earlier[-1]) if earlier else None

    rows = serp_source.read_snapshot(date)
    full_cards = [c.__dict__ for c in
                  registry.build(rows, visibility.load_config(), date=date)]
    strike_path = os.path.join(paths.PROCESSED_DIR, f"{date}-strike-list.json")
    attacks = []
    if os.path.exists(strike_path):
        with open(strike_path, encoding="utf-8") as fh:
            attacks = json.load(fh)
    from attack_engine import work_packages
    packages = work_packages.to_dicts(work_packages.build(attacks))

    histories: dict[str, list[float]] = {}
    for past_date in dates:
        if past_date > date:
            continue
        past = kpi_mod.load_snapshot(past_date) or {}
        for leader in (past.get("лидеры") or []):
            histories.setdefault(leader["домен"], []).append(leader.get("доля") or 0.0)

    page = build(date, snapshot, previous, attacks, full_cards, rows,
                 packages=packages, histories=histories)
    os.makedirs(paths.ARCHIVE_DIR, exist_ok=True)
    archive = os.path.join(paths.ARCHIVE_DIR, f"{date}.html")
    latest = os.path.join(paths.REPORTS_DIR, "latest.html")
    for target in (archive, latest):
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(page)
    size_kb = len(page.encode()) / 1024
    print(f"Отчёт за {date}: {size_kb:.0f} КБ, {len(attacks)} атак, "
          f"{len(full_cards)} доменов")
    print(f"  {archive}")
    print(f"  {latest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
