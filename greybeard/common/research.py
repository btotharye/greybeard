"""Research capability for agents.

Provides methods for gathering context, researching topics, and
analyzing existing data sources.
"""

from __future__ import annotations

from typing import Any
from pathlib import Path
import json


class ResearchCapability:
    """Research and context gathering for agents."""

    def __init__(self):
        """Initialize research capability."""
        self.cached_research: dict[str, Any] = {}

    def research_topic(self, topic: str, sources: list[str] | None = None) -> str:
        """Research a topic using available sources.
        
        Args:
            topic: Topic to research
            sources: Optional list of data sources
            
        Returns:
            Research summary
        """
        if topic in self.cached_research:
            return self.cached_research[topic]
        
        # Placeholder for actual research implementation
        # Could integrate with web APIs, documentation, etc.
        summary = f"Research on: {topic}"
        self.cached_research[topic] = summary
        return summary

    def gather_file_context(self, filepath: str) -> str:
        """Gather context from a file.
        
        Args:
            filepath: Path to file to analyze
            
        Returns:
            File content or summary
        """
        try:
            path = Path(filepath)
            if path.is_file():
                return path.read_text()
            return f"File not found: {filepath}"
        except Exception as e:
            return f"Error reading file: {e}"

    def analyze_structure(self, dirpath: str) -> dict[str, Any]:
        """Analyze directory structure and contents.
        
        Args:
            dirpath: Directory path to analyze
            
        Returns:
            Analysis of directory structure
        """
        try:
            path = Path(dirpath)
            if not path.is_dir():
                return {"error": f"Not a directory: {dirpath}"}
            
            structure = {
                "files": [],
                "directories": [],
                "file_count": 0,
                "dir_count": 0,
            }
            
            for item in path.iterdir():
                if item.is_file():
                    structure["files"].append(item.name)
                    structure["file_count"] += 1
                elif item.is_dir() and not item.name.startswith("."):
                    structure["directories"].append(item.name)
                    structure["dir_count"] += 1
            
            return structure
        except Exception as e:
            return {"error": str(e)}

    def get_git_context(self, repo_path: str | None = None) -> dict[str, Any]:
        """Get git repository context.
        
        Args:
            repo_path: Optional path to git repo (defaults to cwd)
            
        Returns:
            Git repository information
        """
        import subprocess
        
        try:
            cwd = repo_path or "."
            
            # Get current branch
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=cwd,
                text=True
            ).strip()
            
            # Get recent commits
            log = subprocess.check_output(
                ["git", "log", "--oneline", "-n", "10"],
                cwd=cwd,
                text=True
            ).strip()
            
            # Get diff summary
            diff = subprocess.check_output(
                ["git", "diff", "--stat"],
                cwd=cwd,
                text=True
            ).strip()
            
            return {
                "current_branch": branch,
                "recent_commits": log,
                "current_diff": diff,
            }
        except Exception as e:
            return {"error": str(e)}

    def load_json_data(self, filepath: str) -> dict[str, Any] | list[Any]:
        """Load and parse JSON data.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Parsed JSON data
        """
        try:
            path = Path(filepath)
            with path.open() as f:
                return json.load(f)
        except Exception as e:
            return {"error": str(e)}

    def clear_cache(self) -> None:
        """Clear cached research results."""
        self.cached_research.clear()
