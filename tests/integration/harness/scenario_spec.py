"""
Scenario Specification Schema & Validator (Task 5.1).
Validates YAML scenario configuration for deterministic acceptance testing.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class SpecValidationError(ValueError):
    """Raised when a scenario YAML specification fails validation."""
    pass


@dataclass
class CameraSpec:
    id: str
    clip: str
    config: Optional[str] = None


@dataclass
class EventExpect:
    type: str
    camera: Optional[str] = None
    plate: Optional[str] = None
    within_s: Tuple[float, float] = (0.0, 1e9)


@dataclass
class AlertExpect:
    priority: str
    score: int
    count: int = 1
    plate: Optional[str] = None
    factors: List[str] = field(default_factory=list)
    within_s: Tuple[float, float] = (0.0, 1e9)


@dataclass
class ForbiddenRule:
    type: Optional[str] = None
    plate_not: Optional[str] = None
    alert_priority_at_least: Optional[str] = None


@dataclass
class ScenarioSpec:
    id: str
    mode: str = "file_offline"
    clock: Dict[str, Any] = field(default_factory=dict)
    cameras: List[CameraSpec] = field(default_factory=list)
    setup: Dict[str, Any] = field(default_factory=dict)
    expect_events: List[EventExpect] = field(default_factory=list)
    expect_alerts: List[AlertExpect] = field(default_factory=list)
    forbidden: List[ForbiddenRule] = field(default_factory=list)
    budgets: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioSpec":
        allowed_top_keys = {
            "id", "name", "mode", "clock", "cameras", "setup",
            "expect", "forbidden", "websocket", "email", "dashboard",
            "reconcile", "budgets",
        }
        for k in data:
            if k not in allowed_top_keys:
                raise SpecValidationError(f"Unknown key in scenario spec: '{k}'")

        if not data.get("id"):
            raise SpecValidationError("Scenario specification missing required 'id'")

        mode = data.get("mode", "file_offline")
        if mode not in ("file_offline", "file_paced", "rtsp_live"):
            raise SpecValidationError(f"Invalid replay mode: '{mode}'")

        cameras = []
        for cam in data.get("cameras", []):
            if "id" not in cam or "clip" not in cam:
                raise SpecValidationError("Each camera entry must have 'id' and 'clip'")
            cameras.append(CameraSpec(id=cam["id"], clip=cam["clip"], config=cam.get("config")))

        expect_data = data.get("expect", {})
        expect_events = []
        for ev in expect_data.get("events", []):
            win = ev.get("within_s", [0.0, 1e9])
            if len(win) != 2 or win[0] > win[1]:
                raise SpecValidationError(f"Invalid within_s window {win}: min must be <= max")
            expect_events.append(
                EventExpect(
                    type=ev["type"],
                    camera=ev.get("camera"),
                    plate=ev.get("plate"),
                    within_s=(float(win[0]), float(win[1])),
                )
            )

        expect_alerts = []
        for al in expect_data.get("alerts", []):
            win = al.get("within_s", [0.0, 1e9])
            if len(win) != 2 or win[0] > win[1]:
                raise SpecValidationError(f"Invalid within_s window {win}: min must be <= max")
            expect_alerts.append(
                AlertExpect(
                    priority=al["priority"],
                    score=int(al["score"]),
                    count=int(al.get("count", 1)),
                    plate=al.get("plate"),
                    factors=al.get("factors", []),
                    within_s=(float(win[0]), float(win[1])),
                )
            )

        forbidden = []
        for fb in data.get("forbidden", expect_data.get("forbidden", [])):
            forbidden.append(
                ForbiddenRule(
                    type=fb.get("type"),
                    plate_not=fb.get("plate_not"),
                    alert_priority_at_least=fb.get("alert_priority_at_least"),
                )
            )

        return cls(
            id=data["id"],
            mode=mode,
            clock=data.get("clock", {}),
            cameras=cameras,
            setup=data.get("setup", {}),
            expect_events=expect_events,
            expect_alerts=expect_alerts,
            forbidden=forbidden,
            budgets=data.get("budgets", {}),
            raw=data,
        )
