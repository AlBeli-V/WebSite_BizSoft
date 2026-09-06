"""Отбор кампаний для сбора статистики Директа (раунд 3, 05.09.2026).

До раунда 3 сбор читал одну кампанию по имени; теперь — все с префиксом bs-,
чтобы кампании подарочных карт Apple попадали в статистику без правки кода.
DIRECT_CAMPAIGNS сужает набор для ручного прогона.
"""

import os
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ppc"))
import direct_stats as ds  # noqa: E402

CAMPS = [{"Id": 1, "Name": "bs-test-2026-09"}, {"Id": 2, "Name": "bs-apple-gift-2026-09"},
         {"Id": 3, "Name": "bs-apple-regions-2026-09"}, {"Id": 4, "Name": "Чужая кампания"}]


class TargetsTest(unittest.TestCase):
    def setUp(self):
        os.environ.pop("DIRECT_CAMPAIGNS", None)

    def test_prefix_selects_all_ours(self):
        self.assertEqual([c["Id"] for c in ds.select_targets(CAMPS)], [1, 2, 3])

    def test_env_narrows(self):
        os.environ["DIRECT_CAMPAIGNS"] = "bs-apple-gift-2026-09, bs-apple-regions-2026-09"
        try:
            self.assertEqual([c["Id"] for c in ds.select_targets(CAMPS)], [2, 3])
        finally:
            os.environ.pop("DIRECT_CAMPAIGNS", None)

    def test_metrika_sections_takes_campaign_name(self):
        import inspect
        self.assertIn("campaign_name", inspect.signature(ds.metrika_sections).parameters)


if __name__ == "__main__":
    unittest.main()
