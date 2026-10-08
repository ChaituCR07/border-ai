from collections import deque
from datetime import datetime, timezone

import numpy as np

from app.analytics.rules_config import CameraRules
from app.pipeline.types import FrameResult
from app.pipeline.visualizer import (FlashState, draw_event_feed, draw_lines, draw_tracks,
                                     draw_zones, put_text)


def mmss(seconds: float) -> str:
    return f"{int(seconds // 60):02d}:{seconds % 60:04.1f}"


class FrameRenderer:
    """Composes the final annotated frame for ONE camera. Used from that camera's output thread."""

    def __init__(self, camera_id: str, rules: CameraRules):
        self.camera_id = camera_id
        self.rules = rules
        self.flash = FlashState()
        self.feed = deque(maxlen=50)

    def render(self, res: FrameResult, out_fps: float) -> np.ndarray:
        image = res.frame.image                   # owned by this pipeline; drawn on in place
        ts = res.ft.timestamp
        offline = res.video_s is not None
        clock = (mmss(res.video_s) if offline
                 else datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M:%S"))

        self.flash.trigger(res.events, ts)
        for e in res.events:
            parts = [clock, e.type, e.rule_name, e.direction or "", f"{e.object_class} #{e.track_id}"]
            self.feed.append(" ".join(p for p in parts if p))

        draw_zones(image, self.rules, res.rule_stats["zone_occupancy"], self.flash, ts)
        draw_lines(image, self.rules, res.rule_stats["line_counts"], self.flash, ts)
        draw_tracks(image, res.ft.tracks, res.store)
        put_text(image, f"{self.camera_id}  {clock}{'' if offline else ' UTC'}  "
                        f"{out_fps:.1f} FPS  tracks {res.n_active}", (10, 25))
        draw_event_feed(image, self.feed)
        return image
