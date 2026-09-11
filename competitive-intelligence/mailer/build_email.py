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
from attack_engine import occupancy as occupancy_mod  # noqa: E402
from decision_engine import kpi as kpi_mod  # noqa: E402
from decision_engine import signal as signal_mod  # noqa: E402
from mailer import sections  # noqa: E402
from mailer.sections import kit  # noqa: E402

MSK = timezone(timedelta(hours=3))
TEXT_LIMIT = 1000
# Непубличный путь: угадать нельзя, ссылок с сайта нет, отдаётся с
# X-Robots-Tag noindex. Basic auth не заводится по решению руководителя от
# 31.08 — риск принят; при подозрении на утечку меняется токен пути в
# deploy/nginx-biz-soft.conf.template и здесь.
REPORT_URL = "https://biz-soft.pro/ci-c98370a0ebe87d97/latest.html"


def do_next_text(attack: dict | None, package: dict | None = None,
                 compact: bool = False) -> str:
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
        actions = package.get("действия") or []
        first = actions[0] if actions else None
        # Поручение называет конкретный шаг и место правки. Раньше здесь было
        # направление («добавить коммерческий блок»), выбранное по типу
        # страницы: поручить его было нельзя, а проверка показала, что на
        # части страниц оно попросту неверно.
        if first:
            steps = first.get("steps", [])
            # Компактная форма нужна в дни, когда остальные блоки письма
            # длиннее обычного: лимит верхнего уровня — 1000 видимых символов,
            # и поручение сокращается первым, оставаясь исполнимым.
            if compact:
                examples = steps[0].split(" — не хватает")[0] if steps else ""
            else:
                examples = "; ".join(steps[:2])
            tail = (f" Ещё {len(actions) - 1} шага ТЗ — в отчёте."
                    if len(actions) > 1 else "")
            return (f"Что делать: {package['package_id']} ({url_short}) — "
                    f"{first['what'].lower()}: {examples}. "
                    f"Трудоёмкость {first['effort']}, исполнитель — "
                    f"{first['owner']}.{_условие(package)}{tail}")
        upside = (f"при выходе в ТОП-3 даст примерно "
                  f"+{package['traffic_upside']:.0f} переходов"
                  if package.get("traffic_upside") is not None
                  else f"потенциал {package['potential_label']}")
        return (f"Что делать: {package['package_id']} — {package['action']} "
                f"({url_short}). Закроет {package['queries_count']} запросов, "
                f"{sections.format_demand(package)}, сейчас позиции "
                f"{package['position_best']}–{package['position_worst']}; "
                f"{upside}. Трудоёмкость {package['effort']}."
                f"{_условие(package)}")
    if not attack:
        return ("Что делать: подтверждённых точек атаки нет — "
                "накапливаем наблюдения.")
    return (f"Что делать: {attack['attack_id']} «{attack['query']}» — "
            f"мы на {attack['our_position']}-м месте, выше "
            f"{attack['rival_domain']} на {attack['rival_position']}-м. "
            f"Opportunity {attack['opportunity']}, "
            f"уверенность {attack['confidence']}.")


def _dm(iso: str | None) -> str:
    """Дата ДД.ММ для подписи в тексте письма."""
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m") if iso else "—"


def delta_caption(compared_with: str | None) -> str:
    """Подпись дельты называет день сравнения, а не период.

    Одна и та же величина подписывалась «Δ7д», «за сутки» и «к прошлому»,
    хотя считается к последнему сравнимому снимку — не обязательно вчерашнему
    (письмо 01.09.2026 сравнивало с 30.08 под подписью «за сутки»).
    """
    return f"к {_dm(compared_with)}" if compared_with else "сравнения нет"


def watch_text(threat_leader: tuple[dict, object] | None) -> str:
    """WATCH — одна угроза, а не перечень конкурентов."""
    if not threat_leader:
        return "Следим: угроз выше порога не зафиксировано."
    card, threat = threat_leader
    return (f"Следим: {card['домен']} — Threat {threat.score} из {threat.scale_max}, "
            f"топ-3 по {card['топ3']} запросам, доля "
            f"{kpi_mod.ru_number(100 * card['доля'])}%.")


