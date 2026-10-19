import logging
from pathlib import Path
from typing import Optional

from app import config
from app.behaviour.authorized import AuthorizedPlates
from app.behaviour.engine import BehaviourEngine
from app.behaviour.rules_config import check_rules_against_zones, load_behaviour_config

log = logging.getLogger("behaviour")


def build_behaviour(path: Optional[str] = None) -> Optional[BehaviourEngine]:
    """Load configs/rules.json (or `path`), validate it against the zone files, and build the engine.
    Raises ValueError for a bad rules file or for rules that name zones/lines that do not exist."""
    rules_path = Path(path) if path else config.CONFIG_DIR / "rules.json"
    if not rules_path.exists():
        log.warning("No rules file at %s: the behaviour engine is disabled", rules_path)
        return None
    cfg = load_behaviour_config(rules_path)

    zones_dir = config.CONFIG_DIR / "zones"
    if zones_dir.exists():
        errors, warnings = check_rules_against_zones(cfg, zones_dir)
        for w in warnings:
            log.warning("rules: %s", w)
        if errors:
            raise ValueError("rules do not match the zone files:\n  " + "\n  ".join(errors))

    authorized = None
    if cfg.authorized_plates_csv:
        authorized = AuthorizedPlates.from_csv(config.BASE_DIR / cfg.authorized_plates_csv)
        log.info("Authorized plates loaded: %d", len(authorized))
    return BehaviourEngine(cfg, authorized, rules_path=rules_path)
