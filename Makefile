.PHONY: help install install-dev install-all test test-cov test-verbose lint lint-fix format format-check check clean build docs docs-build release run init packs config pre-commit-install pre-commit-run type-check

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install package for production use
	uv pip install -e .

install-dev: ## Install package with development dependencies
	uv pip install -e ".[dev]"
	@echo ""
	@echo "✓ Development dependencies installed"
	@echo "  Run 'make test' to run tests"

install-all: ## Install package with all optional dependencies
	uv pip install -e ".[all]"

test: ## Run tests (installs dev deps if needed)
	@uv run pytest 2>/dev/null || (echo "Installing dev dependencies..." && uv pip install -e ".[dev]" && uv run pytest)

test-cov: ## Run tests with coverage report
	uv run pytest --cov=greybeard --cov-report=term-missing --cov-report=html

test-verbose: ## Run tests with verbose output
	uv run pytest -v

lint: ## Run linting checks (ruff)
	uv run ruff check .

lint-fix: ## Run linting and auto-fix issues
	uv run ruff check . --fix

format: ## Format code with ruff
	uv run ruff format .

format-check: ## Check code formatting without modifying files
	uv run ruff format --check .

check: lint format-check test ## Run all checks (lint, format, test)

type-check: ## Run type checking with mypy
	uv run mypy greybeard

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install
	uv run pre-commit install --hook-type pre-push
	@echo ""
	@echo "✓ Pre-commit hooks installed"
	@echo "  Hooks will run automatically on commit/push"

pre-commit-run: ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

clean: ## Remove build artifacts and cache files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf site/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build distribution packages
	uv pip install --system build
	python -m build

docs: ## Serve documentation locally
	uv pip install -e ".[docs]"
	uv run mkdocs serve

docs-build: ## Build documentation
	uv pip install -e ".[docs]"
	uv run mkdocs build

release: ## Create a new release (usage: make release VERSION=0.2.0)
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION is required. Usage: make release VERSION=0.2.0"; \
		exit 1; \
	fi
	./release.sh $(VERSION)

# Development convenience targets
run: ## Run greybeard CLI (usage: make run ARGS="analyze --help")
	uv run greybeard $(ARGS)

init: ## Initialize greybeard configuration
	uv run greybeard init

packs: ## List available content packs
	uv run greybeard packs

config: ## Show current configuration
	uv run greybeard config show
