"""Секции детализации письма — второй уровень под executive-блоком.

Разделение уровней (уточнение руководителя 31.08): верхний уровень письма —
до 1000 видимых символов, ниже идёт детализация, по информативности не
уступающая ежедневному SEO-письму. Гейт качества считает лимит только по
верхнему уровню.

Графика сделана на HTML и CSS, а не картинками. Причина практическая:
почтовые клиенты блокируют внешние изображения, а вложения через CID
требуют сборки PNG в прогоне (лишняя зависимость и лишняя точка отказа).
Цветные полосы на таблицах читаются везде, масштабируются и ничего не
весят. Линейные графики трендов появятся, когда накопится история — сейчас
её один день, и рисовать линию не по чему.
"""
from __future__ import annotations

import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from competitors import classifier  # noqa: E402
from decision_engine import kpi as kpi_mod  # noqa: E402

INK = "#101828"
MUTED = "#667085"
LINE = "#EAECF0"
BRAND = "#F4511E"
DANGER = "#D92D20"
OURS = "biz-soft.pro"


def esc(value) -> str:
    return html.escape(str(value if value is not None else "—"))


def pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "нет данных"
    return kpi_mod.ru_number(100 * value, digits) + "%"


SOURCE_NAMES = {
    "wordstat": "частотность Wordstat, за месяц",
    "webmaster": "показы Вебмастера, за две недели",
}


def format_demand(pkg: dict) -> str:
    """Спрос по источникам, без суммирования разнородных величин."""
    by_source = pkg.get("demand_by_source") or {}
    queries = pkg.get("demand_queries_by_source") or {}
    if not by_source:
        return "спрос не измерен"
    parts = []
    for source, value in sorted(by_source.items(), key=lambda kv: -kv[1]):
        name = SOURCE_NAMES.get(source, source)
        count = queries.get(source, 0)
        parts.append(f"{value} ({name}) по {count} запр.")
    return "спрос: " + "; ".join(parts)


def _heading(title: str, hint: str = "") -> str:
    hint_html = (f'<span style="font-weight:400;color:{MUTED};"> — {esc(hint)}</span>'
                 if hint else "")
    return (f'<tr><td style="padding:22px 24px 6px;">'
            f'<div style="font-size:11px;color:{MUTED};letter-spacing:.06em;'
            f'font-weight:700;text-transform:uppercase;">{esc(title)}{hint_html}</div>'
            f'</td></tr>')


def _table(rows_html: str, head_html: str = "") -> str:
    return (f'<tr><td style="padding:6px 24px 0;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;font-size:13px;">{head_html}{rows_html}'
            f'</table></td></tr>')


def _th(text: str, align: str = "left") -> str:
    return (f'<th align="{align}" style="padding:4px 6px;font-size:10px;color:{MUTED};'
            f'text-transform:uppercase;letter-spacing:.04em;font-weight:600;'
            f'border-bottom:1px solid {LINE};">{esc(text)}</th>')


def _td(text: str, *, align: str = "left", bold: bool = False,
        color: str = INK, small: bool = False) -> str:
    weight = "600" if bold else "400"
    size = "11px" if small else "13px"
    return (f'<td align="{align}" style="padding:6px;border-bottom:1px solid {LINE};'
            f'font-weight:{weight};color:{color};font-size:{size};'
            f'font-variant-numeric:tabular-nums;">{text}</td>')


