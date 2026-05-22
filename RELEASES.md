# Versioning & Release Guide

## Version Format

This project uses **Semantic Versioning** (semver): `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes, major features
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, small improvements

Example: `v1.2.3`

## Release Process

### 1. **Update Version** (in code/files)

Update version in these files if applicable:
- `__version__` in main module 
- `setup.py` or `pyproject.toml` (if you create one)
- `README.md` (release notes section)

### 2. **Create Git Tag**

```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

Or manually in VS Code:
- Open Source Control → Tags
- Create new tag: `v1.0.0`
- Push tag to GitHub

### 3. **GitHub Actions Runs Automatically**

When you push a tag matching `v*.*.*`:
- ✅ Installs all dependencies
- ✅ Builds the .exe using PyInstaller
- ✅ Creates a GitHub Release
- ✅ Uploads .exe and .zip to the release
- ⏱️ Build takes ~10-15 minutes

### 4. **Manual Release (Workflow Dispatch)**

If needed, trigger a manual build:
- Go to Actions → Build & Release EXE
- Click "Run workflow"
- Enter version number (e.g., `1.0.0`)
- Watch the build progress

## Accessing Releases

Users can download from:
- **GitHub**: Releases tab on your repository
- **Direct link**: `https://github.com/{owner}/Rocket-Simulator---GUI/releases`

## Release Notes Template

```markdown
## v1.0.0 - 2026-03-30

### New Features
- [ ] Feature description

### Bug Fixes
- [ ] Fix description

### Dependencies
- PyQt6 6.x
- NumPy, SciPy, Pandas
- Matplotlib, PyVista

### Installation
Windows users can now download `RocketSimulator.exe` and run without Python!
```

## CI/CD Pipeline Status

Monitor builds: **Actions** tab in GitHub

Check for:
- ✅ Build succeeded
- ✅ Tests passed (if added)
- ✅ Release created
- ✅ Assets uploaded

## Future Enhancements

To add to the workflow:
- [ ] Add version auto-increment
- [ ] Add changelog generation
- [ ] Add code signing for .exe
- [ ] Add installer (.msi) creation
- [ ] Add macOS/Linux builds
