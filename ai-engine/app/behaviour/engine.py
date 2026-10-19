import logging
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.behaviour.authorized import AuthorizedPlates
from app.behaviour.conditions import Env, evaluate_all
from app.behaviour.context import TrackContext
from app.behaviour.rules_config import BehaviourConfig, Rule, load_behaviour_config
from app.behaviour.timeutil import get_zone
from app.schemas.events import Event

log = logging.getLogger("behaviour")

CONTEXT_TTL_S = 600.0
PRUNE_EVERY_S = 60.0


class BehaviourEngine:
    def __init__(self, cfg: BehaviourConfig, authorized: Optional[AuthorizedPlates] = None,
                 rules_path: Optional[Path] = None, reload_check_s: float = 5.0):
        self.authorized = authorized
        self.stats: Counter = Counter()
        self.fired: Counter = Counter()

        self._lock = threading.Lock()
        self._inbox: Dict[str, List[Event]] = {}
        self._contexts: Dict[Tuple[str, int], TrackContext] = {}
        self._active: Dict[Tuple[str, int], Dict[str, Dict[tuple, float]]] = {}     # track -> rule -> binding -> last true
        self._last_fire: Dict[Tuple[str, int], Dict[str, float]] = {}
        self._broken: set = set()
        self._last_prune = 0.0

        self._rules_path = Path(rules_path) if rules_path else None
        self._reload_check_s = reload_check_s
        self._next_check = 0.0
        self._mtime = self._rules_path.stat().st_mtime if self._rules_path and self._rules_path.exists() else 0.0
        self._set_config(cfg)

    # ------------------------------------------------------------------ configuration
    def _set_config(self, cfg: BehaviourConfig) -> None:
        self.cfg = cfg
        self._rules = [r for r in cfg.rules if r.enabled]

    def rules_for(self, camera_id: str) -> List[Rule]:
        return [r for r in self._rules if r.cameras is None or camera_id in r.cameras]

    def _tz(self, camera_id: str):
        return get_zone(self.cfg.camera_timezones.get(camera_id, self.cfg.timezone))

    def reload(self) -> bool:
        """Re-read the rules file. A valid file replaces the rules; an invalid one is ignored."""
        if self._rules_path is None:
            return False
        try:
            cfg = load_behaviour_config(self._rules_path)
        except Exception as e:                                  # noqa: BLE001
            self.stats["reload_errors"] += 1
            log.error("Rules file %s is invalid; keeping the previous rules: %s", self._rules_path, e)
            return False
        self._set_config(cfg)
        self._broken.clear()
        self.stats["reloads"] += 1
        log.info("Rules reloaded: %d enabled rule(s)", len(self._rules))
        return True

    def maybe_reload(self) -> None:
        if self._rules_path is None or time.time() < self._next_check:
            return
        self._next_check = time.time() + self._reload_check_s
        try:
            mtime = self._rules_path.stat().st_mtime
        except OSError:
            return
        if mtime != self._mtime:
            self._mtime = mtime
            self.reload()

    # ------------------------------------------------------------------ input
    def observe(self, camera_id: str, events: List[Event]) -> None:
        """Thread-safe: queue observation events for the next update(). Behaviour events are ignored."""
        events = [e for e in events if e.rule_kind != "behaviour"]
        if events:
            with self._lock:
                self._inbox.setdefault(camera_id, []).extend(events)

    def _ctx(self, camera_id: str, track_id: int) -> TrackContext:
        key = (camera_id, track_id)
        ctx = self._contexts.get(key)
        if ctx is None:
            ctx = self._contexts[key] = TrackContext(camera_id, track_id)
        return ctx

    # ------------------------------------------------------------------ evaluation
    def update(self, ft, upd=None) -> List[Event]:
        """Evaluate the rules for the tracks in this frame. `ft` is a FrameTracks, `upd` an optional
        TrackUpdate (its `removed` tracks are forgotten)."""
        self.maybe_reload()
        cid, now = ft.camera_id, ft.timestamp
        with self._lock:
            pending = self._inbox.pop(cid, [])
        for e in pending:
            self._ctx(cid, e.track_id).ingest(e)

        out: List[Event] = []
        rules = self.rules_for(cid)
        tz = self._tz(cid)
        for o in ft.tracks:
            ctx = self._ctx(cid, o.track_id)
            ctx.touch(o.label, now)
            tkey = (cid, o.track_id)
            for rule in rules:
                if rule.rule_id in self._broken:
                    continue
                active_map = self._active.get(tkey, {}).get(rule.rule_id, {})
                active_set = set(active_map.keys())
                env = Env(now, tz, getattr(o, "age_s", 0.0), self.authorized, active_bindings=active_set)
                while True:
                    try:
                        res = evaluate_all(rule.conditions, ctx, env)
                    except Exception:                                # noqa: BLE001
                        log.exception("Rule %s failed on %s #%s; disabling it until the next reload",
                                      rule.rule_id, cid, o.track_id)
                        self._broken.add(rule.rule_id)
                        self.stats["errors"] += 1
                        break
                    self.stats["evaluations"] += 1
                    emitted = self._consider(rule, ctx, res, o, ft)
                    out.extend(emitted)
                    if not emitted:
                        break
                    bkey = tuple(sorted(res.bindings.items()))
                    if bkey and bkey not in active_set:
                        active_set.add(bkey)
                        env.active_bindings = active_set
                    else:
                        break

        if upd is not None:
            for t in upd.removed:
                self._drop(cid, t.track_id)
        if now - self._last_prune >= PRUNE_EVERY_S:
            self._prune(now)
        return out

    def _consider(self, rule: Rule, ctx: TrackContext, res, obj, ft) -> List[Event]:
        tkey = (ctx.camera_id, ctx.track_id)
        now = ft.timestamp
        active = self._active.setdefault(tkey, {}).setdefault(rule.rule_id, {})
        bkey = tuple(sorted(res.bindings.items())) if res.ok else None

        for k in [k for k, last in active.items() if k != bkey and now - last >= rule.rearm_s]:
            del active[k]                                         # re-armed: may fire again
        if not res.ok:
            return []

        was_active = bkey in active
        active[bkey] = now
        if was_active:
            return []                                             # same episode: do not repeat

        last_fires = self._last_fire.setdefault(tkey, {})
        last = last_fires.get(rule.rule_id)
        if rule.cooldown_s > 0 and last is not None and now - last < rule.cooldown_s:
            self.stats["suppressed_cooldown"] += 1
            return []
        last_fires[rule.rule_id] = now
        self.fired[rule.rule_id] += 1
        return [self._build_event(rule, ctx, res, obj, ft)]

    def _build_event(self, rule: Rule, ctx: TrackContext, res, obj, ft) -> Event:
        details = {
            "severity": rule.severity, "points": rule.points, "rule_id": rule.rule_id,
            "description": rule.description, "reasons": res.reasons,
            "bindings": {k: v for k, v in res.bindings.items()},
            "track_age_s": round(getattr(obj, "age_s", 0.0), 1),
        }
        if ctx.plate:
            details["plate"] = ctx.plate
        if ctx.watchlist:
            details["watchlist"] = {"status": ctx.watchlist["status"], "risk_level": ctx.watchlist["risk_level"]}
        return Event(
            type=rule.event_type, camera_id=ctx.camera_id, timestamp=ft.timestamp, frame_id=ft.frame_id,
            track_id=ctx.track_id, object_class=ctx.object_class, confidence=1.0, bbox=tuple(obj.bbox),
            rule_id=rule.rule_id, rule_name=rule.name, rule_kind="behaviour", rule_type="rule",
            details=details)

    # ------------------------------------------------------------------ cleanup and status
    def _drop(self, camera_id: str, track_id: int) -> None:
        key = (camera_id, track_id)
        self._contexts.pop(key, None)
        self._active.pop(key, None)
        self._last_fire.pop(key, None)

    def _prune(self, now: float) -> None:
        self._last_prune = now
        stale = [k for k, c in self._contexts.items() if now - c.last_touch > CONTEXT_TTL_S]
        for cid, tid in stale:
            self._drop(cid, tid)
        self.stats["pruned_contexts"] += len(stale)

    def status(self) -> dict:
        return {"rules": len(self._rules), "contexts": len(self._contexts),
                "fired": dict(self.fired), **dict(self.stats)}
