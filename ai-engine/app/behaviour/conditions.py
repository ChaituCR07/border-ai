from dataclasses import dataclass, field
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from app.behaviour.authorized import AuthorizedPlates
from app.behaviour.context import TrackContext
from app.behaviour.timeutil import get_zone, in_window, local_minutes_and_day, parse_hhmm
from app.watchlist.models import RISK_RANK


@dataclass
class Env:
    now: float
    tz: ZoneInfo
    age_s: float = 0.0
    authorized: Optional[AuthorizedPlates] = None
    active_bindings: Optional[set] = None


@dataclass
class CondResult:
    ok: bool
    bindings: Dict[str, object] = field(default_factory=dict)      # what the match was about (zone, crossing)
    reasons: List[str] = field(default_factory=list)               # human-readable evidence


FALSE = CondResult(False)


def _object(node, ctx, env) -> CondResult:
    ok = ctx.object_class in node["value"]
    return CondResult(ok, {}, [f"object is a {ctx.object_class}"] if ok else [])


def _zone(node, ctx, env) -> CondResult:
    zid, ztype = node.get("zone_id"), node.get("zone_type")
    matches = [z for z in ctx.zones.values()
               if (zid is None or z.zone_id == zid) and (ztype in (None, "any") or z.zone_type == ztype)]
    if not node["inside"]:
        return CondResult(not matches, {}, [] if matches else ["not inside the zone"])

    def find_best(candidates):
        best = None
        for z in candidates:
            dwell = env.now - z.entered_at
            if dwell >= node["min_dwell_s"] and (best is None or dwell > best[1]):
                best = (z, dwell)
        return best

    best = None
    if env.active_bindings:
        unfired = [z for z in matches if (("zone_id", z.zone_id),) not in env.active_bindings]
        if unfired:
            best = find_best(unfired)
    if best is None:
        best = find_best(matches)

    if best is None:
        return FALSE
    z, dwell = best
    return CondResult(True, {"zone_id": z.zone_id}, [f"inside zone {z.zone_id} ({z.zone_type}) for {dwell:.0f} s"])


def _recent_event(ctx, env, event_type, within_s, predicate):
    for e in reversed(ctx.events):
        if e["type"] == event_type and 0 <= env.now - e["ts"] <= within_s and predicate(e):
            return e
    return None


def _line_crossing(node, ctx, env) -> CondResult:
    line, direction, expected = node.get("line"), node.get("direction"), node.get("expected_direction")

    def match(e):
        if line and e["rule_id"] != line:
            return False
        if direction and e["direction"] != direction:
            return False
        if expected and (e["direction"] is None or e["direction"] == expected):
            return False
        return True

    e = _recent_event(ctx, env, "LINE_CROSSING", node["within_s"], match)
    if e is None:
        return FALSE
    what = f"crossed line {e['rule_id']} going {e['direction']}"
    if expected:
        what += f" (expected {expected})"
    return CondResult(True, {"line_id": e["rule_id"], "event_ts": round(e["ts"], 3)}, [what])


def _event(node, ctx, env) -> CondResult:
    where = node["where"]

    def match(e):
        return all(e.get(k) == v for k, v in where.items())

    e = _recent_event(ctx, env, node["event"], node["within_s"], match)
    if e is None:
        return FALSE
    return CondResult(True, {"event": node["event"], "event_ts": round(e["ts"], 3)}, [f"{node['event']} observed"])


def _time(node, ctx, env) -> CondResult:
    tz = get_zone(node["timezone"]) if node.get("timezone") else env.tz
    minutes, day = local_minutes_and_day(env.now, tz)
    start, end = (parse_hhmm(x) for x in node["between"])
    if not in_window(minutes, start, end):
        return FALSE
    if node.get("days") and day not in node["days"]:
        return FALSE
    return CondResult(True, {}, [f"local time {minutes // 60:02d}:{minutes % 60:02d} {day} is within "
                                  f"{node['between'][0]}-{node['between'][1]}"])


def _watchlist(node, ctx, env) -> CondResult:
    hit = ctx.watchlist
    ok = hit is not None
    if ok and node.get("status") and hit["status"] not in node["status"]:
        ok = False
    if ok and node.get("risk_level_min") and RISK_RANK[hit["risk_level"]] < RISK_RANK[node["risk_level_min"]]:
        ok = False
    if ok and node.get("entity_types") and hit["entity_type"] not in node["entity_types"]:
        ok = False
    if node["present"]:
        return CondResult(ok, {}, [f"watchlist {hit['status']} ({hit['risk_level']})"] if ok else [])
    return CondResult(not ok, {}, [] if ok else ["no matching watchlist hit"])


def _plate(node, ctx, env) -> CondResult:
    reasons = []
    if "read" in node:
        if (ctx.plate is not None) != node["read"]:
            return FALSE
        reasons.append("plate has been read" if node["read"] else "plate not read yet")
    if "authorized" in node:
        if ctx.plate is None or env.authorized is None:
            return FALSE                                   # an unread plate cannot be judged
        if env.authorized.contains(ctx.plate) != node["authorized"]:
            return FALSE
        reasons.append("plate is authorized" if node["authorized"] else "plate is not in the authorized list")
    return CondResult(True, {}, reasons)


def _track_age(node, ctx, env) -> CondResult:
    ok = env.age_s >= node["min_s"]
    return CondResult(ok, {}, [f"track age {env.age_s:.0f} s"] if ok else [])


def _all(node, ctx, env) -> CondResult:
    return evaluate_all(node["conditions"], ctx, env)


def _any(node, ctx, env) -> CondResult:
    for sub in node["conditions"]:
        r = evaluate(sub, ctx, env)
        if r.ok:
            return r
    return FALSE


def _not(node, ctx, env) -> CondResult:
    r = evaluate(node["condition"], ctx, env)
    return CondResult(not r.ok, {}, [] if r.ok else ["negated condition holds"])


_DISPATCH = {"object": _object, "zone": _zone, "line_crossing": _line_crossing, "event": _event,
             "time": _time, "watchlist": _watchlist, "plate": _plate, "track_age": _track_age,
             "all": _all, "any": _any, "not": _not}


def evaluate(node: dict, ctx: TrackContext, env: Env) -> CondResult:
    return _DISPATCH[node["type"]](node, ctx, env)


def evaluate_all(conditions: List[dict], ctx: TrackContext, env: Env) -> CondResult:
    """AND of the conditions. Bindings and reasons are merged; stops at the first false one."""
    bindings, reasons = {}, []
    for node in conditions:
        r = evaluate(node, ctx, env)
        if not r.ok:
            return FALSE
        bindings.update(r.bindings)
        reasons.extend(r.reasons)
    return CondResult(True, bindings, reasons)
