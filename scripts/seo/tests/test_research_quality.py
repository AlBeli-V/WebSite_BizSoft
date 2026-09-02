"""Качество исследования: что попадает в отчёт и что из него не должно выходить.

Проверки написаны по замечаниям руководителя от 21.08.2026. Он получил письмо,
в котором «непокрытым спросом» назывались товары, стоящие на сайте, а среди
кандидатов на заведение — сервисы, которые он сам отклонил накануне, и сервисы
для частных лиц. Каждое из этих замечаний здесь превращено в проверку: словами
такие вещи не удерживаются, они возвращаются с первым же новым прогоном.
"""
import importlib
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts/seo/wordstat'))

audience = importlib.import_module('audience')
playbook = importlib.import_module('playbook')
discovery = importlib.import_module('discovery')

# Данные из фикстур: копии machine-данных вычищены из main 30.08.2026.
_FIXWS = pathlib.Path(__file__).resolve().parent / 'fixtures/reports/seo/wordstat'
audience.DECISIONS_PATH = _FIXWS / 'decisions.json'
audience.VENDOR_DECISIONS_PATH = (pathlib.Path(__file__).resolve().parent
                                  / 'fixtures/reports/seo/intelligence/vendor-decisions.json')
discovery.CANDIDATES_TS = _FIXWS / 'vendor-candidates.json'


class TestDecisions(unittest.TestCase):
    """Решение руководителя принимается один раз."""

    def test_rejected_never_returns(self):
        for brand in ('spotify', 'chatgpt plus', 'youtube premium'):
            self.assertIsNotNone(audience.skip_reason(brand),
                                 f'{brand} снова предлагается')

    def test_rejection_survives_template_words(self):
        # В отчёте кластер называется «spotify купить», а решение записано
        # на бренд: без нормализации фильтр молча промахивался.
        self.assertIsNotNone(audience.skip_reason('spotify купить'))
        self.assertIsNotNone(audience.skip_reason('chatgpt plus купить'))

    def test_approved_passes(self):
        for brand in ('wordpress', 'deepl'):
            self.assertIsNone(audience.skip_reason(brand))

    def test_owner_decision_beats_classification(self):
        """Одобренное руководителем проходит, даже если список зовёт иначе."""
        approved = audience.approved_brands()
        self.assertTrue(approved)
        for b in approved:
            self.assertIsNone(audience.skip_reason(b))

    def test_отказ_из_второго_реестра_тоже_действует(self):
        # 29.08.2026 руководитель отклонил NordVPN и Ansys, но решение легло
        # только в один реестр, и кандидаты предлагались заново. Теперь любой
        # из двух реестров закрывает вопрос.
        self.assertIsNotNone(audience.skip_reason('vercel'))
        self.assertIsNotNone(audience.skip_reason('vercel купить'))

    def test_registry_entries_are_traceable(self):
        d = audience.load_decisions()
        for row in d['rejected'] + d['approved']:
            self.assertTrue(row.get('brand'))
            self.assertTrue(row.get('decided_on'), row)
            self.assertTrue(row.get('reason'), row)


class TestAudience(unittest.TestCase):
    """Юрлицам не предлагаем то, что покупают себе."""

    def test_consumer_services_are_out(self):
        for brand in ('netflix', 'apple music', 'twitch', 'steam'):
            self.assertEqual(audience.audience_of(brand), 'consumer')
            self.assertIsNotNone(audience.skip_reason(brand))

    def test_business_services_stay(self):
        for brand in ('autodesk', 'wordpress', 'aws', 'deepl'):
            self.assertEqual(audience.audience_of(brand), 'business')

    def test_dual_services_keep_business_plan_note(self):
        """У сервиса с двойным лицом указывается корпоративный тариф."""
        self.assertEqual(audience.audience_of('canva'), 'dual')
        self.assertIn('команд', audience.business_note('canva'))
        self.assertIsNone(audience.skip_reason('canva'))


