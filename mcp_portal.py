"""
Portal MCP Server — exposes Brain Factory portal data as MCP tools.

Agents query this to discover pipelines, conversations, files, and catalog entities.
Humans use the Streamlit portal. Both read the same data.

Usage:
    python3 mcp_portal.py                  # stdio mode (for Claude/Codex MCP config)
    python3 mcp_portal.py --config X.yaml  # custom config for other systems

Protocol: MCP over stdin/stdout (JSON-RPC 2.0)
"""

import json
import sys
import pathlib
import datetime
import subprocess
import yaml

# ── Configuration ─────────────────────────────────────────────────────────────
# Default config for Brain Factory. Override with --config for other systems.

DEFAULT_CONFIG = {
    "system_name": "Brain Factory",
    "repo_root": str(pathlib.Path(__file__).parent),
    "pipeline": {
        "name": "sawmill",
        "runs_pattern": "sawmill/FMWK-*/runs/*/events.jsonl",
        "status_file": "status.json",
        "run_dir_prefix": "FMWK-",
    },
    "conversations": {
        "claude": str(pathlib.Path.home() / ".claude/projects/-Users-raymondbruni-Cowork-Brain-Factory"),
        "codex": str(pathlib.Path.home() / ".codex/sessions"),
        "gemini": str(pathlib.Path.home() / ".gemini/tmp"),
    },
    "catalog_files": [
        str(pathlib.Path.home() / "dopejar/catalog-info.yaml"),
        str(pathlib.Path.home() / "dopejar/platform_sdk/catalog-info.yaml"),
        str(pathlib.Path.home() / "dopejar/examples/org.yaml"),
        "catalog-info.yaml",
    ],
}


def load_config():
    if "--config" in sys.argv:
        idx = sys.argv.index("--config")
        config_path = pathlib.Path(sys.argv[idx + 1])
        return yaml.safe_load(config_path.read_text())
    return DEFAULT_CONFIG


CONFIG = load_config()
ROOT = pathlib.Path(CONFIG["repo_root"])


# ── Tool implementations ──────────────────────────────────────────────────────

