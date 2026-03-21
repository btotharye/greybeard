"""ADR (Architecture Decision Record) reporter for greybeard review results.

Converts review findings into structured ADRs following a standardized format.
Integrates with git for decision logging and version control.

ADR Template:
  - Title: Brief decision name
  - Status: Proposed | Accepted | Deprecated | Superseded
  - Context: Problem/constraints/background
  - Decision: The actual decision made
  - Consequences: Impact on the system (positive and negative)
  - Alternatives Considered: What else was evaluated
  - Related Decisions: Links to related ADRs
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

ADRStatus = Literal["Proposed", "Accepted", "Deprecated", "Superseded"]


@dataclass
class ADREntry:
    """Structured representation of an Architecture Decision Record."""

    title: str
    status: ADRStatus
    context: str
    decision: str
    consequences: str
    alternatives: str
    date: str | None = None
    authors: list[str] | None = None
    related_decisions: list[str] | None = None

    def to_markdown(self) -> str:
        """Render the ADR as markdown."""
        lines = [f"# ADR: {self.title}\n"]
        lines.append(f"**Status:** {self.status}\n")
        if self.date:
            lines.append(f"**Date:** {self.date}\n")
        if self.authors:
            lines.append(f"**Authors:** {', '.join(self.authors)}\n")

        lines.append("\n## Context\n")
        lines.append(self.context)

        lines.append("\n## Decision\n")
        lines.append(self.decision)

        lines.append("\n## Consequences\n")
        lines.append(self.consequences)

        lines.append("\n## Alternatives Considered\n")
        lines.append(self.alternatives)

        if self.related_decisions:
            lines.append("\n## Related Decisions\n")
            for ref in self.related_decisions:
                lines.append(f"- {ref}\n")

        return "".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON/YAML export."""
        data: dict[str, Any] = {
            "title": self.title,
            "status": self.status,
            "context": self.context,
            "decision": self.decision,
            "consequences": self.consequences,
            "alternatives": self.alternatives,
        }
        if self.date:
            data["date"] = self.date
        if self.authors:
            data["authors"] = self.authors
        if self.related_decisions:
            data["related_decisions"] = self.related_decisions
        return data


class ADRReporter:
    """Convert review findings into structured Architecture Decision Records."""

    def __init__(self, review_text: str, title: str | None = None):
        """Initialize the ADR reporter.

        Args:
            review_text: Full LLM review output.
            title: Optional override for ADR title. If not provided,
                   will be extracted or generated from review content.
        """
        self.review_text = review_text
        self.title = title or self._extract_title()
        self.now_utc = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    def _extract_title(self) -> str:
        """Extract or infer a title from the review text."""
        # Look for a first-line heading or title pattern
        for line in self.review_text.split("\n")[:10]:
            line = line.strip()
            # Check for markdown heading
            if line.startswith("# "):
                return line[2:].strip()
        # Fallback: use first 60 chars of review as title
        first_sentence = self.review_text.split("\n")[0].strip()
        if len(first_sentence) > 60:
            first_sentence = first_sentence[:60].rsplit(" ", 1)[0] + "..."
        return first_sentence or "Architecture Decision"

    def extract_sections(self) -> dict[str, str]:
        """Extract structured sections from review text.

        Attempts to identify:
          - Context/Background (problem, constraints, current state)
          - Decision/Recommendation (what to do)
          - Consequences (impacts, trade-offs)
          - Alternatives (other options considered)

        Uses heuristics based on markdown headers and content patterns.
        """
        sections: dict[str, str] = {
            "context": "",
            "decision": "",
            "consequences": "",
            "alternatives": "",
        }

        # Split on markdown headers
        current_section = "context"
        current_lines: list[str] = []

        for line in self.review_text.split("\n"):
            stripped = line.strip()

            # Detect section headers (h2-h4)
            if stripped.startswith("##"):
                # Save previous section
                if current_lines:
                    sections[current_section] = "\n".join(current_lines).strip()
                    current_lines = []

                # Determine new section
                header_text = stripped.lstrip("#").strip().lower()
                if any(
                    kw in header_text
                    for kw in [
                        "context",
                        "background",
                        "problem",
                        "constraint",
                        "current state",
                    ]
                ):
                    current_section = "context"
                elif any(
                    kw in header_text
                    for kw in [
                        "decision",
                        "recommendation",
                        "solution",
                        "proposed",
                    ]
                ):
                    current_section = "decision"
                elif any(
                    kw in header_text
                    for kw in ["consequence", "impact", "trade-off", "result"]
                ):
                    current_section = "consequences"
                elif any(
                    kw in header_text
                    for kw in ["alternative", "option", "considered", "rejected"]
                ):
                    current_section = "alternatives"
            else:
                # Accumulate all lines (including empty ones for formatting)
                current_lines.append(line)

        # Save final section
        if current_lines:
            sections[current_section] = "\n".join(current_lines).strip()

        # Fallback: if minimal sections found, ensure decision is populated
        # (count non-empty sections)
        non_empty_sections = sum(1 for s in sections.values() if s)
        if non_empty_sections == 0:
            sections["context"] = self.review_text.strip()
            sections["decision"] = "See context above for recommended approach."
        elif non_empty_sections == 1 and not sections["decision"]:
            # Only one section and no decision: add a fallback decision
            sections["decision"] = "See context above for recommended approach."

        return sections

    def generate_adr(
        self,
        status: ADRStatus = "Proposed",
        authors: list[str] | None = None,
        related_decisions: list[str] | None = None,
    ) -> ADREntry:
        """Generate a structured ADR from the review.

        Args:
            status: ADR status (Proposed | Accepted | Deprecated | Superseded).
            authors: List of author names.
            related_decisions: List of related ADR references.

        Returns:
            ADREntry object with structured fields.
        """
        sections = self.extract_sections()

        return ADREntry(
            title=self.title,
            status=status,
            context=sections["context"] or _generate_fallback_context(self.review_text),
            decision=sections["decision"] or _generate_fallback_decision(self.review_text),
            consequences=sections["consequences"]
            or _generate_fallback_consequences(self.review_text),
            alternatives=sections["alternatives"]
            or _generate_fallback_alternatives(self.review_text),
            date=self.now_utc,
            authors=authors or ["greybeard"],
            related_decisions=related_decisions,
        )


