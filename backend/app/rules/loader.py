"""Load the versioned rule repository (one YAML file per scheme)."""

from functools import lru_cache
from pathlib import Path

import yaml

from app.rules.engine import SchemeRules

SCHEMES_DIR = Path(__file__).parent / "schemes"


@lru_cache(maxsize=1)
def load_all_rules() -> dict[str, SchemeRules]:
    rules: dict[str, SchemeRules] = {}
    for path in sorted(SCHEMES_DIR.glob("*.yaml")):
        scheme = SchemeRules.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        rules[scheme.scheme_id] = scheme
    if not rules:
        raise RuntimeError(f"no rule files found in {SCHEMES_DIR}")
    return rules
