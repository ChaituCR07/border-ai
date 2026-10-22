from app.events.config import EventsConfig
from app.events.streams import StreamClient


def collect_stats(client: StreamClient, cfg: EventsConfig) -> dict:
    out = {}
    for label, stream in (("events", cfg.stream), ("alerts", cfg.alerts_stream), ("dead", cfg.dead_stream)):
        try:
            groups = client.groups_info(stream)
        except Exception:                                      # the stream or its groups may not exist yet
            groups = []
        out[label] = {"stream": stream, "length": client.length(stream),
                      "groups": [{"name": g["name"], "consumers": g["consumers"], "pending": g["pending"],
                                  "lag": g.get("lag")} for g in groups]}
    return out


def format_stats(stats: dict) -> str:
    lines = []
    for label, s in stats.items():
        lines.append(f"{label:<8}{s['stream']:<28}length {s['length']}")
        for g in s["groups"]:
            lines.append(f"          group {g['name']:<14}consumers {g['consumers']}  pending {g['pending']}  lag {g['lag']}")
    return "\n".join(lines)
