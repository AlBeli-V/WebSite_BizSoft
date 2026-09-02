"""Занятость страницы действующим экспериментом базового SEO-контура.

Зачем модуль появился (правка 1.7.0). Разбор плана работ 02.09.2026 показал
дефект, который не видел ни один из прежних контуров контроля: пакет работ
выдавался в очередь по странице, о которой базовый SEO-контур в тот же день
вёл собственный эксперимент. Из 24 пакетов дня шесть указывали на страницы,
где 01–02.09 уже была внесена правка сниппета или заводилась статья кластера,
и ещё четыре — на кластеры, которые чужой эксперимент держит контрольной
группой до 16.09.

Последствие двойное и в обе стороны плохое:

  * чужой эксперимент теряет оценку — на странице оказывается две правки в
    одном окне наблюдения, и разделить их вклад нечем;
  * наш эксперимент теряет оценку ровно так же — «эффект» правки контура
    окажется суммой с чужой правкой, внесённой днём раньше.

Проект уже знает эту ошибку и один раз её обошёл вручную: CorelDRAW не взяли
в SEO-EXP-004, «чтобы не смешивать два изменения на одной странице» — правку
отложили до вердикта по SEO-EXP-001. Модуль превращает это разовое решение в
правило, которое соблюдается само.

Источник — реестр экспериментов базового контура, читается так же, как срезы
выдачи: `git show origin/seo-data:<путь>`, только на чтение, ничего не
пишем (раздел 2.2 методики — правило неповторной закупки и независимости
контуров).

Различаются две степени занятости, и они намеренно ведут к разным решениям:

  ЗАНЯТА     — страница прямо перечислена в `pages` действующего эксперимента.
               Это запрет: пакет выводится из очереди до контрольной точки.
  КОНТРОЛЬ   — кластер страницы назван контрольной группой чужого
               эксперимента. Это не запрет, а условие: ограничение чужого
               эксперимента цитируется дословно, решение принимает человек.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401

SEO_BRANCH = "seo-data"
REGISTRY = "reports/seo/intelligence/seo-experiments.json"

BUSY_PAGE = "занята"
BUSY_CONTROL = "контрольная группа"

# Состояния реестра, при которых эксперимент ещё меряет. `decided` означает,
# что решение принято и страница освободилась — ровно так базовый контур
# поступил с /vendors/coreldraw 02.09.2026.
LIVE_STATES = {"running", "observing", "watch"}


def _registry_raw(branch: str = SEO_BRANCH) -> str:
    try:
        return subprocess.run(
            ["git", "show", f"origin/{branch}:{REGISTRY}"],
            capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, OSError):
        return ""


def load(branch: str = SEO_BRANCH) -> list[dict]:
    """Действующие эксперименты базового контура. Нет реестра — пустой список.

    Отсутствие реестра не превращается в «занятых нет»: вызывающий код
    отличает пустой ответ от несостоявшегося чтения по флагу `available`.
    """
    raw = _registry_raw(branch)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [e for e in (data.get("experiments") or [])
            if (e.get("status") or "").lower() in LIVE_STATES]


def available(branch: str = SEO_BRANCH) -> bool:
    """Удалось ли прочитать реестр вообще."""
    return bool(_registry_raw(branch))


def _path_of(url: str) -> str:
    return re.sub(r"^https?://[^/]+", "", url or "").rstrip("/") or "/"


def _checkpoint(experiment: dict) -> str:
    """Дата, до которой страница занята, — из метрики успеха или окна.

    В реестре контрольная точка записана человеком в тексте `success_metric`
    («контрольная точка 16.09.2026»), отдельного поля под неё нет. Берём
    последнюю дату из текста: раньше неё эксперимент не закрывается.
    """
    text = " ".join(str(experiment.get(k) or "")
                    for k in ("success_metric", "control_group"))
    dates = re.findall(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if not dates:
        return ""
    day, month, year = max(dates, key=lambda d: (d[2], d[1], d[0]))
    return f"{year}-{month}-{day}"


def _control_clusters(experiment: dict) -> list[str]:
    """Кластеры, которые эксперимент держит контрольной группой.

    Машиночитаемое поле `control_clusters` — основной источник. Если его нет,
    имена вытаскиваются из текстового `control_group`: там они перечислены
    через запятую после слова «кластеры». Формулировка «остальные
    vendor-страницы без изменений» имён не содержит и в контроль никого не
    записывает — это правильно: такой контроль назван общо, и запрещать по
    нему работу со всеми страницами сайта было бы подменой смысла.
    """
    named = experiment.get("control_clusters")
    if isinstance(named, list) and named:
        return [str(n).lower() for n in named]
    text = experiment.get("control_group") or ""
    match = re.search(r"кластер\w*\s+([^—\.;]+)", text)
    if not match:
        return []
    return [part.strip().lower() for part in match.group(1).split(",")
            if part.strip() and " " not in part.strip().strip(".")]


def find(url: str, subject: str, experiments: list[dict]) -> dict | None:
    """Кто занял страницу или её кластер. None — свободна.

    Приоритет у прямой занятости страницей: она запрещает работу, тогда как
    контрольная группа только ставит условие.
    """
    path = _path_of(url)
    subject_norm = (subject or "").strip().lower()
    control_hit: dict | None = None
    for experiment in experiments:
        pages = [_path_of(p) for p in (experiment.get("pages") or [])]
        if path in pages:
            return {
                "степень": BUSY_PAGE,
                "эксперимент": experiment.get("id", ""),
                "заявка": experiment.get("ticket", ""),
                "начат": experiment.get("start", ""),
                "до": _checkpoint(experiment),
                "почему": (f"страница входит в действующий эксперимент "
                           f"базового SEO-контура «{experiment.get('id')}» "
                           f"(начат {experiment.get('start')}): вторая правка "
                           f"в том же окне лишит оценки оба эксперимента"),
                "ограничение": experiment.get("success_metric", ""),
            }
        if control_hit is None and subject_norm and \
                subject_norm in _control_clusters(experiment):
            control_hit = {
                "степень": BUSY_CONTROL,
                "эксперимент": experiment.get("id", ""),
                "заявка": experiment.get("ticket", ""),
                "начат": experiment.get("start", ""),
                "до": _checkpoint(experiment),
                "почему": (f"кластер «{subject}» — контрольная группа "
                           f"эксперимента «{experiment.get('id')}»: работа по "
                           f"нему меняет то, с чем сравнивают результат"),
                "ограничение": experiment.get("control_group", ""),
            }
    return control_hit


def mark(packages: list[dict], experiments: list[dict] | None = None
         ) -> tuple[list[dict], list[dict]]:
    """Делит пакеты на свободные и занятые, проставляя пометку занятости.

    Возвращает (свободные, занятые). Пакеты в контрольной группе остаются
    свободными: у них только пометка, потому что ограничение чужого
    эксперимента может и не касаться нашей правки — читать его и решать
    должен человек.
    """
    live = load() if experiments is None else experiments
    free: list[dict] = []
    busy: list[dict] = []
    for package in packages:
        hit = find(package.get("url", ""), package.get("subject", ""), live)
        if hit is None:
            free.append(package)
            continue
        package["занятость"] = hit
        (busy if hit["степень"] == BUSY_PAGE else free).append(package)
    return free, busy