def kpi_section(kpi, snapshot: dict, signal_delta: float | None = None) -> str:
    """Показатели с источником и оценкой достоверности — как в SEO-письме.

    Две дельты различаются намеренно (замечание внешнего аудита): суточная
    справочна, а вердикт и главный сигнал строятся на сглаженной. Без этого
    возникал бы вопрос, почему при заметном движении за сутки вердикт
    остаётся нейтральным.
    """
    coverage = snapshot.get("покрытие") or {}
    usable = coverage.get("яндекс_запросов_с_данными")
    delta_text = kpi_mod.format_delta(kpi.share_delta_pp, unit=" п.п.")
    if signal_delta is not None:
        delta_text += f" · сигнальная {kpi_mod.format_delta(signal_delta, unit=' п.п.')}"
    google = snapshot.get("google") or {}
    if google:
        google_row = ("Доля видимости в Google",
                      kpi_mod.format_share(google.get("наша_доля_видимости")),
                      "н/д",
                      f"Google, {google.get('гео', 'Россия')}, "
                      f"{google.get('запросов_с_данными')} запросов, "
                      f"глубина {google.get('глубина', 10)}, "
                      f"срез {google.get('дата_среза')}")
    else:
        google_row = ("Доля видимости в Google", "нет данных", "н/д",
                      "Google-среза за эту дату нет (сбор еженедельный)")
    rows = [
        ("Доля видимости в Яндексе", kpi_mod.format_share(kpi.share_yandex),
         delta_text,
         f"Яндекс, Москва, {usable} запросов"),
        ("Запросов в ТОП-3", f"{kpi.top3} из {kpi.queries}",
         kpi_mod.format_delta(kpi.top3_delta), "срез выдачи"),
        ("Запросов в ТОП-10", f"{kpi.top10} из {kpi.queries}",
         kpi_mod.format_delta(kpi.top10_delta), "срез выдачи"),
        google_row,
    ]
    body = "".join(
        f'<tr>{_td(esc(name))}{_td(esc(value), align="right", bold=True)}'
        f'{_td(esc(delta), align="right", color=MUTED)}'
        f'{_td(esc(source), color=MUTED, small=True)}</tr>'
        for name, value, delta, source in rows)
    head = (f'<tr>{_th("Показатель")}{_th("Значение", "right")}'
            f'{_th("Δ к прошлому", "right")}{_th("Источник")}</tr>')
    return _heading("Показатели") + _table(body, head)


def field_section(snapshot: dict) -> str:
    """Кто держит коммерческую выдачу — с полосами вместо картинки."""
    shares = snapshot.get("доли_по_категориям") or {}
    leaders = snapshot.get("лидеры") or []
    if not shares:
        return ""
    top_value = max(shares.values())
    rows = []
    for cat, share in sorted(shares.items(), key=lambda kv: kv[1], reverse=True)[:5]:
        name = classifier.CATEGORY_NAMES.get(cat, cat)
        in_rank = classifier.in_main_ranking(cat)
        who = ", ".join(d["домен"] for d in leaders
                        if d.get("категория") == cat)[:46]
        width = max(2, round(100 * share / top_value))
        color = BRAND if in_rank else "#B9C0CA"
        bar = (f'<table role="presentation" cellpadding="0" cellspacing="0" '
               f'style="width:100%;"><tr>'
               f'<td style="background:{color};height:8px;width:{width}%;'
               f'border-radius:4px;font-size:0;line-height:0;">&nbsp;</td>'
               f'<td style="font-size:0;line-height:0;">&nbsp;</td></tr></table>')
        suffix = "" if in_rank else f' <span style="color:{MUTED};">(вне рейтинга)</span>'
        who_text = esc(who) if who else "—"
        rows.append(
            f'<tr>{_td(esc(name) + suffix)}'
            f'{_td(pct(share), align="right", bold=in_rank)}'
            f'{_td(bar)}{_td(who_text, color=MUTED, small=True)}</tr>')
    head = (f'<tr>{_th("Категория")}{_th("Доля", "right")}{_th("")}{_th("Кто внутри")}</tr>')
    return (_heading("Кто держит выдачу", "доля взвешенной видимости")
            + _table("".join(rows), head))


def rivals_section(leaders: list[dict], ranked: list, limit: int = 5) -> str:
    """Конкуренты по уровню угрозы."""
    if not ranked:
        return ""
    rows = []
    for card, threat in ranked[:limit]:
        cat = card.get("категория", "?")
        rows.append(
            f'<tr>{_td(esc(card["домен"]), bold=True)}'
            f'{_td(esc(classifier.CATEGORY_NAMES.get(cat, cat)), color=MUTED, small=True)}'
            f'{_td(pct(card.get("доля")), align="right")}'
            f'{_td(esc(card.get("топ3")), align="right")}'
            f'{_td(str(threat.score), align="right", bold=True, color=DANGER)}</tr>')
    head = (f'<tr>{_th("Конкурент")}{_th("Кто это")}{_th("Доля", "right")}'
            f'{_th("ТОП-3", "right")}{_th("Угроза", "right")}</tr>')
    return (_heading("Кто давит сильнее всего", "угроза 0–100: доля, позиции, динамика")
            + _table("".join(rows), head))


