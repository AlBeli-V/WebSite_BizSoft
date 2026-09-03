"""Барьер против утверждений без срока годности в тексте отчётов.

Письмо Growth Intelligence две недели печатало «переобход не запрашивался —
инструмент ждёт токена с правами Вебмастера»: фраза была зашита в код и
не зависела от данных. Аудит 03.09.2026 нашёл около 150 мест того же рода
во всех отчётных контурах: даты, имена секретов, суммы, квоты, обещания
«следующий шаг», «этап B», «появится после первого прогона», «Сейчас 10:45».
Общее у них одно: текст утверждает то, чего код не измерял, и ничто не
роняет сборку, когда утверждение перестаёт быть правдой.

Проверка проходит по строковым литералам отчётных слоёв (docstring и
комментарии не считаются — их руководитель не читает) и по промптам
Routine. Каждое совпадение обязано быть либо убрано, либо записано в
data/reports/literal-allowlist.json с причиной и датой valid_until:
просроченная запись роняет тест так же, как и новая находка. Неиспользуемая
запись тоже роняет — список не должен зарастать.

Отчёт без падения: python3 scripts/seo/tests/test_report_literals.py --report
"""
from __future__ import annotations

import ast
import datetime as dt
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
ALLOWLIST = ROOT / "data" / "reports" / "literal-allowlist.json"

# Отчётные слои: то, что превращается в письмо, веб-отчёт, запись в журнал
# или инструкцию Routine. Тесты и фикстуры исключены.
PY_SCOPES = [
    ("scripts/seo", ["*.py"]),
    ("scripts/seo/wordstat", ["*.py"]),
    ("scripts/ppc", ["*.py"]),
    ("competitive-intelligence", ["run_daily.py"]),
    ("competitive-intelligence/mailer", ["*.py"]),
    ("competitive-intelligence/reports", ["*.py"]),
    ("competitive-intelligence/decision_engine", ["*.py"]),
    ("competitive-intelligence/attack_engine", ["*.py"]),
    ("competitive-intelligence/discovery", ["*.py"]),
    ("competitive-intelligence/scoring", ["*.py"]),
    ("competitive-intelligence/experiments", ["*.py"]),
]
TEXT_SCOPES = [
    ("ops/routines/prompts", ["*.md"]),
]
# В воркфлоу проверяются только строки, которые уходят в журнал или письмо.
YML_LINE_RE = re.compile(r"^\s*(echo\s|print\(|.*\.append\(f?['\"]|body:)")

# Классы утверждений без срока годности. Регулярные выражения намеренно
# узкие: лучше пропустить спорное, чем зашуметь список исключений.
# Сообщения вида «SMTP_PASS не задан», напечатанные после проверки секрета,
# сюда не входят: код это действительно проверил. Ловятся утверждения, которые
# из данных не выводятся никогда: дата в тексте, обещание («появится после»,
# «следующий шаг», «подготовлю», «этап B»), «ждёт токена», «Сейчас 10:45»,
# «ещё не собран/накоплен/запущен» там, где код знает лишь «файла нет»,
# сумма в рублях и квота числом.
RULES = {
    "DATE": re.compile(r"\b\d{2}\.\d{2}\.20\d{2}\b|\b20\d{2}-\d{2}-\d{2}\b"),
    "PROMISE": re.compile(
        r"появится после|появится со|после первого|следующий шаг|\bэтап [AB]\b"
        r"|подготовлю|не запрашивался|только начинается|ждёт токена|ждём токена"
        r"|восстановлени\w+ .{0,20}токена|Сейчас \d{1,2}:\d{2}",
        re.IGNORECASE),
    "NOTYET": re.compile(
        r"ещё не (?:накоп|собран|запущен|выполн|измер|очист|провер|попал|разлож"
        r"|внесен|истек|доведён|покрыва|был[аио]? )",
        re.IGNORECASE),
    "MONEY": re.compile(r"(?<![{\w.,])\d[\d ]*\s?(?:₽|руб\.)"),
    "QUOTA": re.compile(r"квот[аыеу]\s+\d|\b\d+\s*(?:URL|запрос\w*)\s+в\s+(?:сутки|час|день|месяц)\b",
                        re.IGNORECASE),
}
PATH_LIKE = re.compile(r"\S*/\S*|\S+\.(?:md|json|yml|py|html)\b")


CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


