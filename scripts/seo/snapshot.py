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
import leads as leads_mod
import passport
import technical

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
    # Обвал индекса: падение числа страниц в поиске Яндекса, которое нельзя
    # списать на дневное дрожание. 09.09.2026 индекс упал 650 → 455 (−30%), и
    # ни одна проверка этого не увидела: статус письма считался по показам, а
    # показы — окно за прошлые дни, которое об индексе сегодняшнего дня не
    # знает. Обычное дрожание тех же дней — 663 → 650, то есть −2%.
    "index_drop_share": 0.05,   # доля, ниже которой падение — дрожание
    "index_drop_pages": 20,     # и одновременно столько страниц минимум
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


# Ветка-хранилище машинных данных. История сырых выгрузок живёт только в ней:
# в рабочей копии (main) каталог reports/seo/data лежит в .gitignore, поэтому
# «git log -- <файл>» без ссылки на ветку не находит ни одного коммита.
DATA_BRANCH_REFS = ("origin/seo-data", "seo-data")


def data_branch_ref() -> str | None:
    """Первая существующая ссылка на ветку данных, иначе None."""
    for ref in DATA_BRANCH_REFS:
        try:
            ok = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref],
                                capture_output=True, text=True, timeout=10,
                                check=False).returncode == 0
        except Exception:  # noqa: BLE001
            return None
        if ok:
            return ref
    return None


