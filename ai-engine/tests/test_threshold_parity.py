import json
from pathlib import Path
import unittest
from app.threat.config import LEVEL_NAMES, ScoringConfig, load_threat_thresholds_file


def test_threshold_config_file_loads():
    tiers = load_threat_thresholds_file()
    assert len(tiers) == 4
    assert [name for name, _ in tiers] == list(LEVEL_NAMES)
    assert tiers == [("LOW", 0), ("MEDIUM", 30), ("HIGH", 60), ("CRITICAL", 80)]


def test_threshold_parity_with_shared_fixture():
    fixture_paths = [
        Path(__file__).resolve().parent.parent.parent / "docs" / "fixtures" / "threshold_cases.json",
        Path(__file__).resolve().parent.parent / "docs" / "fixtures" / "threshold_cases.json",
        Path("docs/fixtures/threshold_cases.json"),
    ]
    target = None
    for p in fixture_paths:
        if p.exists():
            target = p
            break

    assert target is not None, "Shared threshold fixture docs/fixtures/threshold_cases.json must exist"

    with open(target, "r", encoding="utf-8") as f:
        cases = json.load(f)

    tiers = load_threat_thresholds_file()
    cfg = ScoringConfig(
        max_score=100,
        window_s=60.0,
        alert_min_score=30,
        cooldown_s=60.0,
        rearm_s=30.0,
        merge_by_plate=True,
        merge_scope="camera",
        levels=tiers,
        bonus=None,
        sources=[],
    )

    for tc in cases:
        score = tc["score"]
        expected_tier = tc["tier"]
        actual_tier = cfg.level_for(score)
        assert actual_tier == expected_tier, f"Score {score} expected tier {expected_tier}, got {actual_tier}"


class TestThresholdParity(unittest.TestCase):
    def test_loads(self):
        test_threshold_config_file_loads()

    def test_parity(self):
        test_threshold_parity_with_shared_fixture()


if __name__ == "__main__":
    unittest.main()
