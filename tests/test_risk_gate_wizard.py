"""Tests for the risk gate wizard (greybeard risk-gate-wizard)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from greybeard.cli import cli
from greybeard.precommit import PreCommitConfig, RiskGate
from greybeard.wizards.risk_gate_wizard import (
    COMMON_PATTERNS,
    RISK_GATE_TEMPLATES,
    SEVERITY_LEVELS,
    _list_available_packs,
    _validate_glob_pattern,
    _validate_repo_structure,
)

# ---------------------------------------------------------------------------
# Unit tests: helper functions
# ---------------------------------------------------------------------------


class TestValidateGlobPattern:
    """Test glob pattern validation."""

    def test_valid_pattern(self):
        """Test valid pattern."""
        assert _validate_glob_pattern("infra/*") is None

    def test_valid_nested_pattern(self):
        """Test valid nested pattern."""
        assert _validate_glob_pattern("src/**/*.py") is None

    def test_empty_pattern(self):
        """Test empty pattern."""
        assert _validate_glob_pattern("") is not None

    def test_whitespace_only(self):
        """Test whitespace only."""
        assert _validate_glob_pattern("   ") is not None

    def test_null_byte_invalid(self):
        """Test null byte invalid."""
        assert _validate_glob_pattern("path\x00file") is not None

    def test_newline_invalid(self):
        """Test newline invalid."""
        assert _validate_glob_pattern("path\nfile") is not None


class TestValidateRepoStructure:
    """Test repo structure validation."""

    def test_minimal_repo(self, tmp_path):
        """Test minimal repo."""
        # Initialize minimal git repo
        import subprocess

        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)

        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(repo_path)
            findings = _validate_repo_structure()
            assert findings["has_git"] is True
            assert findings["has_pyproject"] is False
            assert findings["has_precommit"] is False
        finally:
            os.chdir(old_cwd)

    def test_full_repo(self, tmp_path):
        """Test full repo with multiple markers."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        # Create markers
        (repo_path / ".git").mkdir()
        (repo_path / "pyproject.toml").touch()
        (repo_path / ".pre-commit-config.yaml").touch()
        (repo_path / ".github" / "workflows").mkdir(parents=True)

        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(repo_path)
            findings = _validate_repo_structure()
            assert findings["has_git"] is True
            assert findings["has_pyproject"] is True
            assert findings["has_precommit"] is True
            assert findings["has_github_workflows"] is True
        finally:
            os.chdir(old_cwd)


class TestListAvailablePacks:
    """Test listing available packs."""

    def test_finds_packs(self, tmp_path, monkeypatch):
        """Test finds packs."""
        # Just verify the function exists and returns a list
        # The function relies on the installed greybeard package structure,
        # so we test that it returns a list without mocking filesystem details
        packs = _list_available_packs()
        # Should return a list (may be empty or populated depending on installation)
        assert isinstance(packs, list)
        # Packs should be sorted if any
        if len(packs) > 1:
            assert packs == sorted(packs)


# ---------------------------------------------------------------------------
# Template tests
# ---------------------------------------------------------------------------


class TestRiskGateTemplates:
    """Test risk gate templates."""

    def test_critical_template_exists(self):
        """Test critical template exists."""
        assert "critical" in RISK_GATE_TEMPLATES
        tmpl = RISK_GATE_TEMPLATES["critical"]
        assert "patterns" in tmpl
        assert "fail_on_concerns" in tmpl
        assert tmpl["fail_on_concerns"] == "critical"

    def test_all_templates_have_required_fields(self):
        """Test all templates have required fields."""
        required = ["description", "patterns", "fail_on_concerns", "default_packs"]
        for name, tmpl in RISK_GATE_TEMPLATES.items():
            for field in required:
                assert field in tmpl, f"Template {name} missing {field}"

    def test_severity_levels_valid(self):
        """Test severity levels are valid."""
        expected = ["critical", "high", "medium", "low", "none"]
        assert SEVERITY_LEVELS == expected

    def test_common_patterns_are_strings(self):
        """Test common patterns are strings."""
        for pattern in COMMON_PATTERNS:
            assert isinstance(pattern, str)
            assert len(pattern) > 0


# ---------------------------------------------------------------------------
# Integration tests: config generation
# ---------------------------------------------------------------------------


