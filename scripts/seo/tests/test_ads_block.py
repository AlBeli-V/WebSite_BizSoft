"""Блок «Реклама» письма (Direct Control Report, этап A, 29.08.2026).

Правила вердиктов: маркер всегда со словом-причиной; до 10 накопленных
кликов — серый «мало данных»; мусорные запросы копят расход и при 300 ₽
становятся красным «требует решения». Отсутствие выгрузки письмо не ломает.
"""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ppc"))
import ads_block  # noqa: E402
import direct_report  # noqa: E402


def _stats(groups=None, queries=None):
    return {"schema_version": "1.0.0", "date_from": "2026-08-28",
            "date_to": "2026-08-29", "groups": groups or [],
            "queries": queries or []}


def _g(date, name, imp, clicks, cost):
    return {"Date": date, "CampaignId": "713927850", "AdGroupId": "1",
            "AdGroupName": name, "Impressions": imp, "Clicks": clicks,
            "Cost": cost}


def _q(date, name, query, imp, clicks, cost):
    return {"Date": date, "AdGroupName": name, "Query": query,
            "Impressions": imp, "Clicks": clicks, "Cost": cost}


class AdsBlockTest(unittest.TestCase):
    def _build(self, payload, date="2026-08-29"):
        tmp = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False,
                                          encoding='utf-8')
        json.dump(payload, tmp, ensure_ascii=False)
        tmp.close()
        old = ads_block.STATS
        ads_block.STATS = pathlib.Path(tmp.name)
        try:
            return ads_block.build(date)
        finally:
            ads_block.STATS = old
            pathlib.Path(tmp.name).unlink(missing_ok=True)

    def test_без_выгрузки_блок_недоступен(self):
        old = ads_block.STATS
        ads_block.STATS = pathlib.Path('/nонет/direct-stats.json')
        try:
            b = ads_block.build('2026-08-29')
        finally:
            ads_block.STATS = old
        self.assertFalse(b['available'])

    def test_мало_кликов_серый_вердикт_с_причиной(self):
        b = self._build(_stats(groups=[
            _g('2026-08-28', 'Claude — подписки', 50, 3, 120.0)]))
        r = next(x for x in b['rows'] if x['key'] == 'k1')
        self.assertEqual(r['verdict']['tone'], 'grey')
        self.assertIn('мало данных', r['verdict']['label'])

    def test_стоп_порог_даёт_жёлтый_сигнал(self):
        groups = [_g('2026-08-28', 'ChatGPT Business — фильтрующая', 900, 12, 700.0)]
        b = self._build(_stats(groups=groups))
        r = next(x for x in b['rows'] if x['key'] == 'k4')
        self.assertEqual(r['verdict']['tone'], 'warn')

    def test_мусор_дороже_порога_требует_решения(self):
        queries = [_q('2026-08-28', 'Claude — подписки',
                      'claude бесплатно скачать', 40, 5, 350.0)]
        b = self._build(_stats(groups=[_g('2026-08-28', 'Claude — подписки',
                                          40, 5, 350.0)], queries=queries))
        bad = [d for d in b['decisions'] if d['tone'] == 'bad']
        self.assertTrue(any('минус' in d['text'] for d in bad))
        self.assertIn('claude бесплатно скачать', b['junk']['queries'])

    def test_немного_мусора_только_наблюдение(self):
        queries = [_q('2026-08-28', 'Midjourney', 'midjourney промокод', 9, 1, 45.0)]
        b = self._build(_stats(groups=[_g('2026-08-28', 'Midjourney', 9, 1, 45.0)],
                               queries=queries))
        self.assertTrue(all(d['tone'] != 'bad' for d in b['decisions']))
        self.assertTrue(any('наблюдаю' in d['text'] for d in b['decisions']))

    def test_рабочий_день_без_показов_красный(self):
        # Письмо от пн 31.08 смотрит на пт 28.08 (рабочий день) без показов.
        b = self._build(_stats(), date='2026-08-29')
        self.assertTrue(any('ни одного показа' in d['text']
                            for d in b['decisions']))

    def test_выходной_без_показов_не_аномалия(self):
        # Письмо от вс 30.08 смотрит на сб 29.08 — показы закрыты расписанием.
        b = self._build(_stats(), date='2026-08-30')
        self.assertEqual(b['decisions'], [])

    def test_недельный_расход_суммируется_по_всем_группам(self):
        groups = [_g('2026-08-28', 'Claude — подписки', 10, 2, 100.0),
                  _g('2026-08-28', 'Midjourney', 10, 1, 50.5)]
        b = self._build(_stats(groups=groups))
        self.assertAlmostEqual(b['week']['spent'], 150.5)
        self.assertEqual(b['week']['limit'], 4098)


class ParseTsvTest(unittest.TestCase):
    FIELDS = ["Date", "AdGroupName", "Query", "Impressions", "Clicks", "Cost"]

    def test_обычные_строки_и_прочерк_расхода(self):
        raw = ("Date\tAdGroupName\tQuery\tImpressions\tClicks\tCost\n"
               "2026-08-28\tClaude — подписки\tclaude купить\t12\t2\t93.40\n"
               "2026-08-28\tMidjourney\tmidjourney цена\t5\t0\t--\n")
        rows = direct_report.parse_tsv(raw, self.FIELDS)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['Clicks'], 2)
        self.assertAlmostEqual(rows[0]['Cost'], 93.40)
        self.assertEqual(rows[1]['Cost'], 0.0)

    def test_пустой_ответ_не_падает(self):
        self.assertEqual(direct_report.parse_tsv("", self.FIELDS), [])
        self.assertEqual(direct_report.parse_tsv(
            "Date\tAdGroupName\tQuery\tImpressions\tClicks\tCost\n",
            self.FIELDS), [])


if __name__ == '__main__':
    unittest.main()
