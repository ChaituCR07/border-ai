from app.anpr.plate_format import PlateFormats, clean_text, correct_indian


def test_clean_text():
    assert clean_text(" ka-01 ab 1234.") == "KA01AB1234"


def test_valid_plate_is_unchanged():
    c = correct_indian("KA01AB1234")
    assert (c.text, c.subs, c.state_ok) == ("KA01AB1234", 0, True)


def test_letter_in_a_digit_position_is_corrected():
    c = correct_indian("KAO1AB1234")
    assert c.text == "KA01AB1234" and c.subs == 1


def test_digit_in_a_letter_position_is_corrected():
    assert correct_indian("KA01A81234").text == "KA01AB1234"
    assert correct_indian("KA0IAB1234").text == "KA01AB1234"


def test_hsrp_strip_prefix_is_ignored():
    assert correct_indian(clean_text("IND KA01AB1234")).text == "KA01AB1234"


def test_single_digit_district_and_three_letter_series():
    assert correct_indian("MH2CDE5678").text == "MH2CDE5678"


def test_strict_loose_and_invalid_levels():
    f = PlateFormats(["indian"])
    assert f.check("kA 01 ab 1234").level == "strict"
    assert f.check("ZZ01AB1234").level == "loose"          # right shape, unknown state code
    assert f.check("HELLO").level == "invalid"


def test_generic_format_fallback():
    f = PlateFormats(["generic"])
    assert f.check("ABC1234").level == "loose"
    assert f.check("A").level == "invalid"
