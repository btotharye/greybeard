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
make pre-commit-install # Install pre-commit hooks (recommended)

# Testing
make test              # Run tests
make test-cov          # Run tests with coverage report
make test-verbose      # Run tests with verbose output

# Linting & Formatting
make lint              # Check code with ruff
make lint-fix          # Auto-fix linting issues
make format            # Format code
make format-check      # Check formatting without changes
make type-check        # Run type checking with mypy
make check             # Run all checks (lint + format + test)

# Pre-commit
make pre-commit-run    # Run pre-commit on all files

# Other
make clean             # Remove build artifacts
make docs              # Serve docs locally
make help              # Show all available commands
```

### Pre-commit Hooks (Recommended)

We use pre-commit hooks to catch issues before committing:

```bash
# Install hooks (one time)
make pre-commit-install

# Now hooks run automatically on:
# - git commit: ruff linting and formatting
# - git push: pytest tests
```

You can also run hooks manually:

```bash
make pre-commit-run    # Run on all files
```

### Manual Commands

If you prefer not to use Make:

```bash
# Running tests
uv run pytest
uv run pytest --cov=greybeard --cov-report=term-missing

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

## Contributing to Interactive Mode

Interactive mode (`greybeard/interactive.py`) is a relatively new feature that enables stateful, multi-turn conversations. If you're improving or extending it:

### Key Files

- **`greybeard/interactive.py`** — Core `InteractiveSession` class and REPL loop
- **`tests/test_interactive.py`** — Test suite
- **`docs/guides/interactive-mode.md`** — User guide (refer here for behavior details)

### Testing Interactive Mode

Interactive mode requires human input simulation in tests. Use `unittest.mock` to patch the `Prompt.ask()` call:

```python
from unittest.mock import patch
from greybeard.interactive import InteractiveSession

def test_followup_question():
    session = InteractiveSession(mode="review", pack=sample_pack, config=sample_config)
    session.run_initial_analysis("test input")
    
    # Mock user input
    with patch('greybeard.interactive.Prompt.ask', return_value="What are the risks?"):
        response = session.ask_followup("What are the risks?")
    
    assert response  # response is non-empty
    assert len(session.get_conversation_history()) == 2  # user + assistant
```

See `tests/test_interactive.py` for more examples.

### Common Changes & Patterns

**Adding a new interactive command:**

1. Add method to `InteractiveSession` (e.g., `session.analyze_alternative()`)
2. Add parsing in `run_interactive_repl()` to recognize the command
3. Call the session method and stream the response
4. Add tests in `test_interactive.py`
5. Update help text in `_print_help()`
6. Document in `docs/guides/interactive-mode.md`

**Modifying system prompts for follow-ups:**

- Update `_build_followup_system_prompt()` in `InteractiveSession`
- This prompt is crucial for coherent multi-turn conversations
- Always reference the pack's perspective/heuristics
- Include clear instructions to build on prior context

**Streaming responses:**

Interactive mode streams all LLM output to the terminal. Do NOT suppress streaming for UX reasons (see `_call_openai_compat()` and `_call_anthropic()` for patterns).

### Interactive Mode Architecture

The design is intentionally simple:

1. **Session initialization** — Store mode, pack, config, model
2. **Initial analysis** — Run full `run_review()`, store result, add to history
3. **Conversation loop** — User input → reconstruct context → call LLM → stream response → add to history
4. **History management** — Keep recent messages for context, trim old ones to avoid token bloat

The `conversation_history` list is the single source of truth for all prior context.

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
├── greybeard/
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
