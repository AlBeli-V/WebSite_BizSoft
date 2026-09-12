"""KPI дня и вердикт письма — из снимка, и только из него.

Единственный источник цифр для письма и отчёта — канонический снимок дня
(правило методики базового контура: никаких пересчётов «на лету» в момент
вёрстки письма, иначе письмо и отчёт разойдутся в цифрах).

Вердикт (раздел 23 задания): 🟢 усиливаемся · 🟡 нейтрально-риск ·
🔴 значимое ухудшение · ⚪ недостаточно данных. Отдельно важно: пока истории
меньше шести сравнимых измерений, вердикт обязан быть ⚪ — не потому что всё
плохо, а потому что сравнивать не с чем.

**Две доли вместо одной (1.3.0).** Доля считается внутри поля, а поле задаётся
составом мониторингового ядра. Поэтому в снимке живут два разных числа:

  * **доля в текущем поле** — сколько мы весим сегодня среди сегодняшнего
    состава запросов. Это то, что показывается как B2B Share;
  * **сравнимая доля** — та же величина, пересчитанная по пересечению
    составов сравниваемых дней. Только она годится для динамики.

Пока состав ядра не менялся, оба числа совпадают. Как только ядро
редактируется, они расходятся, и разница между ними — это ровно тот эффект,
который иначе выглядел бы как движение конкурентов.
"""
from __future__ import annotations

import glob
import json
import os
import statistics
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402

VERDICT_GROWTH = "🟢"
VERDICT_NEUTRAL = "🟡"
VERDICT_DECLINE = "🔴"
VERDICT_NO_DATA = "⚪"

# Порог значимости изменения доли видимости в процентных пунктах. Меньшее
# движение — шум, а не сигнал (раздел 9 задания).
SIGNIFICANT_SHARE_PP = 0.5

# Сколько сравнимых измерений нужно, чтобы говорить о динамике. Общий фильтр
# значимости сравнивает медиану трёх последних измерений с медианой трёх
# предыдущих — значит раньше шестого валидного среза тренда не существует.
WINDOW = 3
MIN_OBSERVATIONS_FOR_TREND = WINDOW * 2

# Доля мониторингового ядра, ниже которой срез считается непригодным.
CRITICAL_COVERAGE_RATIO = 0.80
# Второй гейт: покрытие, взвешенное по спросу. Можно собрать 90% запросов и
# потерять при этом самый частотный — по числу запросов это рабочий день, по
# объёму спроса дыра. Считается отдельно по каждому источнику: складывать
# частотность Wordstat с показами Вебмастера нельзя даже в знаменателе.
CRITICAL_WEIGHTED_COVERAGE = 0.80

# Какая часть текущего ядра должна попасть в пересечение, чтобы динамику
# вообще имело смысл считать. Ниже этого порога сравнимое подмножество
# описывает уже не то поле, о котором идёт речь в письме.
MIN_COMPARABLE_CORE_RATIO = 0.70

# Обязательные источники: их отсутствие делает вердикт невозможным.
REQUIRED_SOURCES = ("яндекс",)


@dataclass
class Kpi:
    """Показатели дня и их изменение к сравнимому прошлому."""
    date: str
    share_yandex: float | None
    share_google: float | None
    top3: int | None
    top10: int | None
    queries: int | None
    share_delta_pp: float | None = None
    top3_delta: int | None = None
    top10_delta: int | None = None
    compared_with: str | None = None
    coverage_ok: bool = True
    maturity: str = "базовый"
    # Ядро измерения: версия состава, отпечаток и размер.
    core_version: str = ""
    core_hash: str = ""
    core_size: int | None = None
    # Сравнимая доля и то, на каком подмножестве она получена.
    share_comparable: float | None = None
    comparable_core: int | None = None
    core_changed: bool = False
    delta_basis: str = "то же ядро"
    notes: list[str] = field(default_factory=list)
    # Google RU (серия google_ru, xmlriver): дата среза, из которого взята
    # доля, размер поля и дельта к прошлому срезу другой даты — по
    # пересечению запросов, как и у Яндекса.
    google_date: str | None = None
    google_queries: int | None = None
    google_top3: int | None = None
    google_top10: int | None = None
    google_delta_pp: float | None = None
    google_compared_with: str | None = None


