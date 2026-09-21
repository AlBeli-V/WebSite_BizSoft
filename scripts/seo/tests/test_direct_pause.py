"""Остановка кампании: выбор цели перед записью (21.09.2026).

Скрипт переводит кампанию в паузу — необратимого тут ничего нет, но
остановить можно не ту: в кабинете рядом живут кампании Apple, которые
работают и к эксперименту отношения не имеют. Плюс вторая беда тише:
остановка уже остановленной или архивной кампании выглядит как успех и
скрывает, что состояние кабинета не то, которое ожидали.

Обе защиты держит pick(), и обе проверяются здесь.
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ppc"))
import direct_pause  # noqa: E402


def _camp(name, state="ON", cid=1):
    return {"Id": cid, "Name": name, "State": state, "Status": "ACCEPTED"}


CABINET = [
    _camp("bs-test-2026-09", cid=713927850),
    _camp("bs-apple-gift-2026-09", cid=714166675),
    _camp("bs-apple-regions-2026-09", cid=714166677),
]


class PauseTest(unittest.TestCase):
    def test_выбирает_кампанию_эксперимента(self):
        camp = direct_pause.pick(CABINET, "bs-test-2026-09")
        self.assertEqual(camp["Id"], 713927850)

    def test_не_трогает_кампании_apple(self):
        # Имя сверяется точным совпадением: префиксов и подстрок не бывает.
        with self.assertRaises(SystemExit) as ctx:
            direct_pause.pick(CABINET, "bs-apple")
        self.assertIn("не найдена", str(ctx.exception))

    def test_падает_на_одноимённых_кампаниях(self):
        double = CABINET + [_camp("bs-test-2026-09", cid=999)]
        with self.assertRaises(SystemExit) as ctx:
            direct_pause.pick(double, "bs-test-2026-09")
        self.assertIn("несколько", str(ctx.exception))

    def test_не_останавливает_уже_остановленную(self):
        paused = [_camp("bs-test-2026-09", state="SUSPENDED", cid=713927850)]
        with self.assertRaises(SystemExit) as ctx:
            direct_pause.pick(paused, "bs-test-2026-09")
        self.assertIn("SUSPENDED", str(ctx.exception))

    def test_не_останавливает_архивную(self):
        archived = [_camp("bs-test-2026-09", state="ARCHIVED", cid=713927850)]
        with self.assertRaises(SystemExit):
            direct_pause.pick(archived, "bs-test-2026-09")

    def test_пустой_кабинет_называет_причину(self):
        with self.assertRaises(SystemExit) as ctx:
            direct_pause.pick([], "bs-test-2026-09")
        self.assertIn("пусто", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
