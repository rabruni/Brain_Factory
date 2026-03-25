"""
Workspace — shared read/write surface for cross-agent communication.

One module, two consumers:
  - portal.py imports this for the UI
  - mcp_portal.py imports this for the MCP tools

Primary storage now lives in SQLite under workspace/workspace.db.
Legacy YAML / JSON files are imported on first use for compatibility.
"""

import datetime
import json
import os
import pathlib
import re
import sqlite3
import uuid


WORKSPACE_DIR = pathlib.Path(__file__).parent / "workspace"
_override = os.environ.get("WORKSPACE_DIR_OVERRIDE", "")
if _override:
    WORKSPACE_DIR = pathlib.Path(_override)
AUDIT_LOG = WORKSPACE_DIR / "audit.jsonl"
TOKENS_FILE = WORKSPACE_DIR / "tokens.json"
AGENT_REGISTRY = WORKSPACE_DIR / "agents.yaml"
DB_FILE = WORKSPACE_DIR / "workspace.db"

VALID_TYPES = {"plan", "results", "review", "prompt", "handoff", "question", "context"}
VALID_STATUSES = {"sent", "read", "complete"}
VALID_CLIS = {"claude", "codex", "gemini", "human", "any"}
DEFAULT_MAX_DEPTH = 2
VALID_AGENT_TYPES = {"worker", "interactive", "sawmill-role", "human"}
VALID_CONTEXT_MODES = {"full_thread", "last_n", "task_only"}
VALID_PROVIDERS = {"codex-cli", "ollama", "anthropic", "openai", "google"}
VALID_TOOLS = {"read_file", "list_directory", "search_files"}
RESERVED_AGENT_NAMES = {"builder", "reviewer", "evaluator", "spec-agent", "holdout-agent", "orchestrator", "auditor"}
AGENT_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
PROVIDER_TO_CLI = {
    "anthropic": "claude",
    "openai": "openai",
    "ollama": "local",
    "google": "gemini",
    "codex-cli": "codex",
}


def _utc_now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_dir():
    WORKSPACE_DIR.mkdir(exist_ok=True)


def _parse_item_file(path):
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            import yaml
            meta = yaml.safe_load(parts[1]) or {}
            content = parts[2].strip()
        else:
            meta = {}
            content = text
    else:
        meta = {}
        content = text
    meta["content"] = content
    meta["_path"] = str(path)
    meta["_filename"] = path.name
    return meta


