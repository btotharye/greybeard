"""Pre-commit hook integration for greybeard."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field

import yaml  # type: ignore[import-untyped]


@dataclass
class RiskGate:
    """Configuration for a risk gate."""

    name: str
    patterns: list[str] = field(default_factory=list)
    fail_on_concerns: str = "critical"
    required_packs: list[str] = field(default_factory=list)
    skip_if_branch: list[str] = field(default_factory=list)


@dataclass
class PreCommitConfig:
    """Configuration for pre-commit hook."""

    enabled: bool = True
    default_pack: str = "staff-core"
    additional_packs: list[str] = field(default_factory=list)
    fail_on_concerns: str = "critical"
    skip_unstaged: bool = True
    max_context_lines: int = 500
    verbose: bool = False
    risk_gates: list[RiskGate] = field(default_factory=list)
    excluded_paths: list[str] = field(default_factory=list)

    def save(self, path: str) -> None:
        """Save configuration to file."""
        config_dict = {
            "enabled": self.enabled,
            "default_pack": self.default_pack,
            "additional_packs": self.additional_packs,
            "fail_on_concerns": self.fail_on_concerns,
            "skip_unstaged": self.skip_unstaged,
            "max_context_lines": self.max_context_lines,
            "verbose": self.verbose,
            "excluded_paths": self.excluded_paths,
        }

        if self.risk_gates:
            config_dict["risk_gates"] = [
                {
                    "name": gate.name,
                    "patterns": gate.patterns,
                    "fail_on_concerns": gate.fail_on_concerns,
                    "required_packs": gate.required_packs,
                    "skip_if_branch": gate.skip_if_branch,
                }
                for gate in self.risk_gates
            ]

        with open(path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False)

    @classmethod
    def load(cls, path: str) -> PreCommitConfig:
        """Load configuration from file."""
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        risk_gates = []
        if "risk_gates" in data:
            risk_gates = [
                RiskGate(
                    name=gate["name"],
                    patterns=gate.get("patterns", []),
                    fail_on_concerns=gate.get("fail_on_concerns", "critical"),
                    required_packs=gate.get("required_packs", []),
                    skip_if_branch=gate.get("skip_if_branch", []),
                )
                for gate in data.get("risk_gates", [])
            ]

        return cls(
            enabled=data.get("enabled", True),
            default_pack=data.get("default_pack", "staff-core"),
            additional_packs=data.get("additional_packs", []),
            fail_on_concerns=data.get("fail_on_concerns", "critical"),
            skip_unstaged=data.get("skip_unstaged", True),
            max_context_lines=data.get("max_context_lines", 500),
            verbose=data.get("verbose", False),
            risk_gates=risk_gates,
            excluded_paths=data.get("excluded_paths", []),
        )


@dataclass
class PreCommitReview:
    """Result of a pre-commit review."""

    passed: bool
    message: str
    concerns: list[str] = field(default_factory=list)
    failed_gates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self))


def should_skip_file(filepath: str, patterns: list[str]) -> bool:
    """Check if a file should be skipped based on patterns."""
    for pattern in patterns:
        # Convert glob pattern to regex
        regex_pattern = pattern.replace(".", r"\.").replace("*", ".*")
        if re.match(f"^{regex_pattern}$", filepath):
            return True
        # Also check path components for patterns like ".venv/*"
        if "*" in pattern:
            parts = pattern.split("/")
            file_parts = filepath.split("/")
            if len(file_parts) >= len(parts):
                match = True
                for i, part in enumerate(parts):
                    part_regex = part.replace(".", r"\.").replace("*", ".*")
                    if not re.match(f"^{part_regex}$", file_parts[i]):
                        match = False
                        break
                if match:
                    return True
    return False


def should_skip_gate(gate: RiskGate, branch: str) -> bool:
    """Check if a gate should be skipped for the current branch."""
    for skip_pattern in gate.skip_if_branch:
        pattern_regex = skip_pattern.replace(".", r"\.").replace("*", ".*")
        if re.match(f"^{pattern_regex}$", branch):
            return True
    return False


def get_applicable_gate(filepath: str, gates: list[RiskGate], branch: str) -> RiskGate | None:
    """Find the applicable risk gate for a file."""
    for gate in gates:
        if should_skip_gate(gate, branch):
            continue

        for pattern in gate.patterns:
            pattern_regex = pattern.replace(".", r"\.").replace("*", ".*")
            if re.match(f"^{pattern_regex}$", filepath):
                return gate

    return None


def extract_diff_context(diff: str, max_lines: int = 500) -> str:
    """Extract diff context with optional truncation."""
    lines = diff.split("\n")

    if len(lines) <= max_lines:
        return diff

    # Truncate and add indicator
    truncated_lines = lines[:max_lines]
    truncated_lines.append("[... truncated ...]")
    return "\n".join(truncated_lines)


def analyze_review_output(review_text: str, threshold: str) -> tuple[bool, list[str]]:
    """Analyze review output and determine if it passes based on threshold."""
    if threshold == "none":
        return True, []

    # Extract concerns from review text
    concerns = []
    concern_pattern = r"\[([A-Z]+)\]\s+(.+)"
    for match in re.finditer(concern_pattern, review_text):
        level = match.group(1)
        message = match.group(2)
        concerns.append(message)

        # Check threshold
        if threshold == "critical" and level == "CRITICAL":
            return False, concerns
        elif threshold == "high" and level in ("CRITICAL", "HIGH"):
            return False, concerns
        elif threshold == "medium" and level in ("CRITICAL", "HIGH", "MEDIUM"):
            return False, concerns

    return True, concerns


def get_staged_files() -> list[str]:
    """Get list of staged files in git."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return []

    return [f for f in result.stdout.strip().split("\n") if f]


def get_staged_diff() -> str:
    """Get staged diff from git."""
    result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.stdout if result.returncode == 0 else ""


def get_current_branch() -> str:
    """Get current git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.stdout.strip() if result.returncode == 0 else "HEAD"


def format_review_output(review: PreCommitReview) -> str:
    """Format review output for display."""
    symbol = "✓" if review.passed else "✗"
    output = f"{symbol} {review.message}\n"

    if review.concerns:
        output += "\nConcerns:\n"
        for concern in review.concerns:
            output += f"  - {concern}\n"

    if review.failed_gates:
        output += "\nFailed Gates:\n"
        for gate in review.failed_gates:
            output += f"  - {gate}\n"

    if review.warnings:
        output += "\nWarnings:\n"
        for warning in review.warnings:
            output += f"  - {warning}\n"

    return output
