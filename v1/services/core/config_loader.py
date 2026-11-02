"""
OncoSentinel v2.0 — Config Loader
Loads taxonomy, thresholds, and fairness strata from versioned YAML files.
Satisfies: FR-04, FR-28 (version everything; no hard-coded thresholds)
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from services.core.logging import get_logger
from services.core.settings import get_settings

logger = get_logger(__name__)


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load and parse a YAML config file."""
    target_path = path
    if not target_path.exists():
        repo_root = Path(__file__).resolve().parents[2]
        alt = repo_root / path
        if alt.exists():
            target_path = alt
        elif (Path("v1") / path).exists():
            target_path = Path("v1") / path
        else:
            raise FileNotFoundError(f"Config file not found: {path}")
    with open(target_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logger.info("config_loaded", path=str(target_path), version=data.get("version", "unknown"))
    return data


@lru_cache(maxsize=1)
def get_taxonomy() -> dict[str, Any]:
    """Return cached taxonomy config."""
    return _load_yaml(get_settings().taxonomy_config_path)


@lru_cache(maxsize=1)
def get_thresholds() -> dict[str, Any]:
    """Return cached thresholds config."""
    return _load_yaml(get_settings().thresholds_config_path)


@lru_cache(maxsize=1)
def get_fairness_strata() -> dict[str, Any]:
    """Return cached fairness strata config."""
    return _load_yaml(get_settings().fairness_strata_config_path)


def get_category_config(category: str) -> dict[str, Any]:
    """Return config for a specific category, raising if not found."""
    taxonomy = get_taxonomy()
    cats = taxonomy.get("categories", {})
    if category not in cats:
        raise KeyError(f"Category '{category}' not found in taxonomy v{taxonomy['version']}")
    return cats[category]


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, val in overrides.items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


def get_uncertainty_thresholds(category: str) -> dict[str, Any]:
    """Return recursively merged global + category uncertainty thresholds."""
    thresholds = get_thresholds()
    global_thresh = thresholds.get("global", {})
    cat_overrides = thresholds.get("categories", {}).get(category, {})
    return _deep_merge(global_thresh, cat_overrides)


def is_category_available(category: str, current_phase: int | None = None) -> bool:
    """Check if a category is available in the current platform phase."""
    if current_phase is None:
        current_phase = get_settings().platform_phase
    try:
        cat_config = get_category_config(category)
    except KeyError:
        return False
    return cat_config.get("phase_availability", 99) <= current_phase


def get_supported_modalities(category: str) -> list[str]:
    """Return supported modalities for a category."""
    return get_category_config(category).get("supported_modalities", [])


def get_taxonomy_version() -> str:
    """Return the current taxonomy version string."""
    return get_taxonomy().get("version", "unknown")


def get_thresholds_version() -> str:
    """Return the current thresholds version string."""
    return get_thresholds().get("version", "unknown")
