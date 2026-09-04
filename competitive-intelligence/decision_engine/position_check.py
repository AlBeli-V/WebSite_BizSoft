"""Сверка позиции из среза с позицией по данным Вебмастера.

Зачем модуль появился (разбор 04.09.2026 по замечанию руководителя). Отчёт
сообщил, что по запросу «как оплатить box business из россии» мы в Яндексе
первые. Ручная проверка выдачи показала другое: первым стоит конкурент, мы
вторые, и перед обоими — четыре рекламных объявления.

Разбор показал, что отчёт передал срез верно: в срезе мы действительно первые.
Ошибка не в расчёте позиции, а в том, что за «место в выдаче» выдавалась
величина другой природы. Срез приходит из Yandex Cloud Search API, а он
отдаёт только органические документы: рекламы и колдунщиков в ответе нет
вовсе. То есть измеряется **органическая позиция в индексе API**, а не место,
которое видит человек.

Насколько это расходится с действительностью — вопрос измеримый. Вебмастер
даёт `AVG_SHOW_POSITION`: позицию, на которой Яндекс фактически показывал нас
в выдаче, со всеми её блоками. Сверка на 71 запросе (04.09.2026) дала медиану
расхождения +1,8 позиции, причём в 79% случаев срез оптимистичнее.

Важно, чего эта сверка НЕ даёт. Она меряет размер расхождения, но не его
причину. Сдвиг неравномерен: на позициях 2–5 он около +2,2, а на 6–10 — всего
+0,5. Будь дело только в рекламе, сдвиг был бы одинаковым на всех позициях —
четыре объявления сдвигают всех сразу. Значит вклад дают и реклама, и иное
ранжирование самого API (без персонализации, без колдунщиков, десктоп), и
разделить их можно только эталонным замером фактической выдачи.

Поэтому у сверки одна задача: держать расхождение под наблюдением и поднимать
тревогу, когда оно растёт. Абсолютная величина расхождения — не повод для
тревоги, она известна и названа в отчёте; поводом является рост относительно
зафиксированной базовой линии.
"""
from __future__ import annotations

import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402,F401
from discovery import demand_source, serp_source  # noqa: E402

OURS = "biz-soft.pro"
REGION = "213"

# Меньше этого числа показов средняя позиция Вебмастера — шум: она посчитана
# по двум-трём показам и скачет на несколько позиций от одного попадания.
MIN_SHOWS = 3
# Меньше этого числа сопоставленных запросов вывод не делается вовсе.
MIN_SAMPLE = 20
# Диапазоны позиций, по которым расхождение разбирается отдельно: сдвиг
# зависит от глубины, и одно число по всей выборке это скрывает.
BANDS = ((1, 1), (2, 3), (4, 5), (6, 10), (11, 20))


def _normalize(phrase: str) -> str:
    return " ".join((phrase or "").lower().replace("ё", "е").split())


def our_position(row: serp_source.SerpRow) -> int | None:
    for index, item in enumerate(row.top, start=1):
        if serp_source.normalize_domain(item.get("domain", "")) == OURS:
            return index
    return None


def baseline_queries(window_to: str, branch: str = serp_source.SEO_BRANCH
                     ) -> set[str]:
    """Запросы, по которым мы уже ранжировались к концу окна Вебмастера.

    Без этого отбора сверка врёт в обе стороны сразу. Половина ядра — статьи,
    написанные после окна: Вебмастер меряет период, когда страницы ещё не
    было, и её «позиция» там либо отсутствует, либо относится к другой
    странице. 04.09.2026 таких запросов было 69 из 140 — почти половина
    выборки.
    """
    dates = [d for d in serp_source.available_dates(branch) if d <= window_to]
    if not dates:
        return set()
    return {_normalize(row.query)
            for row in serp_source.read_snapshot(dates[-1], branch)
            if row.has_data and row.region == REGION and our_position(row)}


