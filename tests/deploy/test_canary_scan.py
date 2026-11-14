import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.compose_canary_scan import scan_repository, scan_text, ROOT_DIR

class TestCanaryScanner(unittest.TestCase):
    def test_repository_has_zero_canary_leaks(self):
        findings = scan_repository(ROOT_DIR)
        # Exclude this test file and scanner itself
        clean_findings = [
            f for f in findings
            if not f[0].endswith("compose_canary_scan.py")
            and not f[0].endswith("test_canary_scan.py")
        ]
        self.assertEqual(
            len(clean_findings),
            0,
            f"Repository contains unencrypted or leaked secrets: {clean_findings}"
        )

    def test_scanner_detects_planted_canary_token(self):
        test_snippet = 'const token = "CANARY_SECRET_LEAK_TEST_TOKEN";'
        findings = scan_text(test_snippet, "mock_source.ts")
        self.assertEqual(len(findings), 1)
        self.assertIn("Synthetic test canary", findings[0][2])

    def test_scanner_detects_hardcoded_database_password(self):
        test_snippet = "POSTGRES_PASSWORD: mySuperSecretPassword123!"
        findings = scan_text(test_snippet, "docker-compose.test.yml")
        self.assertEqual(len(findings), 1)
        self.assertIn("PostgreSQL password", findings[0][2])

    def test_scanner_ignores_safe_file_reference(self):
        safe_snippet = "POSTGRES_PASSWORD_FILE: /run/secrets/pg_admin_password"
        findings = scan_text(safe_snippet, "docker-compose.yml")
        self.assertEqual(len(findings), 0)

if __name__ == "__main__":
    unittest.main()
