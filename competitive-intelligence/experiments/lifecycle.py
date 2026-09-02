"""Жизненный цикл эксперимента: внедрение, мораторий, оценка эффекта.

Три вопроса, на которые отвечает модуль, и почему они решены именно так.

**1. Как узнать, что правка сделана?** По странице, а не по отметке человека.
В момент предложения система запомнила фразы, которых на странице не было.
Если они появились — работа выполнена, и это проверяемый факт. Отметка
«сделано» руками означала бы «человек считает, что сделал»; нам нужно «на
странице это есть».

**2. Зачем мораторий.** Сразу после правки страница выводится из очереди
поручений на срок наблюдения. Иначе система на следующее же утро потребует
доработать только что доработанное, а измерение эффекта станет невозможным:
непонятно, какая из двух правок сдвинула позиции. Срок — параметр конфига;
по умолчанию две недели: этого хватает на переиндексацию и на шесть
сравнимых замеров, которых требует сглаживание 3×3.

**3. Как отделить эффект правки от движения выдачи.** Разностью разностей.
Считается изменение позиций по запросам эксперимента и — за тот же период —
изменение по всем прочим запросам ядра, где мы ничего не трогали. Эффектом
считается разница между ними. Без контрольной группы любой общий сдвиг
выдачи (сезонность, апдейт алгоритма, уход конкурента) записывался бы в
заслугу правки, и обучение системы строилось бы на выдуманных победах.

Оговорка, которая остаётся в отчёте всегда: это наблюдение, а не
доказательство. Мы не ставим A/B-тест на поисковой выдаче и не можем
исключить, что на позиции повлияло что-то ещё.
"""
from __future__ import annotations

import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401
from attack_engine import page_audit  # noqa: E402
from experiments import journal as jr  # noqa: E402

# Тип страницы по адресу: нужен, чтобы отличить правку одной страницы от
# правки шаблона, которая задевает все страницы своего типа.
KIND_BY_PREFIX = {"/vendors/": "vendor", "/product/": "product",
                  "/blog/": "blog"}
SCOPE_PAGE = "страница"
SCOPE_KIND = "тип страниц"
# Сколько соседних страниц того же типа проверяем, чтобы понять, правка была
# точечной или шаблонной.
PEERS_TO_CHECK = 3

# Значения по умолчанию; конфиг может их переопределить.
WATCH_DAYS = 14
WINDOW = 3                 # сколько дней усредняем на каждом конце
EFFECT_THRESHOLD = 1.0     # позиций, меньше — считаем шумом
# Какая доля требований должна быть выполнена, чтобы признать внедрение.
# Единица недостижима: правка редко закрывает все формулировки сразу, и
# ожидание стопроцентного совпадения означало бы, что внедрение не будет
# зафиксировано никогда. Одна фраза из десяти внедрением тоже не является.
IMPLEMENTED_RATIO = 0.5
MIN_QUERIES_CONFIDENT = 3  # меньше — вывод помечается предварительным


def settings(config: dict | None = None) -> dict:
    block = ((config or {}).get("эксперименты") or {})
    return {
        "окно_наблюдения_дней": int(block.get("окно_наблюдения_дней", WATCH_DAYS)),
        "окно_усреднения": int(block.get("окно_усреднения", WINDOW)),
        "порог_эффекта_позиций": float(block.get("порог_эффекта_позиций",
                                                 EFFECT_THRESHOLD)),
        "минимум_запросов": int(block.get("минимум_запросов_для_уверенности",
                                          MIN_QUERIES_CONFIDENT)),
        "порог_внедрения": float(block.get("порог_внедрения", IMPLEMENTED_RATIO)),
    }


def kind_of_url(url: str) -> str:
    """Тип страницы по её адресу. Неизвестный адрес типа не имеет."""
    path = (url or "").replace("https://biz-soft.pro", "")
    for prefix, kind in KIND_BY_PREFIX.items():
        if path.startswith(prefix):
            return kind
    return ""


