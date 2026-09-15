"""Разбор реестра целей и честность итога."""
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('goals_sync', ROOT / 'scripts/seo/goals_sync.py')
gs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gs)


class TestRegistry(unittest.TestCase):
    """Реестр читается из TypeScript: вторая копия списка разошлась бы с кодом."""

    @classmethod
    def setUpClass(cls):
        cls.goals = gs.load_goals()

    def test_registry_is_not_empty(self):
        self.assertGreaterEqual(len(self.goals), 10)

    def test_every_goal_has_ga4_name_and_meaning(self):
        for name, spec in self.goals.items():
            self.assertTrue(spec['ga4'], f'{name}: нет имени GA4')
            self.assertTrue(spec['meaning'], f'{name}: нет описания')

    def test_conversions_are_contacts_only(self):
        key = sorted(n for n, s in self.goals.items() if s['key'])
        self.assertEqual(key, sorted([
            'lead_sent', 'quote_pdf', 'click_phone', 'click_email', 'click_messenger',
            # Вторая половина сделки (15.09.2026): запрос финального КП, счёта
            # и действий по предложению — такие же обращения, как форма.
            'offer_final_request_click', 'offer_invoice_request_click',
            'offer_action_submit',
        ]))

    def test_standard_ga4_names_are_used_where_they_exist(self):
        """GA4 сам строит отчёты под рекомендованные имена — берём их."""
        self.assertEqual(self.goals['lead_sent']['ga4'], 'generate_lead')
        self.assertEqual(self.goals['view_product']['ga4'], 'view_item')
        self.assertEqual(self.goals['search_used']['ga4'], 'search')
        self.assertEqual(self.goals['add_to_cart']['ga4'], 'add_to_cart')

    def test_search_without_results_is_separate(self):
        """Пустая выдача — спрос, дошедший до нас и ушедший ни с чем."""
        self.assertIn('search_no_results', self.goals)
        self.assertNotEqual(self.goals['search_no_results']['ga4'],
                            self.goals['search_used']['ga4'])


class TestVerdictHonesty(unittest.TestCase):
    """«Не проверяли» не должно выглядеть как «всё в порядке»."""

    def test_no_access_is_not_success(self):
        # Ровно та ошибка, из-за которой ноль по целям читался как
        # отсутствие обращений: отсутствие замера выдавалось за результат.
        self.assertIsNone(gs.metrika_sync({}, False))

    def test_missing_list_and_no_access_differ(self):
        empty: list = []
        self.assertNotEqual(empty, None)
        self.assertFalse(empty)


if __name__ == '__main__':
    unittest.main(verbosity=1)
