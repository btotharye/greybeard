"""MCP (Model Context Protocol) server for greybeard.

Run with: greybeard mcp

This starts a stdio-based MCP server that exposes greybeard's review
capabilities as tools. Works with:
  - Claude Desktop
  - Cursor
  - Zed
  - Any MCP-compatible client

Tools exposed:
  - review_decision: Staff-level review of a decision or document
  - self_check: Review your own proposal before sharing
  - coach_communication: Get help phrasing a concern for a specific audience
  - list_packs: List available content packs

Claude Desktop config (~/Library/Application Support/Claude/claude_desktop_config.json):
  {
    "mcpServers": {
      "greybeard": {
        "command": "greybeard",
        "args": ["mcp"]
      }
    }
  }
"""

from __future__ import annotations

import json
import sys

from .analyzer import run_review
from .config import GreybeardConfig
from .models import ReviewRequest
from .packs import list_builtin_packs, list_installed_packs, load_pack

# MCP protocol version
MCP_VERSION = "2024-11-05"


def serve() -> None:
    """Start the MCP stdio server. Blocks until stdin closes."""
    _log("greybeard MCP server starting")
    config = GreybeardConfig.load()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = _handle(request, config)
        except json.JSONDecodeError as e:
            response = _error_response(None, -32700, f"Parse error: {e}")
        except Exception as e:
            response = _error_response(None, -32603, f"Internal error: {e}")

        print(json.dumps(response), flush=True)


def _handle(req: dict, config: GreybeardConfig) -> dict:
    """Dispatch a JSON-RPC request to the appropriate handler."""
    req_id = req.get("id")
    method = req.get("method", "")
    params = req.get("params", {})

    if method == "initialize":
        return _handle_initialize(req_id)
    if method == "tools/list":
        return _handle_tools_list(req_id)
    if method == "tools/call":
        return _handle_tool_call(req_id, params, config)
    if method == "notifications/initialized":
        return None  # type: ignore[return-value]  # no response for notifications

    return _error_response(req_id, -32601, f"Method not found: {method}")


def _handle_initialize(req_id) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": MCP_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "greybeard",
                "version": "0.1.0",
                "description": "Staff-level review and decision assistant",
            },
        },
    }


def _handle_tools_list(req_id) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": [
                {
                    "name": "review_decision",
                    "description": (
                        "Review a decision, design document, or git diff from a Staff Engineer "
                        "perspective. Returns structured markdown with risks, tradeoffs, and "
                        "questions to answer before proceeding."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "input": {
                                "type": "string",
                                "description": "The text to review (diff, design doc, ADR, etc.)",
                            },
                            "context": {
                                "type": "string",
                                "description": "Optional: additional context about this change",
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["review", "mentor", "self-check"],
                                "description": "Review mode (default: review)",
                                "default": "review",
                            },
                            "pack": {
                                "type": "string",
                                "description": (
                                    "Content pack to use (default: staff-core). "
                                    "Run list_packs to see available options."
                                ),
                                "default": "staff-core",
                            },
                        },
                        "required": ["input"],
                    },
                },
                {
                    "name": "self_check",
                    "description": (
                        "Review your own proposal or decision before sharing it. "
                        "Acts as your internal critic, surfacing weak arguments, "
                        "unstated assumptions, and questions your reviewer will ask."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "context": {
                                "type": "string",
                                "description": "The decision or proposal you want to self-check",
                            },
                            "input": {
                                "type": "string",
                                "description": "Optional: supporting document or draft",
                            },
                            "pack": {
                                "type": "string",
                                "description": "Content pack to use (default: staff-core)",
                                "default": "staff-core",
                            },
                        },
                        "required": ["context"],
                    },
                },
                {
                    "name": "coach_communication",
                    "description": (
                        "Get help communicating a concern, risk, or decision to a specific "
                        "audience. Returns suggested phrasings that are collaborative rather "
                        "than blocking."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "concern": {
                                "type": "string",
                                "description": "The concern or decision you need to communicate",
                            },
                            "audience": {
                                "type": "string",
                                "enum": ["team", "peers", "leadership", "customer"],
                                "description": "Who you're communicating with",
                            },
                            "pack": {
                                "type": "string",
                                "description": "Content pack to use (default: mentor-mode)",
                                "default": "mentor-mode",
                            },
                        },
                        "required": ["concern", "audience"],
                    },
                },
                {
                    "name": "list_packs",
                    "description": "List all available content packs (built-in and installed).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                    },
                },
            ]
        },
    }


def _handle_tool_call(req_id, params: dict, config: GreybeardConfig) -> dict:
    tool_name = params.get("name", "")
    args = params.get("arguments", {})

    try:
        if tool_name == "review_decision":
            result = _tool_review_decision(args, config)
        elif tool_name == "self_check":
            result = _tool_self_check(args, config)
        elif tool_name == "coach_communication":
            result = _tool_coach(args, config)
        elif tool_name == "list_packs":
            result = _tool_list_packs()
        else:
            return _error_response(req_id, -32601, f"Unknown tool: {tool_name}")
    except FileNotFoundError as e:
        result = f"Error: {e}"
    except Exception as e:
        result = f"Error running {tool_name}: {e}"

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "content": [{"type": "text", "text": result}],
            "isError": result.startswith("Error:"),
        },
    }


def _tool_review_decision(args: dict, config: GreybeardConfig) -> str:
    pack = load_pack(args.get("pack", config.default_pack))
    mode = args.get("mode", "review")
    request = ReviewRequest(
        mode=mode,  # type: ignore[arg-type]
        pack=pack,
        input_text=args.get("input", ""),
        context_notes=args.get("context", ""),
    )
    return run_review(request, config=config, stream=False)


def _tool_self_check(args: dict, config: GreybeardConfig) -> str:
    pack = load_pack(args.get("pack", config.default_pack))
    request = ReviewRequest(
        mode="self-check",
        pack=pack,
        input_text=args.get("input", ""),
        context_notes=args.get("context", ""),
    )
    return run_review(request, config=config, stream=False)


def _tool_coach(args: dict, config: GreybeardConfig) -> str:
    pack = load_pack(args.get("pack", "mentor-mode"))
    request = ReviewRequest(
        mode="coach",
        pack=pack,
        context_notes=args.get("concern", ""),
        audience=args.get("audience"),  # type: ignore[arg-type]
    )
    return run_review(request, config=config, stream=False)


def _tool_list_packs() -> str:
    lines = ["## Available Content Packs\n", "### Built-in\n"]
    for name in list_builtin_packs():
        try:
            pack = load_pack(name)
            lines.append(f"- **{name}**: {pack.description or pack.perspective[:60]}")
        except Exception:
            lines.append(f"- {name}")

    installed = list_installed_packs()
    if installed:
        lines.append("\n### Installed (remote)\n")
        for p in installed:
            lines.append(f"- **{p['name']}** (from {p['source']}): {p['description']}")

    lines.append("\nInstall more packs with: `greybeard pack install github:owner/repo`")
    return "\n".join(lines)


def _error_response(req_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def _log(msg: str) -> None:
    """Log to stderr (not stdout — that's reserved for JSON-RPC)."""
    print(f"[greybeard-mcp] {msg}", file=sys.stderr)
