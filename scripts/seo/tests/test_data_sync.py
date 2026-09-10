"""Обмен с веткой-хранилищем seo-data: push не затирает чужие правки.

Полная замена каталога била четырежды за неделю: 29.08 откат почтового
маркера и повторное письмо (issue #230), 30.08 три одновременных workflow
затёрли друг другу файлы, 31.08 сборщик удалил свежий site-check через 26
секунд после записи, 04.09 проверка живых страниц затёрла реестр
экспериментов через минуту после правки. Решение руководителя 04.09.2026 —
общая защита вместо точечных списков: pull запоминает снятую версию, push
отправляет только изменённое.

Тест гоняет настоящий `data_sync.sh` на настоящих репозиториях: bare-репо
играет origin, две рабочие копии — два параллельных прогона.
"""

import json
import os
import pathlib
import sys
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "seo" / "data_sync.sh"


def run(cmd, cwd, **kw):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           **kw.pop("env_extra", {})}
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, shell=isinstance(cmd, str),
                          capture_output=True, check=kw.pop("check", True), **kw)


class DataSyncTest(unittest.TestCase):
    """Два прогона работают одновременно, каждый пушит своё."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.origin = self.tmp / "origin.git"
        run(["git", "init", "--bare", "-b", "seo-data", str(self.origin)], self.tmp)

        # Заполняем хранилище: реестр, маркер письма и файл данных.
        seed = self.tmp / "seed"
        run(["git", "clone", str(self.origin), str(seed)], self.tmp)
        self.write(seed, "reports/seo/intelligence/seo-experiments.json", '{"v": 1}')
        self.write(seed, "reports/seo/intelligence/last-mailed.txt", "2026-09-03")
        self.write(seed, "reports/seo/data/yandex-2026-09-03.json", '{"day": 3}')
        run(["git", "add", "-A"], seed)
        run(["git", "commit", "-qm", "seed"], seed)
        run(["git", "push", "-q", "origin", "seo-data"], seed)

    def write(self, repo, rel, text):
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def read_origin(self, rel):
        out = run(["git", "show", f"seo-data:{rel}"], self.origin, check=False)
        return out.stdout if out.returncode == 0 else None

    def clone(self, name):
        """Рабочая копия прогона: код обмена берётся из репозитория проекта."""
        repo = self.tmp / name
        run(["git", "clone", "-q", str(self.origin), str(repo)], self.tmp)
        (repo / "scripts" / "seo").mkdir(parents=True, exist_ok=True)
        shutil.copy(SCRIPT, repo / "scripts" / "seo" / "data_sync.sh")
        # Ветка кода отдельно от ветки данных, как main и seo-data в проекте.
        run(["git", "checkout", "-qb", "main"], repo)
        return repo

    def sync(self, repo, *args):
        return run(["bash", "scripts/seo/data_sync.sh", *args], repo)

    # ── Сценарии гонки ──────────────────────────────────────────────────────

    def test_чужая_правка_не_затирается(self):
        """04.09: проверка сайта затёрла реестр экспериментов.

        Прогон A снял данные, прогон B за это время записал реестр. A пушит
        свой файл данных — реестр B обязан уцелеть.
        """
        a, b = self.clone("a"), self.clone("b")
        self.sync(a, "pull")                       # A снял версию 1

        self.sync(b, "pull")
        self.write(b, "reports/seo/intelligence/seo-experiments.json", '{"v": 2}')
        self.sync(b, "push", "правка реестра")

        self.write(a, "reports/seo/data/yandex-2026-09-04.json", '{"day": 4}')
        self.sync(a, "push", "данные дня")

        self.assertEqual(self.read_origin(
            "reports/seo/intelligence/seo-experiments.json"), '{"v": 2}')
        self.assertEqual(self.read_origin(
            "reports/seo/data/yandex-2026-09-04.json"), '{"day": 4}')

    def test_почтовый_маркер_не_откатывается(self):
        """29.08: push откатил last-mailed, и письмо ушло повторно."""
        a, b = self.clone("a"), self.clone("b")
        self.sync(a, "pull")

        self.sync(b, "pull")
        self.write(b, "reports/seo/intelligence/last-mailed.txt", "2026-09-04")
        self.sync(b, "push", "письмо отправлено")

        self.write(a, "reports/seo/data/yandex-2026-09-04.json", '{"day": 4}')
        self.sync(a, "push", "данные дня")

        self.assertEqual(self.read_origin(
            "reports/seo/intelligence/last-mailed.txt"), "2026-09-04")

    def test_свежий_файл_проверки_сайта_не_удаляется(self):
        """31.08: сборщик удалил site-check через 26 секунд после записи."""
        a, b = self.clone("a"), self.clone("b")
        self.sync(a, "pull")

        self.sync(b, "pull")
        self.write(b, "reports/seo/intelligence/site-check-2026-09-04.json", "{}")
        self.sync(b, "push", "проверка живых страниц")

        self.write(a, "reports/seo/data/yandex-2026-09-04.json", '{"day": 4}')
        self.sync(a, "push", "данные дня")

        self.assertIsNotNone(self.read_origin(
            "reports/seo/intelligence/site-check-2026-09-04.json"))

    # ── Прежнее поведение сохраняется ───────────────────────────────────────

    def test_свои_правки_доезжают(self):
        a = self.clone("a")
        self.sync(a, "pull")
        self.write(a, "reports/seo/intelligence/seo-experiments.json", '{"v": 9}')
        self.sync(a, "push", "правка")
        self.assertEqual(self.read_origin(
            "reports/seo/intelligence/seo-experiments.json"), '{"v": 9}')

    def test_удалённый_прогоном_файл_исчезает_из_хранилища(self):
        """Истёкший кэш должен уходить, иначе хранилище только растёт."""
        a = self.clone("a")
        self.sync(a, "pull")
        (a / "reports/seo/data/yandex-2026-09-03.json").unlink()
        self.sync(a, "push", "чистка кэша")
        self.assertIsNone(self.read_origin("reports/seo/data/yandex-2026-09-03.json"))

    def test_чужой_файл_не_воскресает_после_удаления(self):
        """Файл, удалённый другим прогоном, не возвращается нашей копией."""
        a, b = self.clone("a"), self.clone("b")
        self.sync(a, "pull")                       # у A файл ещё есть

        self.sync(b, "pull")
        (b / "reports/seo/data/yandex-2026-09-03.json").unlink()
        self.sync(b, "push", "чистка кэша")

        self.write(a, "reports/seo/data/yandex-2026-09-04.json", '{"day": 4}')
        self.sync(a, "push", "данные дня")
        self.assertIsNone(self.read_origin("reports/seo/data/yandex-2026-09-03.json"))

    def test_каталог_владение_ограничивает_отправку(self):
        a = self.clone("a")
        self.sync(a, "pull")
        self.write(a, "reports/seo/data/yandex-2026-09-04.json", '{"day": 4}')
        self.write(a, "reports/seo/intelligence/seo-experiments.json", '{"v": 7}')
        self.sync(a, "push", "только данные", "reports/seo/data")
        self.assertEqual(self.read_origin(
            "reports/seo/data/yandex-2026-09-04.json"), '{"day": 4}')
        self.assertEqual(self.read_origin(
            "reports/seo/intelligence/seo-experiments.json"), '{"v": 1}')

    def test_без_изменений_ничего_не_отправляется(self):
        a = self.clone("a")
        self.sync(a, "pull")
        out = self.sync(a, "push", "пустой прогон")
        self.assertIn("изменений нет", out.stdout)

    def test_push_без_pull_работает_от_текущего_состояния(self):
        """Сессия может пушить без pull: сверять не с чем, берём хранилище."""
        a = self.clone("a")
        self.write(a, "reports/seo/intelligence/seo-experiments.json", '{"v": 5}')
        out = self.sync(a, "push", "правка без pull")
        self.assertIn("метки pull нет", out.stdout)
        self.assertEqual(self.read_origin(
            "reports/seo/intelligence/seo-experiments.json"), '{"v": 5}')

    def test_каталог_вне_списка_отвергается(self):
        a = self.clone("a")
        self.sync(a, "pull")
        out = run(["bash", "scripts/seo/data_sync.sh", "push", "x", "reports/other"],
                  a, check=False)
        self.assertEqual(out.returncode, 2)
        self.assertIn("вне списка хранилища", out.stderr)


if __name__ == "__main__":
    unittest.main()


class RevisionHistoryTest(unittest.TestCase):
    """Учёт пересборов читает историю ветки данных, а не текущей.

    09.09.2026 выгрузка Яндекса собиралась дважды: в 04:47 UTC она дала 650
    страниц в поиске, в 08:19 — 455. Отчёт ушёл в 04:54 по первой цифре, и о
    пересмотре не узнал никто: git_revisions вызывал «git log» на рабочей
    копии main, где reports/seo/data лежит в .gitignore и истории не имеет.
    Список всегда был пуст, а вместе с ним молчали и находки о пересборе.
    """

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.origin = self.tmp / "origin.git"
        run(["git", "init", "--bare", "-b", "seo-data", str(self.origin)], self.tmp)

        seed = self.tmp / "seed"
        run(["git", "clone", "-q", str(self.origin), str(seed)], self.tmp)
        self.commit_value(seed, 650, "2026-09-09T04:47:02")
        self.commit_value(seed, 455, "2026-09-09T08:19:00")
        run(["git", "push", "-q", "origin", "seo-data"], seed)

        self.repo = self.tmp / "run"
        run(["git", "clone", "-q", str(self.origin), str(self.repo)], self.tmp)
        run(["git", "checkout", "-qb", "main"], self.repo)
        # Как в проекте: код на main, данные — только в ветке хранилища.
        (self.repo / ".gitignore").write_text("reports/seo/data/\n", encoding="utf-8")

    def commit_value(self, repo, pages, when):
        p = repo / "reports" / "seo" / "data" / "yandex-2026-09-09.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"summary": {"searchable_pages_count": pages}}),
                     encoding="utf-8")
        run(["git", "add", "-A"], repo)
        run(["git", "commit", "-qm", f"сбор {pages}"], repo,
            env_extra={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when})

    def revisions(self):
        code = (
            "import sys, json\n"
            f"sys.path.insert(0, {str(ROOT / 'scripts' / 'seo')!r})\n"
            "import snapshot\n"
            "print(json.dumps(snapshot.revisions_for('yandex', '2026-09-09',"
            " lambda d: d.get('summary', {}).get('searchable_pages_count'), 'm')))\n")
        out = run([sys.executable, "-c", code], self.repo)
        return json.loads(out.stdout)

    def test_оба_сбора_дня_видны(self):
        self.repo.joinpath("reports/seo/data").mkdir(parents=True, exist_ok=True)
        run(["git", "restore", "--source", "origin/seo-data", "--worktree",
             "--", "reports/seo/data"], self.repo)
        rev = self.revisions()
        self.assertIsNotNone(rev)
        self.assertEqual(rev["values_seen"], [455.0, 650.0])
        self.assertEqual(rev["canonical"], 455.0)

    def test_локальная_ветка_данных_подходит_когда_нет_origin(self):
        run(["git", "restore", "--source", "origin/seo-data", "--worktree",
             "--", "reports/seo/data"], self.repo)
        run(["git", "update-ref", "-d", "refs/remotes/origin/seo-data"], self.repo)
        self.assertEqual(self.revisions()["values_seen"], [455.0, 650.0])

    def test_без_ветки_данных_проверка_молчит(self):
        run(["git", "restore", "--source", "origin/seo-data", "--worktree",
             "--", "reports/seo/data"], self.repo)
        for ref in ("refs/remotes/origin/seo-data", "refs/heads/seo-data"):
            run(["git", "update-ref", "-d", ref], self.repo, check=False)
        self.assertIsNone(self.revisions())


if __name__ == "__main__":
    unittest.main()
