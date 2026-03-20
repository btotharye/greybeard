"""Tests for the MCP server."""

from __future__ import annotations

from unittest.mock import patch

from greybeard.config import GreybeardConfig
from greybeard.mcp_server import _handle


def _cfg() -> GreybeardConfig:
    return GreybeardConfig()


class TestMCPInitialize:
    """Test M C P Initialize."""

    def test_initialize_returns_server_info(self):
        """Test initialize returns server info."""
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = _handle(req, _cfg())
        assert resp["id"] == 1
        assert "result" in resp
        assert resp["result"]["serverInfo"]["name"] == "greybeard"

    def test_initialize_includes_capabilities(self):
        """Test initialize includes capabilities."""
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = _handle(req, _cfg())
        assert "tools" in resp["result"]["capabilities"]


class TestMCPToolsList:
    """Test M C P Tools List."""

    def test_tools_list_returns_tools(self):
        """Test tools list returns tools."""
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = _handle(req, _cfg())
        tools = resp["result"]["tools"]
        names = [t["name"] for t in tools]
        assert "review_decision" in names
        assert "self_check" in names
        assert "coach_communication" in names
        assert "list_packs" in names

    def test_all_tools_have_input_schema(self):
        """Test all tools have input schema."""
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = _handle(req, _cfg())
        for tool in resp["result"]["tools"]:
            assert "inputSchema" in tool
            assert "description" in tool


class TestMCPToolCall:
    """Test M C P Tool Call."""

    def test_list_packs_tool(self):
        """Test list packs tool."""
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "list_packs", "arguments": {}},
        }
        resp = _handle(req, _cfg())
        assert "result" in resp
        content = resp["result"]["content"][0]["text"]
        assert "staff-core" in content

    def test_review_decision_tool_mocked(self):
        """Test review decision tool mocked."""
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "review_decision",
                "arguments": {
                    "input": "We are adding a new microservice for auth.",
                    "context": "Mid-sprint migration",
                    "mode": "review",
                    "pack": "staff-core",
                },
            },
        }
        with patch("greybeard.mcp_server.run_review") as mock_run:
            mock_run.return_value = "## Summary\n\nMocked."
            resp = _handle(req, _cfg())

        mock_run.assert_called_once()
        assert resp["result"]["content"][0]["text"] == "## Summary\n\nMocked."

    def test_self_check_tool_mocked(self):
        """Test self check tool mocked."""
        req = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "self_check",
                "arguments": {"context": "Adding a DB table per tenant"},
            },
        }
        with patch("greybeard.mcp_server.run_review") as mock_run:
            mock_run.return_value = "## Summary\n\nSelf-check result."
            _handle(req, _cfg())

        call_kwargs = mock_run.call_args
        request_arg = call_kwargs[0][0]
        assert request_arg.mode == "self-check"

    def test_coach_tool_mocked(self):
        """Test coach tool mocked."""
        req = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "coach_communication",
                "arguments": {
                    "concern": "We are shipping too fast",
                    "audience": "leadership",
                },
            },
        }
        with patch("greybeard.mcp_server.run_review") as mock_run:
            mock_run.return_value = "## Suggested Language\n\nPhrase it this way..."
            _handle(req, _cfg())

        request_arg = mock_run.call_args[0][0]
        assert request_arg.mode == "coach"
        assert request_arg.audience == "leadership"

    def test_unknown_tool_returns_error(self):
        """Test unknown tool returns error."""
        req = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        }
        resp = _handle(req, _cfg())
        assert "error" in resp

    def test_unknown_method_returns_error(self):
        """Test unknown method returns error."""
        req = {"jsonrpc": "2.0", "id": 8, "method": "unknown/method", "params": {}}
        resp = _handle(req, _cfg())
        assert "error" in resp
        assert resp["error"]["code"] == -32601
