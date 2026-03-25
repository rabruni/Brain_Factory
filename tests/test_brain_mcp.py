from __future__ import annotations

import mcp_portal


def test_brain_tools_are_registered():
    for name in ["capture_thought", "search_thoughts", "list_thoughts", "thought_stats"]:
        assert name in mcp_portal.TOOLS


def test_capture_thought_schema_requires_content():
    schema = mcp_portal.TOOLS["capture_thought"]["inputSchema"]

    assert schema["required"] == ["content"]
    assert "tags" in schema["properties"]
    assert "source" in schema["properties"]


def test_search_thoughts_schema_requires_query():
    schema = mcp_portal.TOOLS["search_thoughts"]["inputSchema"]

    assert schema["required"] == ["query"]
    assert "limit" in schema["properties"]
    assert "tag" in schema["properties"]


def test_list_and_stats_schemas_are_optional_only():
    list_schema = mcp_portal.TOOLS["list_thoughts"]["inputSchema"]
    stats_schema = mcp_portal.TOOLS["thought_stats"]["inputSchema"]

    assert "required" not in list_schema
    assert list_schema["properties"].keys() == {"limit", "tag"}
    assert stats_schema == {"type": "object", "properties": {}}
