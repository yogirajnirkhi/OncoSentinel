"""
OncoSentinel v2.0 — Standalone Desktop Application Entrypoint
Provides native Windows window UI (via WebView2) with embedded FastAPI backend.
"""
from __future__ import annotations

import sys
import types
import numpy as np

# Inject lightweight pure-NumPy mock for scipy / scipy.special before any module loads it
# Prevents PyInstaller frozen Cython loader errors (scipy._cyutility)
if "scipy" not in sys.modules:
    scipy_mock = types.ModuleType("scipy")
    scipy_special_mock = types.ModuleType("scipy.special")

    def _logsumexp(a, axis=None, keepdims=False):
        a = np.asarray(a)
        a_max = np.max(a, axis=axis, keepdims=True)
        out = a_max + np.log(np.sum(np.exp(a - a_max), axis=axis, keepdims=keepdims))
        return float(np.squeeze(out)) if axis is None else np.squeeze(out, axis=axis)

    def _softmax(x, axis=-1):
        x = np.asarray(x)
        e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return e_x / np.sum(e_x, axis=axis, keepdims=True)

    scipy_special_mock.logsumexp = _logsumexp
    scipy_special_mock.softmax = _softmax
    scipy_mock.special = scipy_special_mock
    sys.modules["scipy"] = scipy_mock
    sys.modules["scipy.special"] = scipy_special_mock

import argparse
import os
import shutil
import socket
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

# Setup file and console logging
is_frozen = getattr(sys, "frozen", False)
if is_frozen:
    log_dir = Path(sys.executable).resolve().parent
else:
    log_dir = Path(__file__).resolve().parent

log_file_path = log_dir / "oncosentinel.log"

class LogTee:
    def __init__(self, original_stream, log_file):
        self.original = original_stream
        self.log_file = log_file

    def write(self, data):
        if self.original:
            try:
                self.original.write(data)
                self.original.flush()
            except Exception:
                pass
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(data)
        except Exception:
            pass

    def flush(self):
        if self.original:
            try:
                self.original.flush()
            except Exception:
                pass

    def isatty(self):
        if self.original and hasattr(self.original, "isatty"):
            try:
                return self.original.isatty()
            except Exception:
                pass
        return False

sys.stdout = LogTee(sys.stdout, log_file_path)
sys.stderr = LogTee(sys.stderr, log_file_path)

def log_uncaught_exception(exctype, value, tb):
    import traceback
    lines = "".join(traceback.format_exception(exctype, value, tb))
    msg = f"\n[UNCAUGHT EXCEPTION {time.strftime('%Y-%m-%d %H:%M:%S')}]\n{lines}"
    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    if sys.__stderr__:
        try:
            sys.__stderr__.write(msg + "\n")
        except Exception:
            pass

sys.excepthook = log_uncaught_exception


