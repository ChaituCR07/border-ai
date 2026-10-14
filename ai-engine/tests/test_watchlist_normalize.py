import pytest

from app.watchlist.models import InvalidEntry
from app.watchlist.normalize import normalize_plate, prepare_entry, validate_update_fields


def test_normalization_ignores_case_spaces_and_punctuation():
    assert normalize_plate("ka-01 ab 1234") == "KA01AB1234"


def test_normalization_corrects_lookalikes_like_anpr_does():
    assert normalize_plate("KAO1AB1234") == "KA01AB1234"


@pytest.mark.parametrize("text", ["KA01AB1234", "kao1ab1234", "MH2CDE5678", "ABC1234", "IND KA01AB1234"])
def test_normalization_is_idempotent(text):
    once = normalize_plate(text)
    assert normalize_plate(once) == once


def test_prepare_plate_entry():
    p = prepare_entry("vehicle", " ka 01 ab 1234 ", "Watchlist Vehicle 01", "high")
    assert (p.entity_type, p.normalized, p.risk_level) == ("VEHICLE", "KA01AB1234", "HIGH")
    assert p.identifier == "ka 01 ab 1234"


def test_prepare_person_entry_is_not_plate_normalized():
    p = prepare_entry("PERSON", "  Case   Ref 17 ", "Person of interest", "LOW")
    assert p.normalized == "case ref 17"


@pytest.mark.parametrize("args", [
    ("SPACESHIP", "KA01AB1234", "n", "HIGH"),            # bad entity type
    ("VEHICLE", "KA01AB1234", "n", "SEVERE"),            # bad risk level
    ("VEHICLE", "A1", "n", "HIGH"),                      # too short for a plate
    ("VEHICLE", "KA01AB1234" * 3, "n", "HIGH"),          # far too long
    ("VEHICLE", "!!!!!!!", "n", "HIGH"),                 # no letters or digits
    ("VEHICLE", "KA01AB1234", "   ", "HIGH"),            # empty name
    ("VEHICLE", "", "n", "HIGH"),                        # empty identifier
])
def test_invalid_entries_are_rejected(args):
    with pytest.raises(InvalidEntry):
        prepare_entry(*args)


def test_overlong_free_text_is_rejected_and_control_characters_are_removed():
    with pytest.raises(InvalidEntry):
        prepare_entry("VEHICLE", "KA01AB1234", "x" * 201, "LOW")
    p = prepare_entry("VEHICLE", "KA01AB1234", "Name\x00with\x1fcontrol", "LOW")
    assert "\x00" not in p.name and "\x1f" not in p.name


def test_update_fields_are_whitelisted():
    assert validate_update_fields({"name": " New ", "risk_level": "critical", "description": None}) == \
        {"name": "New", "risk_level": "CRITICAL"}
    with pytest.raises(InvalidEntry):
        validate_update_fields({"normalized_identifier": "X"})
    with pytest.raises(InvalidEntry):
        validate_update_fields({"risk_level": "nope"})
