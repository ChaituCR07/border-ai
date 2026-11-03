import unittest
from scripts.chaos.inject_fault import ChaosController


class TestChaosInjection(unittest.TestCase):
    def test_chaos_simulation_runs_all_faults(self):
        controller = ChaosController()
        ok = controller.run_all()
        self.assertTrue(ok)
        self.assertEqual(len(controller.results), 6)
        self.assertTrue(all(r.passed for r in controller.results))

    def test_chaos_report_generation(self):
        controller = ChaosController()
        controller.run_all()
        report_path = "artifacts/tmp_chaos_results.md"
        controller.write_report(report_path)

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("F1", content)
        self.assertIn("F2", content)
        self.assertIn("F8", content)
        self.assertIn("PASSED", content)


if __name__ == "__main__":
    unittest.main()
