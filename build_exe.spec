# =============================================================================
# PyInstaller Spec File for Rocket Simulator Pro
# =============================================================================
#
# Usage: pyinstaller build_exe.spec --noconfirm
#
# This spec file creates a directory-based executable with all required
# data files and dependencies bundled.
#
# =============================================================================

from PyInstaller.__main__ import run
import os
import sys

# Application metadata
app_name = "RocketSimulator"
main_script = "main.py"

# Data files to include (source, destination)
datas = [
    # Data directory and all subdirectories
    ("data", "data"),
    
    # UI directory
    ("ui", "ui"),
    
    # Source directory
    ("src", "src"),
    
    # Models directory (legacy)
    ("models", "models"),
    
    # Workers directory
    ("workers", "workers"),
    
    # Version file
    ("version.py", "."),
]

# Hidden imports (modules that need to be explicitly included)
hidden_imports = [
    # PyQt6
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtSvg",
    
    # Scientific computing
    "numpy",
    "scipy",
    "scipy.integrate",
    "scipy.interpolate",
    "pandas",
    
    # Visualization
    "matplotlib",
    "matplotlib.backends.backend_qt5agg",
    "cartopy",
    "pyqtgraph",
    
    # Rocket simulation specific
    "navpy",
    "fluids",
    "ephem",
    
    # Data validation
    "jsonschema",
    
    # Document generation
    "reportlab",
    
    # System
    "encodings.*",
]

# Excluded modules
excludes = [
    "_tkinter",
    "tkinter",
    "unittest",
    "email",
    "http",
    "xml",
    "pdb",
    "doctest",
    "test",
]

# Build configuration
Analysis(
    [main_script],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)

# Create executable
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Windows/macOS/Linux compatible EXE
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=app_name,
    debug=False,
    strip=False,
    upx=False,
    console=False,  # Windowed mode (no console)
)

# Create directory-based distribution (not single file)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=app_name,
)