def python_literals(path: pathlib.Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    skip = _docstring_ids(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            if len(node.value.strip()) >= 4:
                yield node.lineno, node.value


def text_lines(path: pathlib.Path):
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        yield n, line


def yml_report_lines(path: pathlib.Path):
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if YML_LINE_RE.match(line):
            yield n, line


def scan() -> list[dict]:
    hits = []

    def check(rel: str, lineno: int, text: str):
        # Литерал без русских букв — ключ, путь или имя переменной, а не
        # фраза для руководителя: os.environ["YANDEX_METRIKA_TOKEN"] не
        # утверждение о токене.
        if not CYRILLIC.search(text):
            return
        for code, rx in RULES.items():
            for m in rx.finditer(text):
                if code == "DATE" and any(m.group(0) in w for w in PATH_LIKE.findall(text)):
                    continue        # дата внутри имени файла или пути
                hits.append({"file": rel, "line": lineno, "code": code,
                             "match": m.group(0), "text": text.strip()[:160]})

    for base, globs in PY_SCOPES:
        for g in globs:
            for p in sorted((ROOT / base).glob(g)):
                if "tests" in p.parts:
                    continue
                for lineno, value in python_literals(p):
                    check(p.relative_to(ROOT).as_posix(), lineno, value)
    for base, globs in TEXT_SCOPES:
        for g in globs:
            for p in sorted((ROOT / base).glob(g)):
                for lineno, line in text_lines(p):
                    check(p.relative_to(ROOT).as_posix(), lineno, line)
    for p in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for lineno, line in yml_report_lines(p):
            check(p.relative_to(ROOT).as_posix(), lineno, line)
    return hits


def load_allowlist() -> list[dict]:
    if not ALLOWLIST.exists():
        return []
    return json.loads(ALLOWLIST.read_text(encoding="utf-8"))["entries"]


def _applies(entry: dict, hit: dict) -> bool:
    if entry["file"] != hit["file"]:
        return False
    if entry.get("code") and entry["code"] != hit["code"]:
        return False
    needle = entry["match"]
    return needle in hit["match"] or needle in hit["text"]


def evaluate(hits: list[dict], allowlist: list[dict], today: dt.date):
    """(новые находки, просроченные записи, неиспользуемые записи)."""
    used = [False] * len(allowlist)
    fresh = []
    for h in hits:
        covered = False
        for i, e in enumerate(allowlist):
            if _applies(e, h):
                used[i] = True
                covered = True
        if not covered:
            fresh.append(h)
    expired = [e for e in allowlist if dt.date.fromisoformat(e["valid_until"]) < today]
    unused = [e for i, e in enumerate(allowlist) if not used[i]]
    return fresh, expired, unused


def _fmt(h: dict) -> str:
    return f"{h['file']}:{h['line']} [{h['code']}] «{h['match']}» — {h['text']}"


class TestReportLiterals(unittest.TestCase):
    def test_allowlist_is_well_formed(self):
        for e in load_allowlist():
            for key in ("file", "match", "reason", "valid_until"):
                self.assertIn(key, e, e)
            dt.date.fromisoformat(e["valid_until"])
            self.assertTrue((ROOT / e["file"]).exists(), e["file"])

    def test_no_unexpired_claims_outside_allowlist(self):
        fresh, expired, unused = evaluate(scan(), load_allowlist(), dt.date.today())
        problems = []
        if fresh:
            problems.append("Новые утверждения без срока годности (убрать или занести в "
                            "data/reports/literal-allowlist.json с valid_until):\n  "
                            + "\n  ".join(_fmt(h) for h in fresh))
        if expired:
            problems.append("Просроченные исключения (срок valid_until вышел, текст всё ещё "
                            "в коде):\n  " + "\n  ".join(
                                f"{e['file']} «{e['match']}» до {e['valid_until']}: {e['reason']}"
                                for e in expired))
        if unused:
            problems.append("Исключения, которым больше ничего не соответствует (удалить):\n  "
                            + "\n  ".join(f"{e['file']} «{e['match']}»" for e in unused))
        self.assertFalse(problems, "\n\n".join(problems))


if __name__ == "__main__":
    if "--report" in sys.argv:
        hits = scan()
        fresh, expired, unused = evaluate(hits, load_allowlist(), dt.date.today())
        by_file: dict[str, list] = {}
        for h in fresh:
            by_file.setdefault(h["file"], []).append(h)
        for f, hs in sorted(by_file.items()):
            print(f"\n{f} ({len(hs)})")
            for h in hs:
                print(f"  {h['line']:>5} [{h['code']}] «{h['match']}» — {h['text'][:110]}")
        print(f"\nвсего находок {len(hits)}, новых {len(fresh)}, просрочено {len(expired)}, "
              f"неиспользуемых {len(unused)}")
        sys.exit(0)
    unittest.main()
