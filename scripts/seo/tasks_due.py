#!/usr/bin/env python3
"""Созревшие тикеты: что пора делать сегодня и что этого ждёт.

Тикеты `reports/seo/tasks/*.md` в проекте есть давно, но их никто не читает:
письмо и веб-отчёт дают на папку ссылку, и всё. Тикет с пометкой «после 06.10»
пролежит там ровно столько, сколько о нём помнят. Этот слой закрывает разрыв —
он превращает срок в событие.

Дисциплина тишины сохраняется: пока ничего не созрело, вывода нет и возврат 1.
Пишет в журнал только вызывающий workflow и только когда есть что сказать.

Заголовок тикета читается по двум полям (остальное — свободный текст):

    **Статус:** queued · **Созревает:** 2026-10-06 · **Ждёт:** MONEY-A1

`Созревает` — дата, с которой задача выполнима. `Ждёт` — эксперимент или тикет,
без которого её делать нельзя; поле информационное, срок задаёт дату.

Второй режим — `--unmanaged`. Слой видит только тикеты со сроком, и это его
слабое место: тикет, у которого момент запуска записан прозой («через 7 дней
после деплоя», «после мержа волны 1»), для него не существует. Ровно это и
случилось 08.09.2026 — семь тикетов GIDX-*, заведённых в тот же день соседней
веткой, держат срок в тексте. Аудит показывает такие тикеты, чтобы владелец
проставил дату; сам он даты не выдумывает.

Запуск: python3 scripts/seo/tasks_due.py [--date YYYY-MM-DD] [--all|--unmanaged]
Возврат: 0 — есть что показать; 1 — нет (это не ошибка).
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sys

TASKS = pathlib.Path("reports/seo/tasks")

RE_TITLE = re.compile(r"^#\s+(\S+)\s+—\s+(.+)$", re.M)
RE_FIELD = re.compile(r"\*\*(Приоритет|Статус|Созревает|Ждёт|Заведено):\*\*\s*"
                      r"([^·\n*]+)")
# Статусы, при которых тикет ещё ждёт работы. Список закрытый и полный по
# фактическим статусам папки: «approved» и «implemented» тоже означают
# незакрытую работу — у первого решение принято, но не применено, у второго код
# выкачен, но результат не снят. Считать их закрытыми значило бы прятать ровно
# те тикеты, у которых всё готово к следующему шагу.
# Не ждут работы: done, confirmed, decided, deferred, closed, on hold.
OPEN_STATES = ("queued", "open", "waiting", "proposed", "in_progress", "running",
               "approved", "implemented")


def parse(path: pathlib.Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    head = text.split("\n## ", 1)[0]
    title = RE_TITLE.search(text)
    if not title:
        return None
    fields = {k: v.strip() for k, v in RE_FIELD.findall(head)}
    due = fields.get("Созревает")
    try:
        due_date = dt.date.fromisoformat(due) if due else None
    except ValueError:
        due_date = None
    status = (fields.get("Статус") or "").strip()
    return {"id": title.group(1), "title": title.group(2).strip(),
            "file": str(path), "priority": fields.get("Приоритет", "—"),
            "status": status,
            "status_open": any(status.startswith(s) for s in OPEN_STATES),
            "due": due_date, "due_raw": due,
            "waits_for": fields.get("Ждёт")}


def collect(root: pathlib.Path = TASKS) -> list[dict]:
    rows = [parse(p) for p in sorted(root.glob("*.md"))]
    return [r for r in rows if r]


def ripe(rows: list[dict], today: dt.date, window: int = 3) -> list[dict]:
    """Тикеты, созревшие в последние `window` дней и ещё не закрытые.

    Не «все просроченные»: иначе запись в журнал повторялась бы каждый день,
    пока тикет не закроют, и «созрело» перестало бы читаться как событие. Окно
    в несколько дней нужно ровно затем, чтобы один упавший прогон не проглотил
    созревание; дальше тикет замолкает сам, даже если его не закрыли.

    Тикеты без срока не возвращаются никогда: их ведут иначе, и включать их
    сюда значило бы каждый день печатать один и тот же список.
    """
    earliest = today - dt.timedelta(days=max(window - 1, 0))
    out = [r for r in rows
           if r["due"] and earliest <= r["due"] <= today and r["status_open"]]
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    out.sort(key=lambda r: (order.get(r["priority"].split()[0], 9), r["due"]))
    return out


def unmanaged(rows: list[dict]) -> list[dict]:
    """Открытые тикеты без даты созревания.

    Такой тикет слой не покажет никогда, поэтому его судьба зависит от памяти
    людей — то есть от того, ради чего слой и заводился. Аудит не решает за
    владельца, когда задача созреет: он только называет тикеты, у которых
    момент запуска не переведён в дату.
    """
    out = [r for r in rows if r["status_open"] and not r["due"]]
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    out.sort(key=lambda r: order.get(r["priority"].split()[0], 9))
    return out


def render_unmanaged(rows: list[dict]) -> str:
    lines = [f"Открытых тикетов без даты созревания: {len(rows)}",
             "Пока даты нет, слой созревания их не покажет — срок держится "
             "только памятью.", ""]
    for r in rows:
        lines.append(f"[{r['priority']}] {r['id']} — {r['title']}")
        lines.append(f"    статус {r['status']}; {r['file']}")
    return "\n".join(lines)


def render(rows: list[dict], today: dt.date) -> str:
    lines = [f"Созрело тикетов к {today.isoformat()}: {len(rows)}", ""]
    for r in rows:
        wait = f", ждал {r['waits_for']}" if r["waits_for"] else ""
        lines.append(f"[{r['priority']}] {r['id']} — {r['title']}")
        lines.append(f"    срок {r['due_raw']}{wait}; статус {r['status']}")
        lines.append(f"    {r['file']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--tasks", type=pathlib.Path, default=TASKS)
    ap.add_argument("--all", action="store_true",
                    help="показать все тикеты со сроком, включая будущие")
    ap.add_argument("--unmanaged", action="store_true",
                    help="открытые тикеты без даты созревания — их слой не видит")
    ap.add_argument("--window", type=int, default=3,
                    help="сколько дней назад считать созревание событием")
    args = ap.parse_args()
    today = dt.date.fromisoformat(args.date)
    rows = collect(args.tasks)
    if args.all:
        dated = sorted((r for r in rows if r["due"]), key=lambda r: r["due"])
        for r in dated:
            mark = "созрел" if r["due"] <= today else f"через {(r['due'] - today).days} дн."
            print(f"[{r['priority']}] {r['due_raw']} {mark:14} {r['id']} — {r['title']}")
        return 0
    if args.unmanaged:
        rows_u = unmanaged(rows)
        if not rows_u:
            return 1
        print(render_unmanaged(rows_u))
        return 0
    due = ripe(rows, today, args.window)
    if not due:
        return 1
    print(render(due, today))
    return 0


if __name__ == "__main__":
    sys.exit(main())
