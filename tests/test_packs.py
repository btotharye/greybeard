"""Tests for content pack loading."""

from __future__ import annotations

import pytest
import yaml

from staff_review.models import ContentPack
from staff_review.packs import (
    BUILTIN_PACK_NAMES,
    _source_slug,
    list_builtin_packs,
    list_installed_packs,
    load_pack,
)


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

    @pytest.mark.parametrize("pack_name", BUILTIN_PACK_NAMES)
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
        pack_file.write_text(
            yaml.dump(
                {
                    "name": "my-pack",
                    "perspective": "A test perspective",
                    "tone": "testing tone",
                    "focus_areas": ["area1", "area2"],
                    "heuristics": ["heuristic one", "heuristic two"],
                    "example_questions": ["Question 1?"],
                    "communication_style": "Be clear.",
                    "description": "Test pack",
                }
            )
        )
        pack = load_pack(str(pack_file))
        assert pack.name == "my-pack"
        assert pack.perspective == "A test perspective"
        assert pack.heuristics == ["heuristic one", "heuristic two"]

    def test_loads_with_missing_optional_fields(self, tmp_path):
        pack_file = tmp_path / "minimal.yaml"
        pack_file.write_text(yaml.dump({"name": "minimal", "perspective": "Min", "tone": "calm"}))
        pack = load_pack(str(pack_file))
        assert pack.heuristics == []
        assert pack.communication_style == ""

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_pack("/nonexistent/path/pack.yaml")

    def test_uses_stem_as_name_if_name_not_in_yaml(self, tmp_path):
        pack_file = tmp_path / "auto-named.yaml"
        pack_file.write_text(yaml.dump({"perspective": "Some", "tone": "direct"}))
        pack = load_pack(str(pack_file))
        assert pack.name == "auto-named"


class TestListBuiltinPacks:
    def test_returns_list(self):
        packs = list_builtin_packs()
        assert isinstance(packs, list)
        assert len(packs) > 0

    def test_includes_expected_packs(self):
        packs = list_builtin_packs()
        for expected in BUILTIN_PACK_NAMES:
            assert expected in packs


class TestListInstalledPacks:
    def test_returns_empty_when_no_cache(self, tmp_path, monkeypatch):
        monkeypatch.setattr("staff_review.packs.PACK_CACHE_DIR", tmp_path / "empty-packs")
        result = list_installed_packs()
        assert result == []

    def test_finds_cached_packs(self, tmp_path, monkeypatch):
        cache = tmp_path / "packs"
        source_dir = cache / "test__source"
        source_dir.mkdir(parents=True)
        pack_file = source_dir / "my-cached-pack.yaml"
        pack_file.write_text(
            yaml.dump(
                {
                    "name": "my-cached-pack",
                    "perspective": "Cached perspective",
                    "tone": "calm",
                    "description": "A cached test pack",
                }
            )
        )
        monkeypatch.setattr("staff_review.packs.PACK_CACHE_DIR", cache)

        result = list_installed_packs()
        assert len(result) == 1
        assert result[0]["name"] == "my-cached-pack"
        assert result[0]["source"] == "test__source"


class TestSourceSlug:
    def test_github_source(self):
        slug = _source_slug("github:owner/repo")
        assert "owner" in slug
        assert "repo" in slug
        assert "/" not in slug

    def test_url_source(self):
        slug = _source_slug("https://example.com/packs/my-pack.yaml")
        assert "/" not in slug
        assert len(slug) < 80

    def test_long_source_truncated(self):
        long = "github:" + "a" * 100 + "/" + "b" * 100
        slug = _source_slug(long)
        assert len(slug) <= 64


class TestContentPackPromptFragment:
    def test_fragment_includes_perspective(self):
        pack = load_pack("staff-core")
        fragment = pack.to_system_prompt_fragment()
        assert pack.perspective[:20] in fragment

    def test_fragment_includes_heuristics(self):
        pack = load_pack("staff-core")
        fragment = pack.to_system_prompt_fragment()
        assert any(h[:20] in fragment for h in pack.heuristics)

    def test_fragment_includes_tone(self):
        pack = load_pack("staff-core")
        fragment = pack.to_system_prompt_fragment()
        assert pack.tone[:10] in fragment
