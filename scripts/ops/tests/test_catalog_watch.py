#!/usr/bin/env python3
"""Проверки сторожа каталога: что считается событием, а что — переоценкой.

Цена этих проверок высокая: по строке ANOMALIES=N воркфлоу решает, слать ли
письмо руководителю. Ложное срабатывание на ежедневной переоценке по курсу ЦБ
превратит сторож в шум и его перестанут читать; пропущенное снятие карточки
с витрины — ровно та беда, ради которой сторож и заведён.

  python3 -m unittest discover -s scripts/ops/tests -t scripts/ops/tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from catalog_watch import diff_states, render, round1  # noqa: E402


def card(sku, **over):
    row = {
        'id': 1, 'sku': sku, 'slug': sku.lower(), 'name': f'Товар {sku}',
        'vendor': 'Vendor', 'status': 'published', 'price': 1000,
        'price_note': 'за пользователя в год',
        'base_price_usd': 10, 'base_price_eur': None, 'peg_currency': 'USD',
        'peg_to_usd': True, 'markup_coeff': 1.9, 'price_locked': 0,
        'promo_price': None, 'promo_label': None,
        'product_type': None, 'parent_sku': None,
    }
    row.update(over)
    return row


def state(products, usd=85.0, eur=99.0, taken='2026-09-10T06:00:00+00:00'):
    return {'taken_at': taken, 'rate': {'usd': usd, 'eur': eur, 'date': '2026-09-10'},
            'products': {p['sku']: p for p in products}}


class TestCurrencyIsNotAnEvent(unittest.TestCase):
    def test_daily_reprice_is_silent(self):
        old = state([card('A', price=round1(10 * 85.0 * 1.9))], usd=85.0)
        new = state([card('A', price=round1(10 * 86.5 * 1.9))], usd=86.5)
        self.assertEqual(diff_states(old, new), [])

    def test_rounding_within_one_rouble_is_silent(self):
        old = state([card('A', price=round1(10 * 85.0 * 1.9))], usd=85.0)
        new = state([card('A', price=round1(10 * 86.5 * 1.9) + 1)], usd=86.5)
        self.assertEqual(diff_states(old, new), [])

    def test_price_off_formula_is_an_event(self):
        old = state([card('A', price=round1(10 * 85.0 * 1.9))], usd=85.0)
        new = state([card('A', price=1)], usd=85.0)
        events = diff_states(old, new)
        self.assertEqual([e['kind'] for e in events], ['changed'])
        self.assertIn('цена, ₽', events[0]['details'][0])

    def test_purchase_price_change_is_an_event(self):
        old = state([card('A', price=round1(10 * 85.0 * 1.9))], usd=85.0)
        new = state([card('A', base_price_usd=120, price=round1(120 * 85.0 * 1.9))], usd=85.0)
        kinds = {d.split(':')[0] for e in diff_states(old, new) for d in e['details']}
        self.assertIn('закупка USD', kinds)
        self.assertIn('цена, ₽', kinds)

    def test_coefficient_change_is_an_event(self):
        old = state([card('A', price=round1(10 * 85.0 * 1.85), markup_coeff=1.85)], usd=85.0)
        new = state([card('A', price=round1(10 * 85.0 * 1.9), markup_coeff=1.9)], usd=85.0)
        self.assertTrue(diff_states(old, new))

    def test_manual_rouble_card_price_change_is_an_event(self):
        # Без валютной привязки курс цену не объясняет ни при каких условиях.
        base = dict(peg_to_usd=False, peg_currency=None, base_price_usd=None)
        old = state([card('A', price=1100, **base)], usd=85.0)
        new = state([card('A', price=13200, **base)], usd=86.5)
        self.assertTrue(diff_states(old, new))


class TestPresence(unittest.TestCase):
    def test_new_card_is_reported(self):
        events = diff_states(state([card('A')]), state([card('A'), card('B')]))
        self.assertEqual([(e['kind'], e['sku']) for e in events], [('appeared', 'B')])

    def test_deleted_card_is_reported(self):
        events = diff_states(state([card('A'), card('B')]), state([card('A')]))
        self.assertEqual([(e['kind'], e['sku']) for e in events], [('vanished', 'B')])

    def test_unpublish_is_reported(self):
        events = diff_states(state([card('A')]), state([card('A', status='draft')]))
        self.assertEqual([e['kind'] for e in events], ['unpublished'])

    def test_republish_is_reported(self):
        events = diff_states(state([card('A', status='draft')]), state([card('A')]))
        self.assertEqual([e['kind'] for e in events], ['published'])

    def test_vanished_goes_first(self):
        old = state([card('A'), card('B'), card('C')])
        new = state([card('A', name='новое'), card('B', status='draft'), card('D')])
        self.assertEqual([e['kind'] for e in diff_states(old, new)],
                         ['vanished', 'unpublished', 'appeared', 'changed'])


class TestIdentityFields(unittest.TestCase):
    def test_rename_and_slug_change_are_events(self):
        old = state([card('A')])
        new = state([card('A', name='Другое имя', slug='other')])
        details = diff_states(old, new)[0]['details']
        self.assertEqual(len(details), 2)
        self.assertTrue(any(d.startswith('название') for d in details))
        self.assertTrue(any(d.startswith('слаг') for d in details))

    def test_price_note_change_is_an_event(self):
        old = state([card('A')])
        new = state([card('A', price_note='за пользователя в месяц')])
        self.assertTrue(diff_states(old, new)[0]['details'][0].startswith('приписка к цене'))


class TestRender(unittest.TestCase):
    def test_quiet_report_says_so(self):
        text = render([], state([card('A')]), state([card('A')]))
        self.assertIn('Расхождений нет', text)

    def test_report_groups_events(self):
        old = state([card('A'), card('B')])
        new = state([card('A', status='draft')])
        text = render(diff_states(old, new), old, new)
        self.assertIn('Удалены из базы: 1', text)
        self.assertIn('Сняты с витрины: 1', text)


if __name__ == '__main__':
    unittest.main()
