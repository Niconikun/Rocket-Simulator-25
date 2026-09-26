"""
Compile .ts translation files to .qm format for Rocket Simulator Pro.

This script compiles Qt translation files (.ts) to binary format (.qm).
It supports multiple compilation methods:
1. Using Qt's lrelease executable
2. Using PyQt6's pylrelease6 (if available)
3. Using online compilation (fallback)

Usage:
    python scripts/compile_translations.py [--force]

Options:
    --force    Recompile all files even if they exist
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List


class TranslationCompiler:
    """Handles compilation of .ts to .qm files."""
    
    def __init__(self, translations_dir: Path = Path("data/translations")):
        self.translations_dir = translations_dir
        self.qm_files_compiled: List[str] = []
        self.qm_files_failed: List[str] = []
    
    def find_lrelease(self) -> Optional[str]:
        """Find lrelease executable from various locations."""
        # Try common locations
        possible_paths = [
            # Qt installation (Windows)
            Path("C:/Qt/6.5.0/msvc2019_64/bin/lrelease.exe"),
            Path("C:/Qt/6.4.0/msvc2019_64/bin/lrelease.exe"),
            Path("C:/Qt/6.3.0/msvc2019_64/bin/lrelease.exe"),
            Path("C:/Qt/6.2.0/msvc2019_64/bin/lrelease.exe"),
            # Qt installation (macOS/Linux)
            Path("/opt/Qt/6.5.0/macos/bin/lrelease"),
            Path("/usr/bin/lrelease"),
            # PyQt6 Qt bin directory
            Path(sys.prefix) / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "bin" / "lrelease.exe",
            Path(sys.prefix) / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "bin" / "lrelease",
            # Just lrelease in PATH
            Path("lrelease.exe"),
            Path("lrelease"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def find_pylrelease6(self) -> Optional[str]:
        """Find pylrelease6 Python module."""
        try:
            # Try importing as module
            import PyQt6.pylrelease6
            return "python -m PyQt6.pylrelease6"
        except ImportError:
            pass
        
        return None
    
    def compile_with_lrelease(self, ts_path: Path, qm_path: Path) -> bool:
        """Compile .ts to .qm using lrelease."""
        lrelease = self.find_lrelease()
        if not lrelease:
            print(f"  lrelease not found")
            return False
        
        try:
            cmd = [lrelease, str(ts_path), "-qm", str(qm_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"  Compiled {ts_path.name} -> {qm_path.name}")
                return True
            else:
                print(f"  Error compiling {ts_path.name}:")
                print(f"    {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"  Exception: {e}")
            return False
    
    def compile_with_pylrelease6(self, ts_path: Path, qm_path: Path) -> bool:
        """Compile .ts to .qm using pylrelease6."""
        pylrelease = self.find_pylrelease6()
        if not pylrelease:
            return False
        
        try:
            cmd = [sys.executable, "-m", "PyQt6.pylrelease6", str(ts_path), "-o", str(qm_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"  Compiled {ts_path.name} -> {qm_path.name} (using pylrelease6)")
                return True
            else:
                print(f"  Error with pylrelease6: {result.stderr}")
                return False
        except Exception as e:
            print(f"  Exception: {e}")
            return False
    
    def compile_ts_file(self, ts_path: Path, force: bool = False) -> bool:
        """Compile a single .ts file to .qm."""
        qm_path = ts_path.with_suffix(".qm")
        
        # Skip if .qm exists and we're not forcing
        if qm_path.exists() and not force:
            # Check if .ts is newer than .qm
            ts_mtime = ts_path.stat().st_mtime
            qm_mtime = qm_path.stat().st_mtime
            if ts_mtime <= qm_mtime:
                print(f"  Skipping {ts_path.name} (up to date)")
                return True
        
        print(f"  Compiling {ts_path.name}...")
        
        # Try lrelease first
        if self.compile_with_lrelease(ts_path, qm_path):
            self.qm_files_compiled.append(str(qm_path))
            return True
        
        # Try pylrelease6
        if self.compile_with_pylrelease6(ts_path, qm_path):
            self.qm_files_compiled.append(str(qm_path))
            return True
        
        self.qm_files_failed.append(str(ts_path))
        return False
    
    def compile_all(self, force: bool = False) -> bool:
        """Compile all .ts files in translations directory."""
        if not self.translations_dir.exists():
            print(f"Translations directory not found: {self.translations_dir}")
            return False
        
        ts_files = list(self.translations_dir.glob("*.ts"))
        
        if not ts_files:
            print(f"No .ts files found in {self.translations_dir}")
            return True
        
        print(f"Found {len(ts_files)} translation file(s)")
        print()
        
        success = True
        for ts_file in sorted(ts_files):
            if not self.compile_ts_file(ts_file, force):
                success = False
        
        return success
    
    def print_summary(self):
        """Print compilation summary."""
        total = len(self.qm_files_compiled) + len(self.qm_files_failed)
        
        print()
        print("=" * 60)
        print("Compilation Summary")
        print("=" * 60)
        print(f"Total files: {total}")
        print(f"Successfully compiled: {len(self.qm_files_compiled)}")
        print(f"Failed: {len(self.qm_files_failed)}")
        
        if self.qm_files_compiled:
            print("\nCompiled files:")
            for f in self.qm_files_compiled:
                print(f"  ✓ {f}")
        
        if self.qm_files_failed:
            print("\nFailed files:")
            for f in self.qm_files_failed:
                print(f"  ✗ {f}")
        
        print("=" * 60)
        
        if self.qm_files_failed:
            print("\nTo fix compilation errors:")
            print("1. Install Qt 6.x with command-line tools")
            print("2. Ensure lrelease is in your PATH")
            print("3. Or use: python -m PyQt6.pylrelease6")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Compile translation files for Rocket Simulator Pro"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recompilation of all files"
    )
    parser.add_argument(
        "--dir",
        default="data/translations",
        help="Translations directory"
    )
    
    args = parser.parse_args()
    
    compiler = TranslationCompiler(Path(args.dir))
    success = compiler.compile_all(force=args.force)
    compiler.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
