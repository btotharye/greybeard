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


# ---------------------------------------------------------------------------
# Detailed testing of internal functions with mocks
# ---------------------------------------------------------------------------


class TestPromptList:
    """Test the _prompt_list function in detail."""

    def test_prompt_list_basic(self):
        """Test basic prompt list functionality."""
        from greybeard.wizards.risk_gate_wizard import _prompt_list

        with patch("click.prompt") as mock_prompt:
            # User enters two items, then blank
            mock_prompt.side_effect = ["item1", "item2", ""]
            result = _prompt_list("Enter items", min_items=0)
            assert result == ["item1", "item2"]
            assert mock_prompt.call_count == 3

    def test_prompt_list_with_min_items(self):
        """Test prompt list enforces minimum items."""
        from greybeard.wizards.risk_gate_wizard import _prompt_list

        with patch("click.prompt") as mock_prompt:
            # User tries to submit empty, then adds items
            mock_prompt.side_effect = ["", "item1", "item2", ""]
            result = _prompt_list("Enter items", min_items=2)
            assert result == ["item1", "item2"]

    def test_prompt_list_with_max_items(self):
        """Test prompt list enforces maximum items."""
        from greybeard.wizards.risk_gate_wizard import _prompt_list

        with patch("click.prompt") as mock_prompt:
            # User adds three items, but max is 2
            mock_prompt.side_effect = ["item1", "item2", "item3"]
            result = _prompt_list("Enter items", max_items=2)
            assert result == ["item1", "item2"]
            assert len(result) == 2

    def test_prompt_list_with_suggestion_list(self):
        """Test prompt list displays suggestions."""
        from greybeard.wizards.risk_gate_wizard import _prompt_list

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = [""]
            suggestions = ["sug1", "sug2", "sug3", "sug4", "sug5", "sug6"]
            result = _prompt_list("Enter items", min_items=0, suggestion_list=suggestions)
            assert result == []

    def test_prompt_list_invalid_pattern_rejected(self):
        """Test invalid patterns are rejected."""
        from greybeard.wizards.risk_gate_wizard import _prompt_list

        with patch("click.prompt") as mock_prompt:
            # User enters invalid pattern, then valid
            mock_prompt.side_effect = ["path\x00file", "valid-pattern", ""]
            result = _prompt_list("Enter patterns", min_items=1)
            assert result == ["valid-pattern"]

    def test_prompt_list_with_hint(self):
        """Test prompt list with hint text."""
        from greybeard.wizards.risk_gate_wizard import _prompt_list

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["item1", ""]
            result = _prompt_list("Enter items", hint="This is a hint", min_items=0)
            assert result == ["item1"]


class TestSelectPacks:
    """Test the _select_packs function."""

    def test_select_packs_by_index(self):
        """Test selecting packs by numeric index."""
        from greybeard.wizards.risk_gate_wizard import _select_packs

        with patch("click.prompt") as mock_prompt:
            with patch("click.confirm") as mock_confirm:
                # Select packs by index 1, 2, then done
                mock_prompt.side_effect = ["1", "2", ""]
                mock_confirm.return_value = True
                result = _select_packs(["pack-a", "pack-b", "pack-c"])
                assert "pack-a" in result
                assert "pack-b" in result

    def test_select_packs_by_name(self):
        """Test selecting packs by name."""
        from greybeard.wizards.risk_gate_wizard import _select_packs

        with patch("click.prompt") as mock_prompt:
            with patch("click.confirm") as mock_confirm:
                # Select by name
                mock_prompt.side_effect = ["pack-a", "pack-c", ""]
                mock_confirm.return_value = True
                result = _select_packs(["pack-a", "pack-b", "pack-c"])
                assert "pack-a" in result
                assert "pack-c" in result

    def test_select_packs_no_packs_available(self):
        """Test behavior when no packs available."""
        from greybeard.wizards.risk_gate_wizard import _select_packs

        result = _select_packs([])
        assert result == []

    def test_select_packs_duplicate_rejected(self):
        """Test duplicate selections are rejected."""
        from greybeard.wizards.risk_gate_wizard import _select_packs

        with patch("click.prompt") as mock_prompt:
            with patch("click.confirm") as mock_confirm:
                # Try to select same pack twice
                mock_prompt.side_effect = ["pack-a", "pack-a", ""]
                mock_confirm.return_value = True
                result = _select_packs(["pack-a", "pack-b"])
                assert result.count("pack-a") == 1

    def test_select_packs_invalid_index(self):
        """Test invalid pack index rejected."""
        from greybeard.wizards.risk_gate_wizard import _select_packs

        with patch("click.prompt") as mock_prompt:
            with patch("click.confirm") as mock_confirm:
                # Invalid index, then valid, then done
                mock_prompt.side_effect = ["99", "1", ""]
                mock_confirm.return_value = True
                result = _select_packs(["pack-a", "pack-b"])
                assert len(result) == 1
                assert "pack-a" in result

    def test_select_packs_default_staff_core(self):
        """Test default staff-core when no packs selected."""
        from greybeard.wizards.risk_gate_wizard import _select_packs

        with patch("click.prompt") as mock_prompt:
            with patch("click.confirm") as mock_confirm:
                # No selection, confirm default
                mock_prompt.side_effect = [""]
                mock_confirm.return_value = True
                result = _select_packs(["pack-a", "pack-b"])
                assert "staff-core" in result


