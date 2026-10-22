import threading
import time

import pytest

from app.events.streams import StreamUnavailable

IDLE_MS = 60


def add(client, stream, n=1, start=0):
    return [client.xadd(stream, {"n": str(start + i)}) for i in range(n)]


def test_ids_increase_and_length_counts(stream_client, stream_name):
    ids = add(stream_client, stream_name, 5)
    key = lambda s: tuple(int(x) for x in s.split("-"))
    assert [key(i) for i in ids] == sorted(key(i) for i in ids) and len(set(ids)) == 5
    assert stream_client.length(stream_name) == 5


def test_exact_trimming_keeps_the_newest_entries(stream_client, stream_name):
    for i in range(20):
        stream_client.xadd(stream_name, {"n": str(i)}, maxlen=5, approximate=False)
    assert stream_client.length(stream_name) == 5
    assert [f["n"] for _, f in stream_client.range(stream_name, 10)] == ["15", "16", "17", "18", "19"]


def test_xadd_many_keeps_order(stream_client, stream_name):
    stream_client.xadd_many(stream_name, [{"n": str(i)} for i in range(10)])
    assert [f["n"] for _, f in stream_client.range(stream_name, 10)] == [str(i) for i in range(10)]


def test_group_creation_is_idempotent(stream_client, stream_name):
    stream_client.group_create(stream_name, "g")
    stream_client.group_create(stream_name, "g")
    assert [g["name"] for g in stream_client.groups_info(stream_name)] == ["g"]


def test_a_group_reads_each_message_once(stream_client, stream_name):
    stream_client.group_create(stream_name, "g")
    add(stream_client, stream_name, 5)
    first = stream_client.read_group(stream_name, "g", "c1", count=10)
    assert [f["n"] for _, f in first] == ["0", "1", "2", "3", "4"]
    assert stream_client.read_group(stream_name, "g", "c1", count=10) == []


def test_consumers_in_a_group_share_the_messages_and_groups_each_get_all(stream_client, stream_name):
    stream_client.group_create(stream_name, "g1")
    stream_client.group_create(stream_name, "g2")
    add(stream_client, stream_name, 6)
    a = stream_client.read_group(stream_name, "g1", "c1", count=3)
    b = stream_client.read_group(stream_name, "g1", "c2", count=3)
    assert {f["n"] for _, f in a} | {f["n"] for _, f in b} == {"0", "1", "2", "3", "4", "5"}
    assert not {f["n"] for _, f in a} & {f["n"] for _, f in b}
    assert len(stream_client.read_group(stream_name, "g2", "c1", count=10)) == 6


def test_a_group_started_at_zero_sees_older_messages(stream_client, stream_name):
    add(stream_client, stream_name, 3)
    stream_client.group_create(stream_name, "g", "0")
    assert len(stream_client.read_group(stream_name, "g", "c", count=10)) == 3


def test_ack_clears_the_pending_list(stream_client, stream_name):
    stream_client.group_create(stream_name, "g")
    add(stream_client, stream_name, 3)
    msgs = stream_client.read_group(stream_name, "g", "c", count=10)
    assert stream_client.pending_count(stream_name, "g") == 3
    stream_client.ack(stream_name, "g", [mid for mid, _ in msgs[:2]])
    assert stream_client.pending_count(stream_name, "g") == 1
    stream_client.ack(stream_name, "g", [])                                # nothing to do, must not fail


def test_unacknowledged_messages_can_be_claimed_after_the_idle_time(stream_client, stream_name):
    stream_client.group_create(stream_name, "g")
    add(stream_client, stream_name, 2)
    stream_client.read_group(stream_name, "g", "crashed", count=10)
    assert stream_client.claim_stale(stream_name, "g", "rescuer", min_idle_ms=IDLE_MS) == []      # too fresh
    time.sleep(IDLE_MS / 1000 + 0.05)
    claimed = stream_client.claim_stale(stream_name, "g", "rescuer", min_idle_ms=IDLE_MS)
    assert [f["n"] for _, f, _ in claimed] == ["0", "1"] and all(times == 2 for _, _, times in claimed)
    assert stream_client.claim_stale(stream_name, "g", "rescuer", min_idle_ms=IDLE_MS) == []      # idle restarted
    assert stream_client.pending_count(stream_name, "g") == 2


def test_delivery_counts_keep_growing_with_each_claim(stream_client, stream_name):
    stream_client.group_create(stream_name, "g")
    add(stream_client, stream_name, 1)
    stream_client.read_group(stream_name, "g", "c1", count=1)
    counts = []
    for consumer in ("c2", "c3"):
        time.sleep(IDLE_MS / 1000 + 0.05)
        counts.append(stream_client.claim_stale(stream_name, "g", consumer, min_idle_ms=IDLE_MS)[0][2])
    assert counts == [2, 3]


def test_a_blocking_read_returns_empty_quickly_and_wakes_up_for_new_messages(stream_client, stream_name):
    stream_client.group_create(stream_name, "g")
    t0 = time.time()
    assert stream_client.read_group(stream_name, "g", "c", count=5, block_ms=80) == []
    assert time.time() - t0 < 2.0
    threading.Timer(0.05, lambda: stream_client.xadd(stream_name, {"n": "late"})).start()
    got = stream_client.read_group(stream_name, "g", "c", count=5, block_ms=2000)
    assert [f["n"] for _, f in got] == ["late"]


def test_range_returns_the_newest_entries_oldest_first(stream_client, stream_name):
    add(stream_client, stream_name, 6)
    assert [f["n"] for _, f in stream_client.range(stream_name, 3)] == ["3", "4", "5"]


def test_group_info_reports_pending_and_lag(stream_client, stream_name):
    stream_client.group_create(stream_name, "g")
    add(stream_client, stream_name, 4)
    stream_client.read_group(stream_name, "g", "c", count=3)
    info = stream_client.groups_info(stream_name)[0]
    assert info["name"] == "g" and info["pending"] == 3


def test_delete_removes_the_stream(stream_client, stream_name):
    add(stream_client, stream_name, 2)
    stream_client.delete(stream_name)
    assert stream_client.length(stream_name) == 0


def test_the_in_memory_client_can_simulate_outages():
    from app.events.streams import InMemoryStreamClient
    c = InMemoryStreamClient()
    c.down = True
    with pytest.raises(StreamUnavailable):
        c.xadd("s", {"a": "1"})
    c.down = False
    c.fail_after_adds = 1
    c.xadd("s", {"a": "1"})
    with pytest.raises(StreamUnavailable):
        c.xadd("s", {"a": "2"})
    c.xadd("s", {"a": "3"})                                        # the failure was one-shot
    assert c.length("s") == 2
