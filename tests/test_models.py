"""Tests for the ReviewRequest model."""

from __future__ import annotations

from staff_review.models import ContentPack, ReviewRequest


class TestContentPack:
    def test_to_system_prompt_fragment_minimal(self):
        pack = ContentPack(
            name="test",
            perspective="A test perspective",
            tone="calm",
        )
        fragment = pack.to_system_prompt_fragment()
        assert "A test perspective" in fragment
        assert "calm" in fragment

    def test_to_system_prompt_fragment_with_heuristics(self):
        pack = ContentPack(
            name="test",
            perspective="Tester",
            tone="direct",
            heuristics=["Check X before Y", "Always ask why"],
        )
        fragment = pack.to_system_prompt_fragment()
        assert "Check X before Y" in fragment
        assert "Always ask why" in fragment

    def test_to_system_prompt_fragment_with_questions(self):
        pack = ContentPack(
            name="test",
            perspective="Tester",
            tone="direct",
            example_questions=["Who owns the runbook?", "What breaks at 3am?"],
        )
        fragment = pack.to_system_prompt_fragment()
        assert "Who owns the runbook?" in fragment
        assert "What breaks at 3am?" in fragment

    def test_to_system_prompt_fragment_with_communication_style(self):
        pack = ContentPack(
            name="test",
            perspective="Tester",
            tone="direct",
            communication_style="Be concise and specific.",
        )
        fragment = pack.to_system_prompt_fragment()
        assert "Be concise and specific." in fragment

    def test_empty_lists_not_in_fragment(self):
        pack = ContentPack(
            name="test",
            perspective="Tester",
            tone="direct",
        )
        fragment = pack.to_system_prompt_fragment()
        assert "heuristics" not in fragment.lower()
        assert "example" not in fragment.lower()


class TestReviewRequest:
    def _make_pack(self) -> ContentPack:
        return ContentPack(name="test", perspective="Tester", tone="calm")

    def test_default_values(self):
        pack = self._make_pack()
        req = ReviewRequest(mode="review", pack=pack)
        assert req.input_text == ""
        assert req.context_notes == ""
        assert req.audience is None
        assert req.repo_path is None

    def test_with_all_fields(self):
        pack = self._make_pack()
        req = ReviewRequest(
            mode="mentor",
            pack=pack,
            input_text="diff content",
            context_notes="context here",
            audience="team",
            repo_path="/some/path",
        )
        assert req.mode == "mentor"
        assert req.input_text == "diff content"
        assert req.context_notes == "context here"
        assert req.audience == "team"
        assert req.repo_path == "/some/path"
