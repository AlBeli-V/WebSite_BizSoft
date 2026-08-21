#!/usr/bin/env python3
"""Semantic Universe — постоянная база найденной семантики.

История не перезаписывается: у каждой фразы копится ряд частотностей с датами,
дата первого и последнего обнаружения, стоимость её получения и связь со
страницей сайта. Это отличает базу от снимка: снимок отвечает «сколько сейчас»,
база — «как менялось и что мы с этим сделали».

Хранилище — JSONL по одной фразе на строку: файл дописывается, читается потоком
и не требует внешней СУБД.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import normalize as N  # noqa: E402

UNIVERSE_PATH = pathlib.Path("reports/seo/wordstat/semantic-universe.jsonl")
SCHEMA_VERSION = "1.0.0"

FIELDS = (
    "phrase", "normalized_phrase", "morph_key", "source_seed", "vendor", "product",
    "category", "cluster", "subcluster", "intent", "commercial_intent_score",
    "informational_intent_score", "brand_or_nonbrand", "phrase_type",
    "wordstat_frequency", "wordstat_period", "region", "first_seen", "last_seen",
    "historical_frequency", "source_method", "api_cost_rub", "mapped_url",
    "page_exists", "indexed_yandex", "indexed_google", "yandex_position",
    "google_position", "yandex_impressions", "google_impressions", "clicks", "ctr",
    "conversion_evidence", "priority_score", "confidence", "in_scope",
    "attribution", "monthly_dynamics",
)


def blank(phrase: str) -> dict:
    return {f: None for f in FIELDS} | {"phrase": phrase, "historical_frequency": []}


class Universe:
    def __init__(self, path: pathlib.Path | None = None,
                 vendors: dict[str, str] | None = None):
        self.path = path or UNIVERSE_PATH
        self.vendors = vendors or {}
        self.rows: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                # Правила отбора уточняются по мере находок: фразы, собранные до
                # появления фильтра омонимов, иначе остались бы засчитанными.
                # Пересчёт при загрузке дешевле повторного сбора и не даёт базе
                # разъехаться со свежими правилами.
                #
                # Интент пересчитывается вместе с охватом. Пересчитывать одно и
                # оставлять другое — значит держать в одной строке правила
                # разных версий: фраза с новым охватом и старым интентом даёт
                # число, которое не воспроизводится ни одним набором правил.
                commercial, informational = N.intent_scores(row["phrase"])
                row["attribution"] = N.attribution_of(row["phrase"],
                                                      row.get("source_seed"))
                row["intent"] = N.classify_intent(row["phrase"])
                row["commercial_intent_score"] = commercial
                row["informational_intent_score"] = informational
                row["in_scope"] = (N.in_scope(row["phrase"])
                                   and row["attribution"] == "confident")
                # Привязка к вендору пересчитывается по той же причине.
                # Индекс пополняется именами продуктов — «claude» ведёт на
                # anthropic, «gemini» на google, — и без пересчёта накопленная
                # база остаётся с прежней привязкой: кластер «claude купить»
                # числился без страницы, хотя страница есть с самого начала,
                # и отчёт предлагал завести уже заведённое.
                if self.vendors:
                    recomputed = N.cluster_of(row["phrase"], self.vendors,
                                              row.get("source_seed"))
                    if recomputed:
                        row["cluster"] = recomputed
                self.rows[row["morph_key"]] = row

    def __len__(self) -> int:
        return len(self.rows)

    def get(self, phrase: str) -> dict | None:
        return self.rows.get(N.morph_key(phrase))

    def observe(self, *, phrase: str, frequency: int | None, date: str,
                source_seed: str, region: str, period: str, method: str,
                cost_rub: float, vendors: dict[str, str],
                vendor: str | None = None, category: str | None = None) -> tuple[dict, bool]:
        """Записать наблюдение. Возвращает строку и признак «фраза новая»."""
        key = N.morph_key(phrase)
        row = self.rows.get(key)
        is_new = row is None
        if is_new:
            row = blank(phrase)
            row.update({
                "normalized_phrase": N.normalize(phrase),
                "morph_key": key,
                "source_seed": source_seed,
                "first_seen": date,
                "api_cost_rub": 0.0,
                "historical_frequency": [],
            })
            self.rows[key] = row

        commercial, informational = N.intent_scores(phrase)
        row.update({
            "cluster": row["cluster"] or N.cluster_of(phrase, vendors, source_seed),
            "attribution": N.attribution_of(phrase, source_seed),
            "in_scope": N.in_scope(phrase) and N.relevant_to_seed(phrase, source_seed),
            "subcluster": N.subcluster_of(phrase),
            "intent": N.classify_intent(phrase),
            "commercial_intent_score": commercial,
            "informational_intent_score": informational,
            "brand_or_nonbrand": "brand" if N.is_branded(phrase) else "nonbrand",
            "phrase_type": N.phrase_type(phrase),
            "wordstat_frequency": frequency,
            "wordstat_period": period,
            "region": region,
            "last_seen": date,
            "source_method": method,
            "vendor": vendor or row.get("vendor"),
            "category": category or row.get("category"),
            "api_cost_rub": round((row.get("api_cost_rub") or 0.0) + cost_rub, 6),
        })
        hist = row["historical_frequency"]
        if not hist or hist[-1]["date"] != date:
            hist.append({"date": date, "frequency": frequency})
        else:
            hist[-1]["frequency"] = frequency
        return row, is_new

    def link_site(self, phrase: str, **site) -> dict | None:
        """Связать фразу с данными сайта: URL, индексация, позиции, клики."""
        row = self.get(phrase)
        if row is None:
            return None
        for k, v in site.items():
            if k in FIELDS:
                row[k] = v
        return row

    def observe_dynamics(self, phrase: str, results: list[dict]) -> dict | None:
        """Сохранить помесячный ряд спроса.

        Раньше ответ сервиса на запрос динамики выбрасывался сразу после оплаты:
        деньги списывались, а тренд у всех кластеров оставался «неизвестен».
        Ряд нужен именно здесь — по нему считается направление спроса за год,
        а не по двум соседним суточным замерам одного и того же числа.
        """
        row = self.get(phrase)
        if row is None or not results:
            return None
        series = []
        for r in results:
            date = (r.get("date") or "")[:10]
            count = r.get("count")
            if not date or count is None:
                continue
            try:
                series.append({"month": date[:7], "frequency": int(count)})
            except (TypeError, ValueError):
                continue
        if not series:
            return None
        row["monthly_dynamics"] = series
        return row

    def trend(self, phrase: str) -> dict:
        """Направление спроса: сначала по годовому ряду, иначе по замерам."""
        row = self.get(phrase)
        series = (row or {}).get("monthly_dynamics") or []
        if len(series) >= 4:
            return self._trend_from_series(series)
        hist = [h for h in (row or {}).get("historical_frequency", [])
                if h.get("frequency") is not None]
        if len(hist) < 2:
            return {"direction": "unknown", "change": None,
                    "reason": "меньше двух замеров"}
        first, last = hist[0]["frequency"], hist[-1]["frequency"]
        if not first:
            return {"direction": "unknown", "change": None, "reason": "нулевая база"}
        change = (last - first) / first
        direction = ("growing" if change > 0.15 else
                     "declining" if change < -0.15 else "stable")
        return {"direction": direction, "change": round(change, 3),
                "from": first, "to": last, "points": len(hist)}

    @staticmethod
    def _trend_from_series(series: list[dict]) -> dict:
        """Направление за год: две половины ряда, а не первая и последняя точки.

        Одна точка — это один месяц со своей сезонностью и шумом. Сравнение
        половин сглаживает и то и другое, и не объявляет рост из-за единственного
        удачного месяца.
        """
        half = len(series) // 2
        old_avg = sum(p["frequency"] for p in series[:half]) / half
        new_avg = sum(p["frequency"] for p in series[half:]) / (len(series) - half)
        if not old_avg:
            return {"direction": "unknown", "change": None, "reason": "нулевая база"}
        change = (new_avg - old_avg) / old_avg
        direction = ("growing" if change > 0.15 else
                     "declining" if change < -0.15 else "stable")
        return {"direction": direction, "change": round(change, 3),
                "from": round(old_avg), "to": round(new_avg),
                "points": len(series), "source": "годовой ряд Вордстата"}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for row in sorted(self.rows.values(),
                              key=lambda r: -(r.get("wordstat_frequency") or 0)):
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def stats(self) -> dict:
        rows = list(self.rows.values())
        commercial = [r for r in rows if r["intent"] == "commercial"
                      and r.get("in_scope") is not False]
        clusters = {r["cluster"] for r in rows if r["cluster"]}
        return {
            "phrases": len(rows),
            "commercial_phrases": len(commercial),
            "clusters": len(clusters),
            "total_commercial_demand": sum(r["wordstat_frequency"] or 0
                                           for r in commercial),
            "total_demand": sum(r["wordstat_frequency"] or 0 for r in rows),
            "with_page": sum(1 for r in rows if r.get("page_exists")),
            "cost_rub": round(sum(r.get("api_cost_rub") or 0 for r in rows), 4),
        }
