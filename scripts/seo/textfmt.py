#!/usr/bin/env python3
"""Форматирование чисел и согласование слов — письмо читает человек."""

from __future__ import annotations


def num(v, dash: str = "нет данных") -> str:
    if v is None:
        return dash
    return f"{int(v):,}".replace(",", " ")


def signed(v, dash: str = "нет данных") -> str:
    if v is None:
        return dash
    return f"{int(v):+d}".replace("-", "−")


def pct(v, digits: int = 1, dash: str = "нет данных") -> str:
    if v is None:
        return dash
    return f"{v * 100:.{digits}f}".replace(".", ",") + "%"


def signed_pct(v, digits: int = 1, dash: str = "") -> str:
    if v is None:
        return dash
    s = f"{v * 100:+.{digits}f}".replace(".", ",").replace("-", "−")
    return s + "%"


def plural(n, one: str, few: str, many: str) -> str:
    n = abs(int(n or 0))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def counted(n, one: str, few: str, many: str) -> str:
    return f"{num(n)} {plural(n, one, few, many)}"


def ru_date(iso: str | None) -> str:
    if not iso:
        return "нет данных"
    return f"{iso[8:10]}.{iso[5:7]}"


def ru_date_full(iso: str | None) -> str:
    if not iso:
        return "нет данных"
    return f"{iso[8:10]}.{iso[5:7]}.{iso[0:4]}"
