"""Паспорт блока данных: статус, дата данных и код причины.

Аудит 03.09.2026 (docs/ops/report-integrity-audit-2026-09-03.md) нашёл один
и тот же механизм во всех отчётных контурах: загрузчик возвращает «нет», а
текст в ветке else называет причину, которую код не проверял — «ждёт
токена», «ещё не накоплен», «после первого прогона». Паспорт закрывает
этот механизм контрактом:

* недоступный блок обязан нести `reason_code` из перечня REASONS, а его
  текст `reason` берётся из словаря по коду — свободной формулировки
  причины в коде больше нет;
* `detail` и `source` — только машинные подробности (имя источника, дата,
  регион, число), не причина;
* доступный блок несёт `as_of` — дату данных, отдельную от даты отчёта;
  если производитель знает, какой даты он ждал (`expected_as_of`), и данные
  старше, он обязан поставить `stale: True`.

Правило одной строкой: код не различает причину — текст её не называет.
Проверка контракта — `check_block`/`check_freshness`; их вызывает
invariants.py как блокирующие правила письма.
"""
from __future__ import annotations

# Код причины → текст для читателя. Только то, что код действительно
# установил. Порядок важен для чтения, не для логики.
REASONS: dict[str, str] = {
    "no_file": "пригодного файла источника за окно нет",
    "no_rows": "источник отдал пустой ответ",
    "no_match": "в данных нет записей по этому объекту",
    "parse_error": "файл источника не разобран",
    "api_error": "запрос к источнику завершился ошибкой",
    "no_previous": "предыдущего замера для сравнения нет",
    "no_signal": "данных меньше порога для вывода",
    "not_measured": "измерение не выполняется",
    "unsupported": "источник не отдаёт этот разрез",
    "excluded": "данные исключены правилом методики",
}

# Статус блока по коду причины. missing — нечего читать; empty — прочитано,
# но пусто; error — сломано; not_measured — так задумано.
STATUS_OF: dict[str, str] = {
    "no_file": "missing", "no_previous": "missing",
    "no_rows": "empty", "no_match": "empty", "no_signal": "empty",
    "parse_error": "error", "api_error": "error",
    "not_measured": "not_measured", "unsupported": "not_measured",
    "excluded": "not_measured",
}

STATUSES = frozenset({"ok", "stale", *STATUS_OF.values()})


def unavailable(code: str, *, source: str | None = None,
                detail: str | None = None, **fields) -> dict:
    """Недоступный блок с причиной из словаря.

    source — что именно не прочиталось («витрина Директа»), detail —
    машинная подробность («окно 7 дней», «регион 213»). Ни то, ни другое
    не объясняет, почему: объяснение — только код.
    """
    if code not in REASONS:
        raise ValueError(f"неизвестный код причины: {code}")
    text = REASONS[code]
    if source:
        text += f": {source}"
    if detail:
        text += f" ({detail})"
    return {"available": False, "status": STATUS_OF[code],
            "reason_code": code, "reason": text, **fields}


def flag(ok: bool, code: str, *, source: str | None = None,
         detail: str | None = None) -> dict:
    """Поля доступности по факту: пусто — с кодом причины, иначе ok.

    Для блоков, которые собирают список и считают себя доступными, когда
    в нём что-то есть: {**passport.flag(bool(items), "no_signal"), ...}.
    """
    if ok:
        return {"available": True, "status": "ok"}
    return unavailable(code, source=source, detail=detail)


def available(as_of: str | None, *, expected_as_of: str | None = None,
              **fields) -> dict:
    """Доступный блок с датой данных; устаревание считается от ожидаемой даты."""
    stale = bool(as_of and expected_as_of and as_of < expected_as_of)
    out = {"available": True, "status": "stale" if stale else "ok",
           "as_of": as_of, **fields}
    if expected_as_of:
        out["expected_as_of"] = expected_as_of
    if stale:
        out["stale"] = True
    return out


def normalize(block: dict | None, *, default_code: str = "no_rows",
              source: str | None = None) -> dict:
    """Довести блок из внешнего файла до контракта.

    Данные в ветках-хранилищах собраны старым кодом и кода причины не несут;
    падать на них письмо не должно, но и печатать чужую формулировку — тоже.
    """
    if not block:
        return unavailable("no_file", source=source)
    if block.get("available"):
        return block
    if block.get("reason_code") in REASONS:
        return block
    out = dict(block)
    out.update(unavailable(default_code, source=source))
    return out


def check_block(block: dict, path: str = "") -> list[str]:
    """Нарушения контракта у одного блока; пустой список — блок в порядке."""
    v: list[str] = []
    where = path or "блок"
    if not block.get("available"):
        code = block.get("reason_code")
        if code not in REASONS:
            v.append(f"{where}: недоступен без кода причины")
            return v
        reason = block.get("reason") or ""
        if not reason.startswith(REASONS[code]):
            v.append(f"{where}: текст причины не из словаря «{reason}»")
    return v


def check_freshness(block: dict, path: str = "") -> list[str]:
    """Данные старше ожидаемых обязаны быть помечены stale — и наоборот."""
    v: list[str] = []
    where = path or "блок"
    if not block.get("available"):
        return v
    as_of, expected = block.get("as_of"), block.get("expected_as_of")
    if as_of and expected:
        older = as_of < expected
        if older and not block.get("stale"):
            v.append(f"{where}: данные за {as_of} при ожидаемых {expected} без пометки stale")
        if block.get("stale") and not older:
            v.append(f"{where}: пометка stale при данных за {as_of} не старше {expected}")
    elif block.get("stale") and not as_of:
        v.append(f"{where}: пометка stale без даты данных as_of")
    return v


def walk(node, path: str = "blocks"):
    """Все словари с ключом available внутри структуры письма, с путём."""
    if isinstance(node, dict):
        if "available" in node:
            yield path, node
        for k, val in node.items():
            if isinstance(val, (dict, list)):
                yield from walk(val, f"{path}.{k}")
    elif isinstance(node, list):
        for i, val in enumerate(node):
            if isinstance(val, (dict, list)):
                yield from walk(val, f"{path}[{i}]")


def check_all(blocks: dict) -> list[str]:
    """Контракт и свежесть по всем блокам письма."""
    v: list[str] = []
    for path, block in walk(blocks):
        v += check_block(block, path)
        v += check_freshness(block, path)
    return v