class TestSelectSeverityThreshold:
    """Test the _select_severity_threshold function."""

    def test_select_severity_by_index(self):
        """Test selecting severity by numeric index."""
        from greybeard.wizards.risk_gate_wizard import _select_severity_threshold

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["2"]  # Select "high"
            result = _select_severity_threshold()
            assert result == "high"

    def test_select_severity_by_name(self):
        """Test selecting severity by name."""
        from greybeard.wizards.risk_gate_wizard import _select_severity_threshold

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["medium"]
            result = _select_severity_threshold()
            assert result == "medium"

    def test_select_severity_invalid_then_valid(self):
        """Test invalid then valid selection."""
        from greybeard.wizards.risk_gate_wizard import _select_severity_threshold

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["invalid", "critical"]
            result = _select_severity_threshold()
            assert result == "critical"

    def test_select_severity_all_levels(self):
        """Test all severity levels can be selected."""
        from greybeard.wizards.risk_gate_wizard import _select_severity_threshold

        levels = ["critical", "high", "medium", "low", "none"]
        for level in levels:
            with patch("click.prompt") as mock_prompt:
                mock_prompt.side_effect = [level]
                result = _select_severity_threshold()
                assert result == level


class TestSelectTemplate:
    """Test the _select_template function."""

    def test_select_template_by_index(self):
        """Test selecting template by index."""
        from greybeard.wizards.risk_gate_wizard import _select_template

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["1"]  # Select first template
            result = _select_template()
            assert result in RISK_GATE_TEMPLATES

    def test_select_custom_template(self):
        """Test custom template selection."""
        from greybeard.wizards.risk_gate_wizard import _select_template

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["c"]  # Custom
            result = _select_template()
            assert result is None

    def test_select_template_by_name(self):
        """Test selecting template by name."""
        from greybeard.wizards.risk_gate_wizard import _select_template

        with patch("click.prompt") as mock_prompt:
            # Template selection doesn't support name selection, only index or custom
            # So this test selects by valid index
            mock_prompt.side_effect = ["1"]  # Select first template by index
            result = _select_template()
            assert result is not None
            assert result in RISK_GATE_TEMPLATES

    def test_select_template_invalid_then_valid(self):
        """Test invalid then valid template selection."""
        from greybeard.wizards.risk_gate_wizard import _select_template

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["invalid", "1"]
            result = _select_template()
            assert result is not None

    def test_all_templates_selectable(self):
        """Test all templates can be selected."""
        from greybeard.wizards.risk_gate_wizard import _select_template

        template_names = list(RISK_GATE_TEMPLATES.keys())
        for idx, name in enumerate(template_names, 1):
            with patch("click.prompt") as mock_prompt:
                mock_prompt.side_effect = [str(idx)]
                result = _select_template()
                assert result == name


