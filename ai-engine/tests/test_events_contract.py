from test_watchlist_service import make, plate_event, push


def test_watchlist_event_json_matches_the_plan_example():
    """Plan, Day 13: {event_id, camera, type: WATCHLIST_MATCH, track_id, plate, score, timestamp}."""
    svc, _, out = make()
    push(svc, plate_event(track=42, cam="CAM_03", conf=0.91))
    d = out[0].to_dict()
    for key in ("event_id", "type", "track_id", "plate", "score", "timestamp"):
        assert key in d
    assert d["type"] == "WATCHLIST_MATCH" and d["track_id"] == 42 and d["score"] == 91
    assert d["camera_id"] == "CAM_03"                          # Day 13's serializer can alias this to "camera"
    assert isinstance(d["score"], int) and 0 <= d["score"] <= 100
