# Installation

## Requirements

- Python 3.11 or higher
- An LLM backend (see [LLM Backends](../guides/backends.md))

## Install with uv (recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager.

```bash
uv pip install greybeard
```

### Install from source

```bash
git clone https://github.com/btotharye/greybeard.git
cd greybeard
uv pip install -e .

# If uv creates a virtual environment, you can either:
# 1. Activate it
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate       # Windows

# 2. Or use uv run without activation
uv run greybeard --version
uv run greybeard init
```

### Optional extras

```bash
# Anthropic/Claude backend support
uv pip install "greybeard[anthropic]"

# Everything
uv pip install "greybeard[all]"
```

## Install with pip

If you don't have uv installed:

```bash
pip install greybeard

# or from source:
git clone https://github.com/btotharye/greybeard.git
cd greybeard
pip install -e .
```

## Verify installation

```bash
# If you activated the virtual environment:
greybeard --version
greybeard packs

# Or if using uv run:
uv run greybeard --version
uv run greybeard packs
```

## Next step

Run the setup wizard to configure your LLM backend:

```bash
greybeard init
```

Or jump straight to the [Quick Start](quickstart.md).
