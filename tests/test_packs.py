"""Tests for content pack loading."""

from __future__ import annotations

import pytest
import yaml

from staff_review.models import ContentPack
from staff_review.packs import BUILTIN_PACKS, list_builtin_packs, load_pack


class TestLoadBuiltinPacks:
    def test_loads_staff_core(self):
        pack = load_pack("staff-core")
        assert isinstance(pack, ContentPack)
        assert pack.name == "staff-core"
        assert pack.perspective
        assert pack.tone
        assert len(pack.heuristics) > 0
        assert len(pack.example_questions) > 0

    def test_loads_oncall_future_you(self):
        pack = load_pack("oncall-future-you")
        assert pack.name == "oncall-future-you"
        assert "3am" in pack.perspective.lower() or "on-call" in pack.perspective.lower()

    def test_loads_mentor_mode(self):
        pack = load_pack("mentor-mode")
        assert pack.name == "mentor-mode"
        assert pack.tone

    def test_loads_solutions_architect(self):
        pack = load_pack("solutions-architect")
        assert pack.name == "solutions-architect"
        assert len(pack.heuristics) > 0

    def test_loads_idp_readiness(self):
        pack = load_pack("idp-readiness")
        assert pack.name == "idp-readiness"
        assert len(pack.focus_areas) > 0

    @pytest.mark.parametrize("pack_name", BUILTIN_PACKS)
    def test_all_builtin_packs_load(self, pack_name):
        pack = load_pack(pack_name)
        assert pack.name == pack_name
        assert pack.perspective
        assert pack.tone

    def test_raises_on_unknown_pack(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_pack("nonexistent-pack")


class TestLoadCustomPack:
    def test_loads_from_yaml_file(self, tmp_path):
        pack_file = tmp_path / "my-pack.yaml"
        pack_file.write_text(yaml.dump({
            "name": "my-pack",
            "perspective": "A test perspective",
            "tone": "testing tone",
            "focus_areas": ["area1", "area2"],
            "heuristics": ["heuristic one", "heuristic two"],
            "example_questions": ["Question 1?"],
            "communication_style": "Be clear.",
            "description": "Test pack",
        }))
        pack = load_pack(str(pack_file))
        assert pack.name == "my-pack"
        assert pack.perspective == "A test perspective"
        assert pack.tone == "testing tone"
        assert pack.focus_areas == ["area1", "area2"]
        assert pack.heuristics == ["heuristic one", "heuristic two"]
        assert pack.example_questions == ["Question 1?"]

    def test_loads_with_missing_optional_fields(self, tmp_path):
        pack_file = tmp_path / "minimal.yaml"
        pack_file.write_text(yaml.dump({
            "name": "minimal",
            "perspective": "Minimal perspective",
            "tone": "calm",
        }))
        pack = load_pack(str(pack_file))
        assert pack.name == "minimal"
        assert pack.heuristics == []
        assert pack.example_questions == []
        assert pack.communication_style == ""

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_pack("/nonexistent/path/pack.yaml")

    def test_uses_stem_as_name_if_name_not_in_yaml(self, tmp_path):
        pack_file = tmp_path / "auto-named.yaml"
        pack_file.write_text(yaml.dump({
            "perspective": "Some perspective",
            "tone": "direct",
        }))
        pack = load_pack(str(pack_file))
        assert pack.name == "auto-named"


class TestListBuiltinPacks:
    def test_returns_list(self):
        packs = list_builtin_packs()
        assert isinstance(packs, list)
        assert len(packs) > 0

    def test_includes_expected_packs(self):
        packs = list_builtin_packs()
        for expected in BUILTIN_PACKS:
            assert expected in packs


class TestContentPackPromptFragment:
    def test_fragment_includes_perspective(self):
        pack = load_pack("staff-core")
        fragment = pack.to_system_prompt_fragment()
        assert "perspective" in fragment.lower() or pack.perspective[:20] in fragment

    def test_fragment_includes_heuristics(self):
        pack = load_pack("staff-core")
        fragment = pack.to_system_prompt_fragment()
        # At least one heuristic should appear in the fragment
        assert any(h[:20] in fragment for h in pack.heuristics)

    def test_fragment_includes_tone(self):
        pack = load_pack("staff-core")
        fragment = pack.to_system_prompt_fragment()
        assert pack.tone[:10] in fragment