def _generate_fallback_context(text: str) -> str:
    """Generate context section if not explicitly found."""
    lines = []
    for line in text.split("\n")[:15]:
        if line.strip() and not line.startswith("#"):
            lines.append(line)
        if len(lines) >= 5:
            break
    return "\n".join(lines).strip() or "See full review for context."


def _generate_fallback_decision(text: str) -> str:
    """Generate decision section if not explicitly found."""
    # Look for imperative sentences or recommendations
    for line in text.split("\n"):
        stripped = line.strip()
        if any(
            stripped.startswith(verb)
            for verb in ["Use", "Build", "Adopt", "Implement", "Choose", "Recommend"]
        ):
            return stripped
    # Fallback: extract first sentence with action verb
    for sentence in text.split("."):
        if any(
            verb in sentence
            for verb in [
                "should",
                "recommend",
                "use",
                "adopt",
                "implement",
                "choose",
            ]
        ):
            return sentence.strip() + "."
    return "See alternatives and consequences above for recommended approach."


def _generate_fallback_consequences(text: str) -> str:
    """Generate consequences section if not explicitly found."""
    # Look for impact-related language
    lines = []
    for line in text.split("\n"):
        if any(
            kw in line.lower()
            for kw in ["impact", "affect", "require", "risk", "trade-off", "pro", "con"]
        ):
            lines.append(line)
    fallback = (
        "Positive: Improves decision quality. "
        "Negative: Requires documentation."
    )
    return "\n".join(lines).strip() or fallback


def _generate_fallback_alternatives(text: str) -> str:
    """Generate alternatives section if not explicitly found."""
    # Look for option/alternative language
    lines = []
    for line in text.split("\n"):
        if any(
            kw in line.lower()
            for kw in [
                "alternative",
                "option",
                "instead",
                "could",
                "might",
                "another approach",
            ]
        ):
            lines.append(line)
    return (
        "\n".join(lines).strip()
        or "See context and decision sections for full analysis."
    )