def list_pipeline_runs(limit=20):
    """List recent pipeline runs with metadata (no events loaded)."""
    sawmill = ROOT / "sawmill"
    runs = []
    prefix = CONFIG["pipeline"].get("run_dir_prefix", "FMWK-")
    for fw_dir in sorted(sawmill.iterdir(), reverse=True):
        if not fw_dir.is_dir() or not fw_dir.name.startswith(prefix):
            continue
        runs_dir = fw_dir / "runs"
        if not runs_dir.exists():
            continue
        for run_dir in sorted(runs_dir.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue
            status_file = run_dir / "status.json"
            status = {}
            if status_file.exists():
                try:
                    status = json.loads(status_file.read_text())
                except Exception:
                    pass
            events_file = run_dir / "events.jsonl"
            event_count = 0
            first_ts = ""
            if events_file.exists():
                lines = events_file.read_text().splitlines()
                event_count = len([l for l in lines if l.strip()])
                if lines:
                    try:
                        first_ts = json.loads(lines[0]).get("timestamp", "")
                    except Exception:
                        pass
            runs.append({
                "run_id": run_dir.name,
                "framework": fw_dir.name,
                "state": status.get("state", "unknown"),
                "event_count": event_count,
                "timestamp": first_ts,
                "current_turn": status.get("current_turn", ""),
                "current_role": status.get("current_role", ""),
            })
    runs.sort(key=lambda r: r.get("timestamp", "0"), reverse=True)
    return runs[:limit]


def get_run_events(framework, run_id):
    """Get all events for a specific pipeline run."""
    events_file = ROOT / "sawmill" / framework / "runs" / run_id / "events.jsonl"
    if not events_file.exists():
        return {"error": f"Run not found: {framework}/{run_id}"}
    events = []
    for line in events_file.read_text().splitlines():
        if line.strip():
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    return events


def get_run_trace(framework, run_id):
    """Get events organized as a parent→child trace tree."""
    events = get_run_events(framework, run_id)
    if isinstance(events, dict) and "error" in events:
        return events
    by_id = {}
    children = {}
    roots = []
    for ev in events:
        eid = ev.get("event_id", "")
        pid = ev.get("causal_parent_event_id")
        by_id[eid] = ev
        if pid and pid in by_id:
            children.setdefault(pid, []).append(eid)
        else:
            roots.append(eid)

    def build_node(eid):
        ev = by_id.get(eid, {})
        node = {
            "event_id": eid,
            "event_type": ev.get("event_type"),
            "role": ev.get("role"),
            "turn": ev.get("turn"),
            "outcome": ev.get("outcome"),
            "summary": ev.get("summary"),
            "timestamp": ev.get("timestamp"),
            "evidence_refs": ev.get("evidence_refs", []),
            "contract_refs": ev.get("contract_refs", []),
            "children": [build_node(cid) for cid in children.get(eid, [])],
        }
        return node

    return [build_node(r) for r in roots]


def list_conversations(cli=None, limit=30):
    """List recent agent conversations across CLIs."""
    sessions = []
    conv_config = CONFIG.get("conversations", {})

    for cli_name, base_path in conv_config.items():
        if cli and cli != cli_name:
            continue
        base = pathlib.Path(base_path)
        if not base.exists():
            continue

        if cli_name == "claude":
            for f in sorted(base.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
                preview, ts = "", ""
                for line in f.read_text().splitlines()[:20]:
                    try:
                        rec = json.loads(line)
                        if rec.get("type") == "user":
                            content = rec.get("message", {}).get("content", "")
                            if isinstance(content, str):
                                preview = content[:80]
                            ts = rec.get("timestamp", "")
                            break
                    except Exception:
                        pass
                sessions.append({"cli": "claude", "session": f.stem[:12], "timestamp": ts,
                                  "preview": preview, "path": str(f)})

        elif cli_name == "codex":
            for f in sorted(base.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
                ts, cwd = "", ""
                for line in f.read_text().splitlines()[:10]:
                    try:
                        rec = json.loads(line)
                        if rec.get("type") == "session_meta":
                            ts = rec.get("payload", {}).get("timestamp", "")
                            cwd = rec.get("payload", {}).get("cwd", "")
                            break
                    except Exception:
                        pass
                sessions.append({"cli": "codex", "session": f.stem[:20], "timestamp": ts,
                                  "preview": cwd, "path": str(f)})

        elif cli_name == "gemini":
            for f in sorted(base.rglob("chats/session-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
                preview, ts = "", ""
                try:
                    data = json.loads(f.read_text())
                    ts = data.get("startTime", "")
                    for msg in data.get("messages", []):
                        if msg.get("type") == "user":
                            for b in msg.get("content", []):
                                if b.get("text"):
                                    preview = b["text"][:80]
                                    break
                            if preview:
                                break
                except Exception:
                    pass
                sessions.append({"cli": "gemini", "session": f.stem[:20], "timestamp": ts,
                                  "preview": preview, "path": str(f)})

    sessions.sort(key=lambda s: s.get("timestamp", "0"), reverse=True)
    return sessions[:limit]


def get_conversation(path):
    """Get the full content of a conversation transcript."""
    p = pathlib.Path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if p.suffix == ".jsonl":
        records = []
        for line in p.read_text().splitlines():
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
        return records
    elif p.suffix == ".json":
        return json.loads(p.read_text())
    return {"error": "Unsupported format"}


def list_catalog_entities():
    """List all Backstage catalog entities."""
    entities = []
    for cat_path in CONFIG.get("catalog_files", []):
        p = pathlib.Path(cat_path) if pathlib.Path(cat_path).is_absolute() else ROOT / cat_path
        if not p.exists():
            continue
        try:
            for doc in yaml.safe_load_all(p.read_text()):
                if doc and isinstance(doc, dict) and "kind" in doc:
                    entities.append({
                        "kind": doc.get("kind"),
                        "name": doc.get("metadata", {}).get("name"),
                        "description": doc.get("metadata", {}).get("description", "").strip(),
                        "type": doc.get("spec", {}).get("type"),
                        "owner": doc.get("spec", {}).get("owner"),
                        "lifecycle": doc.get("spec", {}).get("lifecycle"),
                        "system": doc.get("spec", {}).get("system"),
                        "tags": doc.get("metadata", {}).get("tags", []),
                        "provides_apis": doc.get("spec", {}).get("providesApis", []),
                        "depends_on": doc.get("spec", {}).get("dependsOn", []),
                        "source": str(p),
                    })
        except Exception:
            pass
    return entities


def get_api_spec(api_name):
    """Get the full API specification for a catalog API entity."""
    for cat_path in CONFIG.get("catalog_files", []):
        p = pathlib.Path(cat_path) if pathlib.Path(cat_path).is_absolute() else ROOT / cat_path
        if not p.exists():
            continue
        try:
            for doc in yaml.safe_load_all(p.read_text()):
                if doc and doc.get("kind") == "API" and doc.get("metadata", {}).get("name") == api_name:
                    defn = doc.get("spec", {}).get("definition")
                    if isinstance(defn, str):
                        return {"name": api_name, "type": doc["spec"].get("type"), "definition": defn}
                    if isinstance(defn, dict) and "$text" in defn:
                        ref_path = p.parent / defn["$text"]
                        if ref_path.exists():
                            return {"name": api_name, "type": doc["spec"].get("type"),
                                    "definition": ref_path.read_text()}
                    return {"name": api_name, "type": doc["spec"].get("type"), "definition": str(defn)}
        except Exception:
            pass
    return {"error": f"API not found: {api_name}"}


def browse_files(rel_path=""):
    """Browse directory contents relative to repo root."""
    target = ROOT / rel_path if rel_path else ROOT
    if not target.exists():
        return {"error": f"Path not found: {rel_path}"}
    if target.is_file():
        return {"type": "file", "path": rel_path, "size": target.stat().st_size,
                "modified": datetime.datetime.fromtimestamp(target.stat().st_mtime).isoformat()}
    items = []
    for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        items.append({
            "name": item.name,
            "type": "dir" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
            "modified": datetime.datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
        })
    return {"path": rel_path or ".", "items": items}


def read_file(rel_path):
    """Read a file's contents."""
    target = ROOT / rel_path
    if not target.exists():
        return {"error": f"Not found: {rel_path}"}
    if not target.is_file():
        return {"error": f"Not a file: {rel_path}"}
    try:
        return {"path": rel_path, "content": target.read_text(encoding="utf-8"),
                "size": target.stat().st_size,
                "modified": datetime.datetime.fromtimestamp(target.stat().st_mtime).isoformat()}
    except Exception as e:
        return {"error": str(e)}


def get_recent_commits(limit=20):
    """Get recent git commits."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{limit}", "--format=%H\t%aI\t%an\t%s"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=10)
        commits = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t", 3)
            if len(parts) == 4:
                commits.append({"hash": parts[0], "date": parts[1], "author": parts[2], "subject": parts[3]})
        return commits
    except Exception as e:
        return {"error": str(e)}


def get_working_changes():
    """Get uncommitted changes in the working tree."""
    try:
        result = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                                capture_output=True, text=True, timeout=10)
        changes = []
        for line in result.stdout.strip().splitlines():
            if len(line) >= 4:
                changes.append({"status": line[:2].strip(), "path": line[3:]})
        return changes
    except Exception as e:
        return {"error": str(e)}


# ── Workspace (imports from workspace.py — single source of logic) ────────────
import workspace as ws


def _brain():
    from shell.helpers import brain

    return brain


# ── MCP Protocol (JSON-RPC over stdio) ────────────────────────────────────────

TOOLS = {
    "post_to_workspace": {
        "description": "Post a plan, result, review, prompt, or handoff to the shared workspace. Use reply_to to continue an existing conversation thread.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["plan", "results", "review", "prompt", "handoff", "question", "context"],
                         "description": "What kind of item this is"},
                "to": {"type": "string", "description": "Who should pick this up"},
                "summary": {"type": "string", "description": "One-line summary of the item"},
                "content": {"type": "string", "description": "Full markdown content"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
                "reply_to": {"type": "string", "description": "ID of the item you are responding to (threads the conversation)"},
            },
            "required": ["type", "to", "summary", "content"],
        },
        "handler": lambda args: ws.create_item(
            item_type=args["type"], from_cli=args.get("from_cli", "agent"),
            to=args["to"], summary=args["summary"], content=args["content"],
            tags=args.get("tags", []), from_session=args.get("from_session", ""),
            from_agent=args.get("from_agent", ""), reply_to=args.get("reply_to", "")),
    },
    "get_workspace_items": {
        "description": "List workspace items. Filter by status (pending/approved/complete), recipient, source CLI, or type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["draft", "pending", "approved", "rejected", "in_progress", "complete"]},
                "to": {"type": "string", "description": "Filter by recipient"},
                "from_cli": {"type": "string", "description": "Filter by source CLI"},
                "type": {"type": "string", "description": "Filter by item type"},
            },
        },
        "handler": lambda args: ws.list_items(
            status=args.get("status"), to=args.get("to"),
            from_cli=args.get("from_cli"), item_type=args.get("type")),
    },
    "get_workspace_item": {
        "description": "Get a workspace item by ID, including full content.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "Item ID"}},
            "required": ["id"],
        },
        "handler": lambda args: ws.get_item(args["id"]),
    },
    "update_workspace_status": {
        "description": "Update a workspace item's status. Agents can set 'read'. Only human can set 'complete'. Agents MUST respond after reading — no silent reads.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "status": {"type": "string", "enum": ["sent", "read", "complete"], "description": "Agents: use 'read'. Only human can use 'complete'."},
            },
            "required": ["id", "status"],
        },
        "handler": lambda args: ws.update_status(args["id"], args["status"], actor=args.get("actor", "agent")),
    },
    "comment_on_workspace_item": {
        "description": "Add a comment to a workspace item.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "text": {"type": "string", "description": "Comment text"},
            },
            "required": ["id", "text"],
        },
        "handler": lambda args: ws.add_comment(args["id"], args.get("from_cli", "agent"), args["text"]),
    },
    "register_agent": {
        "description": "Register this agent's identity so it appears in the workspace routing and is discoverable by other agents. Call this at the start of a session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Unique agent name (e.g. claude-portal-builder, codex-techdocs-cleanup)"},
                "cli": {"type": "string", "description": "Which CLI this agent runs on (claude, codex, gemini)"},
                "description": {"type": "string", "description": "What this agent is currently working on"},
                "capabilities": {"type": "array", "items": {"type": "string"}, "description": "What this agent can do (e.g. code-review, planning, execution)"},
            },
            "required": ["name", "cli", "description"],
        },
        "handler": lambda args: ws.register_agent(
            args["name"], args["cli"], args.get("description", ""),
            args.get("capabilities", [])),
    },
    "list_agents": {
        "description": "List all registered agents with their CLI, description, and capabilities.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda args: ws.list_agents(),
    },
    "capture_thought": {
        "description": "Capture a thought into the brain — DoPeJarMo's shared semantic memory. Anything stored here is retrievable by meaning from any agent session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Thought content to store"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
                "source": {"type": "string", "description": "Optional source label"},
            },
            "required": ["content"],
        },
        "handler": lambda args: _brain().capture(
            content=args["content"],
            tags=args.get("tags", []),
            source=args.get("source", ""),
        ),
    },
    "search_thoughts": {
        "description": "Search the brain by meaning. Use this before starting work to check what's already known.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Semantic search query"},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
                "tag": {"type": "string", "description": "Optional tag filter"},
            },
            "required": ["query"],
        },
        "handler": lambda args: _brain().search(
            query=args["query"],
            limit=args.get("limit", 10),
            tag=args.get("tag", ""),
        ),
    },
    "list_thoughts": {
        "description": "List recent thoughts stored in the brain, optionally filtered by tag.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results", "default": 50},
                "tag": {"type": "string", "description": "Optional tag filter"},
            },
        },
        "handler": lambda args: _brain().list_recent(
            limit=args.get("limit", 50),
            tag=args.get("tag", ""),
        ),
    },
    "thought_stats": {
        "description": "Get summary stats for the brain, including total thoughts and tag counts.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda args: _brain().stats(),
    },
    "route_workspace_item": {
        "description": "Route a workspace item to a different recipient (e.g. send to gemini for review before codex executes).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "to": {"type": "string", "description": "New recipient (claude, codex, gemini, human, any)"},
            },
            "required": ["id", "to"],
        },
        "handler": lambda args: ws.route_item(args["id"], args["to"], actor=args.get("actor", "agent")),
    },
    "list_pipeline_runs": {
        "description": "List recent pipeline/process runs with status, event count, and timestamps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max runs to return", "default": 20}
            },
        },
        "handler": lambda args: list_pipeline_runs(args.get("limit", 20)),
    },
    "get_run_events": {
        "description": "Get all execution events for a specific pipeline run.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "framework": {"type": "string", "description": "Framework ID (e.g. FMWK-001-ledger)"},
                "run_id": {"type": "string", "description": "Run ID"},
            },
            "required": ["framework", "run_id"],
        },
        "handler": lambda args: get_run_events(args["framework"], args["run_id"]),
    },
    "get_run_trace": {
        "description": "Get execution events as a parent→child trace tree for debugging.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "framework": {"type": "string"},
                "run_id": {"type": "string"},
            },
            "required": ["framework", "run_id"],
        },
        "handler": lambda args: get_run_trace(args["framework"], args["run_id"]),
    },
    "list_conversations": {
        "description": "List recent agent conversations across CLIs (Claude, Codex, Gemini).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cli": {"type": "string", "description": "Filter by CLI name", "enum": ["claude", "codex", "gemini"]},
                "limit": {"type": "integer", "default": 30},
            },
        },
        "handler": lambda args: list_conversations(args.get("cli"), args.get("limit", 30)),
    },
    "get_conversation": {
        "description": "Get the full transcript of a conversation by file path.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Full path to transcript file"}},
            "required": ["path"],
        },
        "handler": lambda args: get_conversation(args["path"]),
    },
    "list_catalog_entities": {
        "description": "List all system catalog entities (components, APIs, resources, users).",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda args: list_catalog_entities(),
    },
    "get_api_spec": {
        "description": "Get the full API specification for a named API from the catalog.",
        "inputSchema": {
            "type": "object",
            "properties": {"api_name": {"type": "string", "description": "API entity name"}},
            "required": ["api_name"],
        },
        "handler": lambda args: get_api_spec(args["api_name"]),
    },
    "browse_files": {
        "description": "Browse directory contents relative to repo root.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative path (empty for root)", "default": ""}},
        },
        "handler": lambda args: browse_files(args.get("path", "")),
    },
    "read_file": {
        "description": "Read a file's contents by relative path.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative path to file"}},
            "required": ["path"],
        },
        "handler": lambda args: read_file(args["path"]),
    },
    "get_recent_commits": {
        "description": "Get recent git commits with hash, date, author, and subject.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 20}},
        },
        "handler": lambda args: get_recent_commits(args.get("limit", 20)),
    },
    "get_working_changes": {
        "description": "Get uncommitted changes in the working tree.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda args: get_working_changes(),
    },
}


def handle_request(request):
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": req_id, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": CONFIG["system_name"] + " Portal MCP", "version": "1.0.0"},
        }}
    elif method == "notifications/initialized":
        return None  # no response for notifications
    elif method == "tools/list":
        tools_list = []
        for name, spec in TOOLS.items():
            tools_list.append({
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            })
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        if tool_name not in TOOLS:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}
        try:
            result = TOOLS[tool_name]["handler"](arguments)
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
            }}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}
    else:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


# ── Kit files (served over HTTP for remote systems) ───────────────────────────

KIT_FILES = ["PORTAL_KIT.md", "portal.py", "mcp_portal.py", "workspace.py", "catalog-info.yaml", "portal_config.template.yaml"]


def main_stdio():
    """Run MCP server over stdin/stdout (for local Claude/Codex MCP config)."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            sys.stderr.write(f"Invalid JSON: {line}\n")
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")


def main_http(port=8502):
    """Run MCP server over HTTP (for remote agents with network-only access).

    Endpoints:
        GET  /                     → server info + tool list
        GET  /kit                  → list available kit files
        GET  /kit/<filename>       → download a kit file (raw text)
        POST /mcp                  → JSON-RPC MCP endpoint (same as stdio)
        POST /tools/<tool_name>    → call a tool directly with JSON body
    """
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, content_type="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.wfile.write(body)

        def do_OPTIONS(self):
            self._send(200, "")

        def _get_agent_token(self, args):
            """Read agent token from request body first, then Bearer auth."""
            token = args.get("agent_token", "")
            if token:
                return token
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                return auth[7:]
            return ""

        def do_GET(self):
            path = self.path.rstrip("/")

            if path == "" or path == "/":
                # Server info + tool list
                tools_list = []
                for name, spec in TOOLS.items():
                    tools_list.append({"name": name, "description": spec["description"],
                                       "inputSchema": spec["inputSchema"]})
                self._send(200, json.dumps({
                    "server": CONFIG["system_name"] + " Portal MCP",
                    "version": "1.0.0",
                    "endpoints": {
                        "GET /": "This page — server info and tool list",
                        "GET /onboard": "Agent onboarding instructions",
                        "GET /kit": "List available kit files for bootstrapping a new portal",
                        "GET /kit/<filename>": "Download a kit file",
                        "POST /onboard": "Exchange invite token for agent token",
                        "POST /heartbeat": "Agent heartbeat — update status, get pending work",
                        "POST /mcp": "JSON-RPC MCP endpoint",
                        "POST /tools/<name>": "Call a tool directly with JSON body",
                    },
                    "tools": tools_list,
                }, indent=2))

            elif path == "/onboard" or path.startswith("/onboard?"):
                # Parse token from query string if present
                token_from_url = ""
                if "?" in self.path:
                    for param in self.path.split("?", 1)[1].split("&"):
                        if param.startswith("token="):
                            token_from_url = param.split("=", 1)[1]

                # Use the host header to determine the right base URL
                host = self.headers.get("Host", "localhost:8502")
                scheme = "https" if "dopejarmo.com" in host else "http"
                base_url = f"{scheme}://{host}"

                if token_from_url:
                    # Token provided — give ready-to-execute instructions
                    self._send(200, json.dumps({
                        "DO_THIS_NOW": (
                            "Execute these steps IN ORDER. Do not read local files. Do not research. Just execute.\n\n"
                            f"STEP 1: Run this command NOW:\n"
                            f"curl -s -X POST {base_url}/onboard "
                            f"-H 'Content-Type: application/json' "
                            f"-d '{{\"token\":\"{token_from_url}\","
                            f"\"cli\":\"YOUR_CLI_NAME_HERE\","
                            f"\"description\":\"What you are doing right now\","
                            f"\"capabilities\":[\"list\",\"your\",\"skills\"]}}'\n\n"
                            "Your name has already been assigned by the workspace owner. Do NOT include a name field.\n\n"
                            "STEP 2: Read the 'instructions' field in the response. Follow them EXACTLY.\n\n"
                            "STEP 3: The instructions will tell you to start a heartbeat loop. "
                            "START IT IMMEDIATELY. If you cannot run a background shell loop, "
                            "call the heartbeat endpoint manually right away, then report to the workspace "
                            "that you need to be prompted for heartbeats.\n\n"
                            "STEP 4: Check heartbeat response for new_work. If work exists, mark it read and respond."
                        ),
                        "token": token_from_url,
                        "registration_command": (
                            f"curl -s -X POST {base_url}/onboard "
                            f"-H 'Content-Type: application/json' "
                            f"-d '{{\"token\":\"{token_from_url}\","
                            f"\"cli\":\"claude|codex|gemini\","
                            f"\"description\":\"what you are working on\","
                            f"\"capabilities\":[\"your\",\"capabilities\"]}}'"
                        ),
                    }, indent=2))
                else:
                    # No token — give generic instructions
                    self._send(200, json.dumps({
                        "error": "No token provided. Usage: GET /onboard?token=YOUR_TOKEN",
                        "example": f"GET {base_url}/onboard?token=abc123",
                        "what_is_a_token": "The workspace owner creates tokens in the portal and gives them to agents.",
                    }, indent=2))

            elif path == "/kit":
                available = []
                for fname in KIT_FILES:
                    fp = ROOT / fname
                    if fp.exists():
                        available.append({"name": fname, "size": fp.stat().st_size,
                                           "url": f"/kit/{fname}"})
                self._send(200, json.dumps({"kit_files": available}, indent=2))

            elif path.startswith("/kit/"):
                fname = path[5:]
                if fname not in KIT_FILES:
                    self._send(404, json.dumps({"error": f"Not a kit file: {fname}"}))
                    return
                fp = ROOT / fname
                if not fp.exists():
                    self._send(404, json.dumps({"error": f"File not found: {fname}"}))
                    return
                self._send(200, fp.read_text(encoding="utf-8"), content_type="text/plain; charset=utf-8")

            else:
                self._send(404, json.dumps({"error": f"Unknown path: {path}"}))

        def do_POST(self):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8") if content_len else "{}"
            path = self.path.rstrip("/")

            if path == "/onboard":
                try:
                    args = json.loads(body)
                    host = self.headers.get("Host", "localhost:8502")
                    scheme = "https" if "dopejarmo.com" in host else "http"
                    post_base_url = f"{scheme}://{host}"
                    result = ws.onboard_agent(
                        token=args.get("token", ""),
                        name=args.get("name", ""),
                        cli=args.get("cli", ""),
                        description=args.get("description", ""),
                        capabilities=args.get("capabilities", []),
                        base_url=post_base_url,
                    )
                    if "error" in result:
                        self._send(401, json.dumps(result))
                    else:
                        self._send(200, json.dumps(result, indent=2))
                except Exception as e:
                    self._send(500, json.dumps({"error": str(e)}))

            elif path == "/heartbeat":
                try:
                    args = json.loads(body) if body.strip() else {}
                    token = self._get_agent_token(args)
                    if not token:
                        self._send(401, json.dumps({"error": "Missing agent_token"}))
                        return
                    result = ws.heartbeat(token)
                    if "error" in result:
                        self._send(401, json.dumps(result))
                    else:
                        self._send(200, json.dumps(result, indent=2, default=str))
                except Exception as e:
                    self._send(500, json.dumps({"error": str(e)}))

            elif path == "/mcp":
                # Full JSON-RPC MCP endpoint
                try:
                    request = json.loads(body)
                    response = handle_request(request)
                    if response:
                        self._send(200, json.dumps(response))
                    else:
                        self._send(204, "")
                except Exception as e:
                    self._send(500, json.dumps({"error": str(e)}))

            elif path.startswith("/tools/"):
                # Direct tool call: POST /tools/list_pipeline_runs {"limit": 5}
                tool_name = path[7:]
                if tool_name not in TOOLS:
                    self._send(404, json.dumps({"error": f"Unknown tool: {tool_name}"}))
                    return
                try:
                    args = json.loads(body) if body.strip() else {}
                    token = self._get_agent_token(args)
                    if not token:
                        self._send(401, json.dumps({"error": "Missing agent_token"}))
                        return
                    agent = ws.validate_token(token)
                    if not agent:
                        self._send(401, json.dumps({"error": "Invalid or revoked token"}))
                        return
                    # Inject resolved identity into args so handlers know who's calling
                    args["actor"] = agent.get("name", "agent")
                    args["from_cli"] = agent.get("cli", "agent")
                    args["from_agent"] = agent.get("name", "agent")
                    result = TOOLS[tool_name]["handler"](args)
                    self._send(200, json.dumps(result, indent=2, default=str))
                except Exception as e:
                    self._send(500, json.dumps({"error": str(e)}))

            else:
                self._send(404, json.dumps({"error": f"Unknown path: {path}"}))

        def log_message(self, format, *args):
            sys.stderr.write(f"[portal-mcp] {args[0]} {args[1]} {args[2]}\n")

    server = HTTPServer(("0.0.0.0", port), Handler)
    sys.stderr.write(f"Portal MCP HTTP server running on http://0.0.0.0:{port}\n")
    sys.stderr.write(f"  Tools:  POST http://localhost:{port}/tools/<name>\n")
    sys.stderr.write(f"  Kit:    GET  http://localhost:{port}/kit\n")
    sys.stderr.write(f"  MCP:    POST http://localhost:{port}/mcp\n")
    server.serve_forever()


def main():
    if "--http" in sys.argv:
        port = 8502
        if "--port" in sys.argv:
            port = int(sys.argv[sys.argv.index("--port") + 1])
        main_http(port)
    else:
        main_stdio()


if __name__ == "__main__":
    main()
