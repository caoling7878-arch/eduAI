# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for eduAI local server (run from apps/api).

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None
# SPECPATH = directory containing this .spec (desktop/)
repo_root = Path(SPECPATH).resolve().parent
api_root = repo_root / "apps" / "api"
app_pkg = api_root / "app"

datas = []
binaries = []
hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "app.main",
    "email_validator",
    "passlib.handlers.bcrypt",
    "httpx",
    "httpcore",
    "anyio",
    "h11",
    "sniffio",
]

# Package data: SPA builds, static vocab images, JSON banks
for rel in ("spa/web", "spa/admin", "static", "data"):
    src = app_pkg / rel
    if src.exists():
        datas.append((str(src), f"app/{rel}"))

# Optional math worksheet corpus at repo root
math_dir = repo_root / "1-6年级计算专项练习"
if math_dir.is_dir():
    datas.append((str(math_dir), "1-6年级计算专项练习"))

for pkg in ("uvicorn", "edge_tts", "docx", "fitz", "pptx"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

datas += collect_data_files("certifi")

a = Analysis(
    [str(api_root / "desktop_entry.py")],
    pathex=[str(api_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="eduai-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False if sys.platform == "win32" else True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="eduai-server",
)
