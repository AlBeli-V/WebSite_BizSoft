"""Дневная витрина: парсеры ответов API и слияние рядов — без сети."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import collect_daily as cd  # noqa: E402


class TestParsers(unittest.TestCase):
    def test_yandex_history_dates_and_metrics(self):
        payload = {'indicators': {
            'TOTAL_SHOWS': [
                {'date': '2026-08-20T00:00:00.000+03:00', 'value': 150.0},
                {'date': '2026-08-21T00:00:00.000+03:00', 'value': 170.0},
            ],
            'TOTAL_CLICKS': [
                {'date': '2026-08-20T00:00:00.000+03:00', 'value': 3.0},
            ],
        }}
        series = cd.parse_yandex_history(payload)
        self.assertEqual(series['impressions']['2026-08-20'], 150.0)
        self.assertEqual(series['impressions']['2026-08-21'], 170.0)
        self.assertEqual(series['clicks']['2026-08-20'], 3.0)
        self.assertNotIn('2026-08-21', series['clicks'])

    def test_yandex_history_empty(self):
        self.assertEqual(cd.parse_yandex_history({}),
                         {'impressions': {}, 'clicks': {}})

    def test_gsc_rows(self):
        payload = {'rows': [
            {'keys': ['2026-08-20'], 'impressions': 7, 'clicks': 1, 'position': 12.5},
            {'keys': ['2026-08-21'], 'impressions': 4, 'clicks': 0, 'position': 20.0},
        ]}
        series = cd.parse_gsc_rows(payload)
        self.assertEqual(series['impressions']['2026-08-21'], 4)
        self.assertEqual(series['clicks']['2026-08-20'], 1)
        self.assertEqual(series['position']['2026-08-20'], 12.5)

    def test_metrika_rows(self):
        payload = {'data': [
            {'dimensions': [{'name': '2026-08-20'}], 'metrics': [5, 4, 1]},
            {'dimensions': [{'name': '2026-08-21'}], 'metrics': [2, 2, 0]},
        ]}
        series = cd.parse_metrika_rows(payload, cd.METRIKA_METRICS)
        self.assertEqual(series['visits_organic']['2026-08-20'], 5)
        self.assertEqual(series['goal_reaches_organic']['2026-08-21'], 0)

    def test_ga4_rows_normalises_dates(self):
        payload = {'rows': [
            {'dimensionValues': [{'value': '20260820'}],
             'metricValues': [{'value': '6'}, {'value': '1'}]},
        ]}
        series = cd.parse_ga4_rows(payload, cd.GA4_METRICS)
        self.assertEqual(series['sessions_organic']['2026-08-20'], 6.0)
        self.assertEqual(series['key_events_organic']['2026-08-20'], 1.0)


class TestMerge(unittest.TestCase):
    def test_fresh_overwrites_tail_and_keeps_history(self):
        existing = {'impressions': {'2026-08-01': 100, '2026-08-20': 140}}
        fresh = {'impressions': {'2026-08-20': 150, '2026-08-21': 170}}
        merged = cd.merge_series(existing, fresh)
        # История вне хвоста не тронута, хвост перезаписан свежим значением.
        self.assertEqual(merged['impressions']['2026-08-01'], 100)
        self.assertEqual(merged['impressions']['2026-08-20'], 150)
        self.assertEqual(merged['impressions']['2026-08-21'], 170)

    def test_short_fresh_window_does_not_erase_metrics(self):
        existing = {'impressions': {'2026-08-01': 100}, 'clicks': {'2026-08-01': 2}}
        merged = cd.merge_series(existing, {'impressions': {'2026-08-02': 90}})
        self.assertEqual(merged['clicks']['2026-08-01'], 2)

    def test_none_values_do_not_poison_series(self):
        merged = cd.merge_series({}, {'impressions': {'2026-08-02': None}})
        self.assertEqual(merged['impressions'], {})

    def test_dates_sorted(self):
        merged = cd.merge_series(
            {'impressions': {'2026-08-03': 1}},
            {'impressions': {'2026-08-01': 2}})
        self.assertEqual(list(merged['impressions']), ['2026-08-01', '2026-08-03'])


class TestWindow(unittest.TestCase):
    def test_empty_store_requests_full_history(self):
        date_from, _ = cd.window_for({})
        self.assertEqual(date_from, cd.HISTORY_START)

    def test_filled_store_requests_tail_only(self):
        store = {'series': {'impressions': {'2026-08-01': 1}}}
        date_from, date_to = cd.window_for(store)
        self.assertEqual((date_to - date_from).days, cd.TAIL_DAYS)


if __name__ == '__main__':
    unittest.main()