def compare(rows: list[serp_source.SerpRow],
            positions: dict[str, dict] | None = None,
            window: tuple[str, str] | None = None,
            branch: str = serp_source.SEO_BRANCH) -> dict:
    """Расхождение позиции среза с позицией показа по Вебмастеру."""
    positions = demand_source.load_positions(branch) if positions is None else positions
    window = demand_source.webmaster_window(branch) if window is None else window
    window_from, window_to = window
    if not positions or not window_to:
        return {"доступна": False,
                "причина": "выгрузка Вебмастера недоступна — сверять не с чем"}

    eligible = baseline_queries(window_to, branch)
    pairs: list[tuple[int, float]] = []
    skipped_new = 0
    for row in rows:
        if not row.has_data or row.region != REGION:
            continue
        position = our_position(row)
        if position is None:
            continue
        key = _normalize(row.query)
        measured = positions.get(key)
        if not measured or measured["показов"] < MIN_SHOWS:
            continue
        if key not in eligible:
            skipped_new += 1
            continue
        pairs.append((position, measured["позиция"]))

    if len(pairs) < MIN_SAMPLE:
        return {"доступна": False,
                "причина": (f"сопоставлено {len(pairs)} запросов при минимуме "
                            f"{MIN_SAMPLE} — выборка ничего не показывает"),
                "окно_вебмастера": f"{window_from} — {window_to}"}

    diffs = [webmaster - serp for serp, webmaster in pairs]
    optimistic = sum(1 for d in diffs if d > 0.5)
    bands = []
    for low, high in BANDS:
        inside = [w - s for s, w in pairs if low <= s <= high]
        if inside:
            bands.append({"диапазон": f"{low}–{high}" if low != high else str(low),
                          "запросов": len(inside),
                          "медиана": round(statistics.median(inside), 2)})
    return {
        "доступна": True,
        "окно_вебмастера": f"{window_from} — {window_to}",
        "сопоставлено": len(pairs),
        "исключено_новых_страниц": skipped_new,
        "медиана_расхождения": round(statistics.median(diffs), 2),
        "среднее_расхождения": round(statistics.mean(diffs), 2),
        "срез_оптимистичнее": optimistic,
        "доля_оптимистичных": round(optimistic / len(pairs), 3),
        "срез_пессимистичнее": sum(1 for d in diffs if d < -0.5),
        "по_диапазонам": bands,
    }


def settings(config: dict | None = None) -> dict:
    block = ((config or {}).get("сверка_позиций") or {})
    return {
        "базовая_линия": float(block.get("базовая_линия_медианы", 1.8)),
        "допустимый_рост": float(block.get("допустимый_рост_медианы", 1.0)),
    }


def verdict(measure: dict, config: dict | None = None) -> dict:
    """Тревога поднимается на рост расхождения, а не на его величину.

    Величина известна, названа в отчёте и сама по себе новостью не является:
    органическая позиция API и позиция показа — разные величины, они и должны
    расходиться. Новость — если расхождение выросло: значит либо изменился
    источник, либо выдача, либо наш парсер, и цифрам отчёта больше доверять
    нельзя, пока причина не найдена.
    """
    if not measure.get("доступна"):
        return {"тревога": False,
                "объяснение": measure.get("причина", "сверка не выполнялась")}
    limits = settings(config)
    ceiling = limits["базовая_линия"] + limits["допустимый_рост"]
    median = measure["медиана_расхождения"]
    if median > ceiling:
        return {
            "тревога": True,
            "объяснение": (
                f"расхождение среза с Вебмастером выросло до {median:+.2f} "
                f"позиции при базовой линии {limits['базовая_линия']:+.2f} и "
                f"допустимом росте {limits['допустимый_рост']:.2f}. Пока "
                f"причина не найдена, позиции этого дня сравнивать с прежними "
                f"нельзя"),
            "медиана": median, "потолок": round(ceiling, 2)}
    return {
        "тревога": False,
        "объяснение": (
            f"расхождение {median:+.2f} позиции при базовой линии "
            f"{limits['базовая_линия']:+.2f} — в пределах наблюдаемого"),
        "медиана": median, "потолок": round(ceiling, 2)}
