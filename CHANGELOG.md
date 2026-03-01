# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
