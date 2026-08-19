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
from textfmt import counted, num  # noqa: E402

REGISTRY = pathlib.Path("reports/seo/intelligence/seo-experiments.json")
MIN_EXPOSURE_IMPRESSIONS = 500   # ниже — выборка не позволяет судить о кликабельности
MIN_EXPOSURE_DAYS = 7


def load_registry() -> list[dict]:
    if not REGISTRY.exists():
        return []
    return json.loads(REGISTRY.read_text(encoding="utf-8")).get("experiments", [])


def impressions_for_pages(snap: dict, pages: list[str]) -> tuple[int | None, int | None]:
    """Показы и клики по страницам эксперимента.

    Яндекс.Вебмастер отдаёт выборку запросов без разбивки по страницам, поэтому
    считаем по запросам, содержащим имя вендора страницы: это оценка, а не точный
    охват, и она помечается как оценка в отчёте.
    """
    slugs = [p.rsplit("/", 1)[-1] for p in pages]
    rows = [e for e in ((snap.get("yandex") or {}).get("entities") or [])
            if e.get("entity_type") == "query"]
    if not rows:
        return None, None
    imp = clicks = 0
    for r in rows:
        low = r["entity_id"].lower()
        if any(s.replace("-", " ") in low or s in low for s in slugs):
            imp += r.get("impressions") or 0
            clicks += r.get("clicks") or 0
    return imp, clicks


def verdict_for(days: int, impressions: int | None, live: int | None,
                total: int) -> tuple[str, str]:
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
    if impressions < MIN_EXPOSURE_IMPRESSIONS:
        return ("observing",
                f"накоплено {num(impressions)} показов из {MIN_EXPOSURE_IMPRESSIONS} "
                "минимальных для вывода")
    return ("observing", "экспозиция набрана, ждём контрольную дату")


def build(snap: dict, date: str, site_check: dict | None = None) -> list[dict]:
    today = dt.date.fromisoformat(date)
    out = []
    for e in load_registry():
        if e.get("status") not in ("running", "observing"):
            continue
        pages = e.get("pages") or []
        start = dt.date.fromisoformat(e["start"])
        days = (today - start).days
        imp, clicks = impressions_for_pages(snap, pages)
        checked = (site_check or {}).get(e["id"], {})
        # Проверка живого сайта подтверждает выкат, но не обновление сниппета в
        # выдаче: индекс поисковика по своему же сайту не проверить. Разводим
        # эти сущности, чтобы не выдавать выкат за переобход.
        live = checked.get("pages_recrawled")
        snippets = checked.get("new_snippets_detected")
        v, why = verdict_for(days, imp, live, len(pages))
        out.append({
            "id": e["id"],
            "ticket": "SEO-EXP-001",
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
            "new_variant_detected_on_site": snippets,
            "search_snippet_refresh": ("не подтверждено" if live else "нет данных"),
            "search_snippet_refresh_note":
                "Выкат на сайте проверен напрямую. Обновил ли Яндекс сниппет в выдаче, "
                "по нашему сайту установить нельзя — это будет видно по данным "
                "Вебмастера через несколько дней после переобхода.",
            "impressions_since_deploy": imp,
            "impressions_estimated": True,
            "clicks_since_deploy": clicks,
            "primary_metric": e.get("success_metric", ""),
            "current_result": (
                f"{counted(clicks, 'переход', 'перехода', 'переходов')} "
                f"на {counted(imp, 'показ', 'показа', 'показов')} по запросам кластеров"
                if imp else "экспозиция не измерена"),
            "confidence": "low" if (imp or 0) < MIN_EXPOSURE_IMPRESSIONS else "sufficient",
            "next_review": e.get("next_review", "2026-08-26"),
            "verdict": v,
            "verdict_reason": why,
            # Человеческие формулировки для письма: руководитель читает их, а не
            # исходные строки реестра.
            "hypothesis_plain": "понятнее ли описание страницы в выдаче для того, кто "
                                "покупает на компанию, и чаще ли по ней переходят",
            "treatment_plain": "переписали заголовок и описание страницы под покупку "
                               "по счёту и добавили блок ответов на частые вопросы.",
            "metric_plain": "переходы из выдачи Яндекса по запросам этих пяти карточек; "
                            "первая контрольная точка — 26.08, вторая — 02.09",
            "confidence_plain": ("низкая: выборка мала" if (imp or 0) < MIN_EXPOSURE_IMPRESSIONS
                                 else "достаточная по объёму показов"),
        })
    return out
