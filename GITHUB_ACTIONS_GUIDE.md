# GitHub Actions & Versioning Quick Start Guide

## 🚀 What's New?

Your project now has **fully automated CI/CD**:
- ✅ Automatic `.exe` builds on every release
- ✅ GitHub Release creation with downloads
- ✅ Semantic versioning (MAJOR.MINOR.PATCH)
- ✅ Dev build testing on demand

---

## 📋 How to Create a Release

### **Step 1: Make Your Code Changes**

```bash
git add .
git commit -m "feat: add new dashboard features"
git push origin pyqt-gui
```

### **Step 2: Update Version** (optional but recommended)

Edit [version.py](../version.py):
```python
__version__ = "1.0.0"  # Update to your version
```

Or update in your main module:
```python
__version__ = "1.0.0"
```

### **Step 3: Create a Version Tag**

Using git command:
```bash
git tag v1.0.0
git push origin v1.0.0
```

Or in VS Code:
1. Open **Source Control** panel (Ctrl+Shift+G)
2. Click **Tags** dropdown
3. Enter tag name: `v1.0.0`
4. Push to remote

### **Step 4: GitHub Actions Automatically**

✨ This happens automatically:
1. **Build Phase** (~5-10 min)
   - Installs Python 3.12
   - Installs all dependencies
   - Runs PyInstaller to build .exe
   - Creates distribution .zip

2. **Release Phase** (~30 sec)
   - Creates GitHub Release
   - Uploads `.exe` file
   - Uploads `.zip` archive
   - Generates release notes

3. **Monitor Progress**
   - Go to **Actions** tab in GitHub
   - Watch the workflow run
   - See step-by-step output

---

## 📦 What Users Download

After release, users can download from:
- **GitHub Releases Page**: https://github.com/Niconikun/Rocket-Simulator-25/releases

Files available:
- `RocketSimulator.exe` - Standalone executable
- `RocketSimulator-windows.zip` - Full bundle with dependencies

---

## 🧪 Manual Development Builds

To test builds without creating a release:

1. Go to **Actions** tab → **Dev Build (Manual Testing)**
2. Click **Run workflow** (blue button)
3. Wait for build to complete (~10 min)
4. Download artifacts under **Artifacts** section
5. Artifacts keep for 7 days

This is useful for:
- Testing build before release
- Creating scheduled development builds
- Validating code changes

---

## 📝 Version Format

Use **Semantic Versioning**:

```
v MAJOR . MINOR . PATCH
v   1   .   0   .   0
```

| Component | Increment When | Example |
|-----------|---|---------|
| **MAJOR** | Breaking changes, major feature | v1.0.0 → v2.0.0 |
| **MINOR** | New features (backward compatible) | v1.0.0 → v1.1.0 |
| **PATCH** | Bug fixes, small improvements | v1.0.0 → v1.0.1 |

Examples:
- `v0.1.0` - Initial alpha release
- `v1.0.0` - First stable release
- `v1.1.0` - New features added
- `v1.1.1` - Bug fix

---

## 🔍 Monitoring Builds

### **Real-time View**
1. Push a tag or trigger workflow
2. Go to **Actions** tab
3. Click running workflow
4. Watch each step execute

### **View Past Releases**
- **Actions** tab: See all workflow runs
- **Releases** tab: See published releases

### **Troubleshooting**

If a build fails:
1. Click the failed workflow
2. Scroll to failed step
3. Read error message
4. Common issues:
   - Missing dependencies → Update `requirements.txt`
   - Import errors → Check module paths
   - File not found → Verify data files in spec

---

## 🔧 File Structure

```
.github/
  workflows/
    build-exe.yml      ← Main release workflow
    dev-build.yml      ← Dev testing workflow

version.py            ← Version configuration
RELEASES.md          ← Release documentation
build_exe.py         ← Local build script
build_exe.spec       ← PyInstaller configuration
requirements.txt     ← Python dependencies
```

---

## 💡 Pro Tips

### **Automatic Release Notes**
The workflow auto-generates release notes with:
- Version number
- Installation instructions
- System requirements
- What's included

### **Multiple Releases**
You can have multiple versions active:
- v1.0.0 (stable)
- v1.1.0-beta (testing)
- v2.0.0 (development)

Users can choose which to download.

### **Rollback**
Need to revert a release?
1. Delete the problematic tag
2. Delete the GitHub Release
3. Fix the code
4. Create new tag with patch version (e.g., v1.0.1)

### **Schedule Releases**
To automate releases on schedule, modify **build-exe.yml**:
```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday midnight
```

---

## 📋 Checklist for Each Release

- [ ] Code changes tested locally
- [ ] Version number updated in `version.py`
- [ ] Commit message is descriptive
- [ ] All files committed and pushed
- [ ] Create version tag (e.g., `v1.0.0`)
- [ ] Push tag to GitHub
- [ ] Monitor Actions workflow
- [ ] Verify release appears in Releases tab
- [ ] Test download and run .exe
- [ ] Update README with new version

---

## 🆘 Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "Tag already exists" | Use a new version (e.g., v1.0.1 instead of v1.0.0) |
| Build fails | Check Actions tab → Error message. Usually dependency or import issue |
| .exe too large | Normal! (~200-400 MB with all dependencies) |
| Slow first build | First PyInstaller run downloads symbols. Later builds faster |
| Release created but no files | Check "Upload Assets" step in Actions for errors |

---

## Next Steps

1. **Try a test release**:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

2. **Monitor the build** in Actions tab

3. **Download from Releases** and test the .exe

4. **Email this guide** to your team so they know the workflow

---

## 📚 Additional Resources

- [Semantic Versioning](https://semver.org/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [PyInstaller Docs](https://pyinstaller.org/)
- [Release Management Best Practices](https://github.blog/2021-04-22-release-management-best-practices/)

---

**Questions?** Check `RELEASES.md` for more detailed information about releases and versioning.
