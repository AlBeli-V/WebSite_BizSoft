#!/usr/bin/env python3
"""BIZSoft Growth Intelligence — Executive Command Center (письмо V4).

Панель управления ростом: результат, причины изменений, автономные действия,
состояние экспериментов и следующие контрольные точки. Порядок блоков фиксирован:

  A Header · B Status bar · C От вас · D Четыре показателя · E Сигналы дня ·
  E-а Заявки за сутки · E-б Реклама · F Драйверы и детракторы ·
  G Контроль экспериментов · H Автономное исполнение · I Радар возможностей ·
  J Здоровье данных и риски · K Контрольные точки · L Ссылки

Объём 800–1200 видимых слов, первый экран — не более 250 (потолок поднят
29–30.08.2026 под секции «Реклама», «Перспективные идеи» и loop-health;
правило: новая постоянная секция расширяет потолок в том же PR).
Числа берутся только из снимка и аналитических модулей; в текст не вписываются.

Запуск: python3 scripts/seo/report_v4.py [YYYY-MM-DD]
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "viz"))

import ads_block                      # noqa: E402
import charts_v4                      # noqa: E402
import kpi_kit as kit                 # noqa: E402
import drivers as drivers_mod         # noqa: E402
import invariants as invariants_mod   # noqa: E402
import passport                      # noqa: E402
import technical                     # noqa: E402
import leads as leads_mod             # noqa: E402
import measurement                    # noqa: E402
import experiments as exp_mod         # noqa: E402
import loop_health as loop_health_mod  # noqa: E402
import opportunity as opp_mod         # noqa: E402
import snapshot as snapshot_mod       # noqa: E402
import vendor_radar as vendor_radar_mod  # noqa: E402
from textfmt import (counted, num, plural, pct, ru_date,  # noqa: E402
                     ru_date_full, signed, signed_pct)

BASE = pathlib.Path("reports/seo/intelligence")
REPO = "https://github.com/AlBeli-V/WebSite_BizSoft"
BRANCH = "seo-data"
BLOB = f"{REPO}/blob/{BRANCH}"
# Адрес опубликованной страницы отчёта. Файл проще переменной окружения: он
# лежит в данных (ветка seo-data), виден в репозитории и переживает
# пересоздание среды; переменная окружения его переопределяет.
REPORT_URL_FILE = pathlib.Path("reports/seo/public/report-url.txt")
PUBLIC_REPORT_BASE_URL = os.environ.get("PUBLIC_REPORT_BASE_URL", "").rstrip("/")
if not PUBLIC_REPORT_BASE_URL and REPORT_URL_FILE.exists():
    PUBLIC_REPORT_BASE_URL = REPORT_URL_FILE.read_text(encoding="utf-8").strip().rstrip("/")
DEMAND_STATE = pathlib.Path("reports/seo/wordstat/intelligence-state.json")
GROWTH_IDEAS = pathlib.Path("reports/seo/intelligence/growth-ideas.json")
LOOP_HEALTH = pathlib.Path("reports/seo/intelligence/loop-health.json")

# ── Design tokens ───────────────────────────────────────────────────────────
# Палитра — из KPI-kit (scripts/viz/kpi_kit.py): один визуальный слой у письма,
# веб-отчёта и конкурентной разведки. Ключи сохранены ради существующей вёрстки.
T = {
    "background": kit.LIGHT["plane"], "surface": kit.LIGHT["surface"],
    "text_primary": kit.LIGHT["ink"], "text_secondary": kit.LIGHT["muted"],
    "border": kit.LIGHT["hair"], "brand": kit.LIGHT["accent"],
    "positive": kit.LIGHT["good"], "warning": kit.LIGHT["warn"], "info": kit.LIGHT["s1"],
    "danger": kit.LIGHT["crit"], "muted": kit.LIGHT["gray"],
}
SP = {"xs": 4, "s": 8, "m": 12, "l": 16, "xl": 24, "xxl": 32}
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',"
        "Arial,sans-serif")
FIRST_SCREEN_MARKER = "<!--first-screen-end-->"

# База, ниже которой относительное изменение не публикуется. Совпадает с
# порогом low_base в quality.delta: одно определение малой базы на всю систему.
LOW_BASE = 30

PILL_COLOUR = {
    "positive": T["positive"], "mixed": T["warning"], "negative": T["danger"],
    "stable": T["info"], "verified": T["positive"], "limited": T["warning"],
    "degraded": T["danger"], "none": T["muted"], "required": T["brand"],
    "unknown": T["muted"],
}
PILL_LABEL = {
    "positive": "рост", "mixed": "смешанная", "negative": "снижение",
    "stable": "без изменений", "verified": "сверено", "limited": "ограничено",
    "degraded": "сбой", "none": "не требуется", "required": "требуется",
    "unknown": "нет данных",
}
VERDICT_LABEL = {
    "too_early": "рано для вывода", "observing": "наблюдаем",
    "positive": "подтверждён", "negative": "не подтверждён",
    "inconclusive": "вывод невозможен",
}
STAGE_LABEL = {
    "proposed": "предложено", "approved": "утверждено", "implemented": "внедрено",
    "tested": "проверено", "deployed": "на сайте", "observing": "наблюдение",
    "accepted": "принято", "rejected": "отклонено", "blocked": "заблокировано",
}


def words(*parts: str) -> int:
    text = re.sub(r"<[^>]+>", " ", " ".join(p for p in parts if p))
    return len([w for w in re.split(r"\s+", text) if w.strip(" ·—–-|→")])


# ── Аналитические блоки ─────────────────────────────────────────────────────

def index_drop(snap: dict, prev: dict | None) -> dict | None:
    """Падение числа страниц в поиске Яндекса против предыдущего снимка.

    Возвращает размер падения и признак материальности: дневное дрожание
    индекса — обычное дело (663 → 650), обвал — нет (650 → 455).
    """
    if not prev:
        return None
    now = ((snap.get("yandex") or {}).get("indexation") or {}).get("indexed_urls")
    was = ((prev.get("yandex") or {}).get("indexation") or {}).get("indexed_urls")
    if now is None or was is None or not was or now >= was:
        return None
    lost = was - now
    share = lost / was
    th = snap.get("thresholds") or {}
    return {
        "was": was, "now": now, "lost": lost, "share": share,
        "material": (share >= (th.get("index_drop_share") or 0.05)
                     and lost >= (th.get("index_drop_pages") or 20)),
    }


def search_status(snap: dict, prev: dict | None) -> str:
    """positive | mixed | negative | stable | unknown — по знакам изменений доступных систем."""
    # Без единого доступного источника поиска статус неизвестен независимо от
    # наличия предыдущего снимка: «без изменений» утверждало бы измерение,
    # которого не было.
    if not (snap["yandex"].get("available") or snap["google"].get("available")):
        return "unknown"
    if not prev:
        return "stable"
    signs = []
    if snap["google"].get("available") and prev["google"].get("available"):
        g = snap["google"]["totals"]
        signs.append(1 if g["impressions_last7"] > g["impressions_prev7"]
                     else (-1 if g["impressions_last7"] < g["impressions_prev7"] else 0))
    if snap["yandex"].get("available") and prev["yandex"].get("available"):
        yt, yp = snap["yandex"]["totals"], prev["yandex"]["totals"]
        for key in ("impressions", "queries_position_le_10"):
            d = (yt.get(key) or 0) - (yp.get(key) or 0)
            signs.append(1 if d > 0 else (-1 if d < 0 else 0))
        # Индекс — отдельный знак, и обвал перебивает остальные. Показы
        # считаются по окну прошлых дней и об индексе сегодняшнего дня не
        # знают: 09.09.2026 индекс упал 650 → 455, показы за прошлую неделю
        # выросли, и статус письма вышел «рост».
        drop = index_drop(snap, prev)
        if drop:
            signs.append(-1)
            if drop["material"]:
                return "negative"
    if not signs:
        # Ни одна система не отдала данных в оба дня. «Без изменений» здесь
        # утверждало бы измерение, которого не было, — статус честно неизвестен.
        return "unknown"
    if all(s == 0 for s in signs):
        return "stable"
    if all(s >= 0 for s in signs):
        return "positive"
    if all(s <= 0 for s in signs):
        return "negative"
    return "mixed"


# Канонические статусы источника → причина для читателя (см. методичку).
STATUS_REASON = {"missing": "выгрузки нет",
                 "empty": "источник ответил без данных",
                 "malformed": "формат выгрузки не распознан"}
STATUS_SHORT = {"missing": "выгрузки нет",
                "empty": "ответ без данных",
                "malformed": "формат не распознан"}


def stale_sources(dq: dict) -> set:
    """Источники, не обновившиеся с прошлого отчёта, — вывод проверки качества.

    Письмо повторяет вывод слоя качества, а не вычисляет заново по сырым
    полям; для старых файлов data-quality без блока derived — по находкам.
    """
    derived = dq.get("derived") or {}
    if "stale_sources" in derived:
        return set(derived["stale_sources"])
    return {f.get("source") for f in (dq.get("findings") or [])
            if f.get("code") == "SOURCE_NOT_UPDATED" and f.get("source")}


def _no_data_card(key: str, label: str, unit: str, block: dict, source_label: str) -> dict:
    """Карточка источника, не отдавшего данные: «нет данных» вместо нуля.

    Причина называется по каноническому статусу источника; период берётся из
    source, когда он известен даже при сбое. Дельты и сравнения не
    публикуются: сравнивать с отсутствующим замером нечего, а дельта от нуля
    была бы выдумкой.
    """
    src = block.get("source") or {}
    reason = STATUS_REASON.get(src.get("status"), "источник вернул ошибку")
    period = (f"{ru_date(src.get('current_period_start'))}–"
              f"{ru_date(src.get('current_period_end'))}"
              if src.get("current_period_start") else "период неизвестен")
    return {"key": key, "label": label, "value": num(None), "unit": unit,
            "delta": None, "delta_dir": None, "relative": None,
            "relative_note": "дельты не публикуются: данных нет",
            "period": period, "source": source_label,
            "confidence": reason,
            "interpretation": f"Источник не отдал данные за период: {reason}. "
                              "Показатель не равен нулю — он не измерен, поэтому "
                              "сравнение с прошлым замером не публикуется.",
            "muted": True, "sparkline": None}



def _daily_windows(dq_or_snap: dict, source: str) -> dict | None:
    """Полные окна источника из дневной витрины снимка, иначе None."""
    blk = (dq_or_snap.get("daily") or {}).get(source) or {}
    return blk if blk.get("complete") else None


def _daily_card_common(win: dict) -> dict:
    """Общие поля карточки, считанные из окна витрины."""
    cur, prev = win["current"], win["previous"]
    delta = win.get("delta")
    return {
        "value_num": cur["sum"],
        "delta_num": delta,
        "period": f"{ru_date(cur['from'])}–{ru_date(cur['to'])}",
        "period_vs": f"против {ru_date(prev['from'])}–{ru_date(prev['to'])}",
        "prev_num": prev["sum"],
    }


def kpi_cards(snap: dict, prev: dict | None, dq: dict) -> list[dict]:
    """Четыре показателя руководителя. Отсутствие CRM — приглушённое состояние."""
    y_block, g_block = snap["yandex"], snap["google"]
    m = snap["analytics"]["metrika"]
    sample = dq.get("sample_ctr") or {}
    rules = dq.get("publication_rules") or {}
    # Абсолютная разница показов публикуется только тогда, когда её есть с чем
    # сравнивать. При разной длине окна и пересобранной выборке два числа
    # складываются из разных слагаемых, и их разность не описывает видимость:
    # на 20.08 → 21.08 окна были 12 и 13 дней, а состав выборки сменился на
    # четверть — заявленный прирост в 107 показов объяснялся этим целиком.
    show_delta = rules.get("allow_absolute_delta", True)
    stale_set = stale_sources(dq)
    cards = []

    y_daily = _daily_windows(snap, "yandex") if rules.get("kpi_from_daily") else None
    if y_daily:
        # Показы всего сайта из дневной витрины: окна равной длины встык,
        # дельта — сравнение независимых периодов. Выборка запросов остаётся
        # только вспомогательной строкой о первой странице.
        w = _daily_card_common(y_daily["windows"]["impressions"])
        imp = int(w["value_num"])
        delta = int(w["delta_num"]) if w["delta_num"] is not None else None
        clicks_cur = y_daily["windows"]["clicks"]["current"]["sum"]
        # CTR по всему сайту: показы и клики витрины — один охват, отношение
        # корректно без оговорки про выборку.
        site_ctr = (clicks_cur / imp) if imp else None
        yt = y_block.get("totals") or {}
        top10_note = (f"На первой странице {yt.get('queries_position_le_10')} из "
                      f"{yt.get('queries_tracked')} запросов выборки. "
                      if y_block.get("available") else "")
        cards.append(
            {"key": "yandex", "label": "Видимость в Яндексе",
             "value": num(imp), "unit": "показов за неделю",
             "delta": signed(delta) if delta is not None else None,
             "delta_dir": _dir(delta) if delta is not None else None,
             "relative": (signed_pct(delta / w["prev_num"])
                          if delta is not None and w["prev_num"] >= LOW_BASE else None),
             "relative_note": ("низкая база прошлой недели"
                               if delta is not None and w["prev_num"] < LOW_BASE else None),
             "period": w["period"],
             "source": "Яндекс.Вебмастер, весь сайт, дневные ряды",
             "confidence": ("достаточная"
                            if imp >= snap["thresholds"]["low_impressions"]
                            else "низкая, малые числа"),
             "interpretation": (top10_note
                                + (f"CTR {pct(site_ctr, 2)} по всему сайту."
                                   if site_ctr is not None else "")),
             "muted": False,
             "sparkline": y_daily["windows"]["impressions"].get("tail"),
             "sparkline_from": y_daily["windows"]["impressions"]["previous"]["from"]})
    elif y_block.get("available"):
        yt = y_block["totals"]
        yp = (prev or {}).get("yandex", {}).get("totals", {})
        imp_delta = (yt["impressions"] - yp["impressions"]) if (yp and show_delta) else None
        top_delta = (yt["queries_position_le_10"] - yp["queries_position_le_10"]) if yp else None
        days = y_block["source"].get("current_period_days")
        per_day = round(yt["impressions"] / days) if days else None
        delta_note = (None if show_delta else
                      "разница с прошлым замером не публикуется: окна разной длины "
                      "или выборка пересобрана — сравнивать нечего с чем")
        cards.append(
            {"key": "yandex", "label": "Видимость в Яндексе",
             "value": num(yt["impressions"]), "unit": "показов",
             "delta": signed(imp_delta) if imp_delta is not None else None,
             "delta_dir": _dir(imp_delta) if imp_delta is not None else None,
             "relative": None,
             "relative_note": delta_note or
                              "относительный процент не публикуется: окна источника пересекаются",
             "period": f"{ru_date(y_block['source']['current_period_start'])}–"
                       f"{ru_date(y_block['source']['current_period_end'])}",
             "source": f"Яндекс.Вебмастер, {measurement.yandex_scope_label(y_block)}",
             # Достоверность — из порога методики, а не константой.
             "confidence": ("достаточная"
                            if (yt["impressions"] or 0) >= snap["thresholds"]["low_impressions"]
                            else "низкая, малые числа"),
             "interpretation": (f"В среднем {num(per_day)} показов в день за {days} дн. "
                                if per_day else "") +
                               f"На первой странице {yt['queries_position_le_10']} из "
                               f"{yt['queries_tracked']} запросов выборки" +
                               # Без предыдущего замера фраза «к вчера» не имеет
                               # правой части — сравнение просто не называется.
                               (f", {signed(top_delta)} к вчера. "
                                if top_delta is not None else ". ") +
                               f"{sample.get('label', 'CTR выборки')} "
                               f"{pct(sample.get('value'), 2)} — "
                               f"{sample.get('caveat', '')}.",
             "muted": False, "sparkline": None})
    else:
        cards.append(_no_data_card("yandex", "Видимость в Яндексе", "показов",
                                   y_block, "Яндекс.Вебмастер, запросы хоста"))

    g_daily = _daily_windows(snap, "gsc") if rules.get("kpi_from_daily") else None
    if g_daily:
        w = _daily_card_common(g_daily["windows"]["impressions"])
        imp = int(w["value_num"])
        delta = int(w["delta_num"]) if w["delta_num"] is not None else None
        clicks_cur = int(g_daily["windows"]["clicks"]["current"]["sum"])
        clicks_prev = g_daily["windows"]["clicks"].get("previous") or {}
        clicks_was = clicks_prev.get("sum")
        # «Пока нет» — утверждение обо всём прошлом, и оно неверно, если в
        # прошлом окне переход был. 09.09.2026 плитка писала «Переходов из
        # Google пока нет» при росте показов на 110,9%, тогда как переходы за
        # то же окно ушли с одного до нуля: это не отсутствие, а падение.
        if clicks_cur:
            interpretation = f"Переходы из Google за окно: {num(clicks_cur)}."
        elif clicks_was:
            interpretation = (f"За окно переходов из Google нет; "
                              f"в прошлом окне {num(int(clicks_was))}.")
        else:
            interpretation = "Переходов из Google пока нет."
        cards.append(
            {"key": "google", "label": "Видимость в Google",
             "value": num(imp), "unit": "показов за неделю",
             "delta": signed(delta) if delta is not None else None,
             "delta_dir": _dir(delta) if delta is not None else None,
             "relative": (signed_pct(delta / w["prev_num"])
                          if delta is not None and w["prev_num"] >= LOW_BASE else None),
             "relative_note": "низкая база: десятки показов"
                              if delta is not None and w["prev_num"] < LOW_BASE else None,
             "period": w["period"],
             "source": "Google Search Console, весь сайт, дневные ряды",
             "confidence": ("данные не обновились с прошлого отчёта"
                            if "google" in stale_set else
                            "низкая, малые числа"
                            if imp < snap["thresholds"]["low_impressions"]
                            else "достаточная"),
             "interpretation": interpretation,
             "muted": False,
             "sparkline": g_daily["windows"]["impressions"].get("tail"),
             "sparkline_from": g_daily["windows"]["impressions"]["previous"]["from"],
             "slope": {"prev_label": "пред. неделя", "prev": int(w["prev_num"]),
                       "cur_label": "эта неделя", "cur": imp,
                       "label": "Показы Google за неделю"}})
    elif g_block.get("available"):
        gt = g_block["totals"]
        daily = [d["impressions"] for d in (g_block.get("daily") or [])][-14:]
        # Сравнение недель публикуется только при двух полных окнах: у молодой
        # или отстающей выгрузки «предыдущая неделя» короче семи дней, и
        # разность окон разной длины — не изменение видимости (тот же принцип,
        # что WINDOW_LENGTH_MISMATCH у Яндекса). Старые снимки без полей
        # длины считаются полными.
        full_weeks = (gt.get("last7_days", 7) == 7 and gt.get("prev7_days", 7) == 7)
        d7 = (gt["impressions_last7"] - gt["impressions_prev7"]) if full_weeks else None
        # Утверждение о переходах выводится из измеренных кликов, а не
        # константой: зашитое «переходов нет» становится ложью в первый же
        # день с кликом. «Пока нет» — только при доказанном источником нуле.
        clicks_window = gt.get("clicks_window")
        interpretation = (f"Переходы из Google за окно: {num(clicks_window)}."
                          if clicks_window else
                          "Переходов из Google пока нет." if clicks_window == 0 else
                          "Число переходов из Google в этой выгрузке не измерено.")
        cards.append(
            {"key": "google", "label": "Видимость в Google",
             "value": num(gt["impressions_last7"]), "unit": "показов за неделю",
             "delta": signed(d7) if d7 is not None else None,
             "delta_dir": _dir(d7) if d7 is not None else None,
             # Процент при малой базе — это шум, поданный как результат. Рост с 19
             # до 38 показов даёт «+100,0 %», хотя при пуассоновском разбросе
             # такая разница ожидаема. Абсолютные числа остаются, процент — нет.
             "relative": (signed_pct(d7 / gt["impressions_prev7"])
                          if d7 is not None and gt["impressions_prev7"] >= LOW_BASE
                          else None),
             "relative_note": ("низкая база: десятки показов" if full_weeks else
                               f"окна сравнения неполные "
                               f"({gt.get('last7_days')} и {gt.get('prev7_days')} дн.) — "
                               f"дельта не публикуется"),
             "period": f"{ru_date(gt['last7_start'])}–{ru_date(gt['last7_end'])} "
                       f"против {ru_date(gt['prev7_start'])}–{ru_date(gt['prev7_end'])}",
             "source": "Google Search Console, весь сайт",
             "confidence": ("данные не обновились с прошлого отчёта"
                            if "google" in stale_set else
                            "низкая, малые числа"
                            if gt["impressions_last7"] < snap["thresholds"]["low_impressions"]
                            else "достаточная"),
             "interpretation": interpretation,
             "muted": False,
             "sparkline": daily if len(daily) > 2 else None,
             **({"slope": {"prev_label": "пред. неделя", "prev": gt["impressions_prev7"],
                           "cur_label": "эта неделя", "cur": gt["impressions_last7"],
                           "label": "Показы Google за неделю"}} if full_weeks else {})})
    else:
        cards.append(_no_data_card("google", "Видимость в Google", "показов за неделю",
                                   g_block, "Google Search Console, весь сайт"))

    m_daily = _daily_windows(snap, "metrika") if rules.get("kpi_from_daily") else None
    if m_daily:
        w = _daily_card_common(m_daily["windows"]["visits_organic"])
        visits = int(w["value_num"])
        delta = int(w["delta_num"]) if w["delta_num"] is not None else None
        cards.append(
            {"key": "traffic", "label": "Органический трафик",
             "value": num(visits), "unit": "визитов за неделю",
             "delta": signed(delta) if delta is not None else None,
             "delta_dir": _dir(delta) if delta is not None else "flat",
             "relative": None,
             "relative_note": None,
             "period": w["period"],
             "source": "Яндекс.Метрика, весь сайт, дневные ряды",
             "confidence": ("данные не обновились с прошлого отчёта"
                            if "metrika" in stale_set else
                            "достаточная"
                            if visits >= snap["thresholds"]["low_visits"]
                            else "низкая, малые числа"),
             "interpretation": "Визиты из поиска: весь сайт, все поисковые системы.",
             "muted": False,
             "sparkline": m_daily["windows"]["visits_organic"].get("tail"),
             "sparkline_from": m_daily["windows"]["visits_organic"]["previous"]["from"]})
    elif m.get("available"):
        cards.append(
            {"key": "traffic", "label": "Органический трафик",
             "value": num(m.get("organic_visits")), "unit": "визитов",
             "delta": None, "delta_dir": "flat", "relative": None,
             "relative_note": "сравнения с предыдущим периодом нет: дневная серия не покрывает оба окна",
             "period": f"{ru_date(m['source']['current_period_start'])}–"
                       f"{ru_date(m['source']['current_period_end'])}",
             "source": "Яндекс.Метрика, весь сайт",
             "confidence": ("данные не обновились с прошлого отчёта"
                            if "metrika" in stale_set else
                            "достаточная"
                            if (m.get("organic_visits") or 0) >= snap["thresholds"]["low_visits"]
                            else "низкая, малые числа"),
             "interpretation": "Люди, пришедшие на сайт из поиска: весь сайт, "
                               "все поисковые системы.",
             "muted": False, "sparkline": None})
    else:
        cards.append(_no_data_card("traffic", "Органический трафик", "визитов",
                                   m, "Яндекс.Метрика, весь сайт"))

    events = m.get("organic_goal_events")
    gap = any(f.get("code") == "MEASUREMENT_GAP" for f in (dq.get("findings") or []))
    crm = snap.get("crm") or {}
    if crm.get("connected"):
        block = crm.get("block") or {}
        day = block.get("day") or ""
        # Показатель называется обращениями, а не целевыми событиями: это
        # заявки воронки, у каждой есть компания и состав запроса. Достоверность
        # честная — счёт заявок точен, но суточные числа однозначные, и на
        # одной заявке выводов о канале не делают.
        count = crm.get("qualified_leads") or 0
        cards.append({"key": "commercial", "label": "Обращения",
                      "value": num(count),
                      "unit": plural(count, "заявка за сутки", "заявки за сутки",
                                     "заявок за сутки"),
                      "delta": None, "delta_dir": "flat", "relative": None,
                      "relative_note": "", "period": ru_date(day) if day else "",
                      "source": "воронка сайта (Directus)",
                      "confidence": (f"выгрузка от {ru_date(block['data_date'])}, "
                                     "сутки покрыты не полностью"
                                     if block.get("stale")
                                     else "полный подсчёт, малые числа"),
                      # Разбор по каналам — в блоке «Заявки за сутки»; повторять
                      # его в карточке значит дважды сказать одно и то же в
                      # письме, где объём ограничен.
                      "interpretation": ("Заявки воронки сайта: компания, состав "
                                         "запроса и канал каждой — в блоке "
                                         "«Заявки за сутки»."),
                      "muted": False, "sparkline": None})
    elif not m.get("available"):
        # Целевые события считает Метрика; без неё коммерческий сигнал не измерен.
        cards.append(_no_data_card("commercial", "Коммерческий сигнал", "целевых событий",
                                   m, "Яндекс.Метрика, весь сайт"))
    else:
        # Сколько целей сайт шлёт мимо счётчика и не отстала ли выгрузка целей —
        # готовые выводы проверки качества (derived): она сверяет ключи и по
        # именам, и по идентификаторам событий в условиях целей. Пересчёт здесь
        # по одним именам давал бы другой ответ на тот же вопрос. Фолбэк — для
        # файлов data-quality старой схемы, без блока derived.
        derived = dq.get("derived") or {}
        declared = snap.get("declared_goals") or []
        goals_lagging = derived.get(
            "goals_lagging",
            any(f["code"] == "GOALS_CONFIGURED_AFTER_COLLECTION"
                for f in dq.get("findings", [])))
        goals_missing = derived.get("goals_missing")
        if goals_missing is None:
            configured = {g_["name"] for g_ in m.get("goals_configured") or []}
            goals_missing = len([n for n in declared if n not in configured])
        if goals_lagging:
            goals_missing = 0
        cards.append({
            "key": "commercial", "label": "Коммерческий сигнал",
            "value": num(events), "unit": "целевых событий",
            "delta": None, "delta_dir": "flat", "relative": None,
            "relative_note": "",
            "period": f"{ru_date(m['source']['current_period_start'])}–"
                      f"{ru_date(m['source']['current_period_end'])}",
            "source": "Яндекс.Метрика, весь сайт",
            "confidence": f"низкая: {counted(events, 'событие', 'события', 'событий')}",
            # Ноль по незаведённой цели — не «обращений не было», а «не
            # измерялось». Смешивать эти два утверждения нельзя: первое требует
            # объяснения и действий, второе — заведения целей в счётчике.
            #
            # Причина называется та, что действует сейчас. Прежняя формулировка
            # «вызовы вырезаны из сборки» описывала уже устранённый дефект: в
            # src/lib/analytics.ts стоит непустой фолбэк идентификатора, и код
            # достижим. Остаётся отсутствие целей в счётчике, и починка нужна
            # именно там — текст, называющий закрытую причину, отправлял работу
            # не по адресу.
            "interpretation": _commercial_interpretation(m, goals_lagging,
                                                         goals_missing),
            "muted": True, "sparkline": None,
            "sample_ctr": f"{sample.get('label')} {pct(sample.get('value'), 2)}"
                          if sample else None})
    return cards[:4]


def _commercial_interpretation(m: dict, goals_lagging: bool,
                               goals_missing: int) -> str:
    """Трактовка «Коммерческого сигнала» (вопрос руководителя 01.09.2026).

    Прежний текст выбирался по флагу MEASUREMENT_GAP любого рода и при
    goals_missing=0 печатал бессмыслицу «сайт отправляет 0 целей … счётчик
    их отбрасывает». Теперь: причина называется только когда она есть, а
    при наличии разбивки по целям показывается состав — без него сумма
    нечитаема (клик по телефону и автоцель «поиск по сайту» в одной цифре).
    """
    base = "Действия посетителей из поиска по целям Метрики"
    tail = "; это не подтверждённые обращения — с заявками воронки не сверяется"
    if goals_lagging:
        return (f"{base}. Конверсионные цели заведены в счётчике позже начала "
                f"окна и в этот замер не попали: первые сопоставимые числа — "
                f"со следующего сбора{tail}.")
    if goals_missing:
        return (f"{base}. Сайт отправляет "
                f"{counted(goals_missing, 'цель', 'цели', 'целей')}, которых "
                f"нет в счётчике, — по ним ноль означает отсутствие замера, "
                f"а не отсутствие обращений{tail}.")
    bd = m.get("goal_breakdown")
    if bd:
        top = "; ".join(f"{r['name'].lower().replace('автоцель: ', '')} — "
                        f"{num(r['events'])}" for r in bd[:3])
        more = len(bd) - 3
        return (f"{base}. Состав: {top}"
                + (f" и ещё {more}" if more > 0 else "") + tail + ".")
    return (f"{base}: сумма по всем целям вперемешку — от клика по телефону "
            f"до автоцели «поиск по сайту»; разбивки по целям в этом снимке "
            f"нет{tail}.")


def _dir(delta) -> str:
    if delta is None or delta == 0:
        return "flat"
    return "up" if delta > 0 else "down"


def source_stale(snap: dict, prev: dict | None, engine: str) -> bool:
    """Источник не обновился: последняя дата события та же, что в прошлом отчёте.

    Повторять вчерашнюю дельту как сегодняшнюю новость нельзя — это одно и то же
    наблюдение, поданное дважды.
    """
    if not prev:
        return False
    # «Не обновился» — состояние живого источника: данные есть, но их последняя
    # дата прежняя. Недоступный источник — другое состояние (ошибка или
    # отсутствие выгрузки); у него latest_event_date нет вовсе, и совпадение
    # None == None объявляло бы сбой «данными, которые не обновились».
    if not snap[engine].get("available") or not prev[engine].get("available"):
        return False
    return (snap[engine]["source"]["latest_event_date"]
            == prev[engine]["source"]["latest_event_date"])


def delta_text(d: int | None) -> str:
    """Нулевая дельта словами: числа «+0» в письме не бывает."""
    if d is None:
        return "нет данных"
    return "без изменений" if d == 0 else signed(d)


# Что означает движение строки сводной воронки. Текст короткий и не толкует
# причину: сигнал говорит, что именно изменилось, а не почему.
FUNNEL_MEANING = {
    "impressions": ("Страницы показывались чаще.", "Страницы показывались реже."),
    "clicks": ("Из выдачи переходили чаще.", "Из выдачи переходили реже."),
    "visits_organic": ("Визитов из поиска стало больше.", "Визитов из поиска стало меньше."),
    "sessions_organic": ("Сессий из поиска стало больше.", "Сессий из поиска стало меньше."),
    "goal_reaches_organic": ("Целевых действий на сайте стало больше.",
                             "Целевых действий на сайте стало меньше."),
    "key_events_organic": ("Ключевых действий на сайте стало больше.",
                           "Ключевых действий на сайте стало меньше."),
}


def funnel_movers(dq: dict) -> list[dict]:
    """Строки сводной воронки, отсортированные по величине изменения.

    Постоянных сигналов три, и 09.09.2026 все три оказались неотрицательными,
    а два падения того же дня — переходы из Google 1 → 0 и целевые события
    органики 45 → 26 — в письмо не попали: набор сигналов фиксирован, и место
    для них не предусмотрено. Воронка для этого подходит лучше всего: её
    строки уже посчитаны за одно окно с общим концом.

    Величина считается от базы не ниже LOW_BASE — иначе изменение с единицы до
    нуля обгоняло бы падение с сорока пяти до двадцати шести.
    """
    fn = dq.get("funnel") or {}
    if not fn.get("available"):
        return []
    out = []
    for row in fn.get("rows") or []:
        if not row.get("complete"):
            continue
        cur, prev, d = row.get("current"), row.get("previous"), row.get("delta")
        if cur is None or prev is None or not d:
            continue
        up, down = FUNNEL_MEANING.get(row["metric"], ("Значение выросло.", "Значение упало."))
        out.append({
            "tone": "positive" if d > 0 else "negative",
            "metric": row["label"],
            "current": num(cur), "previous": num(prev), "delta": delta_text(d),
            "confidence": ("низкая, база в десятки" if prev < LOW_BASE else "достаточная"),
            "meaning": up if d > 0 else down,
            "score": abs(d) / max(prev, LOW_BASE),
        })
    return sorted(out, key=lambda r: -r["score"])


def signals(snap: dict, prev: dict | None, dq: dict) -> list[dict]:
    """Три сигнала дня: положительный, нейтральный, отрицательный.

    Сигнал — это сравнение двух замеров, поэтому строится только по источникам,
    доступным в обоих снимках. Сбой источника сигналом дня не притворяется: о
    нём говорят карточка показателя, строка источников и блок здоровья данных.
    """
    if not prev:
        return []
    out = []
    if snap["google"].get("available") and prev["google"].get("available"):
        gt = snap["google"]["totals"]
        full_weeks = (gt.get("last7_days", 7) == 7 and gt.get("prev7_days", 7) == 7)
        stale = "google" in stale_sources(dq)
        # Тон и текст выводятся из знака изменения, а не задаются константой:
        # зашитое «positive / стали показываться чаще» выдавало бы падение за
        # рост. Сбой источника (unavailable) сюда не доходит — сигнал строится
        # только по источникам, доступным в обоих снимках.
        if stale:
            d, tone = None, "neutral"
            meaning = (f"Google не отдал новых данных: последний день выгрузки прежний — "
                       f"{ru_date(snap['google']['source']['latest_event_date'])}. "
                       "Значение повторяет вчерашнее и новым наблюдением не является.")
        elif not full_weeks:
            d, tone = None, "neutral"
            meaning = (f"Окна сравнения неполные ({gt.get('last7_days')} и "
                       f"{gt.get('prev7_days')} дн.) — изменение не публикуется.")
        else:
            d = gt["impressions_last7"] - gt["impressions_prev7"]
            tone = "positive" if d > 0 else ("negative" if d < 0 else "neutral")
            if gt["impressions_prev7"] == 0 and gt["impressions_last7"] > 0:
                # Переход с нулевой базы: не «рост на ∞%», а появление показов.
                meaning = "Появились показы в Google: на прошлой неделе их не было."
            elif d > 0:
                meaning = "Страницы сайта стали показываться чаще."
            elif d < 0:
                meaning = "Страницы сайта стали показываться реже."
            else:
                meaning = "Число показов за неделю не изменилось."
        out.append({
            "tone": tone,
            "metric": "Показы в Google за неделю",
            "current": num(gt["impressions_last7"]), "previous": num(gt["impressions_prev7"]),
            "delta": delta_text(d),
            "confidence": ("данные не обновились с прошлого отчёта" if stale
                           else "низкая, база в десятки показов"
                           if gt["impressions_prev7"] < LOW_BASE else "достаточная"),
            "meaning": meaning})

    if snap["yandex"].get("available") and prev["yandex"].get("available"):
        yt, yp = snap["yandex"]["totals"], prev["yandex"]["totals"]
        idx = snap["yandex"]["indexation"]["indexed_urls"]
        pidx = prev["yandex"]["indexation"]["indexed_urls"]
        # Индексация в одном из сборов может быть не измерена (None):
        # разность не считается, а текст не утверждает «не изменился».
        d_idx = (idx - pidx) if idx is not None and pidx is not None else None
        out.append({
            "tone": ("neutral" if not d_idx else
                     "positive" if d_idx > 0 else "negative"),
            "metric": "Страницы в поиске Яндекса",
            "current": num(idx), "previous": num(pidx), "delta": delta_text(d_idx),
            "confidence": "достаточная" if d_idx is not None else "нет данных для сравнения",
            "meaning": ("Число страниц в поиске в одном из сборов не измерено — "
                        "сравнение не публикуется." if d_idx is None else
                        "Объём проиндексированного сайта не изменился." if d_idx == 0 else
                        "В поиске стало больше страниц сайта." if d_idx > 0 else
                        "Часть страниц выпала из поиска Яндекса.")})

        td = yt["queries_position_le_10"] - yp["queries_position_le_10"]
        out.append({
            "tone": "negative" if td < 0 else ("positive" if td > 0 else "neutral"),
            "metric": "Запросы выборки на первой странице",
            "current": num(yt["queries_position_le_10"]),
            "previous": num(yp["queries_position_le_10"]), "delta": delta_text(td),
            "confidence": "достаточная",
            # Про «Яндекс в целом» этот сигнал ничего не доказывает — говорим
            # только о том, что измерено: составе выборки на первой странице.
            "meaning": ("Внутри выборки стало меньше запросов на первой странице."
                        if td < 0 else
                        "Внутри выборки прибавилось запросов на первой странице."
                        if td > 0 else
                        "Число запросов выборки на первой странице не изменилось.")})
    out = out[:3]

    # Постоянные показатели выше отвечают на вопрос «что с индексацией и
    # видимостью». Ниже добавляется то, что сильнее всего изменилось за сутки,
    # и обязательно — худшее изменение, если среди показанного падения нет.
    # Без этой добавки 09.09.2026 три неотрицательных постоянных показателя
    # вытеснили из письма оба падения дня.
    shown = {s["metric"] for s in out}
    movers = [m for m in funnel_movers(dq) if m["metric"] not in shown]
    extra = []
    if movers:
        extra.append(movers[0])
    if not any(s["tone"] == "negative" for s in out + extra):
        worst = next((m for m in movers if m["tone"] == "negative"
                      and m["metric"] not in {e["metric"] for e in extra}), None)
        if worst:
            extra.append(worst)
    for m in extra:
        out.append({k: v for k, v in m.items() if k != "score"})
    return out[:5]


def execution_board(actions_cfg: dict, date: str) -> list[dict]:
    """Только задачи, изменившие статус сегодня, заблокированные или срочные."""
    roles = actions_cfg["roles"]
    today = dt.date.fromisoformat(date)
    rows = []
    for a in actions_cfg["actions"]:
        due = dt.date.fromisoformat(a["due"]) if a.get("due") else None
        changed_today = a.get("status_changed_at") == date
        blocked = a["status"] in ("blocked", "blocked_by_policy")
        soon = due is not None and 0 <= (due - today).days <= 7
        if not (changed_today or blocked or soon):
            continue
        rows.append({
            "id": a["id"], "task": a["title"],
            "owner": roles[a["owner_role"]]["title"],
            "stage": STAGE_LABEL.get(a.get("stage", ""), a.get("stage", "")),
            "status": a["status_label"], "zone": a["zone"],
            "due": ru_date(a["due"]) if a.get("due") else "без срока",
            "artifact": a.get("artifact"), "artifact_url": _artifact_url(a),
            "pr": a.get("pr"), "ci": a.get("ci"), "qa": a.get("qa"),
            "deploy": a.get("deploy"), "rollback": a.get("rollback"),
        })
    return rows[:5]


def _artifact_url(a: dict) -> str:
    if a.get("pr"):
        return f"{REPO}/pull/{a['pr']}"
    return f"{BLOB}/{a['ticket']}"


def web_url(date: str) -> tuple[str, bool]:
    """Адрес полного отчёта.

    Порядок выбора:
      1. собственный домен, если задан — открывается кем угодно;
      2. Markdown-отчёт в репозитории — GitHub показывает его как страницу,
         и доступ к репозиторию у получателя уже есть;
      3. опубликованная страница как запасной вариант.

    Ссылка на HTML в репозитории не годится: GitHub отдаёт его исходным текстом,
    а не страницей. Опубликованная страница на claude.ai приватна и получателю
    письма не открывается — на этом ссылка и ломалась.
    """
    if PUBLIC_REPORT_BASE_URL:
        # Прямо на index.html, а не на каталог: на проде действует общесайтовый
        # URL-стандарт «301 со слэша на без-слэша», и адрес каталога зацикливается
        # между этим редиректом и nginx-овым «каталог → слэш». Явный файл не
        # редиректится вовсе.
        return f"{PUBLIC_REPORT_BASE_URL}/daily/{date}/index.html", True
    md = pathlib.Path(f"reports/seo/public/daily/{date}/README.md")
    if md.exists():
        return f"{REPO}/blob/{BRANCH}/reports/seo/public/daily/{date}/README.md", True
    if REPORT_URL_FILE.exists():
        url = REPORT_URL_FILE.read_text(encoding="utf-8").strip()
        if url:
            return url, True
    return f"{REPO}/tree/{BRANCH}/reports/seo/public/daily/{date}", False


def ads_headline(ads: dict, currency: str = "₽") -> str:
    """Шапка блока рекламы: день, неделя и «с запуска» — три разных числа.

    Прежде расход за всё время кампании печатался «из недельного лимита»;
    с восьмого дня фраза теряла смысл. Дата данных — из витрины: если
    выгрузка отстала, письмо говорит об этом, а не считает день пустым.
    """
    name = ads.get("campaign") or "Кампания Директа"
    line = (f"{name}, данные за {ru_date(ads['as_of'])}: за день "
            f"{ads['day_spend']:.0f} {currency}, за 7 дней "
            f"{ads['week']['spent']:.0f} из {num(ads['week']['limit'])} {currency} "
            f"недельного лимита, с запуска {ads['since_launch']['spent']:.0f} {currency} "
            f"({ads['since_launch']['days']} дн.).")
    if ads.get("stale"):
        line += (f" Выгрузка отстаёт: ожидались данные за "
                 f"{ru_date(ads['expected_as_of'])}.")
    return line


def decision_label(o: dict) -> str:
    """«Решение к дате», если срок назначен; иначе — без выдуманной даты."""
    return (f"решение к {ru_date(o['decision_date'])}" if o.get("decision_date")
            else "решение за вами, срок не назначен")


def assemble(snap, prev, dq, actions_cfg, site_check):
    date = snap["report_date"]
    health = dq["data_health"]
    # Техническое здоровье — тактический показатель, а не стратегический KPI:
    # он живёт пилюлей в статусбаре и компактной секцией, но не занимает место
    # среди четырёх показателей роста и не входит в SEO-оценку.
    tech = snap.get("technical") or {
        **passport.unavailable("no_file", source="замер PageSpeed"),
        "level": "unknown"}
    st = search_status(snap, prev)
    kpis = kpi_cards(snap, prev, dq)
    sig = signals(snap, prev, dq)
    dec = drivers_mod.build(snap, prev)
    exps = exp_mod.build(snap, date, site_check)
    board = execution_board(actions_cfg, date)
    opps = opp_mod.build(snap)
    red = [a for a in actions_cfg["actions"] if a["zone"] == "RED"
           and a.get("status") == "awaiting_decision"]
    # Вердикт эксперимента в контрольную дату (задание 30.08.2026): если движок
    # просит решение владельца, это поднимается в «От вас» наравне с RED.
    exp_decisions = [e for e in exps if e.get("control_date_today")
                     and (e.get("evaluation") or {}).get("requires_owner_decision")]
    url, public = web_url(date)

    google_block = next((b for b in dec["blocks"] if b["engine"] == "google"), None)
    driver_rows = (google_block or {}).get("pages", {}).get("all") or []

    demand_block = load_demand()
    growth_ideas = load_growth_ideas()
    mgmt = _management_actions(exps, opps, demand_block, growth_ideas)
    # Стол решений (замечание руководителя 31.08.2026): «решений не
    # требуется» в шапке при письме, полном предложений ниже, — дезинформация.
    # Когда срочного решения нет, шапка агрегирует предложения нижних блоков.
    desk: list[str] = []
    exp_props = sorted(
        (ev2.get("clean_window_eta") or e2["next_review"], e2["ticket"])
        for e2 in exps
        for ev2 in [e2.get("evaluation") or {}]
        if not ev2.get("requires_owner_decision")
        and (ev2.get("clean_window_eta") or e2.get("next_review")))
    if exp_props:
        when, tick = exp_props[0]
        desk.append(f"эксперименты: ближайшее предложение решения — "
                    f"{ru_date(when)} ({tick}); варианты и вероятный исход — "
                    f"в «Контроле эксперимента»")
    if opps.get("available") and opps.get("items"):
        cl = ", ".join(o["cluster"] for o in opps["items"][:3])
        desk.append(f"рост без бюджета: {counted(len(opps['items']), 'кластер', 'кластера', 'кластеров')} "
                    f"с показами без переходов ({cl}) ждут переписанных "
                    f"сниппетов — «Где ближе всего рост»")
    exp_dm = (demand_block or {}).get("expansion") or {}
    n_ready = len(exp_dm.get("items") or [])
    n_manual = len(exp_dm.get("manual_check") or [])
    if n_ready or n_manual:
        first = (exp_dm.get("items") or [{}])[0].get("brand", "")
        part = []
        if n_ready:
            part.append(f"{counted(n_ready, 'кандидат', 'кандидата', 'кандидатов')} "
                        f"к добавлению ({first})")
        if n_manual:
            part.append(f"{n_manual} — ручная проверка оплаты")
        desk.append("ассортимент: " + ", ".join(part) +
                    " — «Каких вендоров добавить»")
    if growth_ideas.get("fresh"):
        desk.append(f"продвижение: {growth_ideas['fresh'][0]['title']} — "
                    f"«Перспективные идеи»")

    # Тикет по идентификатору эксперимента: журнал решений ведётся по id,
    # а текст реестра ссылается на тикет (CONTENT-001).
    tickets = {x["id"]: x.get("ticket") for x in exp_mod.load_registry()}

    return {
        "date": date,
        "date_h": ru_date_full(date),
        "title": "BIZSoft Growth Intelligence",
        "subtitle": "Daily Search, Demand &amp; Experiment Control",
        "pills": [
            {"label": "ПОИСК", "state": st, "text": PILL_LABEL[st]},
            {"label": "ДАННЫЕ", "state": health["status"],
             "text": PILL_LABEL[health["status"]]},
            {"label": "ТЕХНИКА", "state": _tech_pill_state(tech),
             "text": _tech_pill_text(tech)},
            {"label": "ОТ ВАС",
             "state": "required" if (red or exp_decisions) else "none",
             "text": (PILL_LABEL["required"] if (red or exp_decisions) else
                      counted(len(desk), "предложение", "предложения", "предложений")
                      if desk else PILL_LABEL["none"])},
        ],
        "sources_line": _sources_line(snap),
        "user_action": (
            red[0]["title"] if red else
            _experiment_decision_line(exp_decisions[0]) if exp_decisions else
            "Срочных решений нет." if desk else
            "Решений от вас сегодня не требуется."),
        "user_action_required": bool(red or exp_decisions),
        "owner_desk": desk,
        "management_actions": mgmt,
        "kpis": kpis,
        "signals": sig,
        "drivers": dec,
        "driver_rows": driver_rows,
        "driver_summary": (drivers_mod.summarise(google_block) if google_block
                           else "Причина изменения пока не определена."),
        "driver_blocks": _driver_blocks(dec),
        "experiments": exps,
        # Журнал решений в блоках — чтобы инвариант S5 сверял с ним даты
        # вердиктов, названные в свободном тексте реестра.
        "owner_decisions": {
            eid: {"dates": [rec.get("date")], "verdict": rec.get("verdict"),
                  "owner_decision": rec.get("owner_decision"),
                  "ticket": tickets.get(eid)}
            for eid, rec in exp_mod.owner_decisions().items()
            if rec.get("date")},
        "board": board,
        "opportunities": opps,
        "vendor_radar": vendor_radar_mod.build(snap),
        "health": health,
        "technical": tech,
        "loop_health": load_loop_health(),
        "demand": demand_block,
        "leads": passport.normalize((snap.get("crm") or {}).get("block"),
                                    default_code="no_file",
                                    source="выгрузка заявок (ops-leads-collect)"),
        "crm": snap.get("crm") or {},
        "ads": ads_block.build(
            date, (snap.get("analytics") or {}).get("metrika", {})
            .get("direct_attribution")),
        "growth_ideas": growth_ideas,
        "measurement_summary": _measurement_summary(dq),
        "checkpoints": _checkpoints(exps, actions_cfg, date),
        "links": {"web": url, "web_public": public,
                  "tasks": f"{REPO}/tree/{BRANCH}/reports/seo/tasks"},
    }


def _driver_blocks(dec: dict) -> list[dict]:
    """Разложение по каждой поисковой системе: рост и снижение с конкретными адресами."""
    out = []
    for b in dec.get("blocks", []):
        part = b["pages"] if b["pages"].get("available") else b["queries"]
        kind = "страницам" if b["pages"].get("available") else "запросам"
        if not part.get("available"):
            out.append(passport.unavailable(
                "no_signal", detail="разложение по страницам и запросам",
                engine=b["engine_label"], window=b["window_label"],
                text="Причина изменения пока не определена: разложить его "
                     "на имеющихся данных нельзя.", rows=[]))
            continue
        rows = [{"entity": i["entity"], "delta": signed(i["delta"]),
                 "share": f"{round(i['share_of_total_delta'] * 100)}%",
                 "state": {"new": "новая", "lost": "выпала",
                           "changed": ""}.get(i["state"], ""),
                 "positive": i["delta"] > 0,
                 "position_delta": i.get("position_delta")}
                for i in part["all"]]
        ups = [r for r in rows if r["positive"]]
        downs = [r for r in rows if not r["positive"]]
        pieces = [f"Изменение {signed(part['total_delta'])} по {kind}."]
        if ups:
            pieces.append(f"Прибавили: {', '.join(r['entity'] for r in ups[:3])}.")
        if downs:
            pieces.append(f"Потеряли: {', '.join(r['entity'] for r in downs[:3])}.")
        if not ups:
            pieces.append("Растущих адресов выше порога значимости нет.")
        text = " ".join(pieces)
        out.append({"engine": b["engine_label"], "window": b["window_label"],
                    "available": True, "text": text, "rows": rows,
                    "counted": part["counted"]})
    return out


def _measurement_summary(dq: dict) -> str:
    """Что именно измеряет каждый источник — одной фразой, без повторов в других блоках."""
    rows = {r["metric"]: r for r in dq.get("measurement_map", [])}
    imp = rows.get("impressions", {})
    visits = rows.get("visits", {})
    # Вывод про «одно определение визита» уже сделан блоком здоровья данных —
    # здесь только состав каждого источника и корректные пары для сравнения.
    return (f"Показы и переходы Яндекса относятся к {imp.get('scope', 'выборке запросов')}, "
            f"визиты Метрики — к {visits.get('scope', 'всему сайту')} и ко всем поисковым "
            f"системам сразу. Сопоставлять корректно показы с переходами одной выборки, "
            f"а визиты Метрики — с сессиями GA4.")


def _sources_line(snap: dict) -> str:
    def one(label: str, block: dict) -> str:
        src = block.get("source") or {}
        if block.get("available"):
            return f"{label} по {ru_date(src.get('latest_event_date'))}"
        # «Сбой сбора» ≠ «не обновился»: здесь данных за день нет вовсе.
        return f"{label}: {STATUS_SHORT.get(src.get('status'), 'сбой сбора')}"

    md = snap.get("market_demand") or {}
    demand = (f"спрос {ru_date(md['source']['measured_at'])}" if md.get("available")
              else "спрос не измерен")
    return (f"{one('Яндекс', snap['yandex'])} · {one('Google', snap['google'])} · "
            f"{one('Метрика', snap['analytics']['metrika'])} · {demand}")


# Метки вердикт-движка экспериментов (задание руководителя 30.08.2026).
EXP_VERDICT_LABEL = {
    "CONFIRMED": "ПОДТВЕРЖДЁН", "REJECTED": "ОТВЕРГНУТ: ухудшение",
    "INCONCLUSIVE": "вывод невозможен", "INSUFFICIENT_DATA": "мало данных",
}
EXP_VERDICT_TONE = {
    "CONFIRMED": "positive", "REJECTED": "danger",
    "INCONCLUSIVE": "warning", "INSUFFICIENT_DATA": "muted",
}
EXP_REC_LABEL = {
    "EXPAND": "расширить", "REVERT": "откатить", "KEEP": "оставить",
    "EXTEND": "продлить наблюдение", "NEW_TEST": "новый тест",
}
EXP_CONF_LABEL = {"HIGH": "высокая", "MEDIUM": "средняя", "LOW": "низкая"}


def _experiment_decision_line(e: dict) -> str:
    ev = e["evaluation"]
    return (f"{e['ticket']}: вердикт {EXP_VERDICT_LABEL[ev['verdict']]}, "
            f"рекомендация — {EXP_REC_LABEL[ev['recommendation']]}. "
            f"Ответьте в чате: {ev['recommendation']} {e['ticket']} "
            f"(или KEEP/REVERT/EXPAND/EXTEND {e['ticket']}).")


def _pctf(v, digits=1) -> str:
    return "—" if v is None else f"{v * 100:.{digits}f}%"


# ── Контроль эксперимента: строки статуса ───────────────────────────────────
# Форма переделана по разбору руководителя 31.08.2026 («2 балла из 10»):
# каждая строка отвечает на один его вопрос — выкачен ли новый вариант,
# виден ли он в выдаче, сколько показов набрано из порога, как идёт старый
# против нового. «Нет данных» без причины и следующего шага не допускается.

def _exp_implementation_line(e: dict) -> str:
    live = e.get("pages_live_with_treatment")
    if live is None:
        return ("выкат не подтверждён: проверка живых страниц не выполнялась "
                "последние 3 дня")
    when = (f"проверка сайта {ru_date(e['site_check_date'])}"
            if e.get("site_check_date") else "проверено напрямую")
    return f"{num(live)} из {e['pages_total']} страниц отдают новый вариант ({when})"


def _exp_serp_line(e: dict) -> str:
    s = e.get("serp")
    line = e["search_snippet_refresh"]
    if s and s.get("pages"):
        posn = sorted(v["best_position"] for v in s["pages"].values())
        line += (f", позиции {posn[0]}–{posn[-1]}" if posn[0] != posn[-1]
                 else f", позиция {posn[0]}")
    # Переобход в Вебмастере работает (ops-yandex-recrawl, квота 150 URL в
    # сутки, журнал — issue #22); утверждать «не запрашивался» письмо не
    # может — машинного реестра заявок нет. Прежняя формулировка про
    # «ожидание токена» была ложной (разбор 03.09.2026).
    if s and s.get("pages_with_new_snippet"):
        line += " — Яндекс уже показывает новый вариант"
    elif s and s.get("pages_seen"):
        line += ("; если сниппет не обновится за неделю — переобход через "
                 "ops-yandex-recrawl")
    return line


def _exp_exposure_line(e: dict) -> str:
    imp = e.get("impressions_since_deploy")
    if imp is None:
        return "экспозиция не измерена: в выборке Вебмастера нет запросов кластера"
    thr = e["exposure_min_impressions"]
    state = ("порог пройден" if e.get("exposure_ok")
             else f"до порога ещё {num(thr - imp)}")
    if e.get("exposure_gate_adapted"):
        state += ", порог адаптирован под ёмкость кластера"
    # Считается по совпадающим запросам окон — тому набору, на котором
    # выносится вердикт (решение 04.09.2026); охват кластера целиком стоит
    # рядом, чтобы масштаб присутствия в выдаче не пропадал.
    scope = ""
    if e.get("exposure_basis") == "matched" and e.get("cluster_impressions"):
        scope = (f" по совпадающим запросам окон; кластер целиком — "
                 f"{counted(e['cluster_impressions'], 'показ', 'показа', 'показов')}")
    elif e.get("exposure_ok"):
        # Показы кластера набраны, но окно источника ещё захватывает период до
        # внедрения: сравнивать не с чем, и «порог пройден» без этой оговорки
        # читается как «данных достаточно для вывода» (проверка 04.09.2026).
        eta = (e.get("evaluation") or {}).get("clean_window_eta")
        if eta:
            scope = f", вывод ждёт чистого окна с {ru_date(eta)}"
    return (f"{counted(imp, 'показ', 'показа', 'показов')} из {num(thr)} "
            f"минимальных ({state}){scope} · "
            f"{counted(e.get('clicks_since_deploy'), 'клик', 'клика', 'кликов')} · "
            f"день {e['days_elapsed']} из {exp_mod.MIN_EXPOSURE_DAYS} минимальных")


def _exp_interim_line(e: dict) -> tuple[str, str | None]:
    """Строка «старый → новый» и оговорки к ней (может не быть).

    Формат следует метрике эксперимента: CTR — для сниппет-экспериментов,
    показы/день — для контентного роста, прогресс запуска — для новых страниц
    (у них «старого варианта» не существует).
    """
    kind = e.get("evaluation_kind", "ctr")
    ev = e.get("evaluation") or {}
    if kind == "launch":
        return (ev.get("summary_line")
                or "страницы новые — набор данных запуска ещё идёт", None)
    i = e.get("interim")
    if kind == "impressions_growth" and i:
        b, c = i["baseline"], i["current"]
        rel = ""
        if b.get("impressions"):
            growth = (c["impressions"] - b["impressions"]) / b["impressions"]
            rel = f" — предварительно {growth * 100:+.0f}%".replace("-", "−")
        line = (f"показы кластера {num(b['impressions'])} "
                f"(окно {ru_date(b['from'])}–{ru_date(b['to'])}, до внедрения) → "
                f"{num(c['impressions'])} (окно {ru_date(c['from'])}–{ru_date(c['to'])}, "
                f"{c['post_days']} из {c['window_days']} дней после){rel}")
        return line, ("; ".join(i.get("caveats") or []) or None)
    if not i:
        eta = ((e.get("evaluation") or {}).get("windows") or {}).get(
            "clean_experiment_eta")
        return ("сравнения нет: у источника нет выгрузки с окном "
                "после внедрения"
                + (f" (ожидается к {ru_date(eta)})" if eta else ""), None)
    b, c = i["baseline"], i["current"]
    mult = ""
    if i.get("relative_uplift") is not None:
        mult = (" — предварительно ×"
                + f"{1 + i['relative_uplift']:.1f}".replace(".", ","))
    posline = ""
    if b.get("avg_position") and c.get("avg_position"):
        posline = ("; позиция "
                   + f"{b['avg_position']:.1f} → {c['avg_position']:.1f}"
                   .replace(".", ","))
    line = (f"CTR {pct(b['ctr'], 2)} (окно {ru_date(b['from'])}–{ru_date(b['to'])}, "
            f"до внедрения) → {pct(c['ctr'], 2)} "
            f"(окно {ru_date(c['from'])}–{ru_date(c['to'])}, "
            f"{c['post_days']} из {c['window_days']} дней после){mult}{posline}")
    return line, ("; ".join(i.get("caveats") or []) or None)


def _management_actions(exps: list, opps: dict, demand_block: dict,
                        growth_ideas: dict) -> list[dict]:
    """Раздел «Управленческие воздействия» (поручение руководителя 01.09.2026).

    Каждое предложение «стола решений» разворачивается в постановку задачи:
    что сделать, почему (доказательство данными), шаги, критерий приёмки и
    что требуется от руководителя. Система без его команды ничего не меняет.
    """
    out = []

    # 1. Решения по экспериментам на ближайшей контрольной точке.
    props = sorted(
        ((ev.get("clean_window_eta") or e["next_review"], e)
         for e in exps for ev in [e.get("evaluation") or {}]
         if ev.get("clean_window_eta") or e.get("next_review")),
        key=lambda x: x[0])
    if props:
        when, e = props[0]
        interim = e.get("interim") or {}
        rel = interim.get("relative_uplift")
        prelim = (f"предварительно ×{1 + rel:.1f}".replace(".", ",")
                  if rel is not None else "предварительных данных мало")
        out.append({
            "task": f"Принять решение по эксперименту {e['ticket']}",
            "why": (f"контрольная точка {ru_date(when)}; {prelim} по CTR кластера "
                    f"({num(e.get('impressions_since_deploy'))} показов)"),
            "steps": ("прочитать панель вердикта в письме контрольной даты "
                      "(вердикт, уверенность, p-value, рекомендация с целевыми "
                      "страницами) и ответить в чате командой"),
            "acceptance": "решение зафиксировано в журнале решений экспериментов",
            "from_you": (f"одна команда {ru_date(when)}: EXPAND / KEEP / REVERT / "
                         f"EXTEND {e['ticket']}"),
        })

    # 2. Рост без бюджета: сниппеты под запросы с показами без переходов.
    items = (opps.get("items") or []) if opps.get("available") else []
    if items:
        # Slug сопоставляется и с дефисом, и с пробелом: запрос кластера
        # пишется «motion array», страница — /vendors/motion-array (02.09
        # письмо предложило переписать сниппет, уже переписанный в #273).
        exp_slugs = set()
        for e in exps:
            for pg in _registry_pages(e):
                slug = pg.rstrip("/").rsplit("/", 1)[-1]
                exp_slugs |= {slug, slug.replace("-", " ")}
        qlist = []
        held = []
        for o in items:
            cl = o["cluster"]
            if any(s in cl for s in exp_slugs):
                held.append(cl)
            else:
                qlist.append(cl)
        steps = ("для каждого запроса: переписать title целевой страницы под "
                 "запросную формулу (≤65 символов, штатный слой src/lib/seo.ts), "
                 "description ≤160 с оффером «счёт, договор, ЭДО», добавить "
                 "вопрос в FAQ-блок; изменения — отдельным PR с частотностью "
                 "по каждой правке, мерж ваш")
        why = "; ".join(f"«{o['cluster']}» — {o['evidence']}" for o in items[:3])
        note = (f"; запросы страниц активных экспериментов ({', '.join(held)}) — "
                f"после вердикта, чтобы не смазать оценку" if held else "")
        out.append({
            "task": (f"Переписать сниппеты под "
                     f"{counted(len(items), 'запрос', 'запроса', 'запросов')} "
                     f"с показами без переходов"),
            "why": why + note,
            "steps": steps,
            "acceptance": ("по каждому запросу появились переходы (CTR > 0) в "
                           "течение 14 дней при позиции не хуже исходной ±1"),
            "from_you": "команда «делай сниппеты» — правки уходят в PR",
        })

    # 3. Ассортимент: кандидаты в каталог (отклонённые руководителем скрыты).
    exp_dm = (demand_block or {}).get("expansion") or {}
    ready = exp_dm.get("items") or []
    manual = exp_dm.get("manual_check") or []
    if ready or manual:
        parts_why, parts_steps, parts_from = [], [], []
        if ready:
            first = ready[0]
            parts_why.append(
                f"{first.get('brand')} — {num(first.get('commercial_demand'))} "
                f"коммерческих запросов/мес, {first.get('recommendation_why', '')}")
            parts_steps.append("по готовым: завести карточку штатным конвейером "
                               "(Directus, иконки, микроразметка, sitemap)")
            parts_from.append("решение «заводим <бренд>»")
        if manual:
            parts_why.append(f"у {len(manual)} кандидатов "
                             f"({', '.join(manual)}) спрос подтверждён, "
                             "но платёжная схема не опознана автоматически")
            parts_steps.append("по ручным: проверить оплату на сайтах "
                               "кандидатов и вернуть вердикт в исследование")
            parts_from.append("решение по каждому после проверки")
        out.append({
            "task": "Расширение линейки: решить судьбу кандидатов с замеренным спросом",
            "why": "; ".join(parts_why),
            "steps": "; ".join(parts_steps) + "; параллельно исследование "
                     "продолжает замерять остальных кандидатов вне каталога",
            "acceptance": "каждый кандидат получает статус: заведён / отклонён "
                          "(отклонённые больше не предлагаются)",
            "from_you": "; ".join(parts_from),
        })

    # 4. Продвижение: свежие идеи копилки.
    for it in (growth_ideas.get("fresh") or [])[:1]:
        out.append({
            "task": it["title"],
            "why": it["why"],
            "steps": it.get("steps", "конкретные шаги — в карточке идеи в "
                                     "веб-отчёте"),
            "acceptance": it.get("acceptance", "идея переведена в задачу со "
                                               "сроком или отклонена"),
            "from_you": it.get("from_you", "решение: развиваем / отклоняем"),
        })
    return out


def _registry_pages(e: dict) -> list[str]:
    """Страницы эксперимента из собранного словаря письма (по реестру)."""
    reg = {x["id"]: x for x in exp_mod.load_registry()}
    return (reg.get(e.get("id")) or {}).get("pages") or []


def _exp_outlook_line(e: dict) -> str:
    """Когда «наблюдаем» сменится предложением решения, варианты и вероятный.

    Вопрос руководителя 31.08.2026: «вывод не понятен — когда наблюдение
    станет управленческим предложением, какие варианты возможны и какой
    оптимален». Дата берётся из движка (чистое окно/веха), вероятный
    вариант — из предварительных данных, финальный выбор всегда за
    владельцем на контрольной точке.
    """
    ev = e.get("evaluation") or {}
    kind = e.get("evaluation_kind", "ctr")
    if ev.get("requires_owner_decision"):
        return ""  # решение уже запрошено панелью вердикта — прогноз не нужен
    eta = ev.get("clean_window_eta")
    when = (f"{ru_date(eta)} (первое чистое окно данных)" if eta
            else (f"на контрольной точке {ru_date(e['next_review'])}"
                  if e.get("next_review") else "на ближайшей вехе"))
    if kind == "launch":
        crit = "KEEP — держать курс; EXTEND — разбор незашедших страниц"
        likely = ""
        m = (ev.get("metrics") or {}).get("launch") or {}
        if m.get("pages_in_search", 0) >= m.get("need_pages", 99):
            likely = " по текущему ходу вероятен KEEP;"
        return (f"Предложение решения — {when}: варианты {crit};{likely} "
                f"выбор за вами")
    if kind == "impressions_growth":
        variants = ("EXPAND — тираж приёма на следующие кластеры; "
                    "EXTEND — продлить; KEEP — оставить как есть")
    else:
        variants = ("EXPAND — тираж формулы на следующие карточки по спросу; "
                    "KEEP — оставить; REVERT — откат; EXTEND — продлить")
    likely = ""
    i = e.get("interim")
    if i and i.get("relative_uplift") is not None:
        rel = i["relative_uplift"]
        if rel >= 0.10:
            likely = (" по предварительным данным вероятен EXPAND"
                      " (если рост подтвердится статистически);")
        elif rel <= -0.10:
            likely = " по предварительным данным вероятен REVERT или KEEP;"
        else:
            likely = " по предварительным данным вероятен EXTEND;"
    return (f"Предложение решения — {when}: варианты {variants};{likely} "
            f"выбор за вами")


def _exp_status_html(e: dict) -> str:
    """Строки статуса ведущего эксперимента в письме."""
    interim_line, interim_caveat = _exp_interim_line(e)
    rows = [
        ("Внедрение", _exp_implementation_line(e), None),
        ("Выдача Яндекса", _exp_serp_line(e), None),
        ("Экспозиция", _exp_exposure_line(e), None),
        ("Старый → новый", interim_line, interim_caveat),
        ("Вывод", f"<b>{VERDICT_LABEL[e['verdict']]}</b> — {e['verdict_reason']}. "
                  f"Следующая проверка {ru_date(e['next_review'])}", None),
    ]
    outlook = _exp_outlook_line(e)
    if outlook:
        rows.append(("Что дальше", outlook, None))
    out = (f"<div data-meta=\"1\" style=\"font-size:12.5px;"
           f"color:{T['text_secondary']};padding-top:{SP['m']}px;\">"
           f"Запуск {ru_date(e['start'])} · день {e['days_elapsed']} · минимум "
           f"для вывода {e['minimum_exposure']}</div>")
    for label, text, caveat in rows:
        out += (f"<div style=\"font-size:14.5px;padding-top:{SP['s']}px;"
                f"line-height:1.55;\"><b>{label}:</b> {text}.</div>")
        if caveat:
            out += (f"<div data-meta=\"1\" style=\"font-size:12.5px;"
                    f"color:{T['text_secondary']};line-height:1.45;\">"
                    f"оговорки: {caveat}</div>")
    return out


def _exp_short_line(o: dict) -> str:
    """Строка «остальных» экспериментов: прогресс цифрами, а не только днями.

    Прогресс следует метрике эксперимента: порог 500 показов — гейт
    CTR-оценки; у контентного роста и запуска страниц свои критерии.
    """
    kind = o.get("evaluation_kind", "ctr")
    imp = o.get("impressions_since_deploy")
    review = (f"проверка {ru_date(o['next_review'])}" if o.get("next_review")
              else "вехи пройдены, вердикт не вынесен")
    if kind == "launch":
        m = ((o.get("evaluation") or {}).get("metrics") or {}).get("launch")
        if m:
            expo = (f"в выдаче {m['pages_in_search']} из {m['pages_total']} "
                    f"страниц · ~{num(m['weekly_impressions'])} показов/нед "
                    f"из {num(m['need_weekly'])}")
        else:
            expo = "набор данных запуска идёт"
        return f"день {o['days_elapsed']} · {expo} · {review}"
    if kind == "impressions_growth":
        expo = (f"{counted(imp, 'показ', 'показа', 'показов')} кластера"
                if imp is not None else "экспозиция не измерена")
        return f"день {o['days_elapsed']} · {expo} · рост к baseline — {review}"
    expo = (f"{num(imp)} из {num(o['exposure_min_impressions'])} показов"
            + (" (порог адаптирован)" if o.get("exposure_gate_adapted") else "")
            if imp is not None else "экспозиция не измерена")
    return (f"день {o['days_elapsed']} из {exp_mod.MIN_EXPOSURE_DAYS} · {expo} · "
            f"{review}")


def _verdict_line(e: dict) -> str:
    """Короткая строка вердикта для «остальных» экспериментов контрольной даты."""
    ev = e["evaluation"]
    tail = ""
    if ev["requires_owner_decision"]:
        tail = " Требуется ваше решение — подробности в веб-отчёте."
    return (f"вердикт <b>{EXP_VERDICT_LABEL[ev['verdict']]}</b> "
            f"({ev['verdict_reason']}); рекомендация — "
            f"{EXP_REC_LABEL[ev['recommendation']]}.{tail}")


def _verdict_panel(e: dict) -> str:
    """Панель вердикта в контрольную дату (задание 30.08.2026, §11).

    Показывается только когда сегодня контрольная точка эксперимента и
    оценка выполнена; в остальные дни блок эксперимента прежний.
    """
    if not (e.get("control_date_today") and e.get("evaluation")):
        return ""
    ev = e["evaluation"]
    colour = {"positive": T["positive"], "danger": T["danger"],
              "warning": T["warning"], "muted": T["muted"]}[
        EXP_VERDICT_TONE[ev["verdict"]]]
    lines = [f"<div style=\"font-size:15px;font-weight:700;color:{colour};\">"
             f"Вердикт контрольной точки: {EXP_VERDICT_LABEL[ev['verdict']]}"
             f" · уверенность {EXP_CONF_LABEL[ev['confidence']]}</div>",
             f"<div style=\"font-size:14.5px;padding-top:{SP['xs']}px;"
             f"line-height:1.55;\">{ev['verdict_reason']}.</div>"]
    if ev.get("summary_line"):
        # Не-CTR оценки (рост показов, запуск страниц) несут готовую сводку.
        lines.append(
            f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
            f"padding-top:{SP['s']}px;line-height:1.5;\">{ev['summary_line']}</div>")
    elif ev.get("windows"):
        w = ev["windows"]
        mm = ev["matched_metrics"]
        stat = ev["statistical_result"] or {}
        taint = " (окно захватывает день внедрения)" if w["experiment"].get("tainted") else ""
        pos_s = "—" if ev["position_delta"] is None else f"{ev['position_delta']:+.1f}"
        p_val = stat.get("p_value")
        p_s = "—" if p_val is None else f"{p_val:.3f}"
        lines.append(
            f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
            f"padding-top:{SP['s']}px;line-height:1.5;\">"
            f"До: {ru_date(w['baseline']['from'])}–{ru_date(w['baseline']['to'])}, "
            f"{num(mm['baseline']['impressions'])} показов, CTR "
            f"{_pctf(mm['baseline']['ctr'])} · После: "
            f"{ru_date(w['experiment']['from'])}–{ru_date(w['experiment']['to'])}{taint}, "
            f"{num(mm['experiment']['impressions'])} показов, CTR "
            f"{_pctf(mm['experiment']['ctr'])} · совпадающих запросов {mm['queries']} · "
            f"позиция {pos_s} · p={p_s}</div>")
        if ev.get("per_page"):
            # Перезапуск SEO-EXP-002: экспозиция каждой страницы видна отдельно,
            # чтобы сумма по кластеру не скрывала страницу без показов.
            parts = [f"{pp['page'].rsplit('/', 1)[-1]}: "
                     f"{num(pp['baseline']['impressions'])} → "
                     f"{num(pp['experiment']['impressions'])} показов, CTR "
                     f"{_pctf(pp['baseline']['ctr'])} → {_pctf(pp['experiment']['ctr'])}"
                     for pp in ev["per_page"]]
            lines.append(
                f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
                f"padding-top:2px;line-height:1.5;\">По страницам — {'; '.join(parts)}</div>")
    rec = [f"<div style=\"font-size:14.5px;padding-top:{SP['s']}px;line-height:1.55;\">"
           f"<b>Рекомендация: {EXP_REC_LABEL[ev['recommendation']]}.</b> "
           f"{ev['recommendation_detail']}.</div>"]
    if ev.get("recommended_targets"):
        head = ", ".join(ev["recommended_targets"][:3])
        more = len(ev["recommended_targets"]) - 3
        rec.append(f"<div data-meta=\"1\" style=\"font-size:12.5px;"
                   f"color:{T['text_secondary']};padding-top:2px;\">"
                   f"Первые страницы: {head}"
                   + (f" и ещё {more} — полный список в веб-отчёте" if more > 0 else "")
                   + "</div>")
    if ev["requires_owner_decision"]:
        rec.append(f"<div style=\"font-size:14.5px;padding-top:{SP['s']}px;"
                   f"font-weight:700;color:{T['brand']};\">"
                   f"ТРЕБУЕТСЯ ВАШЕ РЕШЕНИЕ — ответьте в чате: "
                   f"{ev['recommendation']} {e['ticket']} "
                   f"(или KEEP/REVERT/EXPAND/EXTEND {e['ticket']}).</div>")
    return (f"<div style=\"margin-top:{SP['m']}px;padding:{SP['m']}px;"
            f"background:{T['background']};border-left:3px solid {colour};"
            f"border-radius:0 10px 10px 0;\">{''.join(lines + rec)}</div>")


def _review_subject(e: dict) -> str:
    """Что именно замеряет ближайшая проверка — по метрике эксперимента."""
    kind = e.get("evaluation_kind", "ctr")
    if kind == "impressions_growth":
        return "замер роста показов кластера и позиции статьи"
    if kind == "launch":
        return "замер индексации и показов новых страниц"
    return "замер кликабельности изменённых страниц"


def _checkpoints(exps, actions_cfg, date: str = "") -> list[dict]:
    out = []
    for e in exps:
        # next_review = None: все вехи эксперимента позади — он ждёт вердикта
        # (это видно в «Контроле эксперимента»), а «следующей проверки» у него
        # нет. Прошедшие даты сюда не попадают: их отсекает next_review_for
        # (вопрос руководителя 30.08 — письмо показывало 26.08 как будущее).
        # Контрольная дата сегодня: проверка уже проведена, и её результат —
        # в блоке «Контроль эксперимента» этого же письма. Показывать её как
        # предстоящую нельзя (вопрос руководителя 02.09.2026), но и молчать о
        # ней не нужно: строка называет вердикт и уводит к разбору.
        if not e.get("next_review"):
            continue
        out.append({"date": ru_date(e["next_review"]),
                    "what": f"{e['ticket']}: {_review_subject(e)}"})
    for a in actions_cfg["actions"]:
        # Срок сегодня или в прошлом — не «следующая» проверка: письмо 03.09
        # печатало задачу со сроком «сегодня» рядом с «проверки проведены
        # сегодня» (аудит 03.09.2026).
        if a.get("due") and a["status"] in ("in_progress", "blocked") \
                and (not date or a["due"] > date):
            out.append({"date": ru_date(a["due"]), "what": f"{a['id']}: {a['title']}"})
    # Дедупликация по (дата, идентификатор): у задачи журнала и эксперимента
    # совпадает тикет (SEO-EXP-002), и один и тот же контроль печатался
    # дважды разными формулировками.
    seen, uniq = set(), []
    for c in out:
        k = (c["date"], c["what"].split(":", 1)[0].strip())
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    # По возрастанию даты: ближайшее сверху. Дата в формате ДД.ММ, поэтому
    # сортируется по (месяц, день).
    uniq.sort(key=lambda c: tuple(reversed(c["date"].split("."))))
    return uniq[:3]


# ── Рендер письма ───────────────────────────────────────────────────────────

# Пилюля технического состояния. Состояния переиспользуют существующую
# палитру статусбара: verified — зелёное, limited — жёлтое, degraded — красное.
TECH_PILL_STATE = {"green": "verified", "yellow": "limited", "red": "degraded",
                   "unknown": "unknown"}


def _tech_pill_state(tech: dict) -> str:
    return TECH_PILL_STATE.get(tech.get("level", "unknown"), "unknown")


def _tech_pill_text(tech: dict) -> str:
    """«GREEN · 93» — статус и балл мобильной скорости, без десятых долей."""
    if not tech.get("available"):
        return "нет данных"
    label = {"green": "GREEN", "yellow": "YELLOW", "red": "RED"}[tech["level"]]
    perf = tech.get("mobile_performance")
    return f"{label} · {perf}" if perf is not None else label


def _pill(p: dict) -> str:
    c = PILL_COLOUR[p["state"]]
    return (f"<span data-meta=\"1\" style=\"display:inline-block;padding:3px 10px;margin:0 6px 6px 0;"
            f"border:1px solid {c};border-radius:999px;font-size:12.5px;"
            f"color:{c};white-space:nowrap;\">{p['label']}: {p['text']}</span>")


PILL_STATE = {
    "positive": "good", "mixed": "warn", "negative": "crit", "stable": "good",
    "verified": "good", "limited": "warn", "degraded": "crit", "none": "neutral",
    "required": "crit", "unknown": "neutral",
}


def _pill_row(p: dict) -> dict:
    """Пилюля статуса → строка светофора KPI-kit (глиф + цвет состояния)."""
    return {"state": PILL_STATE.get(p["state"], "neutral"), "name": p["label"],
            "comment": p["text"]}


def _kpi_cell(k: dict, charts: dict, cid_mode: bool) -> str:
    """Плитка показателя — компонент KPI-kit для письма.

    delta_dir отсутствует, когда дельта не публикуется: окна разной длины или
    выборка пересобрана. Это не «нет изменения», а «сравнивать нечего с чем».
    График дня (тренд по дням или «было → стало») вкладывается в плитку того
    показателя, по которому он построен.
    """
    delta = k["delta"] or ""
    if k.get("relative"):
        delta = f"{delta} {k['relative']}".strip()
    trend = charts.get("kpi-trend") or {}
    extra = ""
    if trend and trend.get("kpi_key") == k.get("key"):
        extra = (f"<div style=\"padding-top:{SP['s']}px;\">"
                 f"{_img(charts, 'kpi-trend', cid_mode)}</div>")
    return kit.email_tile(
        k["label"], k["value"], k["unit"], delta or None, k.get("delta_dir"),
        note=k["interpretation"],
        meta=f"{k['period']} · {k['source']} · достоверность: {k['confidence']}",
        muted=bool(k["muted"]), extra=extra)


def _tech_metric_line(tech: dict) -> str:
    """LCP и CLS одной строкой: «в норме» или конкретное отклонение."""
    parts = []
    parts.append("LCP: в норме" if tech.get("lcp_ok") else "LCP: выше нормы")
    parts.append("CLS: в норме" if tech.get("cls_ok") else "CLS: выше нормы")
    return " · ".join(parts)


def _technical_html(tech: dict) -> str:
    """Компактный блок скорости: 5–7 строк в зелёном состоянии.

    Подробности печатаются только при просадке и не более чем по трём
    страницам: длинный аудит Lighthouse в ежедневном письме не нужен, для
    него есть отдельный ручной прогон ops-pagespeed.
    """
    if not tech.get("available"):
        tail = technical._no_data_tail(
            tech, "Последний удачный замер: {}.".format(
                ru_date(tech.get("last_success") or "")),
            "Последняя попытка {} не удалась.".format(
                ru_date(tech.get("last_attempt") or "")),
            "Замеров ещё не было.")
        return (f"<div style=\"font-size:15px;line-height:1.55;\">"
                f"<b>Данные недоступны.</b> {tail} "
                f"На остальные показатели отчёта это не влияет: скорость "
                f"измеряется отдельным источником.</div>")

    label = {"green": "GREEN", "yellow": "YELLOW", "red": "RED"}[tech["level"]]
    colour = {"green": T["positive"], "yellow": T["warning"],
              "red": T["danger"]}[tech["level"]]
    head = (f"<div style=\"font-size:15.5px;font-weight:700;color:{colour};\">"
            f"{label} · мобильная скорость {tech.get('mobile_performance')}</div>")

    pages = ", ".join(f"{p['page_type'].lower()} {p['performance']}"
                      for p in tech.get("pages", []) if p.get("performance") is not None)
    body = (f"<div style=\"font-size:15px;padding-top:{SP['xs']}px;line-height:1.55;\">"
            f"Проверено страниц: {tech.get('pages_checked')} — {pages}.</div>"
            f"<div style=\"font-size:14.5px;padding-top:{SP['xs']}px;"
            f"color:{T['text_secondary']};\">{_tech_metric_line(tech)}</div>")

    if not tech.get("regressions"):
        body += (f"<div style=\"font-size:14.5px;padding-top:{SP['xs']}px;"
                 f"color:{T['text_secondary']};\">"
                 f"Значимых изменений к прошлому замеру нет.</div>")
    else:
        for r in tech["regressions"]:
            body += (f"<div style=\"font-size:15px;padding-top:{SP['s']}px;"
                     f"line-height:1.55;\"><b>{r['page_type']}</b> "
                     f"({r['path']}): {_tech_issue_text(r['issues'])}. "
                     f"Вероятная причина: {r['cause']}. {r['priority']}.</div>")

    full = tech.get("last_full")
    if full:
        # Служебная подпись о последней расширенной проверке — метаданные:
        # без data-meta браузерная проверка uxlint (rendered_font_sizes)
        # считает 13,5 px основным текстом и блокирует выпуск (05.09.2026,
        # первая суббота с расширенным замером).
        body += (f"<div data-meta=\"1\" style=\"font-size:13.5px;padding-top:{SP['s']}px;"
                 f"color:{T['text_secondary']};\">"
                 f"Последняя расширенная проверка {ru_date(full['date'])}: "
                 f"{full['urls']} адресов, зелёных {full['green']}, "
                 f"жёлтых {full['yellow']}, красных {full['red']}.</div>")
    return head + body


def _ru_num(value: float, digits: int = 1) -> str:
    """Дробное по-русски: запятой, как остальные числа отчёта."""
    return f"{value:.{digits}f}".replace(".", ",")


def _tech_issue_text(issues: list[dict]) -> str:
    """Что именно ухудшилось — числами, без интерпретаций."""
    out = []
    for i in issues:
        if i["kind"] == "performance":
            out.append(f"скорость {i['was']} → {i['now']} ({i['delta']})")
        elif i["kind"] == "lcp":
            out.append(f"LCP {_ru_num(i['was'] / 1000)} с → "
                       f"{_ru_num(i['now'] / 1000)} с (+{i['delta_pct']} %)")
        elif i["kind"] == "cls":
            out.append(f"CLS {_ru_num(i['was'], 2)} → {_ru_num(i['now'], 2)}")
    return "; ".join(out)


def _section(title: str, body: str, note: str = "") -> str:
    n = (f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
         f"padding-top:2px;line-height:1.45;\">{note}</div>" if note else "")
    return (f"<tr><td style=\"padding:{SP['xl']}px 0 0 0;\">"
            f"<div style=\"font-size:17.5px;font-weight:700;color:{T['text_primary']};"
            f"line-height:1.35;\">{title}</div>{n}"
            f"<div style=\"padding-top:{SP['m']}px;\">{body}</div></td></tr>")


def _img(charts: dict, name: str, cid_mode: bool) -> str:
    c = charts.get(name)
    if not c:
        return ""
    src = f"cid:{c['cid']}" if cid_mode else f"charts/{c['file']}"
    return (f"<img src=\"{src}\" width=\"{c['display_width']}\" alt=\"{c['alt']}\" "
            f"style=\"display:block;width:100%;max-width:{c['display_width']}px;"
            f"height:auto;max-height:{c['max_height']}px;\">"
            f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
            f"padding-top:{SP['xs']}px;line-height:1.45;\">{c['fallback']}</div>")


def html_email(b: dict, charts: dict, cid_mode: bool) -> str:
    rows = []

    # A. Header + B. Status bar — тёмный мастхед KPI-kit и светофор состояний
    # вместо пилюль: те же четыре статуса (ПОИСК, ДАННЫЕ, ТЕХНИКА, ОТ ВАС),
    # но с глифом и цветом состояния, читаемыми без картинок.
    brand = b["title"].replace("BIZSoft", f"BIZ<span style=\"color:{T['brand']};\">Soft</span>", 1)
    rows.append(kit.email_masthead(
        brand, f"{b['subtitle']} · {b['date_h']}<br>{b['sources_line']}"))
    rows.append(
        f"<tr><td style=\"padding:{SP['m']}px 0 0 0;\">"
        + kit.email_status_rows([_pill_row(p) for p in b["pills"]])
        + "</td></tr>")

    # C. От вас
    if b["user_action_required"]:
        rows.append(
            f"<tr><td style=\"padding-top:{SP['l']}px;\">"
            f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
            f"style=\"background:#FFF4ED;border-left:4px solid {T['brand']};"
            f"border-radius:0 12px 12px 0;\"><tr><td style=\"padding:{SP['l']}px;\">"
            f"<div style=\"font-size:15.5px;font-weight:700;color:{T['text_primary']};\">"
            f"Требуется ваше решение</div>"
            f"<div style=\"font-size:15px;padding-top:{SP['xs']}px;line-height:1.55;\">"
            f"{b['user_action']}</div></td></tr></table></td></tr>")
    elif b.get("owner_desk"):
        # Срочного решения нет, но предложения из нижних блоков — на столе:
        # шапка их агрегирует, а не пишет «не требуется» (замечание 31.08).
        desk_rows = "".join(
            f"<div style=\"font-size:14.5px;padding-top:{SP['xs']}px;"
            f"line-height:1.55;\">• {d}</div>" for d in b["owner_desk"])
        rows.append(
            f"<tr><td style=\"padding-top:{SP['l']}px;\">"
            f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
            f"style=\"background:{T['surface']};border:1px solid {T['border']};"
            f"border-radius:12px;\"><tr><td style=\"padding:{SP['l']}px;\">"
            f"<div style=\"font-size:15px;font-weight:700;\">От вас: срочного нет, "
            f"на вашем столе {counted(len(b['owner_desk']), 'предложение', 'предложения', 'предложений')}</div>"
            f"{desk_rows}"
            f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
            f"padding-top:{SP['s']}px;\">Развёрнутые постановки задач — в разделе "
            f"«Управленческие воздействия» внизу письма; решения принимаете вы, "
            f"система без команды ничего не меняет.</div>"
            f"</td></tr></table></td></tr>")
    else:
        rows.append(
            f"<tr><td style=\"padding-top:{SP['l']}px;font-size:15px;"
            f"color:{T['text_primary']};line-height:1.55;\">"
            f"<b>От вас:</b> {b['user_action']} Остальное система ведёт сама.</td></tr>")

    # D. KPI — fluid hybrid: две колонки на десктопе, одна на узком экране.
    # Ширина карточки задана max-width, а не процентом: Gmail вырезает <style>
    # с media queries, поэтому вёрстка не должна на них опираться.
    cells = []
    for i, k in enumerate(b["kpis"]):
        mso_open = ("<!--[if mso]><table role=\"presentation\" width=\"100%\"><tr>"
                    "<td width=\"50%\" valign=\"top\"><![endif]-->" if i == 0 else
                    "<!--[if mso]></td><td width=\"50%\" valign=\"top\"><![endif]-->"
                    if i % 2 == 1 else
                    "<!--[if mso]></td></tr><tr><td width=\"50%\" valign=\"top\">"
                    "<![endif]-->")
        cells.append(
            f"{mso_open}"
            f"<div class=\"kpi\" style=\"display:inline-block;width:100%;"
            f"max-width:290px;vertical-align:top;padding:{SP['s']}px;font-size:15px;\">"
            f"{_kpi_cell(k, charts, cid_mode)}</div>")
    cells.append("<!--[if mso]></td></tr></table><![endif]-->")
    rows.append(_section(
        "Показатели",
        f"<div data-meta=\"1\" style=\"font-size:0;margin:-{SP['s']}px;\">"
        f"{''.join(cells)}</div>"))
    rows.append(FIRST_SCREEN_MARKER)

    # E. Сигналы дня
    if b["signals"]:
        tone_colour = {"positive": T["positive"], "neutral": T["muted"],
                       "negative": T["danger"]}
        sig = "".join(
            f"<div style=\"padding:{SP['m']}px 0;border-bottom:1px solid {T['border']};\">"
            f"<span style=\"display:inline-block;width:8px;height:8px;border-radius:50%;"
            f"background:{tone_colour[s['tone']]};margin-right:{SP['s']}px;\"></span>"
            f"<span style=\"font-size:15.5px;font-weight:600;\">{s['metric']}</span>"
            f"<span style=\"font-size:15px;color:{T['text_secondary']};\"> "
            f"{s['previous']} → {s['current']} ({s['delta']})</span>"
            f"<div style=\"font-size:15px;padding-top:{SP['xs']}px;line-height:1.55;\">"
            f"{s['meaning']}</div>"
            f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
            f"padding-top:2px;\">достоверность: {s['confidence']}</div></div>"
            for s in b["signals"])
        rows.append(_section("Сигналы дня", sig))

    # E-а. Заявки за сутки и путь к запросу.
    #
    # Стоит выше рекламы намеренно: реклама — это расход и гипотеза, заявка —
    # результат. Канал каждой заявки называется с основанием («Метрика» или
    # «метка браузера»): по метке выдача поисковика неотличима от его сервисов,
    # и утверждать «пришли из органики» на таком основании нельзя.
    lb = b.get("leads") or {}
    if lb.get("available"):
        if lb["count"]:
            lead_rows = "".join(
                f"<div style=\"padding:{SP['m']}px 0;border-bottom:1px solid {T['border']};\">"
                f"<div style=\"font-size:15.5px;font-weight:600;line-height:1.45;\">"
                f"{it['time']} · {it['company']}</div>"
                f"<div style=\"font-size:14.5px;padding-top:2px;line-height:1.55;\">"
                f"{it['request']} · {it['form']}</div>"
                f"<div style=\"font-size:14.5px;padding-top:2px;line-height:1.55;\">"
                f"<b>Канал:</b> {it['channel']}</div>"
                f"<div style=\"font-size:14.5px;padding-top:2px;line-height:1.55;\">"
                f"<b>Путь:</b> {it['journey']}</div>"
                f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
                f"padding-top:2px;\">основание: {it['channel_basis']}"
                + (f" · {it['channel_evidence']}" if it['channel_evidence'] else "")
                + "</div></div>"
                for it in lb["items"])
            more = (f"<div style=\"font-size:14.5px;padding-top:{SP['s']}px;\">"
                    f"Ещё {counted(lb['more'], 'заявка', 'заявки', 'заявок')} за сутки — "
                    f"в воронке сайта.</div>" if lb["more"] else "")
        else:
            lead_rows, more = "", ""
        rows.append(_section(
            "Заявки за сутки",
            f"<div style=\"font-size:15px;line-height:1.6;\">"
            f"{leads_mod.summary_line(lb)}</div>"
            f"<div style=\"padding-top:{SP['s']}px;\">{lead_rows}</div>{more}",
            lb.get("note", "")))

    # E-б. Реклама (Директ) — Direct Control Report, этап A. Маркер всегда
    # со словом-причиной; направления без 10 кликов — серые «мало данных».
    ads = b.get("ads") or {}
    if ads.get("available"):
        tone_c = {"grey": T["muted"], "ok": T["positive"],
                  "warn": T["warning"], "bad": T["danger"]}
        ad_rows = "".join(
            f"<div style=\"padding:{SP['s']}px 0;border-bottom:1px solid {T['border']};"
            f"font-size:14.5px;line-height:1.5;\">"
            f"<span style=\"display:inline-block;width:8px;height:8px;border-radius:50%;"
            f"background:{tone_c[r['verdict']['tone']]};margin-right:{SP['s']}px;\"></span>"
            f"<b>{r['label']}</b> — {r['spend_day']:.0f} ₽, "
            f"{counted(r['clicks_day'], 'клик', 'клика', 'кликов')}"
            + (f", CPC {r['cpc']:.0f} ₽" if r["cpc"] else "")
            + (f", заявок {r['leads']}" + (f" · CPA {r['cpa']:.0f} ₽" if r.get("cpa") else "")
               + (f", контактов {r['contacts']}" if r.get("contacts") else "")
               if r.get("leads") is not None else "")
            + f" · <span style=\"color:{tone_c[r['verdict']['tone']]};\">"
              f"{r['verdict']['label']}</span></div>"
            for r in ads["rows"])
        dec_html = "".join(
            f"<div style=\"font-size:14.5px;padding-top:{SP['s']}px;line-height:1.55;"
            f"color:{tone_c[d['tone']]};\"><b>Требует решения:</b> "
            f"<span style=\"color:{T['text_primary']};\">{d['text']}</span></div>"
            for d in ads["decisions"][:3])
        rows.append(_section(
            "Реклама — Яндекс.Директ",
            f"<div style=\"font-size:15px;line-height:1.6;\">"
            f"{ads_headline(ads)}</div>"
            f"<div style=\"padding-top:{SP['s']}px;\">{ad_rows}</div>{dec_html}",
            ads.get("note", "")))

    # F. Драйверы и детракторы
    parts = []
    for db in b["driver_blocks"]:
        rows_html = "".join(
            f"<div style=\"padding:{SP['xs']}px 0;font-size:14.5px;line-height:1.5;\">"
            f"<span style=\"color:{T['positive'] if r['positive'] else T['danger']};"
            f"font-weight:600;\">{r['delta']}</span> "
            f"<span>{r['entity']}</span> "
            f"<span data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};\">"
            f"{r['share']} изменения{' · ' + r['state'] if r['state'] else ''}</span></div>"
            for r in db["rows"][:5])
        chart = _img(charts, "drivers", cid_mode) if db["engine"] == "Google" else ""
        parts.append(
            f"<div style=\"padding-bottom:{SP['l']}px;\">"
            f"<div style=\"font-size:15px;line-height:1.55;\">"
            f"<b>{db['engine']}.</b> {db['text']}</div>"
            f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
            f"padding-top:2px;\">{db['window']}</div>"
            f"<div style=\"padding-top:{SP['s']}px;\">{rows_html}</div>"
            f"<div style=\"padding-top:{SP['s']}px;\">{chart}</div></div>")
    if parts:
        rows.append(_section("Что дало изменение", "".join(parts)))
    else:
        rows.append(_section(
            "Что дало изменение",
            f"<div style=\"font-size:15px;line-height:1.55;\">"
            f"Причина изменения пока не определена.</div>"))

    # G. Контроль экспериментов
    #
    # Подробно раскрывается один — самый продвинутый по накопленной выдержке.
    # Остальные идут строкой: три полных блока с графиком на каждый раздували
    # письмо, вставляли пять изображений вместо трёх и шесть раз повторяли одну
    # и ту же оговорку «рано для вывода». Читателю от этого не яснее.
    # В контрольную дату вперёд выходит эксперимент с вердиктом (задание
    # 30.08.2026); в обычные дни — самый выдержанный, как прежде.
    exps_sorted = sorted(b["experiments"],
                         key=lambda e: (not e.get("control_date_today"),
                                        -e.get("days_elapsed", 0)))
    if exps_sorted:
        e = exps_sorted[0]
        others = exps_sorted[1:]
        extra = ""
        if others:
            lines = "".join(
                f"<div style=\"font-size:14.5px;padding-top:{SP['xs']}px;line-height:1.5;\">"
                f"<b>{o['ticket']}</b> — "
                + (_verdict_line(o) if o.get("control_date_today")
                   and o.get("evaluation") else _exp_short_line(o))
                + "</div>"
                for o in others)
            extra = (f"<div style=\"padding-top:{SP['m']}px;border-top:1px solid {T['border']};"
                     f"margin-top:{SP['m']}px;\">"
                     f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};\">"
                     f"Ещё в работе, выводы по расписанию</div>{lines}</div>")
        extra = _verdict_panel(e) + extra
        rows.append(_section(
            "Контроль эксперимента",
            f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
            f"style=\"background:{T['surface']};border:1px solid {T['border']};"
            f"border-radius:12px;\"><tr><td style=\"padding:{SP['l']}px;\">"
            f"<div style=\"font-size:15.5px;font-weight:600;\">{e['ticket']} · "
            f"заголовки и блок вопросов на {e['pages_total']} карточках</div>"
            f"<div style=\"font-size:14.5px;padding-top:{SP['s']}px;line-height:1.55;\">"
            f"<b>Проверяем:</b> {e['hypothesis_plain']}</div>"
            + _exp_status_html(e) +
            f"<div style=\"padding-top:{SP['m']}px;\">{_img(charts, 'experiment', cid_mode)}</div>"
            f"{extra}</td></tr></table>"))

    # H. Автономное исполнение — фиксированный layout: содержимое переносится,
    # а не распирает письмо. Статус и результат уходят в подпись под задачей,
    # иначе шесть колонок не помещаются в 375 px.
    if b["board"]:
        head = ("Задача", "Кто", "Стадия", "Срок")
        th = "".join(f"<th align=\"left\" data-meta=\"1\" style=\"font-size:12.5px;font-weight:600;"
                     f"color:{T['text_secondary']};padding:0 {SP['s']}px {SP['s']}px 0;\">"
                     f"{h}</th>" for h in head)
        trs = ""
        for r in b["board"]:
            meta = f"{r['status']} · {r.get('artifact') or 'без артефакта'}"
            if r.get("pr"):
                meta += (f" · PR {r['pr']} · проверки {r['ci']} · тестирование {r['qa']}"
                         f" · {r['deploy']} · откат {r['rollback']}")
            cell = (f"padding:{SP['s']}px {SP['s']}px {SP['s']}px 0;"
                    f"border-top:1px solid {T['border']};")
            trs += (f"<tr><td style=\"{cell}font-size:14.5px;line-height:1.5;"
                    f"word-break:break-word;\">"
                    f"<a href=\"{r['artifact_url']}\" style=\"color:{T['text_primary']};"
                    f"text-decoration:none;\">{r['task']}</a>"
                    f"<div data-meta=\"1\" style=\"font-size:12.5px;"
                    f"color:{T['text_secondary']};padding-top:2px;line-height:1.45;\">"
                    f"{meta}</div></td>"
                    f"<td style=\"{cell}font-size:14px;color:{T['text_secondary']};"
                    f"word-break:break-word;\">{r['owner']}</td>"
                    f"<td style=\"{cell}font-size:14px;word-break:break-word;\">"
                    f"{r['stage']}</td>"
                    f"<td style=\"padding:{SP['s']}px 0;border-top:1px solid {T['border']};"
                    f"font-size:14px;color:{T['text_secondary']};\">{r['due']}</td></tr>")
        rows.append(_section(
            "Система уже делает",
            f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
            f"style=\"width:100%;table-layout:fixed;\">"
            f"<colgroup><col style=\"width:46%\"><col style=\"width:19%\">"
            f"<col style=\"width:19%\"><col style=\"width:16%\"></colgroup>"
            f"<tr>{th}</tr>{trs}</table>",
            "Показаны задачи со сменой статуса, блокировкой или сроком в ближайшую неделю"))

    # I. Радар возможностей
    if b["opportunities"]["available"]:
        items = "".join(
            f"<div style=\"padding:{SP['m']}px 0;border-bottom:1px solid {T['border']};\">"
            f"<div style=\"font-size:15.5px;font-weight:600;line-height:1.45;\">"
            f"{o['cluster']}</div>"
            f"<div style=\"font-size:14.5px;padding-top:2px;line-height:1.55;\">"
            f"{o['evidence']}</div>"
            f"<div style=\"font-size:14.5px;padding-top:2px;line-height:1.55;"
            f"color:{T['text_secondary']};\">Потенциал: {o['potential']}</div>"
            f"<div style=\"font-size:14.5px;padding-top:{SP['xs']}px;line-height:1.55;\">"
            f"Что делаем: {o['recommended_action']}</div>"
            f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
            f"padding-top:2px;\">{decision_label(o)} · "
            f"достоверность: {o['confidence']}</div></div>"
            for o in b["opportunities"]["items"])
        rows.append(_section("Где ближе всего рост", items))

    # I-a. Интерес к вендорам в поиске — перенос Vendor Radar из intelligence
    # поверх снимка. Компактно: топ-3 вендора и до двух PPC-кандидатов; движки
    # раздельно, «спросом» показы не называются (спрос — блок Вордстата ниже).
    vr = b.get("vendor_radar") or {}
    if vr.get("available"):
        v_rows = "".join(
            f"<div style=\"padding:{SP['xs']}px 0;font-size:14.5px;line-height:1.5;\">"
            f"<b>{it['vendor']}</b> — "
            f"{num(it['yandex']['impressions'])} "
            f"{plural(it['yandex']['impressions'], 'показ', 'показа', 'показов')} "
            f"в Яндексе"
            + (f" (лучшая позиция {it['yandex']['best_position']})"
               if it['yandex']['best_position'] is not None else "")
            + (f", {num(it['google']['impressions'])} в Google"
               if it['google']['impressions'] else "")
            + "</div>"
            for it in vr["items"][:3])
        ppc_html = ""
        if vr.get("ppc"):
            lines = "; ".join(
                f"«{c['query']}» ({num(c['shows'])} показов, позиция {c['position']})"
                for c in vr["ppc"][:1])
            ppc_html = (f"<div style=\"font-size:14.5px;padding-top:{SP['s']}px;"
                        f"line-height:1.55;\"><b>Проверить платным трафиком:</b> "
                        f"{lines} — конверсионность запросов не измерена.</div>")
        rows.append(_section("Интерес к вендорам в поиске",
                             v_rows + ppc_html, vr.get("note", "")))

    # I-б. Спрос и направления развития — результат регулярного исследования рынка.
    dm = b.get("demand") or {}
    if dm.get("available"):
        cov = dm["coverage"]
        lead = dm.get("lead_opportunity")
        lead_html = ""
        if lead:
            lead_html = (
                f"<div style=\"font-size:15px;padding-top:{SP['m']}px;line-height:1.6;\">"
                f"<b>Ближайшее направление: {lead['cluster']}.</b> "
                f"{lead['why']} — {num(lead['demand'])} "
                f"{plural(lead['demand'], 'запрос', 'запроса', 'запросов')} в месяц. "
                f"Что делаем: {lead['action']}.</div>")
        rows.append(_section(
            dm["title"],
            f"<div style=\"font-size:15px;line-height:1.6;\">{dm['summary']}</div>"
            f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" "
            f"cellspacing=\"0\" style=\"margin-top:{SP['m']}px;\"><tr>"
            + "".join(
                f"<td width=\"33%\" style=\"padding-right:{SP['m']}px;\">"
                f"<div style=\"font-size:22px;font-weight:700;\">{v:.0%}</div>"
                f"<div data-meta=\"1\" style=\"font-size:12.5px;"
                f"color:{T['text_secondary']};\">{label}</div></td>"
                for label, v in (("есть своя страница", cov["page"]),
                                 ("страница в поиске", cov["indexed"]),
                                 ("на первой странице", cov["top10"])))
            + f"</tr></table>{lead_html}",
            f"Замер спроса от {ru_date(dm.get('measured_at'))}, "
            f"обновляется по расписанию исследования"))

    # I-в. Перспективные идеи бесплатного продвижения — только свежие (status=new),
    # компактно; полная копилка со статусами живёт в веб-отчёте.
    gi = b.get("growth_ideas") or {}
    if gi.get("fresh"):
        idea_rows = "".join(
            f"<div style=\"padding:{SP['xs']}px 0;font-size:14.5px;line-height:1.55;\">"
            f"<b>{it['title']}</b> — {it['why']}</div>"
            for it in gi["fresh"])
        rows.append(_section("Перспективные идеи продвижения", idea_rows,
                             "бесплатные каналы; полный список и статусы — в веб-отчёте"))

    # I-в. Расширение каталога: кого добавить. Спрос без возможности оплатить
    # сделкой не становится, поэтому способ оплаты стоит рядом с цифрой спроса.
    exp = dm.get("expansion") if dm.get("available") else None
    if exp and exp.get("items"):
        cards = "".join(
            f"<div style=\"border:1px solid {T['border']};border-radius:10px;"
            f"padding:{SP['m']}px;margin-top:{SP['s']}px;\">"
            f"<div style=\"font-size:15.5px;font-weight:700;"
            f"color:{T['text_primary']};\">{it['brand']} "
            f"<span data-meta=\"1\" style=\"font-size:12.5px;font-weight:500;"
            f"color:{T['text_secondary']};\">· {it['kind']}</span></div>"
            f"<div style=\"font-size:15px;padding-top:{SP['xs']}px;line-height:1.55;\">"
            f"{num(it['demand'])} "
            f"{plural(it['demand'], 'запрос', 'запроса', 'запросов')} в месяц · "
            f"{PAYMENT_LABEL.get(it['payment'], 'оплата не определена')}. "
            f"{it['recommendation'].capitalize()}: {it['effort']}.</div>"
            + (f"<div data-meta=\"1\" style=\"font-size:12.5px;"
               f"color:{T['text_secondary']};padding-top:{SP['xs']}px;"
               f"line-height:1.45;\">{it['confidence_note']}</div>"
               if it.get("confidence_note") else "")
            + "</div>"
            for it in exp["items"])
        manual = ""
        if exp.get("manual_check"):
            manual = (f"<div style=\"font-size:15px;padding-top:{SP['m']}px;"
                      f"line-height:1.55;\"><b>Проверить вручную:</b> "
                      + ", ".join(exp["manual_check"])
                      + " — спрос есть, способ оплаты автоматически определить "
                        "не удалось.</div>")
        rows.append(_section(
            exp["title"],
            f"<div style=\"font-size:15px;line-height:1.6;\">{exp['summary']}</div>"
            f"{cards}{manual}",
            exp.get("note")))

    # I-г. Управленческие воздействия (поручение руководителя 01.09.2026):
    # каждое предложение «стола решений» — развёрнутой постановкой задачи.
    if b.get("management_actions"):
        cards_ma = ""
        for i, m in enumerate(b["management_actions"], 1):
            cards_ma += (
                f"<div style=\"padding:{SP['m']}px 0;"
                f"border-bottom:1px solid {T['border']};\">"
                f"<div style=\"font-size:15px;font-weight:600;line-height:1.45;\">"
                f"{i}. {m['task']}</div>"
                f"<div style=\"font-size:14.5px;padding-top:{SP['xs']}px;"
                f"line-height:1.55;\"><b>Зачем:</b> {m['why']}.</div>"
                f"<div style=\"font-size:14.5px;padding-top:{SP['xs']}px;"
                f"line-height:1.55;\"><b>Что делаем:</b> {m['steps']}.</div>"
                f"<div data-meta=\"1\" style=\"font-size:12.5px;"
                f"color:{T['text_secondary']};padding-top:{SP['xs']}px;"
                f"line-height:1.5;\">Приёмка: {m['acceptance']}. "
                f"От вас: {m['from_you']}.</div></div>")
        rows.append(_section(
            "Управленческие воздействия", cards_ma,
            "постановки задач по предложениям из шапки; система без вашей "
            "команды ничего не меняет"))

    # J-а. Техническое состояние: PageSpeed по представителям шаблонов.
    # В зелёном состоянии блок занимает несколько строк — подробности нужны
    # только когда есть просадка, иначе он превращается в шум.
    rows.append(_section("Техническое состояние", _technical_html(b["technical"])))

    # J. Здоровье данных
    h = b["health"]
    colour = {"positive": T["positive"], "warning": T["warning"],
              "danger": T["danger"]}[h["colour"]]
    bg = {"positive": "#ECFDF3", "warning": "#FFFAEB", "danger": "#FEF3F2"}[h["colour"]]
    lh_line = loop_health_line(b.get("loop_health") or {})
    lh_html = ""
    if lh_line:
        text_lh, alarm = lh_line
        lh_html = (f"<div data-meta=\"1\" style=\"font-size:12.5px;"
                   f"padding-top:{SP['s']}px;line-height:1.45;"
                   f"color:{T['danger'] if alarm else T['text_secondary']};\">"
                   f"{text_lh}</div>")
    rows.append(_section(
        "Здоровье данных",
        f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
        f"style=\"background:{bg};border-left:4px solid {colour};"
        f"border-radius:0 12px 12px 0;\"><tr><td style=\"padding:{SP['l']}px;\">"
        f"<div style=\"font-size:15.5px;font-weight:700;color:{T['text_primary']};\">"
        f"{PILL_LABEL[h['status']].capitalize()}: {h['reason']}</div>"
        f"<div style=\"font-size:15px;padding-top:{SP['xs']}px;line-height:1.55;\">"
        f"{h['detail']}</div>"
        f"<div style=\"font-size:14.5px;padding-top:{SP['s']}px;line-height:1.55;"
        f"color:{T['text_primary']};\">{b['measurement_summary']}</div>"
        f"{lh_html}"
        f"</td></tr></table>"))

    # K. Контрольные точки
    if b["checkpoints"]:
        cps = "".join(
            f"<div style=\"font-size:15px;padding:{SP['xs']}px 0;line-height:1.55;\">"
            f"<b>{c['date']}</b> — {c['what']}</div>" for c in b["checkpoints"])
        done_today = [e["ticket"] for e in b["experiments"]
                      if e.get("control_date_today")]
        note_done = (f"Проверки {', '.join(done_today)} проведены сегодня — их вердикты "
                     f"выше, в «Контроле эксперимента». " if done_today else "")
        cps += (f"<div data-meta=\"1\" style=\"font-size:12.5px;color:{T['text_secondary']};"
                f"padding-top:{SP['s']}px;line-height:1.45;\">"
                f"{note_done}"
                f"До перечисленных дат выводы не делаются: данных выдачи за более "
                f"короткий срок недостаточно, чтобы отличить эффект от обычных колебаний."
                f"</div>")
        rows.append(_section("Следующие проверки", cps))

    # L. Ссылки
    label = "Полный отчёт" if b["links"]["web_public"] else "Полный отчёт (техническая копия)"
    rows.append(
        f"<tr><td style=\"padding:{SP['xl']}px 0 {SP['s']}px 0;\">"
        f"<a class=\"btn\" href=\"{b['links']['web']}\" style=\"display:inline-block;"
        f"background:{T['brand']};color:#fff;text-decoration:none;font-size:15px;"
        f"font-weight:600;padding:11px 20px;border-radius:8px;\">{label}</a>"
        f"<a class=\"btn\" href=\"{b['links']['tasks']}\" style=\"display:inline-block;"
        f"margin-left:{SP['s']}px;border:1px solid {T['border']};color:{T['text_primary']};"
        f"text-decoration:none;font-size:15px;padding:10px 20px;border-radius:8px;\">"
        f"Журнал работ</a></td></tr>")

    media = (
        "@media only screen and (max-width:480px){"
        ".wrap{width:100%!important;padding:16px!important}"
        ".kpi{max-width:100%!important;padding:6px 0!important}"
        ".cell{display:block!important;width:100%!important;border-top:0!important;"
        "padding:2px 0!important}"
        ".row{border-top:1px solid #EAECF0!important;padding-top:10px!important}"
        ".btn{display:block!important;margin:0 0 8px 0!important;text-align:center!important}"
        "}")

    return (
        f"<div style=\"margin:0;padding:0;background:{T['background']};\">"
        f"<style>{media}</style>"
        f"<!--[if mso]><table role=\"presentation\" width=\"680\" align=\"center\"><tr><td><![endif]-->"
        f"<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
        f"style=\"background:{T['background']};\"><tr>"
        f"<td align=\"center\" style=\"padding:{SP['xl']}px {SP['m']}px;\">"
        f"<table role=\"presentation\" class=\"wrap\" width=\"100%\" cellpadding=\"0\" "
        f"cellspacing=\"0\" style=\"width:100%;max-width:680px;background:{T['surface']};"
        f"border-radius:16px;padding:{SP['xxl']}px;font-family:{FONT};"
        f"color:{T['text_primary']};\">"
        + "".join(rows) +
        f"</table></td></tr></table>"
        f"<!--[if mso]></td></tr></table><![endif]--></div>")


def plain_text(b: dict) -> str:
    L = [f"{b['title'].upper()} — {b['date_h']}",
         b["subtitle"].replace("&amp;", "&"),
         " · ".join(f"{p['label']}: {p['text']}" for p in b["pills"]),
         b["sources_line"], "",
         f"ОТ ВАС: {b['user_action']}"]
    if not b["user_action_required"] and b.get("owner_desk"):
        L += [f"  на вашем столе {counted(len(b['owner_desk']), 'предложение', 'предложения', 'предложений')}:"]
        L += [f"  - {d}" for d in b["owner_desk"]]
    L += ["", "ПОКАЗАТЕЛИ"]
    for k in b["kpis"]:
        d = f" ({k['delta']}{' ' + k['relative'] if k.get('relative') else ''})" if k["delta"] else ""
        L.append(f"- {k['label']}: {k['value']} {k['unit']}{d}. {k['interpretation']}")
        L.append(f"  {k['period']} · {k['source']} · достоверность: {k['confidence']}")
    # Техника — одной строкой: состояние, балл и суть изменения. Подробности
    # ждут в полном отчёте, письмо ими не нагружается.
    L += ["", technical.email_line(b["technical"])]
    if b["signals"]:
        L += ["", "СИГНАЛЫ ДНЯ"]
        for s in b["signals"]:
            L.append(f"- {s['metric']}: {s['previous']} -> {s['current']} ({s['delta']}). "
                     f"{s['meaning']}")
    lb = b.get("leads") or {}
    if lb.get("available"):
        L += ["", "ЗАЯВКИ ЗА СУТКИ", leads_mod.summary_line(lb)]
        for it in lb["items"]:
            L.append(f"- {it['time']} · {it['company']}: {it['request']} ({it['form']})")
            L.append(f"  канал: {it['channel']} — основание: {it['channel_basis']}")
            L.append(f"  путь: {it['journey']}")
        if lb["more"]:
            L.append(f"  ещё {counted(lb['more'], 'заявка', 'заявки', 'заявок')} "
                     f"за сутки — в воронке сайта")
        if lb.get("note"):
            L.append(f"  {lb['note']}")
    ads = b.get("ads") or {}
    if ads.get("available"):
        L += ["", "РЕКЛАМА — ЯНДЕКС.ДИРЕКТ", ads_headline(ads, currency="р.")]
        tone_word = {"grey": "[серый]", "ok": "[зелёный]",
                     "warn": "[жёлтый]", "bad": "[красный]"}
        for r in ads["rows"]:
            cpc = f", CPC {r['cpc']:.0f} р." if r["cpc"] else ""
            if r.get("leads") is not None:
                cpc += f", заявок {r['leads']}"
                if r.get("cpa"):
                    cpc += f" (CPA {r['cpa']:.0f} р.)"
                if r.get("contacts"):
                    cpc += f", контактов {r['contacts']}"
            L.append(f"- {r['label']}: {r['spend_day']:.0f} р., "
                     f"{counted(r['clicks_day'], 'клик', 'клика', 'кликов')} за день{cpc} "
                     f"{tone_word[r['verdict']['tone']]} {r['verdict']['label']}")
        for d in ads["decisions"][:3]:
            L.append(f"  ТРЕБУЕТ РЕШЕНИЯ: {d['text']}")
        if ads.get("note"):
            L.append(f"  {ads['note']}")
    L += ["", "ЧТО ДАЛО ИЗМЕНЕНИЕ", b["driver_summary"]]
    for r in b["driver_rows"]:
        L.append(f"  {r['entity']}: {signed(r['delta'])} "
                 f"({round(r['share_of_total_delta'] * 100)}% изменения)")
    # Текстовая версия повторяет вёрстку письма: подробно один эксперимент,
    # остальные — строкой. Иначе plain text расходится с HTML по составу.
    exps_txt = sorted(b["experiments"],
                      key=lambda x: (not x.get("control_date_today"),
                                     -x.get("days_elapsed", 0)))
    if exps_txt:
        e = exps_txt[0]
        interim_line, interim_caveat = _exp_interim_line(e)
        L += ["", "КОНТРОЛЬ ЭКСПЕРИМЕНТА",
              f"- {e['ticket']}: запуск {ru_date(e['start'])}, день "
              f"{e['days_elapsed']}, минимум для вывода {e['minimum_exposure']}",
              f"  внедрение: {_exp_implementation_line(e)}",
              f"  выдача Яндекса: {_exp_serp_line(e)}",
              f"  экспозиция: {_exp_exposure_line(e)}",
              f"  старый -> новый: {interim_line}"]
        if interim_caveat:
            L.append(f"    оговорки: {interim_caveat}")
        L += [f"  вывод: {VERDICT_LABEL[e['verdict']]} — {e['verdict_reason']}, "
              f"следующая проверка {ru_date(e['next_review'])}"]
        outlook = _exp_outlook_line(e)
        if outlook:
            L.append(f"  что дальше: {outlook}")
        L.append(f"  {e['combined_note']}")
        if e.get("control_date_today") and e.get("evaluation"):
            ev = e["evaluation"]
            L.append(f"  ВЕРДИКТ КОНТРОЛЬНОЙ ТОЧКИ: {EXP_VERDICT_LABEL[ev['verdict']]} "
                     f"(уверенность {EXP_CONF_LABEL[ev['confidence']]}) — "
                     f"{ev['verdict_reason']}")
            if ev.get("summary_line"):
                L.append(f"    {ev['summary_line']}")
            L.append(f"  рекомендация: {EXP_REC_LABEL[ev['recommendation']]} — "
                     f"{ev['recommendation_detail']}")
            if ev["requires_owner_decision"]:
                L.append(f"  ТРЕБУЕТСЯ ВАШЕ РЕШЕНИЕ: ответьте "
                         f"{ev['recommendation']} {e['ticket']} "
                         f"(или KEEP/REVERT/EXPAND/EXTEND {e['ticket']})")
        for o in exps_txt[1:]:
            if o.get("control_date_today") and o.get("evaluation"):
                ov = o["evaluation"]
                L.append(f"- {o['ticket']}: вердикт {EXP_VERDICT_LABEL[ov['verdict']]} — "
                         f"{ov['verdict_reason']}; рекомендация "
                         f"{EXP_REC_LABEL[ov['recommendation']]}")
            else:
                L.append(f"- {o['ticket']}: {_exp_short_line(o)}")
    if b["board"]:
        L += ["", "СИСТЕМА УЖЕ ДЕЛАЕТ"]
        for r in b["board"]:
            L.append(f"- {r['task']} — {r['owner']} · стадия: {r['stage']} · "
                     f"{r['status']} · до {r['due']} · {r.get('artifact') or '—'}")
            if r.get("pr"):
                L.append(f"  PR {r['pr']} · проверки {r['ci']} · тестирование {r['qa']} · "
                         f"{r['deploy']} · откат {r['rollback']}")
    if b["opportunities"]["available"]:
        L += ["", "ГДЕ БЛИЖЕ ВСЕГО РОСТ"]
        for o in b["opportunities"]["items"]:
            L.append(f"- {o['cluster']}: {o['evidence']}")
            L.append(f"  потенциал: {o['potential']}")
            L.append(f"  что делаем: {o['recommended_action']} "
                     f"({decision_label(o)})")
    vr = b.get("vendor_radar") or {}
    if vr.get("available"):
        L += ["", "ИНТЕРЕС К ВЕНДОРАМ В ПОИСКЕ"]
        for it in vr["items"][:3]:
            line = (f"- {it['vendor']}: {num(it['yandex']['impressions'])} показов "
                    f"в Яндексе")
            if it["google"]["impressions"]:
                line += f", {num(it['google']['impressions'])} в Google"
            L.append(line)
        for c in (vr.get("ppc") or [])[:1]:
            L.append(f"  проверить платным трафиком: «{c['query']}» "
                     f"({num(c['shows'])} показов, позиция {c['position']})")
        L.append(f"  {vr.get('note', '')}")
    dm = b.get("demand") or {}
    if dm.get("available"):
        cov = dm["coverage"]
        L += ["", dm["title"].upper(), dm["summary"],
              f"Покрытие: страница {cov['page']:.0%}, в поиске {cov['indexed']:.0%}, "
              f"первая страница {cov['top10']:.0%}."]
        if dm.get("lead_opportunity"):
            lead = dm["lead_opportunity"]
            L.append(f"Ближайшее направление: {lead['cluster']} — {lead['action']} "
                     f"({num(lead['demand'])} "
                     f"{plural(lead['demand'], 'запрос', 'запроса', 'запросов')} "
                     "в месяц).")
        exp = dm.get("expansion")
        if exp and exp.get("items"):
            L += ["", exp["title"].upper(), exp["summary"]]
            for it in exp["items"]:
                L.append(f"- {it['brand']} ({it['kind']}): {num(it['demand'])} "
                         f"{plural(it['demand'], 'запрос', 'запроса', 'запросов')} "
                         f"в месяц, {PAYMENT_LABEL.get(it['payment'], 'оплата не определена')} "
                         f"— {it['recommendation']}")
            if exp.get("manual_check"):
                L.append("Проверить вручную: " + ", ".join(exp["manual_check"]) + ".")
    gi = b.get("growth_ideas") or {}
    if gi.get("fresh"):
        L += ["", "ПЕРСПЕКТИВНЫЕ ИДЕИ ПРОДВИЖЕНИЯ"]
        for it in gi["fresh"]:
            L.append(f"- {it['title']} — {it['why']}")
    h = b["health"]
    if b.get("management_actions"):
        L += ["", "УПРАВЛЕНЧЕСКИЕ ВОЗДЕЙСТВИЯ"]
        for i, m in enumerate(b["management_actions"], 1):
            L += [f"{i}. {m['task']}",
                  f"   зачем: {m['why']}",
                  f"   что делаем: {m['steps']}",
                  f"   приёмка: {m['acceptance']}",
                  f"   от вас: {m['from_you']}"]
    L += ["", "ЗДОРОВЬЕ ДАННЫХ",
          f"{PILL_LABEL[h['status']].capitalize()}: {h['reason']}. {h['detail']}",
          b["measurement_summary"]]
    lh_line = loop_health_line(b.get("loop_health") or {})
    if lh_line:
        L.append(lh_line[0])
    if b["checkpoints"]:
        L += ["", "СЛЕДУЮЩИЕ ПРОВЕРКИ"]
        done_today = [e["ticket"] for e in b["experiments"]
                      if e.get("control_date_today")]
        if done_today:
            L.append(f"  проверки {', '.join(done_today)} проведены сегодня — "
                     f"вердикты выше, в «Контроле эксперимента»")
        for c in b["checkpoints"]:
            L.append(f"- {c['date']} — {c['what']}")
    L += ["", f"Полный отчёт: {b['links']['web']}", f"Журнал работ: {b['links']['tasks']}"]
    return "\n".join(L)


def strip_tags(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"&[a-z]+;", " ", html)


def visible_words(html: str) -> int:
    """Слова, которые действительно видит читатель, — по готовому письму."""
    return words(strip_tags(html))


def first_screen_words(html: str) -> int:
    """Первый экран: до маркера, поставленного после блока показателей."""
    head = html.split(FIRST_SCREEN_MARKER)[0]
    return visible_words(head)


def build_eml(b: dict, html: str, text: str, charts: dict, date: str) -> bytes:
    from email.message import EmailMessage
    from email.utils import formatdate, make_msgid
    msg = EmailMessage()
    msg["From"] = "BIZSoft Growth Intelligence <hello@biz-soft.pro>"
    msg["To"] = "avbelyaev@biz-soft.pro"
    msg["Subject"] = f"BIZSoft Growth Intelligence — {b['date_h']}"
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(text)
    real = {}
    for key, c in charts.items():
        cid = make_msgid(domain="biz-soft.pro")
        html = html.replace(f"cid:{c['cid']}", f"cid:{cid[1:-1]}")
        real[cid] = charts_v4.OUT / c["file"]
    msg.add_alternative(html, subtype="html")
    part = msg.get_payload()[-1]
    for cid, path in real.items():
        if path.exists():
            part.add_related(path.read_bytes(), "image", "png", cid=cid,
                             filename=path.name, disposition="inline")
    return msg.as_bytes()


# Как звучит способ оплаты в письме: без API-терминов, языком решения.
PAYMENT_LABEL = {
    "card": "оплата картой на сайте вендора есть",
    "likely_card": "покупка на сайте есть, платёжную систему подтвердить при первой сделке",
    "sales_only": "покупка только через отдел продаж",
    "unknown": "способ оплаты не определён",
    "unreachable": "сайт вендора не открылся при проверке",
    "not_checked": "оплата не проверена",
}


def load_demand() -> dict:
    """Блок спроса из системы исследования рынка.

    Спрос обновляется по расписанию исследования, а не ежедневно, поэтому в письме
    он идёт отдельным блоком аналитики и не смешивается с суточными показателями.
    """
    if not DEMAND_STATE.exists():
        return passport.unavailable("no_file", source="исследование спроса")
    state = json.loads(DEMAND_STATE.read_text(encoding="utf-8"))
    # Сводка приходит из ветки данных и могла быть собрана старым кодом без
    # кода причины — доводится до контракта здесь, а не роняет письмо.
    block = passport.normalize(state.get("executive_block"),
                               default_code="no_rows", source="сводка исследования спроса")
    if block.get("available") and not block.get("as_of"):
        block["as_of"] = state.get("date") or block.get("date")
    return _drop_vendors_already_on_site(block)


def load_growth_ideas() -> dict:
    """Перспективные идеи бесплатного продвижения и расширения.

    Раздел заведён решением руководителя 29.08.2026 после лида из
    Бизнес-каталога Яндекса. Копилка живёт в growth-ideas.json (seo-data):
    в письме показываются только свежие идеи (status=new, до двух), полный
    список со статусами — в веб-отчёте. Идея, принятая или отклонённая
    руководителем, меняет статус и из письма уходит.
    """
    if not GROWTH_IDEAS.exists():
        return passport.unavailable("no_file", source="копилка идей", items=[], fresh=[])
    data = json.loads(GROWTH_IDEAS.read_text(encoding="utf-8"))
    items = data.get("items", [])
    fresh = [i for i in items if i.get("status") == "new"][:2]
    return {"available": bool(items), "items": items, "fresh": fresh}


def _site_vendor_words() -> set[str]:
    """Имена вендоров каталога целыми словами — из src/data/vendors.ts."""
    p = pathlib.Path("src/data/vendors.ts")
    if not p.exists():
        return set()
    text = p.read_text(encoding="utf-8")
    words: set[str] = set()
    for slug, name in re.findall(r"\{\s*slug:\s*'([^']+)',\s*vendor:\s*'([^']+)'", text):
        words.add(slug.replace("-", " ").lower())
        words.add(name.lower())
    return words


VENDOR_DECISIONS = BASE / "vendor-decisions.json"
# Второй реестр решений по кандидатам — им пользуется исследование
# (scripts/seo/wordstat/audience.py). Реестра было два, и они не знали друг о
# друге: 29.08.2026 руководитель отклонил NordVPN и Ansys, запись легла только
# в reports/vendors/rejected-products.md, и оба контура продолжали предлагать
# их заново (проверка руководителя 02.09.2026). Читаем оба: решение,
# записанное в любой из них, действует и в письме, и в исследовании.
WORDSTAT_DECISIONS = pathlib.Path("reports/seo/wordstat/decisions.json")


def _norm_brand(b: str) -> str:
    return " ".join(re.findall(r"[a-zа-яё0-9]+", (b or "").lower()))


def rejected_vendor_brands() -> set[str]:
    """Кандидаты в каталог, отклонённые руководителем (нормализованные имена)."""
    out: set[str] = set()
    if VENDOR_DECISIONS.exists():
        try:
            d = json.loads(VENDOR_DECISIONS.read_text(encoding="utf-8"))
            out |= {_norm_brand(b) for b in (d.get("rejected") or {})}
        except (OSError, json.JSONDecodeError):
            pass
    if WORDSTAT_DECISIONS.exists():
        try:
            d = json.loads(WORDSTAT_DECISIONS.read_text(encoding="utf-8"))
            out |= {_norm_brand(r.get("brand", ""))
                    for r in (d.get("rejected") or []) if r.get("brand")}
        except (OSError, json.JSONDecodeError):
            pass
    return {b for b in out if b}


def _drop_vendors_already_on_site(block: dict) -> dict:
    """Не предлагать к заведению вендора, который уже на сайте.

    Рекомендации приходят из состояния исследования, а оно обновляется своим
    прогоном. 21.08 письмо ушло с предложением завести Suno и Cloudflare —
    обе карточки к тому моменту уже стояли на сайте, прогон исследования
    закрыл их через полминуты после сборки письма. Поэтому список сверяется
    с каталогом в момент сборки, а не только в момент исследования.
    """
    exp = (block or {}).get("expansion")
    if not exp:
        return block
    on_site = _site_vendor_words()
    if not on_site:
        return block
    # Бренды, отклонённые руководителем, не предлагаются повторно
    # (01.09.2026: «aws не добавляем и из предложений на будущее исключаем»).
    rejected = rejected_vendor_brands()

    def known(brand: str) -> bool:
        b = " ".join(re.findall(r"[a-zа-яё0-9]+", (brand or "").lower()))
        return (bool(b) and any(b == w or b in w.split() for w in on_site)
                or b in rejected)

    items = [i for i in (exp.get("items") or []) if not known(i.get("brand", ""))]
    manual = [m for m in (exp.get("manual_check") or []) if not known(m)]
    dropped = (len(exp.get("items") or []) - len(items)
               + len(exp.get("manual_check") or []) - len(manual))
    if not dropped:
        return block
    exp = dict(exp, items=items, manual_check=manual)
    if not items and not manual:
        exp["summary"] = ("Новых вендоров с подтверждённым спросом вне каталога "
                          "сейчас нет: все кандидаты уже заведены.")
    block = dict(block, expansion=exp)
    return block


def load_loop_health() -> dict:
    """Реестр исполнения контуров конвейера (пишет loop_health.py).

    Файл может отсутствовать в старых данных — тогда блок молчит, а не
    сообщает ложное «всё в срок».
    """
    if not LOOP_HEALTH.exists():
        return passport.unavailable("no_file", source="реестр исполнения контуров")
    try:
        return json.loads(LOOP_HEALTH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return passport.unavailable("parse_error", source="реестр исполнения контуров")


def loop_health_line(lh: dict) -> tuple[str, bool] | None:
    """Одна строка о конвейере для блока «Здоровье данных» (текст, тревога).

    Коротко намеренно: подробная таблица контуров живёт в веб-отчёте,
    письму хватает факта «в срок / просрочено что».
    """
    if not lh.get("available"):
        return None
    over = [r for r in lh.get("contours", []) if r.get("overdue")]
    if not over:
        return (f"Конвейер: {lh.get('ok_count')} из {lh.get('total')} "
                "контуров отработали в срок.", False)
    named = "; ".join(
        f"{r['label']} — последний прогон "
        f"{ru_date(r['last_run']) if r['last_run'] else 'не найден'}"
        for r in over[:2])
    extra = f" и ещё {len(over) - 2}" if len(over) > 2 else ""
    return (f"Конвейер: просрочено {counted(len(over), 'контур', 'контура', 'контуров')}"
            f"{extra}: {named}.", True)


def load_site_check(date: str) -> dict | None:
    """Свежайшая проверка живых страниц, не обязательно сегодняшняя.

    31.08.2026 сегодняшний файл затёрла гонка параллельных пушей в seo-data,
    и письмо написало «нет данных», хотя проверка прошла за минуты до сборки.
    Устойчивость: берём файл за дату письма, а без него — свежайший не старше
    трёх дней; его дата возвращается и показывается в письме честно.
    """
    for back in range(4):
        d = (dt.date.fromisoformat(date) - dt.timedelta(days=back)).isoformat()
        p = BASE / f"site-check-{d}.json"
        if p.exists():
            return {"experiments":
                    json.loads(p.read_text(encoding="utf-8")).get("experiments"),
                    "date": d}
    return None


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    snap = json.loads((BASE / "snapshots" / f"{date}.json").read_text(encoding="utf-8"))
    prev = snapshot_mod.prev_snapshot(date)
    dq = json.loads((BASE / "data-quality" / f"{date}.json").read_text(encoding="utf-8"))
    actions_cfg = json.loads((BASE / "actions.json").read_text(encoding="utf-8"))

    # Реестр исполнения контуров обновляется здесь, а не отдельным шагом
    # конвейера: письмо строится ежедневно, и лишний шаг в промпте Routine —
    # лишняя точка отказа.
    loop_health_mod.write(date)
    b = assemble(snap, prev, dq, actions_cfg, load_site_check(date))
    charts = charts_v4.build(date, b["kpis"], b["driver_rows"],
                             b["experiments"][0] if b["experiments"] else None)

    email_html = html_email(b, charts, cid_mode=True)
    preview_html = html_email(b, charts, cid_mode=False)
    text = plain_text(b)

    (BASE / f"{date}-v4.html").write_text(preview_html, encoding="utf-8")
    (BASE / f"{date}-v4.txt").write_text(text, encoding="utf-8")
    (BASE / f"{date}-v4-blocks.json").write_text(
        json.dumps(b, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    # Инварианты боевого письма — те же правила, что в сценарных тестах.
    # Два уровня (решение руководителя 03.09.2026): ложь о дате или причине
    # блокирует выпуск — файл для отправки не пишется, а причины ложатся в
    # <дата>-v4-blocked.json, откуда их берёт уведомление о сбое сборки
    # (seo-report-email.yml). Мягкие нарушения формы остаются в
    # <дата>-invariants.json, письмо уходит.
    inv = invariants_mod.write_report(date, snap, dq, b, preview_html)
    email_path = BASE / f"{date}-v4-email.html"
    blocked_path = BASE / f"{date}-v4-blocked.json"
    if inv["blocking"]:
        email_path.unlink(missing_ok=True)
        blocked_path.write_text(json.dumps(
            {"date": date, "blocking": inv["blocking"], "soft": inv["soft"]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print("ПИСЬМО ЗАБЛОКИРОВАНО инвариантами о дате и причине "
              f"({len(inv['blocking'])}):")
        for line in inv["blocking"]:
            print(f"  - {line}")
        print(f"Файл для отправки не записан; причины — {blocked_path.name}")
        return 2
    blocked_path.unlink(missing_ok=True)
    email_path.write_text(email_html, encoding="utf-8")
    (BASE / f"{date}-v4.eml").write_bytes(build_eml(b, email_html, text, charts, date))
    inv_status = ("ок" if inv["passed"]
                  else "мягкие нарушения: " + "; ".join(inv["soft"]))

    print(f"V4: видимых слов {visible_words(preview_html)}, "
          f"первый экран {first_screen_words(preview_html)}, "
          f"текстовая версия {words(text)}, изображений {len(charts)}, "
          f"инварианты: {inv_status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
