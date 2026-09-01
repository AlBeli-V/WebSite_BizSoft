#!/usr/bin/env python3
"""Growth Committee: еженедельное письмо решений (механика №40, §6 аудита).

Ежедневное письмо отвечает «что происходит», комитет — «что решаем».
Ровно пять вопросов: что выросло; что упало; почему (только подтверждённые
драйверы — неподтверждённая причина не называется вовсе); три сильнейшие
возможности; ≤5 действий следующей недели (allocator). Плюс два обязательных
блока: вердикты активных экспериментов (experiment_verdict) и подтверждение
исполнения (loop-health). Negative knowledge — реестр отклонённого, чтобы
не тестировать одно и то же дважды.

Окно: завершённая неделя понедельник–воскресенье перед датой отправки;
сравнение — с предыдущей такой же неделей (period_report.collect_metrics).

Запуск: python3 scripts/seo/committee.py [дата-отправки YYYY-MM-DD]
Выход:  reports/seo/intelligence/<дата>-committee-email.html и -committee.txt
        (отправляет workflow seo-committee-email по пушу в seo-data)
"""

from __future__ import annotations

import datetime as dt
import html
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from textfmt import num  # noqa: E402

BASE = pathlib.Path("reports/seo")
OUT_DIR = BASE / "intelligence"
NEGATIVE = OUT_DIR / "negative-knowledge.json"
DECISIONS = OUT_DIR / "experiment-decisions.jsonl"

# Гейт содержания: письмо не отправляется, если нарушает методику.
# NO_CRM: цели Метрики не равны обращениям клиентов. Стем «заяв», а не
# «заявк»: у слова беглая гласная («заявок»), и узкий стем пропускал бы
# ровно ту форму, которой чаще всего и пишут отчёты.
FORBIDDEN_WORDS = ("заяв",)
REQUIRED_BLOCKS = ("Что выросло", "Что упало", "Почему", "Возможности",
                   "Действия недели", "Вердикты экспериментов",
                   "Подтверждение исполнения")


def week_bounds(send_date: dt.date) -> tuple[dt.date, dt.date]:
    """Завершённая неделя пн–вс перед датой отправки."""
    last_sunday = send_date - dt.timedelta(days=send_date.isoweekday())
    return last_sunday - dt.timedelta(days=6), last_sunday


# ── Negative knowledge ──────────────────────────────────────────────────────

def refresh_negative_knowledge(date_s: str) -> dict:
    """Пополнить реестр отклонённого из журнала решений (append-only).

    Источник истины — experiment-decisions.jsonl (REJECTED/REVERT);
    реестр хранит краткую форму для дедупа allocator и блока письма.
    """
    entries = []
    if NEGATIVE.exists():
        try:
            entries = json.loads(
                NEGATIVE.read_text(encoding="utf-8")).get("entries", [])
        except (OSError, ValueError):
            entries = []
    known = {e.get("key") for e in entries}
    if DECISIONS.exists():
        for line in DECISIONS.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("verdict") not in ("REJECTED",) \
                    and d.get("decision") not in ("REVERT",):
                continue
            key = (d.get("experiment_id") or "").lower()
            if not key or key in known:
                continue
            known.add(key)
            entries.append({"key": key,
                            "what": d.get("experiment_id"),
                            "verdict": d.get("verdict") or d.get("decision"),
                            "date": d.get("date"),
                            "why": d.get("reason") or ""})
    data = {"updated": date_s, "entries": entries,
            "note": ("доказанно не работающее не тестируем повторно; "
                     "пополняется из журнала решений экспериментов")}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    NEGATIVE.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    return data


# ── Сборка данных письма ────────────────────────────────────────────────────

