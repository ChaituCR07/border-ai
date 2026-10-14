from dataclasses import dataclass, field, fields
from typing import List


@dataclass
class WatchlistConfig:
    enabled: bool = True
    backend: str = "postgres"
    require_db: bool = False
    seed_csv: str = ""
    entity_types: List[str] = field(default_factory=lambda: ["VEHICLE", "PLATE"])
    alert_min_confidence: float = 0.70
    min_score: int = 40
    near_max_distance: float = 1.0
    near_penalty: float = 0.2
    near_can_alert: bool = False
    cooldown_s: float = 60.0
    snapshot_refresh_s: float = 60.0
    queue_size: int = 100
    submit_timeout_s: float = 2.0
    max_candidates: int = 5000

    def __post_init__(self):
        if self.backend not in ("postgres", "memory"):
            raise ValueError("backend must be 'postgres' or 'memory'")
        if not 0.0 <= self.alert_min_confidence <= 1.0:
            raise ValueError("alert_min_confidence must be between 0 and 1")
        if not 0 <= self.min_score <= 100:
            raise ValueError("min_score must be between 0 and 100")
        if self.near_max_distance < 0 or self.near_penalty < 0:
            raise ValueError("near_max_distance and near_penalty must be >= 0")
        if self.cooldown_s < 0 or self.queue_size < 1 or self.max_candidates < 1:
            raise ValueError("cooldown_s must be >= 0; queue_size and max_candidates must be >= 1")
        if not self.entity_types:
            raise ValueError("entity_types must not be empty")

    @classmethod
    def from_config(cls, cfg: dict) -> "WatchlistConfig":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (cfg or {}).items() if k in known})
