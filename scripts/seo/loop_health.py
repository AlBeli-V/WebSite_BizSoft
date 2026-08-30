#!/usr/bin/env python3
"""Loop-health: подтверждение, что контуры Growth Engine реально отработали.

Письмо не должно верить конвейеру на слово. Каждый контур подтверждается
артефактом с датой (файл выгрузки, снимок, маркер отправки), а не фактом
наличия кода или расписания: расписания GitHub Actions недетерминированы
(инцидент 27.08.2026 — шесть часов без запусков по всему репозиторию),
и «должно было запуститься» ничего не доказывает.

Контур с просрочкой попадает строкой в блок «Здоровье данных» письма и
таблицей в веб-отчёт; сам реестр хранится в seo-data.

Запуск: python3 scripts/seo/loop_health.py [YYYY-MM-DD]
Результат: reports/seo/intelligence/loop-health.json
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys

BASE = pathlib.Path("reports/seo")
OUT = BASE / "intelligence" / "loop-health.json"

# Сколько дней назад искать последний артефакт: дальше «последний прогон»
# не интересен — контур в любом случае давно просрочен.
LOOKBACK_DAYS = 14

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _dates_from_names(paths) -> str | None:
    """Последняя дата из имён файлов вида *-YYYY-MM-DD.* или YYYY-MM-DD.*"""
    dates = []
    for p in paths:
        m = DATE_RE.search(p.name)
        if m:
            dates.append(m.group(1))
    return max(dates) if dates else None


def _last_collect(date: dt.date) -> str | None:
    return _dates_from_names((BASE / "data").glob("*-2*.json")
                             if (BASE / "data").exists() else [])


def _last_gsc_pairs(date: dt.date) -> str | None:
    """Последний день, когда пары «запрос × страница» собраны без ошибки."""
    for back in range(LOOKBACK_DAYS + 1):
        d = (date - dt.timedelta(days=back)).isoformat()
        p = BASE / "data" / f"gsc-{d}.json"
        if not p.exists():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        pairs = raw.get("pairs")
        if isinstance(pairs, dict) and not pairs.get("error") \
                and "rows" in pairs:
            return d
    return None


def _last_wordstat(date: dt.date) -> str | None:
    wd = BASE / "wordstat"
    return _dates_from_names(wd.glob("*-demand-report.md") if wd.exists() else [])


def _last_snapshot(date: dt.date) -> str | None:
    d = BASE / "intelligence" / "snapshots"
    return _dates_from_names(d.glob("2*.json") if d.exists() else [])


def _last_quality(date: dt.date) -> str | None:
    d = BASE / "intelligence" / "data-quality"
    return _dates_from_names(d.glob("2*.json") if d.exists() else [])


def _last_report(date: dt.date) -> str | None:
    return _dates_from_names((BASE / "intelligence").glob("2*-v4.html"))


def _last_mailed(date: dt.date) -> str | None:
    p = BASE / "intelligence" / "last-mailed.txt"
    if not p.exists():
        return None
    m = DATE_RE.search(p.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def _last_direct(date: dt.date) -> str | None:
    p = BASE / "ppc" / "direct-stats.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    days = [r.get("Date") for r in data.get("groups") or [] if r.get("Date")]
    return max(days) if days else None


def _last_weekday(d: dt.date) -> dt.date:
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def _expected(cadence: str, date: dt.date) -> dt.date:
    """Самая старая дата артефакта, при которой контур считается отработавшим.

    daily        — артефакт за сегодня (контур идёт до сборки письма);
    daily-lag1   — за вчера (письмо и его отправка проверяются на следующий
                   день: сегодняшнее письмо в момент проверки ещё строится);
    weekdays-lag1 — данные за день перед последним будним запуском
                   (Директ собирается по будням и отдаёт вчерашний день).
    """
    if cadence == "daily":
        return date
    if cadence == "daily-lag1":
        return date - dt.timedelta(days=1)
    if cadence == "weekdays-lag1":
        return _last_weekday(date) - dt.timedelta(days=1)
    raise ValueError(f"неизвестная каденция: {cadence}")


# Контуры конвейера. required=False — контур ещё не обязан был запуститься
# ни разу (новый сенсор): без единого артефакта он «ожидает первого прогона»,
# а не «просрочен».
CONTOURS = [
    {"id": "collect", "label": "Сбор GSC/Вебмастер/Метрика/GA4",
     "cadence": "daily", "cadence_label": "ежедневно 06:07 МСК",
     "last": _last_collect, "required": True},
    {"id": "gsc-pairs", "label": "Пары запрос×страница (GSC)",
     "cadence": "daily", "cadence_label": "ежедневно, в сборе GSC",
     "last": _last_gsc_pairs, "required": False},
    {"id": "wordstat", "label": "Разведка спроса (Вордстат)",
     "cadence": "daily", "cadence_label": "ежедневно 04:20 МСК",
     "last": _last_wordstat, "required": True},
    {"id": "snapshot", "label": "Канонический снимок дня",
     "cadence": "daily", "cadence_label": "ежедневно 09:00 МСК",
     "last": _last_snapshot, "required": True},
    {"id": "quality", "label": "Проверки качества данных",
     "cadence": "daily", "cadence_label": "ежедневно 09:00 МСК",
     "last": _last_quality, "required": True},
    {"id": "report", "label": "Сборка письма V4",
     "cadence": "daily-lag1", "cadence_label": "ежедневно 09:00 МСК",
     "last": _last_report, "required": True},
    {"id": "email", "label": "Отправка письма руководителю",
     "cadence": "daily-lag1", "cadence_label": "ежедневно ~09:30 МСК",
     "last": _last_mailed, "required": True},
    {"id": "direct", "label": "Статистика Яндекс.Директа",
     "cadence": "weekdays-lag1", "cadence_label": "будни 07:10 МСК",
     "last": _last_direct, "required": True},
]


def build(date_s: str) -> dict:
    date = dt.date.fromisoformat(date_s)
    rows, overdue = [], []
    for c in CONTOURS:
        last = c["last"](date)
        expected = _expected(c["cadence"], date)
        if last is None:
            is_over = c["required"]
            row = {"id": c["id"], "label": c["label"],
                   "cadence": c["cadence_label"],
                   "last_run": None, "expected_since": expected.isoformat(),
                   "overdue": is_over, "days_late": None,
                   "note": ("артефактов контура не найдено" if c["required"]
                            else "ожидает первого прогона")}
        else:
            late = (expected - dt.date.fromisoformat(last)).days
            is_over = late > 0
            row = {"id": c["id"], "label": c["label"],
                   "cadence": c["cadence_label"],
                   "last_run": last, "expected_since": expected.isoformat(),
                   "overdue": is_over, "days_late": max(late, 0),
                   "note": None}
        rows.append(row)
        if row["overdue"]:
            overdue.append(c["id"])
    return {
        "date": date_s,
        "generated_at": dt.datetime.now(dt.timezone.utc)
                          .isoformat(timespec="seconds"),
        "contours": rows,
        "overdue": overdue,
        "ok_count": len(rows) - len(overdue),
        "total": len(rows),
        "available": True,
    }


def write(date_s: str) -> dict:
    res = build(date_s)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return res


def main() -> int:
    date_s = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(
        dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    res = write(date_s)
    for r in res["contours"]:
        mark = "ПРОСРОЧЕН" if r["overdue"] else "ок"
        print(f"  [{mark:>9}] {r['label']}: последний прогон "
              f"{r['last_run'] or '—'}, ожидается не старше {r['expected_since']}")
    print(f"loop-health: {res['ok_count']}/{res['total']} контуров в срок -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
