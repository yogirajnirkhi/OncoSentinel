"""
OncoSentinel v2.0 + HMS Unified Runner
Launches the integrated FastAPI application.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

CONFIG_PATH = BASE_DIR / "configs" / "hms.yaml"
if CONFIG_PATH.exists():
    os.environ.setdefault("HMS_CONFIG_PATH", str(CONFIG_PATH))

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'oncosentinel.db'}")

if __name__ == "__main__":
    import argparse
    import socket
    import uvicorn

    parser = argparse.ArgumentParser(description="OncoSentinel v2.0 Runner")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on (default 8000)")
    args = parser.parse_args()

    port = args.port
    # Verify port availability; find free port if default is occupied
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            for alt_port in range(port + 1, port + 50):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as alt_s:
                    try:
                        alt_s.bind(("127.0.0.1", alt_port))
                        print(f"[OncoSentinel] Notice: Port {port} was occupied. Auto-switching to free port {alt_port}.")
                        port = alt_port
                        break
                    except OSError:
                        continue

    print("=" * 70)
    print("  ONCOSENTINEL v2.0 + HOSPITAL MANAGEMENT SYSTEM (HMS)")
    print("=" * 70)
    print(f"  Clinical AI Platform:   http://127.0.0.1:{port}/")
    print(f"  Hospital Management:    http://127.0.0.1:{port}/hms")
    print(f"  API Docs (Swagger UI):  http://127.0.0.1:{port}/docs")
    print(f"  Health Status:          http://127.0.0.1:{port}/health")
    print("=" * 70)

    uvicorn.run(
        "services.gateway.app:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="info",
    )
