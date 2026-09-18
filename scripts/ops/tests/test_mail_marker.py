#!/usr/bin/env python3
"""Маркер отправки письма: одно письмо на дату при любом формате маркера."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mail_marker as mm  # noqa: E402


class TestParse(unittest.TestCase):
    def test_три_поля_разведки(self):
        self.assertEqual(mm.parse("2026-09-16 abc123 2"),
                         {"date": "2026-09-16", "hash": "abc123", "count": 2})

    def test_одна_дата_отчёта(self):
        self.assertEqual(mm.parse("2026-09-16"),
                         {"date": "2026-09-16", "hash": "", "count": 0})

    def test_пустой_маркер_не_роняет_разбор(self):
        self.assertEqual(mm.parse(""), {"date": "", "hash": "", "count": 0})

    def test_счётчик_не_число_читается_нулём(self):
        self.assertEqual(mm.parse("2026-09-16 abc много")["count"], 0)


class TestAlreadySent(unittest.TestCase):
    def test_трёхпольный_маркер_считается_отправленным(self):
        """Разбор целой строкой не совпадал никогда — отсюда четыре письма 16.09.2026."""
        self.assertTrue(mm.already_sent("2026-09-16 abc123 1", "2026-09-16"))

    def test_однопольный_маркер_считается_отправленным(self):
        self.assertTrue(mm.already_sent("2026-09-16", "2026-09-16"))

    def test_вчерашний_маркер_не_блокирует_сегодня(self):
        self.assertFalse(mm.already_sent("2026-09-15 abc123 1", "2026-09-16"))

    def test_пустой_маркер_не_блокирует(self):
        self.assertFalse(mm.already_sent("", "2026-09-16"))

    def test_другое_письмо_того_же_дня_не_дубль(self):
        """Изменился расчёт — это уточнение, и решает его почтовый контур."""
        self.assertFalse(mm.already_sent("2026-09-16 abc123 1", "2026-09-16", "def456"))

    def test_то_же_письмо_того_же_дня_дубль(self):
        self.assertTrue(mm.already_sent("2026-09-16 abc123 1", "2026-09-16", "abc123"))

    def test_хэш_без_маркерного_не_снимает_блокировку(self):
        """Старый однопольный маркер: хэша нет, но письмо за дату уже ушло."""
        self.assertTrue(mm.already_sent("2026-09-16", "2026-09-16", "def456"))


if __name__ == "__main__":
    unittest.main()
