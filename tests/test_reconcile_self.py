from datetime import datetime, timezone, timedelta
import unittest
from scripts.reconcile import Reconciler


class TestReconciliationSelf(unittest.TestCase):
    def test_r01_catches_missing_events(self):
        r = Reconciler()
        journal_ids = {"ev-1", "ev-2", "ev-3"}
        db_ids = {"ev-1"}
        dead_ids = {"ev-2"}
        # ev-3 is neither in DB nor dead-letter
        r.check_r01_journal_subset(journal_ids, db_ids, dead_ids)
        self.assertEqual(len(r.violations), 1)
        self.assertEqual(r.violations[0].rule_id, "R01")

    def test_r02_catches_extra_db_events_in_strict_mode(self):
        r = Reconciler(strict=True)
        journal_ids = {"ev-1"}
        db_ids = {"ev-1", "ev-bogus"}
        r.check_r02_db_extra_events(journal_ids, db_ids)
        self.assertEqual(len(r.violations), 1)
        self.assertEqual(r.violations[0].rule_id, "R02")

    def test_r03_catches_duplicate_event_ids(self):
        r = Reconciler()
        journal = ["ev-1", "ev-2", "ev-1"]
        db = ["ev-1", "ev-2"]
        r.check_r03_uniqueness(journal, db)
        self.assertEqual(len(r.violations), 1)
        self.assertEqual(r.violations[0].rule_id, "R03")

    def test_r04_catches_redis_alert_missing_in_db(self):
        r = Reconciler()
        r.check_r04_alert_origin({"al-1", "al-2"}, {"al-1"})
        self.assertEqual(len(r.violations), 1)
        self.assertEqual(r.violations[0].rule_id, "R04")

    def test_r05_catches_critical_alert_without_notification(self):
        r = Reconciler()
        alerts = [{"alert_id": "al-crit-1", "priority": "CRITICAL"}]
        notifications = []
        r.check_r05_critical_notifications(alerts, notifications)
        self.assertEqual(len(r.violations), 1)
        self.assertEqual(r.violations[0].rule_id, "R05")

    def test_r06_catches_sent_notification_missing_in_mailpit(self):
        r = Reconciler()
        notifs = [{"notification_id": "n-1", "status": "SENT", "message_id": "<msg-123@border-ai>"}]
        mailpit_msgs = {"<msg-other@border-ai>"}
        r.check_r06_mailpit_match(notifs, mailpit_msgs)
        self.assertEqual(len(r.violations), 1)
        self.assertEqual(r.violations[0].rule_id, "R06")

    def test_r07_catches_future_timestamps(self):
        r = Reconciler()
        now = datetime(2026, 11, 3, 10, 0, 0, tzinfo=timezone.utc)
        future_ts = (now + timedelta(seconds=60)).isoformat()
        events = [{"camera_id": "CAM-01", "timestamp": future_ts}]
        r.check_r07_timestamps(events, now_dt=now)
        self.assertEqual(len(r.violations), 1)
        self.assertEqual(r.violations[0].rule_id, "R07")

    def test_r08_catches_missing_snapshot_file(self):
        r = Reconciler()
        alerts = [{"alert_id": "al-1", "snapshot_path": "non_existent_image.jpg"}]
        r.check_r08_snapshot_files(alerts, snapshot_base_dir="artifacts/tmp_missing")
        self.assertEqual(len(r.violations), 1)
        self.assertEqual(r.violations[0].rule_id, "R08")

    def test_r10_catches_sequence_gaps(self):
        r = Reconciler()
        r.check_r10_websocket_seq([1, 2, 4, 5])
        self.assertEqual(len(r.violations), 1)
        self.assertEqual(r.violations[0].rule_id, "R10")

    def test_r11_catches_dead_letter_missing_reason(self):
        r = Reconciler()
        r.check_r11_dead_letter_reasons([{"event_id": "ev-fail", "reason": ""}])
        self.assertEqual(len(r.violations), 1)
        self.assertEqual(r.violations[0].rule_id, "R11")

    def test_clean_input_passes_with_zero_violations(self):
        r = Reconciler(strict=True)
        r.check_r01_journal_subset({"ev-1"}, {"ev-1"}, set())
        r.check_r02_db_extra_events({"ev-1"}, {"ev-1"})
        r.check_r03_uniqueness(["ev-1"], ["ev-1"])
        r.check_r04_alert_origin({"al-1"}, {"al-1"})
        r.check_r05_critical_notifications([{"alert_id": "al-1", "priority": "CRITICAL"}], [{"alert_id": "al-1"}])
        r.check_r10_websocket_seq([1, 2, 3, 4])
        self.assertEqual(len(r.violations), 0)


if __name__ == "__main__":
    unittest.main()
