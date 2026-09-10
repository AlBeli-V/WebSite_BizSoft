#!/usr/bin/env python3
"""KPI-kit: единый визуальный слой отчётов (scripts/viz/kpi_kit.py).

Проверяется то, что компоненты обещают потребителям: серия закреплена за
источником, графики строятся без библиотек и без внешних ресурсов, письмо
получает вёрстку без картинок и с шрифтами не мельче лимитов uxlint, у
таблицы-дашборда есть значения сортировки, теплокарта честно показывает дыры.
"""

import importlib.util
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "viz"))

spec = importlib.util.spec_from_file_location("kpi_kit", ROOT / "scripts/viz/kpi_kit.py")
kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit)


class TestPalette(unittest.TestCase):
    def test_series_bound_to_source(self):
        self.assertEqual(kit.series_color("yandex", hex_mode=True), kit.LIGHT["s1"])
        self.assertEqual(kit.series_color("google", hex_mode=True), kit.LIGHT["s2"])
        self.assertEqual(kit.series_color("google", hex_mode=True), kit.LIGHT["accent"])

    def test_status_colours_are_not_series_colours(self):
        series = {kit.LIGHT[k] for k in ("s1", "s2", "s3", "s4")}
        for k in ("good", "warn", "crit"):
            self.assertNotIn(kit.LIGHT[k], series)

    def test_dark_theme_declares_every_light_token(self):
        self.assertEqual(set(kit.LIGHT), set(kit.DARK))
        css = kit.tokens_css()
        self.assertIn(':root:not([data-theme="light"])', css)
        self.assertIn(':root[data-theme="dark"]', css)


class TestFormatting(unittest.TestCase):
    def test_num_ru(self):
        self.assertEqual(kit.num(1234), "1\u202f234")
        self.assertEqual(kit.num(0.65), "0,65")
        self.assertEqual(kit.num(None), "—")

    def test_signed(self):
        self.assertEqual(kit.signed(9), "+9")
        self.assertEqual(kit.signed(-3, "%"), "−3%")
        self.assertEqual(kit.signed(0), "0")

    def test_delta_dir_inverts_for_positions(self):
        self.assertEqual(kit.delta_dir(5), "up")
        self.assertEqual(kit.delta_dir(-5, good_up=False), "up")
        self.assertIsNone(kit.delta_dir(None))


class TestSvg(unittest.TestCase):
    def test_sparkline_needs_two_points(self):
        self.assertEqual("", kit.sparkline([1]))
        svg = kit.sparkline([1, 3, 2], hex_mode=True)
        self.assertIn("<polyline", svg)
        self.assertIn(kit.LIGHT["s1"], svg)
        self.assertIn("<circle", svg)

    def test_line_chart_single_series_has_no_legend(self):
        svg = kit.line_chart([{"name": "Показы", "values": [1, 2, 3, 4]}], ["1", "2", "3", "4"])
        self.assertNotIn("kit-legend", svg)
        self.assertIn("data-kit-line", svg)
        self.assertIn("<path", svg)

    def test_line_chart_two_series_has_legend_and_context_is_grey(self):
        svg = kit.line_chart([{"name": "Сейчас", "values": [1, 2, 3]},
                              {"name": "Прошлый период", "values": [2, 2, 2], "context": True}],
                             ["a", "b", "c"], hex_mode=True)
        self.assertIn("kit-legend", svg)
        self.assertIn(kit.LIGHT["gray"], svg)

    def test_line_chart_skips_gaps(self):
        svg = kit.line_chart([{"name": "x", "values": [1, None, 3, 4]}], list("abcd"))
        self.assertEqual(2, svg.count(" M") + svg.count('"M'))

    def test_no_external_resources_in_components(self):
        html = (kit.line_chart([{"name": "x", "values": [1, 2]}], ["a", "b"])
                + kit.heatmap(["2026-08-03", "2026-08-04"], [1, 2])
                + kit.kit_js() + kit.kit_css())
        self.assertNotIn("<script src=", html)
        self.assertNotIn("<link", html)
        self.assertNotIn("https://", html)


class TestComponents(unittest.TestCase):
    def test_tile_with_key_is_a_button(self):
        t = kit.stat_tile("Показы", "926", delta="+9%", direction="up", key="ya")
        self.assertTrue(t.startswith("<button"))
        self.assertIn('data-kit-key="ya"', t)
        self.assertIn("▲", t)
        self.assertTrue(kit.stat_tile("Показы", "926").startswith("<div"))

    def test_status_rows_state_glyph_and_meter(self):
        h = kit.status_rows([{"state": "warn", "name": "CTR", "value": "0,65%",
                              "progress": 0.43, "target": "цель 1,5%"}])
        self.assertIn("kit-dot warn", h)
        self.assertIn("!", h)
        self.assertIn("width:43%", h)

    def test_waterfall_levels(self):
        h = kit.waterfall("База", 40, [("Google", 4), ("CTR", -1)], "Итог")
        self.assertIn("+4", h)
        self.assertIn("−1", h)
        self.assertIn(">43<", h)

    def test_heatmap_marks_gaps_and_sums_weeks(self):
        dates = [f"2026-08-{d:02d}" for d in range(3, 10)]  # понедельник — воскресенье
        vals = [10, 20, None, 5, 5, 0, 0]
        h = kit.heatmap(dates, vals)
        self.assertIn("kit-heat-empty", h)
        self.assertIn(">40<", h)
        self.assertIn("всего <b>40</b>", h)

    def test_dense_table_sort_values(self):
        cols = [{"key": "n", "label": "Имя"}, {"key": "imp", "label": "Показы", "align": "right"}]
        rows = [{"n": "a", "imp": kit.bar_cell(13, 13)}, {"n": "b", "imp": kit.bar_cell(4, 13)}]
        h = kit.dense_table(cols, rows)
        self.assertIn('data-sort="13.0"', h)
        self.assertIn("kit-sortable", h)
        self.assertIn("kit-bar", h)
        self.assertIn("Строк нет", kit.dense_table(cols, []))

    def test_pos_cell_inverts_delta(self):
        self.assertIn("kit-delta up", kit.pos_cell(9.0, -1.5)["html"])
        self.assertIn("kit-delta down", kit.pos_cell(9.0, 2.0)["html"])


