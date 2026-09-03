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
    def _build(self, payload, date="2026-08-29", attribution=None):
        tmp = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False,
                                          encoding='utf-8')
        json.dump(payload, tmp, ensure_ascii=False)
        tmp.close()
        old = ads_block.STATS
        ads_block.STATS = pathlib.Path(tmp.name)
        try:
            return ads_block.build(date, attribution)
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

    def test_неделя_и_с_запуска_разные_суммы(self):
        # Расход за всё время сравнивался с недельным лимитом; теперь неделя —
        # последние семь дней данных, «с запуска» — отдельная сумма.
        groups = [_g('2026-08-10', 'Claude — подписки', 10, 2, 1000.0),
                  _g('2026-08-28', 'Claude — подписки', 10, 2, 100.0)]
        b = self._build(_stats(groups=groups) | {"date_from": "2026-08-10"})
        self.assertAlmostEqual(b['week']['spent'], 100.0)
        self.assertAlmostEqual(b['since_launch']['spent'], 1100.0)
        self.assertEqual(b['since_launch']['days'], 19)
        self.assertFalse(b['stale'])
        self.assertEqual(b['as_of'], '2026-08-28')

    def test_отставшая_выгрузка_не_пустой_кабинет(self):
        # Витрина покрывает только 26.08, письмо от 29.08 ждёт 28.08: это
        # сбой сбора, а не «ни одного показа в рабочий день».
        groups = [_g('2026-08-26', 'Claude — подписки', 10, 2, 100.0)]
        b = self._build(_stats(groups=groups) | {"date_to": "2026-08-26"})
        self.assertTrue(b['stale'])
        self.assertEqual(b['as_of'], '2026-08-26')
        self.assertEqual(b['expected_as_of'], '2026-08-28')
        self.assertFalse(any('ни одного показа' in d['text'] for d in b['decisions']))
        self.assertTrue(any('отстаёт' in d['text'] and d['tone'] == 'warn'
                            for d in b['decisions']))
        self.assertAlmostEqual(b['day_spend'], 100.0)

    def test_имя_кампании_не_зашито(self):
        b = self._build(_stats())
        self.assertIsNone(b['campaign'])
        b = self._build(_stats() | {"campaign": "bs-2026-10"})
        self.assertEqual(b['campaign'], 'bs-2026-10')

    def test_недельный_расход_суммируется_по_всем_группам(self):
        groups = [_g('2026-08-28', 'Claude — подписки', 10, 2, 100.0),
                  _g('2026-08-28', 'Midjourney', 10, 1, 50.5)]
        b = self._build(_stats(groups=groups))
        self.assertAlmostEqual(b['week']['spent'], 150.5)
        self.assertEqual(b['week']['limit'], 4098)

    def test_новые_группы_cursor_и_adobe_видны_как_направления(self):
        groups = [_g('2026-08-28', 'Cursor — редактор для команд разработки',
                     20, 3, 90.0),
                  _g('2026-08-28', 'Adobe — подписки для юрлиц', 15, 2, 60.0)]
        b = self._build(_stats(groups=groups))
        keys = {r['key'] for r in b['rows'] if r['clicks_total']}
        self.assertIn('k5', keys)
        self.assertIn('k6', keys)

    def test_группа_вне_списка_не_теряется_из_пейсинга(self):
        # Кабинет ушёл вперёд списка GROUPS (инцидент #217): расход чужой
        # группы обязан войти в неделю и показаться строкой «прочие».
        groups = [_g('2026-08-28', 'Claude — подписки', 10, 2, 100.0),
                  _g('2026-08-28', 'Runway — новая группа', 30, 4, 200.0)]
        b = self._build(_stats(groups=groups))
        self.assertAlmostEqual(b['week']['spent'], 300.0)
        other = [r for r in b['rows'] if r['key'] == 'other']
        self.assertEqual(len(other), 1)
        self.assertIn('Runway', other[0]['label'])
        self.assertEqual(other[0]['verdict']['tone'], 'warn')


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


def _att(rows, dimension="ym:s:lastDirectBannerGroup"):
    return {"dimension": dimension, "goal_keys": ["lead_sent"], "rows": rows}


