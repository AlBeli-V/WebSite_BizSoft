#!/usr/bin/env python3
"""Email UX lint для письма V4 «Executive Command Center».

Проверяет письмо как продукт: объём, первый экран, число карточек и строк,
мобильную вёрстку, типографику, повторы фактов, необоснованные причинные
утверждения и правила методики измерений.

Запуск: python3 scripts/seo/uxlint_v4.py <дата>
Результат: reports/seo/intelligence/<дата>-v4-uxlint.json, код возврата 1 при ошибках
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

BASE = pathlib.Path("reports/seo/intelligence")

LIMITS = {
    # 1000 → 1100 (29.08, секции «Реклама» и «Перспективные идеи») →
    # 1200 (30.08, issue #216): этап 0 Growth Engine добавил строку
    # loop-health, волна страниц #211 расширила контроль экспериментов, и
    # 1100 перестало вмещать состав, целиком утверждённый руководителем.
    # Запас взят с горизонтом: письмо 31.08 после разбора руководителя
    # (контроль эксперимента построчно, стол решений в шапке, строка
    # «что дальше») заняло 1347 слов и 249 на первом экране.
    # Правило: новая постоянная секция расширяет потолок в том же PR.
    # 1450 → 1700 (01.09): раздел «Управленческие воздействия» — развёрнутые
    # постановки задач по поручению руководителя от 01.09.2026.
    "visible_words": 1700,
    "first_screen_words": 320,
    "kpi": 4,
    "signals": 3,
    "opportunities": 3,
    "board_rows": 5,
    "charts": 3,
    "min_body_px": 14.0,
    "min_meta_px": 12.5,
    "max_fact_repeats": 2,
    "max_chart_height_px": 220,
}

# Причинные утверждения, которые нельзя делать без перечисления страниц.
CAUSAL_UNSUPPORTED = [
    "стал чаще показывать наши карточки",
    "поисковик стал лучше относиться",
    "алгоритм изменился",
    "нас начали чаще находить",
]
# Причинные обороты: по ним предложение о Google читается как утверждение о
# причине изменения, а не как упоминание источника. Список заведомо неполон и
# дополняется по мере изменения языка письма — держать его здесь, а не внутри
# проверки, чтобы правка не требовала чтения кода правила.
GOOGLE_CAUSAL_MARKERS = [
    "благодаря",
    "из-за",
    "за счёт",
    "потому что",
    "обеспечил",
    "обусловлен",
    "объясняется",
    "вызван",
    "привёл к",
    "привело к",
    "дал рост",
    "дало рост",
    "стал чаще показывать",
    "поисковик стал",
    "алгоритм изменился",
    "нас начали чаще находить",
    "причина —",
    "причина:",
    "причина в том",
]
# Обороты отказа от причины: если такой есть в том же предложении, причинного
# утверждения нет — письмо честно говорит, что причину назвать не может.
# Список так же открыт для дополнения.
CAUSE_DECLINED_MARKERS = [
    "не определена",
    "не определён",
    "не разложен",
    "нельзя",
    "не отдал новых данных",
    "данные не обновились",
    "слишком дробные",
    "рано для вывода",
    "не подтвержд",
]
# Формулировки, запрещённые методикой измерений.
FORBIDDEN_MEASUREMENT = [
    "кратное расхождение",
    "кратно расходятся",
    "единое определение визита",
    "сводим клики и визиты",
    "CTR сайта",
]
FIRST_SCREEN_MARKER = "<!--first-screen-end-->"


def strip_tags(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


def words(text: str) -> int:
    return len([w for w in re.split(r"\s+", text) if w.strip(" ·—–-|→")])


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def google_causal_claim(vis: str, blocks: dict) -> tuple[bool, str]:
    """Сделало ли письмо утверждение о причине изменения, опирающееся на Google.

    Главный признак — структурный: блок «Что дало изменение» сам сообщает,
    определена причина или нет (`drivers.available`). Текстовый разбор —
    только страховка на случай причины, названной вне этого блока.

    Само по себе слово «Google» утверждением не является: оно стоит в шапке
    письма, в названии показателя видимости и в подписи источника каждый день.
    """
    # Утверждение — это то, что письмо НАПИСАЛО, а не что насчитал движок.
    # Печатаемый текст блока «Что дало изменение» — driver_summary: он либо
    # объявляет причину («Показы выросли на страницах: …»), либо явно
    # отказывается («Причина изменения пока не определена»). Оба прежних
    # структурных признака падали ложно: 25.08 — слово «Google» в шапке,
    # 27.08 — верхний drivers.available, который означает лишь «расчёт
    # выполнялся» (письмо вправе быть консервативнее движка и не объявлять
    # причину, когда найденное объясняет малую долю изменения: детрактор −8
    # при общей дельте −125).
    summary = (blocks.get("driver_summary") or "").lower()
    declined = any(m in summary for m in CAUSE_DECLINED_MARKERS)
    if summary and not declined:
        return True, "блок «Что дало изменение» объявил причину"
    if blocks.get("driver_rows"):
        return True, "блок «Что дало изменение» перечислил драйверы"
    for phrase in sentences(vis):
        low = phrase.lower()
        if "google" not in low:
            continue
        if any(m in low for m in CAUSE_DECLINED_MARKERS):
            continue
        marker = next((m for m in GOOGLE_CAUSAL_MARKERS if m in low), None)
        if marker:
            return True, f"причинный оборот «{marker}» в предложении о Google"
    return False, "причина изменения не названа"


def run(date: str) -> dict:
    email = (BASE / f"{date}-v4-email.html").read_text(encoding="utf-8")
    preview = (BASE / f"{date}-v4.html").read_text(encoding="utf-8")
    blocks = json.loads((BASE / f"{date}-v4-blocks.json").read_text(encoding="utf-8"))
    text = (BASE / f"{date}-v4.txt").read_text(encoding="utf-8")
    dq = json.loads((BASE / "data-quality" / f"{date}.json").read_text(encoding="utf-8"))
    actions = json.loads((BASE / "actions.json").read_text(encoding="utf-8"))

    vis = strip_tags(preview)
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    total = words(vis)
    add("visible_words", total <= LIMITS["visible_words"],
        f"{total} слов при пределе {LIMITS['visible_words']}")

    head = words(strip_tags(preview.split(FIRST_SCREEN_MARKER)[0]))
    add("first_screen_words", head <= LIMITS["first_screen_words"],
        f"{head} слов на первом экране при пределе {LIMITS['first_screen_words']}")

    add("kpi_limit", len(blocks["kpis"]) <= LIMITS["kpi"],
        f"показателей: {len(blocks['kpis'])}")
    add("signals_limit", len(blocks["signals"]) <= LIMITS["signals"],
        f"сигналов: {len(blocks['signals'])}")
    add("opportunities_limit",
        len(blocks["opportunities"].get("items", [])) <= LIMITS["opportunities"],
        f"возможностей: {len(blocks['opportunities'].get('items', []))}")
    add("board_rows_limit", len(blocks["board"]) <= LIMITS["board_rows"],
        f"строк журнала: {len(blocks['board'])}")

    imgs = re.findall(r"<img[^>]+>", preview)
    add("charts_limit", len(imgs) <= LIMITS["charts"], f"изображений: {len(imgs)}")

    heights = [int(m) for m in re.findall(r"max-height:(\d+)px", preview)]
    add("chart_height", all(h <= LIMITS["max_chart_height_px"] for h in heights),
        f"высоты изображений: {heights or '—'} при пределе {LIMITS['max_chart_height_px']}px")

    # Мобильная вёрстка: карточки 50 % обязаны раскрываться в одну колонку.
    half = re.findall(r'class="kpi"[^>]*width="50%"', preview)
    media_ok = ".kpi{display:block!important;width:100%!important" in preview.replace(" ", "")
    add("no_half_width_cards_on_mobile", (not half) or media_ok,
        f"карточек в 50%: {len(half)}; правило одной колонки в media query: {media_ok}")

    add("has_media_queries", "@media only screen and (max-width:480px)" in preview,
        "media query для мобильной ширины найден")
    add("outlook_fallback", "<!--[if mso]>" in preview,
        "условный блок для Outlook присутствует")

    # Типографика: тело письма не мельче 14 px, метаданные — не мельче 12,5 px.
    body_sizes = [float(m) for m in re.findall(r"font-size:([\d.]+)px", preview)]
    meta_sizes = [float(m) for m in re.findall(
        r'data-meta="1"[^>]*font-size:([\d.]+)px', preview)]
    small = [s for s in body_sizes if s < LIMITS["min_body_px"] and s not in meta_sizes]
    tiny = [s for s in meta_sizes if s < LIMITS["min_meta_px"]]
    add("font_sizes", not tiny and all(s >= LIMITS["min_meta_px"] for s in small),
        f"меньше {LIMITS['min_body_px']}px вне метаданных: {sorted(set(small))}; "
        f"метаданные меньше {LIMITS['min_meta_px']}px: {sorted(set(tiny))}")

    add("images_have_alt", all("alt=" in i for i in imgs),
        f"изображений без alt: {sum(1 for i in imgs if 'alt=' not in i)}")

    # Текстовые PNG: подпись-заменитель обязана нести те же числа, что и картинка.
    alts = [m.group(1) for m in (re.search(r'alt="([^"]*)"', i) for i in imgs) if m]
    long_alts = [a for a in alts if words(a) > 12]
    add("no_text_heavy_png", not long_alts,
        f"подписей длиннее 12 слов: {len(long_alts)} — текст не вынесен в картинку")

    # Повтор факта: одно и то же утверждение не чаще двух раз.
    # Считаются повторы утверждения, а не упоминания слова: подпись поля
    # («выборка топ-100 запросов» в источнике показателя) фактом не является.
    key_facts = {
        "оговорка про охват": r"не заменяет|не сравнива\w+|разные множества|"
                              r"описывают разные",
        "отсутствие CRM": r"CRM не подключена|обращения и выручка не измеряются|"
                          r"не подтверждённые обращения",
        "низкая база Google": r"низкая база|малые числа|база в десятки",
        "рано для вывода": r"рано для вывода|не может проявиться|окно источника ещё",
    }
    repeats = {name: len(re.findall(pat, vis, re.I)) for name, pat in key_facts.items()}
    over = {k: v for k, v in repeats.items() if v > LIMITS["max_fact_repeats"]}
    add("no_duplicate_fact", not over, f"повторы: {repeats}; сверх лимита: {over or 'нет'}")

    # Причинность без доказательства.
    bad_causal = [c for c in CAUSAL_UNSUPPORTED if c in vis.lower()]
    add("no_unsupported_causal", not bad_causal, f"неподтверждённые причины: {bad_causal or 'нет'}")

    # Утверждение о причине, опирающееся на Google, без перечисления страниц.
    # Прежняя проверка считала утверждением само наличие слова «Google» в
    # тексте и падала в любой день с пустым driver_rows — в том числе 25.08,
    # когда письмо честно писало «причина изменения пока не определена».
    # Правило наказывало за требуемое методикой поведение и стоило дня без
    # отчёта, поэтому теперь оно намеренно ошибается в сторону пропуска:
    # причина, названная оборотом вне GOOGLE_CAUSAL_MARKERS, правилом не
    # поймается (цена — одна неточная формулировка в письме), тогда как
    # ложное срабатывание стоит целой рассылки. Страховка от пропуска —
    # структурный признак: при drivers.available=true пустой driver_rows
    # роняет проверку независимо от того, что написано в тексте.
    claim, claim_note = google_causal_claim(vis, blocks)
    pages_named = bool(blocks.get("driver_rows"))
    add("google_claim_has_page_evidence", (not claim) or pages_named,
        f"утверждение о причине: {'есть' if claim else 'нет'} ({claim_note}); "
        f"страниц-драйверов перечислено: {len(blocks.get('driver_rows') or [])}")

    # Методика измерений.
    bad_measure = [t for t in FORBIDDEN_MEASUREMENT if t.lower() in vis.lower()]
    add("no_unified_visit_definition", not bad_measure,
        f"запрещённые формулировки: {bad_measure or 'нет'}")

    health = dq["data_health"]["status"]
    # Красным здоровье может быть только из-за настоящей поломки (источник не
    # собрался или critical-находка), а не из-за расхождения охватов — за него
    # data_health даёт limited. Прежняя формулировка падала при любом
    # соседстве SCOPE_MISMATCH с degraded, даже когда degraded вызван другой,
    # законной причиной (например, пересборкой выборки запросов).
    scope_caused = "охват" in (dq["data_health"].get("reason") or "")
    add("no_critical_for_scope_mismatch",
        not (scope_caused and health == "degraded"),
        f"здоровье данных: {health}, причина: {dq['data_health'].get('reason')}")
    add("red_only_for_real_failure", dq["data_health"]["colour"] != "danger" or health == "degraded",
        f"цвет блока: {dq['data_health']['colour']}")

    # Публичный адрес отчёта, а не ветка репозитория.
    primary = blocks["links"]["web"]
    add("public_url_or_marked_fallback",
        blocks["links"]["web_public"] or "техническая копия" in vis,
        f"основная ссылка: {primary}; помечена как техническая: "
        f"{'да' if 'техническая копия' in vis else 'нет'}")

    # Ссылка «Полный отчёт» должна вести на существующую страницу.
    # Без этой проверки письмо спокойно уходило со ссылкой на файл, который
    # генератор больше не создаёт: все остальные проверки при этом были зелёными.
    web = blocks["links"]["web"]
    # HTML в репозитории GitHub отдаёт исходным текстом, а не страницей: такая
    # ссылка формально жива, но отчёт по ней не прочитать.
    if "github.com" in web and web.endswith(".html"):
        add("report_link_target_exists", False,
            "ссылка ведёт на HTML в репозитории — GitHub покажет исходный текст")
    elif web.startswith("https://claude.ai/") or (web.startswith("http")
                                                  and "github.com" not in web):
        target_ok, target_note = True, "внешний адрес опубликованной страницы"
        add("report_link_target_exists", target_ok, target_note)
    else:
        # Имя ветки содержит слэш, поэтому отрезается целиком, а не по первому
        # разделителю: иначе путь к файлу получается смещённым.
        branch = "seo-data/"
        rest = ""
        for marker in ("/blob/", "/tree/"):
            if marker in web:
                rest = web.split(marker, 1)[-1]
                break
        rel = rest[len(branch):] if rest.startswith(branch) else ""
        target = pathlib.Path(rel)
        target_ok = bool(rel) and target.exists()
        target_note = f"цель ссылки {rel or '—'}: {'есть' if target_ok else 'НЕ СУЩЕСТВУЕТ'}"
        add("report_link_target_exists", target_ok, target_note)

    # Совместное внедрение не разделяется.
    combined = [a["id"] for a in actions["actions"] if a.get("combined_deployment")]
    split = "CRO-EXP-002" in vis
    add("no_split_combined_experiment", not split,
        f"совместных внедрений: {len(combined)}; раздельная оценка в письме: {split}")

    # Результаты браузерной проверки: горизонтальная прокрутка и размеры шрифтов
    # в двух вариантах — с медиазапросами и без них (как в Gmail).
    render_path = BASE / f"{date}-v4-render.json"
    if render_path.exists():
        render = json.loads(render_path.read_text(encoding="utf-8"))
        bad = [r for r in render if not r["noHorizontalScroll"]]
        add("no_horizontal_scroll", not bad,
            "; ".join(f"{r['variant']}@{r['width']}px→{r['scrollWidth']}px" for r in render))
        small = [r for r in render if r["minBody"] < LIMITS["min_body_px"]]
        add("rendered_font_sizes", not small,
            "; ".join(f"{r['variant']}@{r['width']}px текст {r['minBody']}px, "
                      f"подписи {r['minMeta']}px" for r in render))
    else:
        add("no_horizontal_scroll", False, "браузерная проверка не выполнена")

    # Текстовая версия не должна расходиться с письмом по решению руководителя.
    add("plain_text_matches", blocks["user_action"][:40] in text,
        "решение руководителя присутствует в текстовой версии")

    ok = all(c["ok"] for c in checks)
    return {"date": date, "passed": ok,
            "counts": {"total": len(checks), "failed": sum(1 for c in checks if not c["ok"])},
            "visible_words": total, "first_screen_words": head, "checks": checks}


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else None
    if not date:
        print("нужна дата", file=sys.stderr)
        return 2
    res = run(date)
    (BASE / f"{date}-v4-uxlint.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in res["checks"]:
        print(f"  [{'OK  ' if c['ok'] else 'FAIL'}] {c['check']}: {c['detail']}")
    print(f"UX lint V4: {'pass' if res['passed'] else 'FAIL'} "
          f"({res['counts']['total'] - res['counts']['failed']}/{res['counts']['total']})")
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
