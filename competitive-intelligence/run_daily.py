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

    # История долей по дням — для динамики Threat и вердикта.
    #
    # Ряд по нашей доле строится не из сохранённых чисел, а пересчётом по
    # пересечению составов ядра (kpi.comparable_series): доля считается
    # внутри поля, и если состав запросов между днями менялся, «изменение
    # доли» смешивало бы движение конкурентов с редактированием списка.
    # Для конкурентов такого пересчёта нет — по-доменной видимости по каждому
    # запросу мы не храним, — поэтому там действует более грубое правило:
    # динамика считается, только если состав ядра во всех днях ряда совпадал.
    histories: dict[str, list[float]] = {}
    past_snapshots: list[dict] = []
    for past_date in kpi_mod.available_snapshots():
        if past_date > date:
            continue
        past = kpi_mod.load_snapshot(past_date) or {}
        past_snapshots.append(past)
        for leader in (past.get("лидеры") or []):
            histories.setdefault(leader["домен"], []).append(leader.get("доля") or 0.0)
    # Свежий снимок за сегодня уже записан на диск, поэтому он в ряду есть.
    our_history, core_meta = kpi_mod.comparable_series(past_snapshots)
    core_hashes = {kpi_mod.core_hash(s) for s in past_snapshots if kpi_mod.core_hash(s)}
    core_stable = len(core_hashes) <= 1
    core_note = core_meta.get("причина") or (
        "" if core_stable else "состав ядра между днями менялся")
    print(f"3а. Сравнимый ряд: {len(our_history)} измерений"
          + (f" по пересечению из {core_meta.get('пересечение')} запросов"
             if core_meta.get("пересечение") else "")
          + (f"; {core_note}" if core_note else ""))

    rivals = [d for d in (snapshot.get("лидеры") or []) if d["домен"] != OURS]
    ranked = threat_mod.rank(rivals, histories=histories,
                             queries_total=len(usable),
                             core_stable=core_stable)
    threat_leader = ranked[0] if ranked else None
    if threat_leader:
        print(f"4. Threat-лидер: {threat_leader[0]['домен']} "
              f"({threat_leader[1].score}, {threat_leader[1].confidence})")

    attacks = strike_list.to_dicts(strike_list.build(rows))
    with open(os.path.join(paths.PROCESSED_DIR, f"{date}-strike-list.json"),
              "w", encoding="utf-8") as fh:
        json.dump(attacks, fh, ensure_ascii=False, indent=2)
    print(f"5. Strike List: {len(attacks)} кандидатов в атаку")

    from attack_engine import page_audit, recommendations, work_packages
    packages = work_packages.to_dicts(work_packages.build(attacks, config))

    # Позиции по регионам — основание для гео-действия. Считается только там,
    # где запрос измерен в обоих регионах: сравнивать позицию в Москве с
    # отсутствием замера в Петербурге бессмысленно.
    geo_by_query: dict[str, list] = {}
    for row in rows:
        if not row.has_data:
            continue
        position = next((index for index, item in enumerate(row.top, start=1)
                         if serp_source.normalize_domain(item.get("domain", "")) == OURS),
                        None)
        entry = geo_by_query.setdefault(page_audit.normalize(row.query), [None, None])
        if row.region == "213":
            entry[0] = position
        elif row.region == "2":
            entry[1] = position

    # Исполнительная часть: что именно сделать на каждой странице. Пакеты уже
    # отсортированы и оценены — здесь добавляются только действия.
    # Порядок действий внутри пакета подстраивается под накопленный опыт —
    # но только по типам, где экспериментов уже достаточно (см. learning).
    from experiments import journal as _journal
    from experiments import learning as _learning
    effect_ranking = _learning.ranking(_journal.load(), config)
    recommendations.enrich(packages, geo_by_query, effect_ranking)

    # --- цикл экспериментов -------------------------------------------------
    # Порядок шагов важен. Сначала отмечаем внедрённое и оцениваем созревшее:
    # обе операции смотрят в прошлое. Потом убираем из поручений страницы под
    # мораторием. И только потом заводим эксперименты по тому, что осталось —
    # иначе страница, ушедшая на наблюдение, тут же получила бы новый опыт.
    from experiments import journal as exp_journal
    from experiments import learning as exp_learning
    from experiments import lifecycle as exp_lifecycle

    snapshots_by_date = {}
    for past_date in kpi_mod.available_snapshots():
        if past_date <= date:
            snapshots_by_date[past_date] = kpi_mod.load_snapshot(past_date) or {}

    experiments = exp_journal.load()
    implemented = exp_lifecycle.detect_implementation(
        experiments, snapshots_by_date, date, config)
    evaluated = exp_lifecycle.evaluate_due(
        experiments, snapshots_by_date, date, config)
    frozen = exp_lifecycle.moratorium(experiments)

    # Страницы на наблюдении не попадают в поручения: правка уже внесена, идёт
    # замер эффекта. Они не исчезают из отчёта — для них отдельный раздел.
    on_watch = [p for p in packages if p["url"] in frozen]
    packages = [p for p in packages if p["url"] not in frozen]
    for package in on_watch:
        experiment = frozen[package["url"]]
        package["мораторий_до"] = experiment.watch_until
        package["эксперимент"] = experiment.id

    created = exp_lifecycle.register(experiments, packages, date)
    exp_journal.save(experiments)
    print(f"6а. Эксперименты: заведено {len(created)}, подтверждено внедрение "
          f"{len(implemented)}, оценено {len(evaluated)}, под мораторием "
          f"{len(on_watch)} страниц")
    with open(os.path.join(paths.PROCESSED_DIR, f"{date}-work-packages.json"),
              "w", encoding="utf-8") as fh:
        json.dump(packages, fh, ensure_ascii=False, indent=2)
    countable = [p for p in packages if p["traffic_upside"] is not None]
    high = sum(1 for p in packages if p["potential_label"] == "высокий")
    unscored = sum(1 for p in packages if p["potential_index"] is None)
    print(f"6. Пакеты работ: {len(packages)}, из них {high} с высоким "
          f"потенциалом; переходы считаются для {len(countable)} "
          f"(сопоставимый спрос); без измеренного спроса и потому без "
          f"индекса — {unscored}")

    meta = build_email.build(date, snapshot, previous, attacks=attacks,
                             threat_leader=threat_leader,
                             stale_notice=stale_notice, ranked_rivals=ranked,
                             packages=packages, history=our_history,
                             core_note=core_note,
                             experiments_line=exp_learning.summary_line(
                                 experiments, config))
    kpi_obj = kpi_mod.build_kpi(snapshot, previous)
    os.makedirs(paths.REPORTS_DIR, exist_ok=True)
    base = os.path.join(paths.REPORTS_DIR, f"{date}-email")
    with open(f"{base}.txt", "w", encoding="utf-8") as fh:
        fh.write(build_email.render_txt(meta, snapshot=snapshot, attacks=attacks,
                                        ranked_rivals=ranked, packages=packages))
    with open(f"{base}.html", "w", encoding="utf-8") as fh:
        fh.write(build_email.render_html(
            meta, kpi=kpi_obj, snapshot=snapshot, attacks=attacks,
            ranked_rivals=ranked, packages=packages,
            signal_delta=meta.get("дельта_сигнальная_пп"),
            on_watch=on_watch))
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
                             packages=packages, histories=histories,
                             experiments=experiments, config=config,
                             on_watch=on_watch)
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
