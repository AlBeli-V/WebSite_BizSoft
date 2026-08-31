#!/usr/bin/env python3
"""Сборка ежедневного письма конкурентной разведки.

Формат зафиксирован разделом 23 задания: VERDICT → KPI → MAIN SIGNAL →
DO NEXT → WATCH. В Phase 1 письмо выходит в MVP-виде (первые три блока плюс
пометка зрелости скоринга); DO NEXT и WATCH появляются в Phase 2 вместе с
Opportunity и Threat.

Два жёстких ограничения, которые проверяются перед отправкой:
  * основная текстовая часть ≤ 1000 видимых символов (оптимум 500–850);
  * письмо читаемо без картинок — графики появятся в Phase 2, и у каждого
    будет alt-текст с цифрами.

Пишет три файла в reports/competitive/: <дата>-email.html, <дата>-email.txt
и <дата>-email.json (метаданные для гейтов качества и анти-повтора).
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402
from decision_engine import kpi as kpi_mod  # noqa: E402
from decision_engine import signal as signal_mod  # noqa: E402
from mailer import sections  # noqa: E402

MSK = timezone(timedelta(hours=3))
TEXT_LIMIT = 1000
# Непубличный путь: угадать нельзя, ссылок с сайта нет, отдаётся с
# X-Robots-Tag noindex. Basic auth не заводится по решению руководителя от
# 31.08 — риск принят; при подозрении на утечку меняется токен пути в
# deploy/nginx-biz-soft.conf.template и здесь.
REPORT_URL = "https://biz-soft.pro/ci-c98370a0ebe87d97/latest.html"


def do_next_text(attack: dict | None, package: dict | None = None) -> str:
    """DO NEXT — одно поручение, а не список и не строка про один запрос.

    Формулируется через пакет работ: страница, охват, ожидаемый эффект.
    Отдельный запрос поручить нельзя — доработка страницы закрывает сразу
    несколько, и именно это решение принимает руководитель.

    Требование раздела 23: Opportunity HIGH при Confidence LOW главным
    действием не делаем. Пока нет ни одного кандидата — честная строка о
    том, что действий нет, а не выдуманное задание.
    """
    if package:
        url_short = package["url"].replace("https://biz-soft.pro", "")
        upside = (f"при выходе в ТОП-3 даст примерно "
                  f"+{package['traffic_upside']:.0f} переходов"
                  if package.get("traffic_upside") is not None
                  else f"потенциал {package['potential_label']}")
        return (f"Что делать: {package['package_id']} — {package['action']} "
                f"({url_short}). Закроет {package['queries_count']} запросов "
                f"со спросом {package['demand_total']}, сейчас позиции "
                f"{package['position_best']}–{package['position_worst']}; "
                f"{upside}. Трудоёмкость {package['effort']}.")
    if not attack:
        return ("Что делать: подтверждённых точек атаки нет — "
                "накапливаем наблюдения.")
    return (f"Что делать: {attack['attack_id']} «{attack['query']}» — "
            f"мы на {attack['our_position']}-м месте, выше "
            f"{attack['rival_domain']} на {attack['rival_position']}-м. "
            f"Opportunity {attack['opportunity']}, "
            f"уверенность {attack['confidence']}.")


def watch_text(threat_leader: tuple[dict, object] | None) -> str:
    """WATCH — одна угроза, а не перечень конкурентов."""
    if not threat_leader:
        return "Следим: угроз выше порога не зафиксировано."
    card, threat = threat_leader
    return (f"Следим: {card['домен']} — Threat {threat.score}, "
            f"топ-3 по {card['топ3']} запросам, доля "
            f"{kpi_mod.ru_number(100 * card['доля'])}%.")


def visible_text(kpi, verdict_mark, verdict_why, signal, *,
                 attack=None, threat_leader=None, package=None) -> str:
    """Основная текстовая часть письма — то, что считается против лимита.

    Ссылки, подписи и футер в лимит не входят (раздел 23), поэтому здесь
    собирается ровно смысловое содержание.
    """
    lines = [
        f"{verdict_mark} {verdict_why}.",
        (f"B2B Share Яндекс {kpi_mod.format_share(kpi.share_yandex)} "
         f"(Δ7д {kpi_mod.format_delta(kpi.share_delta_pp, unit=' п.п.')}) · "
         f"Google {kpi_mod.format_share(kpi.share_google)} · "
         f"ТОП-3 {kpi.top3}/{kpi.queries} · ТОП-10 {kpi.top10}/{kpi.queries}."),
        f"Главный сигнал: {signal.text}",
        do_next_text(attack, package),
        watch_text(threat_leader),
    ]
    return "\n".join(lines)


def pick_attack(attacks: list[dict] | None) -> dict | None:
    """Лучшая точка атаки для DO NEXT.

    Максимальный Opportunity при приемлемой уверенности: высокая
    возможность с уверенностью LOW главным действием не становится
    (раздел 23 задания).
    """
    usable = [a for a in (attacks or []) if a.get("confidence") in ("HIGH", "MEDIUM")]
    if not usable:
        return None
    return max(usable, key=lambda a: a["opportunity"])


def build(date: str, snapshot: dict, previous: dict | None,
          attacks: list[dict] | None = None,
          threat_leader=None, stale_notice: str | None = None,
          ranked_rivals=None, packages: list[dict] | None = None,
          history: list[float] | None = None) -> dict:
    kpi = kpi_mod.build_kpi(snapshot, previous)
    verdict_mark, verdict_why = kpi_mod.verdict(kpi, history)
    if stale_notice:
        # Данные не за сегодня. Показать их можно — они честно датированы, —
        # но вердикт обязан стать «недостаточно данных»: выводы о динамике по
        # вчерашнему срезу были бы выводами о вчерашнем дне, поданными как
        # сегодняшние.
        verdict_mark = kpi_mod.VERDICT_NO_DATA
        verdict_why = f"Данные неполные: {stale_notice}"
    signal = signal_mod.pick(snapshot, previous)
    attack = pick_attack(attacks)
    package = (packages or [None])[0]
    text = visible_text(kpi, verdict_mark, verdict_why, signal,
                        attack=attack, threat_leader=threat_leader,
                        package=package)

    coverage = snapshot.get("покрытие") or {}
    subject = (f"Конкурентная разведка · "
               f"{datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')} · "
               f"{verdict_mark}")

    return {
        "дата": date,
        "тема": subject,
        "вердикт": verdict_mark,
        "текст": text,
        "видимых_символов": len(text),
        "лимит_символов": TEXT_LIMIT,
        "лимит_соблюдён": len(text) <= TEXT_LIMIT,
        "зрелость_скоринга": kpi.maturity,
        "сигнал_тип": signal.kind,
        "сигнал_хэш": hashlib.sha256(signal.text.encode()).hexdigest()[:16],
        "действие": attack,
        "пакет_работ": package,
        "действие_хэш": (
            hashlib.sha256((package or attack or {}).get(
                "package_id", (attack or {}).get("attack_id", "")).encode()
            ).hexdigest()[:16] if (package or attack) else None),
        "кандидатов_в_атаку": len(attacks or []),
        "покрытие": coverage,
        "предупреждение_о_свежести": stale_notice,
        "сравнение_с": kpi.compared_with,
        "kpi": {
            "share_yandex": kpi.share_yandex,
            "share_google": kpi.share_google,
            "top3": kpi.top3,
            "top10": kpi.top10,
            "queries": kpi.queries,
            "share_delta_pp": kpi.share_delta_pp,
        },
    }


def render_txt(meta: dict, *, snapshot: dict | None = None,
               attacks: list[dict] | None = None, ranked_rivals=None,
               packages: list[dict] | None = None) -> str:
    """Текстовая версия — полноценная, а не огрызок для спам-фильтра.

    Повторяет оба уровня письма: executive-часть и детализацию. Клиент,
    отключивший HTML, обязан получить те же сведения, а не обрубок.
    """
    parts = [meta["тема"], "", meta["текст"]]

    if packages:
        parts += ["", "ЧТО ПОРУЧИТЬ (по убыванию ожидаемого эффекта)"]
        for pkg in packages[:3]:
            url_short = pkg["url"].replace("https://biz-soft.pro", "")
            upside = (f"при выходе в ТОП-3 ≈ +{pkg['traffic_upside']:.0f} переходов"
                      if pkg.get("traffic_upside") is not None
                      else f"потенциал {pkg['potential_label']} "
                           f"({pkg['upside_note']})")
            parts.append(
                f"{pkg['package_id']}. {pkg['action']}\n"
                f"   Страница: {url_short}\n"
                f"   Закроет {pkg['queries_count']} запросов, спрос {pkg['demand_total']}, "
                f"сейчас позиции {pkg['position_best']}–{pkg['position_worst']}, "
                f"выше нас {', '.join(pkg['rivals'][:2])}\n"
                f"   {upside} · трудоёмкость {pkg['effort']} · "
                f"уверенность {pkg['confidence']}")
            for check in (pkg.get("checklist") or [])[:3]:
                parts.append(f"   - {check}")

        quick = [p for p in packages if p["effort"] == "S"][:3]

        def effect(group):
            countable = [p for p in group if p.get("traffic_upside") is not None]
            high = sum(1 for p in group if p.get("potential_label") == "высокий")
            if countable and len(countable) == len(group):
                return f"≈ +{sum(p['traffic_upside'] for p in countable):.0f} переходов"
            return f"{len(group)} страниц, из них {high} с высоким потенциалом"

        parts += ["", "ВАРИАНТЫ ДЕЙСТВИЙ (потенциал, не обещание; переходы — "
                      "только при сопоставимом спросе)"]
        parts.append(f"- Минимум: {len(quick)} лёгких пакета — {effect(quick)}, "
                     "правки текста без новых материалов")
        parts.append(f"- Оптимум: 3 верхних пакета — {effect(packages[:3])}, "
                     "страницы с наибольшим потенциалом")
        parts.append(f"- Полный охват: все {len(packages)} пакетов — "
                     f"{effect(packages)}, имеет смысл растянуть на недели")

    if snapshot:
        shares = snapshot.get("доли_по_категориям") or {}
        leaders = snapshot.get("лидеры") or []
        if shares:
            parts += ["", "КТО ДЕРЖИТ ВЫДАЧУ"]
            for cat, share in sorted(shares.items(), key=lambda kv: kv[1],
                                     reverse=True)[:5]:
                name = _classifier().CATEGORY_NAMES.get(cat, cat)
                mark = "" if _classifier().in_main_ranking(cat) else " (вне рейтинга)"
                who = ", ".join(d["домен"] for d in leaders
                                if d.get("категория") == cat)[:50]
                parts.append(f"- {name}{mark}: "
                             f"{kpi_mod.ru_number(100 * share)}%"
                             + (f" — {who}" if who else ""))

    if ranked_rivals:
        parts += ["", "КТО ДАВИТ СИЛЬНЕЕ ВСЕГО"]
        for card, threat in ranked_rivals[:5]:
            parts.append(
                f"- {card['домен']}: угроза {threat.score}, доля "
                f"{kpi_mod.ru_number(100 * (card.get('доля') or 0))}%, "
                f"ТОП-3 по {card.get('топ3')} запросам")

    if attacks:
        parts += ["", f"ГДЕ БЛИЖЕ ВСЕГО РОСТ (первые 5 из {len(attacks)})"]
        for a in attacks[:5]:
            parts.append(
                f"- {a['attack_id']} «{a['query']}»: мы №{a['our_position']}, "
                f"выше {a['rival_domain']} №{a['rival_position']}; "
                f"выгода {a['opportunity']}, уверенность {a['confidence']}, "
                f"спрос {a['demand']} ({a['demand_source']})")

    parts += [
        "",
        f"Полная аналитика: {REPORT_URL}",
        "",
        f"Scoring: {meta['зрелость_скоринга']} · "
        f"источник: Яндекс (Москва), {meta['покрытие'].get('яндекс_запросов_с_данными')} запросов · "
        f"Google: {'NO DATA' if meta['kpi']['share_google'] is None else 'есть'} · "
        "B2C и маркетплейсы вне основного рейтинга · NO DATA не равно нулю.",
    ]
    return "\n".join(parts)


def _classifier():
    from competitors import classifier
    return classifier


def _block(title: str, body: str, *, accent: bool = False) -> str:
    """Секция письма. Пустая строка не рисуется вовсе — лучше короче."""
    if not body:
        return ""
    escaped = html.escape(body)
    frame = ('padding:10px 12px;background:#FFF4EF;border-left:3px solid #F4511E;'
             'border-radius:4px;') if accent else ""
    return (f'<tr><td style="padding:12px 24px 0;"><div style="{frame}">'
            f'<div style="font-size:11px;color:#667085;letter-spacing:.06em;'
            f'font-weight:700;">{html.escape(title)}</div>'
            f'<div style="font-size:14px;line-height:1.45;padding-top:4px;">'
            f'{escaped}</div></div></td></tr>')


def render_html(meta: dict, *, kpi=None, snapshot: dict | None = None,
                attacks: list[dict] | None = None, ranked_rivals=None,
                packages: list[dict] | None = None) -> str:
    """HTML-версия письма: верхний уровень плюс секции детализации.

    Верхний уровень (вердикт, показатели, сигнал, действие, наблюдение)
    ограничен 1000 видимыми символами — его и проверяет гейт качества.
    Секции ниже в лимит не входят: по решению руководителя письмо должно
    быть детализировано не хуже ежедневного SEO-отчёта, а короткая
    executive-часть остаётся первым экраном.
    """
    k = meta["kpi"]
    esc = html.escape
    delta = kpi_mod.format_delta(k["share_delta_pp"], unit=" п.п.")
    lines = meta["текст"].split("\n")
    verdict_line, _kpi_line, signal_line = lines[0], lines[1], lines[2]
    do_next_line = lines[3] if len(lines) > 3 else ""
    watch_line = lines[4] if len(lines) > 4 else ""
    google_share = ("NO DATA" if k["share_google"] is None
                    else f"{100 * k['share_google']:.1f}%")
    yandex_share = ("NO DATA" if k["share_yandex"] is None
                    else f"{100 * k['share_yandex']:.1f}%")

    # Секции детализации собираются только когда переданы данные: письмо
    # обязано оставаться отправляемым и в урезанном виде.
    detail = ""
    if kpi is not None and snapshot is not None:
        detail = (
            '<tr><td style="padding:16px 24px 0;">'
            f'<div style="border-top:1px solid {sections.LINE};"></div></td></tr>'
            + sections.packages_section(packages or [])
            + sections.options_section(packages or [])
            + sections.kpi_section(kpi, snapshot)
            + sections.field_section(snapshot)
            + sections.rivals_section(snapshot.get("лидеры") or [],
                                      ranked_rivals or [])
            + sections.attacks_section(attacks or [])
            + sections.limits_section(snapshot, attacks or []))

    def cell(label: str, value: str, note: str) -> str:
        return (
            '<td style="padding:8px;border:1px solid #EAECF0;border-radius:6px;">'
            f'<div style="color:#667085;font-size:11px;">{esc(label)}</div>'
            f'<div style="font-size:20px;font-weight:700;">{esc(value)}</div>'
            f'<div style="color:#98A2B3;font-size:11px;">{esc(note)}</div></td>')

    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(meta['тема'])}</title></head>
<body style="margin:0;padding:0;background:#f4f5f7;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;">
<tr><td align="center" style="padding:16px 8px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border:1px solid #EAECF0;border-radius:8px;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#101828;">
<tr><td style="padding:20px 24px 6px;">
<div style="font-size:12px;color:#667085;letter-spacing:.04em;">BIZSOFT · КОНКУРЕНТНАЯ РАЗВЕДКА · {esc(meta['дата'])}</div>
</td></tr>
<tr><td style="padding:6px 24px;"><div style="font-size:17px;font-weight:700;">{esc(verdict_line)}</div></td></tr>
<tr><td style="padding:10px 24px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:13px;"><tr>
{cell('B2B Share · Яндекс', yandex_share, f'Δ7д: {delta}')}<td style="width:6px;"></td>
{cell('B2B Share · Google', google_share, 'еженедельный сбор')}<td style="width:6px;"></td>
{cell('ТОП-3', f"{k['top3']}/{k['queries']}", 'запросов')}<td style="width:6px;"></td>
{cell('ТОП-10', f"{k['top10']}/{k['queries']}", 'запросов')}
</tr></table></td></tr>
<tr><td style="padding:12px 24px 0;">
<div style="font-size:11px;color:#667085;letter-spacing:.06em;font-weight:700;">ГЛАВНЫЙ СИГНАЛ</div>
<div style="font-size:14px;line-height:1.45;padding-top:4px;">{esc(signal_line.removeprefix('Главный сигнал: '))}</div>
</td></tr>
{_block('ЧТО ДЕЛАТЬ СЕГОДНЯ', do_next_line.removeprefix('Что делать: '), accent=True)}
{_block('СЛЕДИМ', watch_line.removeprefix('Следим: '))}
{detail}
<tr><td style="padding:22px 24px 20px;" align="center">
<a href="{REPORT_URL}" style="display:inline-block;background:#101828;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;padding:10px 22px;border-radius:6px;">Открыть полную конкурентную аналитику →</a>
</td></tr>
<tr><td style="padding:0 24px 18px;border-top:1px solid #EAECF0;">
<div style="font-size:11px;color:#98A2B3;padding-top:10px;line-height:1.5;">
Scoring: {esc(meta['зрелость_скоринга'])} · источник: Яндекс (Москва), {esc(str(meta['покрытие'].get('яндекс_запросов_с_данными')))} запросов ·
Google: {esc(google_share)} · B2C и маркетплейсы вне основного рейтинга · NO DATA не равно нулю.
</div></td></tr>
</table></td></tr></table></body></html>"""