def conditions_of(snapshot: dict) -> dict:
    """Условия, в которых снят замер: чем и по какому полю считали.

    Хранится вместе с базой эксперимента. Методика может измениться между
    базой и оценкой — тогда сравнение «было → стало» перестаёт быть
    сравнением одной линейкой, и отчёт обязан это показать, а не молча
    выдать разницу.
    """
    meta = snapshot.get("метаданные") or {}
    return {
        "версия_методики": meta.get("версия_методики"),
        "хеш_конфига": meta.get("хеш_конфига"),
        "ядро_хеш": meta.get("ядро_хеш"),
        "ядро_версия": meta.get("ядро_версия"),
    }


def comparability(base: dict, now: dict) -> tuple[str, str]:
    """Сравнимы ли условия базы и текущего замера.

    Возвращает (оценка, пояснение). «Полная» — считали одинаково. «Ограничена»
    — что-то поменялось, и разницу нельзя целиком относить на счёт правки.
    """
    if not base:
        return "неизвестна", "условия базы не сохранялись"
    отличия = []
    if base.get("хеш_конфига") != now.get("хеш_конфига"):
        отличия.append(f"конфигурация модели ({base.get('хеш_конфига')} → "
                       f"{now.get('хеш_конфига')})")
    if base.get("версия_методики") != now.get("версия_методики"):
        отличия.append(f"версия методики ({base.get('версия_методики')} → "
                       f"{now.get('версия_методики')})")
    if base.get("ядро_хеш") != now.get("ядро_хеш"):
        отличия.append("состав ядра запросов")
    if not отличия:
        return "полная", "база и замер получены одной моделью на одном ядре"
    return "ограничена", (
        "между базой и замером изменилось: " + "; ".join(отличия)
        + ". Позиции измеряются одинаково в любой версии, поэтому сравнение "
          "остаётся осмысленным, но приписывать всю разницу правке нельзя")


def positions_on(snapshot: dict, queries) -> dict[str, int]:
    """Позиции BIZSoft по запросам в конкретном дне.

    Отсутствие в ТОП-20 — не «нет данных», а позиция хуже двадцатой: запрос
    измерялся, нас там не нашли. Поэтому подставляется 21, иначе выпадение из
    выдачи улучшало бы среднее.
    """
    per_query = snapshot.get("по_запросам") or {}
    result = {}
    for query in queries:
        key = page_audit.normalize(query)
        bucket = per_query.get(key)
        if bucket is None:
            continue
        # Снимки до 01.09.2026 позиций не хранили. Отсутствие самого поля —
        # это «не измеряли», а не «нас там не было»: подставлять сюда 21
        # значит уверять, что до правки страница была вне выдачи, и любой
        # эксперимент показал бы улучшение на ровном месте.
        if "позиция" not in bucket:
            continue
        result[query] = bucket["позиция"] or jr.OUT_OF_TOP
    return result


def _median_positions(snapshots: dict, dates: list[str], queries) -> float | None:
    """Медиана позиций по набору запросов за несколько дней."""
    values = []
    for day in dates:
        snapshot = snapshots.get(day) or {}
        values.extend(positions_on(snapshot, queries).values())
    return round(statistics.median(values), 2) if values else None


def _dates_before(snapshots: dict, day: str, count: int) -> list[str]:
    return sorted(d for d in snapshots if d < day)[-count:]


def _dates_upto(snapshots: dict, day: str, count: int) -> list[str]:
    return sorted(d for d in snapshots if d <= day)[-count:]


def baseline_for(snapshots: dict, day: str, queries, window: int) -> dict:
    """База «до»: медиана позиций за последние дни перед внедрением."""
    dates = _dates_before(snapshots, day, window)
    median = _median_positions(snapshots, dates, queries)
    fallback = ""
    if median is None:
        # Позиций за прошлые дни нет — берём день фиксации внедрения. Правка
        # к этому моменту ещё не на проде (деплой идёт после), поэтому замер
        # честно описывает состояние «до».
        dates = _dates_upto(snapshots, day, 1)
        median = _median_positions(snapshots, dates, queries)
        fallback = ("замеров до дня внедрения нет; базой взят сам день "
                    "фиксации — правка к этому моменту ещё не была на проде")
    return {
        "дата": day,
        "дни": dates,
        "медиана_позиций": median,
        "запросов": len(list(queries)),
        "_оговорка": fallback,
    }


