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


def kpi_section(kpi, snapshot: dict) -> str:
    """Показатели с источником и оценкой достоверности — как в SEO-письме."""
    coverage = snapshot.get("покрытие") or {}
    usable = coverage.get("яндекс_запросов_с_данными")
    rows = [
        ("Доля видимости в Яндексе", kpi_mod.format_share(kpi.share_yandex),
         kpi_mod.format_delta(kpi.share_delta_pp, unit=" п.п."),
         f"Яндекс, Москва, {usable} запросов"),
        ("Запросов в ТОП-3", f"{kpi.top3} из {kpi.queries}",
         kpi_mod.format_delta(kpi.top3_delta), "срез выдачи"),
        ("Запросов в ТОП-10", f"{kpi.top10} из {kpi.queries}",
         kpi_mod.format_delta(kpi.top10_delta), "срез выдачи"),
        ("Доля видимости в Google", "нет данных", "н/д",
         "еженедельный сбор не запущен"),
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
        checks = "".join(
            f'<li style="margin:2px 0;">{esc(c)}</li>'
            for c in (pkg.get("checklist") or [])[:3])
        queries = ", ".join(f"«{q}»" for q in (pkg.get("queries") or [])[:3])
        more = (f" и ещё {pkg['queries_count'] - 3}"
                if pkg["queries_count"] > 3 else "")
        url_short = pkg["url"].replace("https://biz-soft.pro", "")
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
      спрос <b style="color:{INK};">{pkg["demand_total"]}</b> ·
      сейчас позиции {pkg["position_best"]}–{pkg["position_worst"]} ·
      выше нас {esc(", ".join(pkg["rivals"][:2]))}<br>
      Даст при выходе в ТОП-3: <b style="color:{BRAND};">
      ≈ +{pkg["uplift_estimate"]:.0f} переходов</b> за тот же период ·
      трудоёмкость {esc(pkg["effort"])} · уверенность {esc(pkg["confidence"])}
    </div>
    <div style="font-size:12px;color:{MUTED};padding-top:6px;">Что проверить:</div>
    <ul style="font-size:12px;color:{MUTED};margin:2px 0 0;padding-left:18px;
               line-height:1.45;">{checks}</ul>
    <div style="font-size:11px;color:{MUTED};padding-top:6px;">
      Запросы: {esc(queries)}{esc(more)}</div>
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
    quick = [p for p in packages if p["effort"] == "S"][:3]
    total_quick = sum(p["uplift_estimate"] for p in quick)
    top3 = packages[:3]
    total_top3 = sum(p["uplift_estimate"] for p in top3)
    all_uplift = sum(p["uplift_estimate"] for p in packages)

    options = [
        ("Минимум",
         f"{len(quick)} лёгких пакета" if quick else "нет лёгких пакетов",
         f"≈ +{total_quick:.0f} переходов",
         "правки текста на существующих страницах, без новых материалов"),
        ("Оптимум",
         f"{len(top3)} верхних пакета",
         f"≈ +{total_top3:.0f} переходов",
         "включает страницы с наибольшим спросом; часть требует переработки"),
        ("Полный охват",
         f"все {len(packages)} пакетов",
         f"≈ +{all_uplift:.0f} переходов",
         "весь список целей; имеет смысл растянуть на несколько недель"),
    ]
    rows = "".join(
        f'<tr>{_td(esc(name), bold=True)}{_td(esc(scope))}'
        f'{_td(esc(effect), align="right", color=BRAND, bold=True)}'
        f'{_td(esc(note), color=MUTED, small=True)}</tr>'
        for name, scope, effect, note in options)
    head = (f'<tr>{_th("Вариант")}{_th("Объём")}{_th("Отдача", "right")}'
            f'{_th("Чем отличается")}</tr>')
    return (_heading("Варианты действий", "оценка по кривой CTR при выходе в ТОП-3, не обещание")
            + _table(rows, head))


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
        "Google не собирается: раздел заполнится после первого еженедельного среза.",
    ]
    body = "".join(
        f'<tr><td style="padding:3px 6px;font-size:12px;color:{MUTED};'
        f'line-height:1.45;">• {esc(text)}</td></tr>' for text in items)
    return (_heading("Что система пока не знает", "чтобы цифры не читались шире, чем они есть")
            + _table(body))
