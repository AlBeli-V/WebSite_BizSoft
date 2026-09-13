#!/usr/bin/env python3
"""Проверки разбора вывода шага ssh-run (.github/actions/ssh-run/result.py).

Цена: по `outcome` journal-post ставит ✓ или ✗ и красит прогон, а по
`stdout` seo-recrawl-sweep двигает курсор очереди. Ошибка разбора — это либо
зелёный прогон при сбое скрипта, либо потерянный курсор и выброшенная
суточная квота Вебмастера.

  python3 -m unittest discover -s scripts/ops/tests -t scripts/ops/tests
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, '.github', 'actions', 'ssh-run'))

from result import parse  # noqa: E402

BANNER = '===============================================\n✅ Successfully executed commands to all hosts.\n===============================================\n'


class ParseTest(unittest.TestCase):
    def test_success(self):
        out = 'токен: задан\nитог: принято 7, отклонено 0\n__OPS_RC=0\n' + BANNER
        res = parse('success', out)
        self.assertEqual(res['outcome'], 'success')
        self.assertEqual(res['rc'], '0')
        self.assertEqual(res['stdout'], 'токен: задан\nитог: принято 7, отклонено 0')
        self.assertEqual(res['body'], res['stdout'])

    def test_script_failure_keeps_output(self):
        out = ('квота: {"quota_remainder": 0}\n'
               '  https://biz-soft.pro/product/x → HTTP 429 ОТКЛОНЕНО\n'
               'итог: принято 0, отклонено 1\n__OPS_RC=1\n' + BANNER)
        res = parse('success', out)
        self.assertEqual(res['outcome'], 'failure')
        self.assertEqual(res['rc'], '1')
        self.assertIn('HTTP 429', res['stdout'])
        self.assertNotIn('Successfully executed', res['body'])
        self.assertTrue(res['body'].endswith('код завершения скрипта: 1'))

    def test_markers_for_consumers_survive(self):
        out = 'итог: принято 149, отклонено 1\nSWEEP_CURSOR=449\nSWEEP_TOTAL=520\n__OPS_RC=1\n' + BANNER
        res = parse('success', out)
        self.assertEqual(res['outcome'], 'failure')
        self.assertIn('SWEEP_CURSOR=449', res['stdout'])
        self.assertNotIn('__OPS_RC', res['stdout'])

    def test_ssh_failure_without_marker(self):
        res = parse('failure', '')
        self.assertEqual(res['outcome'], 'failure')
        self.assertEqual(res['rc'], '')
        self.assertEqual(res['stdout'], '')
        self.assertIn('сеанс SSH завершился со статусом failure', res['body'])

    def test_ssh_timeout_with_partial_output(self):
        res = parse('failure', 'шаг 1 готов\nшаг 2 идёт\n')
        self.assertEqual(res['outcome'], 'failure')
        self.assertTrue(res['body'].startswith('шаг 1 готов\nшаг 2 идёт\n\n'))
        self.assertIn('до маркера кода завершения не дошёл', res['body'])

    def test_session_ok_but_marker_missing_is_failure(self):
        res = parse('success', 'что-то напечатано\n' + BANNER)
        self.assertEqual(res['outcome'], 'failure')
        self.assertEqual(res['rc'], '')

    def test_crlf_and_equals_lines_in_output_kept(self):
        out = 'a=b\r\n== Режим: адресный ==\r\n__OPS_RC=0\r\n' + BANNER
        res = parse('success', out)
        self.assertEqual(res['stdout'], 'a=b\n== Режим: адресный ==')


if __name__ == '__main__':
    unittest.main()