def register(experiments: list[jr.Experiment], packages: list[dict],
             today: str, snapshot: dict | None = None,
             systemic_kinds: list[str] | None = None) -> list[jr.Experiment]:
    """Заводит эксперименты по новым пакетам работ.

    Регистрируются только пакеты с проверяемым признаком внедрения — то есть
    там, где известны конкретные отсутствующие фразы. Пакет «проверить
    вручную» (содержимое страницы недоступно) эксперимента не порождает:
    измерить его внедрение нечем, а запись без признака превратилась бы в
    висящую задачу, которую никто никогда не закроет.
    """
    active = jr.active_by_url(experiments)
    created = []
    for package in packages:
        url = package.get("url") or ""
        if url in active:
            continue
        requirements = []
        kinds = []
        seen = set()
        for action in package.get("действия") or []:
            kind = action.get("kind", "")
            kinds.append(kind)
            # Нужная степень раскрытия зависит от того, что именно поручено.
            need = {"текст": page_audit.COVER_BODY,
                    "заголовки": page_audit.COVER_PROMINENT}.get(kind)
            if not need:
                continue
            for phrase in _phrases_of(action):
                key = (phrase, need)
                if key in seen:
                    continue
                seen.add(key)
                requirements.append({"фраза": phrase, "нужно": need})
        if not requirements:
            continue
        experiment = jr.Experiment(
            id=jr.next_id(experiments + created),
            created=today,
            url=url,
            page_kind=package.get("page_kind", ""),
            package_id=package.get("package_id", ""),
            queries=list(package.get("queries") or []),
            requirements=requirements,
            action_kinds=sorted(set(k for k in kinds if k)),
            hypothesis=(f"выполнение {len(requirements)} требований к тексту "
                        f"страницы поднимет позиции по запросам пакета"),
            conditions=conditions_of(snapshot or {}),
        )
        # Правка шаблона задевает все страницы своего типа. Поэтому такие
        # страницы исключаются из контрольной группы у КАЖДОГО эксперимента,
        # а не только у тех, чьи собственные требования в шаблон попали:
        # контроль строится из всех запросов ядра, и запрос, ведущий на
        # изменённую страницу, контролем быть не может.
        experiment.affected_kinds = sorted(systemic_kinds or [])
        if kind_of_url(url) in (systemic_kinds or []):
            системные = set(package.get("системные_слова") or [])
            слова = {w for req in requirements
                     for w in page_audit.significant_words(req["фраза"])}
            if слова & системные:
                experiment.scope = SCOPE_KIND
        experiment.log(today, f"предложен пакетом {experiment.package_id}")
        created.append(experiment)
    experiments.extend(created)
    return created


def _detect_scope(exp: jr.Experiment, experiments: list[jr.Experiment],
                  loader) -> tuple[str, list[str]]:
    """Точечная правка или шаблонная: проверяем соседей того же типа.

    Если те же требования внезапно выполнились и на других страницах этого
    типа, которых поручение не касалось, — правили шаблон. Тогда все страницы
    типа затронуты, и контролем они быть не могут. Проверка эмпирическая: она
    не зависит от того, кто и через какой файл вносил правку.
    """
    kind = kind_of_url(exp.url)
    if not kind:
        return SCOPE_PAGE, []
    peers = [e for e in experiments
             if e.url != exp.url and kind_of_url(e.url) == kind][:PEERS_TO_CHECK]
    if len(peers) < 2:
        return SCOPE_PAGE, []
    затронуты = 0
    for peer in peers:
        page = loader(peer.url, peer.page_kind)
        if not page.available:
            continue
        if all(_satisfied(page, req) for req in exp.requirements):
            затронуты += 1
    if затронуты >= 2:
        return SCOPE_KIND, [kind]
    return SCOPE_PAGE, []


