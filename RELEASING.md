# Release Process

This document describes how to publish a new version of greybeard to PyPI.

## Prerequisites

### One-time PyPI Setup (Trusted Publishing)

greybeard uses PyPI's [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) for secure, token-free releases.

1. **Create the package on PyPI** (first release only):

   ```bash
   # Build locally
   uv pip install build
   python -m build

   # Upload manually with twine (one time only)
   uv pip install twine
   twine upload dist/*
   ```

2. **Configure Trusted Publisher** on PyPI:
   - Go to https://pypi.org/manage/project/greybeard/settings/publishing/
   - Add a new publisher:
     - **PyPI Project Name**: `greybeard`
     - **Owner**: `btotharye` (your GitHub username)
     - **Repository name**: `greybeard`
     - **Workflow name**: `publish.yml`
     - **Environment name**: `pypi`
   - Save

After this one-time setup, all future releases are automatic via GitHub Actions.

---

## Release Workflow

### Version Management

Version is stored in a single location: [`greybeard/__init__.py`](greybeard/__init__.py)

The version is automatically read from there by `pyproject.toml` at build time, so **you only need to update `greybeard/__init__.py`**.

### Quick Start (Using Helper Script)

The easiest way to create a release:

```bash
./release.sh 0.2.0
```

This script will:

1. ✅ Create a release branch (`release-0.2.0`)
2. ✅ Update `greybeard/__init__.py` with the new version
3. ✅ Create/initialize `CHANGELOG.md` (if it doesn't exist)
4. ✅ Commit the version bump
5. ✅ Push the release branch
6. ✅ Open your browser to create a PR

**After the PR is merged:**

```bash
git checkout main
git pull origin main
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

⚠️ **Important**: The git tag must match the version. If `greybeard/__init__.py` has `__version__ = "0.2.0"`, the tag must be `v0.2.0`.

Then create the GitHub Release, and the workflow will automatically validate and publish to PyPI!

---

## Manual Release Workflow

If you prefer manual control, follow these steps:

### 1. Create Release Branch

```bash
git checkout main
git pull origin main
git checkout -b release-0.2.0
```

### 2. Update Version

Edit [`greybeard/__init__.py`](greybeard/__init__.py):

```python
__version__ = "0.2.0"  # Update this
```

Note: `pyproject.toml` automatically reads the version from here, so no manual update is needed there.

### 3. Update Changelog (if present)

If you're maintaining a CHANGELOG.md, add release notes:

```markdown
## [0.2.0] - 2026-03-01

### Added

- New feature X

### Fixed

- Bug Y

### Changed

- Improved Z
```

### 4. Commit and Push Branch

```bash
git add greybeard/__init__.py CHANGELOG.md  # if you have one
git commit -m "chore: bump version to 0.2.0"
git push origin release-0.2.0
```

### 5. Create and Merge PR

1. Go to your repository and create a PR from `release-0.2.0` to `main`
2. Wait for CI to pass
3. Get approval (if required)
4. Merge the PR

### 6. Create and Push Tag

After the PR is merged:

```bash
git checkout main
git pull origin main
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

⚠️ **Important**: The tag version must match `greybeard/__init__.py`. If `__version__ = "0.2.0"`, the tag must be `v0.2.0`.

### 7. Create a GitHub Release

1. Go to https://github.com/btotharye/greybeard/releases/new
2. **Tag**: Select `v0.2.0` (the tag you just pushed)
3. \*8Release title\*\*: `v0.2.0` or `greybeard v0.2.0`
4. **Description**: Summarize changes from CHANGELOG or write release notes
5. Click **Publish release**

### 7. Automatic Publishing with Validation

When you create the GitHub Release, the publishing workflow starts:

1. **Validation**: Checks that `greybeard/__init__.py` version matches the git tag (e.g., both are "0.2.0")
2. **Build**: Creates distribution files (`sdist` and `wheel`) using hatchling
3. **Publish**: Publishes to PyPI using trusted publishing
4. **Done**: New version appears at https://pypi.org/project/greybeard/

If the version mismatch validation fails, the workflow stops and alerts you to fix the discrepancy.

Monitor the workflow at: https://github.com/btotharye/greybeard/actions/workflows/publish.yml

---

## Testing a Release (TestPyPI)

To test the release process without publishing to production PyPI:

### 1. Set up TestPyPI Trusted Publisher (first time only)

1. Go to https://test.pypi.org/manage/project/greybeard/settings/publishing/
2. Add the same trusted publisher configuration as above, but with:
   - **Environment name**: `testpypi`

### 2. Trigger Manual Workflow

Instead of creating a GitHub Release, manually trigger the workflow:

1. Go to https://github.com/btotharye/greybeard/actions/workflows/publish.yml
2. Click **Run workflow**
3. Select your branch
4. Click **Run workflow**

This will publish to TestPyPI only, allowing you to test installation:

```bash
uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ greybeard
```

---

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (`1.0.0` → `2.0.0`): Breaking changes
- **MINOR** (`0.1.0` → `0.2.0`): New features, backward compatible
- **PATCH** (`0.1.0` → `0.1.1`): Bug fixes, backward compatible

---

## Troubleshooting

### "Filename has been previously used"

PyPI doesn't allow re-uploading the same version. Increment the version number.

### "Invalid or non-existent authentication information"

The trusted publisher isn't configured. Follow the "One-time PyPI Setup" section above.

### Workflow fails on `publish-to-pypi` step

Check:

- The `pypi` environment exists in GitHub repo settings
- The trusted publisher is configured on PyPI
- The workflow has `id-token: write` permissions (already configured)

### Want to skip PyPI and only publish to TestPyPI?

Use manual workflow dispatch and modify the workflow to skip the `publish-to-pypi` job.

---

## Quick Reference

**Using the helper script (recommended):**

```bash
./release.sh 0.2.0
# Script updates greybeard/__init__.py, commits, and opens PR
# After PR is merged:
git checkout main
git pull origin main
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
# Create GitHub release when browser opens
# GitHub Actions validates version match, builds, and publishes
```

**Manual approach:**

```bash
# 1. Create release branch
git checkout main
git pull origin main
git checkout -b release-0.2.0

# 2. Update version in greybeard/__init__.py
#    Change __version__ = "X.Y.Z" to the new version

# 3. Commit changes
git add greybeard/__init__.py
git commit -m "chore: bump version to 0.2.0"
git push origin release-0.2.0

# 4. Create and merge PR

# 5. After PR merge, tag and push (tag must match version!)
git checkout main
git pull origin main
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0

# 6. Create GitHub Release at github.com/yourrepo/releases/new
#    Select the v0.2.0 tag you just pushed
# 7. GitHub Actions validates, builds, and publishes to PyPI
```

---

## Questions?

See the [GitHub Actions workflow](.github/workflows/publish.yml) or open an issue.
