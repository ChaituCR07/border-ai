import json
import time
from pathlib import Path
from typing import Iterator, Optional

from app.events.envelope import envelope_from_dict
from app.events.publisher import Transport


def read_journal(path) -> Iterator[dict]:
    with open(Path(path), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def publish_journal(path, transport: Transport, run_id: str = "", batch_size: int = 100,
                    rate_per_s: Optional[float] = None) -> int:
    """Send every event of a journal file through the transport. Returns the number sent.
    Raises TransportUnavailable if the bus is still down."""
    batch, total = [], 0
    for d in read_journal(path):
        batch.append(envelope_from_dict(d, run_id))
        if len(batch) >= batch_size:
            transport.send(batch)
            total += len(batch)
            batch = []
            if rate_per_s:
                time.sleep(batch_size / rate_per_s)
    if batch:
        transport.send(batch)
        total += len(batch)
    return total