def _satisfied(page, requirement: dict) -> bool:
    """Выполнено ли требование: достигнутая степень не ниже требуемой."""
    reached = page_audit.coverage(page, requirement.get("фраза", ""))[0]
    need = requirement.get("нужно", page_audit.COVER_BODY)
    return jr.COVER_ORDER.get(reached, 0) >= jr.COVER_ORDER.get(need, 1)


def _phrases_of(action: dict) -> list[str]:
    """Фразы из шагов действия: то, что должно появиться на странице."""
    phrases = []
    for step in action.get("steps") or []:
        text = step.split(" — не хватает")[0].strip()
        if text.startswith("«") and text.endswith("»"):
            phrases.append(text.strip("«»"))
    return phrases


def detect_implementation(experiments: list[jr.Experiment], snapshots: dict,
                          today: str, config: dict | None = None,
                          loader=page_audit.load) -> list[jr.Experiment]:
    """Отмечает внедрение там, где обещанные фразы появились на странице."""
    opts = settings(config)
    moved = []
    for exp in experiments:
        if exp.state != jr.STATE_PROPOSED:
            continue
        page = loader(exp.url, exp.page_kind)
        if not page.available:
            continue
        done = [req for req in exp.requirements if _satisfied(page, req)]
        if not exp.requirements:
            continue
        ratio = len(done) / len(exp.requirements)
        if ratio < opts["порог_внедрения"]:
            continue
        exp.state = jr.STATE_WATCH
        exp.implemented_at = today
        exp.implementation_note = (
            f"выполнено требований {len(done)} из {len(exp.requirements)} "
            f"({100 * ratio:.0f}%): "
            + "; ".join(f"«{r['фраза']}» {r['нужно']}" for r in done[:4]))
        exp.baseline = baseline_for(snapshots, today, exp.queries,
                                    opts["окно_усреднения"])
        exp.watch_until = jr.add_days(today, opts["окно_наблюдения_дней"])
        if exp.scope != SCOPE_KIND:
            # Проверка соседей уточняет область, но не отменяет уже известные
            # затронутые типы: их проставили при регистрации по системным
            # правкам дня, и терять их нельзя — контроль снова стал бы грязным.
            scope, kinds = _detect_scope(exp, experiments, loader)
            exp.scope = scope
            exp.affected_kinds = sorted(set(exp.affected_kinds) | set(kinds))
        if exp.scope == SCOPE_KIND:
            exp.log(today, (f"правка затронула все страницы типа "
                            f"«{exp.affected_kinds[0]}» — они исключены из "
                            f"контрольной группы"))
        exp.log(today, (f"внедрение подтверждено, наблюдение до "
                        f"{exp.watch_until}"))
        moved.append(exp)
    return moved


def moratorium(experiments: list[jr.Experiment]) -> dict[str, jr.Experiment]:
    """Страницы под мораторием: внедрено, идёт наблюдение — не трогаем."""
    return {e.url: e for e in experiments if e.state == jr.STATE_WATCH}


def evaluate_due(experiments: list[jr.Experiment], snapshots: dict, today: str,
                 config: dict | None = None) -> list[jr.Experiment]:
    """Считает исход экспериментов, у которых окно наблюдения истекло."""
    opts = settings(config)
    finished = []
    for exp in experiments:
        if exp.state != jr.STATE_WATCH or not exp.watch_until:
            continue
        if today < exp.watch_until:
            continue
        outcome = measure(exp, snapshots, today, opts)
        exp.outcome = outcome
        exp.state = jr.STATE_DONE
        exp.log(today, f"итог: {outcome.get('вердикт')} "
                       f"(чистый эффект {outcome.get('чистый_эффект')})")
        finished.append(exp)
    return finished


