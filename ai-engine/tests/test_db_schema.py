import pytest

pytestmark = pytest.mark.db


@pytest.fixture
def conn(pg_dsn):
    import psycopg
    with psycopg.connect(pg_dsn, autocommit=True) as c:
        c.execute("TRUNCATE alert_history, alerts, vehicles, detections, events, cameras RESTART IDENTITY CASCADE")
        c.execute("INSERT INTO cameras (camera_id, name) VALUES ('CAM_1', 'Gate')")
        yield c


def insert_event(conn, event_id="E1", camera="CAM_1", etype="ZONE_VIOLATION", severity="HIGH", score=None, ts="2026-10-12 02:13:00+00"):
    conn.execute("INSERT INTO events (event_id, camera_id, event_type, track_id, severity, threat_score, timestamp) "
                 "VALUES (%s, %s, %s, 1, %s, %s, %s)", (event_id, camera, etype, severity, score, ts))


def test_the_migration_can_be_applied_twice(pg_dsn):
    from app import config
    from app.db.migrate import apply_migrations
    apply_migrations(pg_dsn, config.BASE_DIR / "database" / "migrations")
    apply_migrations(pg_dsn, config.BASE_DIR / "database" / "migrations")


def test_the_expected_tables_views_and_function_exist(conn):
    tables = {r[0] for r in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")}
    assert {"cameras", "events", "alerts", "alert_history", "vehicles", "detections", "watchlist"} <= tables
    assert {"vehicle_plates", "alert_counts"} <= tables                                              # views are listed here too
    assert conn.execute("SELECT event_ref(129)").fetchone()[0] == "EVT_000129"


def test_the_indexes_the_dashboard_needs_exist(conn):
    names = {r[0] for r in conn.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")}
    assert {"idx_events_time", "idx_events_camera_time", "idx_events_type_time", "idx_events_severity",
            "idx_events_plate", "idx_alerts_status_time", "idx_alerts_priority_time", "idx_vehicles_plate_time",
            "idx_detections_camera_time"} <= names


def test_events_need_a_known_camera(conn):
    import psycopg
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        insert_event(conn, camera="NOPE")


@pytest.mark.parametrize("kwargs", [
    {"severity": "SPICY"}, {"score": 101}, {"score": -1}, {"etype": "not valid"}, {"event_id": ""}, {"event_id": "x" * 65},
])
def test_the_event_table_refuses_invalid_values(conn, kwargs):
    import psycopg
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_event(conn, **kwargs)


def test_the_event_id_is_unique(conn):
    import psycopg
    insert_event(conn)
    with pytest.raises(psycopg.errors.UniqueViolation):
        insert_event(conn)


def test_cameras_refuse_credentials_in_the_url(conn):
    import psycopg
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO cameras (camera_id, name, rtsp_url) VALUES ('CAM_2', 'x', 'rtsp://admin:pw@10.0.0.1/s')")
    conn.execute("INSERT INTO cameras (camera_id, name, rtsp_url) VALUES ('CAM_3', 'x', 'rtsp://10.0.0.1/s')")


def test_an_alert_past_new_needs_a_person(conn):
    import psycopg
    insert_event(conn, severity="HIGH", score=60, etype="THREAT_ALERT")
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO alerts (alert_id, event_id, camera_id, priority, threat_score, status, created_at) "
                     "VALUES ('A1', 'E1', 'CAM_1', 'HIGH', 60, 'RESOLVED', now())")
    conn.execute("INSERT INTO alerts (alert_id, event_id, camera_id, priority, threat_score, status, acknowledged_by, created_at) "
                 "VALUES ('A1', 'E1', 'CAM_1', 'HIGH', 60, 'RESOLVED', 'officer', now())")


def test_deleting_an_event_removes_what_depends_on_it(conn):
    insert_event(conn, etype="THREAT_ALERT", score=60)
    conn.execute("INSERT INTO alerts (alert_id, event_id, camera_id, priority, threat_score, created_at) "
                 "VALUES ('A1', 'E1', 'CAM_1', 'HIGH', 60, now())")
    conn.execute("INSERT INTO alert_history (alert_id, to_status, actor) VALUES ('A1', 'NEW', 'system')")
    conn.execute("INSERT INTO vehicles (event_id, camera_id, track_id, plate_number, confidence, timestamp) "
                 "VALUES ('E1', 'CAM_1', 1, 'KA01AB1234', 0.9, now())")
    conn.execute("DELETE FROM events WHERE event_id = 'E1'")
    for table in ("alerts", "alert_history", "vehicles"):
        assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0


def test_the_views_aggregate_correctly(conn):
    for i, plate in enumerate(["KA01AB1234", "KA01AB1234", "MH12DE1433"]):
        insert_event(conn, event_id=f"P{i}", etype="PLATE_RECOGNIZED", severity=None)
        conn.execute("INSERT INTO vehicles (event_id, camera_id, track_id, plate_number, confidence, timestamp) "
                     "VALUES (%s, 'CAM_1', 1, %s, %s, now())", (f"P{i}", plate, 0.5 + i / 10))
    row = conn.execute("SELECT sightings, cameras, best_confidence FROM vehicle_plates WHERE plate_number = 'KA01AB1234'").fetchone()
    assert row[0] == 2 and row[1] == 1 and row[2] == pytest.approx(0.6, abs=1e-6)


def test_identity_gaps_from_duplicates_do_not_break_the_reference(conn):
    insert_event(conn, event_id="E1")
    conn.execute("INSERT INTO events (event_id, camera_id, event_type, track_id, timestamp) "
                 "VALUES ('E1', 'CAM_1', 'ZONE_VIOLATION', 1, now()) ON CONFLICT DO NOTHING")      # a duplicate consumes a number
    insert_event(conn, event_id="E2")
    refs = [r[0] for r in conn.execute("SELECT event_ref(event_seq) FROM events ORDER BY event_seq")]
    assert refs[0] == "EVT_000001" and refs[1] > refs[0] and len(set(refs)) == 2                     # gaps are allowed, duplicates are not