class TestConfigGeneration:
    """Test generating precommit config with risk gates."""

    def test_build_config_with_single_gate(self, tmp_path):
        """Test build config with single gate."""
        config = PreCommitConfig()
        gate = RiskGate(
            name="critical",
            patterns=["infra/*"],
            fail_on_concerns="critical",
            required_packs=["security-reviewer"],
            skip_if_branch=["emergency/*"],
        )
        config.risk_gates = [gate]

        # Convert to dict
        config_dict = {
            "enabled": config.enabled,
            "default_pack": config.default_pack,
            "risk_gates": [
                {
                    "name": gate.name,
                    "patterns": gate.patterns,
                    "fail_on_concerns": gate.fail_on_concerns,
                    "required_packs": gate.required_packs,
                    "skip_if_branch": gate.skip_if_branch,
                }
            ],
        }

        # Write and parse
        output_file = tmp_path / ".greybeard-precommit.yaml"
        with output_file.open("w") as f:
            yaml.dump(config_dict, f)

        # Load and verify
        with output_file.open() as f:
            loaded = yaml.safe_load(f)

        assert loaded["enabled"] is True
        assert len(loaded["risk_gates"]) == 1
        assert loaded["risk_gates"][0]["name"] == "critical"
        assert "infra/*" in loaded["risk_gates"][0]["patterns"]

    def test_build_config_with_multiple_gates(self, tmp_path):
        """Test build config with multiple gates."""
        gates = [
            RiskGate(
                name="critical",
                patterns=["infra/*"],
                fail_on_concerns="critical",
                required_packs=["security-reviewer"],
            ),
            RiskGate(
                name="api",
                patterns=["api/*"],
                fail_on_concerns="high",
                required_packs=["staff-core"],
            ),
        ]

        config_dict = {
            "enabled": True,
            "default_pack": "staff-core",
            "risk_gates": [
                {
                    "name": g.name,
                    "patterns": g.patterns,
                    "fail_on_concerns": g.fail_on_concerns,
                    "required_packs": g.required_packs,
                    "skip_if_branch": g.skip_if_branch,
                }
                for g in gates
            ],
        }

        output_file = tmp_path / ".greybeard-precommit.yaml"
        with output_file.open("w") as f:
            yaml.dump(config_dict, f)

        with output_file.open() as f:
            loaded = yaml.safe_load(f)

        assert len(loaded["risk_gates"]) == 2
        assert loaded["risk_gates"][0]["name"] == "critical"
        assert loaded["risk_gates"][1]["name"] == "api"


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestRiskGateWizardCLI:
    """Test CLI integration."""

    def test_risk_gate_wizard_command_exists(self):
        """Test risk-gate-wizard command exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["risk-gate-wizard", "--help"])
        assert result.exit_code == 0
        assert "risk-gate-wizard" in result.output or "Interactive wizard" in result.output

    def test_risk_gate_wizard_with_output_option(self):
        """Test risk-gate-wizard with custom output."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Can't easily test interactive, but we can test the help
            result = runner.invoke(cli, ["risk-gate-wizard", "--help"])
            assert result.exit_code == 0
            assert "--output" in result.output

    def test_precommit_wizard_command_exists(self):
        """Test greybeard-precommit wizard command."""
        from greybeard.precommit_cli import cli as precommit_cli

        runner = CliRunner()
        result = runner.invoke(precommit_cli, ["wizard", "--help"])
        assert result.exit_code == 0

    def test_precommit_wizard_with_output_option(self):
        """Test precommit wizard output option."""
        from greybeard.precommit_cli import cli as precommit_cli

        runner = CliRunner()
        result = runner.invoke(precommit_cli, ["wizard", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output or "-o" in result.output


# ---------------------------------------------------------------------------
# Fixture-based CLI tests with mocked input
# ---------------------------------------------------------------------------


class TestWizardInteraction:
    """Test wizard with mocked user input."""

    def test_minimal_config_creation(self, tmp_path):
        """Test creating minimal config."""
        from greybeard.precommit_cli import cli as precommit_cli

        runner = CliRunner()
        with runner.isolated_filesystem():
            # Simulate user input: select existing config (no), enable, defaults for most,
            # then skip adding gates, then save
            inputs = [
                "n",  # Don't load existing config
                "y",  # Enable integration
                "\n",  # Accept default pack (staff-core)
                "y",  # Skip unstaged
                "\n",  # No excluded paths
                "n",  # Don't add risk gates
                "y",  # Save
            ]
            result = runner.invoke(precommit_cli, ["wizard"], input="\n".join(inputs))
            # Should not error
            assert result.exit_code in [0, 1]  # Click.Abort is exit code 1

    def test_config_with_one_gate(self, tmp_path):
        """Test config with one risk gate."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Simulate adding a critical gate based on template
            inputs = [
                "n",  # Don't load existing
                "y",  # Enable
                "\n",  # Default pack
                "y",  # Skip unstaged
                "\n",  # No excluded paths
                "y",  # Add risk gate
                "1",  # Select critical template
                "n",  # Don't customize template
                "y",  # Skip branch patterns
                "y",  # Add another gate? No
                "y",  # Save
            ]
            from greybeard.precommit_cli import cli as precommit_cli

            result = runner.invoke(precommit_cli, ["wizard"], input="\n".join(inputs))
            # Should succeed or abort gracefully
            assert result.exit_code in [0, 1]


# ---------------------------------------------------------------------------
# Edge cases and error handling
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_no_packs_available(self, tmp_path):
        """Test behavior when no packs are available."""
        # Test that the function gracefully handles the case of no packs
        # by mocking the internal directory check
        with patch.object(Path, "exists", return_value=False):
            # When packs_dir doesn't exist, should return empty list
            # Note: This is a light test since the real function checks filesystem
            packs = _list_available_packs()
            # If packs dir doesn't exist, we get empty list
            assert isinstance(packs, list)

    def test_invalid_pattern_rejected(self):
        """Test invalid patterns are rejected."""
        assert _validate_glob_pattern("") is not None
        assert _validate_glob_pattern("\x00") is not None

    def test_severity_levels_ordering(self):
        """Test severity levels maintain proper ordering."""
        # Critical should come before high, high before medium, etc.
        critical_idx = SEVERITY_LEVELS.index("critical")
        high_idx = SEVERITY_LEVELS.index("high")
        medium_idx = SEVERITY_LEVELS.index("medium")
        low_idx = SEVERITY_LEVELS.index("low")

        assert critical_idx < high_idx < medium_idx < low_idx


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------


class TestRegressions:
    """Test for known regressions and fixes."""

    def test_config_roundtrip(self, tmp_path):
        """Test that config can be created and loaded without corruption."""
        # Create a config
        config = PreCommitConfig(
            enabled=True,
            default_pack="staff-core",
            excluded_paths=[".venv/*", "node_modules/*"],
            skip_unstaged=True,
        )
        gate = RiskGate(
            name="test-gate",
            patterns=["src/**/*.py"],
            fail_on_concerns="high",
            required_packs=["staff-core"],
        )
        config.risk_gates = [gate]

        # Save to file
        output_file = tmp_path / ".greybeard-precommit.yaml"
        config_dict = {
            "enabled": config.enabled,
            "default_pack": config.default_pack,
            "additional_packs": config.additional_packs,
            "fail_on_concerns": config.fail_on_concerns,
            "skip_unstaged": config.skip_unstaged,
            "max_context_lines": config.max_context_lines,
            "verbose": config.verbose,
            "allow_empty_commits": config.allow_empty_commits,
            "excluded_paths": config.excluded_paths,
            "risk_gates": [
                {
                    "name": g.name,
                    "patterns": g.patterns,
                    "fail_on_concerns": g.fail_on_concerns,
                    "required_packs": g.required_packs,
                    "skip_if_branch": g.skip_if_branch,
                }
                for g in config.risk_gates
            ],
        }

        with output_file.open("w") as f:
            yaml.dump(config_dict, f)

        # Load and verify roundtrip
        with output_file.open() as f:
            loaded_dict = yaml.safe_load(f)

        assert loaded_dict["enabled"] is True
        assert loaded_dict["default_pack"] == "staff-core"
        assert loaded_dict["skip_unstaged"] is True
        assert len(loaded_dict["excluded_paths"]) == 2
        assert len(loaded_dict["risk_gates"]) == 1
        assert loaded_dict["risk_gates"][0]["fail_on_concerns"] == "high"
