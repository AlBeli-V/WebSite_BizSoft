#!/usr/bin/env python3
"""Сборка ежедневного письма конкурентной разведки.

Формат зафиксирован разделом 23 задания: VERDICT → KPI → MAIN SIGNAL →
DO NEXT → WATCH. В Phase 1 письмо выходит в MVP-виде (первые три блока плюс
пометка зрелости скоринга); DO NEXT и WATCH появляются в Phase 2 вместе с
Opportunity и Threat.

Два жёстких ограничения, которые проверяются перед отправкой:
  * основная текстовая часть ≤ 1000 видимых символов (оптимум 500–850);
  * письмо читаемо без картинок — графики появятся в Phase 2, и у каждого
    будет alt-текст с цифрами.

Пишет три файла в reports/competitive/: <дата>-email.html, <дата>-email.txt
и <дата>-email.json (метаданные для гейтов качества и анти-повтора).
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402
from decision_engine import kpi as kpi_mod  # noqa: E402
from decision_engine import signal as signal_mod  # noqa: E402

MSK = timezone(timedelta(hours=3))
TEXT_LIMIT = 1000
REPORT_URL = "https://biz-soft.pro/ci-<токен>/latest/"


def visible_text(kpi, verdict_mark, verdict_why, signal) -> str:
    """Основная текстовая часть письма — то, что считается против лимита.

    Ссылки, подписи и футер в лимит не входят (раздел 23), поэтому здесь
    собирается ровно смысловое содержание.
    """
    lines = [
        f"{verdict_mark} {verdict_why}.",
        (f"B2B Share Яндекс {kpi_mod.format_share(kpi.share_yandex)} "
         f"(Δ7д {kpi_mod.format_delta(kpi.share_delta_pp, unit=' п.п.')}) · "
         f"Google {kpi_mod.format_share(kpi.share_google)} · "
         f"ТОП-3 {kpi.top3}/{kpi.queries} · ТОП-10 {kpi.top10}/{kpi.queries}."),
        f"Главный сигнал: {signal.text}",
    ]
    return "\n".join(lines)


def build(date: str, snapshot: dict, previous: dict | None) -> dict:
    kpi = kpi_mod.build_kpi(snapshot, previous)
    verdict_mark, verdict_why = kpi_mod.verdict(kpi)
    signal = signal_mod.pick(snapshot, previous)
    text = visible_text(kpi, verdict_mark, verdict_why, signal)

    coverage = snapshot.get("покрытие") or {}
    subject = (f"Конкурентная разведка · "
               f"{datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')} · "
               f"{verdict_mark}")

    return {
        "дата": date,
        "тема": subject,
        "вердикт": verdict_mark,
        "текст": text,
        "видимых_символов": len(text),
        "лимит_символов": TEXT_LIMIT,
        "лимит_соблюдён": len(text) <= TEXT_LIMIT,
        "зрелость_скоринга": kpi.maturity,
        "сигнал_тип": signal.kind,
        "сигнал_хэш": hashlib.sha256(signal.text.encode()).hexdigest()[:16],
        "покрытие": coverage,
        "сравнение_с": kpi.compared_with,
        "kpi": {
            "share_yandex": kpi.share_yandex,
            "share_google": kpi.share_google,
            "top3": kpi.top3,
            "top10": kpi.top10,
            "queries": kpi.queries,
            "share_delta_pp": kpi.share_delta_pp,
        },
    }


def render_txt(meta: dict) -> str:
    """Текстовая версия — полноценная, а не огрызок для спам-фильтра."""
    return "\n".join([
        meta["тема"],
        "",
        meta["текст"],
        "",
        f"Полная аналитика: {REPORT_URL}",
        "",
        f"Scoring: {meta['зрелость_скоринга']} · "
        f"источник: Яндекс (Москва), {meta['покрытие'].get('яндекс_запросов_с_данными')} запросов · "
        f"Google: {'NO DATA' if meta['kpi']['share_google'] is None else 'есть'} · "
        "B2C и маркетплейсы вне основного рейтинга · NO DATA не равно нулю.",
    ])


def render_html(meta: dict) -> str:
    """HTML-версия. Инлайн-стили и таблица — требование почтовых клиентов."""
    k = meta["kpi"]
    esc = html.escape
    delta = kpi_mod.format_delta(k["share_delta_pp"], unit=" п.п.")
    verdict_line, kpi_line, signal_line = meta["текст"].split("\n")
    google_share = ("NO DATA" if k["share_google"] is None
                    else f"{100 * k['share_google']:.1f}%")
    yandex_share = ("NO DATA" if k["share_yandex"] is None
                    else f"{100 * k['share_yandex']:.1f}%")

    def cell(label: str, value: str, note: str) -> str:
        return (
            '<td style="padding:8px;border:1px solid #EAECF0;border-radius:6px;">'
            f'<div style="color:#667085;font-size:11px;">{esc(label)}</div>'
            f'<div style="font-size:20px;font-weight:700;">{esc(value)}</div>'
            f'<div style="color:#98A2B3;font-size:11px;">{esc(note)}</div></td>')

    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(meta['тема'])}</title></head>
<body style="margin:0;padding:0;background:#f4f5f7;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;">
<tr><td align="center" style="padding:16px 8px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border:1px solid #EAECF0;border-radius:8px;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#101828;">
<tr><td style="padding:20px 24px 6px;">
<div style="font-size:12px;color:#667085;letter-spacing:.04em;">BIZSOFT · КОНКУРЕНТНАЯ РАЗВЕДКА · {esc(meta['дата'])}</div>
</td></tr>
<tr><td style="padding:6px 24px;"><div style="font-size:17px;font-weight:700;">{esc(verdict_line)}</div></td></tr>
<tr><td style="padding:10px 24px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:13px;"><tr>
{cell('B2B Share · Яндекс', yandex_share, f'Δ7д: {delta}')}<td style="width:6px;"></td>
{cell('B2B Share · Google', google_share, 'еженедельный сбор')}<td style="width:6px;"></td>
{cell('ТОП-3', f"{k['top3']}/{k['queries']}", 'запросов')}<td style="width:6px;"></td>
{cell('ТОП-10', f"{k['top10']}/{k['queries']}", 'запросов')}
</tr></table></td></tr>
<tr><td style="padding:12px 24px 0;">
<div style="font-size:11px;color:#667085;letter-spacing:.06em;font-weight:700;">ГЛАВНЫЙ СИГНАЛ</div>
<div style="font-size:14px;line-height:1.45;padding-top:4px;">{esc(signal_line.removeprefix('Главный сигнал: '))}</div>
</td></tr>
<tr><td style="padding:18px 24px 20px;" align="center">
<a href="{REPORT_URL}" style="display:inline-block;background:#101828;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;padding:10px 22px;border-radius:6px;">Открыть полную конкурентную аналитику →</a>
</td></tr>
<tr><td style="padding:0 24px 18px;border-top:1px solid #EAECF0;">
<div style="font-size:11px;color:#98A2B3;padding-top:10px;line-height:1.5;">
Scoring: {esc(meta['зрелость_скоринга'])} · источник: Яндекс (Москва), {esc(str(meta['покрытие'].get('яндекс_запросов_с_данными')))} запросов ·
Google: {esc(google_share)} · B2C и маркетплейсы вне основного рейтинга · NO DATA не равно нулю.
</div></td></tr>
</table></td></tr></table></body></html>"""


