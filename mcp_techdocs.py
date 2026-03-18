"""Brain Factory TechDocs MCP server.

Exposes documentation URLs and conversation transcripts as searchable
MCP tools for external agents.

    /opt/homebrew/bin/python3.12 mcp_techdocs.py
"""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

# ── URL index (parsed from generated TECHDOCS_URLS.md) ──────────────

REPO_ROOT = Path(__file__).resolve().parent
DOCS_DIR = REPO_ROOT / "docs"
CONVERSATIONS_DIR = (
    Path.home() / ".claude" / "projects"
    / "-Users-raymondbruni-Cowork-Brain-Factory"
)


def _load_url_index() -> dict[str, list[dict[str, str]]]:
    """Parse docs/TECHDOCS_URLS.md into {section: [{title, url}, ...]}."""
    urls_file = DOCS_DIR / "TECHDOCS_URLS.md"
    if not urls_file.exists():
        return {}

    sections: dict[str, list[dict[str, str]]] = {}
    current = None

    for line in urls_file.read_text().splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current and line.startswith("| ") and "---" not in line:
            parts = [c.strip() for c in line.split("|")[1:-1]]
            if len(parts) == 2:
                title = parts[0]
                m = re.search(r"\[.*?\]\((.*?)\)", parts[1])
                url = m.group(1) if m else parts[1]
                sections[current].append({"title": title, "url": url})

    return sections


# ── Conversation helpers ─────────────────────────────────────────────

def _list_conversations(limit: int = 20) -> list[dict]:
    """List recent conversation files sorted by mtime."""
    if not CONVERSATIONS_DIR.exists():
        return []

    files = sorted(
        CONVERSATIONS_DIR.glob("*.jsonl"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    results = []
    for f in files[:limit]:
        try:
            lines = f.read_text().splitlines()
            events = [json.loads(ln) for ln in lines if ln.strip()]
        except Exception:
            continue
        if events:
            results.append({
                "session_id": f.stem,
                "messages": len(events),
                "first": events[0].get("timestamp", ""),
                "last": events[-1].get("timestamp", ""),
            })
    return results


def _search_conversations(query: str, limit: int = 10) -> list[dict]:
    """Search all conversations for query string, return matching context."""
    if not CONVERSATIONS_DIR.exists():
        return []

    query_lower = query.lower()
    results = []

    files = sorted(
        CONVERSATIONS_DIR.glob("*.jsonl"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    for f in files:
        if len(results) >= limit:
            break
        try:
            lines = f.read_text().splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines):
            if len(results) >= limit:
                break
            if query_lower not in line.lower():
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue

            # Extract text content from various message shapes
            text = ""
            if isinstance(event.get("message"), dict):
                msg = event["message"]
                content = msg.get("content", "")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = " ".join(
                        p.get("text", "")
                        for p in content
                        if isinstance(p, dict) and p.get("type") == "text"
                    )
            elif isinstance(event.get("content"), str):
                text = event["content"]

            if query_lower in text.lower():
                results.append({
                    "session_id": f.stem,
                    "line": i + 1,
                    "role": event.get("message", {}).get("role", event.get("type", "unknown")),
                    "timestamp": event.get("timestamp", ""),
                    "snippet": text[:500],
                })

    return results


# ── Rebuild helper ───────────────────────────────────────────────────

def _rebuild_techdocs() -> dict:
    """Run mkdocs build + deploy to Backstage static dir."""
    result = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build",
         "--site-dir", "/tmp/brain_factory_site", "--quiet"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        return {"status": "error", "stderr": result.stderr[:500]}

    backstage_dir = Path(
        "/Users/raymondbruni/dopejar/node_modules/"
        "@backstage/plugin-techdocs-backend/static/docs/"
        "default/component/brain-factory"
    )
    deployed = False
    if backstage_dir.exists():
        subprocess.run(
            ["cp", "-r", "/tmp/brain_factory_site/.", str(backstage_dir)],
            capture_output=True, timeout=30,
        )
        deployed = True

    return {"status": "ok", "deployed": deployed}


# ── Tool specifications (plain dicts — no mcp dependency) ───────────
# This is the source of truth for tool contracts. The MCP server and
# the Backstage catalog API definition are both derived from this list.

TOOL_SPECS = [
    {
        "name": "list_sections",
        "description": "List all TechDocs nav sections with page counts",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "search_docs",
        "description": "Fuzzy search TechDocs page titles, return matching URLs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to match against page titles",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_section",
        "description": "Get all pages and URLs in a TechDocs section",
        "inputSchema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "Section name (from list_sections)",
                },
            },
            "required": ["section"],
        },
    },
    {
        "name": "list_conversations",
        "description": "List recent Claude Code conversation sessions with timestamps and message counts",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 20)",
                    "default": 20,
                },
            },
        },
    },
    {
        "name": "search_conversations",
        "description": "Search Claude Code conversation content for keywords",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keyword to search for in conversations",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "rebuild_techdocs",
        "description": "Force rebuild TechDocs and deploy to Backstage",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ── MCP server ───────────────────────────────────────────────────────

def _build_server():
    """Build and return the MCP server instance."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool
    except ImportError as exc:
        raise ImportError(
            "Install the MCP package: "
            "/opt/homebrew/bin/python3.12 -m pip install --user "
            "--break-system-packages mcp"
        ) from exc

    server = Server("brain-factory-techdocs")

    tools = [
        Tool(name=s["name"], description=s["description"], inputSchema=s["inputSchema"])
        for s in TOOL_SPECS
    ]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            result = _dispatch(name, arguments)
            return [TextContent(type="text", text=json.dumps(result, default=str))]
        except Exception as exc:
            return [TextContent(type="text", text=json.dumps({"error": str(exc)}))]

    return server, stdio_server


def _dispatch(name: str, arguments: dict):
    """Route tool calls to handler functions."""
    index = _load_url_index()

    if name == "list_sections":
        return {
            section: len(pages)
            for section, pages in index.items()
        }

    if name == "search_docs":
        query = arguments["query"].lower()
        matches = []
        for section, pages in index.items():
            for page in pages:
                if query in page["title"].lower():
                    matches.append({
                        "section": section,
                        "title": page["title"],
                        "url": page["url"],
                    })
        return matches

    if name == "get_section":
        section = arguments["section"]
        # Case-insensitive section lookup
        for sec_name, pages in index.items():
            if sec_name.lower() == section.lower():
                return {"section": sec_name, "pages": pages}
        return {"error": f"Section not found: {section}"}

    if name == "list_conversations":
        limit = arguments.get("limit", 20)
        return _list_conversations(limit)

    if name == "search_conversations":
        query = arguments["query"]
        limit = arguments.get("limit", 10)
        return _search_conversations(query, limit)

    if name == "rebuild_techdocs":
        return _rebuild_techdocs()

    raise ValueError(f"Unknown tool: {name!r}")


async def main() -> None:
    server, stdio_server = _build_server()
    async with stdio_server() as streams:
        await server.run(
            streams[0], streams[1],
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
