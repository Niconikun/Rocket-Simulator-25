# Building Rocket Simulator Pro as an Executable

This guide explains how to create a standalone Windows executable from the PyQt6 application.

## Prerequisites

- Python 3.8+ installed
- Project files downloaded/cloned
- All dependencies installed from `requirements.txt`

## Option 1: Quick Build (Distribution Folder)

The default build creates a folder with the executable and all dependencies.

### Step 1: Install PyInstaller

```bash
pip install PyInstaller>=6.0.0
```

### Step 2: Build the Executable

Navigate to the project directory:

```bash
cd d:\Documents\GitHub\Rocket-Simulator---GUI
```

Build using the provided spec file:

```bash
pyinstaller build/build.spec
```

### Step 3: Find Your Executable

After building, the executable will be in:

```
dist/RocketSimulator/RocketSimulator.exe
```

### Step 4: Run the Executable

Double-click `RocketSimulator.exe` to launch the application. **No Python installation required on target machine!**

To run from command line:

```bash
dist\RocketSimulator\RocketSimulator.exe
```

## Option 2: Single-File Executable (Larger but More Portable)

For a single `.exe` file without a folder:

### Step 1-2: Same as Above

### Step 3: Modify build.spec

Edit `build/build.spec` and change the `EXE` section:

From:
```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    []
    ...
)
```

To add `--onefile` functionality, rebuild with:

```bash
pyinstaller build/build.spec --onefile
```

Or modify `build.spec` permanently:

```python
# Around line 50, find onedir=False and set to True for single file
# Note: One-file executables are slower to start and larger
```

## Option 3: Advanced Build with Customization

For Windows icon and other customizations, edit `build/build.spec`:

### Add Application Icon

1. Create or get a `.ico` file (e.g., `static/rocket.ico`)
2. Update `build.spec`:

```python
exe = EXE(
    ...
    icon='static/rocket.ico',  # Add this line
    ...
)
```

### Exclude Unused Modules

To reduce executable size, update `excludedimports`:

```python
excludedimports=[
    'streamlit',
    'jupyter',
    'IPython',
    # Add other unused modules
],
```

### Add More Data Files

To include additional files (docs, config templates, etc.):

```python
datas=datas + [
    ('data', 'data'),
    ('docs', 'docs'),
    ('templates', 'templates'),
],
```

## Troubleshooting

### "ModuleNotFoundError" When Running Executable

**Solution**: Add the module to `hidden_imports` in `build.spec`:

```python
hidden_imports = [
    'PyQt6',
    'missing_module_name',  # Add here
    ...
]
```

Then rebuild:
```bash
pyinstaller build/build.spec
```

### "DLL not found" or "Library not found"

**Solution**: Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
pip install --upgrade pip
pip install --upgrade setuptools
```

Then rebuild.

### Executable Runs Slowly

**Solutions**:
1. Use folder mode instead of one-file (faster startup)
2. Check antivirus - may be scanning executable on first run
3. Remove unused modules from collector

### Large File Size

**Solutions**:
1. Use one-file mode (more compressed)
2. Remove unused packages from `hidden_imports`
3. Exclude development tools from distribution
4. Compress with UPX (if not already enabled)

```bash
# Install UPX compression
# Windows: Download from https://upx.github.io/
# Then set: upx_exclude=[] to upx_exclude=['vcruntime140.dll']
```

## Distribution Package Creation

To create a distributable package:

### Step 1: Create Distribution Folder

```bash
mkdir RocketSimulatorPro
xcopy dist\RocketSimulator RocketSimulatorPro\bin /E /I
```

### Step 2: Add Documentation

```bash
copy README.md RocketSimulatorPro\
copy PYQT_MIGRATION.md RocketSimulatorPro\
copy LICENSE RocketSimulatorPro\
```

### Step 3: Create Launcher Batch File

Create `RocketSimulatorPro/RocketSimulator.bat`:

```batch
@echo off
REM Rocket Simulator Pro Launcher
cls
echo Starting Rocket Simulator Pro...
start "" "bin\RocketSimulator.exe"
```

### Step 4: Package for Distribution

```bash
# Create ZIP archive
tar -czf RocketSimulatorPro_v2.0_Windows.zip RocketSimulatorPro/

# Or use Windows: Right-click folder → Send to → Compressed folder
```

## Deployment

### For End Users

1. Extract `RocketSimulatorPro.zip`
2. Double-click `RocketSimulator.exe` (or `RocketSimulator.bat`)
3. No installation or Python required!

### For Network Deployment

1. Copy `RocketSimulatorPro` folder to network share
2. Create desktop shortcut pointing to `bin\RocketSimulator.exe`
3. Users run from shortcut

### For Installer (Advanced)

Use NSIS or Inno Setup to create professional installer:

```bash
# Example with Inno Setup:
# Create installer script (.iss) pointing to RocketSimulatorPro folder
# Compile with Inno Setup compiler
# Generates: RocketSimulatorPro_v2.0_Setup.exe
```

## Verification

After building, verify the executable:

### Test Basic Functionality

```bash
# Run with basic test
dist\RocketSimulator\RocketSimulator.exe

# Check it launched without errors
# Run the application and test each tab
```

### Check File Integrity

```bash
# List contents
dir dist\RocketSimulator

# Check size (should be 500-800 MB for folder mode)
```

### Test on Different Machine

Copy the `dist/RocketSimulator` folder to another computer and test.

## Continuous Building (Automation)

Create `build_app.bat` script to automate building:

```batch
@echo off
echo Building Rocket Simulator Pro...
cd /d %~dp0
pip install -r requirements.txt
pyinstaller build/build.spec
echo.
echo Build complete!
echo Executable: dist\RocketSimulator\RocketSimulator.exe
pause
```

Run with:
```bash
build_app.bat
```

## Performance Tips

1. **Remove unused PyQt6 modules** - Reduces size by 100+ MB
2. **Use UPX compression** - Enabled by default, reduces size ~30%
3. **Folder mode** - Faster startup than one-file mode
4. **Update Setuptools** - `pip install --upgrade setuptools wheel`

## Advanced: Creating Update System

For automatic updates:

1. Create version check in `main.py`:
```python
if check_for_updates():
    show_update_dialog()
```

2. Download new executable to temp folder
3. Replace running executable on next launch
4. Or create separate update utility

## Support

If build fails:
1. Check `build.log` for detailed error messages
2. Run with verbose output: `pyinstaller --debug=all build/build.spec`
3. Verify all dependencies: `pip list`
4. Clear cache: `rm -rf build dist` then rebuild

## Summary

| Method | Size | Speed | Compatibility |
|--------|------|-------|----------------|
| Folder (default) | 500-800 MB | Fast ⚡ | Windows 7+ |
| One-file | 400-600 MB | Slow | Windows 7+ |
| Professional Installer | Varies | - | Best UX |

---

**Default Recommendation**: Use folder mode for development/testing, one-file for distribution.

For most users: `pyinstaller build/build.spec` → `dist/RocketSimulator/RocketSimulator.exe`
