"""Разрез «страна × канал» в дневной витрине (21.09.2026).

Расширенный географический таргетинг в Директе оставлен включённым: покупатель
зарубежного ПО часто ищет под VPN, и Яндекс не всегда узнаёт в нём россиянина,
а пропущенный показ стоит заявку против клика за лишний. Проверить цену этого
решения можно только фактом — идут ли из-за рубежа обращения или только расход.

Парсер проверяется без сети: ответ Метрики подставляется готовым.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import collect_daily as C  # noqa: E402


def row(date, country_id, country_name, channel, visits):
    return {"dimensions": [{"name": date},
                           {"id": country_id, "name": country_name},
                           {"id": channel, "name": channel}],
            "metrics": [visits]}


class CountryRowsTest(unittest.TestCase):
    def test_россия_и_заграница_разведены_по_каналам(self):
        out = C.parse_metrika_country_rows({"data": [
            row("2026-09-20", "225", "Россия", "ad", 10),
            row("2026-09-20", "149", "Беларусь", "ad", 3),
            row("2026-09-20", "225", "Россия", "organic", 40),
        ]})
        self.assertEqual(out["visits_ads_geo_home"]["2026-09-20"], 10)
        self.assertEqual(out["visits_ads_geo_abroad"]["2026-09-20"], 3)
        self.assertEqual(out["visits_organic_geo_home"]["2026-09-20"], 40)

    def test_страна_узнаётся_по_идентификатору_а_не_по_названию(self):
        # Название приходит на языке запроса; идентификатор не зависит от него.
        out = C.parse_metrika_country_rows({"data": [
            row("2026-09-20", "225", "Russia", "ad", 7)]})
        self.assertEqual(out["visits_ads_geo_home"]["2026-09-20"], 7)
        self.assertNotIn("visits_abroad|russia", out)

    def test_название_срабатывает_когда_идентификатора_нет(self):
        out = C.parse_metrika_country_rows({"data": [
            {"dimensions": [{"name": "2026-09-20"}, {"name": "Россия"},
                            {"id": "ad", "name": "ad"}], "metrics": [5]}]})
        self.assertEqual(out["visits_ads_geo_home"]["2026-09-20"], 5)

    def test_каждая_зарубежная_страна_получает_свой_ряд(self):
        out = C.parse_metrika_country_rows({"data": [
            row("2026-09-20", "159", "Казахстан", "ad", 2),
            row("2026-09-20", "84", "США", "organic", 1),
        ]})
        self.assertEqual(out["visits_abroad|казахстан"]["2026-09-20"], 2)
        self.assertEqual(out["visits_abroad|сша"]["2026-09-20"], 1)

    def test_дни_суммируются_а_не_затираются(self):
        out = C.parse_metrika_country_rows({"data": [
            row("2026-09-20", "159", "Казахстан", "ad", 2),
            row("2026-09-20", "159", "Казахстан", "social", 3),
        ]})
        self.assertEqual(out["visits_abroad|казахстан"]["2026-09-20"], 5)

    def test_битая_строка_не_роняет_разбор(self):
        out = C.parse_metrika_country_rows({"data": [
            {"dimensions": [{"name": "2026-09-20"}], "metrics": [1]},
            {"dimensions": [], "metrics": []},
            row("2026-09-20", "225", "Россия", "ad", 4),
        ]})
        self.assertEqual(out["visits_ads_geo_home"]["2026-09-20"], 4)

    def test_обязательные_ряды_включают_разрез(self):
        # Ряд в EXPECTED — значит витрина дозаполнит его задним числом, и
        # прошлая рекламная кампания тоже попадёт в разбор.
        self.assertIn("visits_ads_geo_abroad", C.EXPECTED["metrika"])
        self.assertIn("visits_organic_geo_home", C.EXPECTED["metrika"])


if __name__ == "__main__":
    unittest.main()
