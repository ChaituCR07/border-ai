from app.events.journal import publish_journal, read_journal
from app.events.publisher import StreamTransport
from app.events.stats import collect_stats, format_stats
from app.events.streams import InMemoryStreamClient
from events_helpers import ev, make_events_cfg


def test_journal_replay_publishes_every_line_and_stamps_the_run(tmp_path):
    import json
    cfg, client = make_events_cfg(), InMemoryStreamClient()
    path = tmp_path / "events.jsonl"
    events = [ev(i, "THREAT_ALERT" if i == 2 else "ZONE_VIOLATION", severity="HIGH") for i in range(5)]
    path.write_text("\n".join(json.dumps(e.to_dict()) for e in events) + "\n")
    assert len(list(read_journal(path))) == 5
    assert publish_journal(path, StreamTransport(client, cfg), run_id="RUN9", batch_size=2) == 5
    entries = client.range(cfg.stream, 100)
    assert [f["event_id"] for _, f in entries] == [e.event_id for e in events] and entries[0][1]["run_id"] == "RUN9"
    assert len(client.range(cfg.alerts_stream, 100)) == 1


def test_stats_report_length_groups_pending_and_lag():
    cfg, client = make_events_cfg(), InMemoryStreamClient()
    client.group_create(cfg.stream, "processor")
    for i in range(4):
        client.xadd(cfg.stream, {"n": str(i)})
    client.read_group(cfg.stream, "processor", "c1", count=3)
    stats = collect_stats(client, cfg)
    assert stats["events"]["length"] == 4
    group = stats["events"]["groups"][0]
    assert (group["name"], group["pending"], group["lag"]) == ("processor", 3, 1)
    assert "length 4" in format_stats(stats) and "lag 1" in format_stats(stats)