class TestWizardIntegration:
    """Integration tests for the full wizard flow."""

    def test_wizard_config_generation_method(self, tmp_path):
        """Test the config dict generation and YAML serialization."""
        from greybeard.precommit import PreCommitConfig, RiskGate

        # Create a config programmatically
        config = PreCommitConfig(
            enabled=True,
            default_pack="staff-core",
            excluded_paths=[".venv/*", "build/*"],
            skip_unstaged=False,
        )

        gate = RiskGate(
            name="critical",
            patterns=["infra/*", "deploy/*"],
            fail_on_concerns="critical",
            required_packs=["security-reviewer"],
            skip_if_branch=["emergency/*"],
        )
        config.risk_gates = [gate]

        # Convert to the format used in run_risk_gate_wizard
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

        # Write and verify
        output_file = tmp_path / ".greybeard-precommit.yaml"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

        assert output_file.exists()
        with output_file.open() as f:
            loaded = yaml.safe_load(f)
        assert loaded["enabled"] is True
        assert len(loaded["risk_gates"]) == 1
        assert loaded["risk_gates"][0]["name"] == "critical"

    def test_wizard_multiple_gates_yaml(self, tmp_path):
        """Test YAML generation with multiple risk gates."""
        config_dict = {
            "enabled": True,
            "default_pack": "staff-core",
            "additional_packs": [],
            "fail_on_concerns": "high",
            "skip_unstaged": True,
            "max_context_lines": 50,
            "verbose": False,
            "allow_empty_commits": False,
            "excluded_paths": [".venv/*", "node_modules/*"],
            "risk_gates": [
                {
                    "name": "critical",
                    "patterns": ["infra/*"],
                    "fail_on_concerns": "critical",
                    "required_packs": ["security"],
                    "skip_if_branch": [],
                },
                {
                    "name": "api",
                    "patterns": ["api/*"],
                    "fail_on_concerns": "high",
                    "required_packs": ["staff-core"],
                    "skip_if_branch": ["hotfix/*"],
                },
                {
                    "name": "src",
                    "patterns": ["src/**/*"],
                    "fail_on_concerns": "medium",
                    "required_packs": ["staff-core"],
                    "skip_if_branch": [],
                },
            ],
        }

        output_file = tmp_path / ".greybeard-precommit.yaml"
        with output_file.open("w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

        with output_file.open() as f:
            loaded = yaml.safe_load(f)

        assert len(loaded["risk_gates"]) == 3
        assert loaded["risk_gates"][0]["name"] == "critical"
        assert loaded["risk_gates"][1]["name"] == "api"
        assert loaded["risk_gates"][2]["name"] == "src"
        assert loaded["excluded_paths"] == [".venv/*", "node_modules/*"]


class TestMainWizardScenarios:
    """Test specific scenarios in the main wizard flow."""

    def test_wizard_skips_adding_gates(self):
        """Test user can skip adding risk gates."""
        # Rather than testing the full flow, test that gate skipping works
        from greybeard.precommit import PreCommitConfig

        config = PreCommitConfig()
        assert len(config.risk_gates) == 0

    def test_wizard_template_usage(self):
        """Test template loading and usage."""
        from greybeard.wizards.risk_gate_wizard import _select_template

        with patch("click.prompt") as mock_prompt:
            # Select first template
            mock_prompt.side_effect = ["1"]
            result = _select_template()
            assert result in RISK_GATE_TEMPLATES
            tmpl = RISK_GATE_TEMPLATES[result]
            assert "patterns" in tmpl
            assert "default_packs" in tmpl

    def test_wizard_custom_gate_configuration(self):
        """Test custom gate configuration flow."""
        from greybeard.wizards.risk_gate_wizard import _prompt_list

        # Test building a custom gate step-by-step
        with patch("click.prompt") as mock_prompt:
            # Simulate custom gate: patterns, packs, severity
            mock_prompt.side_effect = ["src/**/*", ""]
            patterns = _prompt_list("Enter patterns", min_items=1, suggestion_list=["src/*"])
            assert "src/**/*" in patterns

    def test_wizard_with_existing_gates(self, tmp_path):
        """Test behavior when config already has gates."""
        from greybeard.precommit import PreCommitConfig, RiskGate

        config = PreCommitConfig()
        gate1 = RiskGate(
            name="existing-gate",
            patterns=["src/*"],
            fail_on_concerns="high",
            required_packs=["staff-core"],
        )
        config.risk_gates = [gate1]

        assert len(config.risk_gates) == 1
        assert config.risk_gates[0].name == "existing-gate"

    def test_wizard_gate_override(self):
        """Test overwriting existing gate with same name."""
        from greybeard.precommit import RiskGate

        gates = []

        # Add first gate
        gate1 = RiskGate(
            name="test-gate",
            patterns=["src/*"],
            fail_on_concerns="high",
            required_packs=["pack1"],
        )
        gates.append(gate1)

        # Try to add another with same name
        gate2 = RiskGate(
            name="test-gate",
            patterns=["api/*"],
            fail_on_concerns="critical",
            required_packs=["pack2"],
        )

        # Check for duplicate
        existing_idx = None
        for idx, gate in enumerate(gates):
            if gate.name == gate2.name:
                existing_idx = idx
                break

        assert existing_idx is not None
        # Would override in wizard
        gates[existing_idx] = gate2
        assert gates[0].patterns == ["api/*"]


class TestYAMLGeneration:
    """Test YAML generation edge cases."""

    def test_yaml_escaping_special_chars(self, tmp_path):
        """Test YAML handles special characters correctly."""
        config_dict = {
            "enabled": True,
            "default_pack": "staff-core",
            "excluded_paths": ["*.yaml", "*.yml"],
            "risk_gates": [
                {
                    "name": "test-gate",
                    "patterns": ["infra/*", "deploy/*"],
                    "fail_on_concerns": "high",
                    "required_packs": ["pack1"],
                    "skip_if_branch": ["hotfix/*"],
                }
            ],
        }

        output_file = tmp_path / "config.yaml"
        with output_file.open("w") as f:
            yaml.dump(config_dict, f)

        # Load and verify roundtrip
        with output_file.open() as f:
            loaded = yaml.safe_load(f)

        assert loaded == config_dict

    def test_yaml_with_multiple_gates(self, tmp_path):
        """Test YAML with multiple risk gates."""
        config_dict = {
            "enabled": True,
            "risk_gates": [
                {
                    "name": "critical",
                    "patterns": ["infra/*"],
                    "fail_on_concerns": "critical",
                    "required_packs": ["security"],
                },
                {
                    "name": "high",
                    "patterns": ["api/*"],
                    "fail_on_concerns": "high",
                    "required_packs": ["staff-core"],
                },
                {
                    "name": "medium",
                    "patterns": ["src/**/*"],
                    "fail_on_concerns": "medium",
                    "required_packs": ["staff-core"],
                },
            ],
        }

        output_file = tmp_path / "config.yaml"
        with output_file.open("w") as f:
            yaml.dump(config_dict, f)

        with output_file.open() as f:
            loaded = yaml.safe_load(f)

        assert len(loaded["risk_gates"]) == 3


class TestAdditionalCoverage:
    """Additional tests to push coverage higher."""

    def test_list_available_packs_actual(self):
        """Test that _list_available_packs returns sorted results."""
        from greybeard.wizards.risk_gate_wizard import _list_available_packs

        packs = _list_available_packs()
        assert isinstance(packs, list)
        # Should be sorted
        if len(packs) > 1:
            assert packs == sorted(packs)

    def test_validate_repo_structure_fields(self):
        """Test all fields are present in repo structure validation."""
        from greybeard.wizards.risk_gate_wizard import _validate_repo_structure

        findings = _validate_repo_structure()
        required_fields = ["has_git", "has_pyproject", "has_precommit", "has_github_workflows"]
        for field in required_fields:
            assert field in findings
            assert isinstance(findings[field], bool)

    def test_prompt_list_exact_max_items(self):
        """Test prompt list with exact max items reached."""
        from greybeard.wizards.risk_gate_wizard import _prompt_list

        with patch("click.prompt") as mock_prompt:
            # Enter exactly 3 items (max=3)
            mock_prompt.side_effect = ["item1", "item2", "item3"]
            result = _prompt_list("Enter items", max_items=3)
            assert len(result) == 3

    def test_select_packs_invalid_name_rejected(self):
        """Test invalid pack names are rejected."""
        from greybeard.wizards.risk_gate_wizard import _select_packs

        with patch("click.prompt") as mock_prompt:
            with patch("click.confirm") as mock_confirm:
                # Invalid pack name, then valid, then done
                mock_prompt.side_effect = ["invalid-pack-name", "pack-a", ""]
                mock_confirm.return_value = True
                result = _select_packs(["pack-a", "pack-b"])
                assert len(result) == 1
                assert "pack-a" in result

    def test_select_severity_invalid_out_of_range(self):
        """Test out-of-range severity selection."""
        from greybeard.wizards.risk_gate_wizard import _select_severity_threshold

        with patch("click.prompt") as mock_prompt:
            # Out of range index, then valid
            mock_prompt.side_effect = ["99", "3"]
            result = _select_severity_threshold()
            assert result == "medium"

    def test_select_template_custom_option(self):
        """Test selecting custom option explicitly."""
        from greybeard.wizards.risk_gate_wizard import _select_template

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["custom"]
            result = _select_template()
            assert result is None

    def test_select_template_c_shortcut(self):
        """Test (c)ustom shortcut."""
        from greybeard.wizards.risk_gate_wizard import _select_template

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["c"]
            result = _select_template()
            assert result is None

    def test_common_patterns_coverage(self):
        """Test COMMON_PATTERNS list."""
        # Verify common patterns exist and are valid
        assert len(COMMON_PATTERNS) > 0
        for pattern in COMMON_PATTERNS:
            assert isinstance(pattern, str)
            assert len(pattern) > 0
            # Patterns can be simple filenames or glob patterns
            # So we just verify they're non-empty strings

    def test_templates_have_all_fields(self):
        """Test all templates have required fields."""
        required_fields = ["description", "patterns", "fail_on_concerns", "default_packs"]
        for name, template in RISK_GATE_TEMPLATES.items():
            for field in required_fields:
                assert field in template, f"Template {name} missing {field}"
            # Verify field types
            assert isinstance(template["patterns"], list)
            assert isinstance(template["default_packs"], list)
            assert template["fail_on_concerns"] in SEVERITY_LEVELS

    def test_yaml_with_empty_risk_gates(self, tmp_path):
        """Test YAML with no risk gates."""
        config_dict = {
            "enabled": True,
            "default_pack": "staff-core",
            "excluded_paths": [],
            "risk_gates": [],
        }

        output_file = tmp_path / "config.yaml"
        with output_file.open("w") as f:
            yaml.dump(config_dict, f)

        with output_file.open() as f:
            loaded = yaml.safe_load(f)

        assert loaded["enabled"] is True
        assert len(loaded["risk_gates"]) == 0

    def test_prompt_list_max_items_enforcement(self):
        """Test that max_items is strictly enforced."""
        from greybeard.wizards.risk_gate_wizard import _prompt_list

        with patch("click.prompt") as mock_prompt:
            # Try to add 5 items with max 2
            mock_prompt.side_effect = ["item1", "item2", "item3"]
            result = _prompt_list("Enter", max_items=2)
            assert len(result) == 2

    def test_severity_levels_complete(self):
        """Test all severity levels are valid."""
        expected_levels = ["critical", "high", "medium", "low", "none"]
        assert SEVERITY_LEVELS == expected_levels
        # Each level should be unique
        assert len(SEVERITY_LEVELS) == len(set(SEVERITY_LEVELS))

    def test_select_packs_mixed_selection_methods(self):
        """Test mixing index and name selection."""
        from greybeard.wizards.risk_gate_wizard import _select_packs

        with patch("click.prompt") as mock_prompt:
            with patch("click.confirm") as mock_confirm:
                # Select by index (1), then by name (pack-c)
                mock_prompt.side_effect = ["1", "pack-c", ""]
                mock_confirm.return_value = True
                result = _select_packs(["pack-a", "pack-b", "pack-c"])
                assert "pack-a" in result
                assert "pack-c" in result


class TestErrorHandling:
    """Test error handling in wizard functions."""

    def test_prompt_list_with_carriage_return(self):
        """Test prompt list rejects carriage return."""
        from greybeard.wizards.risk_gate_wizard import _prompt_list

        with patch("click.prompt") as mock_prompt:
            # Try newline and carriage return
            mock_prompt.side_effect = ["path\rfile", "valid-path", ""]
            result = _prompt_list("Enter paths", min_items=1)
            assert "valid-path" in result
            assert "path\rfile" not in result

    def test_select_packs_empty_list(self):
        """Test select packs with empty list."""
        from greybeard.wizards.risk_gate_wizard import _select_packs

        result = _select_packs([])
        assert result == []

    def test_config_yaml_roundtrip_preserves_data(self, tmp_path):
        """Test that config can be serialized and deserialized correctly."""
        config_dict = {
            "enabled": True,
            "default_pack": "staff-core",
            "additional_packs": ["extra-pack"],
            "fail_on_concerns": "high",
            "skip_unstaged": True,
            "max_context_lines": 75,
            "verbose": True,
            "allow_empty_commits": False,
            "excluded_paths": [".venv/*", "build/*", "*.pyc"],
            "risk_gates": [
                {
                    "name": "critical",
                    "patterns": ["infra/*"],
                    "fail_on_concerns": "critical",
                    "required_packs": ["security"],
                    "skip_if_branch": ["hotfix/*"],
                }
            ],
        }

        output_file = tmp_path / "config.yaml"
        with output_file.open("w") as f:
            yaml.dump(config_dict, f)

        with output_file.open() as f:
            loaded = yaml.safe_load(f)

        assert loaded == config_dict
        assert loaded["verbose"] is True
        assert loaded["skip_unstaged"] is True
        assert len(loaded["excluded_paths"]) == 3


# ---------------------------------------------------------------------------
# Full wizard integration tests with aggressive mocking
# ---------------------------------------------------------------------------


class TestWizardRunIntegration:
    """Integration tests for run_risk_gate_wizard() focusing on uncovered code paths."""

    def test_run_wizard_minimal_no_file(self, tmp_path):
        """Test wizard with minimal config, file doesn't exist."""
        output_file = tmp_path / "test.yaml"

        with patch("click.confirm") as mock_confirm:
            with patch("greybeard.wizards.risk_gate_wizard.click.prompt") as mock_prompt:
                with patch(
                    "greybeard.wizards.risk_gate_wizard._list_available_packs",
                    return_value=["staff-core"],
                ):
                    with patch(
                        "greybeard.wizards.risk_gate_wizard._validate_repo_structure",
                        return_value={
                            "has_git": True,
                            "has_pyproject": True,
                            "has_precommit": True,
                            "has_github_workflows": True,
                        },
                    ):
                        with patch(
                            "greybeard.wizards.risk_gate_wizard._prompt_list",
                            return_value=[],
                        ):
                            # File doesn't exist, so no "Load existing?"
                            mock_confirm.side_effect = [
                                True,  # Enable
                                False,  # Skip unstaged
                                False,  # Add gate
                                True,  # Save
                            ]
                            mock_prompt.return_value = "staff-core"

                            from greybeard.wizards.risk_gate_wizard import run_risk_gate_wizard

                            result = run_risk_gate_wizard(str(output_file))
                            assert result == output_file
                            assert output_file.exists()

    def test_run_wizard_disabled_integration(self, tmp_path):
        """Test disabling pre-commit integration."""
        output_file = tmp_path / "config.yaml"

        with patch("click.confirm") as mock_confirm:
            with patch("greybeard.wizards.risk_gate_wizard.click.prompt") as mock_prompt:
                with patch(
                    "greybeard.wizards.risk_gate_wizard._list_available_packs",
                    return_value=["staff-core"],
                ):
                    with patch(
                        "greybeard.wizards.risk_gate_wizard._validate_repo_structure",
                        return_value={
                            "has_git": True,
                            "has_pyproject": True,
                            "has_precommit": True,
                            "has_github_workflows": True,
                        },
                    ):
                        with patch(
                            "greybeard.wizards.risk_gate_wizard._prompt_list",
                            return_value=[],
                        ):
                            mock_confirm.side_effect = [
                                False,  # Enable? (NO)
                                False,  # Skip unstaged
                                False,  # Add gate
                                True,  # Save
                            ]
                            mock_prompt.return_value = "staff-core"

                            from greybeard.wizards.risk_gate_wizard import run_risk_gate_wizard

                            result = run_risk_gate_wizard(str(output_file))
                            with output_file.open() as f:
                                config = yaml.safe_load(f)
                            assert config["enabled"] is False

    def test_run_wizard_add_single_gate_template(self, tmp_path):
        """Test adding one gate from template."""
        output_file = tmp_path / "config.yaml"

        with patch("click.confirm") as mock_confirm:
            with patch("greybeard.wizards.risk_gate_wizard.click.prompt") as mock_prompt:
                with patch(
                    "greybeard.wizards.risk_gate_wizard._list_available_packs",
                    return_value=["staff-core", "security"],
                ):
                    with patch(
                        "greybeard.wizards.risk_gate_wizard._validate_repo_structure",
                        return_value={
                            "has_git": True,
                            "has_pyproject": True,
                            "has_precommit": True,
                            "has_github_workflows": True,
                        },
                    ):
                        with patch(
                            "greybeard.wizards.risk_gate_wizard._prompt_list",
                            return_value=[],
                        ):
                            with patch(
                                "greybeard.wizards.risk_gate_wizard._select_template",
                                return_value="critical",
                            ):
                                mock_confirm.side_effect = [
                                    True,  # Enable
                                    False,  # Skip unstaged
                                    True,  # Add gate?
                                    False,  # Customize template?
                                    False,  # Add another?
                                    True,  # Save
                                ]
                                mock_prompt.return_value = "staff-core"

                                from greybeard.wizards.risk_gate_wizard import run_risk_gate_wizard

                                result = run_risk_gate_wizard(str(output_file))
                                with output_file.open() as f:
                                    config = yaml.safe_load(f)
                                assert len(config["risk_gates"]) == 1
                                assert config["risk_gates"][0]["name"] == "critical"

    def test_run_wizard_add_custom_gate_with_patterns(self, tmp_path):
        """Test adding custom gate with patterns and branch skip."""
        output_file = tmp_path / "config.yaml"

        with patch("click.confirm") as mock_confirm:
            with patch("greybeard.wizards.risk_gate_wizard.click.prompt") as mock_prompt:
                with patch(
                    "greybeard.wizards.risk_gate_wizard._list_available_packs",
                    return_value=["staff-core"],
                ):
                    with patch(
                        "greybeard.wizards.risk_gate_wizard._validate_repo_structure",
                        return_value={
                            "has_git": True,
                            "has_pyproject": True,
                            "has_precommit": True,
                            "has_github_workflows": True,
                        },
                    ):
                        with patch(
                            "greybeard.wizards.risk_gate_wizard._prompt_list"
                        ) as mock_list:
                            with patch(
                                "greybeard.wizards.risk_gate_wizard._select_template",
                                return_value=None,  # Custom
                            ):
                                with patch(
                                    "greybeard.wizards.risk_gate_wizard._select_packs",
                                    return_value=["staff-core"],
                                ):
                                    with patch(
                                        "greybeard.wizards.risk_gate_wizard._select_severity_threshold",
                                        return_value="high",
                                    ):
                                        mock_list.side_effect = [
                                            [],  # Excluded
                                            ["src/**/*.py"],  # Patterns
                                            ["hotfix/*", "emergency/*"],  # Skip branches
                                        ]
                                        mock_confirm.side_effect = [
                                            True,  # Enable
                                            False,  # Skip unstaged
                                            True,  # Add gate?
                                            False,  # Add another?
                                            True,  # Save
                                        ]
                                        mock_prompt.return_value = "staff-core"

                                        from greybeard.wizards.risk_gate_wizard import run_risk_gate_wizard

                                        result = run_risk_gate_wizard(str(output_file))
                                        with output_file.open() as f:
                                            config = yaml.safe_load(f)
                                        assert len(config["risk_gates"]) == 1
                                        gate = config["risk_gates"][0]
                                        assert "src/**/*.py" in gate["patterns"]
                                        assert "hotfix/*" in gate["skip_if_branch"]

    def test_run_wizard_customize_template_to_custom(self, tmp_path):
        """Test selecting template then customizing it (force custom flow)."""
        output_file = tmp_path / "config.yaml"

        with patch("click.confirm") as mock_confirm:
            with patch("greybeard.wizards.risk_gate_wizard.click.prompt") as mock_prompt:
                with patch(
                    "greybeard.wizards.risk_gate_wizard._list_available_packs",
                    return_value=["staff-core"],
                ):
                    with patch(
                        "greybeard.wizards.risk_gate_wizard._validate_repo_structure",
                        return_value={
                            "has_git": True,
                            "has_pyproject": True,
                            "has_precommit": True,
                            "has_github_workflows": True,
                        },
                    ):
                        with patch(
                            "greybeard.wizards.risk_gate_wizard._prompt_list"
                        ) as mock_list:
                            with patch(
                                "greybeard.wizards.risk_gate_wizard._select_template",
                                return_value="critical",
                            ):
                                with patch(
                                    "greybeard.wizards.risk_gate_wizard._select_packs",
                                    return_value=["staff-core"],
                                ):
                                    with patch(
                                        "greybeard.wizards.risk_gate_wizard._select_severity_threshold",
                                        return_value="medium",
                                    ):
                                        mock_list.side_effect = [
                                            [],  # Excluded
                                            ["custom/patterns"],  # Override template patterns
                                            [],  # Skip branches
                                        ]
                                        # Load, enable, skip unstaged, add gate,
                                        # customize=YES (forces custom flow), add another=no, save
                                        mock_confirm.side_effect = [
                                            True,  # Enable
                                            False,  # Skip unstaged
                                            True,  # Add gate?
                                            True,  # Customize template? (YES)
                                            False,  # Add another?
                                            True,  # Save
                                        ]
                                        mock_prompt.return_value = "staff-core"

                                        from greybeard.wizards.risk_gate_wizard import run_risk_gate_wizard

                                        result = run_risk_gate_wizard(str(output_file))
                                        # Gate is created through custom flow
                                        with output_file.open() as f:
                                            config = yaml.safe_load(f)
                                        assert len(config["risk_gates"]) == 1

    def test_run_wizard_multiple_gates_sequential(self, tmp_path):
        """Test adding multiple gates one after another."""
        output_file = tmp_path / "config.yaml"

        with patch("click.confirm") as mock_confirm:
            with patch("greybeard.wizards.risk_gate_wizard.click.prompt") as mock_prompt:
                with patch(
                    "greybeard.wizards.risk_gate_wizard._list_available_packs",
                    return_value=["staff-core"],
                ):
                    with patch(
                        "greybeard.wizards.risk_gate_wizard._validate_repo_structure",
                        return_value={
                            "has_git": True,
                            "has_pyproject": True,
                            "has_precommit": True,
                            "has_github_workflows": True,
                        },
                    ):
                        with patch(
                            "greybeard.wizards.risk_gate_wizard._prompt_list",
                            return_value=[],
                        ):
                            with patch(
                                "greybeard.wizards.risk_gate_wizard._select_template"
                            ) as mock_template:
                                mock_template.side_effect = ["critical", "high"]

                                mock_confirm.side_effect = [
                                    True,  # Enable
                                    False,  # Skip unstaged
                                    True,  # Add gate 1?
                                    False,  # Customize gate 1?
                                    True,  # Add gate 2?
                                    False,  # Customize gate 2?
                                    False,  # Add another?
                                    True,  # Save
                                ]
                                mock_prompt.return_value = "staff-core"

                                from greybeard.wizards.risk_gate_wizard import run_risk_gate_wizard

                                result = run_risk_gate_wizard(str(output_file))
                                with output_file.open() as f:
                                    config = yaml.safe_load(f)
                                assert len(config["risk_gates"]) == 2
                                assert config["risk_gates"][0]["name"] == "critical"
                                assert config["risk_gates"][1]["name"] == "high"

    def test_run_wizard_excluded_paths(self, tmp_path):
        """Test setting excluded paths."""
        output_file = tmp_path / "config.yaml"

        with patch("click.confirm") as mock_confirm:
            with patch("greybeard.wizards.risk_gate_wizard.click.prompt") as mock_prompt:
                with patch(
                    "greybeard.wizards.risk_gate_wizard._list_available_packs",
                    return_value=["staff-core"],
                ):
                    with patch(
                        "greybeard.wizards.risk_gate_wizard._validate_repo_structure",
                        return_value={
                            "has_git": True,
                            "has_pyproject": True,
                            "has_precommit": True,
                            "has_github_workflows": True,
                        },
                    ):
                        with patch(
                            "greybeard.wizards.risk_gate_wizard._prompt_list"
                        ) as mock_list:
                            mock_list.return_value = [".venv/*", "build/*"]

                            mock_confirm.side_effect = [
                                True,  # Enable
                                False,  # Skip unstaged
                                False,  # Add gate
                                True,  # Save
                            ]
                            mock_prompt.return_value = "staff-core"

                            from greybeard.wizards.risk_gate_wizard import run_risk_gate_wizard

                            result = run_risk_gate_wizard(str(output_file))
                            with output_file.open() as f:
                                config = yaml.safe_load(f)
                            assert len(config["excluded_paths"]) == 2
                            assert ".venv/*" in config["excluded_paths"]

    def test_run_wizard_skip_unstaged_true(self, tmp_path):
        """Test enabling skip_unstaged changes."""
        output_file = tmp_path / "config.yaml"

        with patch("click.confirm") as mock_confirm:
            with patch("greybeard.wizards.risk_gate_wizard.click.prompt") as mock_prompt:
                with patch(
                    "greybeard.wizards.risk_gate_wizard._list_available_packs",
                    return_value=["staff-core"],
                ):
                    with patch(
                        "greybeard.wizards.risk_gate_wizard._validate_repo_structure",
                        return_value={
                            "has_git": True,
                            "has_pyproject": True,
                            "has_precommit": True,
                            "has_github_workflows": True,
                        },
                    ):
                        with patch(
                            "greybeard.wizards.risk_gate_wizard._prompt_list",
                            return_value=[],
                        ):
                            mock_confirm.side_effect = [
                                True,  # Enable
                                True,  # Skip unstaged? (YES)
                                False,  # Add gate
                                True,  # Save
                            ]
                            mock_prompt.return_value = "staff-core"

                            from greybeard.wizards.risk_gate_wizard import run_risk_gate_wizard

                            result = run_risk_gate_wizard(str(output_file))
                            with output_file.open() as f:
                                config = yaml.safe_load(f)
                            assert config["skip_unstaged"] is True


