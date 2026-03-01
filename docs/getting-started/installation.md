# Installation

greybeard is available on [PyPI](https://pypi.org/project/greybeard/) and can be installed with any Python package manager.

## Requirements

- Python 3.11 or higher
- An LLM backend (see [LLM Backends](../guides/backends.md))

## Install from PyPI

### Using uv (recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager.

```bash
uv pip install greybeard
```

### Using pip

```bash
pip install greybeard
```

### Optional extras

Install additional backends:

```bash
# With uv
uv pip install "greybeard[anthropic]"  # Claude/Anthropic support
uv pip install "greybeard[all]"        # Everything

# With pip
pip install "greybeard[anthropic]"
pip install "greybeard[all]"
```

## Development Installation

If you want to contribute or modify greybeard:

```bash
git clone https://github.com/btotharye/greybeard.git
cd greybeard

# Using uv (recommended)
uv pip install -e ".[dev]"

# Using pip
pip install -e ".[dev]"

# Or use the Makefile
make install-dev
```

For detailed contribution guidelines, testing, and development workflows, see the [Contributing Guide](../../CONTRIBUTING.md).

## Verify installation

After installing, verify greybeard is available:

```bash
greybeard --version
greybeard packs
```

!!! note "Virtual environments"
If you installed into a virtual environment (created by uv or manually), make sure to activate it first, or use `uv run greybeard` instead.

## Next steps

Run the setup wizard to configure your LLM backend:

```bash
greybeard init
```

Or jump straight to the [Quick Start](quickstart.md) guide.
