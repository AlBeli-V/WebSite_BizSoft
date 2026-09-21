#!/usr/bin/env python3
"""Кандидаты для рекламы: корпоративный спрос там, где нас нет в выдаче.

Решение руководителя 21.09.2026 после разбора трёх недель рекламы
(reports/marketing/ads-vs-organic-2026-09-21.md): рекламировать только те
формулировки, по которым приходят заявки, и только там, где мы не стоим
в выдаче сами — платить за собственный трафик смысла нет.

Три условия отбора, все обязательны:

  1. Корпоративный интент. Заявки приходят по фразам, где человек сам
     назвал себя юрлицом: 74% кликов органики против 8% в рекламе.
     Розничные и пиратские формы («ключ активации», «как обойти»)
     отбраковываются отдельно — на них ушла заметная часть прошлого
     бюджета.
  2. Спрос измерен. Частота Wordstat не ниже порога: реклама по фразе,
     которую не ищут, не окупит даже управления собой.
  3. Мы не забираем этот трафик сами. Порог — первая тройка, а не
     первая страница: по «adobe купить для компании» мы на позиции 1,3 и
     получаем 46 кликов из 47 показов, а на позициях от третьей и ниже
     при полусотне показов кликов ноль. Реклама пересекается с органикой
     только в самом верху выдачи.

Посадочная проверяется отдельно и не отсеивает кандидата: спрос без
страницы — это задача каталогу, а не повод забыть про фразу. Такие
строки помечаются и выносятся в конец отчёта.

Запуск: python3 scripts/seo/wordstat/ad_targets.py [--min-frequency N]
        [--serp reports/seo/serp/<дата>-serp.jsonl]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re

UNIVERSE = pathlib.Path("reports/seo/wordstat/semantic-universe.jsonl")
# Целевой замер корпоративного спроса живёт отдельным файлом: в общую базу
# он не пишется, чтобы не заводить кластер на каждую фразу вида
# «оплата <вендор> юридическим лицом» (см. corporate_demand.py).
CORPORATE = pathlib.Path("reports/seo/wordstat/corporate-demand.json")
SERP_DIR = pathlib.Path("reports/seo/serp")
WEBMASTER_DIR = pathlib.Path("reports/seo/data")
OUT_JSON = pathlib.Path("reports/seo/wordstat/ad-targets.json")
OUR_DOMAIN = "biz-soft"

# Признак того, что человек покупает на организацию. Список собран по
# запросам Вебмастера, которые реально привели заявки, а не придуман.
#
# Признаков два вида, и смешивать их нельзя. Сильный — русская формулировка,
# которую в запрос добавляет именно покупатель от организации. Слабый —
# английские business / enterprise / teams: чаще всего это часть названия
# тарифа или самого продукта. «Microsoft Teams» с ежемесячным спросом 16 439
# — мессенджер, а не корпоративный интент, и первый же прогон отбора притащил
# его в кандидаты. Поэтому слабый признак засчитывается только вместе с
# покупательским словом: «notion business купить» — да, «microsoft teams» — нет.
B2B_STRONG = re.compile(
    r"для компан|для юл\b|юридическ|юрлиц|юр\.? ?лиц|для организац|корпоратив"
    r"|на команду|для команд|коммерческ|для предприят|для бизнеса|договор"
    r"|закрывающ|безнал|с ндс|для сотрудник",
    re.I)
B2B_WEAK = re.compile(r"\bbusiness\b|\benterprise\b|\bteams\b", re.I)
BUYING = re.compile(r"купить|оплат|оплатить|цена|стоимост|подписк|лицензи|тариф|счет|счёт", re.I)


def is_b2b(phrase: str) -> bool:
    """Корпоративный ли интент: сильный признак сам по себе, слабый — с покупкой."""
    if B2B_STRONG.search(phrase):
        return True
    return bool(B2B_WEAK.search(phrase) and BUYING.search(phrase))
# Розница и пиратство: на такие фразы ушла часть прошлого бюджета впустую.
RETAIL = re.compile(
    r"ключ|активац|обойти|взлом|кряк|crack|торрент|бесплатн|скачать"
    r"|для пк\b|на айпад|на ipad|личн|себе\b",
    re.I)
# Глубина, на которой выдача реально забирает клик. Взято из фактов
# Вебмастера, а не из общего правила «топ-10»: по «adobe купить для компании»
# мы на позиции 1,3 и получаем 46 кликов из 47 показов, а на позициях 2,6–7,3
# («оплата artlist юридическим лицом», «оформление zoom business для
# организации из рф») при 39–74 показах кликов ноль. Значит первая страница
# выдачи сама по себе трафика не даёт, и реклама пересекается с органикой
# только в первой тройке.
TOP_DEPTH = 3


def load_universe(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"нет базы семантики {path} — сначала data_sync.sh pull")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_corporate(path: pathlib.Path) -> list[dict]:
    """Фразы целевого замера в том же виде, что строки базы семантики."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [{
        "phrase": r["phrase"],
        "wordstat_frequency": r.get("frequency") or 0,
        "vendor": r.get("vendor"),
        "category": r.get("category"),
        "mapped_url": r.get("url"),
        "page_exists": bool(r.get("url")),
    } for r in (data.get("phrases") or [])]