class StageBAttributionTest(unittest.TestCase):
    """Этап B (01.09.2026): заявки и CPA из связки Метрика→Директ."""

    _build = AdsBlockTest._build

    def test_заявки_с_допустимым_CPA_зелёные(self):
        stats = _stats([_g("2026-08-28", "Claude Code — для команд", 500, 30, 2000.0)])
        att = _att([{"name": "Claude Code — для команд", "visits": 28,
                     "goal_reaches_any": 6,
                     "leads": {"lead_sent": 1, "quote_pdf": 0,
                               "click_phone": 2, "click_email": 0,
                               "click_messenger": 0}}])
        b = self._build(stats, attribution=att)
        row = next(r for r in b["rows"] if r["key"] == "k2")
        self.assertEqual(row["leads"], 1)
        self.assertEqual(row["contacts"], 2)
        self.assertEqual(row["verdict"]["tone"], "ok")
        self.assertIn("CPA 2000", row["verdict"]["label"])

    def test_расход_выше_цены_заявки_без_заявок_красный(self):
        """Порог паузы — CPA-лимит направления, а не число кликов."""
        stats = _stats([_g("2026-08-28", "Claude Code — для команд", 900, 60, 3200.0)])
        att = _att([{"name": "Claude Code — для команд", "visits": 55,
                     "goal_reaches_any": 0, "leads": {}}])
        b = self._build(stats, attribution=att)
        row = next(r for r in b["rows"] if r["key"] == "k2")
        self.assertEqual(row["verdict"]["tone"], "bad")
        self.assertIn("кандидат на паузу", row["verdict"]["label"])
        self.assertIn("решение за вами", row["verdict"]["label"])

    def test_много_кликов_но_расход_ниже_цены_заявки_не_красный(self):
        """Ноль заявок на 30 кликах — обычный исход и у здоровой группы.

        Прежний ручной порог (25 кликов) красил такую строку в красное и
        предлагал паузу, когда направление потратило две трети допустимой
        цены заявки. Теперь до порога строка показывает остаток.
        """
        stats = _stats([_g("2026-08-28", "Claude Code — для команд", 500, 30, 2000.0)])
        att = _att([{"name": "Claude Code — для команд", "visits": 28,
                     "goal_reaches_any": 0, "leads": {}}])
        b = self._build(stats, attribution=att)
        row = next(r for r in b["rows"] if r["key"] == "k2")
        self.assertEqual(row["verdict"]["tone"], "ok")
        self.assertIn("2000 из 3000", row["verdict"]["label"])
        self.assertNotIn("паузу", row["verdict"]["label"])

    def test_CPA_выше_порога_жёлтый(self):
        stats = _stats([_g("2026-08-28", "Midjourney — контрольная", 500, 30, 2000.0)])
        att = _att([{"name": "Midjourney — контрольная", "visits": 28,
                     "goal_reaches_any": 1,
                     "leads": {"lead_sent": 1}}])
        b = self._build(stats, attribution=att)
        row = next(r for r in b["rows"] if r["key"] == "k3")
        self.assertEqual(row["verdict"]["tone"], "warn")  # 2000 > порога 600
        self.assertIn("выше порога", row["verdict"]["label"])

    def test_фолбэк_по_кампании_не_приписывает_группам(self):
        stats = _stats([_g("2026-08-28", "Claude Code — для команд", 500, 30, 2000.0)])
        att = _att([{"name": "bs-test-2026-09", "visits": 100,
                     "goal_reaches_any": 5, "leads": {"lead_sent": 2}}],
                   dimension="ym:s:lastDirectClickOrder")
        b = self._build(stats, attribution=att)
        row = next(r for r in b["rows"] if r["key"] == "k2")
        self.assertIsNone(row["leads"])   # по-групповых данных нет — честный None
        self.assertEqual(row["verdict"]["tone"], "warn")

    def test_без_связки_поведение_этапа_A(self):
        stats = _stats([_g("2026-08-28", "Claude Code — для команд", 500, 30, 2000.0)])
        b = self._build(stats, attribution=None)
        row = next(r for r in b["rows"] if r["key"] == "k2")
        self.assertIsNone(row["leads"])
        self.assertIn("пора оценить вовлечение", row["verdict"]["label"])
