"""Управленческие воздействия и решения по кандидатам (поручения 01.09.2026)."""

import json
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import report_v4  # noqa: E402


class RejectedVendorsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.old = report_v4.VENDOR_DECISIONS
        report_v4.VENDOR_DECISIONS = self.tmp / "vendor-decisions.json"

    def tearDown(self):
        report_v4.VENDOR_DECISIONS = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_отклонённый_бренд_выпадает_из_расширения(self):
        report_v4.VENDOR_DECISIONS.write_text(json.dumps(
            {"rejected": {"aws": {"date": "2026-09-01"}}}), encoding="utf-8")
        block = {"expansion": {
            "items": [{"brand": "aws"}, {"brand": "vercel"}],
            "manual_check": ["nordvpn", "AWS"]}}
        out = report_v4._drop_vendors_already_on_site(block)
        brands = [i["brand"] for i in out["expansion"]["items"]]
        self.assertNotIn("aws", brands)
        self.assertIn("vercel", brands)
        self.assertEqual(out["expansion"]["manual_check"], ["nordvpn"])

    def test_без_файла_решений_ничего_не_фильтруется(self):
        self.assertEqual(report_v4.rejected_vendor_brands(), set())


class ManagementActionsTest(unittest.TestCase):
    def test_постановки_собираются_из_предложений(self):
        exps = [{"id": "x", "ticket": "T-1", "next_review": "2026-09-02",
                 "impressions_since_deploy": 400,
                 "interim": {"relative_uplift": 0.6},
                 "evaluation": {}}]
        opps = {"available": True, "items": [
            {"cluster": "оплата artlist юридическим лицом",
             "evidence": "66 показов, позиция 3.4"}]}
        demand = {"expansion": {"items": [], "manual_check": ["nordvpn"]}}
        ideas = {"fresh": [{"title": "Идея", "why": "потому",
                            "steps": "шаги", "acceptance": "готово",
                            "from_you": "решение"}]}
        ma = report_v4._management_actions(exps, opps, demand, ideas)
        self.assertEqual(len(ma), 4)
        for m in ma:
            for k in ("task", "why", "steps", "acceptance", "from_you"):
                self.assertTrue(m[k], f"пустое поле {k} в «{m['task']}»")
        self.assertIn("EXPAND / KEEP / REVERT / EXTEND T-1", ma[0]["from_you"])

    def test_запрос_страницы_эксперимента_откладывается(self):
        # coreldraw — страница активного эксперимента: запрос не в работу,
        # а с пометкой «после вердикта».
        old = report_v4.exp_mod.REGISTRY
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            report_v4.exp_mod.REGISTRY = tmp / "r.json"
            report_v4.exp_mod.REGISTRY.write_text(json.dumps({"experiments": [
                {"id": "x", "ticket": "T-1", "start": "2026-08-19",
                 "status": "running", "pages": ["/vendors/coreldraw"]}]}),
                encoding="utf-8")
            exps = [{"id": "x", "ticket": "T-1", "next_review": "2026-09-02",
                     "impressions_since_deploy": 1, "interim": None,
                     "evaluation": {}}]
            opps = {"available": True, "items": [
                {"cluster": "оплата coreldraw для россиян", "evidence": "e"}]}
            ma = report_v4._management_actions(exps, opps, {}, {})
            snip = next(m for m in ma if "сниппеты" in m["task"].lower()
                        or "сниппет" in m["task"].lower())
            self.assertIn("после вердикта", snip["why"])
        finally:
            report_v4.exp_mod.REGISTRY = old
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