def load_snapshot(date: str, directory: str | None = None) -> dict | None:
    directory = directory or paths.SNAPSHOTS_DIR
    path = os.path.join(directory, f"{date}-discovery.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def available_snapshots(directory: str | None = None) -> list[str]:
    directory = directory or paths.SNAPSHOTS_DIR
    files = glob.glob(os.path.join(directory, "*-discovery.json"))
    return sorted(os.path.basename(f)[: -len("-discovery.json")] for f in files)


# --- сравнимость ядра -------------------------------------------------------

def core_hash(snapshot: dict) -> str:
    """Отпечаток состава ядра снимка. Пусто — снимок старой версии."""
    return ((snapshot.get("ядро_запросов") or {}).get("хеш")
            or (snapshot.get("метаданные") or {}).get("ядро_хеш") or "")


def query_shares(snapshot: dict) -> dict:
    """Взвешенная видимость по запросам: {запрос: {«наша», «поле»}}."""
    return snapshot.get("по_запросам") or {}


def share_on(snapshot: dict, queries) -> float | None:
    """Доля BIZSoft, пересчитанная по заданному подмножеству запросов.

    Возвращает None, если по этому подмножеству нет данных: пустое поле —
    это NO DATA, а не нулевая видимость.
    """
    per_query = query_shares(snapshot)
    ours = 0.0
    field_total = 0.0
    for query in queries:
        bucket = per_query.get(query)
        if not bucket:
            continue
        ours += bucket.get("наша") or 0.0
        field_total += bucket.get("поле") or 0.0
    if field_total <= 0:
        return None
    return ours / field_total


def comparable_series(snapshots: list[dict]) -> tuple[list[float], dict]:
    """Ряд сравнимых долей по пересечению составов ядра.

    Все дни ряда приводятся к одному подмножеству запросов — тому, что
    присутствует во всех сравниваемых снимках. Иначе изменение доли смешивало
    бы движение конкурентов с редактированием собственного списка запросов.

    Возвращает (ряд, пояснение). Ряд пуст, если сравнимого подмножества нет
    или оно слишком мало по отношению к текущему ядру.
    """
    meta: dict = {"дней": len(snapshots), "причина": ""}
    usable = [s for s in snapshots if query_shares(s)]
    if not usable:
        meta["причина"] = "в снимках нет по-запросной видимости (старый формат)"
        return [], meta

    sets = [set(query_shares(s)) for s in usable]
    common = set.intersection(*sets) if sets else set()
    current = sets[-1]
    meta.update({
        "ядро_текущее": len(current),
        "пересечение": len(common),
        "доля_пересечения": round(len(common) / len(current), 4) if current else 0.0,
        "ядро_менялось": any(core_hash(s) != core_hash(usable[-1]) for s in usable),
    })
    if not common:
        meta["причина"] = "пересечение составов ядра пусто"
        return [], meta
    if current and len(common) / len(current) < MIN_COMPARABLE_CORE_RATIO:
        meta["причина"] = (
            f"пересечение составов ({len(common)} из {len(current)}) меньше "
            f"порога {100 * MIN_COMPARABLE_CORE_RATIO:.0f}% — сравнимого поля "
            f"фактически нет")
        return [], meta

    series = []
    for snapshot in usable:
        value = share_on(snapshot, common)
        if value is None:
            meta["причина"] = (f"по пересечению нет данных за "
                              f"{snapshot.get('дата')}")
            return [], meta
        series.append(value)
    return series, meta


def chained_series(snapshots: list[dict],
                   min_ratio: float = MIN_COMPARABLE_CORE_RATIO
                   ) -> tuple[list[float], dict]:
    """Сцепленный ряд долей: каждая пара дней сравнивается по своему пересечению.

    Зачем понадобился (разбор 10.09.2026). `comparable_series` требует ОДНО
    общее подмножество запросов на все дни ряда. Ядро контура растёт почти
    каждый день, а два дня неполного сбора (05–06.09, 209 и 224 запроса
    против четырёхсот) обрезали общее пересечение до 59 запросов из 489 — 12%
    при пороге 70%. Ряд оказывался пустым, вердикт — «нужно 6 сравнимых
    измерений, не хватает 6», и читалось это как «подождите ещё немного».

    Ждать было бесполезно: общее пересечение по построению только сжимается с
    каждым новым днём. Динамический вердикт был недостижим, и отчёт об этом
    не говорил.

    При этом соседние дни сравнимы отлично: попарные пересечения 86–100%
    везде, кроме стыков с днями неполного сбора. Отсюда решение — сцепление,
    стандартный приём для индексов с меняющейся корзиной: доля считается
    заново на пересечении КАЖДОЙ пары, берётся её изменение, и изменения
    складываются в ряд. Пара, у которой пересечение ниже порога, цепь
    разрывает; возвращается последний непрерывный отрезок.

    Чего сцепление не даёт и что обязано быть названо в отчёте: уровень ряда
    после первого звена — уже не доля в сегодняшнем поле, а накопленное
    изменение от начала отрезка. Ошибки звеньев накапливаются (дрейф цепи),
    поэтому чем длиннее отрезок, тем осторожнее читается его начало.
    Сравнивать сцепленный ряд со строгим нельзя — это разные величины.
    """
    meta: dict = {"дней": len(snapshots), "причина": "", "звеньев": 0,
                  "разрывов": 0}
    usable = [s for s in snapshots if query_shares(s)]
    if len(usable) < 2:
        meta["причина"] = "меньше двух снимков с по-запросной видимостью"
        return [], meta

    # Звенья: для каждой пары — её собственное пересечение и приращение доли.
    links: list[tuple[dict, float | None]] = [(usable[0], None)]
    разрывов = 0
    for prev, cur in zip(usable, usable[1:]):
        common = set(query_shares(prev)) & set(query_shares(cur))
        current = set(query_shares(cur))
        if not current or len(common) / len(current) < min_ratio:
            разрывов += 1
            links.append((cur, None))
            continue
        было, стало = share_on(prev, common), share_on(cur, common)
        if было is None or стало is None:
            разрывов += 1
            links.append((cur, None))
            continue
        links.append((cur, стало - было))
    meta["разрывов"] = разрывов

    # Последний непрерывный отрезок: от последнего разрыва до конца.
    начало = 0
    for index in range(1, len(links)):
        if links[index][1] is None:
            начало = index
    segment = links[начало:]
    if len(segment) < 2:
        meta["причина"] = ("непрерывного отрезка нет: у каждой пары дней "
                           "пересечение составов ниже порога")
        return [], meta

    base = share_on(segment[0][0], set(query_shares(segment[0][0])))
    if base is None:
        meta["причина"] = "по началу отрезка нет доли"
        return [], meta
    series = [base]
    for _, delta in segment[1:]:
        series.append(series[-1] + (delta or 0.0))
    meta.update({"звеньев": len(segment) - 1,
                 "отрезок_с": segment[0][0].get("дата"),
                 "отрезок_по": segment[-1][0].get("дата")})
    return series, meta


def trend_basis(snapshots: list[dict]) -> tuple[list[float], str, dict]:
    """Ряд для динамики и название основания, на котором он посчитан.

    Сначала строгий ряд — одна корзина запросов на все дни. Он точнее всего,
    но требует, чтобы состав ядра держался, а он не держится: ядро растёт
    почти ежедневно, и общее пересечение по построению только сжимается.
    Если строгого ряда нет, берётся сцепленный: каждая пара дней сравнивается
    по своему пересечению.

    Возвращает (ряд, основание, пояснение). Основание обязано доезжать до
    отчёта и письма: величины, посчитанные на разных основаниях, между собой
    не сравниваются.
    """
    строгий, мета = comparable_series(snapshots)
    if строгий:
        return строгий, "строгий", мета
    сцепленный, мета2 = chained_series(snapshots)
    if сцепленный:
        мета2["причина_строгого"] = мета.get("причина", "")
        return сцепленный, "сцепленный", мета2
    return [], "нет", (мета2 if мета2.get("причина") else мета)


def google_block(snapshot: dict) -> dict | None:
    """Блок Google RU снимка, если срез был доступен; иначе None."""
    block = snapshot.get("google") or {}
    return block if block.get("доступен") else None


def build_kpi(snapshot: dict, previous: dict | None = None) -> Kpi:
    """KPI дня. Дельты считаются только при наличии сравнимого прошлого."""
    ours = snapshot.get("наши_показатели") or {}
    coverage = snapshot.get("покрытие") or {}
    core = snapshot.get("ядро_запросов") or {}
    google = google_block(snapshot)
    g_ours = (google or {}).get("наши_показатели") or {}
    kpi = Kpi(
        date=snapshot.get("дата", ""),
        share_yandex=ours.get("доля_видимости"),
        # Доля Google — из блока среза; старые снимки без блока хранят её в
        # «покрытие.google» (там всегда был None).
        share_google=(g_ours.get("доля_видимости") if google
                      else coverage.get("google")),
        google_date=(google or {}).get("дата_среза"),
        google_queries=g_ours.get("запросов_в_поле"),
        google_top3=g_ours.get("топ3"),
        google_top10=g_ours.get("топ10"),
        top3=ours.get("топ3"),
        top10=ours.get("топ10"),
        queries=ours.get("запросов_в_поле"),
        maturity=snapshot.get("зрелость_скоринга", "базовый"),
        coverage_ok=bool(coverage.get("яндекс_запросов_с_данными")),
        core_version=core.get("версия", ""),
        core_hash=core.get("хеш", ""),
        core_size=core.get("запросов"),
    )
    if not previous:
        return kpi

    prev = previous.get("наши_показатели") or {}
    kpi.compared_with = previous.get("дата")

    # Google: дельта только между срезами РАЗНЫХ дат — один и тот же
    # еженедельный срез, прочитанный в два соседних дня, движения не даёт.
    prev_google = google_block(previous)
    if (google and prev_google
            and prev_google.get("дата_среза") != google.get("дата_среза")):
        common_g = (set(google.get("по_запросам") or {})
                    & set(prev_google.get("по_запросам") or {}))
        if common_g:
            today_g = _share_on_block(google, common_g)
            before_g = _share_on_block(prev_google, common_g)
            if today_g is not None and before_g is not None:
                kpi.google_delta_pp = round(100 * (today_g - before_g), 2)
                kpi.google_compared_with = prev_google.get("дата_среза")
    kpi.core_changed = bool(core_hash(snapshot) and core_hash(previous)
                            and core_hash(snapshot) != core_hash(previous))

    if kpi.top3 is not None and prev.get("топ3") is not None:
        kpi.top3_delta = kpi.top3 - prev["топ3"]
    if kpi.top10 is not None and prev.get("топ10") is not None:
        kpi.top10_delta = kpi.top10 - prev["топ10"]

    # Дельта доли: по пересечению составов, если они различаются, и по
    # текущему полю, если состав тот же. Разные знаменатели дают разные
    # величины, поэтому основание дельты подписывается явно.
    common = set(query_shares(snapshot)) & set(query_shares(previous))
    if common:
        today = share_on(snapshot, common)
        before = share_on(previous, common)
        kpi.share_comparable = today
        kpi.comparable_core = len(common)
        if today is not None and before is not None:
            kpi.share_delta_pp = round(100 * (today - before), 2)
            kpi.delta_basis = (
                f"пересечение ядер: {len(common)} запросов"
                if kpi.core_changed else "то же ядро")
            if kpi.core_changed:
                kpi.notes.append(
                    f"состав ядра менялся ({core_hash(previous)} → "
                    f"{core_hash(snapshot)}); дельта посчитана по общему "
                    f"подмножеству из {len(common)} запросов, доля в письме — "
                    f"по текущему полю")
        return kpi

    # Старый формат снимка без по-запросной видимости: сравниваем поля целиком
    # и честно помечаем, что состав ядра при этом не проверялся.
    if kpi.share_yandex is not None and prev.get("доля_видимости") is not None:
        kpi.share_delta_pp = round(
            100 * (kpi.share_yandex - prev["доля_видимости"]), 2)
        kpi.delta_basis = "поля целиком (по-запросной видимости нет)"
        kpi.notes.append("сравнимость состава ядра не проверялась: в снимках "
                         "нет по-запросной видимости")
    return kpi


def _share_on_block(block: dict, queries) -> float | None:
    per_query = block.get("по_запросам") or {}
    ours = field_total = 0.0
    for query in queries:
        bucket = per_query.get(query)
        if not bucket:
            continue
        ours += bucket.get("наша") or 0.0
        field_total += bucket.get("поле") or 0.0
    return ours / field_total if field_total > 0 else None


def trend_change(history: list[float]) -> float | None:
    """Изменение доли между сравнимыми окнами, в процентных пунктах.

    Медиана трёх последних измерений против медианы трёх предыдущих — то же
    сглаживание, что и в остальной системе. Меньше шести измерений — тренда
    нет, возвращается None, а не ноль.

    Ряд обязан быть сравнимым: подаётся результат comparable_series(), а не
    сырые доли по разным составам ядра.
    """
    if len(history) < MIN_OBSERVATIONS_FOR_TREND:
        return None
    recent = statistics.median(history[-WINDOW:])
    earlier = statistics.median(history[-MIN_OBSERVATIONS_FOR_TREND:-WINDOW])
    return round(100 * (recent - earlier), 3)


def structural_verdict(kpi: Kpi, field_leader: tuple[str, float] | None = None
                       ) -> str:
    """Структурный вывод: где мы стоим прямо сейчас.

    Не требует истории и доступен с первого дня. Отвечает на вопрос «какова
    расстановка», а не «куда движемся» — это разные утверждения.
    """
    share = format_share(kpi.share_yandex)
    base = f"BIZSoft занимает {share} взвешенной видимости поля"
    if kpi.top3 is not None and kpi.queries:
        base += f", в ТОП-3 по {kpi.top3} запросам из {kpi.queries}"
    if field_leader:
        domain, value = field_leader
        base += f"; ведущий конкурент — {domain} с {format_share(value)}"
    return base + "."


def coverage_state(snapshot: dict) -> tuple[str, str]:
    """Состояние покрытия данных: критическое или рабочее.

    Два гейта, оба обязательные:
      1. по числу запросов ядра — сколько строк среза пригодны;
      2. по спросу — какая доля объёма спроса попала в пригодные строки,
         отдельно по каждому источнику.

    Второй нужен потому, что потерять один запрос с частотностью 20 000 и
    один с частотностью 5 — это одинаково «минус один запрос» по первому
    гейту и совершенно разные события по существу.
    """
    coverage = snapshot.get("покрытие") or {}
    total = coverage.get("яндекс_запросов_всего") or 0
    usable = coverage.get("яндекс_запросов_с_данными") or 0
    if total <= 0:
        return "критическое", "срез выдачи не собран вовсе"
    ratio = usable / total
    if ratio < CRITICAL_COVERAGE_RATIO:
        return "критическое", (
            f"собрано {usable} запросов из {total} "
            f"({100 * ratio:.0f}% при пороге "
            f"{100 * CRITICAL_COVERAGE_RATIO:.0f}%)")

    weighted = coverage.get("взвешенное_покрытие") or {}
    weak = {source: value for source, value in weighted.items()
            if value < CRITICAL_WEIGHTED_COVERAGE}
    if weak:
        detail = "; ".join(f"{source}: {100 * value:.0f}%"
                           for source, value in sorted(weak.items()))
        return "критическое", (
            f"по числу запросов собрано {100 * ratio:.0f}%, но по объёму "
            f"спроса — ниже порога {100 * CRITICAL_WEIGHTED_COVERAGE:.0f}% "
            f"({detail}): потеряны самые весомые запросы")

    missing = []
    google = google_block(snapshot)
    if google:
        missing.append(f"Google RU: срез xmlriver от {google.get('дата_среза')}")
    elif (snapshot.get("google") or {}).get("причина"):
        missing.append(f"Google: {snapshot['google']['причина']}")
    else:
        missing.append("Google не собирается")
    note = ("; ".join(missing) if missing else "все обязательные источники собраны")
    return "ок", note


def verdict(kpi: Kpi, history: list[float] | None = None) -> tuple[str, str]:
    """Динамический вердикт: усиливаемся, слабеем или движения нет.

    Требует шести сравнимых измерений — раньше динамики не существует.
    Структурная картина при этом доступна всегда, её даёт structural_verdict().

    Методическая оговорка про основание ряда (строгий или сцепленный,
    пересечение составов, звенья цепи) в вердикт не входит: 11.09.2026 она
    занимала 141 символ из 1075 и вместе с остальным текстом выводила письмо
    за лимит первого экрана. Оговорка живёт в детализации, в разделе условий
    расчёта — решение руководителя 11.09.2026.
    """
    if not kpi.coverage_ok:
        return VERDICT_NO_DATA, ("Данные неполные: срез выдачи не собран — "
                                 "выводы по такому дню не делаем")

    history = history or []
    if len(history) < MIN_OBSERVATIONS_FOR_TREND:
        need = MIN_OBSERVATIONS_FOR_TREND - len(history)
        # «Не хватает N» читается как «подождите N дней», и до 1.9.9 это
        # было неправдой: строгий ряд требует одну корзину на все дни, а
        # ядро растёт ежедневно, поэтому пересечение только сжималось и
        # вердикт был недостижим по построению. Теперь при пустом строгом
        # ряде берётся сцепленный, и «не хватает» снова означает время.
        why = (f"Недостаточно данных для оценки динамики: нужно "
               f"{MIN_OBSERVATIONS_FOR_TREND} сравнимых измерений, "
               f"есть {len(history)}, не хватает {need}")
        return VERDICT_NO_DATA, why

    change = trend_change(history)
    if change is None:
        return VERDICT_NO_DATA, "Динамика не определена"
    if change >= SIGNIFICANT_SHARE_PP:
        return VERDICT_GROWTH, (f"Доля видимости выросла на {change:+.2f} п.п. "
                                f"между сравнимыми окнами")
    if change <= -SIGNIFICANT_SHARE_PP:
        return VERDICT_DECLINE, (f"Доля видимости упала на {change:+.2f} п.п. "
                                 f"между сравнимыми окнами")
    return VERDICT_NEUTRAL, (f"Доля видимости устойчива "
                             f"({change:+.2f} п.п. между окнами)")


def ru_number(value: float, digits: int = 1) -> str:
    """Число в русской записи: разделитель дробной части — запятая."""
    return f"{value:.{digits}f}".replace(".", ",")


def format_share(value: float | None) -> str:
    """Доля для письма. NO DATA пишется словами, а не нулём."""
    return "NO DATA" if value is None else f"{ru_number(100 * value)}%"


def format_delta(value: float | None, *, unit: str = "") -> str:
    if value is None:
        return "н/д"
    if isinstance(value, float):
        sign = "+" if value >= 0 else "−"
        return f"{sign}{ru_number(abs(value), 2)}{unit}"
    return f"{value:+d}{unit}"