def find_free_port(start_port: int = 8000, max_attempts: int = 50) -> int:
    """Finds an open TCP port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port


def setup_environment() -> tuple[Path, Path]:
    """Configures paths, database, and environment variables."""
    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        exe_dir = Path(sys.executable).resolve().parent
        bundle_dir = Path(getattr(sys, "_MEIPASS", exe_dir)).resolve()
    else:
        exe_dir = Path(__file__).resolve().parent
        bundle_dir = exe_dir

    # Add v1 directory to sys.path so modules resolve cleanly
    v1_candidates = [
        bundle_dir / "v1",
        bundle_dir,
        exe_dir / "v1",
        exe_dir,
    ]
    for candidate in v1_candidates:
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))

    # Working directory: switch to v1 if it exists
    v1_dir = bundle_dir / "v1" if (bundle_dir / "v1").exists() else bundle_dir
    os.chdir(str(v1_dir))

    # Database persistence: ensure oncosentinel.db lives in the persistent exe_dir
    target_db = exe_dir / "oncosentinel.db"
    if not target_db.exists():
        # Check if a pre-seeded DB is available to copy
        seed_candidates = [
            bundle_dir / "v1" / "oncosentinel.db",
            bundle_dir / "oncosentinel.db",
            exe_dir / "v1" / "oncosentinel.db",
        ]
        for src in seed_candidates:
            if src.exists() and src.stat().st_size > 0:
                try:
                    shutil.copy2(src, target_db)
                    print(f"[OncoSentinel] Seeded database copied to: {target_db}")
                    break
                except Exception as err:
                    print(f"[OncoSentinel] Warning copying seed db: {err}")

    # Set DATABASE_URL to use SQLite file in exe_dir (or fallback to bundle_dir)
    db_file = target_db if target_db.parent.is_dir() else (v1_dir / "oncosentinel.db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file.as_posix()}"

    # HMS configuration
    config_candidates = [
        exe_dir / "configs" / "hms.yaml",
        v1_dir / "configs" / "hms.yaml",
        bundle_dir / "configs" / "hms.yaml",
    ]
    for cfg in config_candidates:
        if cfg.exists():
            os.environ["HMS_CONFIG_PATH"] = str(cfg)
            break

    # Environment
    os.environ.setdefault("ENVIRONMENT", "production")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ["TZ"] = "Asia/Kolkata"
    try:
        import time
        if hasattr(time, "tzset"):
            time.tzset()
    except Exception:
        pass

    return exe_dir, bundle_dir


def wait_for_server(port: int, max_retries: int = 40, delay: float = 0.5) -> bool:
    """Polls the /health endpoint until FastAPI is ready."""
    url = f"http://127.0.0.1:{port}/health"
    for _ in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(delay)
    return False


def check_webview2_installed() -> bool:
    """Checks whether Microsoft Edge WebView2 Runtime is installed on this PC."""
    try:
        import winreg
        guid = r"{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for sub in (
                rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{guid}",
                rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{guid}",
            ):
                try:
                    with winreg.OpenKey(root, sub, 0, winreg.KEY_READ) as k:
                        val, _ = winreg.QueryValueEx(k, "pv")
                        if val and val != "0.0.0.0":
                            return True
                except Exception:
                    pass
    except Exception:
        pass
    return False


def prompt_webview2_install_or_fallback(exe_dir: Path, bundle_dir: Path, port: int, server_thread: threading.Thread):
    """Handles missing WebView2 runtime: offers one-click install or seamless browser fallback."""
    import ctypes
    import subprocess

    installer = None
    for cand in [exe_dir / "MicrosoftEdgeWebview2Setup.exe", bundle_dir / "MicrosoftEdgeWebview2Setup.exe"]:
        if cand.exists():
            installer = cand
            break

    msg = (
        "OncoSentinel requires Microsoft Edge WebView2 Runtime to display its native desktop window.\n\n"
        "Would you like to install it now?\n\n"
        "• Click YES to install the Microsoft WebView2 Runtime automatically.\n"
        "• Click NO to open OncoSentinel immediately in your default browser."
    )
    title = "OncoSentinel — WebView2 Runtime Required"
    # MB_YESNO (0x4) | MB_ICONQUESTION (0x20)
    choice = ctypes.windll.user32.MessageBoxW(0, msg, title, 0x4 | 0x20)
    if choice == 6 and installer:  # IDYES = 6
        try:
            print("[OncoSentinel] Installing WebView2 Runtime in background...")
            subprocess.Popen([str(installer), "/silent", "/install"])
        except Exception as e:
            print(f"[OncoSentinel] Failed to launch installer: {e}")

    # Fallback immediately to default browser so user is never blocked
    print(f"[OncoSentinel] Opening default web browser at http://127.0.0.1:{port}/")
    webbrowser.open(f"http://127.0.0.1:{port}/")
    print("[OncoSentinel] Application running in browser. Close this console or press Ctrl+C to stop.")
    try:
        while server_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def run_desktop():
    parser = argparse.ArgumentParser(description="OncoSentinel Desktop Application")
    parser.add_argument("--port", type=int, default=None, help="Force a specific port (default: auto 8000)")
    parser.add_argument("--browser", action="store_true", help="Open in default system web browser instead of native desktop window")
    parser.add_argument("--server-only", action="store_true", help="Run background server only without GUI window")
    args = parser.parse_args()

    exe_dir, bundle_dir = setup_environment()

    # Determine port
    port = args.port if args.port else find_free_port(8000)
    print("=" * 70)
    print("  ONCOSENTINEL v2.0 — CLINICAL AI & HOSPITAL MANAGEMENT SYSTEM")
    print("=" * 70)
    print(f"  Application Directory: {exe_dir}")
    print(f"  Local Service URL:     http://127.0.0.1:{port}/")
    print(f"  HMS Dashboard:         http://127.0.0.1:{port}/hms")
    print("=" * 70)

    # Import uvicorn & FastAPI app
    import uvicorn
    from services.gateway.app import app

    class ThreadedUvicornServer(uvicorn.Server):
        def install_signal_handlers(self):
            # In a thread, signal handlers cannot be installed; GUI handles exit
            pass

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="warning",
        access_log=False,
        log_config=None,
    )
    server = ThreadedUvicornServer(config=config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    print(f"[OncoSentinel] Initializing server on port {port}...")
    ready = wait_for_server(port)
    if not ready:
        print("[OncoSentinel] ERROR: Server failed to respond to health check in time.")
        server.should_exit = True
        sys.exit(1)

    print("[OncoSentinel] Server is healthy and operational!")

    if args.server_only:
        print("[OncoSentinel] Running in server-only mode. Press Ctrl+C to terminate.")
        try:
            while server_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[OncoSentinel] Shutting down...")
            server.should_exit = True
            server_thread.join(timeout=3)
        return

    if args.browser:
        print(f"[OncoSentinel] Opening browser at http://127.0.0.1:{port}/")
        webbrowser.open(f"http://127.0.0.1:{port}/")
        print("[OncoSentinel] Server is running. Press Ctrl+C in this console to exit.")
        try:
            while server_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[OncoSentinel] Shutting down...")
            server.should_exit = True
            server_thread.join(timeout=3)
        return

    # Check if Microsoft Edge WebView2 runtime is available on this Windows PC
    if not check_webview2_installed():
        print("[OncoSentinel] WebView2 Runtime not detected on this PC.")
        prompt_webview2_install_or_fallback(exe_dir, bundle_dir, port, server_thread)
        print("[OncoSentinel] Stopping server...")
        server.should_exit = True
        server_thread.join(timeout=3)
        print("[OncoSentinel] Clean exit.")
        return

    # Native Desktop UI via pywebview
    try:
        import webview

        print("[OncoSentinel] Launching native desktop window...")
        window = webview.create_window(
            title="OncoSentinel v2.0 — AI Clinical Decision Support & HMS",
            url=f"http://127.0.0.1:{port}/",
            width=1400,
            height=900,
            min_size=(1024, 680),
            text_select=True,
            confirm_close=False,
        )

        start_time = time.time()
        # Starts the native GUI loop (blocks until user closes the window)
        webview.start(debug=False)
        window_duration = time.time() - start_time

        # If the window closed in less than 3 seconds, WebView2 failed internally
        if window_duration < 3.0:
            print("[OncoSentinel] Native window exited immediately. Falling back to system browser...")
            prompt_webview2_install_or_fallback(exe_dir, bundle_dir, port, server_thread)

    except Exception as err:
        print(f"[OncoSentinel] Desktop window notice ({err}). Falling back to system browser.")
        prompt_webview2_install_or_fallback(exe_dir, bundle_dir, port, server_thread)

    finally:
        print("[OncoSentinel] Window closed. Stopping server...")
        server.should_exit = True
        server_thread.join(timeout=3)
        print("[OncoSentinel] Clean exit.")
        sys.exit(0)


if __name__ == "__main__":
    try:
        run_desktop()
    except Exception as exc:
        import traceback
        err_msg = f"[FATAL CRASH] {exc}\n{traceback.format_exc()}"
        print(err_msg)
        try:
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(err_msg + "\n")
        except Exception:
            pass
        sys.exit(1)
