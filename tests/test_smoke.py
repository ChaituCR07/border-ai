import os
import unittest
from scripts.smoke_e2e import check_log_errors, SmokeTestRunner


class TestSmokeHarness(unittest.TestCase):
    def test_log_error_detection_with_allowlist(self):
        test_log = "artifacts/tmp_test.log"
        os.makedirs("artifacts", exist_ok=True)
        with open(test_log, "w", encoding="utf-8") as f:
            f.write("INFO normal startup\n")
            f.write("ERROR connection refused to redis (retrying)\n")
            f.write("ERROR fatal unhandled crash dump\n")

        errors = check_log_errors(test_log, allowlist_path="scripts/log_allowlist.txt")
        self.assertEqual(len(errors), 1)
        self.assertIn("fatal unhandled crash dump", errors[0])

        if os.path.exists(test_log):
            os.remove(test_log)

    def test_smoke_stage_runner_records_result(self):
        runner = SmokeTestRunner()
        res = runner.run_stage("Test Stage", lambda: (True, "Stage passed"))
        self.assertTrue(res)
        self.assertEqual(len(runner.results), 1)
        self.assertEqual(runner.results[0][1], "PASSED")


if __name__ == "__main__":
    unittest.main()