def git_revisions(path: pathlib.Path, date: str) -> list[str]:
    """SHA коммитов, затронувших файл в указанный день (для учёта пересборов).

    Смотреть надо в ветку данных, а не в текущую. Прежняя редакция вызывала
    «git log -- reports/seo/data/<файл>» на рабочей копии main, где этот путь
    в .gitignore и истории не имеет: список всегда выходил пустым, и весь учёт
    пересборов (data_revisions, находки INTRA_DAY_REVISION и BASELINE_REVISED)
    не срабатывал ни разу. Цена промаха видна на 09.09.2026: выгрузка Яндекса
    собиралась дважды — в 04:47 UTC с 650 страницами в поиске и в 08:19 с 455,
    отчёт ушёл в 04:54 по первой, и о пересмотре никто не узнал.
    """
    ref = data_branch_ref()
    if not ref:
        return []
    try:
        out = subprocess.run(
            ["git", "log", "--format=%H %ad", "--date=short", ref, "--", str(path)],
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


def _direct_attribution(metrika: dict) -> dict | None:
    """Связка Метрика→Директ: визиты и ключевые цели по группам объявлений."""
    att = metrika.get("direct_attribution")
    if not isinstance(att, dict) or "error" in att or "rows" not in att:
        return None
    return {
        "dimension": att.get("dimension"),
        "goal_keys": att.get("goal_keys") or [],
        "rows": [{"name": r.get("name") or "—",
                  "visits": int(r.get("visits") or 0),
                  "goal_reaches_any": int(r.get("goal_reaches_any") or 0),
                  "leads": {k: int(v or 0)
                            for k, v in (r.get("leads") or {}).items()}}
                 for r in att["rows"]],
    }


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
    code = "no_file" if status == "missing" else "api_error"
    return {**passport.unavailable(code, source=name, detail=None if status == "missing" else msg),
            "error": msg,
            "source": source_meta(name, (raw or {}).get("date"), None,
                                  p_start, p_end, None, None, filters or {}, status)}


# INDEX-001. Статусы исключения Вебмастера, которые не являются проблемой
# сами по себе: адрес намеренно закрыт, переадресован или склеен.
EXPECTED_EXCLUSION_STATUSES = {
    "REDIRECT_SEARCH", "REDIRECT_NOTSEARCHABLE", "NOT_CANONICAL",
    "NOINDEX", "NOT_MAIN_MIRROR", "PARSER_ERROR_NOINDEX",
}
COMMERCIAL_PREFIXES = ("/product/", "/vendors/", "/solutions/", "/catalog")


def load_sitemap_paths(date: str) -> set[str] | None:
    """Пути живого sitemap из инвентаря (sitemap_inventory.py); None — нет выгрузки."""
    inv = load("sitemap", date)
    if not inv:
        files = sorted(DATA_DIR.glob("sitemap-*.json"))
        if not files:
            return None
        try:
            inv = json.loads(files[-1].read_text(encoding="utf-8"))
        except ValueError:
            return None
    return {u.get("path") for u in (inv.get("urls") or []) if u.get("path")}


def classify_excluded(events: dict | None, excluded_total: int | None,
                      date: str) -> dict:
    """Исключённые из поиска URL по причинам (INDEX-001).

    Источник — выборка событий поиска Вебмастера: у события «снят из
    поиска» есть статус исключения. Классификация трёхслойная: статус
    источника (переадресация, canonical, noindex — ожидаемо), присутствие
    адреса в живом sitemap (снятые карточки и закрытые по правилу каталога
    страницы в sitemap не входят — ожидаемо) и раздел сайта (карточка,
    вендор, решение, каталог — коммерчески значимо). Тревога — только
    коммерческий адрес из sitemap с неожиданным статусом.

    Без выборки (старое сырьё, ошибка среза) — прежние None: «причины
    неизвестны», а не «проблем нет».
    """
    none = {"excluded_by_reason": None, "commercial_excluded_urls": None,
            "unclassified_excluded_urls": excluded_total,
            "excluded_samples": None}
    if not isinstance(events, dict) or events.get("error"):
        return none
    samples = [s for s in (events.get("samples") or [])
               if isinstance(s, dict) and s.get("event") == "REMOVED_FROM_SEARCH"]
    if not samples:
        return none
    sitemap = load_sitemap_paths(date)
    by_reason: dict[str, int] = {}
    commercial, unexpected = [], []
    seen = set()
    for s in samples:
        url = s.get("url") or ""
        path = url.replace("https://biz-soft.pro", "").replace("http://biz-soft.pro", "") or "/"
        if path in seen:
            continue
        seen.add(path)
        status = s.get("excluded_url_status") or "UNKNOWN"
        by_reason[status] = by_reason.get(status, 0) + 1
        in_sitemap = (path in sitemap) if sitemap is not None else None
        is_commercial = path.startswith(COMMERCIAL_PREFIXES)
        expected = status in EXPECTED_EXCLUSION_STATUSES or in_sitemap is False
        if not expected:
            unexpected.append({"path": path, "status": status,
                               "event_date": s.get("event_date"),
                               "commercial": is_commercial})
            if is_commercial:
                commercial.append(path)
    classified = len(seen)
    return {
        "excluded_by_reason": dict(sorted(by_reason.items(), key=lambda kv: -kv[1])),
        "commercial_excluded_urls": len(commercial),
        "unclassified_excluded_urls": max(0, (excluded_total or 0) - classified)
        if excluded_total is not None else None,
        "excluded_samples": {
            "classified": classified,
            "window": {"from": events.get("date_from"), "to": events.get("date_to")},
            "sitemap_known": sitemap is not None,
            "unexpected": sorted(unexpected, key=lambda u: (not u["commercial"], u["path"]))[:50],
        },
    }


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
    # Ноль от API — это «ИКС не определён», а не индекс качества, равный нулю:
    # кабинет на том же хосте пишет «Недостаточно данных для определения ИКС»
    # (сверено 18.09.2026). Значение 0 в снимке прочиталось бы как измеренная
    # оценка и однажды попало бы в отчёт худшей из возможных цифрой.
    sqi = summary.get("sqi") or None
    return {
        "available": True,
        "source": source_meta(
            "yandex_webmaster", raw.get("date"), p_to, p_from, p_to,
            prev_pq.get("date_from"), prev_pq.get("date_to"),
            {"scope": (f"{pq.get('fetched', len(entities))} из {pq.get('count', '?')} "
                       "запросов (API popular queries, постраничный забор)"),
             "region": "не задан в запросе", "device": "все"},
            "ok",
            ("Клики/показы — по всем запросам хоста за окно источника (постраничный "
             "забор); KPI письма — из дневной витрины."
             if pq.get("count") and pq.get("fetched", 0) >= pq["count"] else
             "Клики/показы относятся к выборке запросов, а не ко всему сайту.")),
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
            "sqi": sqi,
            "site_problems": summary.get("site_problems"),
            **classify_excluded(raw.get("search_url_events"),
                                summary.get("excluded_pages_count"), date),
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


# Те же списки, что у сборщиков (collect.INTERNAL_SOURCES и
# collect.AI_ASSISTANT_SOURCES); повторены здесь, чтобы снимок не тянул
# модуль сбора с его зависимостями от секретов.
INTERNAL_SOURCES = ("metrika.yandex.ru", "webmaster.yandex.ru", "direct.yandex.ru")
AI_ASSISTANT_SOURCES = ("alice.yandex.ru",)


def _source_group(rows: list, names: tuple) -> dict | None:
    """Сессии и ключевые события GA4 по группе источников; None — нет строк."""
    hits = [r for r in rows if r["dimensionValues"][0]["value"] in names]
    if not hits:
        return None
    return {
        "sources": [r["dimensionValues"][0]["value"] for r in hits],
        "sessions": sum(int(r["metricValues"][0]["value"]) for r in hits),
        "key_events": sum(float(r["metricValues"][1]["value"]) for r in hits),
    }


def _goal_users(metrika: dict) -> tuple[dict | None, int | None]:
    """Уникальные посетители органики по конверсионным целям.

    Сборщик отдаёт разбивку по ключам целей (ym:s:goal<ID>users). Сумма по
    ключам — верхняя оценка уникальных: посетитель с двумя разными целями
    входит в обе. Пустая разбивка при заведённых целях — измеренный ноль.
    """
    raw = metrika.get("organic_goal_users")
    if not isinstance(raw, dict) or "error" in raw:
        return None, None
    by_key = {k: int(float(v or 0)) for k, v in raw.items()}
    return by_key, sum(by_key.values())


def build_analytics(metrika: dict | None, ga4: dict | None, date: str) -> dict:
    out = {"metrika": passport.unavailable("no_file", source="yandex_metrika"),
           "ga4": passport.unavailable("no_file", source="ga4"),
           "intra_day_revisions": []}
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
            # Уникальные посетители органики с конверсионной целью (решение
            # руководителя 03.09.2026): верхняя оценка суммой по целям,
            # разбивка рядом. None — сборщик не отдал срез (старое сырьё
            # или ошибка запроса).
            "unique_goal_users": _goal_users(metrika)[1],
            "goal_users_by_key": _goal_users(metrika)[0],
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
            # Этап B: рекламный трафик в разрезе групп Директа с достижениями
            # ключевых целей (см. collect.KEY_GOAL_EVENTS). None — связка не
            # собрана (ошибка или старое сырьё), пустой список — измеренный ноль.
            "direct_attribution": _direct_attribution(metrika),
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
        # Свои визиты, которые GA4 засчитал в органический поиск, считаются
        # из сырого среза источников, а не предполагаются. Алиса — отдельный
        # канал: переходы живых пользователей из ассистента и Нейро, не
        # выдача и не сотрудники (решение руководителя 03.09.2026).
        src_rows = ga4.get("organic_sources", {}).get("rows", [])
        internal = _source_group(src_rows, INTERNAL_SOURCES)
        ai_assistant = _source_group(src_rows, AI_ASSISTANT_SOURCES)
        src_tz = ((ga4.get("channels") or {}).get("metadata") or {}).get("timeZone")
        lp = [{"entity_id": r["dimensionValues"][0]["value"],
               "sessions": int(r["metricValues"][0]["value"]),
               "key_events": int(r["metricValues"][1]["value"])}
              for r in ga4.get("organic_landing_pages", {}).get("rows", [])]
        out["ga4"] = {
            "available": True,
            "internal_in_organic": internal,
            "ai_assistant_in_organic": ai_assistant,
            # Органика без своих визитов и без Алисы — тот же состав, что у
            # дневного ряда GA4 (collect_daily фильтрует те же источники);
            # именно по этим числам публикуется конверсия канала.
            "organic_sessions_clean": int(org[0]) - sum(
                (b or {}).get("sessions", 0) for b in (internal, ai_assistant)),
            "organic_key_events_clean": int(org[2]) - int(sum(
                (b or {}).get("key_events", 0) for b in (internal, ai_assistant))),
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
WORDSTAT_DIR = pathlib.Path("reports/seo/wordstat")
DEMAND_STATE = WORDSTAT_DIR / "intelligence-state.json"
DEMAND_STALE_DAYS = 45      # старше — замер считается устаревшим
DEMAND_FULL_CYCLE_DAYS = 31  # полный цикл Wordstat не старше месяца — замер полный


def _demand_from_state(date: str) -> dict | None:
    """Спрос из живого состояния исследования Wordstat (ветка seo-data).

    До 03.09.2026 снимок читал brief-2026-08-20.json из main — выжимку
    упразднённого gap-анализа, которая не обновлялась две недели и
    объявляла замер неполным (360 из 554 фраз), пока живое состояние
    исследования (23 тысячи фраз, 174 кластера, полный цикл ежедневно)
    лежало рядом и питало раздел «Спрос» веб-отчёта. Два раздела одного
    отчёта спорили о свежести одного источника.
    """
    if not DEMAND_STATE.exists():
        return None
    try:
        st = json.loads(DEMAND_STATE.read_text(encoding="utf-8"))
    except ValueError:
        return None
    cov, uni = st.get("coverage") or {}, st.get("universe") or {}
    measured_at = st.get("measured_at") or st.get("date")
    if not cov.get("available") or not measured_at:
        return None
    age = (dt.date.fromisoformat(date) - dt.date.fromisoformat(measured_at)).days
    full_dates = sorted(p.name[:10] for p in WORDSTAT_DIR.glob("*-full-result.json"))
    last_full = full_dates[-1] if full_dates else None
    full_age = ((dt.date.fromisoformat(date) - dt.date.fromisoformat(last_full)).days
                if last_full else None)
    complete = full_age is not None and full_age <= DEMAND_FULL_CYCLE_DAYS
    # Разрывы в форме прежней выжимки: кластер → фразы с частотностью, по
    # которым нас нет. Потребитель — блок возможностей (opportunity.py).
    gaps: dict[str, list] = {}
    top_commercial = []
    for o in st.get("opportunities") or []:
        cluster = o.get("cluster")
        if not cluster:
            continue
        top_commercial.append({"cluster": cluster, "page": o.get("url"),
                               "commercial_impressions": o.get("commercial_demand"),
                               "seed_impressions": None,
                               "gap": o.get("gap"), "gap_title": o.get("gap_title")})
        phrases = [{"phrase": p.get("phrase"), "impressions": p.get("frequency")}
                   for p in (o.get("top_phrases") or []) if p.get("phrase")]
        if phrases and not (o.get("indexed") and (o.get("impressions") or 0) > 0):
            gaps[cluster] = phrases
    return {
        "available": True,
        "source": {
            "source_name": "yandex_wordstat",
            "measured_at": measured_at,
            "age_days": age,
            "region": "Россия",
            "unit": "показы в поиске Яндекса",
            "window": "последние 30 дней",
            "match_type": "broad",
            "refresh": "полный цикл ежедневно",
            "last_full_cycle": last_full,
        },
        "coverage": (f"{uni.get('commercial_phrases')} коммерческих фраз из "
                     f"{uni.get('phrases')} в {uni.get('clusters')} кластерах"),
        "complete": complete,
        "status": "stale" if age > DEMAND_STALE_DAYS else "ok",
        "as_of": measured_at,
        "expected_as_of": (dt.date.fromisoformat(date)
                           - dt.timedelta(days=DEMAND_STALE_DAYS)).isoformat(),
        "stale": age > DEMAND_STALE_DAYS,
        "clusters_measured": uni.get("clusters"),
        "clusters_planned": uni.get("clusters"),
        "total_commercial_demand": cov.get("total_commercial_demand"),
        "coverage_levels": cov.get("levels"),
        "top_commercial": top_commercial,
        "gap_cards": len(gaps),
        "gap_phrases": sum(len(v) for v in gaps.values()),
        "gaps": gaps,
        "discovery": [],
        "comparable_to_visibility": False,
    }


def build_market_demand(date: str) -> dict:
    """Рыночный спрос из Вордстата — знаменатель для нашей видимости.

    Источник — живое состояние исследования Wordstat; старая выжимка
    gap-анализа остаётся запасным путём для сырья до 03.09.2026. Суточной
    дельты у спроса нет и быть не может: сравнивать его день ко дню
    запрещено методикой.
    """
    from_state = _demand_from_state(date)
    if from_state is not None:
        return from_state
    briefs = sorted(SEMANTICS_DIR.glob("brief-*.json"))
    if not briefs:
        return passport.unavailable("no_file", source="замер рыночного спроса",
                                    comparable_to_visibility=False)
    brief = json.loads(briefs[-1].read_text(encoding="utf-8"))
    if "coverage" not in brief:
        # Замеры до 19.08.2026 собраны без фильтра релевантности: по транслитерациям
        # брендов в них попали омонимы («корал тревел», «пион корал шарм»).
        # Такой замер не используется — лучше отсутствие данных, чем чужие числа.
        return passport.unavailable("excluded", source="замер рыночного спроса",
                                    detail="собран до включения фильтра релевантности",
                                    comparable_to_visibility=False)
    measured = brief.get("clusters_measured") or 0
    if not measured:
        return {**passport.unavailable("no_rows", source="замер рыночного спроса",
                                       detail="ни один кластер не собран"),
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
        "status": "stale" if age > DEMAND_STALE_DAYS else "ok",
        "as_of": measured_at,
        "expected_as_of": (dt.date.fromisoformat(date)
                           - dt.timedelta(days=DEMAND_STALE_DAYS)).isoformat(),
        "stale": age > DEMAND_STALE_DAYS,
        "clusters_measured": measured,
        "clusters_planned": brief.get("clusters_planned"),
        "top_commercial": brief.get("top_commercial") or [],
        "gap_cards": len(gaps),
        "gap_phrases": sum(len(v) for v in gaps.values()),
        "gaps": gaps,
        "discovery": brief.get("discovery") or [],
        # Доля голоса не рассчитывается: охват и периоды спроса и нашей
        # видимости не сверены.
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
            # Тикет и маркеры нужны радару возможностей: пока эксперимент
            # меряется, правка его страниц обнуляет замер, и предлагать её
            # нельзя. 09.09.2026 радар рекомендовал «переписать заголовок и
            # описание» по двум кластерам из трёх, оба под действующим опытом.
            "ticket": e.get("ticket"),
            "query_markers": e.get("query_markers") or [],
            "page_markers": e.get("page_markers") or [],
            "next_review": e.get("next_review"),
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


def load_leads(date: str) -> tuple[dict | None, str | None]:
    """Выгрузка заявок за дату, а при её отсутствии — последняя доступная.

    Сбор заявок идёт отдельным воркфлоу и по SSH: он падает по своим
    причинам (сервер, база, сеть), и терять из-за этого весь блок нельзя.
    Устаревшая выгрузка лучше пустоты — но только если письмо честно
    называет её дату, поэтому вместе с данными возвращается их день.
    """
    raw = load("leads", date)
    if raw is not None:
        return raw, date
    files = sorted(DATA_DIR.glob("leads-*.json"))
    files = [f for f in files if f.stem[len("leads-"):] < date]
    if not files:
        return None, None
    latest = files[-1]
    return json.loads(latest.read_text(encoding="utf-8")), latest.stem[len("leads-"):]


def build_crm(date: str) -> dict:
    """Коммерческий результат: заявки воронки и путь клиента к запросу.

    До 01.09.2026 блок был заглушкой «CRM не подключена»: заявки жили в
    Directus и в почте менеджера, а отчёт знал только целевые события
    Метрики — число, в котором смешаны клик по телефону и поиск по сайту.
    Теперь сюда приходит выгрузка воронки, и отчёт впервые может назвать
    канал каждой заявки. Сделки и выручка по-прежнему не измеряются: стадии
    воронки ведёт менеджер вручную, и брать их как факт рано.
    """
    try:
        raw, data_date = load_leads(date)
    except (ValueError, OSError) as e:
        # Битый или недописанный файл выгрузки — это отсутствие данных, а не
        # повод потерять письмо целиком.
        raw, data_date = None, None
        print(f"crm: выгрузка заявок не прочитана: {e}", file=sys.stderr)
    if raw is None:
        return {"connected": False, "qualified_leads": None, "deals": None,
                "revenue": None, "block": leads_mod.build(None, date),
                "note": "выгрузки заявок нет — "
                        "коммерческий результат не измеряется"}
    try:
        block = leads_mod.build(raw, date)
    except Exception as e:  # noqa: BLE001 — сменившаяся форма выгрузки = нет данных
        return {"connected": False, "qualified_leads": None, "deals": None,
                "revenue": None, "block": leads_mod.build(None, date),
                "note": f"выгрузка заявок не разобрана: {type(e).__name__}: {e}"}
    if data_date != date:
        # Флаг stale прежде жил только в снимке, и письмо его не читало:
        # карточка писала «полный подсчёт» по выгрузке, снятой до конца суток.
        block = leads_mod.mark_stale(block, data_date)
    return {
        "connected": True,
        "data_date": data_date,
        "stale": data_date != date,
        "collected_at": raw.get("collected_at"),
        # «Обращения», а не «квалифицированные лиды»: заявка попадает сюда в
        # момент отправки формы, до всякой квалификации. Поле сохраняет имя,
        # которое читает карточка показателя, но смысл назван в примечании.
        "qualified_leads": block.get("count"),
        "leads_week": block.get("week_count"),
        "amount_day": block.get("amount"),
        "deals": None,
        "revenue": None,
        "block": block,
        "note": "обращения — заявки воронки сайта; сделки и выручка "
                "не измеряются: стадии ведёт менеджер вручную",
    }


CTR_CURVE = pathlib.Path("data/seo/ctr-curve.json")


def build_ctr_model() -> dict:
    """Состояние кривой CTR: посчитана ли, утверждена ли, чем ограничена.

    Кривую считает scripts/seo/ctr_curve.py по непересекающимся окнам
    Вебмастера и кладёт в реестр. Утверждение — отдельное решение
    руководителя: кривая по своим данным описывает наш отклик, а не эталон,
    и утверждать её до того, как названа причина низкой кликабельности,
    значит закрепить аномалию как норму. Пока approved ложно, отчёт ведёт
    себя как прежде — «потерянные клики» не публикуются, — но говорит, что
    расчёт есть и чего ему недостаёт, вместо прежнего «кривой нет».
    """
    if not CTR_CURVE.exists():
        return {"approved": False,
                "note": "утверждённая CTR-кривая по позициям отсутствует; "
                        "расчёт «потерянных кликов» не выполняется"}
    try:
        curve = json.loads(CTR_CURVE.read_text(encoding="utf-8"))
    except ValueError as e:
        return {"approved": False,
                "note": f"реестр кривой CTR не читается: {e}"}
    points = curve.get("points") or []
    usable = [p for p in points if p.get("usable")]
    coverage = curve.get("coverage") or {}
    approved = bool(curve.get("approved"))
    return {
        "approved": approved,
        "computed": True,
        "coverage": coverage,
        "buckets_total": len(points),
        "buckets_usable": len(usable),
        "curve": points if approved else None,
        "note": ("кривая утверждена: расчёт недобора кликов ведётся по ней"
                 if approved else
                 "кривая посчитана по своим данным, но не утверждена; "
                 "расчёт «потерянных кликов» не выполняется"),
    }


def build_technical(date: str) -> dict:
    """Блок PageSpeed. Любой сбой разбора — «данных нет», а не падение снимка.

    Технический замер полезен, но письмо руководителя не может от него
    зависеть: сторонний API недоступен чаще, чем собственные выгрузки.
    """
    try:
        return technical.build(date)
    except Exception as e:  # noqa: BLE001 — источник сторонний, форма может смениться
        return {**passport.unavailable(
            "parse_error", source="замер PageSpeed",
            detail=f"{type(e).__name__}: {e}"), "level": "unknown"}


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
        "crm": build_crm(date),
        # Техническое здоровье: PageSpeed по представителям шаблонов. Сбой
        # замера не должен ломать снимок — блок сам возвращает состояние
        # «данных нет» с датой последнего удачного замера.
        "technical": build_technical(date),
        "ctr_model": build_ctr_model(),
    }
    out = OUT_DIR / f"{date}.json"
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"snapshot: {out} (schema {SCHEMA_VERSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
