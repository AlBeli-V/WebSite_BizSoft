"""Журнал экспериментов: что предложили, что внедрили, что из этого вышло.

Зачем (Phase 5 задания, поручение руководителя 01.09.2026). Контур ежедневно
выдаёт поручения, но до сих пор ничего не знал об их судьбе: предложенное
вчера предлагалось снова сегодня, а вопрос «какие правки вообще работают»
оставался без ответа. Журнал закрывает три дыры сразу:

  * **мораторий** — внедрённая правка выводит страницу из очереди поручений на
    срок наблюдения, иначе система будет требовать переделать только что
    сделанное и мешать измерению;
  * **измеримость** — по каждому эксперименту хранится база «до», и результат
    считается по тем же запросам, а не по общему впечатлению;
  * **обучение** — накопленные исходы группируются по типу действия, и через
    несколько десятков наблюдений видно, что даёт эффект, а что нет.

Состояния и переходы (обратных нет, кроме отмены):

    предложен ──внедрение подтверждено──▶ наблюдение ──окно истекло──▶ оценён
        │
        └── страница выпала из поля / пакет неактуален ──▶ отменён

**Внедрение не отмечается руками.** Признак — появление на странице тех самых
фраз, которых там не было в момент предложения. Отметка «сделано» от человека
означала бы «человек считает, что сделал», а нам нужно «на странице это есть».
Заодно это снимает с руководителя лишний ритуал: он правит страницу, а система
сама замечает правку.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402

JOURNAL_PATH = os.path.join(paths.DATA_DIR, "experiments", "journal.json")

STATE_PROPOSED = "предложен"
STATE_WATCH = "наблюдение"
STATE_DONE = "оценён"
STATE_CANCELLED = "отменён"

VERDICT_BETTER = "улучшение"
VERDICT_FLAT = "без изменений"
VERDICT_WORSE = "ухудшение"

# Позиция, которой заменяется отсутствие в ТОП-20. Без такой замены страница,
# вылетевшая из выдачи, просто исчезала бы из расчёта и эксперимент выглядел
# бы успешнее, чем есть: считались бы только те запросы, где нам повезло.
OUT_OF_TOP = 21

# Степени раскрытия по возрастанию: требование выполнено, когда достигнутая
# степень не ниже требуемой.
COVER_ORDER = {"нет": 0, "в тексте": 1, "в заголовке": 2}


@dataclass
class Experiment:
    id: str
    created: str
    url: str
    page_kind: str
    package_id: str
    queries: list[str] = field(default_factory=list)
    # Требования к странице на момент предложения: фраза и нужная степень
    # раскрытия. Степень обязательна: «вынести фразу в заголовок» и «дописать
    # фразу в текст» — разные работы, и первая не считается выполненной от
    # того, что фраза уже была в тексте абзацем ниже. На этом контур один раз
    # уже ошибся, засчитав внедрение там, где ничего не меняли.
    requirements: list[dict] = field(default_factory=list)
    action_kinds: list[str] = field(default_factory=list)
    hypothesis: str = ""
    state: str = STATE_PROPOSED
    baseline: dict = field(default_factory=dict)
    implemented_at: str = ""
    implementation_note: str = ""
    watch_until: str = ""
    outcome: dict = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)

    def log(self, when: str, note: str) -> None:
        self.history.append({"дата": when, "событие": note})


def _to_dict(exp: Experiment) -> dict:
    data = asdict(exp)
    return {
        "id": data["id"],
        "создан": data["created"],
        "url": data["url"],
        "тип_страницы": data["page_kind"],
        "пакет": data["package_id"],
        "запросы": data["queries"],
        "требования": data["requirements"],
        "типы_действий": data["action_kinds"],
        "гипотеза": data["hypothesis"],
        "состояние": data["state"],
        "база": data["baseline"],
        "внедрён": data["implemented_at"],
        "подтверждение_внедрения": data["implementation_note"],
        "наблюдение_до": data["watch_until"],
        "итог": data["outcome"],
        "история": data["history"],
    }


def _from_dict(raw: dict) -> Experiment:
    return Experiment(
        id=raw.get("id", ""),
        created=raw.get("создан", ""),
        url=raw.get("url", ""),
        page_kind=raw.get("тип_страницы", ""),
        package_id=raw.get("пакет", ""),
        queries=raw.get("запросы") or [],
        requirements=raw.get("требования") or [],
        action_kinds=raw.get("типы_действий") or [],
        hypothesis=raw.get("гипотеза", ""),
        state=raw.get("состояние", STATE_PROPOSED),
        baseline=raw.get("база") or {},
        implemented_at=raw.get("внедрён", ""),
        implementation_note=raw.get("подтверждение_внедрения", ""),
        watch_until=raw.get("наблюдение_до", ""),
        outcome=raw.get("итог") or {},
        history=raw.get("история") or [],
    )


def load(path: str | None = None) -> list[Experiment]:
    path = path or JOURNAL_PATH
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        try:
            raw = json.load(fh)
        except json.JSONDecodeError:
            return []
    return [_from_dict(item) for item in raw.get("эксперименты", [])]


def save(experiments: list[Experiment], path: str | None = None) -> str:
    path = path or JOURNAL_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "_смысл": ("журнал экспериментов контура конкурентной разведки: "
                   "предложение → внедрение → наблюдение → оценка. Внедрение "
                   "фиксируется по появлению фраз на странице, а не по отметке "
                   "человека"),
        "обновлён": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "всего": len(experiments),
        "эксперименты": [_to_dict(e) for e in experiments],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return path


def next_id(experiments: list[Experiment]) -> str:
    numbers = [int(e.id.split("-")[-1]) for e in experiments
               if e.id.startswith("EXP-") and e.id.split("-")[-1].isdigit()]
    return f"EXP-{(max(numbers) + 1) if numbers else 1:04d}"


def active_by_url(experiments: list[Experiment]) -> dict[str, Experiment]:
    """Незакрытые эксперименты по адресу страницы: один адрес — один опыт.

    Два параллельных эксперимента на одной странице неразличимы по результату:
    непонятно, какая из правок сдвинула позиции.
    """
    return {e.url: e for e in experiments
            if e.state in (STATE_PROPOSED, STATE_WATCH)}


def add_days(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()
