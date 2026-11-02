# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

root_dir = Path.cwd().resolve()
v1_dir = root_dir / "v1"

# Collect submodules and data for complex packages
uvicorn_datas, uvicorn_binaries, uvicorn_hidden = collect_all("uvicorn")
fastapi_datas, fastapi_binaries, fastapi_hidden = collect_all("fastapi")
webview_datas, webview_binaries, webview_hidden = collect_all("webview")
aiosqlite_datas, aiosqlite_binaries, aiosqlite_hidden = collect_all("aiosqlite")

# App specific datas
datas = [
    (str(v1_dir / "services"), "services"),
    (str(v1_dir / "configs"), "configs"),
    (str(v1_dir / "artifacts"), "artifacts"),
    (str(v1_dir / "project doc"), "project doc"),
    (str(v1_dir / "oncosentinel.db"), "."),
    (str(root_dir / "models"), "models"),
    (str(root_dir / "oncosentinel.ico"), "."),
    (str(root_dir / "MicrosoftEdgeWebview2Setup.exe"), "."),
]
datas += uvicorn_datas + fastapi_datas + webview_datas + aiosqlite_datas

binaries = uvicorn_binaries + fastapi_binaries + webview_binaries

hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "starlette",
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.staticfiles",
    "starlette.responses",
    "aiosqlite",
    "sqlite3",
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.aiosqlite",
    "anyio",
    "anyio._backends._asyncio",
    "asyncio",
    "webview",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "clr",
    "pythonnet",
    "clr_loader",
    "torch",
    "torchvision",
    "timm",
    "sympy",
    "numpy",
    "PIL",
    "sklearn",
    "yaml",
    "pydantic",
    "pydantic_settings",
    "jose",
    "passlib",
    "passlib.handlers",
    "passlib.handlers.bcrypt",
    "bcrypt",
    "multipart",
    "email_validator",
]
hiddenimports += uvicorn_hidden + fastapi_hidden + webview_hidden + aiosqlite_hidden

# Collect all submodules from v1/services
sys_path_added = False
import sys
if str(v1_dir) not in sys.path:
    sys.path.insert(0, str(v1_dir))
    sys_path_added = True

try:
    hiddenimports += collect_submodules("services")
except Exception:
    pass

a = Analysis(
    ["desktop_app.py"],
    pathex=[str(root_dir), str(v1_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=list(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tests", "tkinter", "PyQt5", "PySide2", "PySide6", "tensorflow", "scipy", "matplotlib", "IPython", "notebook"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OncoSentinel",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root_dir / "oncosentinel.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="OncoSentinel",
)