def google_section(snapshot: dict, limit: int = 8) -> str:
    """Google по России: кто держит выдачу и где мы. Отдельный движок —
    отдельная таблица; доли с Яндексом не складываются, глубина 10."""
    google = snapshot.get("google")
    if not google:
        return ""
    ours_share = kpi_mod.format_share(google.get("наша_доля_видимости"))
    rows_html = "".join(
        f'<tr>{_td(esc(item["домен"]), bold=True)}'
        f'{_td(esc(item.get("категория") or "—"), color=MUTED, small=True)}'
        f'{_td(kpi_mod.format_share(item.get("доля")), align="right")}'
        f'{_td(str(item.get("топ3", 0)), align="right")}'
        f'{_td(str(item.get("топ10", 0)), align="right")}</tr>'
        for item in (google.get("лидеры") or [])[:limit])
    rows_html += (
        f'<tr>{_td("biz-soft.pro (мы)", bold=True)}'
        f'{_td("—", color=MUTED, small=True)}'
        f'{_td(ours_share, align="right", bold=True)}'
        f'{_td(str(google.get("топ3", 0)), align="right", bold=True)}'
        f'{_td(str(google.get("топ10", 0)), align="right", bold=True)}</tr>')
    head = (f'<tr>{_th("Домен")}{_th("Категория")}{_th("Доля", "right")}'
            f'{_th("ТОП-3", "right")}{_th("ТОП-10", "right")}</tr>')
    ours_queries = google.get("наши_запросы") or []
    if ours_queries:
        examples = ", ".join(f"«{q['запрос']}» — {q['позиция']}"
                             for q in ours_queries[:5])
        note = f"Мы в ТОП-10 Google: {examples}."
    else:
        note = (f"biz-soft.pro в ТОП-10 Google нет ни по одному из "
                f"{google.get('запросов_с_данными')} запросов ядра — "
                f"самостоятельный сигнал, не ошибка сбора.")
    note_html = (f'<tr><td colspan="5" style="padding:6px 6px 0;font-size:12px;'
                 f'color:{MUTED};line-height:1.45;">{esc(note)}</td></tr>')
    return (_heading("Google по России",
                     f"{google.get('гео', 'Россия')}, xmlriver, глубина "
                     f"{google.get('глубина', 10)}, "
                     f"{google.get('запросов_с_данными')} запросов, срез "
                     f"{google.get('дата_среза')}; доли внутри Google-поля")
            + _table(rows_html + note_html, head))


def attacks_section(attacks: list[dict], limit: int = 5) -> str:
    """Точки атаки — где ближе всего рост."""
    if not attacks:
        return ""
    rows = []
    for a in attacks[:limit]:
        rows.append(
            f'<tr>{_td(esc(a["attack_id"]), color=MUTED, small=True)}'
            f'{_td(esc(a["query"][:44]))}'
            f'{_td("№" + str(a["our_position"]), align="right")}'
            f'{_td(esc(a["rival_domain"][:20]) + " №" + str(a["rival_position"]), color=MUTED, small=True)}'
            f'{_td(str(a["opportunity"]), align="right", bold=True)}'
            f'{_td(esc(a["confidence"]), color=MUTED, small=True)}</tr>')
    head = (f'<tr>{_th("ID")}{_th("Запрос")}{_th("Мы", "right")}{_th("Выше нас")}'
            f'{_th("Выгода", "right")}{_th("Увер.")}</tr>')
    return (_heading("Где ближе всего рост", "мы на 4–20, выше — конкурент за ту же сделку")
            + _table("".join(rows), head))


