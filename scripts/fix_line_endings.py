#!/usr/bin/env python3
"""
Fix Line Endings Script for Rocket Simulator Pro

This script normalizes line endings to LF (Unix-style) for all text files
in the repository. This ensures cross-platform compatibility.

Usage:
    python scripts/fix_line_endings.py [--dry-run] [--force]

Options:
    --dry-run    Show what would be changed without modifying files
    --force      Force conversion even if file appears to be binary
"""

import os
import sys
import argparse
from pathlib import Path


# File extensions to process
TEXT_EXTENSIONS = {
    '.py', '.pyw', '.pyi', '.pyx',
    '.md', '.rst', '.txt', '.csv',
    '.json', '.yaml', '.yml', '.toml',
    '.cfg', '.ini', '.conf',
    '.html', '.css', '.js', '.ts',
    '.xml', '.svg',
    '.qss', '.ui', '.qrc',
    '.sh', '.bash',
    '.bat', '.cmd',
    '.dockerignore', '.gitignore', '.gitkeep',
    '.editorconfig', '.pre-commit-config.yaml',
    'Makefile', 'Dockerfile', 'LICENSE',
    'requirements.txt', 'requirements-dev.txt',
    'setup.py', 'pyproject.toml',
    'CONTRIBUTING', 'CODE_OF_CONDUCT',
    'CHANGELOG', 'README',
}

# Directories to skip
SKIP_DIRS = {
    '__pycache__', '.git', '.mypy_cache', '.pytest_cache',
    'build', 'dist', '.venv', 'venv', 'ENV',
    'node_modules', '.vscode', '.idea',
}

# Binary file signatures (first few bytes)
BINARY_SIGNATURES = [
    b'\x89PNG', b'\xff\xd8\xff', b'\x47IF', b'\x00\x00\x01',
    b'\x7fELF', b'MZ', b'\xca\xfe\xba\xbe',
    b'\x00\x00\x02\x00', b'\x25PDF',
]


def is_text_file(filepath: Path) -> bool:
    """Check if a file is a text file based on extension and content."""
    # Check extension
    if filepath.suffix.lower() in TEXT_EXTENSIONS:
        return True
    
    # Check if it's a special file (no extension but known text file)
    if filepath.name in {'Makefile', 'Dockerfile', 'LICENSE'}:
        return True
    
    # Check if it's in a known text directory
    if any(str(filepath).startswith(d) for d in ['.github/', 'data/', 'docs/', 'scripts/']):
        return True
    
    return False


def is_binary_file(filepath: Path) -> bool:
    """Check if a file is binary by reading its signature."""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(32)
            for sig in BINARY_SIGNATURES:
                if header.startswith(sig):
                    return True
            # Check for null bytes (common in binary files)
            if b'\x00' in header[:100]:
                return True
        return False
    except Exception:
        return False


def has_crlf(filepath: Path) -> bool:
    """Check if a file has CRLF line endings."""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            return b'\r\n' in content
    except Exception:
        return False


def has_mixed_line_endings(filepath: Path) -> bool:
    """Check if a file has mixed line endings (both CRLF and LF)."""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            has_crlf = b'\r\n' in content
            has_lf = b'\n' in content and b'\r\n' not in content
            return has_crlf and has_lf
    except Exception:
        return False


def fix_line_endings(filepath: Path, dry_run: bool = False) -> bool:
    """Convert CRLF line endings to LF."""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Check if file has CRLF
        if b'\r\n' not in content:
            return False
        
        # Replace CRLF with LF
        new_content = content.replace(b'\r\n', b'\n')
        
        # Only write if content changed
        if new_content != content:
            if not dry_run:
                with open(filepath, 'wb') as f:
                    f.write(new_content)
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def should_skip_dir(dirpath: Path) -> bool:
    """Check if a directory should be skipped."""
    return dirpath.name in SKIP_DIRS or dirpath.name.startswith('.')


def process_file(filepath: Path, dry_run: bool = False, force: bool = False) -> bool:
    """Process a single file."""
    # Skip directories
    if filepath.is_dir():
        return False
    
    # Check if it's a text file
    if not is_text_file(filepath):
        # If not in TEXT_EXTENSIONS, check if it's a binary file
        if not force and is_binary_file(filepath):
            return False
    
    # Check if file has CRLF line endings
    if not has_crlf(filepath):
        return False
    
    # Fix line endings
    if fix_line_endings(filepath, dry_run):
        return True
    
    return False


def scan_and_fix(root_dir: Path, dry_run: bool = False, force: bool = False) -> tuple:
    """Scan and fix line endings in all files."""
    total_files = 0
    crlf_files = 0
    fixed_files = 0
    skipped_files = 0
    errors = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Skip directories
        dirs[:] = [d for d in dirs if not should_skip_dir(Path(root) / d)]
        
        for filename in files:
            filepath = Path(root) / filename
            total_files += 1
            
            # Process file
            try:
                if has_crlf(filepath):
                    crlf_files += 1
                    if process_file(filepath, dry_run, force):
                        fixed_files += 1
                        action = "FIXED" if not dry_run else "WOULD FIX"
                        print(f"  [{action}] {filepath.relative_to(root_dir)}")
                else:
                    skipped_files += 1
            except Exception as e:
                errors += 1
                print(f"  [ERROR] {filepath.relative_to(root_dir)}: {e}")
    
    return total_files, crlf_files, fixed_files, skipped_files, errors


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix line endings to LF for Rocket Simulator Pro"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would be changed without modifying files"
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help="Force conversion even if file appears to be binary"
    )
    parser.add_argument(
        '--dir',
        default='.',
        help="Directory to process (default: current directory)"
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help="Show verbose output"
    )
    
    args = parser.parse_args()
    
    root_dir = Path(args.dir).resolve()
    
    print("=" * 60)
    print("Fix Line Endings - Rocket Simulator Pro")
    print("=" * 60)
    print(f"Directory: {root_dir}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Force: {args.force}")
    print()
    
    # Scan and fix
    total, crlf, fixed, skipped, errors = scan_and_fix(
        root_dir, 
        dry_run=args.dry_run, 
        force=args.force
    )
    
    # Print summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total files scanned: {total}")
    print(f"Files with CRLF: {crlf}")
    print(f"Files fixed: {fixed}")
    print(f"Files skipped: {skipped}")
    print(f"Errors: {errors}")
    print("=" * 60)
    
    if args.dry_run and crlf > 0:
        print()
        print("To fix these files, run:")
        print("  python scripts/fix_line_endings.py")
    
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
