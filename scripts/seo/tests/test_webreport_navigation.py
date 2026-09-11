"""Навигация и кат в веб-отчёте.

Отчёт вырос до сотен килобайт: один раздел «Реклама» — две трети страницы.
Читать его подряд невозможно, поэтому объёмное уходит под кат, а по разделам
можно перейти из липкой панели. Проверяем то, что легко сломать незаметно:
ядро отчёта не прячется, короткие блоки не прячутся, а заголовки остаются
видимыми у всех разделов — иначе оглавление и поиск по странице врут.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import webreport  # noqa: E402


def section(sid, crit, size, title="Раздел"):
    return {"id": sid, "title": title, "crit": crit, "desc": "описание",
            "html": "<p>" + "x" * size + "</p>"}


class CutTest(unittest.TestCase):
    def test_obyomnyy_razdel_uhodit_pod_kat(self):
        html = webreport._section_html(section("ads", 2, webreport.CUT_CHARS + 1))
        self.assertIn("<details class='cut'>", html)
        self.assertIn("объёмный блок", html)

    def test_spravochnyy_obyomnyy_uhodit_pod_kat(self):
        html = webreport._section_html(
            section("yandex-queries", 0, webreport.CUT_CHARS_REFERENCE + 1))
        self.assertIn("<details class='cut'>", html)
        self.assertIn("справочный блок", html)

    def test_korotkiy_spravochnyy_ostayotsya_otkrytym(self):
        html = webreport._section_html(section("ideas", 0, 500))
        self.assertNotIn("<details class='cut'>", html)

    def test_yadro_otchyota_ne_svorachivaetsya(self):
        html = webreport._section_html(
            section("experiments", 0, webreport.CUT_CHARS * 3))
        self.assertNotIn("<details class='cut'>", html)

    def test_zagolovok_i_opisanie_vidny_i_pod_katom(self):
        html = webreport._section_html(
            section("ads", 2, webreport.CUT_CHARS + 1, title="Реклама"))
        head = html.split("<details")[0]
        self.assertIn("Реклама", head)
        self.assertIn("описание", head)
        self.assertIn('id="ads"', head)

    def test_ssylka_naverh_u_kazhdogo_razdela(self):
        for s in (section("a", 2, 100), section("b", 0, webreport.CUT_CHARS + 1)):
            self.assertIn("href='#top'", webreport._section_html(s))


class NavbarTest(unittest.TestCase):
    def test_menyu_soderzhit_vse_razdely_i_vozvrat_v_nachalo(self):
        secs = [section("ads", 2, 10, "Реклама"), section("ideas", 0, 10, "Идеи")]
        nav = webreport._navbar(secs, "04.09.2026")
        self.assertIn("#ads", nav)
        self.assertIn("#ideas", nav)
        self.assertIn("href='#top'", nav)
        self.assertIn("04.09.2026", nav)

    def test_pometka_kritichnosti_perenositsya_v_menyu(self):
        nav = webreport._navbar([section("ads", 2, 10, "Реклама")], "04.09.2026")
        self.assertIn("chip", nav)


class OwnerDeskTest(unittest.TestCase):
    """Строка «От вас» и плашка шапки говорят одно и то же.

    09.09.2026 страница печатала «ОТ ВАС: 2 предложения» в шапке и «Срочных
    решений нет» строкой ниже, а сами предложения не называла: блок был только
    в письме.
    """

    DESK = ["ассортимент: 3 кандидата — «Каких вендоров добавить»",
            "продвижение: статья под кластер — «Перспективные идеи»"]

    def test_предложения_названы_на_странице(self):
        html = webreport._owner_desk_html(
            {"user_action_required": False, "owner_desk": self.DESK})
        self.assertIn("2 предложения", html)
        for d in self.DESK:
            self.assertIn(d, html)

    def test_при_срочном_решении_блок_не_дублируется(self):
        self.assertEqual(webreport._owner_desk_html(
            {"user_action_required": True, "owner_desk": self.DESK}), "")

    def test_пустой_стол_блока_не_даёт(self):
        self.assertEqual(webreport._owner_desk_html(
            {"user_action_required": False, "owner_desk": []}), "")


if __name__ == "__main__":
    unittest.main()
