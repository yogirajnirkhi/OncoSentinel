from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    configured = os.environ.get("HMS_CONFIG_PATH")
    if configured and Path(configured).exists():
        path = Path(configured)
    elif Path("configs/hms.yaml").exists():
        path = Path("configs/hms.yaml")
    else:
        # Fallback relative to repository root
        fallback = Path(__file__).resolve().parents[2] / "configs" / "hms.yaml"
        if fallback.exists():
            path = fallback
        else:
            path = Path("configs/hms.yaml")

    with path.open(encoding="utf-8") as stream:
        config: dict[str, Any] = yaml.safe_load(stream)
    if not config.get("resources") or not config.get("roles"):
        raise RuntimeError("HMS configuration is incomplete")
    return config
