"""
Scenario Evaluator (Task 5.3).
Matches recorded timeline observations against scenario expectations and budgets.
Generates informative failure reasons and candidate lists for rapid debugging.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple
from tests.integration.harness.scenario_spec import EventExpect, AlertExpect, ForbiddenRule, ScenarioSpec


def parse_iso(ts_str: str) -> datetime:
    """Parses standard ISO 8601 UTC timestamp."""
    clean = ts_str.replace("Z", "+00:00")
    return datetime.fromisoformat(clean)


def plate_key(plate_str: str) -> str:
    """Canonical plate key normalized for Indian & international layouts (ADR 0023)."""
    return re.sub(r"[^A-Z0-9]", "", (plate_str or "").upper())


class EvaluationResult:
    def __init__(self):
        self.passed = True
        self.errors: List[str] = []
        self.matched_events: List[Dict[str, Any]] = []
        self.matched_alerts: List[Dict[str, Any]] = []

    def add_error(self, err: str) -> None:
        self.passed = False
        self.errors.append(err)


class ScenarioEvaluator:
    def __init__(self, spec: ScenarioSpec, t0: datetime):
        self.spec = spec
        self.t0 = t0

    def scenario_t(self, item_ts: datetime) -> float:
        """Computes offset in seconds relative to scenario start."""
        return (item_ts - self.t0).total_seconds()

    def evaluate(self, events: List[Dict[str, Any]], alerts: List[Dict[str, Any]]) -> EvaluationResult:
        res = EvaluationResult()

        # 1. Evaluate expected events
        for exp in self.spec.expect_events:
            hits = []
            for ev in events:
                if ev.get("event_type") != exp.type and ev.get("type") != exp.type:
                    continue
                if exp.camera and ev.get("camera_id") != exp.camera:
                    continue
                if exp.plate:
                    ev_plate = ev.get("plate_number") or ev.get("plate") or ""
                    if plate_key(ev_plate) != plate_key(exp.plate):
                        continue

                ev_time_str = ev.get("timestamp") or ev.get("created_at")
                if ev_time_str:
                    try:
                        t = self.scenario_t(parse_iso(ev_time_str))
                        lo, hi = exp.within_s
                        if lo <= t <= hi:
                            hits.append(ev)
                    except Exception:
                        hits.append(ev)
                else:
                    hits.append(ev)

            if not hits:
                # Find near candidates
                near = [e for e in events if (e.get("event_type") == exp.type or e.get("type") == exp.type)]
                msg = f"Missing expected event {exp.type} (camera={exp.camera}, plate={exp.plate}, window={exp.within_s}). "
                if near:
                    msg += f"Found {len(near)} same-type events with cameras: {[n.get('camera_id') for n in near[:3]]}"
                else:
                    msg += "No events of this type were emitted."
                res.add_error(msg)
            else:
                res.matched_events.extend(hits)

        # 2. Evaluate expected alerts
        for al_exp in self.spec.expect_alerts:
            hits = []
            for al in alerts:
                if al.get("priority") != al_exp.priority:
                    continue
                if int(al.get("threat_score", 0)) != al_exp.score:
                    continue
                if al_exp.plate:
                    al_plate = al.get("plate") or (al.get("event", {}).get("plate") if isinstance(al.get("event"), dict) else "")
                    if plate_key(al_plate) != plate_key(al_exp.plate):
                        continue
                hits.append(al)

            if len(hits) != al_exp.count:
                res.add_error(
                    f"Alert count mismatch for priority={al_exp.priority}, score={al_exp.score}: expected {al_exp.count}, got {len(hits)}"
                )
            else:
                res.matched_alerts.extend(hits)

        # 3. Evaluate forbidden outcomes
        for fb in self.spec.forbidden:
            if fb.type:
                for ev in events:
                    ev_type = ev.get("event_type") or ev.get("type")
                    if ev_type == fb.type:
                        ev_plate = ev.get("plate_number") or ev.get("plate") or ""
                        if fb.plate_not and plate_key(ev_plate) != plate_key(fb.plate_not):
                            res.add_error(
                                f"Forbidden event emitted: {fb.type} for non-whitelisted plate '{ev_plate}'"
                            )

            if fb.alert_priority_at_least:
                prios = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
                threshold_idx = prios.index(fb.alert_priority_at_least) if fb.alert_priority_at_least in prios else 2
                for al in alerts:
                    al_prio = al.get("priority", "LOW")
                    if al_prio in prios and prios.index(al_prio) >= threshold_idx:
                        al_plate = al.get("plate") or (al.get("event", {}).get("plate") if isinstance(al.get("event"), dict) else "")
                        if fb.plate_not and plate_key(al_plate) != plate_key(fb.plate_not):
                            res.add_error(
                                f"Forbidden alert priority {al_prio} for plate '{al_plate}'"
                            )

        return res
