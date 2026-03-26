# Development Guide — Greybeard

## Quick Start

```bash
# Clone repo
git clone https://github.com/btotharye/greybeard.git
cd greybeard

# Setup
uv sync --all-extras

# Run tests
uv run pytest tests/ -v

# Try CLI
uv run greybeard --help
```

## Development Workflow

### Branching Strategy

- **Feature branches:** `feat/feature-name` (new features, backends, modes)
- **Bug fix branches:** `fix/bug-description` (bug fixes)
- **Documentation:** `docs/section-name` (docs-only changes)
- **Refactor:** `refactor/what-changed` (non-functional improvements)

### Making Changes

1. **Create branch from main:**
   ```bash
   git checkout main
   git pull
   git checkout -b feat/my-feature
   ```

2. **Write code + tests together:**
   ```bash
   # Edit code in greybeard/
   # Write tests in tests/
   # Keep structure parallel
   ```

3. **Run tests frequently:**
   ```bash
   uv run pytest tests/ -v
   ```

4. **Check coverage:**
   ```bash
   uv run pytest --cov=greybeard --cov-report=term-missing
   # Target: 80%+ on new/modified files
   ```

5. **Lint and format:**
   ```bash
   uv run ruff check . --fix
   uv run black .
   uv run mypy greybeard/
   ```

6. **Build docs locally:**
   ```bash
   uv run mkdocs build --strict
   ```

7. **Commit with meaningful message:**
   ```bash
   git commit -m "feat: add my feature

   - What it does
   - Why it's needed
   - How to use it"
   ```

8. **Push and create PR:**
   ```bash
   git push origin feat/my-feature
   # Create PR on GitHub with template
   ```

### PR Requirements

All PRs must meet these criteria to merge:

- ✅ **Tests:** All tests pass locally + in CI
- ✅ **Coverage:** 80%+ on new/modified code (required)
- ✅ **Linting:** `ruff check .` passes
- ✅ **Type checking:** `mypy greybeard/` passes
- ✅ **Documentation:** Docstrings, README if user-facing
- ✅ **Docs build:** `mkdocs build --strict` succeeds

### PR Description Template

```markdown
## What does this do?
Brief description of feature/fix.

## Why?
Motivation, problem it solves, or benefit.

## How?
High-level technical overview.

## Testing
- What tests were added?
- How can this be tested manually?

## Breaking changes?
None / Describe if any.

## Checklist
- [ ] Tests added/updated
- [ ] Coverage 80%+ on new code
- [ ] Linting passes (ruff, black, mypy)
- [ ] Docstrings added
- [ ] README updated (if user-facing)
- [ ] Docs build (`mkdocs build --strict`)
```

## Common Tasks

### Adding a New Backend

1. Create `greybeard/backends/my_backend.py`
2. Extend `Backend` base class
3. Implement required methods:
   ```python
   def call(self, system_prompt, user_message, **kwargs) -> BackendResponse:
       # Sync call
   
   async def call_async(self, system_prompt, user_message, **kwargs):
       # Async wrapper
   ```
4. Add to `greybeard/config.py` `KNOWN_BACKENDS`
5. Create tests in `tests/test_my_backend.py` (mock API calls)
6. Add to README backends section
7. Example usage in docstring

### Adding a Review Mode

1. Add entry to `REVIEW_MODES` in `greybeard/modes.py`
2. Define clear system prompt
3. Test with different backends
4. Document in `docs/modes/`
5. Update README features

### Creating a Content Pack

1. Create `packs/my-pack.yaml`:
   ```yaml
   name: my-pack
   perspective: Senior Engineer
   tone: direct
   focus_areas: [...]
   heuristics: [...]
   ```
2. Test: `uv run greybeard analyze --pack my-pack <file>`
3. Add to `docs/packs/`
4. PR with pack in `packs/`

### Writing Tests

Keep tests organized and comprehensive:

```python
# tests/test_my_feature.py
import pytest
from unittest.mock import Mock, patch

class TestMyFeature:
    """Group related tests."""
    
    def test_happy_path(self):
        """Normal operation."""
        ...
    
    def test_error_case(self):
        """Error handling."""
        ...
    
    @patch("greybeard.module.external_call")
    def test_with_mock(self, mock_external):
        """With mocked dependency."""
        ...

@pytest.fixture
def sample_pack():
    """Reusable test data."""
    return ContentPack(name="test", perspective="Tester", tone="direct")
```

**Coverage requirements:**
- Unit tests: Mock external dependencies
- Integration tests: Use real storage (test DBs, temp files)
- Always test error cases + edge cases
- 80%+ coverage on new/modified code

### Debugging

```bash
# Run with print statements
uv run greybeard analyze <file> --verbose

# Run specific test with output
uv run pytest tests/test_analyzer.py::TestRunReview::test_happy_path -v -s

# Run with debugger
uv run pytest tests/test_analyzer.py -v --pdb

# Type checking for specific file
uv run mypy greybeard/analyzer.py --show-error-codes

# Check what changed (linting)
uv run ruff check greybeard/ --show-source
```

## Useful Commands

```bash
# Setup
uv sync --all-extras

# Testing
uv run pytest tests/ -v                                    # All tests
uv run pytest tests/test_analyzer.py -v                  # Specific file
uv run pytest -k test_run_review -v                       # Specific test pattern
uv run pytest --cov=greybeard --cov-report=term-missing  # Coverage

# Linting
uv run ruff check . --fix                                 # Check + fix
uv run black . --check                                    # Check only
uv run mypy greybeard/ --show-error-codes                # Type check

# Documentation
uv run mkdocs build --strict                              # Build docs
uv run mkdocs serve                                       # Live preview (http://localhost:8000)

# CLI
uv run greybeard --help                                   # Show help
uv run greybeard analyze --help                           # Command help
uv run greybeard analyze <file> --mode review --pack staff-core

# Development
uv add package-name                                       # Add dependency
uv lock --upgrade                                         # Update lock file
```

## Code Standards

- **Type hints:** All functions require parameter + return types
- **Docstrings:** Google-style for public functions/classes
- **Naming:** snake_case (funcs/vars), PascalCase (classes)
- **Imports:** stdlib → third-party → local, no unused imports
- **Line length:** 100 chars max
- **Comments:** Explain *why*, not *what* (code shows what)

## Troubleshooting

### Tests failing locally but CI passes
- Clear cache: `rm -rf .pytest_cache .ruff_cache`
- Reinstall: `uv sync --force-all`

### Type checking errors
- Install stubs: `uv add --dev types-<package>`
- Check mypy config in `pyproject.toml`

### Import errors
- Check `greybeard/__init__.py` exports
- Run `uv sync` to ensure venv is updated

### Coverage not meeting threshold
- Run with `--cov-report=html` for detailed report
- Look at red lines in report
- Add tests for untested branches

## Getting Help

- **Questions?** Open an issue on GitHub
- **Bug report?** Include reproduction steps + test case
- **Feature request?** Describe use case + expected behavior
- **Questions about code?** File an issue or ask in discussions

## Resources

- **Docs:** `docs/` (built with mkdocs)
- **Examples:** `examples/`
- **Tests:** `tests/` (mirrors `greybeard/` structure)
- **GitHub:** https://github.com/btotharye/greybeard
- **Discord:** Community support (link in README)
