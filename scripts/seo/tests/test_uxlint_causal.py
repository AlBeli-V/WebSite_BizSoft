"""Корпус ложных срабатываний google_claim_has_page_evidence.

Каждый кейс — состав реального дня, на котором правило падало или могло
упасть. Новые правки правила обязаны проходить весь корпус: фикс одного
дня не должен открывать другой (25.08 → фикс → 27.08 — уже случалось).
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from uxlint_v4 import google_causal_claim  # noqa: E402


DECLINED = "Причина изменения пока не определена."


def blocks_shape(*, engine_available: tuple[bool, bool] | None,
                 driver_rows: list, summary: str = DECLINED) -> dict:
    """Состав blocks по мотивам реальных дней: drivers.available=True всегда,
    печатаемый текст блока — driver_summary, движковые детали — вложенные."""
    if engine_available is None:
        drivers = {"available": False, "reason": "расчёт не выполнялся"}
    else:
        pages_ok, queries_ok = engine_available
        drivers = {"available": True, "reason": None, "blocks": [{
            "engine": "google",
            "pages": {"available": pages_ok,
                      "reason": None if pages_ok
                      else "изменения слишком дробные, чтобы назвать драйвер",
                      "drivers": []},
            "queries": {"available": queries_ok, "drivers": []},
        }]}
    return {"drivers": drivers, "driver_rows": driver_rows,
            "driver_summary": summary}


HEADER = ("Видимость в Google: 28 показов за неделю. "
          "Google Search Console, весь сайт, дневные ряды.")


class TestCausalClaimCorpus(unittest.TestCase):
    def test_day_2026_08_27_calculated_but_undetermined(self):
        # Расчёт выполнен (available=true), вложенные false, rows пустые,
        # текст честно отказывается от причины — утверждения нет.
        blocks = blocks_shape(engine_available=(False, False), driver_rows=[])
        vis = HEADER + " Причина изменения пока не определена."
        claim, note = google_causal_claim(vis, blocks)
        self.assertFalse(claim, note)

    def test_day_2026_08_26_drivers_named(self):
        # Драйверы определены и перечислены — утверждение есть, и правило
        # проходит, потому что строки названы.
        blocks = blocks_shape(engine_available=(True, False),
                              driver_rows=[{"page": "/vendors/zoom", "delta": 3}],
                              summary="Показы выросли на страницах: /vendors/zoom (+3).")
        vis = HEADER + " Показы выросли на страницах: /vendors/zoom (+3)."
        claim, _ = google_causal_claim(vis, blocks)
        self.assertTrue(claim)
        self.assertTrue(bool(blocks["driver_rows"]))

    def test_summary_claims_but_rows_dropped_fails(self):
        # Письмо объявило причину текстом блока, а строк-доказательств нет —
        # рассинхронизация вёрстки, которую правило обязано ловить (это
        # закрепляет и test_claimed_cause_without_pages_fails на дне 19.08).
        blocks = blocks_shape(engine_available=(True, False), driver_rows=[],
                              summary="Показы выросли на страницах: /vendors/zoom (+3).")
        claim, _ = google_causal_claim(HEADER, blocks)
        self.assertTrue(claim)

    def test_day_2026_08_25_plain_mention_is_not_claim(self):
        # Слово «Google» в шапке и подписи источника — не утверждение о причине.
        blocks = blocks_shape(engine_available=None, driver_rows=[])
        claim, note = google_causal_claim(HEADER, blocks)
        self.assertFalse(claim, note)

    def test_textual_causal_marker_still_caught(self):
        # Страховка: причина, названная текстом вне блока драйверов,
        # остаётся утверждением — без перечисленных страниц правило падает.
        blocks = blocks_shape(engine_available=None, driver_rows=[])
        vis = HEADER + " Рост объясняется индексацией новых страниц Google."
        claim, _ = google_causal_claim(vis, blocks)
        self.assertTrue(claim)

    def test_engine_found_minor_detractor_letter_declined(self):
        # 27.08, вторая грань: движок Яндекса нашёл детрактора с долей 6%
        # (yandex.queries.available=true), но письмо консервативно причину
        # не объявило — rows пусты, текст отказался. Утверждения нет:
        # правило судит по написанному, а не по расчётам движка.
        blocks = blocks_shape(engine_available=(False, True), driver_rows=[])
        vis = HEADER + " Причина изменения пока не определена."
        claim, note = google_causal_claim(vis, blocks)
        self.assertFalse(claim, note)


if __name__ == "__main__":
    unittest.main()
