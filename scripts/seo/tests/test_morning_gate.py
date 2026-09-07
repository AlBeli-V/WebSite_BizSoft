"""Сторож утренних контуров: когда запускать конвейер, а когда молчать.

Планировщик GitHub задерживает слоты на 4–5 часов, поэтому решение о запуске
принимает не расписание, а сторож — по московскому времени и маркеру
отправки. Ошибка здесь стоит либо второго письма за день, либо тишины
вместо утреннего отчёта, поэтому границы окна проверяются тестами.
"""

import pathlib
import subprocess
import unittest

GATE = pathlib.Path(__file__).resolve().parents[2] / "ops" / "morning_gate.sh"


def decide(hour, today="2026-09-05", mailed=""):
    r = subprocess.run(["bash", str(GATE), hour, today, mailed],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


class MorningGateTest(unittest.TestCase):
    def test_do_okna_molchit(self):
        self.assertTrue(decide("05", mailed="2026-09-04").startswith("skip:"))

    def test_v_shest_zapuskaet(self):
        # Нижняя граница опущена до шести 06.09.2026: за ночь сторожа будят
        # два-три раза, и окно 09–13 они пропускали целиком.
        self.assertTrue(decide("06", mailed="2026-09-04").startswith("run:"))

    def test_v_sem_zapuskaet(self):
        self.assertTrue(decide("07", mailed="2026-09-04").startswith("run:"))

    def test_v_devyat_zapuskaet(self):
        self.assertTrue(decide("09", mailed="2026-09-04").startswith("run:"))

    def test_v_trinadtsat_esche_zapuskaet(self):
        self.assertTrue(decide("13", mailed="2026-09-04").startswith("run:"))

    def test_v_chetyrnadtsat_pozdno(self):
        self.assertTrue(decide("14", mailed="2026-09-04").startswith("skip:"))

    def test_nochyu_molchit(self):
        for h in ("00", "03", "05"):
            self.assertTrue(decide(h, mailed="2026-09-04").startswith("skip:"), h)

    def test_pismo_uzhe_otpravleno(self):
        out = decide("10", mailed="2026-09-05")
        self.assertTrue(out.startswith("skip:"))
        self.assertIn("уже отправлено", out)

    def test_pustoy_marker_ne_meshaet(self):
        self.assertTrue(decide("10", mailed="").startswith("run:"))

    def test_chas_s_veduschim_nulyom_ne_lomaet_arifmetiku(self):
        # «08» и «09» — не восьмеричные числа: без 10# скрипт падал бы.
        self.assertTrue(decide("08").startswith("run:"))
        self.assertTrue(decide("09").startswith("run:"))
        self.assertTrue(decide("05").startswith("skip:"))


if __name__ == "__main__":
    unittest.main()