def packages_section(packages: list[dict], limit: int = 3) -> str:
    """Что поручить — пакеты работ вместо списка запросов.

    Руководителю нужна не витрина запросов, а поручение: какую страницу
    доработать, сколько запросов это закроет, что даст и сколько стоит.
    Поэтому каждая строка — законченная единица работы.
    """
    if not packages:
        return ""
    blocks = []
    for pkg in packages[:limit]:
        upside = (f' · при выходе в ТОП-3 ≈ +{pkg["traffic_upside"]:.0f} переходов'
                  if pkg.get("traffic_upside") is not None else "")
        demand_text = format_demand(pkg)
        # В письме — первые шаги ТЗ, а не чеклист приёмки: руководителю нужно
        # понять, что именно он поручает. Полное ТЗ с обоснованием и приёмкой
        # по каждому шагу — в отчёте.
        actions = pkg.get("действия") or []
        checks = "".join(
            f'<li style="margin:2px 0;">{esc(a["what"])} '
            f'<span style="color:{MUTED};">({esc(a["effort"])}, {esc(a["owner"])})</span></li>'
            for a in actions[:3])
        if not checks:
            checks = "".join(
                f'<li style="margin:2px 0;">{esc(c)}</li>'
                for c in (pkg.get("checklist") or [])[:3])
        queries = ", ".join(f"«{q}»" for q in (pkg.get("queries") or [])[:3])
        more = (f" и ещё {pkg['queries_count'] - 3}"
                if pkg["queries_count"] > 3 else "")
        url_short = pkg["url"].replace("https://biz-soft.pro", "")
        done = pkg.get("уже_сделано") or []
        done_line = (
            f'<div style="font-size:11px;color:{MUTED};padding-top:4px;">'
            f'Проверено и работ не требует: {esc("; ".join(done))}</div>'
            if done else "")
        blocks.append(f"""
<tr><td style="padding:10px 24px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="border:1px solid {LINE};border-radius:8px;">
  <tr><td style="padding:12px 14px;">
    <div style="font-size:13px;font-weight:700;color:{INK};line-height:1.4;">
      {esc(pkg["package_id"])} · {esc(pkg["action"])}</div>
    <div style="font-size:12px;color:{MUTED};padding-top:5px;line-height:1.5;">
      Страница: <span style="color:{INK};">{esc(url_short)}</span><br>
      Закроет запросов: <b style="color:{INK};">{pkg["queries_count"]}</b> ·
      {demand_text} ·
      сейчас позиции {pkg["position_best"]}–{pkg["position_worst"]} ·
      выше нас {esc(", ".join(pkg["rivals"][:2]))}<br>
      Потенциал: <b style="color:{BRAND};">{esc(pkg["potential_label"])}</b>{upside} ·
      спрос измерен по {esc(pkg.get("demand_coverage", "0/0"))} запросам ·
      трудоёмкость {esc(pkg["effort"])} · уверенность {esc(pkg["confidence"])}
    </div>
    <div style="font-size:12px;color:{MUTED};padding-top:6px;">Что сделать:</div>
    <ul style="font-size:12px;color:{MUTED};margin:2px 0 0;padding-left:18px;
               line-height:1.45;">{checks}</ul>
    <div style="font-size:11px;color:{MUTED};padding-top:6px;">
      Запросы: {esc(queries)}{esc(more)}</div>
    {done_line}
  </td></tr></table>
</td></tr>""")
    return (_heading("Что поручить", "пакеты работ по убыванию ожидаемого эффекта")
            + "".join(blocks))


def options_section(packages: list[dict]) -> str:
    """Варианты действий — чтобы решение принималось из альтернатив.

    Одно «сделайте это» не даёт руководителю выбора. Три сценария с ценой и
    отдачей позволяют выбрать темп, а не только согласиться.
    """
    if not packages:
        return ""
    def effect(group: list[dict]) -> str:
        """Отдача варианта. Переходы называются только там, где весь спрос
        измерен сопоставимой шкалой; иначе — охват и доля высокого
        потенциала, без перевода в клики."""
        countable = [p for p in group if p.get("traffic_upside") is not None]
        high = sum(1 for p in group if p.get("potential_label") == "высокий")
        if countable and len(countable) == len(group):
            return f"≈ +{sum(p['traffic_upside'] for p in countable):.0f} переходов"
        base = f"{len(group)} страниц, из них {high} с высоким потенциалом"
        if countable:
            return (base + f"; переходы считаются для {len(countable)}: "
                    f"≈ +{sum(p['traffic_upside'] for p in countable):.0f}")
        return base

    quick = [p for p in packages if p["effort"] == "S"][:3]
    top3 = packages[:3]

    options = [
        ("Минимум",
         f"{len(quick)} лёгких пакета" if quick else "нет лёгких пакетов",
         effect(quick),
         "правки текста на существующих страницах, без новых материалов"),
        ("Оптимум",
         f"{len(top3)} верхних пакета",
         effect(top3),
         "включает страницы с наибольшим потенциалом; часть требует переработки"),
        ("Полный охват",
         f"все {len(packages)} пакетов",
         effect(packages),
         "весь список целей; имеет смысл растянуть на несколько недель"),
    ]
    rows = "".join(
        f'<tr>{_td(esc(name), bold=True)}{_td(esc(scope))}'
        f'{_td(esc(effect), align="right", color=BRAND, bold=True)}'
        f'{_td(esc(note), color=MUTED, small=True)}</tr>'
        for name, scope, effect, note in options)
    head = (f'<tr>{_th("Вариант")}{_th("Объём")}{_th("Отдача", "right")}'
            f'{_th("Чем отличается")}</tr>')
    return (_heading("Варианты действий", "потенциал, а не обещание: переходы называются только при сопоставимом спросе")
            + _table(rows, head))