def _условие(package: dict) -> str:
    """Короткая пометка условия рядом с самим поручением.

    Условие обязано ехать вместе с поручением на том уровне, где поручение
    даётся. Верхняя часть письма — единственное, что читают полностью; если
    ограничение живёт только в карточке ниже или в отчёте, поручение уйдёт в
    работу без него. Полная формулировка — в карточке пакета и в отчёте,
    здесь ровно столько, чтобы работа не началась молча.
    """
    занятость = package.get("занятость") or {}
    if занятость.get("степень") != "контрольная группа":
        return ""
    return (f" Условие: страница — контроль чужого замера до "
            f"{занятость.get('до', 'контрольной точки')}, решение за вами.")


def visible_text(kpi, verdict_mark, verdict_why, signal, *,
                 attack=None, threat_leader=None, package=None,
                 signal_delta: float | None = None,
                 compact: bool = False) -> str:
    """Основная текстовая часть письма — то, что считается против лимита.

    Ссылки, подписи и футер в лимит не входят (раздел 23), поэтому здесь
    собирается ровно смысловое содержание.
    """
    lines = [
        f"{verdict_mark} {verdict_why}.",
        (f"B2B Share Яндекс {kpi_mod.format_share(kpi.share_yandex)} "
         f"({delta_caption(kpi.compared_with)} "
         f"{kpi_mod.format_delta(kpi.share_delta_pp, unit=' п.п.')}, "
         f"сигнальная {kpi_mod.format_delta(signal_delta, unit=' п.п.')}) · "
         f"Google {kpi_mod.format_share(kpi.share_google)} · "
         f"ТОП-3 органики {kpi.top3}/{kpi.queries} · "
         f"ТОП-10 органики {kpi.top10}/{kpi.queries}."),
        f"Главный сигнал: {signal.text}",
        do_next_text(attack, package, compact=compact),
        watch_text(threat_leader),
    ]
    return "\n".join(lines)


# Насколько потенциал пакета с неизмеренным спросом должен превосходить
# измеренный, чтобы всё-таки стать главным поручением. Нормализация весов
# при отсутствии фактора даёт такому пакету фору: неудобный признак просто
# исчезает из расчёта. Порог возвращает предпочтение измеренной возможности,
# не запрещая неизмеренную совсем.
UNMEASURED_DEMAND_MARGIN = 1.25


