from test_watchlist_service import make, plate_event, push


def test_plan_test_3_vehicle_with_a_normal_plate_gives_no_watchlist_alert():
    svc, _, out = make()
    push(svc, plate_event("MH12XY4321", conf=0.93))
    assert [e for e in out if e.type == "WATCHLIST_MATCH"] == []


def test_plan_test_4_watchlisted_plate_gives_a_watchlist_alert():
    svc, _, out = make()
    push(svc, plate_event("KA01AB1234", conf=0.93))
    alerts = [e for e in out if e.type == "WATCHLIST_MATCH"]
    assert len(alerts) == 1 and alerts[0].details["status"] == "alert"


def test_plan_scenario_2_watchlisted_vehicle_flow():
    """vehicle detected -> plate -> OCR -> KA01AB1234 -> watchlist lookup -> MATCH -> flagged for scoring."""
    svc, _, out = make()
    push(svc, plate_event("KA01AB1234", conf=0.94, track=27))
    event = out[0]
    assert event.details["plate"] == "KA01AB1234" and event.track_id == 27
    assert event.details["risk_level"] == "HIGH"              # what Day 12's threat score will use
    assert svc.flags_snapshot("CAM") == {27: "HIGH"}          # what the overlay shows