def main(argv: list[str]) -> int:
    dates = kpi_mod.available_snapshots()
    if not dates:
        print("Снимков нет — сначала нужен прогон discovery")
        return 1
    date = argv[1] if len(argv) > 1 else dates[-1]
    snapshot = kpi_mod.load_snapshot(date)
    if snapshot is None:
        print(f"Снимка за {date} нет. Доступны: {', '.join(dates)}")
        return 1
    earlier = [d for d in dates if d < date]
    previous = kpi_mod.load_snapshot(earlier[-1]) if earlier else None

    meta = build(date, snapshot, previous)
    os.makedirs(paths.REPORTS_DIR, exist_ok=True)
    base = os.path.join(paths.REPORTS_DIR, f"{date}-email")
    with open(f"{base}.txt", "w", encoding="utf-8") as fh:
        fh.write(render_txt(meta))
    with open(f"{base}.html", "w", encoding="utf-8") as fh:
        fh.write(render_html(meta))
    with open(f"{base}.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)

    print(f"Тема: {meta['тема']}")
    print(f"Видимых символов: {meta['видимых_символов']} из {TEXT_LIMIT} "
          f"({'в пределах лимита' if meta['лимит_соблюдён'] else 'ЛИМИТ ПРЕВЫШЕН'})")
    print(f"Сравнение с: {meta['сравнение_с'] or 'нет сравнимого дня'}")
    print(f"Файлы: {base}.{{html,txt,json}}")
    return 0 if meta["лимит_соблюдён"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