class TestCatalogueMapping(unittest.TestCase):
    """Продукт ведёт на страницу своего вендора."""

    def test_product_names_resolve_to_vendor_pages(self):
        # Именно из-за отсутствия этой связи «claude купить» и
        # «microsoft 365 купить» числились непокрытым спросом.
        index = discovery.vendor_index(discovery.site_vendors())
        for product, vendor in (('claude', 'anthropic'), ('gemini', 'google'),
                                ('chatgpt plus', 'openai'),
                                ('microsoft 365', 'microsoft'),
                                ('autocad', 'autodesk')):
            self.assertEqual(index.get(product), vendor,
                             f'{product} не ведёт на {vendor}')

    def test_product_map_is_single_source(self):
        """Карта соответствий одна: вторая копия разошлась бы с первой."""
        self.assertTrue(discovery.product_of())
        cfg = json.loads((pathlib.Path(__file__).resolve().parent / 'fixtures/reports/seo/wordstat/vendor-candidates.json')
                         .read_text(encoding='utf-8'))
        self.assertEqual(set(k.lower() for k in cfg['product_of']),
                         set(discovery.product_of()))


class TestPlaybook(unittest.TestCase):
    """Разрыв превращается в задачу, а не в ярлык."""

    SAMPLE = {
        'gap': 'GAP-D', 'cluster': 'heygen', 'commercial_demand': 50,
        'top_phrases': [{'phrase': 'heygen тарифы'}], 'url': '/vendors/heygen',
        'best_position': 6.9, 'impressions': 50, 'clicks': 0,
    }

    def test_every_gap_class_has_a_task(self):
        for cls in ('GAP-A', 'GAP-B', 'GAP-C', 'GAP-D',
                    'GAP-E', 'GAP-F', 'GAP-G', 'GAP-H'):
            r = playbook.build({**self.SAMPLE, 'gap': cls}, '2026-08-21')
            self.assertTrue(r['step'], cls)
            self.assertTrue(r['prompt'], cls)
            self.assertTrue(r['success'], cls)
            self.assertTrue(r['check_on'], cls)

    def test_prompt_is_self_contained(self):
        """Промт копируется и уходит в работу без досочинения."""
        r = playbook.build(self.SAMPLE, '2026-08-21')
        self.assertIn('/vendors/heygen', r['prompt'])
        self.assertIn('heygen тарифы', r['prompt'])
        self.assertGreater(len(r['prompt']), 120)

    def test_success_is_measurable(self):
        """Признак завершения содержит дату — иначе задача не закрывается."""
        for cls in ('GAP-A', 'GAP-B', 'GAP-C', 'GAP-D', 'GAP-E'):
            r = playbook.build({**self.SAMPLE, 'gap': cls}, '2026-08-21')
            self.assertIn('2026-', r['success'], cls)

    def test_new_page_prompt_requires_payment_check(self):
        """Спрос без возможности оплатить в сделку не превращается."""
        r = playbook.build({**self.SAMPLE, 'gap': 'GAP-A'}, '2026-08-21')
        self.assertIn('оплат', r['prompt'].lower())
        self.assertIn('decisions.json', r['prompt'])

    def test_paid_channel_stays_a_calculation(self):
        """Рекламу не запускаем: бюджет — решение руководителя."""
        r = playbook.build({**self.SAMPLE, 'gap': 'GAP-F'}, '2026-08-21')
        self.assertIn('решает руководитель', r['prompt'])

    def test_check_date_matches_nature_of_work(self):
        """Сниппет проверяется раньше, чем новая страница: индексация дольше."""
        snippet = playbook.build({**self.SAMPLE, 'gap': 'GAP-D'}, '2026-08-21')
        page = playbook.build({**self.SAMPLE, 'gap': 'GAP-A'}, '2026-08-21')
        self.assertLess(snippet['check_on'], page['check_on'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
