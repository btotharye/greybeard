"""Batch analysis engine for aggregating multiple reviews and synthesizing findings.

This module provides the BatchAnalyzer class which:
  - Collects multiple individual review results
  - Aggregates risk findings with deduplication
  - Synthesizes cross-review insights
  - Detects patterns and trends across reviews
  - Produces structured output for dashboard visualization
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

RiskLevel = Literal["critical", "high", "medium", "low", "info"]


@dataclass
class Finding:
    """A single finding extracted from a review."""

    title: str
    description: str
    risk_level: RiskLevel
    frequency: int = 1  # How many reviews mention this
    sources: list[str] = field(default_factory=list)  # Which review files
    tags: list[str] = field(default_factory=list)
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "risk_level": self.risk_level,
            "frequency": self.frequency,
            "sources": self.sources,
            "tags": self.tags,
            "context": self.context,
        }


@dataclass
class ReviewSummary:
    """Aggregated summary of a single review."""

    source_file: str
    review_text: str
    findings: list[Finding] = field(default_factory=list)
    total_risk_score: float = 0.0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    parsed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_file": self.source_file,
            "review_text": self.review_text,
            "findings": [f.to_dict() for f in self.findings],
            "total_risk_score": self.total_risk_score,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "parsed_at": self.parsed_at,
        }


@dataclass
class AggregatedFindings:
    """Aggregated findings across all reviews."""

    findings: list[Finding] = field(default_factory=list)
    total_reviews: int = 0
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    risk_heatmap: dict[str, int] = field(default_factory=dict)  # tag -> risk count
    recurring_findings: list[Finding] = field(default_factory=list)  # Found in 2+ reviews
    trends: list[str] = field(default_factory=list)  # Detected patterns
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "findings": [f.to_dict() for f in self.findings],
            "total_reviews": self.total_reviews,
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "risk_heatmap": self.risk_heatmap,
            "recurring_findings": [f.to_dict() for f in self.recurring_findings],
            "trends": self.trends,
            "created_at": self.created_at,
        }


class BatchAnalyzer:
    """Collects and aggregates multiple reviews with risk synthesis."""

    # Risk level scoring for aggregation
    RISK_WEIGHTS = {
        "critical": 10,
        "high": 5,
        "medium": 2,
        "low": 1,
        "info": 0,
    }

    def __init__(self) -> None:
        """Initialize the batch analyzer."""
        self.reviews: list[ReviewSummary] = []
        self.aggregated: AggregatedFindings | None = None

    def add_review(self, source_file: str, review_text: str) -> ReviewSummary:
        """Add a review text and extract findings.

        Args:
            source_file: Path or identifier of the source file being reviewed.
            review_text: Full text of the LLM review output.

        Returns:
            ReviewSummary with extracted findings.
        """
        summary = ReviewSummary(source_file=source_file, review_text=review_text)

        # Extract findings from review text
        findings = self._extract_findings(review_text, source_file)
        summary.findings = findings

        # Calculate risk metrics
        summary = self._calculate_risk_metrics(summary)

        self.reviews.append(summary)
        return summary

    def analyze(self) -> AggregatedFindings:
        """Aggregate all reviews and synthesize findings.

        Returns:
            AggregatedFindings with cross-review analysis.
        """
        aggregated = AggregatedFindings(total_reviews=len(self.reviews))

        # Collect and deduplicate findings
        all_findings = []
        for review in self.reviews:
            all_findings.extend(review.findings)

        # Deduplicate similar findings
        deduplicated = self._deduplicate_findings(all_findings)
        aggregated.findings = deduplicated

        # Calculate aggregate counts
        for finding in deduplicated:
            aggregated.total_findings += 1
            if finding.risk_level == "critical":
                aggregated.critical_count += 1
            elif finding.risk_level == "high":
                aggregated.high_count += 1
            elif finding.risk_level == "medium":
                aggregated.medium_count += 1
            elif finding.risk_level == "low":
                aggregated.low_count += 1
            else:  # info
                aggregated.info_count += 1

        # Identify recurring findings (appearing in 2+ reviews)
        aggregated.recurring_findings = [f for f in deduplicated if f.frequency >= 2]

        # Build risk heatmap by tag
        aggregated.risk_heatmap = self._build_risk_heatmap(deduplicated)

        # Detect trends
        aggregated.trends = self._detect_trends(deduplicated)

        # Sort findings by risk level and frequency
        aggregated.findings.sort(
            key=lambda f: (
                -self.RISK_WEIGHTS[f.risk_level],
                -f.frequency,
            )
        )

        self.aggregated = aggregated
        return aggregated

    def _extract_findings(self, review_text: str, source_file: str) -> list[Finding]:
        """Extract structured findings from review text.

        Uses heuristics to identify risk mentions in the text.

        Args:
            review_text: Full review text from LLM.
            source_file: Source file identifier.

        Returns:
            List of extracted findings.
        """
        findings: list[Finding] = []

        # Pattern for marked findings
        # Looks for lines with risk indicators
        patterns = {
            "critical": (r"(?:critical|severity:\s*critical|🔴.*critical|⚠️\s*critical)"),
            "high": (
                r"(?:^high[:\s]|high\s+(?:risk|concern|severity)|severity:\s*high"
                r"|🟠.*high|⚠️\s*high)"
            ),
            "medium": (
                r"(?:^medium[:\s]|medium\s+(?:risk|concern|severity)|severity:\s*"
                r"medium|🟡.*medium)"
            ),
            "low": (
                r"(?:^low[:\s]|low\s+(?:risk|concern|severity)|severity:\s*low"
                r"|🟢.*low)"
            ),
            "info": r"(?:^info[:\s]|^info$|fyi|note:\s*|note -|ℹ️)",
        }

        # Split text into potential finding blocks
        lines = review_text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # Try to match risk patterns
            risk_level: RiskLevel | None = None
            for level, pattern in patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    risk_level = level  # type: ignore[assignment]
                    break

            if risk_level:
                # Extract title (rest of line)
                title = line.strip()
                if len(title) > 200:
                    title = title[:197] + "..."
                elif not title:
                    title = f"Finding ({risk_level})"

                # Move to next line after processing the current one
                i += 1

                finding = Finding(
                    title=title,
                    description="",
                    risk_level=risk_level,
                    sources=[source_file],
                )
                findings.append(finding)
            else:
                i += 1

        return findings

    def _calculate_risk_metrics(self, summary: ReviewSummary) -> ReviewSummary:
        """Calculate risk metrics for a review summary."""
        for finding in summary.findings:
            weight = self.RISK_WEIGHTS[finding.risk_level]
            summary.total_risk_score += weight

            if finding.risk_level == "critical":
                summary.critical_count += 1
            elif finding.risk_level == "high":
                summary.high_count += 1
            elif finding.risk_level == "medium":
                summary.medium_count += 1
            elif finding.risk_level == "low":
                summary.low_count += 1

        return summary

    def _deduplicate_findings(self, all_findings: list[Finding]) -> list[Finding]:
        """Deduplicate similar findings across reviews.

        Uses fuzzy matching on finding titles to group similar findings.

        Args:
            all_findings: All findings from all reviews.

        Returns:
            Deduplicated list of findings.
        """
        if not all_findings:
            return []

        seen: dict[str, Finding] = {}

        for finding in all_findings:
            # Normalize title for comparison
            normalized = self._normalize_text(finding.title)

            # Try fuzzy match against seen findings
            matched = False
            for key, existing in seen.items():
                if self._fuzzy_match(normalized, key):
                    # Merge with existing finding
                    existing.frequency += 1
                    if finding.sources and finding.sources[0] not in existing.sources:
                        existing.sources.extend(finding.sources)
                    if finding.description and not existing.description:
                        existing.description = finding.description
                    matched = True
                    break

            if not matched:
                # New finding
                seen[normalized] = finding

        return list(seen.values())

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        return re.sub(r"\s+", " ", text.lower().strip())[:100]

    def _fuzzy_match(self, text1: str, text2: str, threshold: float = 0.5) -> bool:
        """Simple fuzzy match using word overlap.

        Args:
            text1: First text to compare.
            text2: Second text to compare.
            threshold: Similarity threshold (0-1), default 0.5.

        Returns:
            True if texts are similar enough.
        """
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return text1 == text2

        # Common words matching (Jaccard similarity)
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold

    def _build_risk_heatmap(self, findings: list[Finding]) -> dict[str, int]:
        """Build a heatmap of risk counts by tag.

        Args:
            findings: Deduplicated findings.

        Returns:
            Dictionary mapping tag to risk count.
        """
        heatmap: dict[str, int] = {}

        for finding in findings:
            weight = self.RISK_WEIGHTS[finding.risk_level]
            for tag in finding.tags:
                heatmap[tag] = heatmap.get(tag, 0) + weight

        return dict(sorted(heatmap.items(), key=lambda x: -x[1])[:20])

    def _detect_trends(self, findings: list[Finding]) -> list[str]:
        """Detect patterns and trends across findings.

        Args:
            findings: Deduplicated findings.

        Returns:
            List of detected trends.
        """
        trends: list[str] = []

        # Trend 1: High frequency findings
        high_freq = [f for f in findings if f.frequency >= len(self.reviews) * 0.5]
        if high_freq:
            trends.append(f"High consensus: {len(high_freq)} finding(s) appear in 50%+ of reviews")

        # Trend 2: Risk concentration
        critical_findings = [f for f in findings if f.risk_level == "critical"]
        if critical_findings:
            trends.append(
                f"Critical risk concentration: {len(critical_findings)} critical "
                f"finding(s) identified"
            )

        # Trend 3: Specific categories
        all_tags = set()
        for f in findings:
            all_tags.update(f.tags)
        if all_tags:
            top_tags = sorted(
                [(tag, sum(1 for f in findings if tag in f.tags)) for tag in all_tags],
                key=lambda x: -x[1],
            )[:5]
            if top_tags:
                trend_str = ", ".join(f"{tag}({count})" for tag, count in top_tags)
                trends.append(f"Top risk categories: {trend_str}")

        return trends

    def export_json(self, path: str | Path) -> None:
        """Export aggregated findings to JSON.

        Args:
            path: Output file path.
        """
        if not self.aggregated:
            self.analyze()

        assert self.aggregated is not None, "aggregated should be set after analyze()"

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": {
                "total_reviews": self.aggregated.total_reviews,
                "total_findings": self.aggregated.total_findings,
                "created_at": self.aggregated.created_at,
            },
            "summary": {
                "critical": self.aggregated.critical_count,
                "high": self.aggregated.high_count,
                "medium": self.aggregated.medium_count,
                "low": self.aggregated.low_count,
                "info": self.aggregated.info_count,
            },
            "findings": [f.to_dict() for f in self.aggregated.findings],
            "recurring": [f.to_dict() for f in self.aggregated.recurring_findings],
            "trends": self.aggregated.trends,
            "reviews": [r.to_dict() for r in self.reviews],
        }

        path.write_text(json.dumps(data, indent=2))

    def export_markdown(self, path: str | Path) -> None:
        """Export aggregated findings to Markdown.

        Args:
            path: Output file path.
        """
        if not self.aggregated:
            self.analyze()

        assert self.aggregated is not None, "aggregated should be set after analyze()"

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = [
            "# Batch Review Analysis Report",
            "",
            f"**Generated:** {self.aggregated.created_at}",
            "",
            "## Executive Summary",
            "",
            f"- **Total Reviews:** {self.aggregated.total_reviews}",
            f"- **Total Findings:** {self.aggregated.total_findings}",
            f"- **Critical Issues:** {self.aggregated.critical_count}",
            f"- **High Risk:** {self.aggregated.high_count}",
            f"- **Medium Risk:** {self.aggregated.medium_count}",
            f"- **Low Risk:** {self.aggregated.low_count}",
            f"- **Info/Notes:** {self.aggregated.info_count}",
            "",
        ]

        if self.aggregated.trends:
            lines.extend(
                [
                    "## Detected Trends",
                    "",
                ]
            )
            for trend in self.aggregated.trends:
                lines.append(f"- {trend}")
            lines.append("")

        if self.aggregated.recurring_findings:
            lines.extend(
                [
                    "## Recurring Findings (Consensus Issues)",
                    "",
                ]
            )
            for finding in self.aggregated.recurring_findings:
                lines.append(
                    f"### {finding.title} ({finding.risk_level.upper()}, "
                    f"found in {finding.frequency} reviews)"
                )
                lines.append("")
                if finding.description:
                    lines.append(finding.description)
                    lines.append("")
                lines.append(f"**Affected sources:** {', '.join(finding.sources)}")
                lines.append("")

        lines.extend(
            [
                "## All Findings",
                "",
            ]
        )
        for i, finding in enumerate(self.aggregated.findings, 1):
            lines.append(f"{i}. {finding.title} ({finding.risk_level.upper()})")
            if finding.description:
                lines.append(f"   {finding.description}")

        path.write_text("\n".join(lines))
