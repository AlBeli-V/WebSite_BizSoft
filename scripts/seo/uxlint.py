#!/usr/bin/env python3
"""Email UX lint для executive-письма V3.

Проверяет письмо как продукт: объём, количество карточек, типографику, отсутствие
технического жаргона, ссылки, логические противоречия и правила автономности агентов.

Запуск: python3 scripts/seo/uxlint.py <дата>
Результат: reports/seo/intelligence/<дата>-uxlint.json (и код возврата 1 при ошибках)
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys

BASE = pathlib.Path("reports/seo/intelligence")

FORBIDDEN_TERMS = ["SOURCE_RECONCILIATION", "guardrail", "snapshot", "ym:s:", "popular queries",
                   "rollback", "stop-condition", "key events", "keyEvents"]
ZERO_DELTA_FORBIDDEN = ["вырос", "рост", "увеличил", "снизил", "падени", "сократил", "прибав"]
LIMITS = {"visible_words_max": 650, "visible_words_min": 450, "kpi_cards": 4,
          "change_cards": 3, "action_cards": 3, "charts": 2, "min_font_px": 14.0,
          "plain_words_max": 650}


def strip_tags(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


def visible_text(html: str) -> str:
    """Текст письма без футера и без alt-описаний."""
    body = html.split("<tr><td style=\"background:#fafafb;")[0]
    body = re.sub(r'alt="[^"]*"', " ", body)
    return strip_tags(body)


def run(date: str) -> dict:
    email = (BASE / f"{date}-executive-email.html").read_text(encoding="utf-8")
    preview = (BASE / f"{date}-executive.html").read_text(encoding="utf-8")
    text = (BASE / f"{date}-executive.txt").read_text(encoding="utf-8")
    snap = json.loads((BASE / "snapshots" / f"{date}.json").read_text(encoding="utf-8"))
    dq = json.loads((BASE / "data-quality" / f"{date}.json").read_text(encoding="utf-8"))
    actions = json.loads((BASE / "actions.json").read_text(encoding="utf-8"))

    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "status": "pass" if ok else "fail", "detail": detail})

    vis = visible_text(email)
    vw = len([w for w in vis.split() if w.strip(" ·—-|")])
    add("visible_words", LIMITS["visible_words_min"] <= vw <= LIMITS["visible_words_max"],
        f"{vw} видимых слов (коридор {LIMITS['visible_words_min']}–{LIMITS['visible_words_max']})")

    tw = len(text.split())
    add("plain_text_words", tw <= LIMITS["plain_words_max"], f"{tw} слов в текстовой версии")

    kpi = email.count("border-radius:10px;padding:12px 14px;")
    add("kpi_cards", kpi <= LIMITS["kpi_cards"], f"{kpi} карточек показателей")

    acts = len(actions["actions"])
    add("action_cards", acts <= LIMITS["action_cards"], f"{acts} карточек действий")

    changes = email.count("border-bottom:1px solid")
    add("change_cards", changes <= LIMITS["change_cards"], f"{changes} блоков изменений")

    imgs = len(re.findall(r"<img ", email))
    add("charts", imgs <= LIMITS["charts"], f"{imgs} изображений")

    add("no_inline_svg", "<svg" not in email, "inline SVG в письме отсутствует")

    body_part = email.split("<tr><td style=\"background:#fafafb;")[0]
    body_tags = [t for t in re.findall(r"<[^>]+font-size:[0-9.]+px[^>]*>", body_part) if "data-meta" not in t]
    body_fonts = [float(re.search(r"font-size:([0-9.]+)px", t).group(1)) for t in body_tags]
    meta_tags = [t for t in re.findall(r"<[^>]+font-size:[0-9.]+px[^>]*>", body_part) if "data-meta" in t]
    meta_fonts = [float(re.search(r"font-size:([0-9.]+)px", t).group(1)) for t in meta_tags]
    small_body = [f for f in body_fonts if f < LIMITS["min_font_px"]]
    small_meta = [f for f in meta_fonts if f < 12.5]
    add("no_small_font", not small_body and not small_meta,
        f"тело от {min(body_fonts):.1f}px, метаданные от {min(meta_fonts):.1f}px"
        if body_fonts and meta_fonts else "нет шрифтов")

    add("all_images_have_alt", len(re.findall(r"<img [^>]*alt=\"[^\"]+\"", email)) == imgs,
        "у всех изображений есть alt")

    raw_paths = re.findall(r"(?<!/)reports/seo/[a-zA-Z0-9._/-]+", visible_text(email))
    add("no_raw_repo_paths", not raw_paths, f"локальных путей в теле: {len(raw_paths)}")

    found_terms = [t for t in FORBIDDEN_TERMS if t.lower() in vis.lower()]
    add("no_forbidden_terms", not found_terms, f"запрещённые термины: {found_terms or 'нет'}")

    # Противоречие «дельта 0 / слова роста»
    idx = snap["yandex"]["indexation"]["indexed_urls"]
    zero_sentences = [s for s in re.split(r"(?<=[.!?])\s+", vis) if str(idx) in s and "не изменилось" in s]
    bad_words = [w for s in zero_sentences for w in ZERO_DELTA_FORBIDDEN if w in s.lower()]
    add("no_zero_delta_contradiction", not bad_words,
        f"в блоке с нулевой дельтой слов роста/падения: {bad_words or 'нет'}")

    # Воронка запрещена до завершения сверки
    reconciled = not any(f["code"] == "SOURCE_RECONCILIATION" for f in dq["findings"])
    funnel_img = bool(re.search(r'(src|cid)[^>]*funnel', email))
    add("no_funnel_before_reconciliation", reconciled or not funnel_img,
        "воронка не показывается: вместо неё карта измерения" if not funnel_img else "воронка показана")

    # Совместное внедрение не разбивается на два эксперимента
    combined = [a for a in actions["actions"] if a.get("combined_deployment")]
    split_claim = "CRO-EXP-002" in vis
    add("no_split_experiment_claim", not split_claim,
        f"совместных внедрений: {len(combined)}; в письме не заявляется раздельная оценка")

    # Владельцы GREEN/YELLOW назначены ролью, а не руководителем
    manual = [a["id"] for a in actions["actions"]
              if a["zone"] in ("GREEN", "YELLOW") and not a.get("owner_role")]
    add("no_manual_owner_for_green_yellow", not manual and "назначает руководитель" not in vis,
        f"без ручного назначения владельцев: {manual or 'ок'}")

    # Рыночный спрос: месячная величина не выдаётся за суточную и за наши показы
    demand_sentences = [snt for snt in re.split(r"(?<=[.!?])\s+", vis)
                        if "запросов в месяц" in snt or "показов в месяц" in snt
                        or "спрос" in snt.lower()]
    daily_words = ("за сутки", "вчера", "за день", "день ко дню")
    mixed = [snt for snt in demand_sentences if any(w in snt.lower() for w in daily_words)]
    add("demand_not_daily", not mixed,
        f"предложений о спросе: {len(demand_sentences)}; смешанных с суточными словами: "
        f"{len(mixed)}")

    # Спрос рынка не подменяет наши показы, доля голоса не публикуется
    substitution = [t for t in ("доля голоса", "наши показы в вордстате", "показы вордстата у нас")
                    if t in vis.lower()]
    add("demand_not_our_impressions", not substitution,
        f"подмен понятий: {substitution or 'нет'}")

    # Ссылки
    links = re.findall(r'href="([^"]+)"', email)
    add("links_absolute", all(l.startswith("http") for l in links), f"{len(links)} ссылок, все абсолютные")

    add("preview_uses_relative_images", "cid:" not in preview,
        "preview-версия ссылается на файлы, письмо — на вложения")

    failed = [c for c in checks if c["status"] == "fail"]
    return {"report_date": date, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "limits": LIMITS, "checks": checks,
            "summary": {"total": len(checks), "passed": len(checks) - len(failed), "failed": len(failed)},
            "status": "pass" if not failed else "fail"}


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    res = run(date)
    (BASE / f"{date}-uxlint.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in res["checks"]:
        mark = "OK  " if c["status"] == "pass" else "FAIL"
        print(f"  [{mark}] {c['check']}: {c['detail']}")
    print(f"UX lint: {res['status']} ({res['summary']['passed']}/{res['summary']['total']})")
    return 0 if res["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
