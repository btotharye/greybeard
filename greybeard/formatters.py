"""Output format converters for greybeard review results.

Supported formats:
  markdown  (default) — plain Markdown, same as current behaviour
  json      — structured JSON with parsed sections + raw markdown
  html      — self-contained HTML page with basic styling
  jira      — Jira wiki markup

All converters receive the raw Markdown string produced by the LLM and a
ReviewMetadata object that carries context (mode, pack, model, timestamp).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

OutputFormat = Literal["markdown", "json", "html", "jira"]
SUPPORTED_FORMATS: list[str] = ["markdown", "json", "html", "jira"]

# File extension to use when --output is not specified or has no extension
FORMAT_EXTENSIONS: dict[str, str] = {
    "markdown": ".md",
    "json": ".json",
    "html": ".html",
    "jira": ".txt",
}


@dataclass
class ReviewMetadata:
    """Metadata about the review run, injected into structured output formats."""

    mode: str
    pack_name: str
    backend: str
    model: str
    generated_at: str = field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def convert(markdown: str, fmt: OutputFormat, meta: ReviewMetadata) -> str:
    """Convert a Markdown review string to the requested output format."""
    if fmt == "markdown":
        return markdown
    elif fmt == "json":
        return _to_json(markdown, meta)
    elif fmt == "html":
        return _to_html(markdown, meta)
    elif fmt == "jira":
        return _to_jira(markdown, meta)
    else:
        raise ValueError(f"Unsupported format: {fmt!r}. Choose from: {SUPPORTED_FORMATS}")


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

# Sections we expect the LLM to produce (from modes.py OUTPUT_FORMAT)
_SECTION_PATTERNS = [
    ("summary", r"##\s+Summary"),
    ("key_risks", r"##\s+Key\s+Risks"),
    ("tradeoffs", r"##\s+Tradeoffs?"),
    ("questions", r"##\s+Questions\s+to\s+Answer\s+Before\s+Proceeding"),
    ("communication_language", r"##\s+Suggested\s+Communication\s+Language"),
]


def _parse_sections(markdown: str) -> dict[str, str]:
    """Extract named sections from the Markdown response."""
    # Build split points: (start_index, section_name)
    markers: list[tuple[int, str]] = []
    for name, pattern in _SECTION_PATTERNS:
        for m in re.finditer(pattern, markdown, re.IGNORECASE):
            markers.append((m.start(), name, m.end()))

    # Sort by position
    markers.sort(key=lambda x: x[0])

    sections: dict[str, str] = {}
    for i, (start, name, end) in enumerate(markers):
        # Content runs from end of this header to start of next header (or EOF)
        content_start = end
        content_end = markers[i + 1][0] if i + 1 < len(markers) else len(markdown)
        raw = markdown[content_start:content_end].strip()
        sections[name] = raw

    return sections


def _parse_bullets(text: str) -> list[str]:
    """Extract bullet-list items from a Markdown section body."""
    items = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ", "+ ")):
            items.append(line[2:].strip())
        elif re.match(r"^\d+\.\s", line):
            items.append(re.sub(r"^\d+\.\s+", "", line).strip())
    return items if items else [text] if text else []


def _to_json(markdown: str, meta: ReviewMetadata) -> str:
    """Convert Markdown review to a structured JSON string."""
    sections = _parse_sections(markdown)

    # For list-heavy sections, try to extract bullets; otherwise keep as prose
    key_risks_raw = sections.get("key_risks", "")
    questions_raw = sections.get("questions", "")

    payload = {
        "format_version": "1.0",
        "generated_at": meta.generated_at,
        "mode": meta.mode,
        "pack": meta.pack_name,
        "backend": meta.backend,
        "model": meta.model,
        "sections": {
            "summary": sections.get("summary", ""),
            "key_risks": _parse_bullets(key_risks_raw) or key_risks_raw,
            "tradeoffs": sections.get("tradeoffs", ""),
            "questions": _parse_bullets(questions_raw) or questions_raw,
            "communication_language": sections.get("communication_language", ""),
        },
        "raw_markdown": markdown,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>🧙 greybeard review — {mode} / {pack}</title>
  <style>
    :root {{
      --bg: #1a1a2e;
      --surface: #16213e;
      --accent: #9b59b6;
      --accent-light: #c39bd3;
      --text: #e0e0e0;
      --text-muted: #888;
      --border: #2c2c4a;
      --risk: #e74c3c;
      --question: #3498db;
      --code-bg: #0d1117;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.7;
      padding: 2rem 1rem;
    }}
    .container {{ max-width: 860px; margin: 0 auto; }}
    header {{
      border-left: 4px solid var(--accent);
      padding: 1rem 1.25rem;
      background: var(--surface);
      border-radius: 0 8px 8px 0;
      margin-bottom: 2rem;
    }}
    header h1 {{ font-size: 1.4rem; color: var(--accent-light); }}
    header .meta {{ font-size: 0.82rem; color: var(--text-muted); margin-top: 0.3rem; }}
    h2 {{
      font-size: 1.1rem;
      color: var(--accent-light);
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.3rem;
      margin: 1.8rem 0 0.8rem;
    }}
    p {{ margin-bottom: 0.8rem; }}
    ul, ol {{ padding-left: 1.5rem; margin-bottom: 0.8rem; }}
    li {{ margin-bottom: 0.3rem; }}
    code {{
      font-family: "JetBrains Mono", "Fira Code", monospace;
      background: var(--code-bg);
      padding: 0.1em 0.35em;
      border-radius: 3px;
      font-size: 0.88em;
    }}
    pre {{
      background: var(--code-bg);
      padding: 1rem;
      border-radius: 6px;
      overflow-x: auto;
      margin-bottom: 1rem;
      font-size: 0.88em;
    }}
    pre code {{ background: none; padding: 0; }}
    hr {{ border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }}
    blockquote {{
      border-left: 3px solid var(--accent);
      padding-left: 1rem;
      color: var(--text-muted);
      font-style: italic;
      margin-bottom: 0.8rem;
    }}
    em {{ color: var(--text-muted); font-style: italic; }}
    strong {{ color: #fff; }}
    footer {{
      margin-top: 3rem;
      font-size: 0.78rem;
      color: var(--text-muted);
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>🧙 greybeard review</h1>
      <div class="meta">
        Mode: <strong>{mode}</strong> &nbsp;·&nbsp;
        Pack: <strong>{pack}</strong> &nbsp;·&nbsp;
        Model: <strong>{model}</strong> &nbsp;·&nbsp;
        {generated_at}
      </div>
    </header>
    <main>
{body}
    </main>
    <footer>Generated by greybeard · {generated_at}</footer>
  </div>
</body>
</html>
"""


