# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-03-22

### Added

- **SLO Agent**: new `greybeard slo` command and `SLOAgent` for AI-driven SLO recommendations —
  analyzes services and suggests appropriate SLO targets, error budgets, and alerting thresholds
- **Risk Gate Wizard**: interactive `greybeard wizard risk-gate` command for guided pre-commit
  configuration generation — walks through risk thresholds and generates a `.greybeard-precommit.yaml`
  tailored to your project
- **Batch analyzer & dashboard**: `BatchAnalyzer` for running reviews across multiple files/PRs and
  `greybeard dashboard` command for an aggregated findings view with severity summaries
- **ADR support**: `greybeard adr` commands (`adr list`, `adr save`) and `reporters.adr` module for
  generating Architecture Decision Records from review output

### Documentation

- Comprehensive SLO Agent guide covering setup, configuration, and example outputs
- Risk Gate Wizard guide covering interactive workflow and generated config reference

## [0.4.1] - 2026-03-21

### Fixed

- **PDF report formatting**: text in risk and question table cells now wraps correctly
  instead of overflowing/truncating — cells use `Paragraph` objects instead of plain strings
- **PDF markdown rendering**: `**bold**`, `*italic*`, and `` `code` `` in LLM output are
  now converted to ReportLab XML before rendering, eliminating literal `**` in the PDF
- **PDF table header**: "Risk" / "Severity" header row now renders as white bold text on
  the purple background (added dedicated `TableHeaderCell` style — `Paragraph` objects
  ignore a table's `TEXTCOLOR` command)
- **PDF severity labels**: replaced emoji severity indicators (`🔴🟠🟡`) which rendered
  as `■` boxes in Helvetica with plain text `[CRITICAL]` / `[HIGH]` / `[MEDIUM]`
- **PDF bullet stripping**: leading `* ` and `- ` bullet prefixes are now stripped from
  risk cell content before rendering
- **Test isolation**: `test_call_openai_compat_import_error` and
  `test_call_anthropic_import_error` were defeating their own `sys.modules` mocks by
  manually deleting the `None` sentinel, causing live API calls and spurious 401 failures

## [0.4.0] - 2026-03-21

### Added

- **PDF report export**: `greybeard analyze --format pdf --output report.pdf` generates a
  structured PDF with title page, risk summary, findings, and metadata footer via
  `reportlab`. Install the optional dependency with `pip install greybeard[pdf]`.
- **Pre-commit hook improvements**:
  - Structured "What to do" guidance displayed on every blocked commit
  - Helpful YAML parse error with file path when `.greybeard-precommit.yaml` is malformed
  - Rate-limit back-off: waits and retries instead of hard-failing on HTTP 429
  - Idempotent pre-commit runs: repeated commits on the same staged diff no longer re-run the review
- **GitHub Actions workflow improvements**:
  - Explicit 8-minute LLM timeout to prevent silent 15-minute job hangs
  - 1 MB diff size guard — oversized PRs are skipped with a clear notice instead of hanging
  - API key validation step gives an actionable error if the secret is missing or empty
  - Unique `<!-- greybeard-bot:PACK -->` HTML comment marker for idempotent PR comment updates
    (prevents false matches on existing user-created comments)

### Changed

- **Default Anthropic model changed from `claude-3-5-sonnet-20241022` to `claude-haiku-4-5-20251001`**
  This is a deliberate cost/speed optimisation for the GitHub Actions workflow (Haiku is ~5×
  cheaper and ~2× faster for typical diffs). **Review quality will be lower** than with Sonnet.
  Users who want Sonnet-level reviews should override explicitly:
  `greybeard config set llm.model claude-sonnet-4-6`
  or set the model via the workflow `env`: `model: claude-sonnet-4-6`.

### Fixed

- `PDFReporter.__init__` default arg `pagesize=letter` caused `NameError` at import time
  when `reportlab` is not installed; changed to `pagesize=None` with deferred assignment

## [0.3.4] - 2026-03-15

## Fixed

- Fixed issues with claude desktop and mcp server configuration.

## [0.3.3] - 2026-03-15

## Changed

- fix: fixing issues with packs loading

## [0.3.2] - 2026-03-15

## Changed

- fix: fixing issue with listing packs by @btotharye in https://github.com/btotharye/greybeard/pull/30

## [0.3.0] - 2026-03-15

### Added

- Dual-format pack loading: support both legacy (`packs/*.yaml`) and new (`packs/folder/*.yaml`) pack structures
- Individual README.md and example files for all 10 built-in packs
- Version validation in GitHub Actions publish workflow to ensure git tag matches code version
- Automated version management: version now read from `greybeard/__init__.py` via hatchling

### Changed

- Migrated all 10 built-in packs to new folder structure: `packs/<pack-name>/<pack-name>.yaml`
- Renamed Python module from `staff_review` to `greybeard` throughout codebase
- Centralized version management: single source of truth in `greybeard/__init__.py`
- Updated release.sh to update version in `greybeard/__init__.py` instead of `pyproject.toml`
- Updated RELEASING.md documentation with new version management workflow

### Fixed

- Fixed hatchling configuration section name from `[tool.hatchling.version]` to `[tool.hatch.version]`

## [0.2.0] - 2026-03-01

### Changed

- Migrated to `uv` as the primary package manager throughout documentation and workflows
- Updated all GitHub Actions workflows to use Python 3.12
- Improved release process to work with branch protection and PR requirements

### Fixed

- Fixed GitHub Actions workflows to properly create virtual environments with `uv`
- Fixed `release.sh` script syntax errors and improved workflow for PR-based releases

### Added

- Added CHANGELOG to documentation site and PyPI project URLs

## [0.1.0] - 2026-03-01

### Added

- Initial release on PyPI
- CLI-first Staff/Principal engineer-level code review tool
- Support for OpenAI, Anthropic, Ollama, and LM Studio backends
- Built-in content packs: staff-core, oncall-future-you, mentor-mode, solutions-architect, idp-readiness
- MCP server integration for Claude Desktop, Cursor, Zed
- Multiple review modes: review, mentor, coach, self-check
- Community pack installation from GitHub repositories
- Comprehensive documentation on ReadTheDocs
