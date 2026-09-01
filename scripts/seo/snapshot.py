#!/usr/bin/env python3
"""Канонический snapshot отчётности BIZSoft (schema v2).

Единственный источник цифр для отчёта: сырые выгрузки reports/seo/data/*.json
нормализуются в одну модель, из которой затем строятся executive brief,
приложение, графики и проверки качества. Правило: отсутствующее значение — None
(в отчёте «нет данных»), ноль означает измеренный ноль.

Запуск: python3 scripts/seo/snapshot.py [YYYY-MM-DD]
Результат: reports/seo/intelligence/snapshots/<дата>.json
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

import daily_windows

SCHEMA_VERSION = "2.2.0"
# Часовой пояс отчётности — московский: так требует правило проекта, и так же
# отдают данные GA4 (metadata.timeZone = Europe/Moscow) и Метрика. Прежнее
# значение Asia/Bishkek не совпадало ни с тем, ни с другим.
TIMEZONE = "Europe/Moscow (UTC+3)"
DATA_DIR = pathlib.Path("reports/seo/data")
OUT_DIR = pathlib.Path("reports/seo/intelligence/snapshots")

# Пороги низкой выборки — конфигурируемые (см. docs/seo/reporting-methodology.md)
THRESHOLDS = {
    "low_impressions": 50,     # ниже — выводы о видимости ненадёжны
    "low_visits": 20,          # ниже — выводы о конверсии ненадёжны
    "low_conversions": 5,      # ниже — только предварительный сигнал
    "top_position": 10.0,      # строгая граница «в топ-10»
    "reconciliation_ratio": 2.0,  # расхождение источников больше чем в 2 раза — critical
}

BRAND_MARKERS = ("bizsoft", "биз софт", "бизсофт", "biz-soft")
COMMERCIAL_MARKERS = (
    "купить", "оплат", "цен", "стоимост", "тариф", "подписк", "лицензи",
    "продл", "заказ", "счет", "счёт", "buy", "price", "license", "pricing",
)
INFO_MARKERS = ("как ", "что ", "почему ", "можно ли", "нужн", "how ", "what ")


SRC_DIR = pathlib.Path("src")
GOAL_CALL = re.compile(r"trackGoal\(\s*['\"]([a-z0-9_]+)['\"]")
GOAL_ATTR = re.compile(r"data-ev(?:-view)?=\"([a-z0-9_]+)\"")


GOALS_REGISTRY = pathlib.Path("src/lib/analytics.ts")
GOAL_SPEC = re.compile(r"^\s{2}([a-z0-9_]+):\s*\{\s*ga4:\s*'[^']*',\s*key:\s*(true|false)", re.M)


def goal_levels() -> dict[str, str]:
    """Уровень каждой цели из реестра src/lib/analytics.ts.

    Реестр один на весь проект: из него же goals_sync заводит цели в кабинетах.
    Второй список уровней рядом означал бы два ответа на вопрос, обязана ли
    цель быть заведена, — ровно та ошибка, которую этот аудит и разбирает.

    Флаг key в реестре отвечает на тот же вопрос: конверсия обязана иметь цель
    в Метрике, сигнал намерения — нет.
    """
    if not GOALS_REGISTRY.exists():
        return {}
    return {name: ("lead" if key == "true" else "engagement")
            for name, key in GOAL_SPEC.findall(GOALS_REGISTRY.read_text(encoding="utf-8"))}


def declared_goals() -> list[str]:
    """Имена целей, которые фактически отправляет сайт.

    Ищутся строковые литералы, а не только аргумент сразу после trackGoal(:
    часть целей выбирается тернарником, часть приходит из таблицы соответствий
    (клики по телефону, почте и в мессенджеры — src/lib/contact-goals.ts).
    Сканер, знающий лишь одну форму вызова, объявил бы половину конверсий
    неотправляемыми и тем самым спрятал бы находку, ради которой он написан.

    Снимок уже носил список целей, заведённых в счётчике. Не хватало второй
    половины сверки — того, что счётчику отправляют. Обе половины лежат рядом,
    и их расхождение проверяется одной строкой: см. GOAL_NOT_CONFIGURED.
    """
    known = set(goal_levels())
    if not known or not SRC_DIR.exists():
        return []
    found: set[str] = set()
    for path in SRC_DIR.rglob("*"):
        if path.suffix not in (".astro", ".ts") or not path.is_file():
            continue
        if path.name == "analytics.ts":
            continue        # сам реестр не является местом вызова
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for name in known:
            if f"'{name}'" in text or f'"{name}"' in text:
                found.add(name)
    return sorted(found)


def days_inclusive(a: str, b: str) -> int:
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days + 1


def classify_intent(q: str) -> str:
    low = q.lower()
    if any(m in low for m in BRAND_MARKERS):
        return "navigational"
    if any(m in low for m in COMMERCIAL_MARKERS):
        return "commercial"
    if any(low.startswith(m) for m in INFO_MARKERS):
        return "informational"
    return "unknown"


def is_branded(q: str) -> bool:
    return any(m in q.lower() for m in BRAND_MARKERS)


def confidence(sample: int | None, kind: str = "impressions") -> str:
    if sample is None:
        return "unknown"
    limit = THRESHOLDS["low_impressions"] if kind == "impressions" else THRESHOLDS["low_visits"]
    if sample < limit / 5:
        return "very_low"
    if sample < limit:
        return "low"
    return "sufficient"


def load(prefix: str, date: str) -> dict | None:
    p = DATA_DIR / f"{prefix}-{date}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def git_revisions(path: pathlib.Path, date: str) -> list[str]:
    """SHA коммитов, затронувших файл в указанный день (для учёта пересборов)."""
    try:
        out = subprocess.run(
            ["git", "log", "--format=%H %ad", "--date=short", "--", str(path)],
            capture_output=True, text=True, timeout=20, check=False).stdout
    except Exception:
        return []
    return [ln.split()[0] for ln in out.splitlines() if ln.strip().endswith(date)]


def git_show_json(sha: str, path: pathlib.Path) -> dict | None:
    try:
        out = subprocess.run(["git", "show", f"{sha}:{path}"],
                             capture_output=True, text=True, timeout=20, check=False)
        return json.loads(out.stdout) if out.returncode == 0 and out.stdout else None
    except Exception:
        return None


def revisions_for(prefix: str, date: str, extract, metric: str) -> dict | None:
    """Значения метрики во всех сборах указанного дня (источник мог пересобираться)."""
    path = DATA_DIR / f"{prefix}-{date}.json"
    if not path.exists():
        return None
    seen = []
    for sha in git_revisions(path, date):
        old = git_show_json(sha, path)
        if not old or old.get("error"):
            continue
        try:
            v = extract(old)
        except Exception:
            continue
        if v is not None and v not in seen:
            seen.append(v)
    current = extract(json.loads(path.read_text(encoding="utf-8")))
    values = sorted({float(v) for v in seen} | ({float(current)} if current is not None else set()))
    if len(values) < 2:
        return None
    return {"metric": metric, "date": date, "values_seen": values,
            "canonical": float(current) if current is not None else None,
            "reason": "источник пересобирался в течение дня; каноническим считается последний сбор"}


def _goal_breakdown(metrika: dict) -> list[dict] | None:
    """Достижения целей органикой: [{name, events}] по убыванию, только ненулевые."""
    reaches = metrika.get("organic_goal_reaches")
    if not isinstance(reaches, dict) or "error" in reaches:
        return None
    names = {str(g.get("id")): g.get("name") for g in metrika.get("goals", [])
             if isinstance(g, dict)}
    rows = [{"name": names.get(gid, gid), "events": int(v)}
            for gid, v in reaches.items() if v]
    return sorted(rows, key=lambda r: -r["events"]) or []


def source_meta(name, collected_at, latest_event, p_start, p_end, cmp_start, cmp_end,
                filters, status, notes=None) -> dict:
    return {
        "source_name": name,
        "collected_at": collected_at,
        "latest_event_date": latest_event,
        "current_period_start": p_start,
        "current_period_end": p_end,
        "current_period_days": days_inclusive(p_start, p_end) if p_start and p_end else None,
        "comparison_period_start": cmp_start,
        "comparison_period_end": cmp_end,
        "comparison_period_days": days_inclusive(cmp_start, cmp_end) if cmp_start and cmp_end else None,
        "filters": filters,
        "status": status,
        "notes": notes,
    }


def source_unavailable(name: str, raw: dict | None, error: str | None = None,
                       p_start: str | None = None, p_end: str | None = None,
                       filters: dict | None = None, status: str | None = None) -> dict:
    """Блок источника, не отдавшего данные.

    Канонические статусы (см. docs/seo/reporting-methodology.md):
      missing   — выгрузки нет (сбор не запускался или файл не доехал);
      error     — источник вернул ошибку (включая ошибку отдельного среза);
      empty     — формально успешный ответ без единой строки данных;
      malformed — формат выгрузки не соответствует ожиданиям.
    Все четыре отличаются от пятого состояния, «источник не обновился», при
    котором данные есть, но latest_event_date не сдвинулась, — его фиксирует
    проверка качества SOURCE_NOT_UPDATED. Смешивать состояния нельзя: чинятся
    они в разных местах.
    """
    status = status or ("missing" if raw is None else "error")
    msg = error or (raw or {}).get("error") or "выгрузка отсутствует"
    return {"available": False, "error": msg,
            "source": source_meta(name, (raw or {}).get("date"), None,
                                  p_start, p_end, None, None, filters or {}, status)}


def build_yandex(raw: dict | None, prev: dict | None, date: str) -> dict:
    w = (raw or {}).get("window") or {}
    if not raw or raw.get("error"):
        return source_unavailable("yandex_webmaster", raw, None,
                                  w.get("from"), w.get("to"))
    pq = raw.get("popular_queries") or {}
    # Частичная ошибка: сборщик кладёт {'error': ...} вместо среза. Прежде такой
    # срез давал пустой список запросов, и в письмо уходил честный на вид ноль
    # показов при available: true. Ошибка любого читаемого среза означает
    # «данных нет», а не «данные нулевые».
    partial = next((f"срез {k}: {v['error']}"
                    for k, v in (("popular_queries", pq),
                                 ("summary", raw.get("summary") or {}))
                    if isinstance(v, dict) and v.get("error")), None)
    if partial:
        return source_unavailable("yandex_webmaster", raw, partial,
                                  pq.get("date_from") or w.get("from"),
                                  pq.get("date_to") or w.get("to"))
    p_from, p_to = pq.get("date_from"), pq.get("date_to")
    prev_pq = (prev or {}).get("popular_queries", {})
    entities = []
    for it in pq.get("queries", []):
        ind = it.get("indicators", {})
        shows = ind.get("TOTAL_SHOWS")
        clicks = ind.get("TOTAL_CLICKS")
        pos = ind.get("AVG_SHOW_POSITION")
        text = it.get("query_text", "")
        entities.append({
            "search_engine": "yandex",
            "entity_type": "query",
            "entity_id": text,
            "impressions": int(shows) if shows is not None else None,
            "clicks": int(clicks) if clicks is not None else None,
            "ctr": (clicks / shows) if shows else None,
            "average_position": round(pos, 2) if pos is not None else None,
            "branded": is_branded(text),
            "intent": classify_intent(text),
            "sample_size": int(shows) if shows is not None else None,
            "confidence": confidence(int(shows) if shows is not None else None),
        })
    # «Пустой успех»: источник заявил count запросов, но не отдал ни одного.
    # Нулевая сумма по пустому списку читалась бы как измеренный ноль показов.
    # count == 0 при этом остаётся честным нулём: у хоста нет запросов.
    if not entities and (pq.get("count") or 0) > 0:
        return source_unavailable(
            "yandex_webmaster", raw,
            f"запросы заявлены источником (count={pq.get('count')}), но не получены",
            pq.get("date_from") or w.get("from"), pq.get("date_to") or w.get("to"),
            status="empty")
    impressions = sum(e["impressions"] or 0 for e in entities)
    clicks = sum(e["clicks"] or 0 for e in entities)
    in_top10 = [e for e in entities if e["average_position"] is not None
                and e["average_position"] <= THRESHOLDS["top_position"]]
    summary = raw.get("summary", {})
    sqi = summary.get("sqi")
    return {
        "available": True,
        "source": source_meta(
            "yandex_webmaster", raw.get("date"), p_to, p_from, p_to,
            prev_pq.get("date_from"), prev_pq.get("date_to"),
            {"scope": (f"{pq.get('fetched', len(entities))} из {pq.get('count', '?')} "
                       "запросов (API popular queries, постраничный забор)"),
             "region": "не задан в запросе", "device": "все"},
            "ok",
            "Клики/показы относятся к выборке топ-100 запросов, а не ко всему сайту."),
        "entities": entities,
        "totals": {
            "impressions": impressions,
            "clicks": clicks,
            "ctr": (clicks / impressions) if impressions else None,
            "queries_tracked": len(entities),
            "queries_position_le_10": len(in_top10),
            "queries_position_le_3": len([e for e in entities if e["average_position"] is not None
                                          and e["average_position"] <= 3.0]),
            "queries_available": pq.get("count"),
            "queries_fetched": pq.get("fetched", len(entities)),
            "scope_note": ("все запросы хоста" if pq.get("count") and
                           pq.get("fetched", 0) >= pq["count"]
                           else "выборка запросов, не весь сайт"),
        },
        "indexation": {
            "total_known_urls": (summary.get("searchable_pages_count") or 0)
                                + (summary.get("excluded_pages_count") or 0)
                                if summary.get("searchable_pages_count") is not None else None,
            "indexed_urls": summary.get("searchable_pages_count"),
            "excluded_urls": summary.get("excluded_pages_count"),
            "excluded_by_reason": None,
            "commercial_excluded_urls": None,
            "unclassified_excluded_urls": summary.get("excluded_pages_count"),
            "sqi": sqi,
            "site_problems": summary.get("site_problems"),
        },
    }


def calendar_series(rows: list[dict]) -> list[dict]:
    """Дневной ряд по календарю, а не по порядку строк ответа.

    Прежде неделя бралась срезом `daily[-7:]` по индексам строк. Это работало
    ровно до первого пропуска: GSC не возвращает дни без показов, а порядок
    строк определяется сортировкой по метрике, а не по дате. Как только у сайта
    появятся клики или день без показов, «последние семь строк» перестанут быть
    последними семью днями — и недельное сравнение сместится молча.

    Пропущенные даты добавляются нулями с признаком `measured: false`: ноль
    показов здесь именно измерен источником, но отличать его от строки с
    данными полезно при разборе.
    """
    if not rows:
        return []
    by_date = {r["keys"][0]: r for r in rows}
    start = dt.date.fromisoformat(min(by_date))
    end = dt.date.fromisoformat(max(by_date))
    out = []
    for i in range((end - start).days + 1):
        day = (start + dt.timedelta(days=i)).isoformat()
        r = by_date.get(day)
        out.append({
            "date": day,
            "impressions": r["impressions"] if r else 0,
            "clicks": r["clicks"] if r else 0,
            "position": round(r.get("position", 0), 2) if r else None,
            "measured": r is not None,
        })
    return out


def build_google(raw: dict | None, prev: dict | None) -> dict:
    if not raw or raw.get("error"):
        return source_unavailable("google_search_console", raw)
    a = raw.get("analytics", {})
    # Срез вернул ошибку вместо данных — источник недоступен, а не пуст.
    # Прежде источник закрывался, только когда ошибку вернули ВСЕ срезы; сбой
    # одного превращался в ноль: пустой date — в нулевую неделю, пустой
    # query — в «0 запросов» без единого предупреждения.
    failed = next((f"срез {k}: {v['error']}" for k, v in a.items()
                   if isinstance(v, dict) and "error" in v), None)
    if failed or not a:
        return source_unavailable("google_search_console", raw,
                                  failed or "ответ без блока analytics")
    rows = a.get("date", {}).get("rows", [])
    # «Пустой успех»: 200 без единой строки за 28 дней. Методика (проверка
    # API_ERROR_AS_ZERO) трактует такой ноль как отсутствие замера, а не как
    # измеренный ноль, — snapshot закрывает его до публикации нулей в письме.
    if not rows:
        return source_unavailable("google_search_console", raw,
                                  "ответ без ошибки и без строк за период",
                                  status="empty")
    daily = calendar_series(rows)
    latest = daily[-1]["date"] if daily else None
    last7, prev7 = daily[-7:], daily[-14:-7]
    entities = []
    for r in a.get("query", {}).get("rows", []):
        q = r["keys"][0]
        entities.append({
            "search_engine": "google", "entity_type": "query", "entity_id": q,
            "impressions": r["impressions"], "clicks": r["clicks"],
            "ctr": (r["clicks"] / r["impressions"]) if r["impressions"] else None,
            "average_position": round(r["position"], 2),
            "branded": is_branded(q), "intent": classify_intent(q),
            "sample_size": r["impressions"], "confidence": confidence(r["impressions"]),
        })
    pages = []
    for r in a.get("page", {}).get("rows", []):
        pages.append({
            "search_engine": "google", "entity_type": "page",
            "entity_id": r["keys"][0].replace("https://biz-soft.pro", "") or "/",
            "impressions": r["impressions"], "clicks": r["clicks"],
            "ctr": (r["clicks"] / r["impressions"]) if r["impressions"] else None,
            "average_position": round(r["position"], 2),
            "sample_size": r["impressions"], "confidence": confidence(r["impressions"]),
        })
    return {
        "available": True,
        "source": source_meta(
            "google_search_console", raw.get("date"), latest,
            daily[0]["date"] if daily else None, latest,
            prev7[0]["date"] if prev7 else None, prev7[-1]["date"] if prev7 else None,
            {"property": "sc-domain:biz-soft.pro", "search_type": "web"}, "ok",
            "Данные GSC отстают на 2–3 дня; последняя доступная дата события — "
            + str(latest)),
        "daily": daily,
        "entities": entities,
        "pages": pages,
        "totals": {
            "impressions_window": sum(d["impressions"] for d in daily),
            "clicks_window": sum(d["clicks"] for d in daily),
            "window_days": len(daily),
            "impressions_last7": sum(d["impressions"] for d in last7),
            "impressions_prev7": sum(d["impressions"] for d in prev7),
            # Длины окон: при молодой или отстающей выгрузке daily короче 14
            # дней, и «предыдущая неделя» — не неделя. Сравнение окон разной
            # длины не публикуется — по той же причине, что и у Яндекса
            # (WINDOW_LENGTH_MISMATCH).
            "last7_days": len(last7),
            "prev7_days": len(prev7),
            "last7_start": last7[0]["date"] if last7 else None,
            "last7_end": last7[-1]["date"] if last7 else None,
            "prev7_start": prev7[0]["date"] if prev7 else None,
            "prev7_end": prev7[-1]["date"] if prev7 else None,
            "queries_tracked": len(entities),
            "queries_position_le_10": len([e for e in entities if e["average_position"] <= THRESHOLDS["top_position"]]),
            "pages_position_le_10": len([p for p in pages if p["average_position"] <= THRESHOLDS["top_position"]]),
        },
    }


def metrika_partial_error(raw: dict) -> str | None:
    """Ошибка любого читаемого среза Метрики.

    Сборщик при HTTP-ошибке кладёт {'error': ...} вместо среза. Прежде разбор
    лез в metrika['traffic_sources']['data'] без проверки, получал KeyError —
    и в день частичного сбоя не собиралось ничего: ни снимок, ни письмо.
    """
    for key in ("traffic_sources", "organic_by_engine", "organic_landing_pages"):
        blk = raw.get(key)
        if not isinstance(blk, dict) or "data" not in blk:
            err = (blk.get("error") if isinstance(blk, dict) else None) or "срез отсутствует"
            return f"срез {key}: {err}"
    goals = raw.get("goals")
    if isinstance(goals, dict):     # при ошибке вместо списка целей лежит {'error': ...}
        return f"срез goals: {goals.get('error', 'срез отсутствует')}"
    # «Пустой успех»: итог заявляет визиты, а строк по источникам нет — из
    # такого среза органика посчиталась бы нулём при ненулевом трафике.
    ts_blk = raw["traffic_sources"]
    if not ts_blk.get("data") and ((ts_blk.get("totals") or [0])[0] or 0) > 0:
        return "срез traffic_sources: строки отсутствуют при ненулевом итоге визитов"
    return None


def ga4_partial_error(raw: dict) -> str | None:
    """Ошибка любого читаемого среза GA4.

    Прежде срез-ошибка проходил через .get('rows', []) как пустой список, и в
    письмо уходили sessions = 0 и organic = 0 при available: true — ошибка
    источника, выданная за измеренный ноль (REP-001).
    """
    for key in ("channels", "organic_sources", "organic_landing_pages"):
        blk = raw.get(key)
        if not isinstance(blk, dict) or blk.get("error"):
            err = (blk.get("error") if isinstance(blk, dict) else None) or "срез отсутствует"
            return f"срез {key}: {err}"
    # «Пустой успех» среза каналов: без единой строки сумма сессий стала бы
    # нулём при available: true. Пустые organic-срезы при этом допустимы:
    # отсутствие органических сессий — измеримый ноль.
    if not (raw.get("channels") or {}).get("rows"):
        return "срез channels: ответ без ошибки и без строк"
    return None


def build_analytics(metrika: dict | None, ga4: dict | None, date: str) -> dict:
    out = {"metrika": {"available": False}, "ga4": {"available": False}, "intra_day_revisions": []}
    m_err = (metrika_partial_error(metrika)
             if metrika and not metrika.get("error") else None)
    if not metrika or metrika.get("error") or m_err:
        w = (metrika or {}).get("window") or {}
        out["metrika"] = source_unavailable(
            "yandex_metrika", metrika, m_err, w.get("from"), w.get("to"),
            {"counter": (metrika or {}).get("counter")})
    else:
        ts = {r["dimensions"][0]["name"]: r["metrics"] for r in metrika["traffic_sources"]["data"]}
        tot = metrika["traffic_sources"].get("totals") or [None] * 5
        # Отсутствие строки органики в успешном срезе — измеренный ноль, а не
        # «нет данных»: Метрика не отдаёт строки по источникам без визитов.
        # None здесь показал бы «нет данных» при доказанном источником нуле.
        org = ts.get("Search engine traffic", [0, 0, 0, 0, 0])
        lp = [{"entity_id": r["dimensions"][0]["name"], "visits": r["metrics"][0],
               "bounce_rate": r["metrics"][1], "goal_events": r["metrics"][2]}
              for r in metrika["organic_landing_pages"]["data"]]
        w = metrika.get("window", {})
        out["metrika"] = {
            "available": True,
            "source": source_meta("yandex_metrika", metrika.get("date"), w.get("to"),
                                  w.get("from"), w.get("to"), None, None,
                                  {"counter": metrika.get("counter"), "accuracy": "full"}, "ok"),
            "metric_name": "visits (ym:s:visits)",
            "visits_total": tot[0], "users_total": tot[1],
            "goal_events_total": tot[4],
            "organic_visits": org[0], "organic_goal_events": org[4],
            "unique_goal_users": None,
            "qualified_leads": None, "deals": None, "revenue": None,
            # Кроме имени сохраняется идентификатор события из условий цели:
            # цели, заведённые 21.08.2026 через API, называются по-русски
            # («Отправлена заявка с формы»), а наш ключ (lead_sent) лежит в
            # conditions[].url. Сверка только по имени объявляла их
            # незаведёнными — ложный critical в каждом отчёте.
            "goals_configured": [
                {"id": g["id"], "name": g["name"], "type": g["type"],
                 "events": sorted({c.get("url") for c in (g.get("conditions") or [])
                                   if isinstance(c, dict) and c.get("url")})}
                for g in metrika.get("goals", [])],
            # Состав целевых событий органики по целям (вопрос руководителя
            # 01.09.2026): без него сумма нечитаема — в ней смешаны клик по
            # телефону и автоцель «поиск по сайту». Пишутся только цели с
            # ненулевыми достижениями, по убыванию.
            "goal_breakdown": _goal_breakdown(metrika),
            "organic_landing_pages": lp,
            "channels": {k: v[0] for k, v in ts.items()},
            # Органика в разбивке по поисковым системам (ym:s:lastSearchEngineRoot):
            # единственные данные, которыми клики Вебмастера сверяются с визитами
            # именно из Яндекса, а не со всей органикой сайта, включая Google.
            "organic_by_engine": {
                r["dimensions"][0]["name"]: r["metrics"][0]
                for r in metrika["organic_by_engine"]["data"]},
        }
        # Учёт пересборов внутри дня (несколько сборов => несколько значений)
        path = DATA_DIR / f"metrika-{date}.json"
        seen = []
        for sha in git_revisions(path, date):
            old = git_show_json(sha, path)
            if not old or old.get("error"):
                continue
            try:
                v = (old["traffic_sources"].get("totals") or [None])[0]
            except Exception:
                continue
            if v is not None and v not in seen:
                seen.append(v)
        if len(seen) > 1 or (seen and tot[0] is not None and float(tot[0]) not in [float(s) for s in seen]):
            values = sorted({float(v) for v in seen} | ({float(tot[0])} if tot[0] is not None else set()))
            out["intra_day_revisions"].append({
                "metric": "metrika.visits_total", "values_seen": values,
                "canonical": float(tot[0]) if tot[0] is not None else None,
                "reason": "источник пересобирался в течение дня; каноническим считается последний сбор",
            })
    g_err = ga4_partial_error(ga4) if ga4 and not ga4.get("error") else None
    if not ga4 or ga4.get("error") or g_err:
        w = (ga4 or {}).get("window") or {}
        out["ga4"] = source_unavailable(
            "ga4", ga4, g_err, w.get("from"), w.get("to"),
            {"property": (ga4 or {}).get("property")})
    else:
        ch = {r["dimensionValues"][0]["value"]: [x["value"] for x in r["metricValues"]]
              for r in ga4.get("channels", {}).get("rows", [])}
        org = ch.get("Organic Search", ["0", "0", "0"])
        w = ga4.get("window", {})
        # Свои визиты, которые GA4 засчитал в органический поиск. Считаются из
        # сырого среза источников, а не предполагаются.
        internal_names = ("metrika.yandex.ru", "webmaster.yandex.ru",
                          "direct.yandex.ru", "alice.yandex.ru")
        hits = [r for r in ga4.get("organic_sources", {}).get("rows", [])
                if r["dimensionValues"][0]["value"] in internal_names]
        internal = {
            "sources": [r["dimensionValues"][0]["value"] for r in hits],
            "sessions": sum(int(r["metricValues"][0]["value"]) for r in hits),
            "key_events": sum(float(r["metricValues"][1]["value"]) for r in hits),
        } if hits else None
        src_tz = ((ga4.get("channels") or {}).get("metadata") or {}).get("timeZone")
        lp = [{"entity_id": r["dimensionValues"][0]["value"],
               "sessions": int(r["metricValues"][0]["value"]),
               "key_events": int(r["metricValues"][1]["value"])}
              for r in ga4.get("organic_landing_pages", {}).get("rows", [])]
        out["ga4"] = {
            "available": True,
            "internal_in_organic": internal,
            "source_timezone": src_tz,
            "source": source_meta("ga4", ga4.get("date"), w.get("to"), w.get("from"),
                                  w.get("to"), None, None,
                                  {"property": ga4.get("property")}, "ok",
                                  "key events размечены 2026-08-18 — сравнение конверсий "
                                  "внутри периода некорректно"),
            "metric_name": "sessions (GA4)",
            "sessions_total": sum(int(v[0]) for v in ch.values()),
            "organic_sessions": int(org[0]),
            "organic_users": int(org[1]),
            "organic_key_events": int(org[2]),
            "key_events_marked_at": "2026-08-18",
            "channels": {k: int(v[0]) for k, v in ch.items()},
            "organic_sources": {r["dimensionValues"][0]["value"]: int(r["metricValues"][0]["value"])
                                for r in ga4.get("organic_sources", {}).get("rows", [])},
            "organic_landing_pages": lp,
        }
    return out


def build_safe(name: str, build, raw: dict | None, *args) -> dict:
    """MALFORMED-страховка: неожиданный формат выгрузки — «нет данных», а не
    падение всей сборки. Известные формы ошибок разобраны выше по коду; здесь
    ловится то, чего разбор не предвидел (сменившаяся схема ответа, обрезанный
    файл), — иначе один изменившийся источник снова лишал бы дня письма."""
    try:
        return build(raw, *args)
    except Exception as e:  # noqa: BLE001 — любой сбой разбора = недоступный источник
        return source_unavailable(
            name, raw if isinstance(raw, dict) else None,
            f"формат выгрузки не соответствует ожиданиям: {type(e).__name__}: {e}",
            status="malformed")


def build_analytics_safe(metrika: dict | None, ga4: dict | None, date: str) -> dict:
    """Та же страховка для составного блока аналитики."""
    try:
        return build_analytics(metrika, ga4, date)
    except Exception as e:  # noqa: BLE001
        reason = f"формат выгрузки не соответствует ожиданиям: {type(e).__name__}: {e}"
        return {
            "metrika": source_unavailable(
                "yandex_metrika", metrika if isinstance(metrika, dict) else None, reason,
                status="malformed"),
            "ga4": source_unavailable(
                "ga4", ga4 if isinstance(ga4, dict) else None, reason,
                status="malformed"),
            "intra_day_revisions": [],
        }


SEMANTICS_DIR = pathlib.Path("reports/seo/semantics")
DEMAND_STALE_DAYS = 45      # старше — замер считается устаревшим


def build_market_demand(date: str) -> dict:
    """Рыночный спрос из Вордстата — знаменатель для нашей видимости.

    Источник обновляется помесячно, поэтому в снимок дня попадает последний
    доступный замер с его собственной датой и возрастом. Суточной дельты у спроса
    нет и быть не может: сравнивать его день ко дню запрещено методикой.
    """
    briefs = sorted(SEMANTICS_DIR.glob("brief-*.json"))
    if not briefs:
        return {"available": False,
                "reason": "замер рыночного спроса ещё не собран",
                "comparable_to_visibility": False}
    brief = json.loads(briefs[-1].read_text(encoding="utf-8"))
    if "coverage" not in brief:
        # Замеры до 19.08.2026 собраны без фильтра релевантности: по транслитерациям
        # брендов в них попали омонимы («корал тревел», «пион корал шарм»).
        # Такой замер не используется — лучше отсутствие данных, чем чужие числа.
        return {"available": False,
                "reason": "замер собран до включения фильтра релевантности и не используется",
                "comparable_to_visibility": False}
    measured = brief.get("clusters_measured") or 0
    if not measured:
        return {"available": False,
                "reason": "замер начат, но ни один кластер ещё не собран",
                "measured_at": brief.get("report_date"),
                "coverage": brief.get("coverage"),
                "complete": brief.get("complete", False),
                "comparable_to_visibility": False}
    measured_at = brief.get("report_date")
    age = (dt.date.fromisoformat(date) - dt.date.fromisoformat(measured_at)).days
    gaps = brief.get("gaps") or {}
    return {
        "available": True,
        "source": {
            "source_name": "yandex_wordstat",
            "measured_at": measured_at,
            "age_days": age,
            "region": brief.get("region"),
            "unit": brief.get("unit"),
            "window": brief.get("window"),
            "match_type": brief.get("match_type"),
            "refresh": "помесячно",
        },
        "coverage": brief.get("coverage"),
        "complete": brief.get("complete", False),
        "stale": age > DEMAND_STALE_DAYS,
        "clusters_measured": measured,
        "clusters_planned": brief.get("clusters_planned"),
        "top_commercial": brief.get("top_commercial") or [],
        "gap_cards": len(gaps),
        "gap_phrases": sum(len(v) for v in gaps.values()),
        "gaps": gaps,
        "discovery": brief.get("discovery") or [],
        # Доля голоса не рассчитывается: наша видимость известна по выборке
        # топ-100 запросов Вебмастера, охват и периоды источников не сверены.
        "comparable_to_visibility": False,
    }


def build_experiments() -> list[dict]:
    p = pathlib.Path("reports/seo/intelligence/seo-experiments.json")
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8")).get("experiments", [])
    out = []
    for e in raw:
        out.append({
            "id": e.get("id"),
            "title": e.get("id"),
            "hypothesis": e.get("hypothesis"),
            "treatment_urls": e.get("pages", []),
            "control_urls": e.get("control_group"),
            "deployment_date": e.get("start"),
            "measurement_start_date": None,
            "status": e.get("status"),
            "primary_metric": e.get("success_metric"),
            "guardrail_metrics": ["impressions", "average_position", "organic_sessions"],
            "minimum_exposure": "не задан — требуется определить до объявления результата",
            "review_date": None,
            "owner": None,
            "result": None,
            "source": e.get("source"),
        })
    return out


def data_revisions_safe(date: str, prev_date: str) -> list[dict]:
    """Учёт пересборов — вспомогательный блок: его сбой не должен валить снимок."""
    try:
        return [r for r in [
            revisions_for("yandex", date, lambda d: d.get("summary", {}).get("searchable_pages_count"),
                          "yandex.indexed_urls"),
            revisions_for("yandex", prev_date, lambda d: d.get("summary", {}).get("searchable_pages_count"),
                          "yandex.indexed_urls (базовая линия предыдущего дня)"),
        ] if r]
    except Exception:  # noqa: BLE001
        return []


def prev_snapshot(date: str) -> dict | None:
    """Предыдущий snapshot: из файла, иначе собирается из сырых выгрузок за вчера.

    Единственная точка получения «вчера» для всего конвейера: и проверки
    качества, и письмо обязаны видеть один и тот же предыдущий снимок — иначе
    выводы «не обновился» и дельты считались бы от разных данных.
    """
    prev_date = (dt.date.fromisoformat(date) - dt.timedelta(days=1)).isoformat()
    p = OUT_DIR / f"{prev_date}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    yx_raw = load("yandex", prev_date)
    g_raw = load("gsc", prev_date)
    if not yx_raw and not g_raw:
        return None
    return {
        "report_date": prev_date,
        "yandex": build_safe("yandex_webmaster", build_yandex, yx_raw, None, prev_date),
        "google": build_safe("google_search_console", build_google, g_raw, None),
        "analytics": build_analytics_safe(load("metrika", prev_date),
                                          load("ga4", prev_date), prev_date),
    }


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(
        dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    prev_date = (dt.date.fromisoformat(date) - dt.timedelta(days=1)).isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    snap = {
        "schema_version": SCHEMA_VERSION,
        "report_date": date,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "reporting_timezone": TIMEZONE,
        "declared_goals": declared_goals(),
        "goal_levels": goal_levels(),
        "thresholds": THRESHOLDS,
        "yandex": build_safe("yandex_webmaster", build_yandex,
                             load("yandex", date), load("yandex", prev_date), date),
        "google": build_safe("google_search_console", build_google,
                             load("gsc", date), load("gsc", prev_date)),
        "analytics": build_analytics_safe(load("metrika", date), load("ga4", date), date),
        # Дневная факт-витрина: окна равной длины с фиксированным лагом,
        # построенные отчётом, а не источником. KPI и дельты письма считаются
        # отсюда; агрегатные блоки выше остаются для сущностей (запросы,
        # страницы), где дневные ряды не ведутся.
        "daily": daily_windows.build(date),
        "experiments": build_experiments(),
        "market_demand": build_market_demand(date),
        "data_revisions": data_revisions_safe(date, prev_date),
        "crm": {"connected": False, "qualified_leads": None, "deals": None, "revenue": None,
                "note": "CRM не подключена — квалифицированные лиды, сделки и выручка недоступны"},
        "ctr_model": {"approved": False,
                      "note": "утверждённая CTR-кривая по позициям отсутствует; "
                              "расчёт «потерянных кликов» не выполняется"},
    }
    out = OUT_DIR / f"{date}.json"
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"snapshot: {out} (schema {SCHEMA_VERSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
