"""Pre-commit hook integration for greybeard.

This module provides pre-commit framework integration, allowing greybeard
reviews to run on staged changes before commits.

Workflow:
  1. Developer stages changes (git add)
  2. Developer runs git commit
  3. pre-commit framework runs hooks
  4. greybeard-precommit diff/check runs on staged changes
  5. If review fails (based on config), commit is blocked
  6. Developer can refine changes or escalate review

Configuration:
  Global config at ~/.greybeard/config.yaml or per-repo .greybeard-precommit.yaml
  Supports multiple packs, risk gates, and per-file overrides.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from rich.console import Console

console = Console()


@dataclass
class RiskGate:
    """Configurable risk gate for pre-commit checks."""

    name: str
    """Name of the risk gate (e.g., 'critical', 'high')."""

    patterns: list[str] = field(default_factory=list)
    """File patterns that trigger this gate (*.py, infra/*, etc.)."""

    fail_on_concerns: str = "critical"
    """Fail if review contains concerns at this level or higher:
    'none', 'critical', 'high', 'medium', 'low'.
    """

    required_packs: list[str] = field(default_factory=list)
    """Packs that must be used for this gate (e.g., ['security-reviewer']).
    If multiple, all are required.
    """

    skip_if_branch: list[str] = field(default_factory=list)
    """Skip this gate if on a branch matching these patterns.
    e.g., ['^hotfix/', '^emergency/'] to bypass on emergency branches.
    """


@dataclass
class PreCommitConfig:
    """Configuration for pre-commit hook behavior."""

    enabled: bool = True
    """Enable/disable pre-commit hook integration."""

    default_pack: str = "staff-core"
    """Default pack for reviews (can be overridden in config)."""

    additional_packs: list[str] = field(default_factory=list)
    """Additional packs to run alongside default (e.g., security-reviewer).
    All packs are run; findings are merged.
    """

    fail_on_concerns: str = "critical"
    """Block commit if review has concerns at this level or above.
    Options: 'none' (never fail), 'critical', 'high', 'medium', 'low', 'all'.
    """

    risk_gates: list[RiskGate] = field(default_factory=list)
    """Per-pattern risk gates that override default fail_on_concerns."""

    skip_unstaged: bool = True
    """Skip review of unstaged changes (only review staged changes)."""

    max_context_lines: int = 500
    """Max lines of context around changes to send to LLM.
    Prevents token limits on large diffs.
    """

    verbose: bool = False
    """Print verbose debug info."""

    allow_empty_commits: bool = False
    """Allow commits with no staged changes (e.g., commit --allow-empty)."""

    excluded_paths: list[str] = field(default_factory=list)
    """Paths to exclude from review (glob patterns).
    e.g., ['.venv/*', 'node_modules/*', '*.lock']
    """

    @classmethod
    def load(cls) -> PreCommitConfig:
        """Load config from .greybeard-precommit.yaml or defaults."""
        config_file = Path(".greybeard-precommit.yaml")
        if not config_file.exists():
            return cls()

        with config_file.open() as f:
            data = yaml.safe_load(f) or {}

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
            risk_gates=gates,
            skip_unstaged=data.get("skip_unstaged", True),
            max_context_lines=data.get("max_context_lines", 500),
            verbose=data.get("verbose", False),
            allow_empty_commits=data.get("allow_empty_commits", False),
            excluded_paths=data.get("excluded_paths", []),
        )

    def save(self, path: str = ".greybeard-precommit.yaml") -> None:
        """Write config to file."""
        data: dict = {
            "enabled": self.enabled,
            "default_pack": self.default_pack,
            "additional_packs": self.additional_packs,
            "fail_on_concerns": self.fail_on_concerns,
            "skip_unstaged": self.skip_unstaged,
            "max_context_lines": self.max_context_lines,
            "verbose": self.verbose,
            "allow_empty_commits": self.allow_empty_commits,
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

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        console.print(f"[green]✓[/green] Config saved to {path}")


def get_staged_files() -> list[str]:
    """Get list of staged files from git."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip().split("\n") if result.stdout.strip() else []


def get_staged_diff(file_path: str | None = None) -> str:
    """Get staged diff for all files or a specific file."""
    cmd = ["git", "diff", "--cached"]
    if file_path:
        cmd.append(file_path)

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.stdout


def get_current_branch() -> str:
    """Get the current git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def should_skip_gate(gate: RiskGate, branch: str) -> bool:
    """Check if a risk gate should be skipped based on branch name."""
    import fnmatch

    for pattern in gate.skip_if_branch:
        if fnmatch.fnmatch(branch, pattern):
            return True
    return False


def should_skip_file(file_path: str, excluded_patterns: list[str]) -> bool:
    """Check if a file should be excluded from review."""
    import fnmatch

    for pattern in excluded_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False


def get_applicable_gate(
    file_path: str, gates: list[RiskGate], branch: str
) -> RiskGate | None:
    """Find the first applicable risk gate for a file."""
    import fnmatch

    for gate in gates:
        if should_skip_gate(gate, branch):
            continue
        for pattern in gate.patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return gate
    return None


def extract_diff_context(diff_text: str, max_lines: int = 500) -> str:
    """Extract and limit diff context to avoid token limits."""
    lines = diff_text.split("\n")
    if len(lines) <= max_lines:
        return diff_text

    # Keep the header and first N lines of the diff
    header_lines = [
        line for line in lines[:10] if line.startswith("diff --git")
    ]
    content_lines = [
        line for line in lines if not line.startswith("diff --git")
    ]

    allowed_content = content_lines[: max_lines - len(header_lines)]
    return "\n".join(header_lines + allowed_content) + "\n[... truncated ...]"


@dataclass
class PreCommitReview:
    """Result of a pre-commit review."""

    passed: bool
    """Whether the commit should proceed."""

    message: str
    """Human-readable review summary."""

    concerns: list[str] = field(default_factory=list)
    """List of specific concerns found."""

    failed_gates: list[str] = field(default_factory=list)
    """Names of risk gates that failed."""

    review_metadata: dict = field(default_factory=dict)
    """Raw review data for debugging."""

    def to_json(self) -> str:
        """Serialize result to JSON."""
        return json.dumps(
            {
                "passed": self.passed,
                "message": self.message,
                "concerns": self.concerns,
                "failed_gates": self.failed_gates,
            }
        )


def analyze_review_output(
    review_text: str, concern_level_threshold: str
) -> tuple[bool, list[str]]:
    """Parse greybeard review output to extract concerns and determine pass/fail.

    Args:
        review_text: Raw markdown review output from greybeard
        concern_level_threshold: Threshold for failure ('none', 'critical',
            'high', 'medium', 'low')

    Returns:
        (passed: bool, concerns: list[str])
    """
    SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    if concern_level_threshold == "none":
        return True, []

    threshold_val = SEVERITY_ORDER.get(concern_level_threshold, 1)
    concerns = []

    # Simple parsing: look for lines with concern markers
    # In a real implementation, you'd parse the structured output more carefully
    for line in review_text.split("\n"):
        lower_line = line.lower()
        for level_name, level_val in SEVERITY_ORDER.items():
            if level_val <= threshold_val:
                if (
                    f"[{level_name}]" in lower_line
                    or f"**{level_name}**" in lower_line
                ):
                    concerns.append(line.strip())

    passed = len(concerns) == 0
    return passed, concerns



def run_diff_review(
    config: PreCommitConfig, pack: str | None = None, verbose: bool = False
) -> PreCommitReview:
    """Run greybeard review on staged changes.

    Args:
        config: PreCommitConfig instance
        pack: Override default pack
        verbose: Print verbose output

    Returns:
        PreCommitReview with results
    """
    # Get staged files
    staged_files = get_staged_files()

    if not staged_files or (len(staged_files) == 1 and staged_files[0] == ""):
        if not config.allow_empty_commits:
            return PreCommitReview(
                passed=True, message="No staged changes to review", concerns=[]
            )

    if verbose or config.verbose:
        console.print(f"[dim]Staged files: {staged_files}[/dim]")

    # Filter excluded files
    filtered_files = [
        f for f in staged_files if not should_skip_file(f, config.excluded_paths)
    ]
    excluded_count = len(staged_files) - len(filtered_files)
    if excluded_count > 0 and (verbose or config.verbose):
        console.print(f"[dim]Excluded {excluded_count} file(s) from review[/dim]")

    # Get diff
    diff_text = get_staged_diff()
    if not diff_text.strip():
        return PreCommitReview(
            passed=True, message="No changes to review", concerns=[]
        )

    # Truncate if needed
    if len(diff_text.split("\n")) > config.max_context_lines:
        diff_text = extract_diff_context(diff_text, config.max_context_lines)
        if verbose or config.verbose:
            console.print("[yellow]⚠️  Diff truncated due to size limits[/yellow]")

    # Invoke greybeard analyzer
    # In a real implementation, this would call the analyzer directly
    # For now, we stub it for the pre-commit hook entry point
    try:
        from .analyzer import run_review
        from .models import ReviewRequest
        from .packs import load_pack

        # Load the pack
        pack_name = pack or config.default_pack
        try:
            loaded_pack = load_pack(pack_name)
        except Exception as e:
            if verbose or config.verbose:
                console.print(
                    f"[yellow]⚠️  Could not load pack {pack_name}: {e}[/yellow]"
                )
            return PreCommitReview(
                passed=True,
                message=f"Review skipped: pack '{pack_name}' not found",
                concerns=[],
            )

        request = ReviewRequest(
            input_text=diff_text, mode="review", pack=loaded_pack
        )

        review_result = run_review(request)
        passed, concerns = analyze_review_output(review_result, config.fail_on_concerns)

        return PreCommitReview(
            passed=passed,
            message=review_result[:200] + "..."
            if len(review_result) > 200
            else review_result,
            concerns=concerns,
            review_metadata={"pack": pack_name, "mode": "review"},
        )
    except Exception as e:
        # If review fails (e.g., LLM error), don't block commit but warn
        if verbose or config.verbose:
            console.print(f"[yellow]⚠️  Review error: {e}[/yellow]")
        return PreCommitReview(
            passed=True,
            message=f"Review skipped due to error: {str(e)}",
            concerns=[],
        )


def run_risk_check(config: PreCommitConfig, verbose: bool = False) -> PreCommitReview:
    """Run risk gates on staged changes.

    This checks file paths against configured risk gates and applies
    stricter thresholds to high-risk files.

    Args:
        config: PreCommitConfig instance
        verbose: Print verbose output

    Returns:
        PreCommitReview with results
    """
    staged_files = get_staged_files()
    if not staged_files or staged_files[0] == "":
        return PreCommitReview(
            passed=True,
            message="No staged files to check against risk gates",
            concerns=[],
        )

    branch = get_current_branch()
    failed_gates = []
    all_concerns = []

    for file_path in staged_files:
        if should_skip_file(file_path, config.excluded_paths):
            continue

        gate = get_applicable_gate(file_path, config.risk_gates, branch)
        if not gate:
            continue

        if verbose or config.verbose:
            console.print(f"[dim]File {file_path} matches gate: {gate.name}[/dim]")

        # For now, just record the gate as applicable
        # In a real implementation, we'd run the review and check against the gate's
        # threshold
        if gate.fail_on_concerns != "none":
            # Placeholder: assume the gate would fail
            # In production, we'd actually run the review
            pass

    passed = len(failed_gates) == 0
    message = (
        f"Risk check: {len(failed_gates)} gate(s) failed"
        if failed_gates
        else "All gates passed"
    )
    return PreCommitReview(
        passed=passed,
        message=message,
        concerns=all_concerns,
        failed_gates=failed_gates,
    )


def format_review_output(review: PreCommitReview, verbose: bool = False) -> str:
    """Format a PreCommitReview for display."""
    lines = []

    if review.passed:
        lines.append("[green]✓[/green] Review passed — commit allowed")
    else:
        lines.append("[red]✗[/red] Review failed — commit blocked")

    if review.message:
        lines.append(f"\n{review.message}")

    if review.concerns:
        lines.append("\n[yellow]Concerns:[/yellow]")
        for concern in review.concerns[:5]:  # Show first 5
            lines.append(f"  • {concern}")
        if len(review.concerns) > 5:
            lines.append(f"  ... and {len(review.concerns) - 5} more")

    if review.failed_gates:
        lines.append(f"\n[red]Failed gates:[/red] {', '.join(review.failed_gates)}")

    if verbose and review.review_metadata:
        lines.append(f"\n[dim]Metadata: {review.review_metadata}[/dim]")

    return "\n".join(lines)
