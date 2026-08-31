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

    # Свежий срез может оказаться пустым: сбор базового контура падает целиком
    # (например, сеть раннера не разрешила имя API — так было 31.08.2026, все
    # 502 запроса вернули ошибку). Требование раздела 24 задания: письмо в
    # такой день всё равно уходит, но с вердиктом «недостаточно данных» и без
    # сильных выводов. Молчание хуже: руководитель не отличит сбой от тишины.
    stale_notice = None
    if not usable and len(argv) <= 1:
        fallback = next((d for d in reversed(dates) if d != date
                         and any(r.has_data for r in serp_source.read_snapshot(d))),
                        None)
        if fallback is None:
            print("   Пригодных срезов нет вообще — письмо не собирается")
            return 1
        stale_notice = (f"свежий сбор за {date} не удался "
                        f"({len(rows)} запросов с ошибкой), "
                        f"показаны данные за {fallback}")
        print(f"   Сбор за {date} пуст — откат на последний пригодный срез {fallback}")
        date = fallback
        rows = serp_source.read_snapshot(date)
        usable = [r for r in rows if r.has_data]
    elif not usable:
        print("   Данных нет — письмо не собирается")
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

    # История долей по дням — для динамики Threat и вердикта. Собирается из
    # сохранённых снимков: сравнимые измерения, а не соседние точки.
    histories: dict[str, list[float]] = {}
    our_history: list[float] = []
    for past_date in kpi_mod.available_snapshots():
        if past_date > date:
            continue
        past = kpi_mod.load_snapshot(past_date) or {}
        for leader in (past.get("лидеры") or []):
            histories.setdefault(leader["домен"], []).append(leader.get("доля") or 0.0)
        share = (past.get("наши_показатели") or {}).get("доля_видимости")
        if share is not None:
            our_history.append(share)

    rivals = [d for d in (snapshot.get("лидеры") or []) if d["домен"] != OURS]
    ranked = threat_mod.rank(rivals, histories=histories,
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

    from attack_engine import work_packages
    packages = work_packages.to_dicts(work_packages.build(attacks, config))
    with open(os.path.join(paths.PROCESSED_DIR, f"{date}-work-packages.json"),
              "w", encoding="utf-8") as fh:
        json.dump(packages, fh, ensure_ascii=False, indent=2)
    countable = [p for p in packages if p["traffic_upside"] is not None]
    high = sum(1 for p in packages if p["potential_label"] == "высокий")
    print(f"6. Пакеты работ: {len(packages)}, из них {high} с высоким "
          f"потенциалом; переходы считаются для {len(countable)} "
          f"(сопоставимый спрос)")

    meta = build_email.build(date, snapshot, previous, attacks=attacks,
                             threat_leader=threat_leader,
                             stale_notice=stale_notice, ranked_rivals=ranked,
                             packages=packages, history=our_history)
    kpi_obj = kpi_mod.build_kpi(snapshot, previous)
    os.makedirs(paths.REPORTS_DIR, exist_ok=True)
    base = os.path.join(paths.REPORTS_DIR, f"{date}-email")
    with open(f"{base}.txt", "w", encoding="utf-8") as fh:
        fh.write(build_email.render_txt(meta, snapshot=snapshot, attacks=attacks,
                                        ranked_rivals=ranked, packages=packages))
    with open(f"{base}.html", "w", encoding="utf-8") as fh:
        fh.write(build_email.render_html(meta, kpi=kpi_obj, snapshot=snapshot,
                                         attacks=attacks, ranked_rivals=ranked,
                                         packages=packages))
    with open(f"{base}.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)

    print(f"7. Письмо: {meta['видимых_символов']} символов из "
          f"{build_email.TEXT_LIMIT}, вердикт {meta['вердикт']}")
    if not meta["лимит_соблюдён"]:
        print("   ЛИМИТ ПРЕВЫШЕН — гейт качества не пропустит письмо")
        return 1

    # Deep report — то, на что ведёт кнопка письма. Собирается тем же
    # прогоном: иначе ссылка показывала бы вчерашнюю аналитику под сегодняшним
    # письмом, а это хуже отсутствующей ссылки.
    from reports import deep_report
    page = deep_report.build(date, snapshot, previous, attacks,
                             [c.__dict__ for c in cards], rows,
                             packages=packages, histories=histories)
    os.makedirs(paths.ARCHIVE_DIR, exist_ok=True)
    for target in (os.path.join(paths.ARCHIVE_DIR, f"{date}.html"),
                   os.path.join(paths.REPORTS_DIR, "latest.html")):
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(page)
    print(f"8. Deep report: {len(page.encode()) / 1024:.0f} КБ "
          f"(архив + latest.html)")
    print(f"   Файлы письма: {base}.{{html,txt,json}}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
