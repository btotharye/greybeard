"""Decision history — save reviews and surface recurring patterns.

Storage is pluggable (see storage.py).
Default: ~/.greybeard/history.jsonl (append-only JSONL, one record per line)

Schema per entry:
  {
    "timestamp":     "2026-03-18T10:05:00Z",   # ISO 8601 UTC
    "decision_name": "auth-migration-q1",       # user-supplied label
    "pack":          "staff-core",              # pack used
    "mode":          "review",                  # analyze mode
    "summary":       "...",                     # first 500 chars of LLM output
    "key_risks":     ["knowledge concentration", ...],  # extracted risk phrases
    "key_questions": ["Have you considered ...?", ...]  # extracted questions
  }

Pattern detection flags any risk that appears 3+ times in the last 30 days.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .storage import FileHistoryStorage, HistoryStorage

# For backward compatibility with cli.py and tests
HISTORY_DIR = Path.home() / ".greybeard"
HISTORY_FILE = HISTORY_DIR / "history.jsonl"

# Risks appearing this many times in the window get flagged
PATTERN_THRESHOLD = 3

# ── Suggestions keyed on common risk keywords ────────────────────────────────
RISK_ADVICE: dict[str, str] = {
    "knowledge concentration": (
        "Document ownership and bus-factor mitigations. "
        "Consider pairing sessions or runbook rotations."
    ),
    "bus factor": (
        "Pair on critical paths and write runbooks so any team member can operate the system."
    ),
    "no rollback": (
        "Design every change to be reversible. Feature flags and blue-green deployments help."
    ),
    "rollback": ("Make sure every deploy has a tested rollback path before you ship."),
    "data loss": ("Add pre-migration snapshots and a restore drill to your runbook."),
    "missing tests": ("Establish a test coverage gate so this pattern doesn't recur."),
    "test coverage": ("Set a minimum coverage threshold in CI so gaps surface before review."),
    "toil": ("Automate the toil or schedule a dedicated reduction sprint."),
    "single point of failure": ("Add redundancy or at least a documented fallback procedure."),
    "no monitoring": ("Add alerting before you ship — you can't fix what you can't see."),
    "observability": ("Instrument the happy path first, then add anomaly alerts."),
    "scope creep": ("Lock the scope before the next review and use a decision log for additions."),
    "deadline": ("Revisit the scope/quality trade-off explicitly with stakeholders."),
    "security": ("Run a threat model early — retrofitting security is expensive."),
    "auth": ("Verify AuthN/AuthZ flows with a dedicated security review or pen test."),
    "performance": ("Add a benchmark suite and a latency budget so regressions surface in CI."),
    "dependency": ("Pin critical dependencies and audit transitive ones periodically."),
    "vendor lock": ("Abstract the vendor behind an interface so you can swap it out if needed."),
    "communication": (
        "Make the decision visible in writing and get explicit sign-off from affected teams."
    ),
    "alignment": ("Run a DACI or RFC process to force alignment before execution."),
    "technical debt": ("Track debt as tickets so it doesn't silently compound."),
    "migration": (
        "Build a validation step that proves the migrated state is correct before cutting over."
    ),
}


# ── Global storage instance (injectable for testing) ──────────────────────────
_storage: HistoryStorage | None = None


def _get_storage() -> HistoryStorage:
    """Get or create the default storage instance.

    Uses lazy initialization so monkeypatching of HISTORY_FILE works in tests.
    """
    global _storage
    if _storage is None:
        _storage = FileHistoryStorage(HISTORY_FILE)
    return _storage


def set_storage(storage: HistoryStorage) -> None:
    """Set the history storage backend (for testing or alternative backends)."""
    global _storage
    _storage = storage


def _now_utc() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Risk / question extraction ────────────────────────────────────────────────


def _extract_key_risks(review_text: str) -> list[str]:
    """Extract risk phrases from LLM review text.

    Looks for:
      - Bulleted/numbered items under risk/concern headings
      - Lines that contain risk-signal words
    Returns up to 10 de-duplicated, lower-cased short phrases.
    """
    risks: list[str] = []
    in_risk_section = False

    risk_heading = re.compile(
        r"^#{1,4}\s*(risk|concern|watch\s*out|caution|warning|flag|blind\s*spot)",
        re.IGNORECASE,
    )
    any_heading = re.compile(r"^#{1,4}\s+\S")
    bullet = re.compile(r"^\s*[-*•]\s+(.+)")
    numbered = re.compile(r"^\s*\d+[.)]\s+(.+)")
    signal_words = re.compile(
        r"\b(risk|concern|danger|critical|caution|warning|fail|loss|outage|"
        r"concentration|missing|lack|no\s+test|no\s+monitor|rollback|debt|toil|"
        r"single\s+point|bus\s+factor|knowledge\s+gap)\b",
        re.IGNORECASE,
    )

    for line in review_text.splitlines():
        stripped = line.strip()
        if risk_heading.match(stripped):
            in_risk_section = True
            continue
        if any_heading.match(stripped) and not risk_heading.match(stripped):
            in_risk_section = False

        m = bullet.match(line) or numbered.match(line)
        if m:
            text = m.group(1).strip()
            if in_risk_section or signal_words.search(text):
                phrase = _clean_phrase(text)
                if phrase and phrase not in risks:
                    risks.append(phrase)

    # Fallback: scan every line for signal words if nothing found
    if not risks:
        for line in review_text.splitlines():
            if signal_words.search(line):
                phrase = _clean_phrase(line.strip())
                if phrase and phrase not in risks:
                    risks.append(phrase)
                if len(risks) >= 10:
                    break

    return risks[:10]


def _extract_key_questions(review_text: str) -> list[str]:
    """Extract sentences ending in '?' from the review text. Returns up to 8."""
    questions: list[str] = []
    for line in review_text.splitlines():
        stripped = line.strip()
        if stripped.endswith("?") and len(stripped) > 15:
            clean = re.sub(r"^[-*•\d.)]+\s*", "", stripped)
            if clean and clean not in questions:
                questions.append(clean)
        if len(questions) >= 8:
            break
    return questions


def _clean_phrase(text: str) -> str:
    """Strip markdown, links, and trailing punctuation from a phrase."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [label](url)
    text = re.sub(r"[*_`#]", "", text)
    text = text.strip(" .,;:")
    # Keep it short — first sentence only
    text = re.split(r"[.!]", text)[0].strip()
    return text[:120].lower() if text else ""


