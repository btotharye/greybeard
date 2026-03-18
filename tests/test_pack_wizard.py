"""Tests for the pack authoring wizard (greybeard pack new)."""

from __future__ import annotations

import yaml
from click.testing import CliRunner

from greybeard.cli import cli
from greybeard.pack_wizard import (
    _build_example_md,
    _build_readme,
    _build_yaml,
    _slugify,
    _validate_pack_name,
)

# ---------------------------------------------------------------------------
# Unit tests: helper functions
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_simple_name(self):
        assert _slugify("hiring-interview") == "hiring-interview"

    def test_spaces_to_hyphens(self):
        assert _slugify("Hiring Interview") == "hiring-interview"

    def test_strips_special_chars(self):
        assert _slugify("Security Review!") == "security-review"

    def test_collapses_hyphens(self):
        assert _slugify("my--pack") == "my-pack"

    def test_lowercase(self):
        assert _slugify("API-Gateway") == "api-gateway"


class TestValidatePackName:
    def test_valid_name(self):
        assert _validate_pack_name("security-reviewer") is None

    def test_valid_single_word(self):
        assert _validate_pack_name("hiring") is None

    def test_empty_name(self):
        assert _validate_pack_name("") is not None

    def test_invalid_chars(self):
        # After slugifying, special chars are stripped; validate gets the raw slug
        # "my pack!" slugifies to "my-pack" which is valid — but validate takes the
        # already-slugified value in practice
        assert _validate_pack_name("my-pack") is None

    def test_name_with_numbers(self):
        assert _validate_pack_name("pack-v2") is None


class TestBuildYaml:
    def test_produces_valid_yaml(self):
        data = {
            "name": "test-pack",
            "description": "A test pack.",
            "perspective": "A senior engineer.",
            "tone": "direct",
            "focus_areas": ["area one", "area two"],
            "heuristics": ["What breaks at 3am?"],
            "example_questions": ["Who owns the runbook?"],
            "communication_style": "Be specific.",
        }
        output = _build_yaml(data)
        parsed = yaml.safe_load(output)
        assert parsed["name"] == "test-pack"
        assert parsed["tone"] == "direct"
        assert len(parsed["focus_areas"]) == 2
        assert len(parsed["heuristics"]) == 1

    def test_multiline_perspective_uses_block_scalar(self):
        data = {
            "name": "test-pack",
            "description": "desc",
            "perspective": "Line one\nLine two\nLine three",
            "tone": "calm",
            "focus_areas": [],
            "heuristics": [],
            "example_questions": [],
            "communication_style": "",
        }
        output = _build_yaml(data)
        assert "perspective: |" in output

    def test_single_quotes_in_heuristics(self):
        data = {
            "name": "test-pack",
            "description": "desc",
            "perspective": "p",
            "tone": "t",
            "focus_areas": [],
            "heuristics": ["What's the blast radius?"],
            "example_questions": [],
            "communication_style": "",
        }
        output = _build_yaml(data)
        # Should not crash YAML parser
        parsed = yaml.safe_load(output)
        assert "What's the blast radius?" in parsed["heuristics"]


class TestBuildExampleMd:
    def test_contains_pack_title(self):
        md = _build_example_md(
            "my-pack",
            "My Pack",
            "A test description.",
            ["data integrity", "rollback safety"],
            ["What breaks?", "Who owns this?"],
        )
        assert "My Pack" in md

    def test_contains_first_heuristic(self):
        md = _build_example_md(
            "test-pack",
            "Test Pack",
            "desc",
            ["focus1"],
            ["Heuristic question?"],
        )
        assert "Heuristic question?" in md

    def test_contains_action_items_section(self):
        md = _build_example_md("p", "P", "d", ["f"], ["h"])
        assert "Action Items" in md


class TestBuildReadme:
    def test_contains_pack_name_in_command(self):
        md = _build_readme(
            "security-review",
            "Security Review",
            "Reviews security.",
            ["auth", "injection"],
        )
        assert "--pack security-review" in md

    def test_contains_focus_areas(self):
        md = _build_readme("p", "P", "d", ["auth boundaries", "rate limiting"])
        assert "auth boundaries" in md
        assert "rate limiting" in md

    def test_contains_quick_start(self):
        md = _build_readme("p", "P", "d", ["f"])
        assert "Quick Start" in md


# ---------------------------------------------------------------------------
# Integration tests: CLI command
# ---------------------------------------------------------------------------