def experiments_section(line: str, on_watch: list[dict] | None = None) -> str:
    """Ход цикла проверки: что внедрено, что на замере, чему научились.

    Раздел стоит внизу письма намеренно. Верхний уровень отвечает на вопрос
    «что делать сегодня», а этот — на вопрос «что стало с тем, что делали
    раньше»: это отчётность о ходе работ, и вытеснять ею решение дня нельзя.
    """
    if not line:
        return ""
    watch = on_watch or []
    frozen = ""
    if watch:
        rows = "".join(
            f'<li style="margin:2px 0;">{esc(p["url"].replace("https://biz-soft.pro", ""))} '
            f'— замер до {esc(p.get("мораторий_до", ""))} '
            f'({esc(p.get("эксперимент", ""))})</li>' for p in watch[:5])
        frozen = (f'<div style="font-size:12px;color:{MUTED};padding-top:6px;">'
                  f'Под мораторием — правка внесена, идёт замер эффекта, '
                  f'новых поручений по этим страницам сегодня нет:</div>'
                  f'<ul style="font-size:12px;color:{MUTED};margin:2px 0 0;'
                  f'padding-left:18px;line-height:1.45;">{rows}</ul>')
    body = (
        f'<tr><td style="padding:6px 24px 0;">'
        f'<div style="font-size:13px;color:{INK};line-height:1.5;">{esc(line)}</div>'
        f'{frozen}'
        f'<div style="font-size:11px;color:{MUTED};padding-top:6px;">'
        f'Эффект считается разностью разностей: изменение позиций по запросам '
        f'эксперимента минус изменение по запросам, где мы ничего не трогали. '
        f'Это наблюдение, а не доказательство — A/B-теста на поисковой выдаче '
        f'не существует. Полная таблица «было → стало» — в отчёте, раздел 6.'
        f'</div></td></tr>')
    return _heading("Эксперименты",
                    "судьба выданных поручений: внедрение, мораторий на время "
                    "замера, эффект") + body


def limits_section(snapshot: dict, attacks: list[dict]) -> str:
    """Границы данных: что система пока не знает. Честность важнее полноты."""
    coverage = snapshot.get("покрытие") or {}
    unknown = snapshot.get("не_классифицировано")
    by_webmaster = sum(1 for a in attacks if a.get("demand_source") == "webmaster")
    items = [
        "Уязвимость страниц конкурентов не измеряется — нужен их обход; "
        "до этого уверенность рекомендаций не выше средней.",
        "Выручка по запросам не измерена: показана оценка «спрос × коммерческий "
        "интент», а не деньги.",
        f"Спрос по {by_webmaster} из {len(attacks)} точек атаки взят из показов "
        "Вебмастера, а не из частотности Wordstat — шкалы разные.",
        f"{unknown} доменов выдачи не классифицированы и в рейтинг не включены.",
        (f"Google собирается еженедельно (xmlriver, Россия) на глубину "
         f"{(snapshot.get('google') or {}).get('глубина', 10)} позиций; "
         "позиции 11–20 сервис не отдаёт — вопрос в его поддержке. Доли Google "
         "и Яндекса считаются внутри своих полей и не складываются."
         if snapshot.get("google") else
         "Google-среза за эту дату нет: сбор еженедельный (xmlriver, Россия, "
         "топ-10), блок заполнится ближайшим срезом."),
    ]
    body = "".join(
        f'<tr><td style="padding:3px 6px;font-size:12px;color:{MUTED};'
        f'line-height:1.45;">• {esc(text)}</td></tr>' for text in items)
    return (_heading("Что система пока не знает", "чтобы цифры не читались шире, чем они есть")
            + _table(body))
