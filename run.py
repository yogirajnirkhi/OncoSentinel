"""
OncoSentinel v2.0 — Root Entrypoint Wrapper
Delegates cleanly to `v1/run.py` with `v1/` as the working directory so relative
paths (database, configs, artifacts) resolve identically from root or `v1/`.
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent
    v1_dir = root_dir / "v1"
    os.chdir(v1_dir)
    if str(v1_dir) not in sys.path:
        sys.path.insert(0, str(v1_dir))
    runpy.run_path(str(v1_dir / "run.py"), run_name="__main__")
