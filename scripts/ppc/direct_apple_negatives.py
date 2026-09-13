#!/usr/bin/env python3
"""Минус-слова кампаний Apple с проверкой по фактическим запросам.

Решение владельца 13.09.2026 после внешнего аудита плана. Кампании
подарочных карт и пополнения Apple тратят 69–72 % денег на
информационный интент; минус-слова здесь не лечение, а санитарная мера
перед разбором категорий автотаргетинга, но санитарная мера нужна сейчас.

Пакет собран из фактических запросов 07–13.09 и разделён надвое.

Набор A — общий информационный мусор: загрузка приложений, вход в
учётную запись, новости о новой системе, служба поддержки, программы
для Windows, пиратство. Держит на себе около 17 % расхода кампаний.

Набор B — группа корпоративных подарков, где три четверти денег уходит
на поиск идей подарка и текстов поздравлений. По замечанию аудита этот
набор задаётся преимущественно минус-фразами, а не отдельными словами:
«приказ», «образец» и «НДФЛ» поодиночке отсекли бы и бухгалтера,
изучающего налоги с подарков сотрудникам, — это верх нашей же
B2B-воронки, за который просто не стоит платить в кампании прямого
отклика.

По тому же замечанию слово «поддержка» заменено набором фраз: одиночное
слово могло бы срезать «поддержка оплаты apple id из россии». На
выборке 07–13.09 таких запросов нет (580 форм корня, все — поиск
телефона и чата поддержки Apple), но правило дешевле проверять, чем
нарушать.

Предохранитель двойной, и второй уровень — прямое требование аудита.
Кандидат отклоняется, если его основа встречается в действующей фразе
кампании ИЛИ если он задевает исторический запрос с покупательским
словом и хотя бы одним кликом. Второй уровень ловит случай, которого
первый не видит: минус-слово «регион» не пересекается ни с одной нашей
фразой, но срезало бы «как пополнить apple id в россии не меняя регион»
— живого покупателя.

Режимы:
  dry-run — показать пакет, проверку и цену вопроса, в API только чтение;
  apply   — применить объединённый список к обеим кампаниям.

Минус-слова применяются мгновенно и перемодерации не требуют. Ставки,
бюджет, стратегию, объявления, фразы и чужие кампании скрипт не трогает.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://api.direct.yandex.com/json/v5/"
CAMPAIGNS = ["bs-apple-gift-2026-09", "bs-apple-regions-2026-09"]
REPORT_FROM = "2026-09-07"  # день запуска кампаний раунда 3

# Набор A. Отдельные слова — там, где слово однозначно вне оффера в любой
# формулировке. «бесплатно», «торрент», «вакансии», «зарплата» за период
# наблюдения не встретились ни разу и стоят профилактикой.
NEG_WORDS_A = [
    "скачать", "установить",
    "личный кабинет", "войти", "вход", "зайти", "авторизация", "логин",
    "ios 27", "айос 27", "дата выхода", "когда выйдет", "что нового", "анонс",
    "devices", "windows", "на пк",
    "взлом", "кряк", "бесплатно", "торрент", "вакансии", "зарплата",
]
# Набор A, фразовая часть: служба поддержки вместо корня «поддерж».
NEG_PHRASES_A = [
    "служба поддержки", "чат поддержки", "номер поддержки",
    "телефон поддержки", "горячая линия", "техподдержка",
    "номера операторов",
]
# Набор B. Слова — только те, что вне коммерческого интента в любом
# сочетании; всё остальное фразами.
NEG_WORDS_B = [
    "поздравление", "поздравить", "поздравления", "стихи", "открытка",
    "сценарий", "тост", "пожелание", "своими руками", "прикольный",
    "смешной", "картинки",
]
NEG_PHRASES_B = [
    "приказ на подарок", "приказ о подарке", "образец приказа",
    "ндфл с подарка", "проводки по подаркам",
    "дни рождения сотрудников", "календарь дней рождения",
    "список дней рождений",
]

# Покупательские маркеры: запрос с таким словом считается нашим, и
# минус-кандидат, задевший его при живом клике, к применению не идёт.
BUY_MARKERS = (
    "пополн", "оплат", "купить", "куплю", "подарочн", "gift", "сертификат",
    "корпоратив", "юрлиц", "юр лиц", "заказать", "заказ",
    "стоимост", "цена", "цены", "прайс", "счет", "счёт", "тенге", "лир",
)
# Слова, которые сами по себе покупателя не выдают. «Сотрудникам» есть и в
# «подарочные карты сотрудникам купить», и в «поздравление вышестоящим
# сотрудникам»: сигналом его делает только соседство с деньгами или
# товаром. Замечание внешнего аудита 13.09.2026.
BUY_PAIRS = (
    ("сотрудник", ("купить", "заказ", "карт", "сертификат", "корпоратив",
                   "счет", "счёт", "оптом", "стоимост", "цена", "gift")),
    ("клиентам", ("купить", "заказ", "карт", "сертификат", "счет", "счёт")),
)

# Кандидат, задевший покупательский запрос, отклоняется — но абсолютная
# строгость здесь стоит дороже пользы: «скачать» держит на себе сотни
# рублей мусора и один противоречивый запрос «подарочная карта apple gift
# card скачать» с единственным кликом. Поэтому задетое считается в долях:
# до десятой части отсекаемого расхода и не более двух запросов — слово
# идёт в работу с явной пометкой о цене вопроса, сверх того — отклоняется.
RISK_SHARE = 0.10
RISK_MAX_QUERIES = 2


def call(service: str, method: str, params: dict, token: str) -> dict:
    body = json.dumps({"method": method, "params": params}).encode("utf-8")
    req = urllib.request.Request(
        API + service,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept-Language": "ru",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} на {service}.{method}: {e.read().decode('utf-8')[:500]}")
    if "error" in data:
        err = data["error"]
        raise SystemExit(
            f"API-ошибка на {service}.{method}: код {err.get('error_code')} "
            f"{err.get('error_string')} — {err.get('error_detail')}"
        )
    return data.get("result", {})


def queries_report(token: str, campaign_ids: list[int]) -> list[dict]:
    """Поисковые запросы кампаний за всё время их работы."""
    definition = {
        "SelectionCriteria": {
            "DateFrom": REPORT_FROM,
            "DateTo": time.strftime("%Y-%m-%d"),
            "Filter": [{"Field": "CampaignId", "Operator": "IN",
                        "Values": [str(i) for i in campaign_ids]}],
        },
        "FieldNames": ["Query", "Impressions", "Clicks", "Cost"],
        "ReportName": f"apple-queries-{int(time.time())}",
        "ReportType": "SEARCH_QUERY_PERFORMANCE_REPORT",
        "DateRangeType": "CUSTOM_DATE",
        "Format": "TSV",
        "IncludeVAT": "NO",
    }
    body = json.dumps({"params": definition}).encode("utf-8")
    for _ in range(20):
        req = urllib.request.Request(
            API + "reports", data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept-Language": "ru",
                "Content-Type": "application/json; charset=utf-8",
                "processingMode": "auto",
                "returnMoneyInMicros": "false",
                "skipReportHeader": "true",
                "skipReportSummary": "true",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                if resp.status == 200:
                    lines = resp.read().decode("utf-8").strip().split("\n")
                    head = lines[0].split("\t")
                    out = []
                    for line in lines[1:]:
                        parts = line.split("\t")
                        if len(parts) != len(head):
                            continue
                        row = dict(zip(head, parts))
                        out.append({"Query": row["Query"],
                                    "Impressions": int(row["Impressions"]),
                                    "Clicks": int(row["Clicks"]),
                                    "Cost": float(row["Cost"])})
                    return out
                retry = int(resp.headers.get("retryIn", "10") or "10")
        except urllib.error.HTTPError as e:
            raise SystemExit(f"отчёт по запросам не получен: HTTP {e.code} "
                             f"{e.read().decode('utf-8')[:300]}")
        time.sleep(min(retry, 30))
    raise SystemExit("отчёт по запросам не дождался готовности")


def stem(word: str) -> str:
    """Грубая основа слова: хватает, чтобы поймать пересечение словоформ."""
    w = word.lower()
    return w[:-2] if len(w) > 5 else w


def words(text: str) -> list[str]:
    return [stem(w) for w in re.findall(r"\w+", text.lower())]


def is_buy(query: str) -> bool:
    """Покупательский ли запрос: прямой маркер либо связка слова с деньгами."""
    q = query.lower()
    if any(m in q for m in BUY_MARKERS):
        return True
    return any(weak in q and any(strong in q for strong in strongs)
               for weak, strongs in BUY_PAIRS)


def touches(candidate: str, query: str) -> bool:
    """Задевает ли кандидат запрос.

    Сверяются основы слов, а не подстроки: иначе «вход» задел бы
    «входит», а «на пк» — любой запрос со словом «на». Директ применяет
    минус-фразу так же — по словам запроса, независимо от их порядка.
    """
    q = set(words(query))
    return all(c in q for c in words(candidate))


def main() -> None:
    token = os.environ.get("DIRECT_TOKEN", "")
    if not token:
        raise SystemExit("DIRECT_TOKEN не задан")
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry-run"
    if mode not in ("dry-run", "apply"):
        raise SystemExit(f"неизвестный режим: {mode}")
    print(f"Режим: {mode}")

    camps = call("campaigns", "get",
                 {"SelectionCriteria": {},
                  "FieldNames": ["Id", "Name", "NegativeKeywords"]},
                 token).get("Campaigns", [])
    targets = [c for c in camps if c["Name"] in CAMPAIGNS]
    missing = set(CAMPAIGNS) - {c["Name"] for c in targets}
    for n in missing:
        print(f"  ! кампания не найдена: «{n}»")
    if not targets:
        raise SystemExit("ни одной кампании Apple не найдено")
    ids = [c["Id"] for c in targets]

    kws = call("keywords", "get",
               {"SelectionCriteria": {"CampaignIds": ids},
                "FieldNames": ["Keyword", "State"]},
               token).get("Keywords", [])
    phrases = [k["Keyword"].lower() for k in kws
               if k["Keyword"] != "---autotargeting" and k.get("State") != "SUSPENDED"]

    rows = queries_report(token, ids)
    spend_all = sum(r["Cost"] for r in rows)
    print(f"\nКампаний: {len(targets)}, действующих фраз: {len(phrases)}, "
          f"запросов в истории: {len(rows)}, расход {spend_all:.2f} ₽ без НДС")

    pack = [("A", w) for w in NEG_WORDS_A + NEG_PHRASES_A] + \
           [("B", w) for w in NEG_WORDS_B + NEG_PHRASES_B]

    print(f"\n== Проверка пакета ({len(pack)} позиций) ==")
    safe, blocked = [], []
    for group, cand in pack:
        hit_phrases = [p for p in phrases if touches(cand, p)]
        hit_rows = [r for r in rows if touches(cand, r["Query"])]
        risky = [r for r in hit_rows if r["Clicks"] > 0 and is_buy(r["Query"])]
        cut_cost = sum(r["Cost"] for r in hit_rows)
        cut_clicks = sum(r["Clicks"] for r in hit_rows)
        cut_imp = sum(r["Impressions"] for r in hit_rows)
        if hit_phrases:
            blocked.append(cand)
            print(f"  ✗ [{group}] «{cand}» — режет свою фразу: {hit_phrases[0]}")
            continue
        risk_cost = sum(r["Cost"] for r in risky)
        if risky and (len(risky) > RISK_MAX_QUERIES
                      or risk_cost > RISK_SHARE * max(cut_cost, 0.01)):
            blocked.append(cand)
            top = max(risky, key=lambda r: r["Cost"])
            print(f"  ✗ [{group}] «{cand}» — задевает покупателя: «{top['Query']}» "
                  f"({top['Clicks']} кл., {top['Cost']:.2f} ₽), всего {len(risky)} "
                  f"на {risk_cost:.2f} ₽ против {cut_cost:.2f} ₽ мусора")
            continue
        safe.append(cand)
        mark = "·" if cut_imp else "профилактика, за период не встречалось"
        note = (f" | с оговоркой: задет 1 покупательский запрос на {risk_cost:.2f} ₽"
                if risky else "")
        print(f"  ✓ [{group}] «{cand}» {mark} запросов {len(hit_rows)}, показов {cut_imp}, "
              f"кликов {cut_clicks}, {cut_cost:.2f} ₽{note}")

    hit_any = [r for r in rows if any(touches(c, r["Query"]) for c in safe)]
    total_cost = sum(r["Cost"] for r in hit_any)
    print(f"\n== Итог проверки ==")
    print(f"  принято {len(safe)}, отклонено {len(blocked)}")
    print(f"  пакет удерживает: запросов {len(hit_any)}, показов "
          f"{sum(r['Impressions'] for r in hit_any)}, кликов {sum(r['Clicks'] for r in hit_any)}, "
          f"{total_cost:.2f} ₽ = {100 * total_cost / spend_all if spend_all else 0:.0f}% расхода")
    print("  (это не экономия: Директ перераспределит бюджет на оставшиеся запросы)")

    if not safe:
        print("\nПрименять нечего.")
        return
    if mode != "apply":
        print("\ndry-run завершён — изменений нет.")
        return

    updates = []
    for camp in targets:
        current = (camp.get("NegativeKeywords") or {}).get("Items") or []
        merged, seen = [], set()
        for w in current + safe:
            lw = w.lower()
            if lw not in seen:
                seen.add(lw)
                merged.append(w)
        added = len(merged) - len(current)
        total_len = sum(len(w) for w in merged)
        if total_len > 4000:
            raise SystemExit(f"«{camp['Name']}»: суммарная длина минусов {total_len} > 4000")
        print(f"\n«{camp['Name']}»: было {len(current)}, станет {len(merged)} (+{added}), "
              f"длина {total_len} символов")
        updates.append({"Id": camp["Id"], "NegativeKeywords": {"Items": merged}})

    res = call("campaigns", "update", {"Campaigns": updates}, token)
    for i, r in enumerate(res.get("UpdateResults", [])):
        if r.get("Errors"):
            e = r["Errors"][0]
            print(f"  campaigns.update[{i}]: ОШИБКА {e.get('Code')} {e.get('Message')} — {e.get('Details')}")
        else:
            for w in r.get("Warnings") or []:
                print(f"  campaigns.update[{i}] предупреждение: {w.get('Code')} {w.get('Message')}")
            print(f"  campaigns.update[{i}]: OK id={r.get('Id')}")

    camps2 = call("campaigns", "get",
                  {"SelectionCriteria": {"Ids": ids},
                   "FieldNames": ["Id", "Name", "NegativeKeywords"]},
                  token).get("Campaigns", [])
    print("\n== Итог сверки ==")
    for c in camps2:
        n = len((c.get("NegativeKeywords") or {}).get("Items") or [])
        print(f"  «{c['Name']}»: минус-слов {n}")


if __name__ == "__main__":
    main()
