from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
import subprocess
from typing import Any, Dict, Optional


def get_git_info() -> Dict[str, Any]:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        diff = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        return {"commit": commit, "dirty": len(diff) > 0}
    except Exception:
        return {"commit": "unknown", "dirty": False}


@dataclass
class RunManifest:
    run_id: str
    task: str  # "detection" or "tracking"
    dataset: Dict[str, Any]
    model: Dict[str, Any]
    inference: Dict[str, Any]
    deployed_thresholds: Dict[str, float]
    hardware: Dict[str, Any]
    git_commit: str = ""
    dirty: bool = False
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_s: float = 0.0
    seed: int = 42

    def __post_init__(self):
        if not self.git_commit:
            git_info = get_git_info()
            self.git_commit = git_info["commit"]
            self.dirty = git_info["dirty"]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def write_json(self, out_dir: str) -> str:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "manifest.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path
