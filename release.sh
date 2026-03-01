#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${BLUE}→ $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if version argument provided
if [ -z "$1" ]; then
    error "Usage: ./release.sh <version>\nExample: ./release.sh 0.2.0"
fi

VERSION="$1"
TAG="v${VERSION}"
RELEASE_BRANCH="release-${VERSION}"

# Validate version format (basic semver check)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    error "Version must be in format X.Y.Z (e.g., 0.2.0)"
fi

# Check if on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    error "Please run this script from the 'main' branch"
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    error "You have uncommitted changes. Commit or stash them first."
fi

# Check if tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    error "Tag $TAG already exists"
fi

# Pull latest changes
info "Pulling latest changes from main..."
git pull origin main || error "Failed to pull latest changes"

# Create release branch
info "Creating release branch: ${RELEASE_BRANCH}"
git checkout -b "$RELEASE_BRANCH"
success "Created branch ${RELEASE_BRANCH}"

echo
info "Preparing release ${TAG}"
echo

# Update version in pyproject.toml
info "Updating version in pyproject.toml..."
if [ "$(uname)" == "Darwin" ]; then
    # macOS
    sed -i '' "s/^version = \".*\"/version = \"${VERSION}\"/" pyproject.toml
else
    # Linux
    sed -i "s/^version = \".*\"/version = \"${VERSION}\"/" pyproject.toml
fi

# Verify the change
if grep -q "version = \"${VERSION}\"" pyproject.toml; then
    success "Updated pyproject.toml to version ${VERSION}"
else
    error "Failed to update version in pyproject.toml"
fi

# Create CHANGELOG.md if it doesn't exist
if [ ! -f CHANGELOG.md ]; then
    info "Creating CHANGELOG.md..."
    cat > CHANGELOG.md << EOF
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [${VERSION}] - $(date +%Y-%m-%d)

### Added
- Initial release

EOF
    success "Created CHANGELOG.md"
else
    info "CHANGELOG.md exists - remember to update it manually!"
fi

# Show changes to review
echo
info "Changes to be committed:"
git diff pyproject.toml
echo

# Commit changes
read -p "Commit version bump? (Y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    error "Release cancelled"
fi

info "Committing version bump..."
git add pyproject.toml CHANGELOG.md 2>/dev/null || git add pyproject.toml
git commit -m "chore: bump version to ${VERSION}"
success "Committed version ${VERSION}"

# Push release branch
echo
read -p "Push release branch to origin? (Y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    warn "Changes committed locally but not pushed"
    warn "Run: git push origin ${RELEASE_BRANCH}"
    exit 0
fi

info "Pushing ${RELEASE_BRANCH} to origin..."
git push origin "$RELEASE_BRANCH"
success "Pushed ${RELEASE_BRANCH}

info "Pushing to origin..."
git push origin "$CURRENT_BRANCH"
git push origin "$TAG"
success "Pushed to origin"

# Get repository URL for GitHub release
REPO_URL=$(git config --get remote.origin.url | sed 's/\.git$//' | sed 's/git@github.com:/https:\/\/github.com\//')

echo
success "Release preparation complete!"
echo
info "Next steps:"PR
REPO_URL=$(git config --get remote.origin.url | sed 's/\.git$//' | sed 's/git@github.com:/https:\/\/github.com\//')
PR_URL="${REPO_URL}/compare/main...${RELEASE_BRANCH}?expand=1"

echo
success "Release branch ready!"
echo
info "Next steps:"
echo "  1. Create and merge PR:"
echo "     ${PR_URL}"
echo
echo "  2. After PR is merged to main, create and push the tag:"
echo "     git checkout main"
echo "     git pull origin main"
echo "     git tag -a ${TAG} -m \"Release ${TAG}\""
echo "     git push origin ${TAG}"
echo
echo "  3. Create GitHub release at:"
echo "     ${REPO_URL}/releases/new?tag=${TAG}"
echo
echo "  4. GitHub Actions will automatically publish to PyPI"
echo

# Optionally open browser (macOS)
if [ "$(uname)" == "Darwin" ]; then
    read -p "Open GitHub PR page in browser? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        open "$PR_URL