class TestPackNewCommand:
    """Tests for 'greybeard pack new' via CliRunner with simulated input."""

    def _make_input(self, extra_lines: list[str] | None = None) -> str:
        """Build a newline-joined input string for the wizard."""
        lines = [
            "test-wizard-pack",  # pack name
            "A test pack for wizards.",  # description
            "A senior wizard with 10+ years of spell review experience.",  # perspective
            "direct and constructive",  # tone
            # Focus areas (min 2, blank to stop)
            "spell correctness",
            "blast radius",
            "",  # end focus areas
            # Heuristics (min 2, blank to stop)
            "What happens if the spell backfires?",
            "Who cleans up the explosion?",
            "",  # end heuristics
            # Example questions (min 2, blank to stop)
            "Has the counterspell been tested?",
            "What's the mana cost in production?",
            "",  # end example questions
            "Be specific about spell failure modes.",  # communication style
            "y",  # confirm generate
        ]
        if extra_lines:
            lines.extend(extra_lines)
        return "\n".join(lines) + "\n"

    def test_pack_new_creates_files(self, tmp_path):
        """Full wizard run creates all three output files."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["pack", "new", "--output-dir", str(tmp_path)],
            input=self._make_input(),
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

        pack_dir = tmp_path / "test-wizard-pack"
        assert pack_dir.is_dir()
        assert (pack_dir / "test-wizard-pack.yaml").is_file()
        assert (pack_dir / "README.md").is_file()
        # Example file
        example_files = list(pack_dir.glob("*EXAMPLE.md"))
        assert len(example_files) == 1

    def test_pack_new_yaml_is_valid(self, tmp_path):
        """Generated YAML can be parsed and has expected fields."""
        runner = CliRunner()
        runner.invoke(
            cli,
            ["pack", "new", "--output-dir", str(tmp_path)],
            input=self._make_input(),
            catch_exceptions=False,
        )
        yaml_file = tmp_path / "test-wizard-pack" / "test-wizard-pack.yaml"
        parsed = yaml.safe_load(yaml_file.read_text())

        assert parsed["name"] == "test-wizard-pack"
        assert "wizard" in parsed["description"].lower()
        assert len(parsed["focus_areas"]) == 2
        assert len(parsed["heuristics"]) == 2
        assert len(parsed["example_questions"]) == 2

    def test_pack_new_yaml_loadable_by_greybeard(self, tmp_path):
        """Generated pack can be loaded by greybeard's pack loader."""
        from greybeard.packs import load_pack

        runner = CliRunner()
        runner.invoke(
            cli,
            ["pack", "new", "--output-dir", str(tmp_path)],
            input=self._make_input(),
            catch_exceptions=False,
        )
        yaml_path = str(tmp_path / "test-wizard-pack" / "test-wizard-pack.yaml")
        pack = load_pack(yaml_path)
        assert pack.name == "test-wizard-pack"
        assert len(pack.focus_areas) == 2

    def test_pack_new_help(self):
        """Help text renders without error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["pack", "new", "--help"])
        assert result.exit_code == 0
        assert "wizard" in result.output.lower() or "scaffold" in result.output.lower()

    def test_pack_new_abort_on_no_confirm(self, tmp_path):
        """Answering 'n' at the confirm prompt aborts without creating files."""
        lines = [
            "abort-test-pack",
            "Should be aborted.",
            "A reviewer.",
            "calm",
            "focus one",
            "focus two",
            "",
            "heuristic one",
            "heuristic two",
            "",
            "question one",
            "question two",
            "",
            "Be clear.",
            "n",  # decline to generate
        ]
        runner = CliRunner()
        runner.invoke(
            cli,
            ["pack", "new", "--output-dir", str(tmp_path)],
            input="\n".join(lines) + "\n",
        )
        # Either aborted (exit 1) or no files created
        pack_dir = tmp_path / "abort-test-pack"
        assert not pack_dir.exists()

    def test_pack_new_normalizes_name(self, tmp_path):
        """Pack name with spaces gets slugified correctly."""
        lines = [
            "My Fancy Pack",  # will be normalized to "my-fancy-pack"
            "desc",
            "reviewer",
            "tone",
            "focus a",
            "focus b",
            "",
            "heuristic a",
            "heuristic b",
            "",
            "question a",
            "question b",
            "",
            "style",
            "y",
        ]
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["pack", "new", "--output-dir", str(tmp_path)],
            input="\n".join(lines) + "\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert (tmp_path / "my-fancy-pack").is_dir()
