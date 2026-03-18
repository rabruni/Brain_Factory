## Brain Factory TechDocs MCP Tools

**Run:** `/opt/homebrew/bin/python3.12 mcp_techdocs.py`

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_sections` | List all TechDocs nav sections with page counts | *(none)* |
| `search_docs` | Fuzzy search TechDocs page titles, return matching URLs | `query` (string, **required**) — Search query to match against page titles |
| `get_section` | Get all pages and URLs in a TechDocs section | `section` (string, **required**) — Section name (from list_sections) |
| `list_conversations` | List recent Claude Code conversation sessions with timestamps and message counts | `limit` (integer, default: `20`) — Max results (default 20) |
| `search_conversations` | Search Claude Code conversation content for keywords | `query` (string, **required**) — Keyword to search for in conversations; `limit` (integer, default: `10`) — Max results (default 10) |
| `rebuild_techdocs` | Force rebuild TechDocs and deploy to Backstage | *(none)* |
