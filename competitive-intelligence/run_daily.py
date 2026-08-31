#!/usr/bin/env python3
"""Ежедневный прогон контура конкурентной разведки — одной командой.

Порядок (раздел 24 задания): проверка покрытия → discovery и пересчёт долей
→ Threat → Strike List → главный сигнал → письмо. Всё детерминировано,
LLM-шагов нет: прогон воспроизводим и не зависит от формулировок.

    python3 competitive-intelligence/run_daily.py [дата]

Без даты берётся последний доступный срез выдачи. Скрипт только пишет файлы
в рабочую копию; отправку данных в хранилище делает вызывающая сторона
(storage/data_sync_ci.sh push), а письмо уходит по push-триггеру workflow.

Код возврата: 0 — прогон удался, 1 — данных нет или гейт качества не пройден.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402
from attack_engine import strike_list  # noqa: E402
from decision_engine import kpi as kpi_mod  # noqa: E402
from discovery import registry, run_discovery, serp_source  # noqa: E402
from mailer import build_email  # noqa: E402
from scoring import threat as threat_mod  # noqa: E402
from scoring import visibility  # noqa: E402

OURS = "biz-soft.pro"


def main(argv: list[str]) -> int:
    dates = serp_source.available_dates()
    if not dates:
        print("Срезов выдачи нет — прогон невозможен")
        return 1
    date = argv[1] if len(argv) > 1 else dates[-1]
    if date not in dates:
        print(f"Среза за {date} нет. Доступны: {', '.join(dates[-5:])}")
        return 1

    print(f"=== Прогон конкурентной разведки за {date} ===")
    rows = serp_source.read_snapshot(date)
    usable = [r for r in rows if r.has_data]
    print(f"1. Покрытие: {len(usable)} запросов с данными из {len(rows)}")
    if not usable:
        print("   Данных нет — письмо не собирается, уйдёт уведомление о сбое")
        return 1

    config = visibility.load_config()
    cards = registry.build(rows, config, date=date)
    registry.append(cards)
    snapshot = run_discovery.build_snapshot(date, cards, rows, config)
    os.makedirs(paths.SNAPSHOTS_DIR, exist_ok=True)
    with open(os.path.join(paths.SNAPSHOTS_DIR, f"{date}-discovery.json"),
              "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2)
    print(f"2. Discovery: {len(cards)} доменов, "
          f"{snapshot['конкурентов_в_основном_рейтинге']} в основном рейтинге")

    # Прошлый сравнимый день — для дельт, вердикта и динамики Threat
    earlier = [d for d in kpi_mod.available_snapshots() if d < date]
    previous = kpi_mod.load_snapshot(earlier[-1]) if earlier else None
    print(f"3. Сравнение с: {earlier[-1] if earlier else 'нет сравнимого дня'}")

    rivals = [d for d in (snapshot.get("лидеры") or []) if d["домен"] != OURS]
    ranked = threat_mod.rank(
        rivals,
        previous_cards=[d for d in ((previous or {}).get("лидеры") or [])
                        if d["домен"] != OURS],
        queries_total=len(usable))
    threat_leader = ranked[0] if ranked else None
    if threat_leader:
        print(f"4. Threat-лидер: {threat_leader[0]['домен']} "
              f"({threat_leader[1].score}, {threat_leader[1].confidence})")

    attacks = strike_list.to_dicts(strike_list.build(rows))
    with open(os.path.join(paths.PROCESSED_DIR, f"{date}-strike-list.json"),
              "w", encoding="utf-8") as fh:
        json.dump(attacks, fh, ensure_ascii=False, indent=2)
    print(f"5. Strike List: {len(attacks)} кандидатов в атаку")

    meta = build_email.build(date, snapshot, previous, attacks=attacks,
                             threat_leader=threat_leader)
    os.makedirs(paths.REPORTS_DIR, exist_ok=True)
    base = os.path.join(paths.REPORTS_DIR, f"{date}-email")
    with open(f"{base}.txt", "w", encoding="utf-8") as fh:
        fh.write(build_email.render_txt(meta))
    with open(f"{base}.html", "w", encoding="utf-8") as fh:
        fh.write(build_email.render_html(meta))
    with open(f"{base}.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)

    print(f"6. Письмо: {meta['видимых_символов']} символов из "
          f"{build_email.TEXT_LIMIT}, вердикт {meta['вердикт']}")
    if not meta["лимит_соблюдён"]:
        print("   ЛИМИТ ПРЕВЫШЕН — гейт качества не пропустит письмо")
        return 1
    print(f"   Файлы: {base}.{{html,txt,json}}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