def measure(exp: jr.Experiment, snapshots: dict, today: str,
            opts: dict | None = None) -> dict:
    """Разность разностей: эффект правки за вычетом движения всей выдачи."""
    opts = opts or settings(None)
    window = opts["окно_усреднения"]
    before_dates = exp.baseline.get("дни") or []
    after_dates = _dates_upto(snapshots, today, window)

    # Состав контроля фиксируется по обоим окнам сразу: разный состав до и
    # после сам по себе сдвинул бы медиану.
    control_queries = _control_queries(snapshots, before_dates + after_dates,
                                       exp.queries, exp.affected_kinds)
    before = _median_positions(snapshots, before_dates, exp.queries)
    after = _median_positions(snapshots, after_dates, exp.queries)
    control_before = _median_positions(snapshots, before_dates, control_queries)
    control_after = _median_positions(snapshots, after_dates, control_queries)

    if before is None or after is None:
        return {"вердикт": "не измерен",
                "почему": "по запросам эксперимента нет позиций в одном из окон"}

    delta = round(after - before, 2)
    control_delta = (round(control_after - control_before, 2)
                     if control_before is not None and control_after is not None
                     else None)
    net = round(delta - control_delta, 2) if control_delta is not None else delta

    if net <= -opts["порог_эффекта_позиций"]:
        verdict = jr.VERDICT_BETTER
    elif net >= opts["порог_эффекта_позиций"]:
        verdict = jr.VERDICT_WORSE
    else:
        verdict = jr.VERDICT_FLAT

    confident = (len(exp.queries) >= opts["минимум_запросов"]
                 and control_delta is not None
                 and len(control_queries) >= 5
                 and len(before_dates) >= 2 and len(after_dates) >= 2)
    сравнимость, пояснение = comparability(
        exp.conditions, conditions_of(snapshots.get(today) or {}))
    return {
        "сравнимость_условий": сравнимость,
        "_сравнимость_пояснение": пояснение,
        "контрольных_запросов": len(control_queries),
        "контроль_исключал": (f"страницы типа {', '.join(exp.affected_kinds)}"
                              if exp.affected_kinds else "ничего, кроме "
                              "запросов самого эксперимента"),
        "медиана_до": before,
        "медиана_после": after,
        "дельта": delta,
        "контроль_дельта": control_delta,
        "чистый_эффект": net,
        "вердикт": verdict,
        "запросов": len(exp.queries),
        "дней_до": len(before_dates),
        "дней_после": len(after_dates),
        "достоверность": "рабочая" if confident else "предварительная",
        "_оговорка": ("это наблюдение, а не доказательство: A/B-теста на "
                      "поисковой выдаче не существует, и влияние других причин "
                      "исключить нельзя. Контрольная группа снимает общий сдвиг "
                      "выдачи, но не индивидуальные события по конкретной "
                      "странице"),
    }


def _control_queries(snapshots: dict, dates: list[str], exclude,
                     exclude_kinds: list[str] | None = None) -> list[str]:
    """Контроль: запросы ядра вне эксперимента, измеренные в те же дни.

    Если правка была шаблонной, из контроля исключаются все страницы её типа.
    Иначе контрольная группа оказалась бы затронута той же правкой, эффект
    «размазался» бы по обеим группам, и разность разностей показала бы ноль
    там, где изменение реально произошло.
    """
    excluded = {page_audit.normalize(q) for q in exclude}
    exclude_kinds = exclude_kinds or []
    keys: set[str] = set()
    for day in dates:
        per_query = (snapshots.get(day) or {}).get("по_запросам") or {}
        for key, bucket in per_query.items():
            if key in excluded:
                continue
            if exclude_kinds and kind_of_url(bucket.get("наш_url") or "") in exclude_kinds:
                continue
            # В контроль идут только запросы, где мы в выдаче. Запрос, по
            # которому нас нет, стоит на условной позиции 21 в оба окна и
            # ничего не измеряет: набрав таких сотни, мы получили бы
            # неподвижную медиану и контроль, который всегда показывает ноль.
            if not bucket.get("позиция"):
                continue
            keys.add(key)
    return sorted(keys)