class TestFitsItsBox(unittest.TestCase):
    """Ничто из кита не выходит за свою рамку.

    09.09.2026 руководитель прислал снимок отчёта с телефона: спарклайн
    вылезал за карточку KPI. Причина у всех находок разбора одна — жёсткий
    размер внутри гибкого контейнера: спарклайн 96 px в плитке 140 px,
    сетка теплокарты 432 px, минимум колонки грида шире экрана. Проверки
    ниже держат договор компонентов; целиком собранную страницу меряет в
    браузере scripts/seo/layoutcheck.mjs.
    """

    def test_sparkline_ring_stays_inside_viewbox(self):
        w, h, r = 96, 28, 3.5 + 1  # радиус кольца плюс половина обводки
        svg = kit.sparkline([1, 5, 3, 9, 2], w=w, h=h)
        pts = re.search(r'points="([^"]+)"', svg).group(1).split()
        xs = [float(p.split(",")[0]) for p in pts]
        ys = [float(p.split(",")[1]) for p in pts]
        self.assertGreaterEqual(min(xs), r)
        self.assertLessEqual(max(xs), w - r)
        self.assertGreaterEqual(min(ys), r)
        self.assertLessEqual(max(ys), h - r)

    def test_line_chart_end_label_does_not_leave_viewbox(self):
        # Широкое число не помещается в правое поле — подпись уходит влево
        # от точки, иначе svg молча срезал бы её по краю viewBox.
        wide = kit.line_chart([{"name": "р", "values": [1, 1234567]}], ["a", "b"], w=320)
        self.assertIn('text-anchor="end"', wide)
        narrow = kit.line_chart([{"name": "р", "values": [1, 7]}], ["a", "b"], w=320)
        self.assertIn('text-anchor="start"', narrow)

    def test_heatmap_scrolls_inside_its_own_box(self):
        html = kit.heatmap(["2026-09-01", "2026-09-02"], [10, 20])
        self.assertTrue(html.startswith('<div class="kit-scroll">'))
        self.assertIn('<div class="kit-heat">', html)
        self.assertEqual(html.count('<div class="kit-scroll">'), 1)

    def test_tile_footer_wraps_and_tile_clips(self):
        css = kit.component_css().replace(" ", "")
        self.assertIn("flex-wrap:wrap", css.split(".kit-sub{")[1].split("}")[0])
        self.assertIn("overflow:hidden", css.split(".kit-tile{")[1].split("}")[0])
        self.assertIn(".kit-sub.kit-spark{max-width:100%", css)

    def test_grid_minimums_never_exceed_container(self):
        # repeat(auto-fit, minmax(170px, 1fr)) на экране уже 170 px распирает
        # ряд наружу; min(170px,100%) честно складывает его в одну колонку.
        css = kit.component_css()
        for rule in (".kit-row{", ".kit-multi{"):
            block = css.split(rule)[1].split("}")[0]
            self.assertIn("minmax(min(", block, rule)

    def test_delta_arrow_never_breaks_from_its_number(self):
        html = kit.delta_html("+3486 +157,6%", "up")
        self.assertIn("\u25b2\u00a0+3486", html)   # стрелка и число неразрывны
        self.assertIn(" +157,6%", html)              # между числами перенос можно


class TestEmail(unittest.TestCase):
    def test_email_tile_fonts_within_uxlint_limits(self):
        t = kit.email_tile("Видимость", "926", "показов", "+9", "up", note="норма", meta="источник")
        sizes = [float(s) for s in re.findall(r"font-size:([\d.]+)px", t)]
        meta = [float(s) for s in re.findall(r'data-meta="1"[^>]*font-size:([\d.]+)px', t)]
        self.assertTrue(all(s >= 14 for s in sizes if s not in meta))
        self.assertTrue(all(s >= 12.5 for s in meta))
        self.assertNotIn("<img", t)
        self.assertNotIn("<svg", t)

    def test_email_status_and_bars_have_no_images(self):
        h = (kit.email_status_rows([{"state": "good", "name": "Индексация", "value": "169"}])
             + kit.email_bar_rows([{"label": "A", "value": 3}, {"label": "B", "value": 1}]))
        self.assertNotIn("<img", h)
        self.assertIn("✓", h)
        self.assertIn("width:100%", h)

    def test_png_document_is_self_contained(self):
        doc = kit.png_document(kit.sparkline([1, 2, 3], hex_mode=True), 300, 60)
        self.assertIn("--kit-s1:", doc)
        self.assertNotIn("<link", doc)


if __name__ == "__main__":
    unittest.main()
