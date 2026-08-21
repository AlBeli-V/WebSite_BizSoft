"""Выравнивание веток: логика решений на настоящем git-репозитории.

Механизм трогает чужие ветки, поэтому проверяется не на заглушках, а на
временном репозитории с воспроизведёнными ситуациями: отставшая ветка,
squash-мерж, конфликт, активная работа.

Главная из них — squash. После squash-мержа в ветке остаётся коммит, которого
нет в main по хешу, хотя все его изменения там уже есть. По счёту коммитов
такая ветка выглядит живой вечно и копится в списке годами.
"""
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('sync', ROOT / 'scripts/git/sync_branches.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def run(*args: str, cwd: str) -> str:
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args)}: {r.stderr[:200]}")
    return r.stdout.strip()


class TestOnRealRepo(unittest.TestCase):
    """Ситуации собираются настоящими командами git, а не описываются словами."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.origin = os.path.join(cls.tmp, 'origin')
        cls.work = os.path.join(cls.tmp, 'work')
        os.makedirs(cls.origin)
        run('git', 'init', '--bare', '-b', 'main', '.', cwd=cls.origin)
        run('git', 'clone', cls.origin, cls.work, cwd=cls.tmp)
        g = lambda *a: run(*a, cwd=cls.work)
        g('git', 'config', 'user.email', 'test@test')
        g('git', 'config', 'user.name', 'test')

        pathlib.Path(cls.work, 'base.txt').write_text('base\n')
        g('git', 'add', '.'); g('git', 'commit', '-m', 'base'); g('git', 'push', 'origin', 'main')

        # Ветка со своей работой, потом main ушёл вперёд.
        g('git', 'checkout', '-b', 'claude/behind')
        pathlib.Path(cls.work, 'feature.txt').write_text('feature\n')
        g('git', 'add', '.'); g('git', 'commit', '-m', 'feature')
        g('git', 'push', 'origin', 'claude/behind')

        g('git', 'checkout', 'main')
        pathlib.Path(cls.work, 'other.txt').write_text('other\n')
        g('git', 'add', '.'); g('git', 'commit', '-m', 'other'); g('git', 'push', 'origin', 'main')

        # Ветка, слитая squash: содержимое в main, коммит свой.
        g('git', 'checkout', '-b', 'claude/squashed', 'main')
        pathlib.Path(cls.work, 'sq.txt').write_text('squashed\n')
        g('git', 'add', '.'); g('git', 'commit', '-m', 'sq')
        g('git', 'push', 'origin', 'claude/squashed')
        g('git', 'checkout', 'main')
        g('git', 'merge', '--squash', 'claude/squashed')
        g('git', 'commit', '-m', 'squash merge'); g('git', 'push', 'origin', 'main')

        # Ветка, конфликтующая с main: один файл изменён с обеих сторон
        # после расхождения — только так возникает настоящий конфликт.
        g('git', 'checkout', '-b', 'claude/conflict', 'main')
        pathlib.Path(cls.work, 'other.txt').write_text('версия ветки\n')
        g('git', 'add', '.'); g('git', 'commit', '-m', 'ветка правит other.txt')
        g('git', 'push', 'origin', 'claude/conflict')
        g('git', 'checkout', 'main')
        pathlib.Path(cls.work, 'other.txt').write_text('версия main\n')
        g('git', 'add', '.'); g('git', 'commit', '-m', 'main правит other.txt')
        g('git', 'push', 'origin', 'main')
        run('git', 'fetch', 'origin', cwd=cls.work)

        cls.prev = os.getcwd()
        os.chdir(cls.work)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.prev)

    def test_finds_only_claude_branches(self):
        names = sync.branches()
        self.assertIn('claude/behind', names)
        self.assertNotIn('main', names)

    def test_squashed_branch_has_no_own_changes(self):
        """Иначе такая ветка висит в списке вечно и мешает видеть живые."""
        self.assertFalse(sync.has_own_changes('claude/squashed'))

    def test_branch_with_work_is_not_treated_as_merged(self):
        self.assertTrue(sync.has_own_changes('claude/behind'))

    def test_counts_reflect_divergence(self):
        behind, ahead = sync.counts('claude/behind')
        self.assertGreater(behind, 0)
        self.assertGreater(ahead, 0)

    def test_conflict_is_reported_not_forced(self):
        """Конфликт останавливает слияние и называет файл, а не решается сам."""
        state, detail = sync.try_merge('claude/conflict', apply=False)
        self.assertEqual(state, 'conflict')
        self.assertIn('other.txt', detail)

    def test_conflict_leaves_branch_untouched(self):
        sync.try_merge('claude/conflict', apply=False)
        # После неудачи рабочая копия должна быть чистой, иначе следующая
        # ветка сольётся поверх недоделанного слияния предыдущей.
        self.assertEqual(run('git', 'status', '--porcelain', cwd=self.work), '')

    def test_dry_run_does_not_push(self):
        before = run('git', 'rev-parse', 'origin/claude/behind', cwd=self.work)
        sync.try_merge('claude/behind', apply=False)
        run('git', 'fetch', 'origin', cwd=self.work)
        after = run('git', 'rev-parse', 'origin/claude/behind', cwd=self.work)
        self.assertEqual(before, after)

    def test_idle_days_counts_from_now(self):
        """От текущего момента, а не от даты коммита main: main отстаёт сам."""
        self.assertEqual(sync.days_idle('claude/behind'), 0)


if __name__ == '__main__':
    unittest.main(verbosity=1)


class VerifyCommands(unittest.TestCase):
    """Проверяющий обязан звать команды, которые в проекте есть.

    Первый рабочий прогон отбраковал все четыре ветки с «Command "check"
    not found»: verify() звал несуществующий `pnpm check`. Со стороны это
    выглядело как сломанный код в ветках, хотя сломан был сам проверяющий,
    и ни одна ветка не была выровнена.
    """

    def test_all_verify_commands_exist_in_package_json(self):
        import inspect
        import json
        import re

        with open(ROOT / 'package.json', encoding='utf-8') as f:
            scripts = json.load(f)['scripts']

        source = inspect.getsource(sync.verify)
        called = re.findall(r'\["pnpm",\s*"([a-z:-]+)"\]', source)
        self.assertTrue(called, 'не нашли ни одной команды в verify()')
        for name in called:
            self.assertIn(name, scripts, f'pnpm {name} в package.json нет')
