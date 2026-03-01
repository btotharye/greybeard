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

### Quick Start (Using Helper Script)

The easiest way to create a release:

```bash
./release.sh 0.2.0
```

This script will:

1. ✅ Verify clean git state and version format
2. ✅ Update `pyproject.toml` with the new version
3. ✅ Create/initialize `CHANGELOG.md` (if it doesn't exist)
4. ✅ Commit the version bump
5. ✅ Create and push the git tag
6. ✅ Open your browser to the GitHub release page

Then just fill in the release notes on GitHub and publish!

---

## Manual Release Workflow

If you prefer manual control, follow these steps:

### 1. Update Version

Edit [`pyproject.toml`](pyproject.toml#L7):

```toml
[project]
version = "0.2.0"  # Update this
```

### 2. Update Changelog (if present)

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

### 3. Commit and Push

```bash
git add pyproject.toml CHANGELOG.md  # if you have one
git commit -m "chore: bump version to 0.2.0"
git push origin main
```

### 4. Create a Git Tag

```bash
git tag v0.2.0
git push origin v0.2.0
```

### 5. Create a GitHub Release

1. Go to https://github.com/btotharye/greybeard/releases/new
2. **Tag**: Select `v0.2.0` (the tag you just pushed)
3. **Release title**: `v0.2.0` or `greybeard v0.2.0`
4. **Description**: Summarize changes from CHANGELOG or write release notes
5. Click **Publish release**

### 6. Automatic Publishing

The GitHub Action will automatically:

- ✅ Build the distribution files (`sdist` and `wheel`)
- ✅ Publish to PyPI using trusted publishing
- ✅ Show the new version at https://pypi.org/project/greybeard/

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
# Then create GitHub release when browser opens
```

**Manual approach:**

```bash
# 1. Update version in pyproject.toml
# 2. Commit changes
git add pyproject.toml
git commit -m "chore: bump version to 0.2.0"
git push origin main

# 3. Tag and push
git tag v0.2.0
git push origin v0.2.0

# 4. Create GitHub Release at github.com/yourrepo/releases/new
# 5. GitHub Actions publishes to PyPI automatically
```

---

## Questions?

See the [GitHub Actions workflow](.github/workflows/publish.yml) or open an issue.