def build(date_s: str) -> dict:
    import period_report
    import allocator as allocator_mod
    import loop_health as loop_health_mod
    import experiments as experiments_mod
    import lifecycle as lifecycle_mod

    send = dt.date.fromisoformat(date_s)
    p_from, p_to = week_bounds(send)
    q_from, q_to = p_from - dt.timedelta(days=7), p_from - dt.timedelta(days=1)

    cur = period_report.collect_metrics(p_from, p_to)
    prev = period_report.collect_metrics(q_from, q_to)

    def delta(key):
        c, p = cur[key]["total"], prev[key]["total"]
        return {"label": cur[key]["label"], "cur": c, "prev": p,
                "pct": ((c - p) / p) if p else None,
                "covered": f"{cur[key]['covered_days']} из {cur[key]['days']} дн."}

    keys = ("yandex_impressions", "yandex_clicks", "gsc_impressions",
            "gsc_clicks", "visits_organic", "goals_organic")
    deltas = [delta(k) for k in keys]
    grown = [d for d in deltas if d["pct"] is not None and d["pct"] > 0.05]
    fallen = [d for d in deltas if d["pct"] is not None and d["pct"] < -0.05]
    flat = [d for d in deltas if d not in grown and d not in fallen]

    lc = lifecycle_mod.build(date_s)
    pages_up = [i for i in (lc.get("items") or []) if i.get("status") == "gaining"]
    pages_down = [i for i in (lc.get("items") or [])
                  if i.get("status") == "declining"]

    # «Почему»: только подтверждённые драйверы. Подтверждением считаем
    # события журнала действий и экспериментов внутри недели; корреляцию
    # без события не называем причиной.
    drivers = []
    try:
        acts = json.loads((OUT_DIR / "actions.json").read_text(encoding="utf-8"))
        for a in acts if isinstance(acts, list) else acts.get("actions", []):
            ch = a.get("status_changed_at") or ""
            if ch and p_from.isoformat() <= ch[:10] <= p_to.isoformat() \
                    and a.get("status") in ("deployed", "done", "observing"):
                drivers.append(f"{a.get('title')} — статус «{a.get('status_label') or a.get('status')}» "
                               f"с {ch[:10]}")
    except (OSError, ValueError):
        pass

    snap = allocator_mod._load_snapshot(date_s)
    import opportunity
    opps = opportunity.build(snap, date_s, limit=3)
    alloc = allocator_mod.write(date_s)
    lh = loop_health_mod.build(date_s)
    exps = experiments_mod.build(snap, date_s)
    negative = refresh_negative_knowledge(date_s)

    return {
        "date": date_s,
        "week": {"from": p_from.isoformat(), "to": p_to.isoformat()},
        "prev_week": {"from": q_from.isoformat(), "to": q_to.isoformat()},
        "deltas": deltas, "grown": grown, "fallen": fallen, "flat": flat,
        "pages_up": pages_up[:5], "pages_down": pages_down[:5],
        "drivers": drivers,
        "opportunities": opps,
        "allocator": alloc,
        "loop_health": lh,
        "experiments": exps,
        "negative": negative,
        "limits_note": ("Показы и клики — по выборкам Вебмастера и GSC (не весь "
                        "трафик); достижения целей Метрики не равны обращениям "
                        "в CRM; поисковые источники дозревают ~3 дня задним "
                        "числом."),
    }


# ── Рендер ──────────────────────────────────────────────────────────────────

def _fmt_delta(d: dict) -> str:
    pct = f" ({d['pct']:+.0%})" if d["pct"] is not None else ""
    return (f"{d['label']}: {num(d['prev'])} → {num(d['cur'])}{pct}, "
            f"данные {d['covered']}")


def _esc(s) -> str:
    return html.escape(str(s or ""))


def _sec(title: str, body: str) -> str:
    return (f'<h2 style="font:600 16px/1.3 Arial,sans-serif;margin:22px 0 8px;'
            f'color:#1a1a1a">{_esc(title)}</h2>{body}')


def _ul(rows: list[str]) -> str:
    if not rows:
        return '<p style="margin:4px 0;color:#666">—</p>'
    lis = "".join(f'<li style="margin:3px 0">{r}</li>' for r in rows)
    return f'<ul style="margin:4px 0 4px 18px;padding:0">{lis}</ul>'


