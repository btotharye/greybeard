# Claude Instructions — Greybeard OSS

## Project Overview

**Greybeard** is a decision-review framework and CLI tool. It analyzes code changes, documentation, and architectural decisions through multiple lenses (Security, Performance, Team Health, etc.) and provides structured feedback.

**Core Value:** Turn ad-hoc code review insights into systematic decision intelligence.

## Architecture

### Core Modules

**`greybeard/analyzer.py`**
- `run_review()` — Main entry point for analysis
- Orchestrates backend selection (OpenAI, Anthropic, Copilot, Groq)
- Handles fallbacks and error recovery
- Streaming and non-streaming modes

**`greybeard/modes.py`**
- Review modes: `review`, `mentor`, `coach`, `brainstorm`, etc.
- Each mode has a distinct system prompt and expectations
- Builds prompts based on packs and context

**`greybeard/packs.py`**
- Content packs (review lenses, personas, focus areas)
- File-based and GitHub-based pack loading
- Caching for performance
- YAML parsing and validation

**`greybeard/reporters/`**
- Output formatters: Markdown, JSON, HTML, Dashboard
- Batch analysis aggregation
- Risk deduplication and synthesis

**`greybeard/storage/` & `greybeard/history.py`**
- Pluggable history storage (file-based default)
- Trend analysis across decisions
- Risk pattern detection

### CLI

**`greybeard/cli.py`**
- Commands: `analyze`, `self-check`, `coach`, `batch`, `config`, etc.
- Argument parsing with Click
- Config management (YAML + dict-based)

## Key Patterns

### Adding a New Backend

```python
# greybeard/backends/my_llm.py
from .base import Backend, BackendResponse

class MyLLMBackend(Backend):
    def __init__(self, config):
        self.api_key = config.get("api_key")
        self.model = config.get("model", "default")
    
    def call(self, system_prompt, user_message, **kwargs):
        """Synchronous call to LLM."""
        response = call_my_llm(
            system=system_prompt,
            message=user_message,
            model=self.model,
            api_key=self.api_key
        )
        return BackendResponse(
            text=response.text,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens
        )
    
    async def call_async(self, system_prompt, user_message, **kwargs):
        """Async wrapper for FastAPI/web use."""
        return await asyncio.to_thread(
            self.call, system_prompt, user_message, **kwargs
        )
```

### Adding a Review Mode

```python
# greybeard/modes.py
REVIEW_MODES = {
    "my-review": {
        "description": "My custom review lens",
        "system_prompt": """You are reviewing code through the lens of [FOCUS].
        
Focus on:
- Item 1
- Item 2
- Item 3

Return structured feedback.""",
        "output_format": "markdown",
    }
}
```

### Adding a Content Pack

```yaml
# packs/my-pack.yaml
name: my-pack
perspective: Senior Engineer
tone: direct
focus_areas:
  - Architecture
  - Performance
heuristics:
  - Check for race conditions
  - Validate error handling
example_questions:
  - Is this thread-safe?
  - How does this scale?
communication_style: Technical
description: A pack for deep technical review
```

## Development Workflow

1. **Setup:** `uv sync --all-extras`
2. **Create branch:** `git checkout -b feat/description`
3. **Code:** Implement feature
4. **Test:** `uv run pytest tests/ -v` (80%+ coverage required)
5. **Lint:** `uv run ruff check . --fix`, `uv run black .`
6. **Type check:** `uv run mypy greybeard/`
7. **Docs:** Update README if user-facing, add docstrings
8. **Push & PR:** Create PR with detailed description

## Testing Standards

- **Unit tests:** Test individual functions (mock dependencies)
- **Integration tests:** Test end-to-end workflows
- **Fixtures:** Use `conftest.py` for shared test data
- **Coverage:** 80%+ required on new/modified files
- **Mocking:** Mock external APIs, use real storage for testing

### Test Structure
```python
# tests/test_my_feature.py
import pytest
from unittest.mock import Mock, patch
from greybeard.my_feature import my_function

class TestMyFeature:
    """Group related tests in classes."""
    
    def test_happy_path(self):
        """Test normal operation."""
        result = my_function("input")
        assert result == "expected"
    
    def test_error_handling(self):
        """Test error cases."""
        with pytest.raises(ValueError, match="expected error"):
            my_function("bad input")
    
    @patch("greybeard.my_feature.external_api")
    def test_with_mock(self, mock_api):
        """Test with mocked dependency."""
        mock_api.return_value = "mocked"
        result = my_function("input")
        assert result == "expected"
        mock_api.assert_called_once_with("input")
```

## Code Standards

- **Type hints:** All functions must have type hints (parameters + return)
- **Docstrings:** Google-style for all public functions/classes
- **Naming:** snake_case for variables/functions, PascalCase for classes
- **Imports:** Organized (stdlib, third-party, local), no unused imports
- **Line length:** 100 chars max
- **Error handling:** Catch specific exceptions, provide context

## Commands

```bash
# Setup
uv sync --all-extras

# Testing
uv run pytest tests/ -v
uv run pytest --cov=greybeard --cov-report=term-missing

# Linting
uv run ruff check . --fix
uv run black .

# Type checking
uv run mypy greybeard/

# Building docs
uv run mkdocs build

# CLI
uv run greybeard --help
```

## How Claude Helps

✅ **Architecture:** Suggest modular designs, API patterns
✅ **Testing:** Generate comprehensive test cases
✅ **Performance:** Identify bottlenecks, optimize queries
✅ **LLM integration:** Help debug model behavior
✅ **Documentation:** Write user guides, API docs
✅ **Refactoring:** Suggest improvements to existing code

## Key Decisions

- **Pluggable backends:** Support multiple LLM providers (OpenAI, Anthropic, Copilot, Groq)
- **Async-ready:** `run_review_async()` for web/FastAPI integration
- **Packs system:** Content packs allow customization without code changes
- **Storage abstraction:** Pluggable storage (file/DB) for history and packs
- **SaaS path:** Core is library-friendly, not CLI-only

## Useful Links

- **Docs:** `docs/` directory (built with mkdocs)
- **Examples:** `examples/` directory
- **Tests:** `tests/` directory (mirrors src structure)
- **GitHub:** https://github.com/btotharye/greybeard
