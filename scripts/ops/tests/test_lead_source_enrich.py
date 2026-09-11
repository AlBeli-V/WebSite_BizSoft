#!/usr/bin/env python3
"""Проверки обогащения заявок данными Метрики и Директа.

Цена этих проверок высокая: слепок уезжает прямо в письмо руководителю, по
которому он судит о канале и о стоимости привлечения. Разбор обязан молчать
там, где данных нет, и не превращать «Не определено» Метрики в подпись,
похожую на факт.

  python3 -m unittest discover -s scripts/ops/tests -t scripts/ops/tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lead_source_enrich import parse_visits, window  # noqa: E402

DIMS = ('ym:s:date,ym:s:lastTrafficSource,ym:s:lastSearchEngine,'
        'ym:s:lastSearchPhrase,ym:s:lastReferalSource,ym:s:startURLPath')


def row(date, source, engine='', phrase='', referral='', page='/', visits=1):
    return {
        'dimensions': [
            {'name': date}, {'id': source, 'name': source}, {'name': engine},
            {'name': phrase}, {'name': referral}, {'name': page},
        ],
        'metrics': [visits],
    }


class TestParseVisits(unittest.TestCase):
    def test_organic_with_phrase(self):
        out = parse_visits({'data': [
            row('2026-09-01', 'organic', 'Яндекс', 'kling ai оплата', page='/'),
            row('2026-09-02', 'organic', 'Яндекс', 'kling ai для юрлиц', page='/product/kling'),
        ]}, DIMS)
        self.assertTrue(out['available'])
        # Последний визит и есть тот, что привёл заявку.
        self.assertEqual(out['searchPhrase'], 'kling ai для юрлиц')
        self.assertEqual(out['trafficSource'], 'organic')
        self.assertEqual(out['visits'], 2)
        self.assertEqual([s['when'] for s in out['steps']], ['2026-09-01', '2026-09-02'])

    def test_steps_sorted_by_date(self):
        out = parse_visits({'data': [
            row('2026-09-05', 'referral', referral='dzen.ru'),
            row('2026-09-01', 'organic', 'Яндекс'),
        ]}, DIMS)
        self.assertEqual([s['when'] for s in out['steps']], ['2026-09-01', '2026-09-05'])
        self.assertEqual(out['referralSource'], 'dzen.ru')

    def test_placeholders_are_dropped(self):
        """«Не определено» Метрики — это отсутствие данных, а не подпись."""
        out = parse_visits({'data': [
            row('2026-09-02', 'organic', 'N/A', 'Не определено', page='/'),
        ]}, DIMS)
        self.assertNotIn('searchEngine', out)
        self.assertNotIn('searchPhrase', out)

    def test_no_visits_is_named_reason(self):
        out = parse_visits({'data': []}, DIMS)
        self.assertFalse(out['available'])
        self.assertIn('визитов', out['error'])

    def test_short_dimension_set(self):
        """Бедный набор измерений: разбор идёт по именам, а не по позициям."""
        dims = 'ym:s:date,ym:s:lastTrafficSource,ym:s:lastSearchEngineRoot,ym:s:startURLPath'
        payload = {'data': [{
            'dimensions': [{'name': '2026-09-02'}, {'id': 'ad', 'name': 'ad'},
                           {'name': 'Яндекс'}, {'name': '/vendors/anthropic'}],
            'metrics': [3],
        }]}
        out = parse_visits(payload, dims)
        self.assertEqual(out['trafficSource'], 'ad')
        self.assertEqual(out['searchEngine'], 'Яндекс')
        self.assertEqual(out['steps'][0]['page'], '/vendors/anthropic')


class TestWindow(unittest.TestCase):
    def test_ninety_days_back(self):
        self.assertEqual(window('2026-09-10T12:00:00Z'), ('2026-06-12', '2026-09-10'))

    def test_broken_date_falls_back_to_today(self):
        date1, date2 = window('')
        self.assertLess(date1, date2)


if __name__ == '__main__':
    unittest.main()
