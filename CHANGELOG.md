# Rocket Simulator Pro - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-08-07

### Added

#### Splash Screen Improvements
- **Separate module**: Created `ui/splash.py` with dedicated splash screen implementation
- **Progress bar**: Added real-time progress bar at the bottom of splash screen
- **Status messages**: Dynamic loading messages during initialization
- **SplashManager**: Class for managing multi-step initialization with automatic progress tracking
- **Programmatic drawing**: No external image dependencies, all graphics drawn with Qt
- **Theme support**: Dark and light theme variants for splash screen
- **Centered positioning**: Splash screen automatically centers on primary display

#### Dark Mode Support
- **Toggle menu**: Added "Dark Mode" option in View menu (checkable)
- **Complete palette**: Full dark theme with all Qt color roles configured
- **Comprehensive stylesheet**: CSS styling for all widget types (buttons, inputs, tables, etc.)
- **Light theme**: Added explicit light theme with complete styling
- **Persistence**: Dark mode preference saved in application state
- **Auto-apply**: Theme automatically applied on application startup

#### Application State Enhancements
- **Improved persistence**: Automatic save/load of application state to/from JSON
- **Session management**: Auto-save on application exit, auto-load on startup
- **Backup system**: Session files are backed up with timestamps before saving
- **Testing support**: Added `hard_reset()` and `reset_instance()` methods for clean state in tests
- **Nested object serialization**: Better handling of complex objects (dicts, lists, dates, datetimes)
- **Compatibility**: Maintains backward compatibility with existing state files

#### CI/CD Pipeline
- **Unified workflow**: Created `.github/workflows/ci-cd.yml` replacing multiple redundant workflows
- **Continuous Integration**: Automatic testing on push and pull requests
  - Linting with flake8
  - Type checking with mypy
  - Tests with pytest
  - Code formatting check with black
- **Continuous Delivery**: Automatic build and release on version tags
  - Builds Windows executable with PyInstaller
  - Creates ZIP distribution archive
  - Publishes GitHub Release with artifacts
- **Manual build**: Support for manual triggering via workflow_dispatch
- **Concurrency control**: Cancels previous runs of the same workflow
- **Artifact upload**: Test results and build artifacts available for download

#### Performance Optimizations
- **Simulation caching**: Added `workers/simulation_cache.py` for Monte Carlo optimizations
  - Rocket configuration cache (avoids repeated file I/O)
  - Planet object cache (reuses objects with same parameters)
  - Atmosphere object cache (reuses for same temperature)
  - Wind model cache (reuses for same configuration)
  - Engine object cache (reuses for same configuration)
- **Thread-safe cache**: Uses locking for concurrent access
- **Cache statistics**: Hit/miss tracking for performance monitoring
- **Automatic cleanup**: Rocket cache cleared after Monte Carlo batch to free memory
- **Configurable limits**: Maximum cache sizes with automatic eviction

#### Code Quality
- **Imports**: Added `requirements-dev.txt` for development dependencies
- **Testing tools**: pytest, pytest-qt, pytest-cov, black, flake8, mypy, pydocstyle
- **Code formatting**: Consistent style with black formatting
- **Type hints**: Added type annotations for better IDE support

### Changed

#### Dependencies
- **Organized requirements**: Categorized dependencies in `requirements.txt`
- **Version pinning**: Added minimum version requirements for all dependencies
- **Environment synchronization**: `environment.yml` now matches `requirements.txt`
- **Optional packages**: Visualization packages (pyvista, plotly, folium) marked as optional

#### Application Structure
- **Cleaner main.py**: Removed inline splash screen code, now uses SplashManager
- **Improved error handling**: Better exception handling with traceback output
- **Better logging**: More informative log messages during startup

#### User Interface
- **Progress feedback**: Users now see loading progress during startup
- **Status bar messages**: Informative messages about theme changes
- **Consistent theming**: All widgets properly styled in both dark and light modes

### Fixed

- **QPoint import**: Corrected import location from `PyQt6.QtGui` to `PyQt6.QtCore`
- **Superclass initialization**: Fixed order of initialization in SplashScreen class
- **ColorRole.Disabled**: Replaced invalid `Disabled` role with `PlaceholderText` for Qt6 compatibility
- **QApplication reference**: Added missing import in main_window.py for app instance access
- **Theme application scope**: Dark mode toggle now applies to entire application, not just main window
- **Light theme palette**: Added explicit light palette instead of relying on system palette
- **Corrupted .gitignore**: Cleaned up .gitignore file with proper formatting

### Removed

- **Redundant workflows**: Removed `build-exe.yml`, `dev-build.yml`, `python-app.yml`, `python-package-conda.yml`
- **Build artifacts**: Removed build directories and log files from repository
- **Duplicate code**: Removed inline splash screen drawing code from main.py

---

## [0.5.7] - 2025-05-22

### Added
- Initial PyQt6 GUI implementation
- 6-DOF physics simulation engine
- Rocket configuration editor with tabs
- Monte Carlo simulation support
- OpenRocket (.ork) import functionality
- STL import support (optional)
- Barrowman stability calculation
- Wind model integration

### Changed
- Migrated from Streamlit to PyQt6
- Improved simulation accuracy
- Enhanced UI/UX design

---

## [0.5.5] - 2025-04-13

### Added
- Basic rocket simulation with 6-DOF dynamics
- Streamlit-based web interface
- JSON configuration support
- Trajectory visualization

---

## [0.3.3] - 2022-10-16

### Added
- Original project by Jorge Orozco
- Basic quaternion-based trajectory prediction
- University of Concepcion foundation

---

## Template for Future Releases

### Added
- New features or functionality

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Vulnerability patches

---

[2.0.0]: https://github.com/Niconikun/Rocket-Simulator-25/compare/v0.5.7...v2.0.0
[0.5.7]: https://github.com/Niconikun/Rocket-Simulator-25/compare/v0.5.5...v0.5.7
[0.5.5]: https://github.com/Niconikun/Rocket-Simulator-25/compare/v0.3.3...v0.5.5
[0.3.3]: https://github.com/Niconikun/Rocket-Simulator-25/releases/tag/v0.3.3
