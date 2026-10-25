import json
import os
import sys
import uuid
import psycopg

db_url = os.environ.get("TEST_DATABASE_URL", "postgres://border_api:border_api_secret@localhost:5432/borderai_test")

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        evt_id = str(uuid.uuid4())
        alert_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO cameras (camera_id, name, location, location_label, enabled)
            VALUES ('E2E-CAM-01', 'E2E Camera', 'Border Line A', 'Border Line A', true)
            ON CONFLICT (camera_id) DO NOTHING;
        """)
        meta = json.dumps({"plate": "KA01AB9999", "explanation": {"factors": [{"name": "speed", "points": 25}]}})
        cur.execute("""
            INSERT INTO events (event_id, camera_id, track_id, event_type, severity, threat_score, timestamp, metadata)
            VALUES (%s, 'E2E-CAM-01', 555, 'ANPR_WATCHLIST_HIT', 'HIGH', 78, now(), %s::jsonb);
        """, (evt_id, meta))
        cur.execute("""
            INSERT INTO alerts (alert_id, event_id, camera_id, priority, threat_score, status, created_at)
            VALUES (%s, %s, 'E2E-CAM-01', 'HIGH', 78, 'NEW', now());
        """, (alert_id, evt_id))
        conn.commit()
        print(f"EVENT_ID:{evt_id}")
