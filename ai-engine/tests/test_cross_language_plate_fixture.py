import json
import os
import pytest
from app.watchlist.normalize import normalize_plate

def test_cross_language_plate_fixtures():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "plate_normalization.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)
    
    for case in fixtures:
        actual = normalize_plate(case["input"])
        assert actual == case["expected"], f"Failed for {case['input']}: got {actual}, expected {case['expected']}"
