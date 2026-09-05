#!/usr/bin/env python3
"""Техническое состояние сайта для ежедневного отчёта: PageSpeed.

Замеры снимает scripts/ops/pagespeed_monitor.mjs, здесь — трактовка: пороги,
регрессии и приоритет. Разделение нужно, чтобы правила решений проверялись
тестами, а не только живым прогоном с расходом квоты API.

Три вещи, за которыми модуль следит особо.

Первая: Lighthouse шумит. Падение на два-три очка — обычное колебание замера,
и объявлять его деградацией значит приучить читателя не верить блоку. Поэтому
предупреждение начинается с пяти очков, критичность — с десяти.

Вторая: балл SEO у Lighthouse — не про продвижение. Он говорит лишь об
отсутствии части базовых технических ошибок вёрстки, поэтому попадает в
техническое здоровье и никогда — в SEO-показатели отчёта.

Третья: отсутствие данных — не поломка отчёта. Если PSI недоступен, блок
показывает возраст последнего удачного замера, а письмо выходит как обычно.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib

import passport

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "pagespeed-monitor.json"
LATEST = ROOT / "reports" / "seo" / "pagespeed" / "latest.json"
HISTORY = ROOT / "reports" / "seo" / "pagespeed" / "history"

PAGE_TYPE_RU = {
    "homepage": "Главная",
    "vendor": "Вендорская страница",
    "product": "Карточка товара",
    "catalog": "Каталог",
    "category": "Категория",
    "content": "Статья",
    "heavy": "Сравнение",
}


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _mobile(pages: list[dict]) -> list[dict]:
    """Решения принимаются по мобильной выдаче: это основной трафик."""
    return [p for p in pages if p.get("strategy") == "mobile" and not p.get("error")]


def score_status(value: int | None, green: int, yellow: int | None = None) -> str:
    if value is None:
        return "unknown"
    if value >= green:
        return "green"
    if yellow is None or value >= yellow:
        return "yellow"
    return "red"


def compare(current: dict, previous: dict | None, cfg: dict) -> list[dict]:
    """Изменения относительно прошлого замера — только значимые.

    Сравниваются одноимённые страницы мобильной стратегии. Малое колебание
    (до четырёх очков) сознательно не попадает в результат: это шум замера,
    а не деградация сайта.
    """
    if not previous:
        return []
    reg = cfg["thresholds"]["regression"]
    prev_by_path = {p["path"]: p for p in _mobile(previous.get("pages") or [])}
    out = []
    for page in _mobile(current.get("pages") or []):
        was = prev_by_path.get(page["path"])
        if not was:
            continue
        issues = []
        p_now, p_was = page.get("performance"), was.get("performance")
        drop = None
        if p_now is not None and p_was is not None:
            drop = p_was - p_now
            if drop >= reg["performance_critical"]:
                issues.append({"kind": "performance", "level": "critical",
                               "was": p_was, "now": p_now, "delta": -drop})
            elif drop >= reg["performance_warning"]:
                issues.append({"kind": "performance", "level": "warning",
                               "was": p_was, "now": p_now, "delta": -drop})
        l_now, l_was = page.get("lcp_ms"), was.get("lcp_ms")
        if l_now and l_was:
            worse = (l_now - l_was) / l_was * 100
            if worse > reg["lcp_warning_pct"]:
                issues.append({"kind": "lcp", "level": "warning",
                               "was": l_was, "now": l_now, "delta_pct": round(worse)})
        c_now, c_was = page.get("cls"), was.get("cls")
        if c_now is not None and c_was is not None:
            if c_now - c_was > reg["cls_warning_abs"]:
                issues.append({"kind": "cls", "level": "warning",
                               "was": c_was, "now": c_now,
                               "delta": round(c_now - c_was, 3)})
        if issues:
            out.append({"path": page["path"], "pageType": page.get("pageType"),
                        "performance": p_now, "issues": issues})
    return out


def likely_cause(page: dict, issues: list[dict]) -> str:
    """Техническая гипотеза по составу метрик — куда смотреть в первую очередь."""
    kinds = {i["kind"] for i in issues}
    if "cls" in kinds:
        return "смещения вёрстки: изображение или блок без заданных размеров"
    if "lcp" in kinds:
        return "главное изображение экрана или блокирующая отрисовку загрузка"
    tbt = page.get("tbt_ms")
    if tbt and tbt > 300:
        return "javascript: длинные задачи в основном потоке"
    return "требуется разбор аудита Lighthouse"


def priority(issues: list[dict], performance: int | None) -> str:
    if any(i["level"] == "critical" for i in issues) or (
            performance is not None and performance < 80):
        return "P1 — разобрать сегодня"
    return "P2 — разобрать на неделе"


def build(date: str) -> dict:
    """Блок технического состояния для снимка дня.

    Возвращает состояние даже тогда, когда замеров нет: отчёт не должен
    зависеть от доступности стороннего API.
    """
    cfg = load_config()
    if not LATEST.exists():
        # Паспортный status описывает доступность источника, level — светофор
        # техники. Разные вопросы: «прочиталось ли» и «всё ли в порядке».
        return {**passport.unavailable("no_file",
                                       source="история замеров PageSpeed"),
                "level": "unknown"}
    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    pages = _mobile(latest.get("pages") or [])
    if not pages:
        # PSI ответил, но метрик нет: квота, таймаут или отказ страницы.
        # Причина — код, подробность — что именно не прочиталось.
        return {**passport.unavailable(
            "api_error", source="PageSpeed Insights",
            detail=latest.get("reason") or "ответ без метрик",
            last_success=latest.get("date")), "level": "unknown"}

    previous = _previous_measurement(latest.get("date"))
    regressions = compare(latest, previous, cfg)

    th = cfg["thresholds"]
    perf = [p["performance"] for p in pages if p.get("performance") is not None]
    worst = min(perf) if perf else None
    home = next((p for p in pages if p["pageType"] == "homepage"), pages[0])

    statuses = [score_status(p.get("performance"), th["performance"]["green"],
                             th["performance"]["yellow"]) for p in pages]
    level = "green"
    if "red" in statuses or any(
            i["level"] == "critical" for r in regressions for i in r["issues"]):
        level = "red"
    elif "yellow" in statuses or regressions:
        level = "yellow"

    problems = []
    for r in sorted(regressions,
                    key=lambda r: 0 if any(i["level"] == "critical"
                                           for i in r["issues"]) else 1)[:3]:
        problems.append({
            "path": r["path"],
            "page_type": PAGE_TYPE_RU.get(r["pageType"], r["pageType"] or "страница"),
            "issues": r["issues"],
            "cause": likely_cause(
                next(p for p in pages if p["path"] == r["path"]), r["issues"]),
            "priority": priority(r["issues"], r["performance"]),
        })

    return {
        # status — паспорт источника, level — светофор техники.
        "status": "ok",
        "level": level,
        "available": True,
        # as_of — дата самих данных: замер может быть вчерашним, если
        # сегодняшний не удался, и читатель должен это видеть.
        "as_of": latest.get("date"),
        "date": latest.get("date"),
        "mode": latest.get("mode"),
        "age_days": _age_days(latest.get("date"), date),
        "mobile_performance": home.get("performance"),
        "worst_performance": worst,
        "pages_checked": len(pages),
        "pages": [{"path": p["path"],
                   "page_type": PAGE_TYPE_RU.get(p["pageType"], p["pageType"]),
                   "performance": p.get("performance"),
                   "seo": p.get("seo"),
                   "accessibility": p.get("accessibility"),
                   "best_practices": p.get("best_practices"),
                   "lcp_ms": p.get("lcp_ms"), "cls": p.get("cls"),
                   "field": p.get("field")} for p in pages],
        "previous_date": (previous or {}).get("date"),
        "regressions": problems,
        "lcp_ok": all((p.get("lcp_ms") or 0) <= 4000 for p in pages),
        "cls_ok": all((p.get("cls") or 0) <= 0.1 for p in pages),
        "last_full": _last_full_audit(),
    }


def _previous_measurement(current_date: str | None) -> dict | None:
    """Прошлый удачный замер — точка сравнения; сегодняшний в неё не входит."""
    if not HISTORY.exists():
        return None
    for f in sorted(HISTORY.glob("*.json"), reverse=True):
        if current_date and f.stem >= current_date:
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        if _mobile(data.get("pages") or []):
            return data
    return None


def _last_full_audit() -> dict | None:
    """Последняя расширенная выборка: она одна показывает состояние шаблонов."""
    if not HISTORY.exists():
        return None
    for f in sorted(HISTORY.glob("*.json"), reverse=True):
        data = json.loads(f.read_text(encoding="utf-8"))
        if data.get("mode") != "weekly":
            continue
        pages = _mobile(data.get("pages") or [])
        if not pages:
            continue
        cfg = load_config()
        th = cfg["thresholds"]["performance"]
        buckets = {"green": 0, "yellow": 0, "red": 0, "unknown": 0}
        for p in pages:
            buckets[score_status(p.get("performance"), th["green"], th["yellow"])] += 1
        return {"date": data["date"], "urls": len(pages), **buckets}
    return None


def _age_days(measured: str | None, today: str) -> int | None:
    if not measured:
        return None
    try:
        a = dt.date.fromisoformat(measured)
        b = dt.date.fromisoformat(today)
    except ValueError:
        return None
    return (b - a).days


def email_line(block: dict) -> str:
    """Одна строка для письма: состояние, балл и суть изменения."""
    if not block.get("available"):
        last = block.get("last_success")
        tail = f"последний замер {last}" if last else "замеров ещё не было"
        return f"Техника: НЕТ ДАННЫХ · {tail}"
    label = {"green": "GREEN", "yellow": "YELLOW", "red": "RED"}[block["level"]]
    perf = block.get("mobile_performance")
    head = f"Техника: {label} · PSI mobile {perf}" if perf is not None else \
           f"Техника: {label}"
    if not block.get("regressions"):
        return f"{head} · регрессий нет"
    r = block["regressions"][0]
    worst = next((i for i in r["issues"] if i["kind"] == "performance"), None)
    if worst:
        return f"{head} ↓{abs(worst['delta'])} · {r['page_type'].lower()}: просадка"
    lcp = next((i for i in r["issues"] if i["kind"] == "lcp"), None)
    if lcp:
        return f"{head} · LCP +{lcp['delta_pct']}% · {r['page_type'].lower()}"
    return f"{head} · {r['page_type'].lower()}: смещения вёрстки"


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    print(json.dumps(build(d), ensure_ascii=False, indent=1))
