#!/usr/bin/env python3
"""Разбор маркера отправки письма: «<дата> [sha256] [счётчик]».

Маркер отвечает на один вопрос: письмо за эту дату уже ушло или нет. Формат
у контуров разный — у ежедневного отчёта одна дата, у конкурентной разведки с
04.09.2026 три поля (дата, хэш письма, счётчик отправок за дату). Сравнение
маркера с датой целой строкой поэтому работало только у отчёта, а у разведки
не совпадало никогда: 16.09.2026 руководитель получил четыре письма подряд —
каждый прогон считал, что письма ещё не было.

Разбор вынесен в скрипт, а не оставлен строкой в YAML: у shell-строки внутри
workflow нет тестов, и ровно поэтому расхождение форматов прожило двенадцать
дней незамеченным.

    python3 scripts/ops/mail_marker.py sent --date 2026-09-16 --marker "<строка>"

Код возврата: 0 — письмо за дату уже отправлено, 1 — ещё нет. Хэш письма
сравнивается, только если он задан и в маркере, и аргументом: другой хэш —
это другое письмо того же дня, то есть уточнение, а не дубль.
"""

from __future__ import annotations

import argparse
import sys


def parse(marker: str) -> dict:
    """Поля маркера. Пустая строка и мусор дают пустую запись, а не отказ."""
    parts = (marker or "").split()
    out = {"date": "", "hash": "", "count": 0}
    if parts:
        out["date"] = parts[0]
    if len(parts) > 1:
        out["hash"] = parts[1]
    if len(parts) > 2:
        try:
            out["count"] = int(parts[2])
        except ValueError:
            out["count"] = 0
    return out


def already_sent(marker: str, date: str, letter_hash: str = "") -> bool:
    """Ушло ли письмо за эту дату — и то же ли это письмо."""
    m = parse(marker)
    if not m["date"] or m["date"] != date:
        return False
    if letter_hash and m["hash"] and letter_hash != m["hash"]:
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=("sent", "fields"))
    ap.add_argument("--date", required=True)
    ap.add_argument("--marker", default="")
    ap.add_argument("--hash", default="")
    args = ap.parse_args()

    m = parse(args.marker)
    if args.command == "fields":
        print(f"date={m['date']} hash={m['hash']} count={m['count']}")
        return 0

    if already_sent(args.marker, args.date, args.hash):
        print(f"письмо за {args.date} уже отправлено (отправок: {m['count'] or 1})")
        return 0
    print(f"письма за {args.date} ещё не было" if m["date"] != args.date
          else f"за {args.date} отправлено другое письмо — это уточнение")
    return 1


if __name__ == "__main__":
    sys.exit(main())