def _split_recipients(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _join_recipients(value):
    return ",".join(_split_recipients(value))


def _normalize_item(meta):
    item = dict(meta)
    item["tags"] = item.get("tags") or []
    item["comments"] = item.get("comments") or []
    item["_path"] = item.get("_path", str(WORKSPACE_DIR / f"{item.get('id', '')}.yaml"))
    item["_filename"] = item.get("_filename", f"{item.get('id', '')}.yaml")
    return item


def _connect():
    _ensure_dir()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _column_names(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _ensure_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            from_cli TEXT NOT NULL,
            from_agent TEXT NOT NULL,
            from_session TEXT NOT NULL DEFAULT '',
            to_recipients TEXT NOT NULL,
            reply_to TEXT NOT NULL DEFAULT '',
            thread_id TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            approved_at TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL,
            tags_json TEXT NOT NULL DEFAULT '[]',
            comments_json TEXT NOT NULL DEFAULT '[]',
            content TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS audit_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event TEXT NOT NULL,
            item_id TEXT NOT NULL,
            actor TEXT NOT NULL,
            detail TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agents (
            name TEXT PRIMARY KEY,
            cli TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            capabilities_json TEXT NOT NULL DEFAULT '[]',
            registered_at TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_tokens (
            token TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            label TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            name TEXT NOT NULL DEFAULT '',
            cli TEXT NOT NULL DEFAULT '',
            registered_at TEXT NOT NULL DEFAULT '',
            last_seen TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS thoughts (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            tags_json TEXT NOT NULL DEFAULT '[]',
            source TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        """
    )
    columns = _column_names(conn, "items")
    migrations = [
        ("claimed_by", "ALTER TABLE items ADD COLUMN claimed_by TEXT NOT NULL DEFAULT ''"),
        ("claimed_at", "ALTER TABLE items ADD COLUMN claimed_at TEXT NOT NULL DEFAULT ''"),
        ("lease_expires_at", "ALTER TABLE items ADD COLUMN lease_expires_at TEXT NOT NULL DEFAULT ''"),
        ("retry_count", "ALTER TABLE items ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0"),
        ("max_depth", f"ALTER TABLE items ADD COLUMN max_depth INTEGER NOT NULL DEFAULT {DEFAULT_MAX_DEPTH}"),
        ("depth", "ALTER TABLE items ADD COLUMN depth INTEGER NOT NULL DEFAULT 0"),
        ("work_root_id", "ALTER TABLE items ADD COLUMN work_root_id TEXT NOT NULL DEFAULT ''"),
        ("work_parent_id", "ALTER TABLE items ADD COLUMN work_parent_id TEXT NOT NULL DEFAULT ''"),
        ("execution_depth", "ALTER TABLE items ADD COLUMN execution_depth INTEGER NOT NULL DEFAULT 0"),
        ("last_error", "ALTER TABLE items ADD COLUMN last_error TEXT NOT NULL DEFAULT ''"),
        ("last_run_at", "ALTER TABLE items ADD COLUMN last_run_at TEXT NOT NULL DEFAULT ''"),
        ("last_exit_code", "ALTER TABLE items ADD COLUMN last_exit_code INTEGER"),
        ("max_retries", "ALTER TABLE items ADD COLUMN max_retries INTEGER NOT NULL DEFAULT 0"),
    ]
    for column_name, statement in migrations:
        if column_name not in columns:
            conn.execute(statement)
    agent_columns = _column_names(conn, "agents")
    agent_migrations = [
        ("provider", "ALTER TABLE agents ADD COLUMN provider TEXT NOT NULL DEFAULT ''"),
        ("model", "ALTER TABLE agents ADD COLUMN model TEXT NOT NULL DEFAULT ''"),
        ("api_base", "ALTER TABLE agents ADD COLUMN api_base TEXT NOT NULL DEFAULT ''"),
        ("credentials_ref", "ALTER TABLE agents ADD COLUMN credentials_ref TEXT NOT NULL DEFAULT ''"),
        ("instructions", "ALTER TABLE agents ADD COLUMN instructions TEXT NOT NULL DEFAULT ''"),
        ("task_types_json", "ALTER TABLE agents ADD COLUMN task_types_json TEXT NOT NULL DEFAULT '[]'"),
        ("tools_json", "ALTER TABLE agents ADD COLUMN tools_json TEXT NOT NULL DEFAULT '[]'"),
        ("context_mode", "ALTER TABLE agents ADD COLUMN context_mode TEXT NOT NULL DEFAULT 'full_thread'"),
        ("context_n", "ALTER TABLE agents ADD COLUMN context_n INTEGER NOT NULL DEFAULT 0"),
        ("context_budget", "ALTER TABLE agents ADD COLUMN context_budget INTEGER NOT NULL DEFAULT 8000"),
        ("max_output_tokens", "ALTER TABLE agents ADD COLUMN max_output_tokens INTEGER NOT NULL DEFAULT 4000"),
        ("timeout", "ALTER TABLE agents ADD COLUMN timeout INTEGER NOT NULL DEFAULT 180"),
        ("sandbox", "ALTER TABLE agents ADD COLUMN sandbox TEXT NOT NULL DEFAULT 'read-only'"),
        ("max_retries", "ALTER TABLE agents ADD COLUMN max_retries INTEGER NOT NULL DEFAULT 2"),
        ("agent_type", "ALTER TABLE agents ADD COLUMN agent_type TEXT NOT NULL DEFAULT 'worker'"),
        ("enabled", "ALTER TABLE agents ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1"),
    ]
    for column_name, statement in agent_migrations:
        if column_name not in agent_columns:
            conn.execute(statement)
    conn.commit()


def _row_to_item(row):
    if row is None:
        return None
    item = {
        "id": row["id"],
        "type": row["type"],
        "from_cli": row["from_cli"],
        "from_agent": row["from_agent"],
        "from_session": row["from_session"],
        "to": row["to_recipients"],
        "reply_to": row["reply_to"],
        "thread_id": row["thread_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "approved_at": row["approved_at"],
        "summary": row["summary"],
        "tags": json.loads(row["tags_json"] or "[]"),
        "comments": json.loads(row["comments_json"] or "[]"),
        "content": row["content"],
        "claimed_by": row["claimed_by"],
        "claimed_at": row["claimed_at"],
        "lease_expires_at": row["lease_expires_at"],
        "retry_count": row["retry_count"],
        "max_depth": row["max_depth"],
        "depth": row["depth"],
        "work_root_id": row["work_root_id"],
        "work_parent_id": row["work_parent_id"],
        "execution_depth": row["execution_depth"],
        "last_error": row["last_error"],
        "last_run_at": row["last_run_at"],
        "last_exit_code": row["last_exit_code"],
        "max_retries": row["max_retries"],
        "_path": str(WORKSPACE_DIR / f"{row['id']}.yaml"),
        "_filename": f"{row['id']}.yaml",
    }
    return item


def _audit(event_type, item_id, actor="system", detail=""):
    timestamp = _utc_now()
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO audit_entries(timestamp, event, item_id, actor, detail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (timestamp, event_type, item_id, actor, detail),
        )
        conn.commit()
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "timestamp": timestamp,
            "event": event_type,
            "item_id": item_id,
            "actor": actor,
            "detail": detail,
        }) + "\n")


def _normalize_bool(value):
    return 1 if bool(value) else 0


def _row_to_agent(row):
    if row is None:
        return None
    return {
        "name": row["name"],
        "cli": row["cli"],
        "description": row["description"],
        "capabilities": json.loads(row["capabilities_json"] or "[]"),
        "registered_at": row["registered_at"],
        "last_seen": row["last_seen"],
        "provider": row["provider"],
        "model": row["model"],
        "api_base": row["api_base"],
        "credentials_ref": row["credentials_ref"],
        "instructions": row["instructions"],
        "task_types": json.loads(row["task_types_json"] or "[]"),
        "tools": json.loads(row["tools_json"] or "[]"),
        "context_mode": row["context_mode"],
        "context_n": row["context_n"],
        "context_budget": row["context_budget"],
        "max_output_tokens": row["max_output_tokens"],
        "timeout": row["timeout"],
        "sandbox": row["sandbox"],
        "max_retries": row["max_retries"],
        "agent_type": row["agent_type"],
        "enabled": bool(row["enabled"]),
    }


def _row_to_thought(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "content": row["content"],
        "tags": json.loads(row["tags_json"] or "[]"),
        "source": row["source"],
        "created_at": row["created_at"],
    }


def _validate_agent_name(name):
    if not AGENT_NAME_RE.match(name or ""):
        raise ValueError("Agent name must match ^[a-z][a-z0-9-]{1,63}$")
    if name in RESERVED_AGENT_NAMES:
        raise ValueError(f"Reserved agent name: {name}")


def _validate_agent_config(*, name, provider, model, instructions, task_types, tools, context_mode, context_n, timeout, max_retries, agent_type, credentials_ref):
    _validate_agent_name(name)
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    if not str(model or "").strip():
        raise ValueError("Agent model is required")
    if not str(instructions or "").strip():
        raise ValueError("Agent instructions are required")
    if agent_type not in VALID_AGENT_TYPES:
        raise ValueError(f"Invalid agent_type: {agent_type}")
    if context_mode not in VALID_CONTEXT_MODES:
        raise ValueError(f"Invalid context_mode: {context_mode}")
    if agent_type == "interactive":
        task_types = []
        if not isinstance(tools, list):
            raise ValueError("tools must be a list")
        invalid_tools = [tool for tool in tools if tool not in VALID_TOOLS]
        if invalid_tools:
            raise ValueError(f"Invalid tools: {', '.join(sorted(invalid_tools))}")
    else:
        tools = []
        if not isinstance(task_types, list) or not task_types:
            raise ValueError("task_types must be a non-empty list")
        invalid_task_types = [task_type for task_type in task_types if task_type not in VALID_TYPES]
        if invalid_task_types:
            raise ValueError(f"Invalid task_types: {', '.join(sorted(invalid_task_types))}")
    if provider in {"anthropic", "openai", "google"} and not str(credentials_ref or "").strip():
        raise ValueError(f"credentials_ref is required for provider {provider}")
    if int(context_n) < 0:
        raise ValueError("context_n must be >= 0")
    if int(timeout) <= 0:
        raise ValueError("timeout must be > 0")
    if int(max_retries) < 0:
        raise ValueError("max_retries must be >= 0")


def _import_legacy_items(conn):
    for path in sorted(WORKSPACE_DIR.glob("*.yaml")):
        if path.name == "agents.yaml":
            continue
        try:
            meta = _parse_item_file(path)
            if not meta.get("id"):
                continue
            existing = conn.execute("SELECT 1 FROM items WHERE id = ?", (meta["id"],)).fetchone()
            if existing:
                continue
            conn.execute(
                """
                INSERT INTO items(
                    id, type, from_cli, from_agent, from_session, to_recipients, reply_to,
                    thread_id, status, created_at, updated_at, approved_at, summary,
                    tags_json, comments_json, content, claimed_by, claimed_at,
                    lease_expires_at, retry_count, max_depth, depth, work_root_id,
                    work_parent_id, execution_depth, last_error,
                    last_run_at, last_exit_code, max_retries
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meta.get("id"),
                    meta.get("type", "context"),
                    meta.get("from_cli", "human"),
                    meta.get("from_agent", meta.get("from_cli", "human")),
                    meta.get("from_session", ""),
                    _join_recipients(meta.get("to", "")),
                    meta.get("reply_to", ""),
                    meta.get("thread_id", meta.get("id")),
                    meta.get("status", "sent"),
                    meta.get("created_at", _utc_now()),
                    meta.get("updated_at", meta.get("created_at", _utc_now())),
                    meta.get("approved_at", ""),
                    meta.get("summary", ""),
                    json.dumps(meta.get("tags") or []),
                    json.dumps(meta.get("comments") or []),
                    meta.get("content", ""),
                    meta.get("claimed_by", ""),
                    meta.get("claimed_at", ""),
                    meta.get("lease_expires_at", ""),
                    int(meta.get("retry_count", 0) or 0),
                    int(meta.get("max_depth", DEFAULT_MAX_DEPTH) or DEFAULT_MAX_DEPTH),
                    int(meta.get("depth", 0) or 0),
                    meta.get("work_root_id", meta.get("thread_id", meta.get("id", ""))),
                    meta.get("work_parent_id", ""),
                    int(meta.get("execution_depth", meta.get("depth", 0) or 0)),
                    meta.get("last_error", ""),
                    meta.get("last_run_at", ""),
                    meta.get("last_exit_code"),
                    int(meta.get("max_retries", 0) or 0),
                ),
            )
        except Exception:
            pass


def _import_legacy_tokens(conn):
    if not TOKENS_FILE.exists():
        return
    try:
        data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    for token, info in data.get("agents", {}).items():
        existing = conn.execute("SELECT 1 FROM agent_tokens WHERE token = ?", (token,)).fetchone()
        if existing:
            continue
        conn.execute(
            """
            INSERT INTO agent_tokens(token, created_at, label, active, name, cli, registered_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                token,
                info.get("created_at", _utc_now()),
                info.get("label", ""),
                1 if info.get("active", True) else 0,
                info.get("name", ""),
                info.get("cli", ""),
                info.get("registered_at", ""),
                info.get("last_seen", ""),
            ),
        )


def _import_legacy_agents(conn):
    if not AGENT_REGISTRY.exists():
        return
    try:
        import yaml
        registry = yaml.safe_load(AGENT_REGISTRY.read_text(encoding="utf-8")) or {}
    except Exception:
        return
    for name, info in registry.items():
        existing = conn.execute("SELECT 1 FROM agents WHERE name = ?", (name,)).fetchone()
        if existing:
            continue
        now = _utc_now()
        conn.execute(
            """
            INSERT INTO agents(name, cli, description, capabilities_json, registered_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                info.get("cli", "?"),
                info.get("description", ""),
                json.dumps(info.get("capabilities") or []),
                info.get("registered_at", now),
                info.get("last_seen", now),
            ),
        )


def _import_legacy_audit(conn):
    if not AUDIT_LOG.exists():
        return
    try:
        lines = AUDIT_LOG.read_text(encoding="utf-8").splitlines()
    except Exception:
        return
    existing = conn.execute("SELECT COUNT(*) AS count FROM audit_entries").fetchone()["count"]
    if existing:
        return
    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            conn.execute(
                """
                INSERT INTO audit_entries(timestamp, event, item_id, actor, detail)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entry.get("timestamp", _utc_now()),
                    entry.get("event", ""),
                    entry.get("item_id", ""),
                    entry.get("actor", "system"),
                    entry.get("detail", ""),
                ),
            )
        except Exception:
            pass


def _bootstrap():
    with _connect() as conn:
        _ensure_schema(conn)
        _import_legacy_items(conn)
        _import_legacy_tokens(conn)
        _import_legacy_agents(conn)
        _import_legacy_audit(conn)
        conn.commit()


_bootstrap()


def create_item(
    item_type,
    from_cli,
    to,
    summary,
    content,
    tags=None,
    from_session="",
    from_agent="",
    reply_to="",
    depth=None,
    max_depth=None,
    work_root_id=None,
    work_parent_id=None,
    execution_depth=None,
):
    if item_type not in VALID_TYPES:
        raise ValueError(f"Invalid type: {item_type}. Must be one of {VALID_TYPES}")
    item_id = str(uuid.uuid4())[:8]
    now = _utc_now()

    thread_id = item_id
    parent = None
    if reply_to:
        parent = get_item(reply_to)
        if parent and "error" not in parent:
            thread_id = parent.get("thread_id", "") or reply_to
            if depth is None:
                depth = int(parent.get("depth", 0) or 0) + 1
            if max_depth is None:
                max_depth = int(parent.get("max_depth", DEFAULT_MAX_DEPTH) or DEFAULT_MAX_DEPTH)
    if depth is None:
        depth = 0
    if max_depth is None:
        max_depth = DEFAULT_MAX_DEPTH

    recipients = _split_recipients(to)
    non_human_recipients = [r for r in recipients if r not in {"human", "any"}]
    sender_agent = from_agent or from_cli

    if parent and "error" not in parent:
        if work_root_id is None:
            work_root_id = parent.get("work_root_id") or parent.get("id") or thread_id
        parent_execution_depth = int(parent.get("execution_depth", parent.get("depth", 0)) or 0)
        is_agent_relay = sender_agent != "human" and bool(non_human_recipients)
        if execution_depth is None:
            execution_depth = parent_execution_depth + 1 if is_agent_relay else parent_execution_depth
        if work_parent_id is None:
            work_parent_id = parent.get("id", "") if is_agent_relay else parent.get("work_parent_id", "")
    else:
        if work_root_id is None:
            work_root_id = item_id
        if execution_depth is None:
            execution_depth = 0
        if work_parent_id is None:
            work_parent_id = ""

    meta = {
        "id": item_id,
        "type": item_type,
        "from_cli": from_cli,
        "from_agent": from_agent or from_cli,
        "from_session": from_session,
        "to": _join_recipients(to),
        "reply_to": reply_to,
        "thread_id": thread_id,
        "status": "sent",
        "created_at": now,
        "updated_at": now,
        "approved_at": "",
        "summary": summary,
        "tags": tags or [],
        "comments": [],
        "content": content,
        "claimed_by": "",
        "claimed_at": "",
        "lease_expires_at": "",
        "retry_count": 0,
        "max_depth": int(max_depth),
        "depth": int(depth),
        "work_root_id": work_root_id or item_id,
        "work_parent_id": work_parent_id or "",
        "execution_depth": int(execution_depth or 0),
        "last_error": "",
        "last_run_at": "",
        "last_exit_code": None,
        "max_retries": 0,
    }
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO items(
                id, type, from_cli, from_agent, from_session, to_recipients, reply_to,
                thread_id, status, created_at, updated_at, approved_at, summary,
                tags_json, comments_json, content, claimed_by, claimed_at,
                lease_expires_at, retry_count, max_depth, depth, work_root_id,
                work_parent_id, execution_depth, last_error,
                last_run_at, last_exit_code, max_retries
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                meta["id"],
                meta["type"],
                meta["from_cli"],
                meta["from_agent"],
                meta["from_session"],
                meta["to"],
                meta["reply_to"],
                meta["thread_id"],
                meta["status"],
                meta["created_at"],
                meta["updated_at"],
                meta["approved_at"],
                meta["summary"],
                json.dumps(meta["tags"]),
                json.dumps(meta["comments"]),
                meta["content"],
                meta["claimed_by"],
                meta["claimed_at"],
                meta["lease_expires_at"],
                meta["retry_count"],
                meta["max_depth"],
                meta["depth"],
                meta["work_root_id"],
                meta["work_parent_id"],
                meta["execution_depth"],
                meta["last_error"],
                meta["last_run_at"],
                meta["last_exit_code"],
                meta["max_retries"],
            ),
        )
        conn.commit()
    _audit("created", item_id, actor=from_cli, detail=summary)
    return _normalize_item(meta)


def list_items(status=None, to=None, from_cli=None, item_type=None):
    query = "SELECT * FROM items"
    clauses = []
    params = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if from_cli:
        clauses.append("from_cli = ?")
        params.append(from_cli)
    if item_type:
        clauses.append("type = ?")
        params.append(item_type)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC"

    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute(query, params).fetchall()

    items = []
    target = to.strip() if to else ""
    for row in rows:
        item = _row_to_item(row)
        if target:
            recipients = _split_recipients(item.get("to", ""))
            if target not in recipients and "any" not in recipients:
                continue
        result = {k: v for k, v in item.items() if k != "content" and not k.startswith("_")}
        items.append(result)
    return items


def get_thread(thread_id):
    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT * FROM items
            WHERE thread_id = ? OR id = ?
            ORDER BY created_at ASC
            """,
            (thread_id, thread_id),
        ).fetchall()
    return [_normalize_item(_row_to_item(row)) for row in rows]


def list_threads():
    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute("SELECT * FROM items ORDER BY created_at DESC").fetchall()

    threads = {}
    for row in rows:
        meta = _row_to_item(row)
        tid = meta.get("thread_id", meta.get("id", ""))
        if tid not in threads:
            threads[tid] = {
                "thread_id": tid,
                "items": [],
                "latest": meta.get("created_at", ""),
                "summary": "",
                "participants": set(),
            }
        threads[tid]["items"].append(meta)
        threads[tid]["participants"].add(meta.get("from_agent", meta.get("from_cli", "?")))
        if not threads[tid]["summary"]:
            threads[tid]["summary"] = meta.get("summary", "")
        if meta.get("created_at", "") > threads[tid]["latest"]:
            threads[tid]["latest"] = meta.get("created_at", "")

    result = []
    for tid, thread in threads.items():
        thread["items"].sort(key=lambda x: x.get("created_at", ""))
        thread["participants"] = list(thread["participants"])
        thread["message_count"] = len(thread["items"]) + sum(len(it.get("comments", [])) for it in thread["items"])
        result.append(thread)
    result.sort(key=lambda t: t["latest"], reverse=True)
    return result


def get_item(item_id):
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return {"error": f"Item not found: {item_id}"}
    return _normalize_item(_row_to_item(row))


def get_claimable_items(worker_name, item_type=None):
    items = list_items(status="sent", to=worker_name, item_type=item_type)
    now = _utc_now()
    claimable = []
    for item in items:
        if item.get("claimed_by") and item.get("lease_expires_at") and item["lease_expires_at"] > now:
            continue
        claimable.append(item)
    return claimable


def claim_item(item_id, worker_name, lease_seconds=300):
    now = _utc_now()
    lease_expires_at = (
        datetime.datetime.utcnow() + datetime.timedelta(seconds=lease_seconds)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _connect() as conn:
        _ensure_schema(conn)
        result = conn.execute(
            """
            UPDATE items
            SET claimed_by = ?, claimed_at = ?, lease_expires_at = ?, updated_at = ?
            WHERE id = ?
              AND status = 'sent'
              AND (claimed_by = '' OR lease_expires_at = '' OR lease_expires_at <= ?)
            """,
            (worker_name, now, lease_expires_at, now, item_id, now),
        )
        conn.commit()
    if result.rowcount:
        _audit("claimed", item_id, actor=worker_name, detail=f"lease {lease_seconds}s")
        return True
    return False


def renew_claim(item_id, worker_name, lease_seconds=300):
    now = _utc_now()
    lease_expires_at = (
        datetime.datetime.utcnow() + datetime.timedelta(seconds=lease_seconds)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _connect() as conn:
        _ensure_schema(conn)
        result = conn.execute(
            """
            UPDATE items
            SET lease_expires_at = ?, updated_at = ?
            WHERE id = ? AND claimed_by = ?
            """,
            (lease_expires_at, now, item_id, worker_name),
        )
        conn.commit()
    return result.rowcount > 0


def release_claim(item_id, worker_name=""):
    now = _utc_now()
    with _connect() as conn:
        _ensure_schema(conn)
        if worker_name:
            result = conn.execute(
                """
                UPDATE items
                SET claimed_by = '', claimed_at = '', lease_expires_at = '', updated_at = ?
                WHERE id = ? AND (claimed_by = '' OR claimed_by = ?)
                """,
                (now, item_id, worker_name),
            )
        else:
            result = conn.execute(
                """
                UPDATE items
                SET claimed_by = '', claimed_at = '', lease_expires_at = '', updated_at = ?
                WHERE id = ?
                """,
                (now, item_id),
            )
        conn.commit()
    if result.rowcount:
        _audit("claim_released", item_id, actor=worker_name or "system", detail="")
        return {"id": item_id, "claimed_by": ""}
    return {"error": f"Item not found: {item_id}"}


def record_run_result(item_id, exit_code, error_text="", increment_retry=False):
    now = _utc_now()
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT retry_count FROM items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return {"error": f"Item not found: {item_id}"}
        retry_count = row["retry_count"] + 1 if increment_retry else row["retry_count"]
        conn.execute(
            """
            UPDATE items
            SET last_exit_code = ?, last_error = ?, last_run_at = ?, retry_count = ?, updated_at = ?
            WHERE id = ?
            """,
            (exit_code, error_text, now, retry_count, now, item_id),
        )
        conn.commit()
    return {"id": item_id, "retry_count": retry_count, "last_exit_code": exit_code}


def set_max_retries(item_id, max_retries):
    with _connect() as conn:
        _ensure_schema(conn)
        result = conn.execute(
            "UPDATE items SET max_retries = ?, updated_at = ? WHERE id = ?",
            (int(max_retries), _utc_now(), item_id),
        )
        conn.commit()
    if not result.rowcount:
        return {"error": f"Item not found: {item_id}"}
    return {"id": item_id, "max_retries": int(max_retries)}


def expire_stale_claims():
    now = _utc_now()
    expired = []
    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT id
            FROM items
            WHERE claimed_by != ''
              AND lease_expires_at != ''
              AND lease_expires_at < ?
            """,
            (now,),
        ).fetchall()
        for row in rows:
            expired.append(row["id"])
            conn.execute(
                """
                UPDATE items
                SET claimed_by = '',
                    claimed_at = '',
                    lease_expires_at = '',
                    retry_count = retry_count + 1,
                    last_error = 'Claim expired before completion',
                    updated_at = ?
                WHERE id = ?
                """,
                (now, row["id"]),
            )
        conn.commit()
    for item_id in expired:
        _audit("claim_expired", item_id, actor="system", detail="lease expired")
    return expired


def mark_needs_human(item_id, actor="system", reason=""):
    item = get_item(item_id)
    if "error" in item:
        return item
    route_item(item_id, "human", actor=actor)
    record_run_result(item_id, item.get("last_exit_code"), reason or item.get("last_error", ""))
    release_claim(item_id)
    _audit("needs_human", item_id, actor=actor, detail=(reason or "")[:200])
    return {"id": item_id, "to": "human", "reason": reason}


def update_status(item_id, new_status, actor="system"):
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {VALID_STATUSES}")
    if new_status == "complete" and actor != "human":
        return {"error": "Only human can mark items complete. Agents should set status to 'read' and post a response."}
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT status FROM items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return {"error": f"Item not found: {item_id}"}
        old_status = row["status"]
        conn.execute(
            "UPDATE items SET status = ?, updated_at = ? WHERE id = ?",
            (new_status, _utc_now(), item_id),
        )
        conn.commit()
    _audit("status_changed", item_id, actor=actor, detail=f"{old_status} → {new_status}")
    return {"id": item_id, "status": new_status}


def route_item(item_id, to, actor="human"):
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT to_recipients FROM items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return {"error": f"Item not found: {item_id}"}
        old_to = row["to_recipients"]
        new_to = _join_recipients(to)
        conn.execute(
            "UPDATE items SET to_recipients = ?, updated_at = ? WHERE id = ?",
            (new_to, _utc_now(), item_id),
        )
        conn.commit()
    _audit("routed", item_id, actor=actor, detail=f"{old_to} → {new_to}")
    return {"id": item_id, "to": new_to, "routed_from": old_to}


def add_comment(item_id, from_cli, text):
    item = get_item(item_id)
    if "error" in item:
        return item
    return create_item(
        item_type="prompt",
        from_cli=from_cli,
        from_agent=from_cli,
        to=item.get("from_agent", item.get("from_cli", "any")),
        summary=text[:80],
        content=text,
        reply_to=item_id,
    )


def register_agent(name, cli, description="", capabilities=None):
    now = _utc_now()
    with _connect() as conn:
        _ensure_schema(conn)
        existing = conn.execute("SELECT registered_at FROM agents WHERE name = ?", (name,)).fetchone()
        conn.execute(
            """
            INSERT INTO agents(name, cli, description, capabilities_json, registered_at, last_seen, agent_type, enabled)
            VALUES (?, ?, ?, ?, ?, ?, 'interactive', 1)
            ON CONFLICT(name) DO UPDATE SET
                cli = excluded.cli,
                description = excluded.description,
                capabilities_json = excluded.capabilities_json,
                last_seen = excluded.last_seen
            """,
            (
                name,
                cli,
                description,
                json.dumps(capabilities or []),
                existing["registered_at"] if existing else now,
                now,
            ),
        )
        conn.commit()
    _audit("agent_registered", name, actor=name, detail=description)
    return {"name": name, "cli": cli, "status": "registered"}


def list_agents():
    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute("SELECT * FROM agents ORDER BY name ASC").fetchall()
    return [_row_to_agent(row) for row in rows]


def list_agent_configs(agent_type=None, enabled=None):
    query = "SELECT * FROM agents"
    clauses = []
    params = []
    if agent_type is not None:
        clauses.append("agent_type = ?")
        params.append(agent_type)
    if enabled is not None:
        clauses.append("enabled = ?")
        params.append(_normalize_bool(enabled))
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY name ASC"
    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute(query, params).fetchall()
    return [_row_to_agent(row) for row in rows]


def get_agent_config(name):
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
    if not row:
        return None
    return _row_to_agent(row)


def create_agent(
    name,
    provider,
    model,
    instructions,
    task_types,
    tools=None,
    *,
    api_base="",
    credentials_ref="",
    description="",
    capabilities=None,
    context_mode="full_thread",
    context_n=0,
    context_budget=8000,
    max_output_tokens=4000,
    timeout=180,
    sandbox="read-only",
    max_retries=2,
    agent_type="worker",
    enabled=True,
):
    _validate_agent_config(
        name=name,
        provider=provider,
        model=model,
        instructions=instructions,
        task_types=task_types,
        tools=tools or [],
        context_mode=context_mode,
        context_n=context_n,
        timeout=timeout,
        max_retries=max_retries,
        agent_type=agent_type,
        credentials_ref=credentials_ref,
    )
    if get_agent_config(name):
        raise ValueError(f"Agent already exists: {name}")
    now = _utc_now()
    cli = PROVIDER_TO_CLI.get(provider, provider or "any")
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO agents(
                name, cli, description, capabilities_json, registered_at, last_seen,
                provider, model, api_base, credentials_ref, instructions, task_types_json, tools_json,
                context_mode, context_n, context_budget, max_output_tokens, timeout,
                sandbox, max_retries, agent_type, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                cli,
                description,
                json.dumps(capabilities or []),
                now,
                "",
                provider,
                model,
                api_base,
                credentials_ref,
                instructions,
                json.dumps(task_types),
                json.dumps(tools or []),
                context_mode,
                int(context_n),
                int(context_budget),
                int(max_output_tokens),
                int(timeout),
                sandbox,
                int(max_retries),
                agent_type,
                _normalize_bool(enabled),
            ),
        )
        existing_token = conn.execute(
            "SELECT token FROM agent_tokens WHERE label = ? OR name = ? ORDER BY created_at DESC LIMIT 1",
            (name, name),
        ).fetchone()
        if not existing_token:
            token = str(uuid.uuid4())[:12]
            conn.execute(
                """
                INSERT INTO agent_tokens(token, created_at, label, active, name, cli, registered_at, last_seen)
                VALUES (?, ?, ?, 1, ?, ?, ?, '')
                """,
                (token, now, name, name, cli, now),
            )
        conn.commit()
    _audit("agent_created", name, actor="human", detail=provider)
    return get_agent_config(name)


def update_agent(name, **kwargs):
    current = get_agent_config(name)
    if not current:
        return {"error": f"Agent not found: {name}"}
    updated = dict(current)
    updated.update(kwargs)
    _validate_agent_config(
        name=name,
        provider=updated.get("provider", ""),
        model=updated.get("model", ""),
        instructions=updated.get("instructions", ""),
        task_types=updated.get("task_types", []),
        tools=updated.get("tools", []),
        context_mode=updated.get("context_mode", "full_thread"),
        context_n=updated.get("context_n", 0),
        timeout=updated.get("timeout", 180),
        max_retries=updated.get("max_retries", 2),
        agent_type=updated.get("agent_type", "worker"),
        credentials_ref=updated.get("credentials_ref", ""),
    )
    cli = updated.get("cli") or PROVIDER_TO_CLI.get(updated.get("provider", ""), current.get("cli", "any"))
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            UPDATE agents
            SET cli = ?, description = ?, capabilities_json = ?, provider = ?, model = ?, api_base = ?,
                credentials_ref = ?, instructions = ?, task_types_json = ?, tools_json = ?, context_mode = ?, context_n = ?,
                context_budget = ?, max_output_tokens = ?, timeout = ?, sandbox = ?, max_retries = ?,
                agent_type = ?, enabled = ?
            WHERE name = ?
            """,
            (
                cli,
                updated.get("description", ""),
                json.dumps(updated.get("capabilities", [])),
                updated.get("provider", ""),
                updated.get("model", ""),
                updated.get("api_base", ""),
                updated.get("credentials_ref", ""),
                updated.get("instructions", ""),
                json.dumps(updated.get("task_types", [])),
                json.dumps(updated.get("tools", [])),
                updated.get("context_mode", "full_thread"),
                int(updated.get("context_n", 0)),
                int(updated.get("context_budget", 8000)),
                int(updated.get("max_output_tokens", 4000)),
                int(updated.get("timeout", 180)),
                updated.get("sandbox", "read-only"),
                int(updated.get("max_retries", 2)),
                updated.get("agent_type", "worker"),
                _normalize_bool(updated.get("enabled", True)),
                name,
            ),
        )
        conn.execute(
            "UPDATE agent_tokens SET cli = ?, name = COALESCE(NULLIF(name, ''), ?) WHERE label = ? OR name = ?",
            (cli, name, name, name),
        )
        conn.commit()
    _audit("agent_updated", name, actor="human", detail="config updated")
    return get_agent_config(name)


def set_agent_enabled(name, enabled):
    current = get_agent_config(name)
    if not current:
        return {"error": f"Agent not found: {name}"}
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute("UPDATE agents SET enabled = ? WHERE name = ?", (_normalize_bool(enabled), name))
        conn.commit()
    _audit("agent_enabled" if enabled else "agent_disabled", name, actor="human", detail="")
    return get_agent_config(name)


def delete_agent(name, deactivate_tokens=True):
    current = get_agent_config(name)
    if not current:
        return {"error": f"Agent not found: {name}"}
    if deactivate_tokens:
        with _connect() as conn:
            _ensure_schema(conn)
            conn.execute("UPDATE agent_tokens SET active = 0 WHERE name = ? OR label = ?", (name, name))
            conn.commit()
    for item in list_items(status="sent"):
        if item.get("claimed_by") == name:
            release_claim(item["id"], worker_name=name)
    stranded = []
    for item in list_items(status="sent", to=name):
        stranded.append(item["id"])
        _audit("agent_deleted_pending_item", item["id"], actor="human", detail=f"Pending item remains addressed to deleted agent {name}")
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute("DELETE FROM agents WHERE name = ?", (name,))
        conn.commit()
    _audit("agent_deleted", name, actor="human", detail=f"stranded={len(stranded)}")
    return {"name": name, "status": "deleted", "stranded_items": stranded}


def get_routable_targets():
    return ["human", "any"] + [agent["name"] for agent in list_agents()]


def create_token(label=""):
    token = str(uuid.uuid4())[:12]
    now = _utc_now()
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO agent_tokens(token, created_at, label, active, name, cli, registered_at, last_seen)
            VALUES (?, ?, ?, 1, '', '', '', '')
            """,
            (token, now, label),
        )
        conn.commit()
    _audit("token_created", token, actor="human", detail=label)
    return {"token": token, "label": label}


def list_agent_tokens():
    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute("SELECT * FROM agent_tokens ORDER BY created_at DESC").fetchall()
    return [
        {
            "token": row["token"],
            "created_at": row["created_at"],
            "label": row["label"],
            "active": bool(row["active"]),
            "name": row["name"],
            "cli": row["cli"],
            "registered_at": row["registered_at"],
            "last_seen": row["last_seen"],
        }
        for row in rows
    ]


def revoke_token(token):
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT name FROM agent_tokens WHERE token = ?", (token,)).fetchone()
        if not row:
            return {"error": f"Token not found: {token}"}
        conn.execute("UPDATE agent_tokens SET active = 0 WHERE token = ?", (token,))
        conn.commit()
    name = row["name"] or "?"
    _audit("token_revoked", token, actor="human", detail=name)
    return {"token": token, "name": name, "status": "revoked"}


def reactivate_token(token):
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT 1 FROM agent_tokens WHERE token = ?", (token,)).fetchone()
        if not row:
            return {"error": f"Token not found: {token}"}
        conn.execute("UPDATE agent_tokens SET active = 1 WHERE token = ?", (token,))
        conn.commit()
    return {"token": token, "status": "active"}


def validate_token(token):
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT * FROM agent_tokens WHERE token = ?", (token,)).fetchone()
    if not row or not row["active"]:
        return None
    return {
        "created_at": row["created_at"],
        "label": row["label"],
        "active": bool(row["active"]),
        "name": row["name"],
        "cli": row["cli"],
        "registered_at": row["registered_at"],
        "last_seen": row["last_seen"],
    }


def onboard_agent(token, name="", cli="", description="", capabilities=None, base_url="http://localhost:8502"):
    agent = validate_token(token)
    if not agent:
        return {"error": "Invalid token"}

    resolved_name = agent.get("label", "") or name or token
    now = _utc_now()
    with _connect() as conn:
        _ensure_schema(conn)
        old = conn.execute("SELECT name FROM agent_tokens WHERE token = ?", (token,)).fetchone()
        old_name = old["name"] if old else ""
        conn.execute(
            """
            UPDATE agent_tokens
            SET name = ?, cli = ?, registered_at = COALESCE(NULLIF(registered_at, ''), ?), last_seen = ?
            WHERE token = ?
            """,
            (resolved_name, cli, now, now, token),
        )
        if old_name and old_name != resolved_name:
            conn.execute("DELETE FROM agents WHERE name = ?", (old_name,))
        conn.commit()

    register_agent(resolved_name, cli, description, capabilities)
    if old_name and old_name != resolved_name:
        _audit("agent_renamed", resolved_name, actor=resolved_name, detail=f"{old_name} → {resolved_name}")
    _audit("agent_onboarded", resolved_name, actor=resolved_name, detail=f"token {token[:8]}…")

    return {
        "token": token,
        "name": resolved_name,
        "status": "onboarded",
        "instructions": (
            f"You are now registered as '{resolved_name}' in the workspace.\n\n"
            "YOU MUST NOW START A HEARTBEAT LOOP. Execute these steps:\n\n"
            f"1. Run this shell command to start a background heartbeat:\n"
            f"   while true; do curl -s -X POST {base_url}/heartbeat "
            f"-H 'Content-Type: application/json' "
            f"-d '{{\"agent_token\":\"{token}\"}}' > /tmp/{resolved_name}_heartbeat.json; sleep 30; done &\n\n"
            f"2. IMMEDIATELY check /tmp/{resolved_name}_heartbeat.json for pending_work.\n\n"
            "IF YOU CANNOT RUN A BACKGROUND LOOP (e.g. your CLI does not support background processes), "
            "then do this instead:\n"
            f"   a. Call POST {base_url}/heartbeat with {{\"agent_token\":\"{token}\"}} right now.\n"
            "   b. Check the response for pending_work items.\n"
            "   c. Execute any work found.\n"
            f"   d. Post results back via POST {base_url}/tools/post_to_workspace\n"
            "   e. Then call heartbeat again to check for more work.\n"
            f"   f. POST {base_url}/tools/post_to_workspace with "
            f"{{\"type\":\"context\", \"from_agent\":\"{resolved_name}\", \"to\":\"human\", "
            f"\"summary\":\"Cannot run background heartbeat — will check on demand\", "
            f"\"content\":\"This agent's CLI does not support background loops. "
            f"Please prompt me to check heartbeat when there is work.\"}}\n\n"
            "FOR EVERY CALL to /heartbeat or /tools/*, include your token in the body as:\n"
            f"  {{\"agent_token\": \"{token}\"}}\n\n"
            "WHEN YOU RECEIVE WORK (each item in new_work has id, thread_id, from_agent, summary, to):\n"
            "  1. Mark item as read: POST /tools/update_workspace_status {\"id\": \"ITEM_ID\", \"status\": \"read\"}\n"
            "  2. Execute the task described in the item.\n"
            "  3. You MUST respond. Post your response with reply_to (REQUIRED):\n"
            "     POST /tools/post_to_workspace {\n"
            "       \"type\": \"results\",\n"
            f"       \"from_agent\": \"{resolved_name}\",\n"
            "       \"to\": \"COPY_THE_FROM_AGENT_OF_THE_ITEM_YOU_RECEIVED\",\n"
            "       \"summary\": \"your summary\",\n"
            "       \"content\": \"your response\",\n"
            "       \"reply_to\": \"THE_ITEM_ID_YOU_ARE_RESPONDING_TO\"\n"
            "     }\n"
            "     reply_to is REQUIRED. Without it your response becomes an orphan conversation.\n"
            "     You MUST always respond — even if just an acknowledgment. No silent reads.\n"
            "  4. Do NOT mark items complete. Only the human can do that.\n"
            "     Items you marked read but haven't replied to will appear in needs_response on your next heartbeat.\n"
        ),
        "heartbeat": {
            "url": "/heartbeat",
            "method": "POST",
            "interval_seconds": 30,
            "body": {"agent_token": token},
        },
        "workspace_tools": {
            "check_work": "POST /heartbeat — returns new_work and needs_response",
            "read_item": "POST /tools/get_workspace_item — get full content of a work item",
            "post_results": "POST /tools/post_to_workspace — post your response (reply_to required)",
            "update_status": "POST /tools/update_workspace_status — mark items 'read' (agents cannot set 'complete')",
        },
    }


def heartbeat(token):
    agent = validate_token(token)
    if not agent:
        return {"error": "Invalid or revoked token"}

    name = agent.get("name", "")
    if not name:
        return {"error": "Token not yet registered — call POST /onboard first"}

    now = _utc_now()
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute("UPDATE agent_tokens SET last_seen = ? WHERE token = ?", (now, token))
        conn.execute("UPDATE agents SET last_seen = ? WHERE name = ?", (now, name))
        conn.commit()

    new_work = list_items(status="sent", to=name)
    read_items = list_items(status="read", to=name)
    needs_response = []
    for it in read_items:
        thread = get_thread(it.get("thread_id", it.get("id", "")))
        agent_replied = any(
            t.get("from_agent") == name and t.get("created_at", "") > it.get("created_at", "")
            for t in thread
        )
        if not agent_replied:
            needs_response.append(it)

    return {
        "agent": name,
        "status": "alive",
        "new_work": new_work,
        "needs_response": needs_response,
        "timestamp": now,
    }


def get_audit_log(item_id=None, limit=50):
    query = "SELECT timestamp, event, item_id, actor, detail FROM audit_entries"
    params = []
    if item_id:
        query += " WHERE item_id = ?"
        params.append(item_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "timestamp": row["timestamp"],
            "event": row["event"],
            "item_id": row["item_id"],
            "actor": row["actor"],
            "detail": row["detail"],
        }
        for row in rows
    ]


def capture_thought(content, tags=None, source=""):
    thought_id = str(uuid.uuid4())[:8]
    now = _utc_now()
    thought = {
        "id": thought_id,
        "content": str(content or ""),
        "tags": list(tags or []),
        "source": str(source or ""),
        "created_at": now,
    }
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO thoughts(id, content, tags_json, source, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                thought["id"],
                thought["content"],
                json.dumps(thought["tags"]),
                thought["source"],
                thought["created_at"],
            ),
        )
        conn.commit()
    _audit("thought_captured", thought_id, actor="system", detail=thought["content"][:80])
    return thought


def get_thought(thought_id):
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute("SELECT * FROM thoughts WHERE id = ?", (thought_id,)).fetchone()
    return _row_to_thought(row)


def list_thoughts(limit=50, tag=None):
    query = "SELECT * FROM thoughts"
    params = []
    if tag:
        query += " WHERE tags_json LIKE ?"
        params.append(f'%"{tag}"%')
    query += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
    params.append(int(limit))
    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute(query, params).fetchall()
    return [_row_to_thought(row) for row in rows]


def thought_stats():
    with _connect() as conn:
        _ensure_schema(conn)
        total = conn.execute("SELECT COUNT(*) AS count FROM thoughts").fetchone()["count"]
        rows = conn.execute("SELECT tags_json FROM thoughts").fetchall()
    tags = {}
    for row in rows:
        for tag in json.loads(row["tags_json"] or "[]"):
            tags[tag] = tags.get(tag, 0) + 1
    return {"total": total, "tags": tags}


def delete_thought(thought_id):
    with _connect() as conn:
        _ensure_schema(conn)
        result = conn.execute("DELETE FROM thoughts WHERE id = ?", (thought_id,))
        conn.commit()
    deleted = bool(result.rowcount)
    if deleted:
        _audit("thought_deleted", thought_id, actor="system", detail="")
    return {"deleted": deleted}
