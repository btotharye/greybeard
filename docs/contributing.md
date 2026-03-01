# Contributing

Thanks for your interest in contributing to greybeard.

## Ways to contribute

- **Content packs** — the easiest and highest-value contribution
- **Bug reports** — open an issue with steps to reproduce
- **Feature requests** — open an issue describing the use case
- **Code** — see below for the development setup

---

## Development setup

```bash
git clone https://github.com/btotharye/greybeard.git
cd greybeard

# With uv (recommended)
uv pip install -e ".[dev]"
source .venv/bin/activate      # if uv created a venv

# Or use uv run for commands without activating
uv run pytest                  # run tests
uv run ruff check .            # run linter

# Or with pip
pip install -e ".[dev]"

# Or use the Makefile (easiest)
make install-dev               # install with dev dependencies
make help                      # see all available commands
```

## Common Development Tasks

The project includes a Makefile for common tasks:

```bash
# Setup
make install-dev       # Install with dev dependencies
make install-all       # Install with all dependencies

# Testing
make test              # Run tests
make test-cov          # Run tests with coverage
make test-verbose      # Run tests with verbose output

# Linting & Formatting
make lint              # Check code with ruff
make lint-fix          # Auto-fix linting issues
make format            # Format code
make format-check      # Check formatting without changes
make check             # Run all checks (lint + format + test)

# Other
make clean             # Remove build artifacts
make docs              # Serve docs locally
make help              # Show all available commands
```

### Manual Commands

If you prefer not to use Make:

```bash
# Running tests
uv run pytest
uv run pytest --cov=staff_review --cov-report=term-missing

# Linting
uv run ruff check .
uv run ruff check . --fix

# Formatting
uv run ruff format .
uv run ruff format --check .
```

## Running docs locally

```bash
uv pip install -e ".[docs]"
mkdocs serve
```

Then open `http://localhost:8000`.

---

## Contributing a content pack

Content packs are the easiest contribution with the highest impact. Here's how:

1. Create a new `.yaml` file in `packs/`
2. Follow the [Pack Schema](reference/pack-schema.md)
3. Test it:
   ```bash
   git diff HEAD~1 | greybeard analyze --pack packs/your-pack.yaml
   ```
4. Open a PR with:
   - The pack file
   - A brief description of the perspective and when to use it
   - An example output (optional but appreciated)

### Pack ideas

Some perspectives that would make great packs:

- **Security engineer** — threat modeling, auth, secrets, injection
- **Data engineer** — schema design, migration safety, pipeline reliability
- **Mobile engineer** — client/server contract, versioning, offline behavior
- **Startup engineer** — speed vs quality tradeoffs, tech debt awareness
- **SRE** — SLOs, error budgets, toil reduction
- **Accessibility** — a11y impact of UI decisions

---

## Code contributions

### Before opening a PR

1. Run tests: `pytest`
2. Run lint: `ruff check .`
3. Add tests for new functionality
4. Update docs if adding new features

### Commit style

Small, logical commits. Commit messages in the format:

```
feat: add X
fix: handle Y edge case
docs: update Z
test: add tests for W
chore: update dependencies
```

### Branch naming

```
feat/my-feature
fix/the-bug-description
docs/update-mcp-guide
```

---

## Project structure

```
greybeard/
├── staff_review/
│   ├── cli.py          # Click CLI entry point
│   ├── analyzer.py     # Review engine + LLM dispatch
│   ├── modes.py        # Mode-specific system prompts
│   ├── packs.py        # Pack loader (built-in + remote)
│   ├── config.py       # Config management
│   ├── mcp_server.py   # MCP stdio server
│   └── models.py       # Data types
├── packs/              # Built-in content packs
├── docs/               # MkDocs documentation
├── tests/              # pytest tests
└── examples/           # Usage examples
```

---

## Questions?

Open an issue or start a discussion on GitHub.
