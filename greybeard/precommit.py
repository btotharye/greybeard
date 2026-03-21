"""Pre-commit hook integration for Greybeard.

This module provides utilities for integrating Greybeard reviews as a pre-commit hook,
including:
- Risk gate configuration and matching
- File pattern matching and filtering
- Git diff extraction and context management
- Review output analysis and formatting
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

import yaml


@dataclass
class RiskGate:
    """Risk gate configuration for file patterns."""

    name: str
    patterns: list[str] = field(default_factory=list)
    fail_on_concerns: str = "critical"
    required_packs: list[str] = field(default_factory=list)
    skip_if_branch: list[str] = field(default_factory=list)

    def matches(self, filepath: str) -> bool:
        """Check if this gate matches a filepath."""
        if not self.patterns:
            return False
        return any(fnmatch(filepath, pattern) for pattern in self.patterns)


@dataclass
class PreCommitConfig:
    """Configuration for pre-commit integration."""

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
        """Save configuration to YAML file."""
        config_dict = {
            "enabled": self.enabled,
            "default_pack": self.default_pack,
            "additional_packs": self.additional_packs,
            "fail_on_concerns": self.fail_on_concerns,
            "skip_unstaged": self.skip_unstaged,
            "max_context_lines": self.max_context_lines,
            "verbose": self.verbose,
            "excluded_paths": self.excluded_paths,
            "risk_gates": [
                {
                    "name": gate.name,
                    "patterns": gate.patterns,
                    "fail_on_concerns": gate.fail_on_concerns,
                    "required_packs": gate.required_packs,
                    "skip_if_branch": gate.skip_if_branch,
                }
                for gate in self.risk_gates
            ],
        }

        Path(path).write_text(yaml.dump(config_dict, default_flow_style=False))

    @classmethod
    def load(cls, path: str) -> PreCommitConfig:
        """Load configuration from YAML file."""
        if not Path(path).exists():
            return cls()

        data = yaml.safe_load(Path(path).read_text())
        if not data:
            return cls()

        gates = []
        for gate_data in data.get("risk_gates", []):
            gates.append(
                RiskGate(
                    name=gate_data.get("name", ""),
                    patterns=gate_data.get("patterns", []),
                    fail_on_concerns=gate_data.get("fail_on_concerns", "critical"),
                    required_packs=gate_data.get("required_packs", []),
                    skip_if_branch=gate_data.get("skip_if_branch", []),
                )
            )

        return cls(
            enabled=data.get("enabled", True),
            default_pack=data.get("default_pack", "staff-core"),
            additional_packs=data.get("additional_packs", []),
            fail_on_concerns=data.get("fail_on_concerns", "critical"),
            skip_unstaged=data.get("skip_unstaged", True),
            max_context_lines=data.get("max_context_lines", 500),
            verbose=data.get("verbose", False),
            excluded_paths=data.get("excluded_paths", []),
            risk_gates=gates,
        )


@dataclass
class PreCommitReview:
    """Result of a pre-commit review."""

    passed: bool
    message: str
    concerns: list[str] = field(default_factory=list)
    failed_gates: list[str] = field(default_factory=list)
    pack_used: str = "staff-core"

    def to_json(self) -> str:
        """Serialize review to JSON."""
        return json.dumps(
            {
                "passed": self.passed,
                "message": self.message,
                "concerns": self.concerns,
                "failed_gates": self.failed_gates,
                "pack_used": self.pack_used,
            }
        )


def should_skip_file(filepath: str, skip_patterns: list[str]) -> bool:
    """Check if a file should be skipped based on patterns."""
    for pattern in skip_patterns:
        if fnmatch(filepath, pattern):
            return True
    return False


def should_skip_gate(gate: RiskGate, branch: str) -> bool:
    """Check if a gate should be skipped for a branch."""
    for branch_pattern in gate.skip_if_branch:
        if fnmatch(branch, branch_pattern):
            return True
    return False


def get_applicable_gate(
    filepath: str, gates: list[RiskGate], branch: str
) -> RiskGate | None:
    """Find the applicable risk gate for a file."""
    for gate in gates:
        if should_skip_gate(gate, branch):
            continue
        if gate.matches(filepath):
            return gate
    return None


def extract_diff_context(
    diff_content: str, max_lines: int = 500
) -> str:
    """Extract diff context with optional truncation."""
    lines = diff_content.split("\n")

    if len(lines) <= max_lines:
        return diff_content

    # Keep first and last portions, truncate middle
    # Account for truncation message (3 lines)
    keep_per_side = (max_lines - 3) // 2
    first_lines = lines[:keep_per_side]
    last_lines = lines[-keep_per_side:]

    result = "\n".join(first_lines)
    result += "\n\n[... truncated ...]\n\n"
    result += "\n".join(last_lines)

    return result


def analyze_review_output(review_content: str, threshold: str) -> tuple[bool, list[str]]:
    """Analyze review output and extract concerns."""
    if threshold == "none":
        return True, []

    # Pattern definitions for different concern levels
    patterns = {
        "critical": r"\[CRITICAL\]",
        "high": r"\[(CRITICAL|HIGH)\]",
        "medium": r"\[(CRITICAL|HIGH|MEDIUM)\]",
        "low": r"\[(CRITICAL|HIGH|MEDIUM|LOW)\]",
    }

    pattern = patterns.get(threshold, patterns["critical"])

    concerns = []
    lines = review_content.split("\n")
    for line in lines:
        if re.search(pattern, line):
            concerns.append(line.strip())

    passed = len(concerns) == 0
    return passed, concerns


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

    return output


def get_staged_files() -> list[str]:
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Handle both returncode attribute and mock object with default returncode
        returncode = getattr(result, 'returncode', 0)
        if returncode != 0:
            return []
        stdout = result.stdout
        return [f.strip() for f in stdout.strip().split("\n") if f.strip()]
    except Exception:
        return []


def get_staged_diff() -> str:
    """Get staged diff from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Handle both returncode attribute and mock object with default returncode
        returncode = getattr(result, 'returncode', 0)
        if returncode != 0:
            return ""
        return result.stdout
    except Exception:
        return ""


def get_current_branch() -> str:
    """Get current branch name from git."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Handle both returncode attribute and mock object with default returncode
        returncode = getattr(result, 'returncode', 0)
        if returncode != 0:
            return "main"
        return result.stdout.strip()
    except Exception:
        return "main"
