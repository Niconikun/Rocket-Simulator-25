#!/usr/bin/env python3
"""
Build script for Rocket Simulator Pro executable
Works on Windows, Linux, and macOS
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'


class BuildEXE:
    """Build executable using PyInstaller."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        
    def print_header(self, title):
        """Print formatted header."""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    
    def run_command(self, cmd, description):
        """Run command and handle errors."""
        print(f"[*] {description}...")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=False,
                check=True
            )
            print(f"[✓] {description} - OK")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[✗] {description} - FAILED")
            print(f"Error: {e}")
            return False
    
    def check_pyinstaller(self):
        """Verify PyInstaller is installed."""
        print("[*] Checking PyInstaller...")
        try:
            import PyInstaller
            print(f"[✓] PyInstaller {PyInstaller.__version__} found")
            return True
        except ImportError:
            print("[!] PyInstaller not found. Installing...")
            if self.run_command(
                f"{sys.executable} -m pip install pyinstaller>=6.0.0",
                "Installing PyInstaller"
            ):
                return True
            return False
    
    def check_dependencies(self):
        """Check all required packages."""
        print("[*] Checking dependencies...")
        required = [
            'PyQt6', 'numpy', 'scipy', 'pandas',
            'matplotlib', 'pyvista', 'plotly'
        ]
        
        missing = []
        for package in required:
            try:
                __import__(package)
                print(f"  [✓] {package}")
            except ImportError:
                print(f"  [✗] {package} - MISSING")
                missing.append(package)
        
        if missing:
            print(f"\n[!] Installing missing packages: {', '.join(missing)}")
            return self.run_command(
                f"{sys.executable} -m pip install {' '.join(missing)}",
                "Installing missing dependencies"
            )
        return True
    
    def clean_builds(self):
        """Remove previous builds."""
        print("\n[*] Cleaning previous builds...")
        dirs_to_remove = [self.build_dir, self.dist_dir]
        
        for dir_path in dirs_to_remove:
            if dir_path.exists():
                print(f"  Removing {dir_path.name}/")
                shutil.rmtree(dir_path, ignore_errors=True)
        
        # Remove .spec files
        for spec_file in self.project_root.glob("*.spec"):
            if spec_file.name != "build_exe.spec":
                try:
                    spec_file.unlink()
                except:
                    pass
        
        print("[✓] Clean complete")
        return True
    
    def build(self):
        """Build executable."""
        print("\n[*] Building executable...")
        print("    Using: build_exe.spec")
        
        cmd = f"{sys.executable} -m PyInstaller build_exe.spec --noconfirm"
        
        if not self.run_command(cmd, "Building with PyInstaller"):
            return False
        
        # Verify output
        if sys.platform.startswith('win'):
            exe_path = self.dist_dir / "RocketSimulator" / "RocketSimulator.exe"
        else:
            exe_path = self.dist_dir / "RocketSimulator" / "RocketSimulator"
        
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024*1024)
            print(f"[✓] Executable created: {exe_path}")
            print(f"    Size: {size_mb:.1f} MB")
            return True
        else:
            print(f"[✗] Executable not found at {exe_path}")
            return False
    
    def main(self):
        """Run complete build process."""
        self.print_header("ROCKET SIMULATOR PRO - BUILD EXECUTABLE")
        
        steps = [
            ("Checking PyInstaller", self.check_pyinstaller),
            ("Checking dependencies", self.check_dependencies),
            ("Cleaning old builds", self.clean_builds),
            ("Building executable", self.build),
        ]
        
        for step_name, step_func in steps:
            if not step_func():
                print(f"\n[✗] Build failed at: {step_name}")
                return 1
        
        # Success
        self.print_header("BUILD SUCCESSFUL!")
        
        if sys.platform.startswith('win'):
            exe_path = self.dist_dir / "RocketSimulator" / "RocketSimulator.exe"
            print(f"Executable: dist\\RocketSimulator\\RocketSimulator.exe")
        else:
            exe_path = self.dist_dir / "RocketSimulator" / "RocketSimulator"
            print(f"Executable: dist/RocketSimulator/RocketSimulator")
        
        print(f"\nNext steps:")
        print("1. Test the executable:")
        if sys.platform.startswith('win'):
            print("   dist\\RocketSimulator\\RocketSimulator.exe")
        else:
            print("   ./dist/RocketSimulator/RocketSimulator")
        
        print("\n2. To create single-file executable:")
        print("   - Edit build_exe.spec")
        print("   - Comment COLLECT section")
        print("   - Run: pyinstaller build_exe.spec --noconfirm")
        
        print("\n" + "="*60 + "\n")
        
        return 0


if __name__ == "__main__":
    builder = BuildEXE()
    sys.exit(builder.main())