def pick_package(packages: list[dict] | None) -> dict | None:
    """Пакет для главного поручения.

    При сопоставимом потенциале предпочтение отдаётся пакету с измеренным
    спросом. Иначе система систематически выбирала бы цели, о которых знает
    меньше всего: у них отсутствующий фактор исключается из расчёта, и
    остальные веса нормализуются вверх.
    """
    if not packages:
        return None
    # Пакеты без измеренного спроса индекса не имеют: сравнивать их с
    # остальными по величине нельзя, и главным поручением они не становятся —
    # по ним сначала измеряется спрос. В очереди они остаются видимыми.
    scored = [p for p in packages if p.get("potential_index") is not None]
    if not scored:
        return packages[0]
    measured = [p for p in scored if p.get("traffic_upside") is not None]
    if not measured:
        return scored[0]
    best_measured = max(measured, key=lambda p: p["potential_index"])
    best_overall = max(scored, key=lambda p: p["potential_index"])
    if best_overall is best_measured:
        return best_measured
    # Неизмеренный побеждает только с запасом, а не по случайному перевесу
    if (best_overall["potential_index"]
            > best_measured["potential_index"] * UNMEASURED_DEMAND_MARGIN):
        return best_overall
    return best_measured


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
          blocked: list[dict] | None = None,
          history: list[float] | None = None,
          experiments_line: str = "") -> dict:
    kpi = kpi_mod.build_kpi(snapshot, previous)
    verdict_mark, verdict_why = kpi_mod.verdict(kpi, history)
    signal_delta = kpi_mod.trend_change(history or [])
    if stale_notice:
        # Данные не за сегодня. Показать их можно — они честно датированы, —
        # но вердикт обязан стать «недостаточно данных»: выводы о динамике по
        # вчерашнему срезу были бы выводами о вчерашнем дне, поданными как
        # сегодняшние.
        verdict_mark = kpi_mod.VERDICT_NO_DATA
        verdict_why = f"Данные неполные: {stale_notice}"
    signal = signal_mod.pick(snapshot, previous)
    attack = pick_attack(attacks)
    # Поручением дня 10.09.2026 стала страница, занятая чужим замером до
    # 30.09: пакет вышел из очереди с одной лишь пометкой. Отсев на входе.
    packages, _занятые = occupancy_mod.split_takeable(packages)
    package = pick_package(packages)
    text = visible_text(kpi, verdict_mark, verdict_why, signal,
                        attack=attack, threat_leader=threat_leader,
                        package=package, signal_delta=signal_delta)
    if len(text) > TEXT_LIMIT:
        # Сокращаем поручение, а не выводы: письмо без вердикта и сигнала
        # бесполезно, а поручение остаётся исполнимым и в краткой форме.
        text = visible_text(kpi, verdict_mark, verdict_why, signal,
                            attack=attack, threat_leader=threat_leader,
                            package=package, signal_delta=signal_delta,
                            compact=True)

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
        "дельта_суточная_пп": kpi.share_delta_pp,
        "основание_дельты": kpi.delta_basis,
        # Строка про эксперименты живёт в детализации, а не в верхнем уровне:
        # состав executive-части задан разделом 23 задания и ограничен 1000
        # символами, а цикл проверки — это отчётность о ходе работ, не решение
        # дня. В отчёте под неё отведён отдельный раздел.
        "эксперименты_строка": experiments_line,
        "ядро": {
            "версия": kpi.core_version,
            "хеш": kpi.core_hash,
            "запросов": kpi.core_size,
            "менялось": kpi.core_changed,
            "сравнимое_подмножество": kpi.comparable_core,
            "примечания": kpi.notes,
        },
        "дельта_сигнальная_пп": signal_delta,
        "kpi": {
            "share_yandex": kpi.share_yandex,
            "share_google": kpi.share_google,
            "google_date": kpi.google_date,
            "google_delta_pp": kpi.google_delta_pp,
            "top3": kpi.top3,
            "top10": kpi.top10,
            "queries": kpi.queries,
            "share_delta_pp": kpi.share_delta_pp,
        },
    }


