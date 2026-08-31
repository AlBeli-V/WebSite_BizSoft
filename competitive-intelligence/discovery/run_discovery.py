#!/usr/bin/env python3
"""Прогон discovery: построить реестр конкурентов за дату и сохранить снимок.

Читает срез выдачи Яндекса из хранилища базового контура (read-only, повторно
не покупается), строит карточки доменов и пишет два артефакта:

  * append-only запись в data/competitive/competitors/registry.jsonl;
  * снимок дня data/competitive/snapshots/<дата>-discovery.json — он станет
    единственным источником цифр для письма и отчёта.

Запуск: python3 competitive-intelligence/discovery/run_discovery.py [дата]
Без аргумента берётся последняя доступная дата среза.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402
from discovery import registry, serp_source  # noqa: E402
from scoring import visibility  # noqa: E402

MSK = timezone(timedelta(hours=3))
OURS = "biz-soft.pro"


def build_snapshot(date: str, cards: list, rows: list, config: dict) -> dict:
    """Канонический снимок дня: цифры письма берутся только отсюда."""
    # Наш домен исключается из всех конкурентных срезов: он не конкурент сам
    # себе. Раньше biz-soft.pro попадал и в перечень «кто держит выдачу», и в
    # карточки конкурентов, а его доля вливалась в категорию «прямые
    # B2B-реселлеры» — из-за чего вес конкурентов в этой категории выглядел
    # больше, чем есть. Наша доля живёт отдельно, в «наши_показатели».
    rivals = [c for c in cards if c.domain != OURS]
    main = [c for c in rivals if c.in_main_ranking]
    ours = next((c for c in cards if c.domain == OURS), None)
    by_category: dict[str, float] = {}
    for card in rivals:
        by_category[card.category] = round(
            by_category.get(card.category, 0.0) + (card.share or 0.0), 6)

    usable = [r for r in rows if r.has_data]
    failed = [r for r in rows if not r.has_data]

    return {
        "дата": date,
        "собран": datetime.now(MSK).isoformat(),
        "версия_конфига": config.get("версия"),
        "зрелость_скоринга": "базовый",
        "_зрелость_пояснение": (
            "Vulnerability недоступен до Phase 4, вес перераспределён; "
            "Confidence рекомендаций не выше MEDIUM"),
        "покрытие": {
            "яндекс_запросов_всего": len(rows),
            "яндекс_запросов_с_данными": len(usable),
            "яндекс_ошибок": len(failed),
            "google": None,
            "_google_пояснение": "NO DATA: еженедельный сбор Google ещё не запущен",
        },
        "наши_показатели": {
            "взвешенная_видимость": ours.weighted_visibility if ours else None,
            "доля_видимости": ours.share if ours else None,
            "топ3": ours.top3 if ours else None,
            "топ10": ours.top10 if ours else None,
            "запросов_в_поле": len(usable),
        } if ours else {"_нет_данных": "домен не найден в срезе"},
        "доли_по_категориям": by_category,
        "_доли_по_категориям_пояснение": (
            "доли конкурентов без BIZSoft; наша доля — в «наши_показатели», "
            "поэтому сумма меньше 100%"),
        "конкурентов_в_основном_рейтинге": len(main),
        "не_классифицировано": sum(1 for c in cards if c.category == "?"),
        "лидеры": [
            {"домен": c.domain, "категория": c.category, "доля": c.share,
             "топ3": c.top3, "топ10": c.top10}
            for c in main[:10]
        ],
    }


def main(argv: list[str]) -> int:
    dates = serp_source.available_dates()
    if not dates:
        print("Срезов выдачи в хранилище базового контура нет — нечего обрабатывать")
        return 1
    date = argv[1] if len(argv) > 1 else dates[-1]
    if date not in dates:
        print(f"Среза за {date} нет. Доступны: {', '.join(dates)}")
        return 1

    rows = serp_source.read_snapshot(date)
    config = visibility.load_config()
    cards = registry.build(rows, config, date=date)
    if not cards:
        print(f"Срез {date} не дал ни одного домена — прогон остановлен")
        return 1

    registry_path = registry.append(cards)
    snapshot = build_snapshot(date, cards, rows, config)
    os.makedirs(paths.SNAPSHOTS_DIR, exist_ok=True)
    snapshot_path = os.path.join(paths.SNAPSHOTS_DIR, f"{date}-discovery.json")
    with open(snapshot_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2)

    ours = snapshot["наши_показатели"]
    print(f"Дата среза: {date}")
    print(f"Доменов в поле: {len(cards)}, в основном рейтинге: "
          f"{snapshot['конкурентов_в_основном_рейтинге']}, "
          f"не классифицировано: {snapshot['не_классифицировано']}")
    if ours.get("доля_видимости") is not None:
        print(f"BIZSoft: доля {100 * ours['доля_видимости']:.2f}%, "
              f"топ-3 {ours['топ3']}, топ-10 {ours['топ10']}")
    print(f"Реестр: {registry_path}")
    print(f"Снимок: {snapshot_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
