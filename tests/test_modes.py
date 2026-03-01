"""Tests for mode prompt construction."""

from __future__ import annotations

import pytest

from staff_review.modes import build_system_prompt
from staff_review.packs import load_pack


@pytest.fixture
def staff_core():
    return load_pack("staff-core")


class TestBuildSystemPrompt:
    def test_review_mode_includes_core_lenses(self, staff_core):
        prompt = build_system_prompt("review", staff_core)
        assert "OPERATIONAL IMPACT" in prompt
        assert "LONG-TERM OWNERSHIP" in prompt
        assert "ON-CALL" in prompt
        assert "WHO PAYS" in prompt

    def test_review_mode_includes_core_behavior(self, staff_core):
        prompt = build_system_prompt("review", staff_core)
        assert "good faith" in prompt.lower()
        assert "nitpick" in prompt.lower()

    def test_review_mode_includes_output_format(self, staff_core):
        prompt = build_system_prompt("review", staff_core)
        assert "## Summary" in prompt
        assert "## Key Risks" in prompt
        assert "## Tradeoffs" in prompt
        assert "## Questions to Answer" in prompt

    def test_mentor_mode_includes_teaching_instructions(self, staff_core):
        prompt = build_system_prompt("mentor", staff_core)
        assert "MENTOR" in prompt
        assert "teaching" in prompt.lower() or "explain" in prompt.lower()

    def test_coach_mode_includes_audience(self, staff_core):
        prompt = build_system_prompt("coach", staff_core, audience="leadership")
        assert "leadership" in prompt.lower()

    def test_coach_mode_default_audience(self, staff_core):
        prompt = build_system_prompt("coach", staff_core, audience=None)
        assert "peer" in prompt.lower()

    def test_self_check_mode_includes_self_review_language(self, staff_core):
        prompt = build_system_prompt("self-check", staff_core)
        assert "SELF-CHECK" in prompt
        assert "assumption" in prompt.lower() or "weakest" in prompt.lower()

    def test_pack_perspective_included_in_prompt(self, staff_core):
        prompt = build_system_prompt("review", staff_core)
        # The pack's perspective should appear somewhere
        assert staff_core.perspective[:30] in prompt

    def test_pack_tone_included_in_prompt(self, staff_core):
        prompt = build_system_prompt("review", staff_core)
        assert staff_core.tone[:15] in prompt

    @pytest.mark.parametrize("mode", ["review", "mentor", "coach", "self-check"])
    def test_all_modes_produce_non_empty_prompt(self, mode, staff_core):
        prompt = build_system_prompt(mode, staff_core)  # type: ignore[arg-type]
        assert len(prompt) > 200

    @pytest.mark.parametrize("pack_name", [
        "staff-core", "oncall-future-you", "mentor-mode", "solutions-architect", "idp-readiness",
    ])
    def test_all_packs_build_valid_prompt(self, pack_name):
        pack = load_pack(pack_name)
        prompt = build_system_prompt("review", pack)
        assert "## Summary" in prompt
        assert len(prompt) > 200
