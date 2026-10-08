import logging
from pathlib import Path
from typing import Dict, List

from app.analytics.lines import LineEngine
from app.analytics.rules_config import CameraRules, load_camera_rules
from app.analytics.zones import ZoneEngine
from app.schemas.events import Event
from app.schemas.tracking import FrameTracks
from app.tracking.track_store import TrackStore, TrackUpdate

log = logging.getLogger("rules")


class _CameraEngines:
    def __init__(self, rules: CameraRules):
        self.rules = rules
        self.zones = ZoneEngine(rules.zones, rules.min_track_hits)
        self.lines = LineEngine(rules.lines, rules.min_track_hits)


class RuleEngine:
    """Runs the zone and line engines for every camera. Call from the single
    pipeline thread, after the tracker, once per frame per camera."""

    def __init__(self, rules_dir: Path):
        self.rules_dir = Path(rules_dir)
        self._cams: Dict[str, _CameraEngines] = {}

    def _get(self, camera_id: str) -> _CameraEngines:
        if camera_id not in self._cams:
            path = self.rules_dir / f"{camera_id}.json"
            if path.exists():
                rules = load_camera_rules(path)          # raises ValueError if invalid
            else:
                log.warning("No rules file for %s (%s); no events will be produced",
                            camera_id, path)
                rules = CameraRules(camera_id=camera_id)
            self._cams[camera_id] = _CameraEngines(rules)
        return self._cams[camera_id]

    def rules_for(self, camera_id: str) -> CameraRules:
        return self._get(camera_id).rules

    def update(self, ft: FrameTracks, upd: TrackUpdate, store: TrackStore) -> List[Event]:
        cam = self._get(ft.camera_id)
        events = cam.zones.update(ft, store, upd)
        events.extend(cam.lines.update(ft, store, upd))
        return events

    def flush(self, camera_id: str, ft: FrameTracks, store: TrackStore) -> List[Event]:
        return self._get(camera_id).zones.flush(ft, store)

    def stats(self, camera_id: str) -> dict:
        cam = self._get(camera_id)
        return {
            "zone_occupancy": dict(cam.zones.occupancy),
            "line_counts": {k: dict(v) for k, v in cam.lines.counts.items()},
        }
