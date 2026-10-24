import pytest

from app.db.alert_workflow import ALLOWED, STATUSES, TERMINAL, sources_for


def test_every_status_is_covered_and_terminal_states_are_final():
    assert set(ALLOWED) == set(STATUSES)
    for s in TERMINAL:
        assert ALLOWED[s] == ()


def test_nothing_moves_back_to_new():
    assert all("NEW" not in targets for targets in ALLOWED.values())
    assert sources_for("NEW") == []


@pytest.mark.parametrize("target, expected", [
    ("ACKNOWLEDGED", {"NEW"}),
    ("IN_PROGRESS", {"NEW", "ACKNOWLEDGED"}),
    ("RESOLVED", {"NEW", "ACKNOWLEDGED", "IN_PROGRESS"}),
    ("FALSE_POSITIVE", {"NEW", "ACKNOWLEDGED", "IN_PROGRESS"}),
])
def test_sources_for_each_target(target, expected):
    assert set(sources_for(target)) == expected
