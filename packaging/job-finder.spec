"""PyInstaller single-executable definition for the offline Windows release."""

from pathlib import Path


ROOT = Path(SPECPATH).parent
API_SOURCE = ROOT / "apps" / "api" / "src"
FRONTEND_DIST = ROOT / "apps" / "web" / "dist"
MIGRATIONS = ROOT / "apps" / "api" / "migrations"


a = Analysis(
    [str(ROOT / "scripts" / "run_local.py")],
    pathex=[str(API_SOURCE)],
    binaries=[],
    datas=[
        (str(FRONTEND_DIST), "apps/web/dist"),
        (str(MIGRATIONS), "apps/api/migrations"),
        (str(ROOT / "alembic.ini"), "."),
    ],
    hiddenimports=["alembic.ddl.sqlite"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["mypy", "pytest", "ruff"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="JobFinder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
