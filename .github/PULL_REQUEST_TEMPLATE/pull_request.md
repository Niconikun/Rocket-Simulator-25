---
name: Pull Request
about: Submit changes for review
labels: ''
assignees: ''

---

## ✨ Pull Request

Thank you for your contribution! Please fill out the form below to help us review your changes.

### ✅ Checklist

Before submitting, please verify that you've completed the following:

- [ ] **Code Changes**:
  - [ ] My code follows the project's [coding standards](CONTRIBUTING.md#coding-standards)
  - [ ] I have performed a self-review of my own code
  - [ ] My changes are focused and address a single issue or feature

- [ ] **Testing**:
  - [ ] I have added tests that prove my fix is effective or that my feature works
  - [ ] All existing tests pass locally with my changes
  - [ ] I have run linting (`black --check .`, `flake8 .`, `mypy .`)

- [ ] **Documentation**:
  - [ ] I have updated documentation as needed
  - [ ] I have updated the [CHANGELOG.md](CHANGELOG.md) with my changes
  - [ ] I have added/updated docstrings for new/changed functions

- [ ] **Git Hygiene**:
  - [ ] My commits follow the [commit message guidelines](CONTRIBUTING.md#commit-message-guidelines)
  - [ ] My branch is up-to-date with the target branch (usually `pyqt-gui` or `master`)
  - [ ] I have squashed or rebased my commits as needed

### 📋 Description

**What does this PR do?**
A clear and concise description of the changes in this pull request.

**Related Issues:**
- Closes: #XXXX
- Fixes: #XXXX
- Addresses: #XXXX

### 🎯 Type of Change

Please select the type(s) of changes in this PR:

- [ ] **Bug fix** (non-breaking change which fixes an issue)
- [ ] **New feature** (non-breaking change which adds functionality)
- [ ] **Breaking change** (fix or feature that would cause existing functionality to not work as expected)
- [ ] **Documentation update** (changes to documentation only)
- [ ] **Code refactoring** (changes that don't affect functionality)
- [ ] **Performance improvement** (changes that improve performance)
- [ ] **Build/CI related changes** (changes to build process, CI/CD, dependencies)
- [ ] **Tests only** (adding or updating tests)
- [ ] **Other** (please describe below):

### 📝 Details

**Changes Made:**
- Change 1: Description
- Change 2: Description
- Change 3: Description

**Motivation:**
Why are these changes needed? What problem do they solve?

**Approach:**
How did you implement these changes? Any design decisions or trade-offs?

### 🧪 Testing

**Tests Added:**
- List any new tests you've added

**Tests Modified:**
- List any tests you've modified

**Test Results:**
```bash
# Example: pytest tests/models/test_rocket.py -v
# Output showing all tests passing
```

### 📊 Impact

**Breaking Changes:**
If this PR introduces breaking changes, please describe them and how users should migrate:

**Performance Impact:**
Does this PR affect performance? If so, please describe:
- [ ] No performance impact
- [ ] Improves performance (describe how)
- [ ] May degrade performance (describe impact)

**Dependencies:**
Does this PR add, remove, or change any dependencies?
- [ ] No dependency changes
- [ ] Adds: list new dependencies
- [ ] Removes: list removed dependencies
- [ ] Updates: list updated dependencies

### 🖼️ Screenshots / Examples

If applicable, add screenshots or examples to demonstrate your changes:

**Before:**
![Before screenshot]

**After:**
![After screenshot]

**Example Usage:**
```python
# Code example showing how to use the new feature
```

### 🔍 Review Notes

**Areas of Concern:**
Are there any parts of this PR that you'd like reviewers to pay special attention to?

**Open Questions:**
Are there any open questions or discussions you'd like to have about this PR?

### 📚 Additional Context

Any other relevant information, context, or background that reviewers should know:

---

**Thank you for your contribution!** 🎉

By submitting this pull request, you agree to license your contributions under the [MIT License](LICENSE).