def _md_to_html_body(markdown: str) -> str:
    """
    Minimal Markdown-to-HTML converter (no external deps).

    Handles: headings, bold, italic, inline code, fenced code blocks,
    bullet/numbered lists, blockquotes, horizontal rules, paragraphs.
    Also handles nested lists via indentation.
    """
    lines = markdown.splitlines()
    output: list[str] = []
    i = 0
    list_stack: list[tuple[str, int]] = []  # [(type, indent_level), ...]
    in_blockquote = False

    def close_lists(up_to_indent: int = -1) -> None:
        """Close lists back to a certain indentation level."""
        while list_stack and (up_to_indent < 0 or list_stack[-1][1] >= up_to_indent):
            list_type, _ = list_stack.pop()
            output.append(f"</{list_type}>")

    def close_blockquote() -> None:
        nonlocal in_blockquote
        if in_blockquote:
            output.append("</blockquote>")
            in_blockquote = False

    def inline(text: str) -> str:
        """Apply inline Markdown transforms."""
        # Escape HTML entities first
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Fenced inline code (before bold/italic to avoid escaping inside)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        # Bold+italic
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
        # Bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        # Italic
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        # Links
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        return text

    def get_indent_level(line: str) -> int:
        """Get the indentation level (in spaces) of a line."""
        return len(line) - len(line.lstrip())

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.startswith("```"):
            close_lists()
            close_blockquote()
            lang = line[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                raw = lines[i].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                code_lines.append(raw)
                i += 1
            lang_attr = f' class="language-{lang}"' if lang else ""
            output.append(f"<pre><code{lang_attr}>{chr(10).join(code_lines)}</code></pre>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}$|^\*{3,}$|^_{3,}$", line.strip()):
            close_lists()
            close_blockquote()
            output.append("<hr />")
            i += 1
            continue

        # Headings
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_match:
            close_lists()
            close_blockquote()
            level = len(heading_match.group(1))
            text = inline(heading_match.group(2))
            output.append(f"<h{level}>{text}</h{level}>")
            i += 1
            continue

        # Blockquote
        if line.strip().startswith("> "):
            close_lists()
            if not in_blockquote:
                output.append("<blockquote>")
                in_blockquote = True
            output.append(f"<p>{inline(line.strip()[2:])}</p>")
            i += 1
            continue
        else:
            close_blockquote()

        # Unordered list (including indented)
        ul_match = re.match(r"^\s*([-*+])\s+(.*)", line)
        if ul_match:
            indent = get_indent_level(line)
            # Close lists at deeper indentation levels
            close_lists(indent)
            # Check if we need to open a new list
            if not list_stack or list_stack[-1][0] != "ul" or list_stack[-1][1] < indent:
                output.append("<ul>")
                list_stack.append(("ul", indent))
            output.append(f"<li>{inline(ul_match.group(2))}</li>")
            i += 1
            continue

        # Ordered list (including indented)
        ol_match = re.match(r"^\s*\d+\.\s+(.*)", line)
        if ol_match:
            indent = get_indent_level(line)
            # Close lists at deeper indentation levels
            close_lists(indent)
            # Check if we need to open a new list
            if not list_stack or list_stack[-1][0] != "ol" or list_stack[-1][1] < indent:
                output.append("<ol>")
                list_stack.append(("ol", indent))
            output.append(f"<li>{inline(ol_match.group(1))}</li>")
            i += 1
            continue

        # Blank line — only close lists if we're truly leaving the list context
        # (i.e., we have content coming that's not a list item)
        if not line.strip():
            # Look ahead to see if the next non-blank line is a list item
            next_line_idx = i + 1
            while next_line_idx < len(lines) and not lines[next_line_idx].strip():
                next_line_idx += 1

            # If next line is a list item at same or less indentation, keep lists open
            next_line = lines[next_line_idx] if next_line_idx < len(lines) else ""
            current_indent = list_stack[-1][1] if list_stack else -1
            is_next_list = bool(re.match(r"^\s*([-*+]|\d+\.)\s+", next_line))
            next_indent = get_indent_level(next_line) if is_next_list else -1

            if not is_next_list or next_indent <= current_indent:
                close_lists()

            close_blockquote()
            output.append("")
            i += 1
            continue

        # Regular paragraph line
        close_lists()
        output.append(f"<p>{inline(line)}</p>")
        i += 1

    close_lists()
    close_blockquote()
    return "\n".join(output)


def _to_html(markdown: str, meta: ReviewMetadata) -> str:
    """Convert Markdown review to a styled, self-contained HTML page."""
    body = _md_to_html_body(markdown)
    return _HTML_TEMPLATE.format(
        mode=meta.mode,
        pack=meta.pack_name,
        model=meta.model,
        generated_at=meta.generated_at,
        body=body,
    )


# ---------------------------------------------------------------------------
# Jira wiki markup
# ---------------------------------------------------------------------------


def _to_jira(markdown: str, meta: ReviewMetadata) -> str:
    """Convert Markdown review to Jira wiki markup."""
    lines = markdown.splitlines()
    output: list[str] = []

    # Header banner
    output.append("h1. 🧙 greybeard review")
    output.append("||Mode||Pack||Model||Generated||")
    output.append(f"|{meta.mode}|{meta.pack_name}|{meta.model}|{meta.generated_at}|")
    output.append("")

    in_code = False
    code_lang = ""

    for line in lines:
        # Fenced code block
        if line.startswith("```"):
            if not in_code:
                code_lang = line[3:].strip()
                lang_attr = code_lang if code_lang else ""
                output.append(f"{{code:{lang_attr}}}" if lang_attr else "{code}")
                in_code = True
            else:
                output.append("{code}")
                in_code = False
            continue

        if in_code:
            output.append(line)
            continue

        # Headings — Jira uses h1. h2. etc.
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = _md_inline_to_jira(heading_match.group(2))
            output.append(f"h{level}. {text}")
            continue

        # Horizontal rule
        if re.match(r"^-{3,}$|^\*{3,}$|^_{3,}$", line.strip()):
            output.append("----")
            continue

        # Unordered list
        ul_match = re.match(r"^(\s*)[-*+]\s+(.*)", line)
        if ul_match:
            indent = len(ul_match.group(1)) // 2 + 1
            text = _md_inline_to_jira(ul_match.group(2))
            output.append(f"{'*' * indent} {text}")
            continue

        # Ordered list
        ol_match = re.match(r"^(\s*)\d+\.\s+(.*)", line)
        if ol_match:
            indent = len(ol_match.group(1)) // 2 + 1
            text = _md_inline_to_jira(ol_match.group(2))
            output.append(f"{'#' * indent} {text}")
            continue

        # Blockquote
        if line.startswith("> "):
            text = _md_inline_to_jira(line[2:])
            output.append(f"bq. {text}")
            continue

        # Regular line (inline transforms)
        output.append(_md_inline_to_jira(line))

    return "\n".join(output)


def _md_inline_to_jira(text: str) -> str:
    """Convert inline Markdown syntax to Jira wiki markup.

    Uses temporary placeholders so bold/italic don't double-convert each other.
    """
    # Inline code first (protect content inside backticks)
    text = re.sub(r"`([^`]+)`", r"{{\1}}", text)
    # Bold+italic — replace with placeholder to avoid italic re-matching
    text = re.sub(r"\*\*\*(.+?)\*\*\*", lambda m: f"JIRA_BI_START{m.group(1)}JIRA_BI_END", text)
    # Bold — replace with placeholder
    text = re.sub(r"\*\*(.+?)\*\*", lambda m: f"JIRA_B_START{m.group(1)}JIRA_B_END", text)
    # Italic: remaining single *text* → _text_
    text = re.sub(r"\*(.+?)\*", r"_\1_", text)
    # Links: [label](url) → [label|url]
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"[\1|\2]", text)
    # Resolve placeholders now that italic pass is done
    text = text.replace("JIRA_BI_START", "*_").replace("JIRA_BI_END", "_*")
    text = text.replace("JIRA_B_START", "*").replace("JIRA_B_END", "*")
    return text
