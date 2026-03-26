"""Data models for staff-review using Pydantic."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["review", "mentor", "coach", "self-check"]
Audience = Literal["team", "peers", "leadership", "customer"]
OutputFormat = Literal["markdown", "json", "html", "jira", "pdf"]


class ContentPack(BaseModel):
    """A loaded content pack defining perspective, tone, and heuristics."""

    model_config = {"str_strip_whitespace": True}

    name: str
    perspective: str
    tone: str
    focus_areas: list[str] = Field(default_factory=list)
    heuristics: list[str] = Field(default_factory=list)
    example_questions: list[str] = Field(default_factory=list)
    communication_style: str = ""
    description: str = ""

    def to_system_prompt_fragment(self) -> str:
        """Render the pack as a system prompt fragment."""
        lines = [
            f"You are reviewing from the perspective of: {self.perspective}.",
            f"Tone: {self.tone}.",
        ]
        if self.focus_areas:
            lines.append(f"Focus areas: {', '.join(self.focus_areas)}.")
        if self.heuristics:
            lines.append("\nKey heuristics to apply:")
            for h in self.heuristics:
                lines.append(f"  - {h}")
        if self.example_questions:
            lines.append("\nExamples of the kinds of questions to surface:")
            for q in self.example_questions:
                lines.append(f"  - {q}")
        if self.communication_style:
            lines.append(f"\nCommunication style: {self.communication_style}")
        return "\n".join(lines)


class ReviewRequest(BaseModel):
    """A review request with all context assembled."""

    model_config = {"str_strip_whitespace": True}

    mode: Mode
    pack: ContentPack
    input_text: str = ""  # diff, design doc, or other input
    context_notes: str = ""  # user-provided context
    audience: Audience | None = None
    repo_path: str | None = None