def render(b: dict) -> tuple[str, str]:
    """HTML и plain-text письма."""
    wk = f"{b['week']['from']} — {b['week']['to']}"
    parts, lines = [], []
    lines.append(f"BIZSoft Growth Committee — неделя {wk}")

    grown_rows = [_esc(_fmt_delta(d)) for d in b["grown"]]
    grown_rows += [_esc(f"страница {p['page']}: показы {p['prev7']} → {p['last7']} за 7 дн.")
                   for p in b["pages_up"]]
    parts.append(_sec("1. Что выросло", _ul(grown_rows)))

    fallen_rows = [_esc(_fmt_delta(d)) for d in b["fallen"]]
    fallen_rows += [_esc(f"страница {p['page']}: показы {p['prev7']} → {p['last7']} за 7 дн.")
                    for p in b["pages_down"]]
    parts.append(_sec("2. Что упало", _ul(fallen_rows)))

    if b["drivers"]:
        why = _ul([_esc(d) for d in b["drivers"]])
    else:
        why = ('<p style="margin:4px 0;color:#666">Подтверждённых драйверов '
               'изменений на этой неделе нет — причины не называем: события '
               'внедрений в окно недели не попадали.</p>')
    parts.append(_sec("3. Почему (только подтверждённое)", why))

    opp_rows = []
    for i in (b["opportunities"].get("items") or []):
        opp_rows.append(f"<b>{_esc(i['cluster'])}</b> — {_esc(i['evidence'])}. "
                        f"Действие: {_esc(i['recommended_action'])}")
    parts.append(_sec("4. Возможности (топ-3)", _ul(opp_rows)))

    act_rows = []
    for i in (b["allocator"].get("items") or []):
        act_rows.append(f"<b>{i['rank']}. {_esc(i['title'])}</b> — "
                        f"{_esc(i['action'])}<br>"
                        f'<span style="color:#666">{_esc(i["evidence"])} '
                        f"[{_esc(i['source'])}]</span>")
    parts.append(_sec("5. Действия недели (allocator, ≤5)", _ul(act_rows)))

    exp_rows = []
    for e in b["experiments"]:
        ev = e.get("evaluation") or {}
        verdict = ev.get("verdict") or e.get("verdict")
        reason = ev.get("verdict_reason") or e.get("verdict_reason") or ""
        exp_rows.append(f"<b>{_esc(e['ticket'])}</b> (старт {_esc(e['start'])}, "
                        f"{e['days_elapsed']} дн.): {_esc(verdict)} — {_esc(reason)}")
    parts.append(_sec("Вердикты экспериментов", _ul(exp_rows)))

    lh_rows = []
    for r in b["loop_health"]["contours"]:
        mark = "ПРОСРОЧЕН" if r["overdue"] else "в срок"
        lh_rows.append(f"{_esc(r['label'])}: {mark}, последний прогон "
                       f"{_esc(r['last_run'] or '—')}")
    parts.append(_sec("Подтверждение исполнения (loop-health)",
                      _ul(lh_rows)))

    neg = b["negative"].get("entries") or []
    if neg:
        parts.append(_sec("Negative knowledge (не повторяем)",
                          _ul([f"{_esc(e['what'])}: {_esc(e['verdict'])} "
                               f"({_esc(e['date'])}) {_esc(e['why'])}"
                               for e in neg[-10:]])))

    parts.append(f'<p style="color:#666;font-size:12px;margin-top:18px">'
                 f'{_esc(b["limits_note"])}</p>')

    body = "".join(parts)
    html_doc = (
        '<div style="max-width:640px;margin:0 auto;font:14px/1.45 Arial,'
        'sans-serif;color:#222">'
        f'<h1 style="font:700 20px/1.3 Arial,sans-serif">BIZSoft Growth '
        f'Committee</h1>'
        f'<p style="color:#666">Неделя {_esc(wk)} (сравнение с '
        f'{_esc(b["prev_week"]["from"])} — {_esc(b["prev_week"]["to"])})</p>'
        + body + "</div>")

    # Plain-text: те же блоки без разметки.
    def strip(rows):
        import re
        return [re.sub("<[^>]+>", "",
                       r.replace("<br>", " — ")) for r in rows]
    lines += ["", "1. Что выросло:"] + (strip(grown_rows) or ["—"])
    lines += ["", "2. Что упало:"] + (strip(fallen_rows) or ["—"])
    lines += ["", "3. Почему:"] + ([d for d in b["drivers"]]
                                   or ["подтверждённых драйверов нет"])
    lines += ["", "4. Возможности:"] + (strip(opp_rows) or ["—"])
    lines += ["", "5. Действия недели:"] + (strip(act_rows) or ["—"])
    lines += ["", "Вердикты экспериментов:"] + (strip(exp_rows) or ["—"])
    lines += ["", "Loop-health:"] + strip(lh_rows)
    lines += ["", b["limits_note"]]
    return html_doc, "\n".join(lines)


def content_gate(html_doc: str) -> list[str]:
    """Нарушения методики, при которых письмо не отправляется."""
    problems = []
    low = html_doc.lower()
    for w in FORBIDDEN_WORDS:
        if w in low:
            problems.append(f"запрещённое слово «{w}» (NO_CRM)")
    for block in REQUIRED_BLOCKS:
        if block.lower() not in low:
            problems.append(f"нет обязательного блока «{block}»")
    return problems


def main() -> int:
    date_s = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(
        dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    b = build(date_s)
    html_doc, plain = render(b)
    problems = content_gate(html_doc)
    if problems:
        print("committee: письмо НЕ собрано, гейт не пройден:")
        for p in problems:
            print(f"  - {p}")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{date_s}-committee-email.html").write_text(
        html_doc, encoding="utf-8")
    (OUT_DIR / f"{date_s}-committee.txt").write_text(plain, encoding="utf-8")
    print(f"committee: письмо за неделю {b['week']['from']}—{b['week']['to']} "
          f"собрано -> {OUT_DIR / (date_s + '-committee-email.html')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