def main(argv: list[str]) -> int:
    dates = kpi_mod.available_snapshots()
    if not dates:
        print("Снимков нет — сначала нужен прогон discovery")
        return 1
    date = argv[1] if len(argv) > 1 else dates[-1]
    snapshot = kpi_mod.load_snapshot(date)
    if snapshot is None:
        print(f"Снимка за {date} нет. Доступны: {', '.join(dates)}")
        return 1
    earlier = [d for d in dates if d < date]
    previous = kpi_mod.load_snapshot(earlier[-1]) if earlier else None

    meta = build(date, snapshot, previous)
    os.makedirs(paths.REPORTS_DIR, exist_ok=True)
    base = os.path.join(paths.REPORTS_DIR, f"{date}-email")
    with open(f"{base}.txt", "w", encoding="utf-8") as fh:
        fh.write(render_txt(meta))
    with open(f"{base}.html", "w", encoding="utf-8") as fh:
        fh.write(render_html(meta))
    with open(f"{base}.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)

    print(f"Тема: {meta['тема']}")
    print(f"Видимых символов: {meta['видимых_символов']} из {TEXT_LIMIT} "
          f"({'в пределах лимита' if meta['лимит_соблюдён'] else 'ЛИМИТ ПРЕВЫШЕН'})")
    print(f"Сравнение с: {meta['сравнение_с'] or 'нет сравнимого дня'}")
    print(f"Файлы: {base}.{{html,txt,json}}")
    return 0 if meta["лимит_соблюдён"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
