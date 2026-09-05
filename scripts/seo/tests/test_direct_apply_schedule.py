"""Расписание показов кампании Директа из спецификации (раунд 3, Apple Gift Card).

Кампании раундов 1–2 показываются пн–пт 9–19 — это зашито в скрипте. Раунд 3
(подарочные карты Apple) добавил ключ campaign.time_targeting: спрос на
пополнение баланса Apple ID вечерний и выходной. Проверяем, что без ключа
поведение прежнее, а с ключом дни и часы берутся из спецификации.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ppc"))
import direct_apply as da  # noqa: E402


def _spec(time_targeting=None):
    camp = {
        "name": "bs-apple-gift-2026-09",
        "start_date": "2026-09-07",
        "strategy": {"weekly_limit_rub_net": 4098},
        "negative_keywords": ["бесплатно"],
    }
    if time_targeting is not None:
        camp["time_targeting"] = time_targeting
    return {"campaign": camp, "groups": [{"max_bid_rub": 40}]}


def _hours(item: str) -> list[int]:
    parts = item.split(",")
    return [h for h, v in enumerate(parts[1:]) if v == "100"]


class ScheduleTest(unittest.TestCase):
    def test_default_is_business_hours(self):
        payload = da.build_campaign(_spec())
        tt = payload["Campaigns"][0]["TimeTargeting"]
        items = tt["Schedule"]["Items"]
        self.assertEqual(len(items), 7)
        self.assertEqual(_hours(items[0]), list(range(9, 19)))
        self.assertEqual(_hours(items[5]), [])
        self.assertEqual(_hours(items[6]), [])
        self.assertEqual(tt["HolidaysSchedule"]["SuspendOnHolidays"], "YES")

    def test_spec_schedule_with_weekends(self):
        payload = da.build_campaign(_spec({"days": [1, 2, 3, 4, 5, 6, 7], "hour_from": 9, "hour_to": 21}))
        tt = payload["Campaigns"][0]["TimeTargeting"]
        items = tt["Schedule"]["Items"]
        for item in items:
            self.assertEqual(_hours(item), list(range(9, 21)))
        # При SuspendOnHolidays = NO API требует часы показов в праздники
        # (код 5000 на apply 05.09.2026) — те же, что и в будни.
        self.assertEqual(tt["HolidaysSchedule"],
                         {"SuspendOnHolidays": "NO", "StartHour": 9, "EndHour": 21, "BidPercent": 100})

    def test_default_holidays_block_has_no_hours(self):
        tt = da.build_campaign(_spec())["Campaigns"][0]["TimeTargeting"]
        self.assertEqual(tt["HolidaysSchedule"], {"SuspendOnHolidays": "YES"})

    def test_invalid_schedule_stops(self):
        with self.assertRaises(SystemExit):
            da.build_campaign(_spec({"days": [8], "hour_from": 9, "hour_to": 21}))
        with self.assertRaises(SystemExit):
            da.build_campaign(_spec({"days": [1], "hour_from": 21, "hour_to": 9}))


if __name__ == "__main__":
    unittest.main()
