from datetime import datetime, timezone
import unittest
from tests.integration.harness.scenario_spec import ScenarioSpec, SpecValidationError
from tests.integration.harness.evaluator import ScenarioEvaluator, plate_key
from tests.integration.harness.quiescence import wait_for_quiescence


class TestHarnessSelf(unittest.TestCase):
    def test_spec_validation_rejects_unknown_keys(self):
        data = {
            "id": "s1",
            "unknown_bogus_field": 123,
        }
        with self.assertRaises(SpecValidationError):
            ScenarioSpec.from_dict(data)

    def test_spec_validation_rejects_inverted_time_windows(self):
        data = {
            "id": "s1",
            "expect": {
                "events": [{"type": "ZONE_ENTRY", "within_s": [60.0, 10.0]}],
            },
        }
        with self.assertRaises(SpecValidationError):
            ScenarioSpec.from_dict(data)

    def test_evaluator_catches_missing_events_and_wrong_camera(self):
        spec_dict = {
            "id": "s1",
            "expect": {
                "events": [
                    {"type": "LINE_CROSSING", "camera": "CAM-01", "within_s": [0, 100]},
                    {"type": "RESTRICTED_ZONE_ENTRY", "camera": "CAM-01", "within_s": [0, 100]},
                ],
                "alerts": [
                    {"priority": "HIGH", "score": 60, "count": 1},
                ],
            },
        }
        spec = ScenarioSpec.from_dict(spec_dict)
        t0 = datetime(2026, 11, 3, 10, 0, 0, tzinfo=timezone.utc)
        evaluator = ScenarioEvaluator(spec, t0)

        # Events only has LINE_CROSSING on CAM-02 (wrong camera), missing RESTRICTED_ZONE_ENTRY
        events = [
            {"event_type": "LINE_CROSSING", "camera_id": "CAM-02", "timestamp": "2026-11-03T10:00:05.000000Z"}
        ]
        alerts = [
            {"priority": "HIGH", "threat_score": 60}
        ]

        res = evaluator.evaluate(events, alerts)
        self.assertFalse(res.passed)
        self.assertEqual(len(res.errors), 2)  # Missing CAM-01 event and missing zone entry

    def test_evaluator_catches_forbidden_events(self):
        spec_dict = {
            "id": "s2",
            "forbidden": [
                {"type": "WATCHLIST_MATCH", "plate_not": "KA01AB1234"},
            ],
        }
        spec = ScenarioSpec.from_dict(spec_dict)
        t0 = datetime(2026, 11, 3, 10, 0, 0, tzinfo=timezone.utc)
        evaluator = ScenarioEvaluator(spec, t0)

        events = [
            {"event_type": "WATCHLIST_MATCH", "plate": "MH12CD5678"}
        ]
        res = evaluator.evaluate(events, [])
        self.assertFalse(res.passed)
        self.assertIn("Forbidden event emitted", res.errors[0])

    def test_quiescence_detector_waits_for_lag_drain(self):
        # Starts with lag, then drains
        states = [
            {"sink_lag": 5, "pending_notifications": 0, "event_count": 10},
            {"sink_lag": 0, "pending_notifications": 0, "event_count": 10},
            {"sink_lag": 0, "pending_notifications": 0, "event_count": 10},
            {"sink_lag": 0, "pending_notifications": 0, "event_count": 10},
        ]
        idx = [0]

        def poll():
            cur = states[min(idx[0], len(states) - 1)]
            idx[0] += 1
            return cur

        ok = wait_for_quiescence(poll, quiet_window_s=0.2, timeout_s=3.0, poll_interval_s=0.05)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
