"""Паспорт блока: причина только из словаря, свежесть только по датам."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import passport  # noqa: E402


class TestUnavailable(unittest.TestCase):
    def test_reason_text_comes_from_dictionary(self):
        b = passport.unavailable("no_file", source="витрина Директа", detail="окно 7 дней")
        self.assertFalse(b["available"])
        self.assertEqual(b["status"], "missing")
        self.assertEqual(b["reason_code"], "no_file")
        self.assertEqual(b["reason"],
                         "пригодного файла источника за окно нет: витрина Директа (окно 7 дней)")
        self.assertEqual(passport.check_block(b), [])

    def test_unknown_code_is_refused(self):
        with self.assertRaises(ValueError):
            passport.unavailable("waiting_for_token")

    def test_free_text_reason_is_a_violation(self):
        old = {"available": False, "reason": "инструмент ждёт токена Вебмастера"}
        self.assertEqual(len(passport.check_block(old, "ads")), 1)
        forged = {"available": False, "reason_code": "no_file",
                  "reason": "ждёт токена"}
        self.assertIn("не из словаря", passport.check_block(forged)[0])

    def test_normalize_keeps_contract_blocks_and_fixes_foreign(self):
        good = passport.unavailable("no_signal")
        self.assertIs(passport.normalize(good), good)
        fixed = passport.normalize({"available": False, "reason": "ещё не накоплен"},
                                   default_code="no_rows", source="замер спроса")
        self.assertEqual(fixed["reason_code"], "no_rows")
        self.assertEqual(passport.check_block(fixed), [])
        self.assertEqual(passport.normalize(None)["reason_code"], "no_file")


class TestFreshness(unittest.TestCase):
    def test_older_than_expected_is_stale(self):
        b = passport.available("2026-09-01", expected_as_of="2026-09-02")
        self.assertTrue(b["stale"])
        self.assertEqual(b["status"], "stale")
        self.assertEqual(passport.check_freshness(b), [])

    def test_fresh_block_has_no_stale_flag(self):
        b = passport.available("2026-09-02", expected_as_of="2026-09-02")
        self.assertNotIn("stale", b)
        self.assertEqual(b["status"], "ok")

    def test_unmarked_old_data_is_a_violation(self):
        b = {"available": True, "as_of": "2026-08-30", "expected_as_of": "2026-09-02"}
        self.assertIn("без пометки stale", passport.check_freshness(b, "leads")[0])

    def test_stale_without_date_is_a_violation(self):
        b = {"available": True, "stale": True}
        self.assertIn("без даты данных", passport.check_freshness(b)[0])


class TestWalk(unittest.TestCase):
    def test_walk_finds_nested_blocks(self):
        blocks = {"ads": passport.unavailable("no_file"),
                  "drivers": {"blocks": [{"pages": {"available": False}}]}}
        paths = [p for p, _ in passport.walk(blocks)]
        self.assertIn("blocks.ads", paths)
        self.assertIn("blocks.drivers.blocks[0].pages", paths)
        self.assertEqual(len(passport.check_all(blocks)), 1)


if __name__ == "__main__":
    unittest.main()
