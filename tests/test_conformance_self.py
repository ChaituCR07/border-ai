import unittest
from scripts.conformance.scan import ConformanceScanner


class TestConformanceSelf(unittest.TestCase):
    def test_catches_planted_canary_secret(self):
        scanner = ConformanceScanner(canaries=["zq9canaryTestSecret"])
        fake_log = "2026-11-03 connecting to url rtsp://user:zq9canaryTestSecret@localhost"
        scanner.scan_text(fake_log, "fake_log.log")
        self.assertEqual(len(scanner.violations), 1)
        self.assertEqual(scanner.violations[0].check_type, "CANARY_SECRET_LEAK")
        # Ensure secret is masked in report detail
        self.assertNotIn("zq9canaryTestSecret", scanner.violations[0].detail)
        self.assertIn("zq9***et", scanner.violations[0].detail)

    def test_catches_raw_biometric_embedding_array(self):
        scanner = ConformanceScanner()
        # 64 floats
        floats = ", ".join(["0.123456"] * 64)
        fake_payload = f'{{"subject": "KA01", "embedding": [{floats}]}}'
        scanner.scan_text(fake_payload, "api_response.json")
        self.assertEqual(len(scanner.violations), 1)
        self.assertEqual(scanner.violations[0].check_type, "BIOMETRIC_EMBEDDING_LEAK")

    def test_catches_pii_in_info_logs(self):
        scanner = ConformanceScanner()
        log_lines = [
            "2026-11-03 [DEBUG] OCR candidate plate KA01AB1234 confidence 0.95",
            "2026-11-03 [INFO] Vehicle detected with plate KA01AB1234 passing gate",
        ]
        scanner.scan_log_for_pii(log_lines, "KA01AB1234", "camera.log")
        self.assertEqual(len(scanner.violations), 1)
        self.assertEqual(scanner.violations[0].check_type, "PII_IN_INFO_LOG")

    def test_clean_input_passes_with_zero_violations(self):
        scanner = ConformanceScanner(canaries=["zq9canarySecret"])
        clean_log = "2026-11-03 [INFO] System pipeline operational. 25.0 FPS."
        scanner.scan_text(clean_log, "clean.log")
        self.assertEqual(len(scanner.violations), 0)


if __name__ == "__main__":
    unittest.main()