class ADRRepository:
    """Manage ADR storage and git integration."""

    def __init__(self, repo_path: Path | str | None = None):
        """Initialize the ADR repository.

        Args:
            repo_path: Path to git repository. If None, uses current working directory.
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.adr_dir = self.repo_path / "docs" / "adr"

    def save_adr(
        self,
        adr: ADREntry,
        filename: str | None = None,
        auto_commit: bool = False,
        commit_message: str | None = None,
    ) -> Path:
        """Save an ADR to the repository.

        Args:
            adr: ADREntry to save.
            filename: Output filename (without extension).
                      If None, auto-generates from title.
            auto_commit: If True, stage and commit the ADR file to git.
            commit_message: Custom commit message. If None, auto-generates one.

        Returns:
            Path to the saved ADR file.
        """
        self.adr_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        if not filename:
            filename = self._generate_filename(adr.title)

        filepath = self.adr_dir / f"{filename}.md"

        # Write markdown
        filepath.write_text(adr.to_markdown(), encoding="utf-8")

        # Auto-commit if requested
        if auto_commit:
            self._commit_adr(filepath, adr, commit_message)

        return filepath

    def _generate_filename(self, title: str) -> str:
        """Generate a filename from ADR title.

        Converts to kebab-case and prefixes with next sequence number.
        E.g., "Use PostgreSQL for persistence" → "0003-use-postgresql-for-persistence"
        """
        # Get the next number
        next_num = self._get_next_adr_number()

        # Convert title to kebab-case
        slug = (
            re.sub(r"[^\w\s-]", "", title.lower())  # Remove non-word chars
            .strip()  # Strip whitespace
            .replace(" ", "-")  # Replace spaces with hyphens
            .replace("--", "-")  # Collapse multiple hyphens
        )

        return f"{next_num:04d}-{slug}"

    def _get_next_adr_number(self) -> int:
        """Get the next ADR sequence number based on existing files."""
        if not self.adr_dir.exists():
            return 1

        max_num = 0
        for filepath in self.adr_dir.glob("*.md"):
            match = re.match(r"(\d+)-", filepath.name)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)
        return max_num + 1

    def _commit_adr(
        self,
        filepath: Path,
        adr: ADREntry,
        commit_message: str | None = None,
    ) -> None:
        """Commit the ADR file to git.

        Args:
            filepath: Path to the ADR file.
            adr: ADREntry for context.
            commit_message: Custom message; if None, auto-generates.
        """
        try:
            # Stage the file
            subprocess.run(
                ["git", "add", str(filepath)],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )

            # Create commit message
            if not commit_message:
                commit_message = f"docs(adr): {adr.title} [{adr.status}]"

            # Commit
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to commit ADR file: {e.stderr.decode('utf-8')}"
            ) from e

    def list_adrs(self) -> list[tuple[Path, ADREntry]]:
        """List all ADRs in the repository.

        Returns:
            List of (filepath, parsed_adr_metadata) tuples.
        """
        adrs: list[tuple[Path, ADREntry]] = []

        if not self.adr_dir.exists():
            return adrs

        for filepath in sorted(self.adr_dir.glob("*.md")):
            try:
                # Parse just the metadata from the file
                content = filepath.read_text(encoding="utf-8")
                adr_meta = _parse_adr_metadata(content, filepath)
                if adr_meta:
                    adrs.append((filepath, adr_meta))
            except Exception:
                # Skip unparseable files
                continue

        return adrs

    def get_adr_by_title(self, title: str) -> Path | None:
        """Find an ADR file by title.

        Args:
            title: ADR title to search for.

        Returns:
            Path to the ADR file, or None if not found.
        """
        for filepath, adr in self.list_adrs():
            if adr.title == title:
                return filepath
        return None


def _parse_adr_metadata(content: str, filepath: Path) -> ADREntry | None:
    """Parse ADR metadata from a markdown file.

    Only extracts headers, status, and title—not full content.
    """
    lines = content.split("\n")
    title = ""
    status: ADRStatus = "Proposed"
    date = None

    for line in lines:
        stripped = line.strip()

        # Extract title from first H1
        if stripped.startswith("# ADR:"):
            title = stripped[6:].strip()
        # Extract status
        elif stripped.startswith("**Status:**"):
            status_text = stripped[11:].strip()
            if status_text in ("Proposed", "Accepted", "Deprecated", "Superseded"):
                status = status_text  # type: ignore[assignment]
        # Extract date
        elif stripped.startswith("**Date:**"):
            date = stripped[9:].strip()

    if not title:
        title = filepath.stem

    return ADREntry(
        title=title,
        status=status,
        context="",
        decision="",
        consequences="",
        alternatives="",
        date=date,
    )