def latest(path: pathlib.Path, pattern: str) -> pathlib.Path | None:
    files = sorted(path.glob(pattern))
    return files[-1] if files else None


def serp_positions(path: pathlib.Path | None) -> dict[str, int | None]:
    """Позиция нашего домена по каждому запросу среза; None — нас в топе нет."""
    if path is None or not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        pos = None
        for i, item in enumerate(row.get("top") or [], 1):
            if OUR_DOMAIN in (item.get("domain") or ""):
                pos = i
                break
        out[row["query"].strip().lower()] = pos
    return out


def webmaster_positions(path: pathlib.Path | None) -> dict[str, float]:
    """Средняя позиция показа по запросам Вебмастера.

    Вебмастер видит то, чего нет в срезе выдачи: он перечисляет все фразы, по
    которым сайт показывался, а срез снимается только по контрольному ядру.
    """
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for q in ((data.get("popular_queries") or {}).get("queries") or []):
        ind = q.get("indicators") or {}
        pos = ind.get("AVG_SHOW_POSITION")
        if pos:
            out[q["query_text"].strip().lower()] = float(pos)
    return out


def classify(row: dict, serp: dict, webmaster: dict, min_frequency: int,
             catalog=None, intent: str = "b2b") -> tuple[bool, str, float | None]:
    """Годится ли фраза в рекламу. Возвращает (годится, причина, позиция).

    Четвёртое условие появилось 21.09.2026: позиция должна быть ЗАМЕРЕНА.
    Раньше «мы не смотрели» и «смотрели, нас там нет» давали один и тот же
    исход — фраза проходила как свободная. Так правило «только вне первой
    тройки» применялось к одному проценту спроса, а за остальные 99% мы
    рисковали платить за собственный трафик. Незамеренное теперь уходит
    в очередь замера (serp_queue), а не в рекламу.
    """
    phrase = row["phrase"].strip().lower()
    # Два признака интента, и выбор между ними — решение о том, за что платим.
    # b2b — формулировки, по которым приходили заявки: их мало, но они точны.
    # commercial — весь покупательский спрос с привязкой к карточке: «под
    # остальные ищем коммерческий спрос, даже если его мало» (решение
    # руководителя 21.09.2026). Второй режим без привязки к каталогу и без
    # замера позиции не работает — иначе это возврат к слепым показам.
    if intent == "b2b":
        if not is_b2b(phrase):
            return False, "нет корпоративного признака", None
    elif (row.get("commercial_intent_score") or 0) < 0.5:
        return False, "нет покупательского интента", None
    if RETAIL.search(phrase):
        return False, "розничный или пиратский интент", None
    if (row.get("wordstat_frequency") or 0) < min_frequency:
        return False, f"спрос ниже {min_frequency} в месяц", None
    if catalog is not None:
        m = catalog.match(row["phrase"])
        if m["kind"] == "none":
            return False, f"нечего продавать: {m['why']}", None
    wm = webmaster.get(phrase)
    if phrase not in serp and wm is None:
        return False, "позиция не замерена — фраза в очереди замера", None
    pos = serp.get(phrase)
    best = min([p for p in (pos, wm) if p], default=None)
    if best is not None and best <= TOP_DEPTH:
        return False, f"мы забираем этот трафик сами, позиция {best:.1f}", best
    return True, "спрос есть, замер сделан, органики нет", best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-frequency", type=int, default=30)
    ap.add_argument("--intent", choices=("b2b", "commercial"), default="b2b",
                    help="b2b — корпоративные формулировки; commercial — весь "
                         "покупательский спрос с привязкой к карточке")
    ap.add_argument("--serp", default=None)
    args = ap.parse_args()

    rows = load_universe(UNIVERSE)
    corporate = load_corporate(CORPORATE)
    catalog = None
    try:
        import catalog_match
        catalog = catalog_match.Catalog()
        print(f"Каталог: {len(catalog.cards)} карточек на витрине")
    except SystemExit as e:
        print(f"Каталог недоступен ({e}) — привязка к товарам не проверяется")
    if corporate:
        # Фразы замера идут первыми: при совпадении побеждает свежая частота.
        seen = {r["phrase"].strip().lower() for r in corporate}
        rows = corporate + [r for r in rows if r["phrase"].strip().lower() not in seen]
    serp_path = pathlib.Path(args.serp) if args.serp else latest(SERP_DIR, "*-serp.jsonl")
    wm_path = latest(WEBMASTER_DIR, "yandex-2026-*.json")
    # Позиции собираются со всего архива срезов, а не с последнего файла:
    # ядро дня — 650 запросов, а замер очереди мог пройти неделю назад, и
    # выбрасывать его значило бы замерять повторно за деньги.
    serp = {}
    if args.serp:
        serp = serp_positions(serp_path)
    else:
        for path in sorted(SERP_DIR.glob("*-serp.jsonl")):
            serp.update(serp_positions(path))
    webmaster = webmaster_positions(wm_path)
    print(f"База семантики: {len(rows)} фраз (целевой замер: {len(corporate)})")
    print(f"Срез выдачи: {serp_path.name if serp_path else 'нет'} ({len(serp)} запросов)")
    print(f"Запросы Вебмастера: {wm_path.name if wm_path else 'нет'} ({len(webmaster)} с позицией)")

    picked, skipped = [], {}
    for row in rows:
        ok, why, pos = classify(row, serp, webmaster, args.min_frequency,
                                catalog, args.intent)
        if ok:
            m = catalog.match(row["phrase"]) if catalog else {}
            picked.append({
                "phrase": row["phrase"],
                "frequency": row.get("wordstat_frequency") or 0,
                "vendor": m.get("vendor") or row.get("vendor"),
                "category": row.get("category"),
                # Посадочная — карточка, на которую фраза села, а не страница
                # вендора из базы: база маппит на вендора вообще всё.
                "url": m.get("url") or row.get("mapped_url"),
                "match": m.get("kind"),
                "page_exists": bool(m.get("url") or row.get("page_exists")),
                "position": pos,
            })
        else:
            skipped[why] = skipped.get(why, 0) + 1

    picked.sort(key=lambda r: -r["frequency"])
    ready = [r for r in picked if r["page_exists"]]
    nopage = [r for r in picked if not r["page_exists"]]

    print(f"\n== Отсеяно ==")
    for why, n in sorted(skipped.items(), key=lambda kv: -kv[1]):
        print(f"  {n:6} — {why}")

    print(f"\n== Кандидаты для рекламы: {len(ready)} фраз с посадочной ==")
    print(f"  суммарный спрос: {sum(r['frequency'] for r in ready)} запросов в месяц")
    by_vendor: dict[str, list] = {}
    for r in ready:
        by_vendor.setdefault(r["vendor"] or "без вендора", []).append(r)
    for vendor, items in sorted(by_vendor.items(), key=lambda kv: -sum(x["frequency"] for x in kv[1])):
        total = sum(x["frequency"] for x in items)
        print(f"\n  {vendor} — {total} в месяц, {len(items)} фраз, {items[0]['url']}")
        for r in items[:6]:
            seen = "нет в выдаче" if r["position"] is None else f"позиция {r['position']:.0f}"
            print(f"    {r['frequency']:6}  {r['phrase']}  [{seen}]")

    if nopage:
        print(f"\n== Спрос без посадочной: {len(nopage)} фраз — это задача каталогу ==")
        for r in nopage[:12]:
            print(f"  {r['frequency']:6}  {r['phrase']}  ({r['vendor']})")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "generated_for": "рекламные группы по корпоративному спросу",
        "intent": args.intent,
        "min_frequency": args.min_frequency,
        "serp_source": serp_path.name if serp_path else None,
        "webmaster_source": wm_path.name if wm_path else None,
        "ready": ready, "without_page": nopage,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nСписок сохранён: {OUT_JSON}")


if __name__ == "__main__":
    main()
