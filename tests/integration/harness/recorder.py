"""
Scenario Recorder (Task 5.2).
Subscribes to Redis, DB, WebSocket and logs to build a single chronological timeline.
"""

from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List, Optional


class TimelineRecorder:
    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.timeline_path = os.path.join(run_dir, "timeline.jsonl")
        self.entries: List[Dict[str, Any]] = []
        os.makedirs(run_dir, exist_ok=True)

    def record(self, src: str, kind: str, data: Dict[str, Any], t_wall: Optional[str] = None) -> None:
        wall_ts = t_wall or datetime.now(timezone.utc).isoformat(timespec="microseconds")
        entry = {
            "t_wall": wall_ts,
            "src": src,
            "kind": kind,
            "data": data,
        }
        self.entries.append(entry)
        with open(self.timeline_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_events(self) -> List[Dict[str, Any]]:
        hits = []
        for e in self.entries:
            if e.get("kind") == "event":
                hits.append(e["data"])
        return hits

    def get_alerts(self) -> List[Dict[str, Any]]:
        hits = []
        for e in self.entries:
            if e.get("kind") == "alert":
                hits.append(e["data"])
        return hits
