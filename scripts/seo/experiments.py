#!/usr/bin/env python3
"""Контроль экспериментов: экспозиция, вердикт и запрет разделять совместное внедрение.

Для каждого активного эксперимента считается фактическая экспозиция — сколько
страниц действительно переобойдено поиском и сколько показов накоплено с момента
внедрения. Вердикт выносится только при достаточной экспозиции; до этого
публикуется too_early, а не «эффекта нет».

SEO-EXP-001 внедрён совместно (метаданные + FAQ одной правкой), поэтому их вклады
не разделяются: раздельная оценка на общих страницах невозможна по построению.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from textfmt import counted, num, ru_date  # noqa: E402

REGISTRY = pathlib.Path("reports/seo/intelligence/seo-experiments.json")
MIN_EXPOSURE_IMPRESSIONS = 500   # ниже — выборка не позволяет судить о кликабельности
MIN_EXPOSURE_DAYS = 7

# Вехи контрольных точек эксперимента: дни от старта. Прежде дата первой
# точки была зашита строкой «2026-08-26» и после прохождения продолжала
# показываться в письме как «следующая» (вопрос руководителя 30.08.2026).
REVIEW_MILESTONES_DAYS = (7, 14, 28)


def next_review_for(start: dt.date, today: dt.date,
                    explicit: str | None = None) -> str | None:
    """Ближайшая контрольная точка эксперимента, но только будущая.

    Явная дата из реестра уважается, пока не наступила; прошедшая дата не
    «следующая проверка» — тогда берётся ближайшая веха от старта (7/14/28
    дней). Если позади и все вехи, точки нет: эксперимент ждёт вердикта, и
    его состояние видно в «Контроле эксперимента», а не в списке проверок.
    """
    if explicit:
        d = dt.date.fromisoformat(explicit)
        if d >= today:
            return d.isoformat()
    future = [start + dt.timedelta(days=n) for n in REVIEW_MILESTONES_DAYS
              if start + dt.timedelta(days=n) >= today]
    return min(future).isoformat() if future else None


def load_registry() -> list[dict]:
    if not REGISTRY.exists():
        return []
    return json.loads(REGISTRY.read_text(encoding="utf-8")).get("experiments", [])


def cluster_keys(e: dict) -> dict:
    """Ключи атрибуции запросов кластера эксперимента.

    По умолчанию — имена страниц (slug и slug с пробелами), но проверка 31.08
    показала два провала эвристики: PAGES-EXP-001 приписывались показы запросов
    «оплата canva для юрлиц» (это старые страницы вендоров, не /alternatives/),
    а SEO-EXP-003 терял «claude»-запросы своего же кластера. Поэтому реестр
    может задавать явные маркеры:
      query_markers     — запрос кластера содержит любой из них;
      query_exclude     — запрос с любым из них исключается (чужой кластер);
      query_intent_any  — дополнительно обязателен один из интент-маркеров
                          (для страниц «аналогов» — «аналог/альтернатива/…»).
    Привязки запрос→страница у Вебмастера нет — это оценка, и она подписана
    оценкой в письме.
    """
    slugs = [p.rstrip("/").rsplit("/", 1)[-1] for p in e.get("pages") or []]
    markers = e.get("query_markers") or sorted(
        {s.replace("-", " ") for s in slugs} | set(slugs))
    return {
        "any": [m.lower() for m in markers],
        "exclude": [m.lower() for m in e.get("query_exclude") or []],
        "intent_any": [m.lower() for m in e.get("query_intent_any") or []],
    }


def query_matches(text: str, keys: dict) -> bool:
    low = text.lower()
    if any(x in low for x in keys.get("exclude") or []):
        return False
    if not any(m in low for m in keys.get("any") or []):
        return False
    intent = keys.get("intent_any") or []
    return not intent or any(i in low for i in intent)


def impressions_for(snap: dict, keys: dict) -> tuple[int | None, int | None]:
    """Показы и клики по запросам кластера эксперимента (оценка, см. cluster_keys)."""
    rows = [e for e in ((snap.get("yandex") or {}).get("entities") or [])
            if e.get("entity_type") == "query"]
    if not rows:
        return None, None
    imp = clicks = 0
    for r in rows:
        if query_matches(r["entity_id"], keys):
            imp += r.get("impressions") or 0
            clicks += r.get("clicks") or 0
    return imp, clicks


def verdict_for(days: int, impressions: int | None, live: int | None,
                total: int, min_imp: int = MIN_EXPOSURE_IMPRESSIONS) -> tuple[str, str]:
    if live is not None and total and live < total:
        return ("too_early",
                f"изменение выкачено на {live} из {total} страниц — эффект не может "
                "проявиться на всей группе")
    if days < MIN_EXPOSURE_DAYS:
        return ("too_early",
                f"прошло {days} дн. из {MIN_EXPOSURE_DAYS} минимальных: окно источника "
                "ещё не покрывает изменение")
    if impressions is None:
        return ("inconclusive", "экспозиция не измерена")
    if impressions < min_imp:
        return ("observing",
                f"накоплено {num(impressions)} показов из {min_imp} "
                "минимальных для вывода")
    return ("observing", "экспозиция набрана, ждём контрольную дату")


def control_dates_for(start: dt.date, explicit: str | None = None) -> list[str]:
    """Все контрольные даты эксперимента: вехи от старта плюс явная из реестра."""
    dates = {(start + dt.timedelta(days=n)).isoformat()
             for n in REVIEW_MILESTONES_DAYS}
    if explicit:
        dates.add(explicit)
    return sorted(dates)


def build(snap: dict, date: str, site_check: dict | None = None) -> list[dict]:
    # Вердикт-движок (задание руководителя 30.08.2026): оценка считается
    # ежедневно и показывается в веб-отчёте; в письмо расширенный блок и
    # запрос решения попадают только в контрольную дату. Сбой оценки не
    # ломает письмо: эксперимент остаётся с прежним наблюдательным вердиктом.
    import experiment_stats
    import experiment_verdict
    import serp_snippets

    # site_check: либо новый формат {"experiments": {...}, "date": "..."}
    # (load_site_check с fallback на свежайший файл), либо прежний плоский
    # словарь по id эксперимента — тесты и старые вызовы передают его.
    sc = site_check or {}
    if "experiments" in sc:
        checked_all, checked_date = sc["experiments"] or {}, sc.get("date")
    else:
        checked_all, checked_date = sc, None

    today = dt.date.fromisoformat(date)
    out = []
    for e in load_registry():
        if e.get("status") not in ("running", "observing"):
            continue
        pages = e.get("pages") or []
        start = dt.date.fromisoformat(e["start"])
        days = (today - start).days
        keys = cluster_keys(e)
        imp, clicks = impressions_for(snap, keys)
        # Порог экспозиции адаптивен (вопрос руководителя 31.08.2026): окно
        # источника скользящее, малый кластер настроенные 500 не наберёт
        # никогда — порог снижается до доли ёмкости, с пометкой в письме.
        gate, gate_adapted = experiment_stats.effective_gate(
            imp, MIN_EXPOSURE_IMPRESSIONS)
        checked = checked_all.get(e["id"], {})
        # Проверка живого сайта подтверждает выкат, но не обновление сниппета в
        # выдаче: индекс поисковика по своему же сайту не проверить. Разводим
        # эти сущности, чтобы не выдавать выкат за переобход.
        live = checked.get("pages_recrawled")
        snippets = checked.get("new_snippets_detected")
        # Обновление сниппета в выдаче измеряется своим же SERP-замером:
        # заголовок в топе сверяется с живым заголовком страницы (31.08.2026
        # выяснилось, что письмо писало «нет данных», хотя данные были).
        live_titles = {p["page"]: p.get("title") or ""
                       for p in checked.get("pages", []) if p.get("page")}
        try:
            serp = serp_snippets.serp_status(pages, live_titles, today)
        except Exception as exc:  # noqa: BLE001 - сбой SERP не ломает письмо
            print(f"serp_status({e['id']}): {exc}", file=sys.stderr)
            serp = None
        try:
            interim = experiment_stats.interim_comparison(keys, start, today)
        except Exception as exc:  # noqa: BLE001 - сбой сравнения не ломает письмо
            print(f"interim_comparison({e['id']}): {exc}", file=sys.stderr)
            interim = None
        if serp and serp.get("pages_with_new_snippet"):
            refresh = (f"новый сниппет виден в выдаче у "
                       f"{serp['pages_with_new_snippet']} из {len(pages)} страниц "
                       f"(замер {ru_date(serp['measured_at'])})")
        elif serp and serp.get("pages_seen"):
            refresh = (f"{serp['pages_seen']} из {len(pages)} страниц в выдаче, "
                       f"обновление сниппета не подтверждено "
                       f"(замер {ru_date(serp['measured_at'])})")
        else:
            refresh = ("не измерено: нет успешного SERP-замера за 7 дней"
                       if live else "нет данных")
        v, why = verdict_for(days, imp, live, len(pages), gate)
        out.append({
            "id": e["id"],
            # Тикет берём из реестра: три разных эксперимента с одним номером
            # в письме неразличимы.
            "ticket": e.get("ticket", "SEO-EXP-001"),
            "hypothesis": e.get("hypothesis", ""),
            "treatment": "; ".join(e.get("changes", [])),
            "combined_treatment": True,
            "combined_note": "Метаданные и FAQ внедрены одной правкой на одних и тех же "
                             "страницах, поэтому их вклады не разделяются.",
            "start": e["start"],
            "days_elapsed": days,
            "minimum_exposure": f"{MIN_EXPOSURE_DAYS} дн. и {MIN_EXPOSURE_IMPRESSIONS} показов",
            "pages_total": len(pages),
            "pages_live_with_treatment": live,
            "site_check_date": checked_date,
            "new_variant_detected_on_site": snippets,
            "search_snippet_refresh": refresh,
            "serp": serp,
            "interim": interim,
            "evaluation_kind": e.get("evaluation_kind", "ctr"),
            "exposure_min_impressions": gate,
            "exposure_gate_adapted": gate_adapted,
            "exposure_ok": (imp or 0) >= gate,
            "impressions_since_deploy": imp,
            "impressions_estimated": True,
            "clicks_since_deploy": clicks,
            "primary_metric": e.get("success_metric", ""),
            "current_result": (
                f"{counted(clicks, 'переход', 'перехода', 'переходов')} "
                f"на {counted(imp, 'показ', 'показа', 'показов')} по запросам кластеров"
                if imp else "экспозиция не измерена"),
            "confidence": "low" if (imp or 0) < MIN_EXPOSURE_IMPRESSIONS else "sufficient",
            "next_review": next_review_for(start, today, e.get("next_review")),
            "verdict": v,
            "verdict_reason": why,
            # Человеческие формулировки для письма: руководитель читает их, а не
            # исходные строки реестра.
            "hypothesis_plain": "понятнее ли описание страницы в выдаче для того, кто "
                                "покупает на компанию, и чаще ли по ней переходят",
            "treatment_plain": "переписали заголовок и описание страницы под покупку "
                               "по счёту и добавили блок ответов на частые вопросы.",
            "metric_plain": (
                "переходы из выдачи Яндекса по запросам страниц эксперимента; "
                "контрольные точки — "
                + " и ".join((start + dt.timedelta(days=n)).strftime("%d.%m")
                             for n in REVIEW_MILESTONES_DAYS[:2])),
            "confidence_plain": ("низкая: выборка мала" if (imp or 0) < MIN_EXPOSURE_IMPRESSIONS
                                 else "достаточная по объёму показов"),
        })
        rec = out[-1]
        rec["control_date_today"] = date in control_dates_for(
            start, e.get("next_review"))
        if rec["control_date_today"]:
            # Сегодня контрольная дата: проверка уже проведена, её результат —
            # в блоке «Контроль эксперимента». «Следующей» она быть не может
            # (вопрос руководителя 02.09.2026: письмо показывало 02.09 как
            # предстоящую проверку в самом письме от 02.09). Следующая — вехa
            # строго после сегодня.
            nxt = e.get("next_review")
            rec["next_review"] = next_review_for(
                start, today + dt.timedelta(days=1),
                nxt if nxt and nxt > date else None)
        try:
            rec["evaluation"] = experiment_verdict.evaluate(e, date)
            if rec["control_date_today"]:
                experiment_verdict.save_history(rec["evaluation"])
        except Exception as err:  # noqa: BLE001 — оценка не должна ронять письмо
            rec["evaluation"] = None
            print(f"experiments: оценка {e['id']} не выполнена: {err}",
                  file=sys.stderr)
    return out
