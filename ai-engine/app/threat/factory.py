import json
import logging
from pathlib import Path
from typing import Optional

from app import config
from app.behaviour.rules_config import load_behaviour_config
from app.threat.config import check_scoring_against_rules, parse_scoring_config
from app.threat.scorer import ThreatScorer

log = logging.getLogger("threat")


def build_scorer(path: Optional[str] = None) -> Optional[ThreatScorer]:
    """Build the scorer from the 'scoring' section of configs/rules.json (or `path`).
    Raises ValueError for an invalid section; returns None if there is no section."""
    rules_path = Path(path) if path else config.CONFIG_DIR / "rules.json"
    if not rules_path.exists():
        log.warning("No rules file at %s: the threat scorer is disabled", rules_path)
        return None
    data = json.loads(rules_path.read_text(encoding="utf-8"))
    if "scoring" not in data:
        log.warning("%s has no 'scoring' section: the threat scorer is disabled", rules_path)
        return None
    cfg = parse_scoring_config(data, source=str(rules_path))
    try:
        for warning in check_scoring_against_rules(cfg, load_behaviour_config(rules_path)):
            log.warning("scoring: %s", warning)
    except ValueError:
        pass                                                   # the behaviour part is validated by its own loader
    return ThreatScorer(cfg)
