"""Потолок цены клика: разбор стратегии перед записью (04.09.2026).

Скрипт переписывает стратегию кампании целиком — Директ принимает
WbMaximumClicks только вместе с недельным лимитом. Значит два способа
испортить кампанию одним прогоном: записать чужую стратегию как
«максимум кликов» и потерять недельный лимит, сняв ограничение расхода.
Оба закрыты проверками, и оба проверяются здесь.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ppc"))
import direct_ceiling  # noqa: E402


def _strategy(weekly=4098, ceiling=50, kind="WB_MAXIMUM_CLICKS"):
    wb = {"WeeklySpendLimit": weekly * 1_000_000} if weekly else {}
    if ceiling is not None:
        wb["BidCeiling"] = ceiling * 1_000_000
    return {"BiddingStrategyType": kind, "WbMaximumClicks": wb}


class CeilingTest(unittest.TestCase):
    def test_читает_текущий_потолок_и_лимит(self):
        kind, current, weekly = direct_ceiling.plan(_strategy(), direct_ceiling.CEILING_RUB)
        self.assertEqual(kind, "WB_MAXIMUM_CLICKS")
        self.assertEqual(current, 50)
        self.assertEqual(weekly, 4098)

    def test_потолок_может_быть_не_задан(self):
        _, current, _ = direct_ceiling.plan(_strategy(ceiling=None), direct_ceiling.CEILING_RUB)
        self.assertIsNone(current)

    def test_чужая_стратегия_роняет_прогон(self):
        with self.assertRaises(SystemExit):
            direct_ceiling.plan(_strategy(kind="WB_MAXIMUM_CONVERSION_RATE"),
                                direct_ceiling.CEILING_RUB)

    def test_без_недельного_лимита_прогон_не_идёт(self):
        """Запись стратегии без лимита сняла бы ограничение расхода."""
        with self.assertRaises(SystemExit):
            direct_ceiling.plan(_strategy(weekly=None), direct_ceiling.CEILING_RUB)

    def test_порог_выше_средней_цены_клика(self):
        """21,27 ₽ с НДС накопительно — это 17,4 ₽ без НДС.

        Порог ниже средней цены клика срезал бы не хвост, а основную массу
        показов, поэтому он держится с запасом.
        """
        self.assertGreater(direct_ceiling.CEILING_RUB, 21.27 / 1.22)


if __name__ == "__main__":
    unittest.main()
