# Deletion Candidates Analysis

**Date:** March 26, 2026  
**Analysis:** Identify unused/redundant files for cleanup

---

## Summary
**Total candidates: 26 files + 2 directories**

---

## CATEGORY 1: OLD TEST FILES (7 files)
These are experimental test files located in root directory, not part of the formal /tests/ suite.

```
[ ] test_new_features.py                   - Experimental feature testing
[ ] test_physics_integration.py            - Old physics integration test
[ ] test_quaternion_stability.py           - Quaternion stability testing
[ ] test_rocket_widget.py                  - Old PyQt widget tests
[ ] test_rocket_widget_integration.py      - Old integration tests
[ ] test_stability_improved.py             - Stability test variant
[ ] demonstrate_rocket_widget.py           - Demo script (old)
```

**Rationale:** Proper tests are in `/tests/models/` and `/tests/test_utils/`. These appear to be development artifacts from PyQt6 migration.

---

## CATEGORY 2: EXPERIMENTAL/DEPRECATED SCRIPTS (4 files)
Utility scripts that appear to be one-off diagnostics or old versions.

```
[ ] verify_dashboard.py                    - Dashboard verification script
[ ] update_widget.py                       - Widget update utility
[ ] diagnose_plotly_map.py                 - Plotly diagnostics
[ ] streamlit_app.py                       - OLD: Streamlit version (replaced by main.py)
```

**Rationale:** main.py is the current PyQt6 entry point. These scripts don't appear in documentation as active tools.

---

## CATEGORY 3: OUTDATED DOCUMENTATION (9 files)
Migration guides and old implementation notes that are no longer relevant.

```
[ ] CHANGES_ROCKET_WIDGET.md               - Old widget changes log
[ ] PYQT_MIGRATION.md                      - PyQt6 migration guide (completed)
[ ] PyQt6_IMPLEMENTATION_SUMMARY.md        - Implementation summary (archived)
[ ] PLOTLY_MAP_VERIFICATION.md             - Plotly verification (old)
[ ] VERIFICATION_CHECKLIST.md              - Old verification checklist
[ ] WIDGET_REFERENCE.txt                   - Old widget reference
[ ] BUILD_INSTRUCTIONS.md                  - Old build instructions
[ ] GENERAR_EJECUTABLE.md                  - Spanish version (old)
[ ] DEVELOPER_REFERENCE.md                 - Replaced by DEVELOPER_QUICK_REFERENCE.md
```

**Rationale:** These document historical migration/implementation. Current guides are:
- README.md (active)
- DEVELOPER_QUICK_REFERENCE.md (current)
- TEST_MODELS_GUIDE.md (current)
- CODE_REVIEW.md (current)
- COMPLETION_REPORT.md (current)
- REVIEW_SUMMARY.md (current)

---

## CATEGORY 4: LOG FILES (2 files)
Build and runtime logs.

```
[ ] build_log.txt                          - Old build log
[ ] rocket_simulator.log                   - Runtime log (regenerated)
```

**Rationale:** Logs are regenerated at runtime. No operational data lost.

---

## CATEGORY 5: BUILD AUTOMATION FILES (3 files)
PyInstaller configuration for executable builds (can be regenerated if needed).

```
[ ] build_exe.bat                          - Windows batch build script
[ ] build_exe.py                           - Python build script
[ ] build_exe.spec                         - PyInstaller spec file
```

**Rationale:** These are for creating .exe executables. Can be recreated if distribution is needed.

---

## CATEGORY 6: BUILD ARTIFACT DIRECTORIES (2 dirs)
Compiled/distributed output artifacts.

```
[ ] build/                                 - PyInstaller build directory
[ ] dist/                                  - Distribution artifacts directory
[ ] __pycache__/                           - Python cache (auto-generated)
```

**Rationale:** Auto-generated during build. Can be recreated with `python build_exe.py`.

---

## FILES TO KEEP (Essential)

✅ **Active Documentation:**
- README.md
- DEVELOPER_QUICK_REFERENCE.md
- TEST_MODELS_GUIDE.md
- CODE_REVIEW.md
- REVIEW_SUMMARY.md
- COMPLETION_REPORT.md

✅ **Active Source Code:**
- main.py (current PyQt6 entry point)
- src/ (core physics engine)
- models/ (Streamlit pages)
- pages/ (PyQt pages)
- ui/ (PyQt UI components)
- workers/ (simulation workers)
- tests/ (test suite)

✅ **Configuration:**
- requirements.txt (dependencies)
- .streamlit/ (Streamlit config)
- .env (environment)
- .gitignore

✅ **Data:**
- data/ (rocket configs, simulation data)

---

## CLEANUP IMPACT

**Space Saved:** ~50-100 MB (mostly build/ and dist/)
**Risk:** Very Low - no active code references these files
**Recovery:** All files are in git history if needed later

---

## RECOMMENDATION

**Safe to delete immediately:**
- All 7 old test files (Category 1)
- All 4 experimental scripts (Category 2)
- All 9 documentation files (Category 3)
- Both log files (Category 4)
- **Subtotal: 22 files - Very Low Risk**

**Conditional deletion (ask user):**
- Build files (Category 5) - Keep if plan to distribute .exe
- Build directories (Category 6) - Safe to delete, recreated on `python build_exe.py`