def render_txt(meta: dict, *, snapshot: dict | None = None,
               attacks: list[dict] | None = None, ranked_rivals=None,
               packages: list[dict] | None = None,
               blocked: list[dict] | None = None) -> str:
    """Текстовая версия — полноценная, а не огрызок для спам-фильтра.

    Повторяет оба уровня письма: executive-часть и детализацию. Клиент,
    отключивший HTML, обязан получить те же сведения, а не обрубок.
    """
    packages, занятые = occupancy_mod.split_takeable(packages)
    blocked = (blocked or []) + [p for p in занятые if p not in (blocked or [])]
    parts = [meta["тема"], "", meta["текст"]]
    if meta.get("эксперименты_строка"):
        parts += ["", meta["эксперименты_строка"]]

    google = kpi_mod.google_block(snapshot or {})
    if google:
        ours = google.get("наши_показатели") or {}
        gap = google.get("разрыв_с_яндексом") or {}
        parts += ["", f"GOOGLE ПО РОССИИ (xmlriver, глубина "
                      f"{google.get('глубина', 10)}, "
                      f"{(google.get('покрытие') or {}).get('запросов_с_данными')} "
                      f"запросов, срез {google.get('дата_среза')})"]
        parts.append(f"Наша доля видимости в Google: "
                     f"{kpi_mod.format_share(ours.get('доля_видимости'))}; "
                     f"ТОП-3: {ours.get('топ3', 0)}, ТОП-10: {ours.get('топ10', 0)}")
        for item in (google.get("лидеры") or [])[:5]:
            parts.append(f"  {item['домен']}: {kpi_mod.format_share(item.get('доля'))}, "
                         f"ТОП-3 {item.get('топ3', 0)}, ТОП-10 {item.get('топ10', 0)}")
        parts.append(f"Разрыв с Яндексом: Яндекс топ-10, в Google нет — "
                     f"{gap.get('яндекс_топ10_google_нет_всего', 0)} из "
                     f"{gap.get('сопоставлено', 0)} общих запросов.")
        parts.append("  Доли внутри Google-поля, с Яндексом не складываются.")

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
                f"   Закроет {pkg['queries_count']} запросов, "
                f"{sections.format_demand(pkg)}\n"
                f"   Сейчас позиции {pkg['position_best']}–{pkg['position_worst']}, "
                f"выше нас {', '.join(pkg['rivals'][:2])}\n"
                f"   {upside} · трудоёмкость {pkg['effort']} · "
                f"уверенность {pkg['confidence']}")
            # То же правило, что в HTML: сначала проверенные действия; если
            # страница проверена и работ не требует — так и сказать; шаблонный
            # чеклист — только когда проверки не было. Письмо 03.09.2026
            # печатало «правок не требуется» и тут же шаблон «добавить FAQ».
            actions = pkg.get("действия") or []
            done = pkg.get("уже_сделано") or []
            if actions:
                for a in actions[:3]:
                    parts.append(f"   - {a['what']} ({a['effort']}, {a['owner']})")
            elif done:
                parts.append("   Проверено и работ не требует: " + "; ".join(done))
            else:
                for check in (pkg.get("checklist") or [])[:3]:
                    parts.append(f"   - {check}")
            control = sections.control_note(pkg)
            if control:
                parts.append(f"   {control}")

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
        blocked_line = sections.blocked_note(blocked)
        if blocked_line:
            parts.append(blocked_line)

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
        f"Google: {_google_source_line(meta)} · "
        "позиции органические (Search API, без рекламы и колдунщиков; "
        "расхождение с позицией показа — в отчёте) · "
        "B2C и маркетплейсы вне основного рейтинга · NO DATA не равно нулю.",
    ]
    return "\n".join(parts)


def _google_source_line(meta: dict) -> str:
    """Подпись источника Google: доля и дата еженедельного среза, либо NO DATA."""
    k = meta["kpi"]
    if k.get("share_google") is None:
        return "NO DATA"
    line = kpi_mod.format_share(k["share_google"])
    if k.get("google_date"):
        line += f" (Россия, xmlriver, срез {k['google_date']})"
    return line


def _classifier():
    from competitors import classifier
    return classifier


def _block(title: str, body: str, *, accent: bool = False) -> str:
    """Секция письма. Пустая строка не рисуется вовсе — лучше короче."""
    if not body:
        return ""
    escaped = html.escape(body)
    frame = (f'padding:10px 12px;background:{kit.LIGHT["accent_soft"]};'
             f'border-left:3px solid {kit.LIGHT["accent"]};border-radius:0 8px 8px 0;'
             if accent else "")
    return (f'<tr><td style="padding:12px 24px 0;"><div style="{frame}">'
            f'<div style="font-size:11px;color:{kit.LIGHT["muted"]};letter-spacing:.06em;'
            f'font-weight:700;">{html.escape(title)}</div>'
            f'<div style="font-size:14px;line-height:1.45;padding-top:4px;">'
            f'{escaped}</div></div></td></tr>')


