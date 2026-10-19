import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.behaviour.rules_config import check_rules_against_zones, load_behaviour_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Validate a rules file and check it against the zone files")
    ap.add_argument("--rules", default=str(config.CONFIG_DIR / "rules.json"))
    args = ap.parse_args()
    try:
        cfg = load_behaviour_config(Path(args.rules))
    except (ValueError, OSError) as e:
        sys.exit(f"INVALID: {e}")
    print(f"site time zone {cfg.timezone} | {len(cfg.rules)} rule(s)\n")
    print(f"{'id':<6}{'event type':<36}{'severity':<10}{'points':>6}  {'enabled':<8}name")
    for r in cfg.rules:
        print(f"{r.rule_id:<6}{r.event_type:<36}{r.severity:<10}{r.points:>6}  {str(r.enabled):<8}{r.name}")
    errors, warnings = check_rules_against_zones(cfg, config.CONFIG_DIR / "zones")
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:  ", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
