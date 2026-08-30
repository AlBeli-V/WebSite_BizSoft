"""Копилка идей бесплатного продвижения (решение руководителя 29.08.2026).

В письме — только свежие идеи (status=new, максимум две), полный список —
в веб-отчёте. Отсутствие файла не ломает сборку письма.
"""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import report_v4  # noqa: E402


class GrowthIdeasTest(unittest.TestCase):
    def _with_file(self, payload):
        tmp = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False,
                                          encoding='utf-8')
        json.dump(payload, tmp, ensure_ascii=False)
        tmp.close()
        old = report_v4.GROWTH_IDEAS
        report_v4.GROWTH_IDEAS = pathlib.Path(tmp.name)
        try:
            return report_v4.load_growth_ideas()
        finally:
            report_v4.GROWTH_IDEAS = old
            pathlib.Path(tmp.name).unlink(missing_ok=True)

    def test_без_файла_блок_недоступен_и_письмо_не_ломается(self):
        old = report_v4.GROWTH_IDEAS
        report_v4.GROWTH_IDEAS = pathlib.Path('/nонет/growth-ideas.json')
        try:
            gi = report_v4.load_growth_ideas()
        finally:
            report_v4.GROWTH_IDEAS = old
        self.assertFalse(gi['available'])
        self.assertEqual(gi['fresh'], [])

    def test_в_письмо_идут_только_новые_и_не_больше_двух(self):
        items = [
            {'id': 'A', 'status': 'new', 'title': 'а', 'why': 'потому'},
            {'id': 'B', 'status': 'watch', 'title': 'б', 'why': 'потому'},
            {'id': 'C', 'status': 'new', 'title': 'в', 'why': 'потому'},
            {'id': 'D', 'status': 'new', 'title': 'г', 'why': 'потому'},
        ]
        gi = self._with_file({'items': items})
        self.assertTrue(gi['available'])
        self.assertEqual([i['id'] for i in gi['fresh']], ['A', 'C'])
        self.assertEqual(len(gi['items']), 4)

    def test_принятые_и_отклонённые_из_письма_уходят(self):
        gi = self._with_file({'items': [
            {'id': 'A', 'status': 'done', 'title': 'а', 'why': 'п'},
            {'id': 'B', 'status': 'dropped', 'title': 'б', 'why': 'п'},
        ]})
        self.assertTrue(gi['available'])
        self.assertEqual(gi['fresh'], [])


if __name__ == '__main__':
    unittest.main()
