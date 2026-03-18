"""Output formatting and documentation generation.

Provides structured output in multiple formats (markdown, JSON, YAML).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from datetime import datetime


class DocumentationGenerator:
    """Generate and format agent outputs."""

    def format(
        self,
        content: str,
        format_type: str = "markdown",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Format content in specified format.
        
        Args:
            content: The content to format
            format_type: Output format (markdown, json, yaml)
            metadata: Optional metadata to include
            
        Returns:
            Formatted output
        """
        if format_type == "json":
            return self._format_json(content, metadata)
        elif format_type == "yaml":
            return self._format_yaml(content, metadata)
        else:  # markdown (default)
            return self._format_markdown(content, metadata)

    def _format_markdown(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Format as markdown."""
        lines = []
        
        if metadata:
            lines.append("---")
            for key, value in metadata.items():
                lines.append(f"{key}: {value}")
            lines.append("---")
            lines.append("")
        
        lines.append(content)
        return "\n".join(lines)

    def _format_json(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Format as JSON."""
        data = {
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if metadata:
            data["metadata"] = metadata
        
        return json.dumps(data, indent=2)

    def _format_yaml(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Format as YAML."""
        try:
            import yaml
        except ImportError:
            # Fallback to JSON if yaml not available
            return self._format_json(content, metadata)
        
        data = {
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if metadata:
            data["metadata"] = metadata
        
        return yaml.dump(data, default_flow_style=False)

    def save_markdown(self, content: str, filepath: str) -> None:
        """Save content as markdown file.
        
        Args:
            content: Content to save
            filepath: Path to save to
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def save_json(self, data: dict[str, Any] | list[Any], filepath: str) -> None:
        """Save data as JSON file.
        
        Args:
            data: Data to save
            filepath: Path to save to
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(data, f, indent=2)

    def save_yaml(self, data: dict[str, Any], filepath: str) -> None:
        """Save data as YAML file.
        
        Args:
            data: Data to save
            filepath: Path to save to
        """
        try:
            import yaml
        except ImportError:
            self.save_json(data, filepath)
            return
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def create_template(
        self,
        title: str,
        sections: dict[str, str],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a markdown template with sections.
        
        Args:
            title: Document title
            sections: Dictionary of section name -> placeholder text
            metadata: Optional metadata
            
        Returns:
            Markdown template
        """
        lines = []
        
        if metadata:
            lines.append("---")
            for key, value in metadata.items():
                lines.append(f"{key}: {value}")
            lines.append("---")
            lines.append("")
        
        lines.append(f"# {title}")
        lines.append("")
        
        for section_name, placeholder in sections.items():
            lines.append(f"## {section_name}")
            lines.append(placeholder)
            lines.append("")
        
        return "\n".join(lines)