def render_html(meta: dict, *, kpi=None, snapshot: dict | None = None,
                attacks: list[dict] | None = None, ranked_rivals=None,
                packages: list[dict] | None = None,
                blocked: list[dict] | None = None,
                signal_delta: float | None = None,
                on_watch: list[dict] | None = None) -> str:
    """HTML-версия письма: верхний уровень плюс секции детализации.

    Верхний уровень (вердикт, показатели, сигнал, действие, наблюдение)
    ограничен 1000 видимыми символами — его и проверяет гейт качества.
    Секции ниже в лимит не входят: по решению руководителя письмо должно
    быть детализировано не хуже ежедневного SEO-отчёта, а короткая
    executive-часть остаётся первым экраном.
    """
    packages, занятые = occupancy_mod.split_takeable(packages)
    blocked = (blocked or []) + [p for p in занятые if p not in (blocked or [])]
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
    google_info = kpi_mod.google_block(snapshot or {})
    google_note = (f"Россия, топ-{google_info.get('глубина', 10)}, "
                   f"срез {google_info.get('дата_среза')}"
                   if google_info else "нет свежего среза")

    # Секции детализации собираются только когда переданы данные: письмо
    # обязано оставаться отправляемым и в урезанном виде.
    detail = ""
    if kpi is not None and snapshot is not None:
        detail = (
            '<tr><td style="padding:16px 24px 0;">'
            f'<div style="border-top:1px solid {sections.LINE};"></div></td></tr>'
            + sections.packages_section(packages or [])
            + sections.options_section(packages or [], blocked)
            + sections.kpi_section(kpi, snapshot, signal_delta)
            + sections.field_section(snapshot)
            + sections.rivals_section(snapshot.get("лидеры") or [],
                                      ranked_rivals or [])
            + sections.google_section(snapshot)
            + sections.attacks_section(attacks or [])
            + sections.experiments_section(
                meta.get('эксперименты_строка', ''), on_watch)
            + sections.limits_section(snapshot, attacks or []))

    def cell(label: str, value: str, note: str) -> str:
        """Плитка KPI-kit: та же, что в SEO-письме; NO DATA — приглушённая."""
        return (f'<td width="50%" valign="top" style="padding:4px;">'
                + kit.email_tile(label, value, note=esc(note), muted=(value == "NO DATA"))
                + '</td>')

    delta_label = "Δ " + delta_caption(meta.get("сравнение_с"))
    C = kit.LIGHT
    masthead = kit.email_masthead(
        f'BIZ<span style="color:{C["accent"]};">Soft</span> · Конкурентная разведка',
        esc(meta["дата"]))

    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(meta['тема'])}</title></head>
<body style="margin:0;padding:0;background:{C['plane']};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{C['plane']};">
<tr><td align="center" style="padding:16px 8px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:{C['surface']};border:1px solid {C['hair']};border-radius:14px;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:{C['ink']};">
{masthead}
<tr><td style="padding:16px 24px 6px;"><div style="font-size:17px;font-weight:700;">{esc(verdict_line)}</div></td></tr>
<tr><td style="padding:6px 20px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:13px;">
<tr>{cell('B2B Share · Яндекс', yandex_share, f'{delta_label}: {delta}')}{cell('B2B Share · Google', google_share, google_note)}</tr>
<tr>{cell('ТОП-3 органики', f"{k['top3']} из {k['queries']}", 'запросов')}{cell('ТОП-10 органики', f"{k['top10']} из {k['queries']}", 'запросов')}</tr>
</table></td></tr>
<tr><td style="padding:12px 24px 0;">
<div style="font-size:11px;color:{C['muted']};letter-spacing:.06em;font-weight:700;">ГЛАВНЫЙ СИГНАЛ</div>
<div style="font-size:14px;line-height:1.45;padding-top:4px;">{esc(signal_line.removeprefix('Главный сигнал: '))}</div>
</td></tr>
{_block('ЧТО ДЕЛАТЬ СЕГОДНЯ', do_next_line.removeprefix('Что делать: '), accent=True)}
{_block('СЛЕДИМ', watch_line.removeprefix('Следим: '))}
{detail}
<tr><td style="padding:22px 24px 20px;" align="center">
<a href="{REPORT_URL}" style="display:inline-block;background:{C['accent']};color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;padding:10px 22px;border-radius:8px;">Открыть полную конкурентную аналитику →</a>
</td></tr>
<tr><td style="padding:0 24px 18px;border-top:1px solid {C['hair']};">
<div style="font-size:11px;color:{C['muted']};padding-top:10px;line-height:1.5;">
Scoring: {esc(meta['зрелость_скоринга'])} · источник: Яндекс (Москва), {esc(str(meta['покрытие'].get('яндекс_запросов_с_данными')))} запросов ·
Google: {esc(_google_source_line(meta))} · позиции органические (Search API, без рекламы и колдунщиков; расхождение с позицией показа — в отчёте) ·
B2C и маркетплейсы вне основного рейтинга · NO DATA не равно нулю.
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
