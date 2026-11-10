# Contributing to Rocket Simulator Pro

First off, thank you for considering contributing to Rocket Simulator Pro! Your contributions help make this project better for everyone.

## 📋 Table of Contents

- [How Can I Contribute?](#how-can-i-contribute)
- [Setting Up Your Development Environment](#setting-up-your-development-environment)
- [Coding Standards](#coding-standards)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Testing](#testing)
- [Documentation](#documentation)
- [Code Review Process](#code-review-process)
- [Community Guidelines](#community-guidelines)

---

## 🤔 How Can I Contribute?

There are many ways to contribute to Rocket Simulator Pro:

### 🐛 Bug Reports
- Report bugs and issues you encounter
- Help verify and reproduce reported issues

### 💡 Feature Requests
- Suggest new features or enhancements
- Discuss potential improvements

### 📝 Documentation
- Improve existing documentation
- Add new documentation and tutorials
- Update examples and use cases

### 🔧 Code Contributions
- Fix bugs
- Implement new features
- Improve performance
- Refactor existing code

### ⚡ Testing
- Write unit tests
- Write integration tests
- Test on different platforms

### 🌍 Translations
- Add new language translations
- Improve existing translations

### 🎨 UI/UX Improvements
- Improve the user interface
- Enhance user experience
- Add visualizations

### 📊 Data & Configuration
- Add new rocket configurations
- Create test scenarios
- Provide real-world data

---

## 🚀 Setting Up Your Development Environment

### Prerequisites

- Python 3.12 or later
- Git
- pip (Python package manager)

### Installation

1. **Fork the repository**
   ```bash
   git clone https://github.com/Niconikun/Rocket-Simulator---GUI.git
   cd Rocket-Simulator---GUI
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

   Or using conda:
   ```bash
   conda env create -n rocket-sim -f environment.yml
   conda activate rocket-sim
   ```

4. **Verify the installation**
   ```bash
   python main.py
   ```

### Optional Dependencies

- **STL Import**: `pip install trimesh`
- **Advanced Visualization**: `pip install pyvista plotly folium`
- **Type Checking**: `pip install mypy pandas-stubs numpy-stubs`

---

## 📐 Coding Standards

### Python Style

We follow [PEP 8](https://peps.python.org/pep-0008/) with some modifications:

- **Line Length**: 120 characters maximum
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Grouped by type (standard library, third-party, local)
- **Naming**:
  - `snake_case` for variables and functions
  - `CamelCase` for classes
  - `UPPER_CASE` for constants
  - `snake_case` for files and directories

### Code Formatting

We use **Black** for automatic code formatting:

```bash
black . --line-length 120 --exclude "(build|dist|__pycache__|.venv)"
```

### Linting

We use **Flake8** for linting:

```bash
flake8 . --max-line-length 120 --exclude "(build|dist|__pycache__|.venv)"
```

### Type Hints

Type hints are **required** for all public functions and methods:

```python
def calculate_trajectory(rocket: Rocket, environment: Environment) -> Trajectory:
    """Calculate rocket trajectory.
    
    Args:
        rocket: The rocket configuration
        environment: Environmental conditions
        
    Returns:
        Calculated trajectory
    """
    pass
```

### Docstrings

All public functions, classes, and modules should have docstrings following the [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings):

```python
def calculate_drag(coefficient: float, velocity: float, area: float) -> float:
    """Calculate drag force using standard formula.
    
    Args:
        coefficient: Drag coefficient (dimensionless)
        velocity: Velocity in m/s
        area: Reference area in m²
        
    Returns:
        Drag force in Newtons
        
    Raises:
        ValueError: If velocity or area is negative
    """
    if velocity < 0:
        raise ValueError("Velocity cannot be negative")
    if area < 0:
        raise ValueError("Area cannot be negative")
    return 0.5 * coefficient * velocity**2 * area
```

### Error Handling

- Use specific exception types when possible
- Always include meaningful error messages
- Log errors appropriately (DEBUG, INFO, WARNING, ERROR, CRITICAL)

```python
try:
    result = simulate_flight(rocket)
except SimulationError as e:
    logger.error(f"Simulation failed for rocket {rocket.name}: {e}")
    raise
```

---

## 📝 Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): subject

body

footer
```

### Commit Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc.)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests
- `chore`: Changes to the build process or auxiliary tools and libraries such as documentation generation
- `revert`: Revert a previous commit

### Examples

```bash
feat(simulation): add Monte Carlo analysis with statistical aggregation

- Add MonteCarloRunner class for parallel simulations
- Add MonteCarloAggregator for result analysis
- Add histograms and scatter plots for visualization
- Update UI with Monte Carlo tab

Closes #123
```

```bash
fix(aerodynamics): correct drag coefficient calculation for supersonic flow

The previous implementation used incorrect compressibility corrections
for Mach numbers > 1. This fix implements the Prandtl-Glauert rule
properly.

Fixes #456
```

```bash
refactor(models): extract rocket state into separate class

- Create RocketState class to manage rocket state
- Move state-related logic from Rocket class
- Improve separation of concerns
- No functional changes
```

### Commit Message Structure

1. **Type and Scope**: Always include type and optional scope
2. **Subject**: Brief description (50 characters or less)
3. **Body**: Detailed explanation (72 characters per line)
4. **Footer**: Reference issues, breaking changes, etc.

---

## 🔄 Pull Request Process

1. **Fork the repository** and create a new branch from `master` or `pyqt-gui`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards

3. **Run tests** to ensure nothing is broken
   ```bash
   pytest tests/ -v
   ```

4. **Run linting**
   ```bash
   black --check .
   flake8 .
   mypy . --ignore-missing-imports
   ```

5. **Update documentation** if applicable

6. **Update CHANGELOG.md** with your changes

7. **Push your changes**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request**
   - Use a clear, descriptive title
   - Include a detailed description of your changes
   - Reference any related issues
   - Follow the PR template if available

9. **Address review comments** and update your PR as needed

10. **Wait for approval** and merge!

### Pull Request Template

```markdown
## Description

Please include a summary of the change and which issue is fixed. Please also include relevant motivation and context.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code refactoring
- [ ] Performance improvement
- [ ] Build/CI related changes
- [ ] Other (please describe):

## Testing

Describe the tests you've added or the testing you've done to verify your changes.

- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Manual testing performed
- [ ] All existing tests pass

## Checklist

- [ ] My code follows the project's coding standards
- [ ] I have performed a self-review of my own code
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

---

## 🐛 Reporting Bugs

When reporting a bug, please include:

1. **Python version** (`python --version`)
2. **Operating system** (Windows, Linux, macOS)
3. **Steps to reproduce** the issue
4. **Expected behavior**
5. **Actual behavior**
6. **Screenshots or logs** (if applicable)
7. **Error messages** (if any)

### Bug Report Template

```markdown
## Description

A clear and concise description of what the bug is.

## Steps to Reproduce

1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior

A clear description of what you expected to happen.

## Actual Behavior

A clear description of what actually happened.

## Screenshots

If applicable, add screenshots to help explain your problem.

## Additional Context

- Python version:
- Operating system:
- Rocket Simulator version:
- Any other relevant information:
```

---

## 💡 Suggesting Features

When suggesting a new feature, please include:

1. **Detailed description** of the feature
2. **Use case** and why it's needed
3. **Potential implementation** ideas (if you have any)
4. **Examples** or mockups (if applicable)

### Feature Request Template

```markdown
## Feature Description

A clear and concise description of the feature you'd like to see.

## Motivation

Why is this feature important? What problem does it solve?

## Proposed Solution

Describe your proposed solution or implementation approach.

## Alternatives Considered

Are there any alternative approaches or existing workarounds?

## Additional Context

Any other relevant information, examples, or mockups.
```

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src --cov=ui --cov=workers --cov-report=html

# Run specific test file
pytest tests/models/test_aerodynamics.py -v

# Run tests with Qt support (for UI tests)
pytest tests/ui/ -v --qt-qapp
```

### Test Structure

- **Unit Tests**: Test individual functions and classes
  - Location: `tests/models/`, `tests/test_utils/`
- **Integration Tests**: Test interactions between components
  - Location: `tests/models/test_simulation_integration.py`
- **UI Tests**: Test PyQt6 widgets and interfaces
  - Location: `tests/ui/`

### Writing Tests

```python
import pytest
from src.models.rocket import Rocket


def test_rocket_initialization():
    """Test that a rocket can be initialized with valid parameters."""
    rocket = Rocket(
        initial_mass=10.0,
        reference_area=0.01,
        I_before_burn={"x": 0.01, "y": 0.1, "z": 0.1}
    )
    
    assert rocket.initial_mass == 10.0
    assert rocket.reference_area == 0.01


def test_rocket_mass_validation():
    """Test that invalid mass raises ValueError."""
    with pytest.raises(ValueError):
        Rocket(initial_mass=-1.0, reference_area=0.01)
```

---

## 📚 Documentation

### Writing Documentation

- Use Markdown for all documentation
- Include code examples where appropriate
- Keep documentation up-to-date with code changes
- Use diagrams for complex concepts

### Documentation Structure

```
docs/
├── EVENT_BUS.md              # Event Bus specification
├── IMPLEMENTATION_EVENT_BUS_STATUS.md  # Event Bus implementation status
├── P3_IMPLEMENTATION.md      # Phase 3 implementation details
├── TRANSLATIONS.md           # Translation guide
└── ...
```

### Updating Documentation

When making changes to the code:

1. **API Changes**: Update relevant documentation files
2. **New Features**: Add documentation for new features
3. **Bug Fixes**: Update documentation if the fix affects usage
4. **Configuration Changes**: Update README.md and other relevant files

---

## 👁️ Code Review Process

### For Contributors

1. **Be patient**: Code reviews can take time
2. **Be responsive**: Address review comments promptly
3. **Be open to feedback**: Reviews are meant to improve code quality, not criticize
4. **Ask questions**: If you don't understand a review comment, ask for clarification

### For Reviewers

1. **Be respectful**: Focus on the code, not the person
2. **Be constructive**: Provide actionable feedback
3. **Be timely**: Try to review PRs within a reasonable timeframe
4. **Be thorough**: Check for bugs, style issues, and edge cases

### Review Checklist

- [ ] Code follows project standards
- [ ] Code is properly documented
- [ ] Tests are added/updated
- [ ] Documentation is updated
- [ ] Changes are backward compatible (or breaking changes are documented)
- [ ] Error handling is adequate
- [ ] Performance implications are acceptable

---

## 👥 Community Guidelines

### Communication

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For general questions and discussions
- **Pull Requests**: For code contributions

### Code of Conduct

Please follow our [Code of Conduct](CODE_OF_CONDUCT.md) in all interactions.

### Recognition

All contributions are valuable and will be recognized:
- Contributors will be listed in the CONTRIBUTORS.md file
- Significant contributions may be highlighted in release notes
- All contributors retain copyright to their contributions

---

## 🎉 Getting Started with Your First Contribution

If you're new to open source or this project, here are some good first issues:

1. **Good First Issues**: Look for issues labeled "good first issue"
2. **Documentation**: Help improve existing documentation
3. **Tests**: Add tests for untested code
4. **Bug Fixes**: Fix reported bugs
5. **Translations**: Add or improve translations

### Steps for Your First Contribution

1. **Find an issue** you'd like to work on
2. **Comment on the issue** to let others know you're working on it
3. **Fork the repository** and create a branch
4. **Make your changes** following the guidelines above
5. **Test your changes**
6. **Submit a Pull Request**
7. **Address feedback** from reviewers
8. **Get your PR merged!**

---

## 📞 Getting Help

If you need help with anything:

- **Development Setup**: Check the README.md and this file
- **Code Questions**: Open a GitHub Discussion
- **Bug Reports**: Open a GitHub Issue
- **Feature Requests**: Open a GitHub Issue
- **Code of Conduct Issues**: Contact project maintainers privately

---

## 🙏 Thank You!

Thank you for your interest in contributing to Rocket Simulator Pro! Your contributions help make this project better for everyone in the rocket simulation community.

Happy coding! 🚀
