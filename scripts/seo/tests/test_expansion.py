"""Отбор целей для тиражирования подтверждённого приёма (решение 02.09.2026).

Закрепляет исправленную ошибку: кандидатов выдавала сортировка по ОБЩЕЙ
частотности бренда (`src/data/vendor-demand.json`), из-за чего вердикт
CONTENT-001 предложил переносить статью на Google, Microsoft и Docker —
кластеры без покупательского спроса или без присутствия сайта в выдаче.
Проверяется, что профиль сниппета считает по коммерческим фразам, профиль
контента — по замеренным показам с позицией в топ-10 и наличию карточек,
а без данных источника список пуст, а не собран не по тому признаку.
"""

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import expansion  # noqa: E402

VENDORS_TS = """
export const VENDORS: VendorEntry[] = [
  { slug: 'perplexity', vendor: 'Perplexity', legalName: 'x' },
  { slug: 'postman', vendor: 'Postman', legalName: 'x' },
  { slug: 'docker', vendor: 'Docker', legalName: 'x' },
  { slug: 'notion', vendor: 'Notion', legalName: 'x' },
  { slug: 'lonely', vendor: 'Lonely', legalName: 'x' },
];
"""


def _phrase(vendor, phrase, freq, intent="commercial", in_scope=True):
    return {"vendor": vendor, "phrase": phrase, "intent": intent,
            "wordstat_frequency": freq, "in_scope": in_scope}


def _query(text, shows, pos):
    return {"query_text": text,
            "indicators": {"TOTAL_SHOWS": shows, "AVG_SHOW_POSITION": pos}}


class ExpansionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp,
                                                            ignore_errors=True))
        (self.tmp / "src/data").mkdir(parents=True)
        (self.tmp / "reports/seo/wordstat").mkdir(parents=True)
        (self.tmp / "reports/seo/data").mkdir(parents=True)
        (self.tmp / "reports/seo/intelligence").mkdir(parents=True)
        (self.tmp / "docs").mkdir(parents=True)
        (self.tmp / "scripts/catalog").mkdir(parents=True)

        (self.tmp / "src/data/vendors.ts").write_text(VENDORS_TS, encoding="utf-8")

        # Спрос: у Docker «коммерческие» фразы чужого кластера (джинсы), у
        # Postman коммерческих фраз нет вовсе — оба случая реальные.
        universe = [
            _phrase("Docker", "dockers купить", 9000),
            _phrase("Perplexity", "купить perplexity pro юридическим лицом", 5000),
            _phrase("Notion", "notion купить", 3000),
            _phrase("Postman", "postman что это", 100, intent="informational"),
            _phrase("Lonely", "lonely купить", 50),
        ]
        (self.tmp / "reports/seo/wordstat/semantic-universe.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in universe),
            encoding="utf-8")

        # Вебмастер: сайт виден по Perplexity и Postman, у Docker показов почти
        # нет, у Notion позиция вне топ-10.
        (self.tmp / "reports/seo/data/yandex-2026-09-02.json").write_text(
            json.dumps({"popular_queries": {
                "date_from": "2026-08-19", "date_to": "2026-08-30",
                "queries": [
                    _query("купить perplexity pro юридическим лицом", 150, 4.2),
                    _query("оплата postman юридическим лицом", 100, 5.0),
                    _query("dockers купить", 3, 7.0),
                    _query("notion купить", 90, 27.0),
                ]}}, ensure_ascii=False), encoding="utf-8")

        (self.tmp / "docs/catalog-product-icon-map.json").write_text(json.dumps([
            {"vendor": "Perplexity", "product": "Enterprise Pro"},
            {"vendor": "Perplexity", "product": "Enterprise Max"},
            {"vendor": "Postman", "product": "Solo"},
            {"vendor": "Postman", "product": "Professional"},
            {"vendor": "Notion", "product": "Business"},
            {"vendor": "Notion", "product": "Enterprise"},
            {"vendor": "Docker", "product": "Team"},
        ], ensure_ascii=False), encoding="utf-8")

        (self.tmp / "reports/seo/intelligence/seo-experiments.json").write_text(
            json.dumps({"experiments": [
                {"id": "alt", "status": "running",
                 "pages": ["/alternatives/notion"]}]}, ensure_ascii=False),
            encoding="utf-8")

        for attr, rel in (("UNIVERSE", "reports/seo/wordstat/semantic-universe.jsonl"),
                          ("VENDORS_TS", "src/data/vendors.ts"),
                          ("REGISTRY", "reports/seo/intelligence/seo-experiments.json"),
                          ("YANDEX_DIR", "reports/seo/data"),
                          ("ICON_MAP", "docs/catalog-product-icon-map.json"),
                          ("CATALOG_DIR", "scripts/catalog")):
            self._patch(attr, self.tmp / rel)

    def _patch(self, attr, value):
        old = getattr(expansion, attr)
        setattr(expansion, attr, value)
        self.addCleanup(setattr, expansion, attr, old)

    # ── профиль сниппета ────────────────────────────────────────────────────

    def test_сниппет_считает_по_коммерческим_фразам(self):
        urls = expansion.candidate_urls(profile="snippet")
        # Docker впереди по коммерческим фразам — формулу сниппета можно
        # применить к любой карточке, качество кластера проверяет не этот слой.
        self.assertEqual(urls[0], "/vendors/docker")
        # Кластер занят действующим экспериментом на страницах аналогов.
        self.assertNotIn("/vendors/notion", urls)

    # ── профиль приёма CONTENT-001 ──────────────────────────────────────────

    def test_контент_ранжирует_по_замеренным_показам(self):
        urls = expansion.candidate_urls(profile="content")
        self.assertEqual(urls, ["/vendors/perplexity", "/vendors/postman"])

    def test_контент_берёт_кластер_с_нулевым_спросом_вордстата(self):
        # У Postman коммерческих фраз в семантике нет, но сайт стоит на 5-й
        # позиции по «оплата postman юридическим лицом» — условия приёма
        # выполнены, и по Вордстату такой кластер не нашёлся бы.
        found = {c["vendor"]: c for c in expansion.candidates(profile="content")}
        self.assertIn("Postman", found)
        self.assertEqual(found["Postman"]["commercial_demand"], 0)

    def test_контент_отсекает_кластер_вне_топ_10(self):
        self.assertNotIn("/vendors/notion",
                         expansion.candidate_urls(profile="content"))

    def test_контент_отсекает_кластер_без_присутствия_в_выдаче(self):
        # Три показа за двенадцать дней — не присутствие, а шум.
        self.assertNotIn("/vendors/docker",
                         expansion.candidate_urls(profile="content"))

    def test_контент_требует_карточек_для_перелинковки(self):
        self._patch("ICON_MAP", self.tmp / "docs/none.json")
        self.assertEqual(expansion.candidate_urls(profile="content"), [])

    def test_явно_исключённые_страницы_не_предлагаются(self):
        urls = expansion.candidate_urls(exclude_pages=["/vendors/perplexity"],
                                        profile="content")
        self.assertNotIn("/vendors/perplexity", urls)

    # ── деградация без данных ───────────────────────────────────────────────

    def test_без_выгрузки_вебмастера_контент_молчит(self):
        self._patch("YANDEX_DIR", self.tmp / "reports/seo/none")
        self.assertEqual(expansion.candidate_urls(profile="content"), [])

    def test_без_семантики_сниппет_молчит(self):
        self._patch("UNIVERSE", self.tmp / "reports/seo/wordstat/none.jsonl")
        self.assertEqual(expansion.candidate_urls(profile="snippet"), [])

    def test_неизвестный_профиль_отвергается(self):
        with self.assertRaises(ValueError):
            expansion.candidates(profile="что-нибудь")


if __name__ == "__main__":
    unittest.main()