# ── Public API ────────────────────────────────────────────────────────────────


def save_decision(name: str, review_text: str, pack: str, mode: str) -> Path:
    """Append one review entry to the history.

    Args:
        name:        User-supplied decision label (e.g. "auth-migration-q1").
        review_text: Full LLM output string.
        pack:        Content pack name used.
        mode:        Review mode (review | mentor | coach | self-check).

    Returns:
        Path to the history file.
    """
    entry: dict[str, Any] = {
        "timestamp": _now_utc(),
        "decision_name": name,
        "pack": pack,
        "mode": mode,
        "summary": review_text[:500].replace("\n", " "),
        "key_risks": _extract_key_risks(review_text),
        "key_questions": _extract_key_questions(review_text),
    }
    _get_storage().save_entry(entry)
    return HISTORY_FILE


def load_history(days: int = 30, pack: str | None = None) -> list[dict[str, Any]]:
    """Load and filter history entries.

    Args:
        days: Only include entries from the last N days. 0 = all time.
        pack: If set, only include entries for this pack name.

    Returns:
        List of entry dicts, newest first.
    """
    return _get_storage().load_entries(days=days, pack=pack)


def analyze_trends(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Identify risk patterns across a set of history entries.

    Returns a dict with:
      - total_decisions (int)
      - risk_frequency  (list of (risk, count) sorted by count desc)
      - flagged_risks   (risks at or above PATTERN_THRESHOLD)
      - suggestions     (dict: risk -> advice string)
      - most_used_packs (list of (pack, count))
      - date_range      (dict with 'from' and 'to' ISO strings)
    """
    if not history:
        return {
            "total_decisions": 0,
            "risk_frequency": [],
            "flagged_risks": [],
            "suggestions": {},
            "most_used_packs": [],
            "date_range": {"from": None, "to": None},
        }

    risk_counter: Counter[str] = Counter()
    pack_counter: Counter[str] = Counter()
    timestamps: list[str] = []

    for entry in history:
        for risk in entry.get("key_risks", []):
            # Normalise: lowercase, collapse whitespace
            normalised = re.sub(r"\s+", " ", risk.lower().strip())
            if normalised:
                risk_counter[normalised] += 1
        if entry.get("pack"):
            pack_counter[entry["pack"]] += 1
        if entry.get("timestamp"):
            timestamps.append(entry["timestamp"])

    risk_frequency = risk_counter.most_common()
    flagged = [r for r, count in risk_frequency if count >= PATTERN_THRESHOLD]

    # Build suggestions for flagged risks
    suggestions: dict[str, str] = {}
    for risk in flagged:
        for keyword, advice in RISK_ADVICE.items():
            if keyword in risk:
                suggestions[risk] = advice
                break
        if risk not in suggestions:
            suggestions[risk] = (
                f"You've flagged '{risk}' {risk_counter[risk]} times. "
                "Consider scheduling a dedicated retro or RFC to address this pattern."
            )

    timestamps.sort()
    return {
        "total_decisions": len(history),
        "risk_frequency": risk_frequency,
        "flagged_risks": flagged,
        "suggestions": suggestions,
        "most_used_packs": pack_counter.most_common(),
        "date_range": {
            "from": timestamps[0] if timestamps else None,
            "to": timestamps[-1] if timestamps else None,
        },
    }
