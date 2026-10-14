import random

import pytest

from app.watchlist.config import WatchlistConfig
from app.watchlist.matcher import lookup_in_repo
from app.watchlist.repo import InMemoryWatchlistRepo

pytestmark = pytest.mark.slow


def test_matching_stays_correct_with_ten_thousand_entries():
    rng = random.Random(5)
    repo = InMemoryWatchlistRepo()
    letters = "ABCDEFGHJKLMNPRSTUVWXYZ"
    plates = set()
    while len(plates) < 10_000:
        plates.add(f"KA{rng.randint(1, 99):02d}{rng.choice(letters)}{rng.choice(letters)}{rng.randint(1000, 9999)}")
    for p in plates:
        repo.add("VEHICLE", p, "n", "LOW")
    target = sorted(plates)[1234]
    cfg = WatchlistConfig()

    exact = lookup_in_repo(repo, target, cfg)
    assert exact.match_type == "exact" and exact.entry.normalized_identifier == target

    unlisted = "MH12XY4321"
    assert unlisted not in plates and lookup_in_repo(repo, unlisted, cfg) is None
