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
import pathlib
import sqlite3
import uuid


WORKSPACE_DIR = pathlib.Path(__file__).parent / "workspace"
AUDIT_LOG = WORKSPACE_DIR / "audit.jsonl"
TOKENS_FILE = WORKSPACE_DIR / "tokens.json"
AGENT_REGISTRY = WORKSPACE_DIR / "agents.yaml"
DB_FILE = WORKSPACE_DIR / "workspace.db"

VALID_TYPES = {"plan", "results", "review", "prompt", "handoff", "question", "context"}
VALID_STATUSES = {"sent", "read", "complete"}
VALID_CLIS = {"claude", "codex", "gemini", "human", "any"}


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
        """
    )
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
                    tags_json, comments_json, content
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def create_item(item_type, from_cli, to, summary, content, tags=None, from_session="", from_agent="", reply_to=""):
    if item_type not in VALID_TYPES:
        raise ValueError(f"Invalid type: {item_type}. Must be one of {VALID_TYPES}")
    item_id = str(uuid.uuid4())[:8]
    now = _utc_now()

    thread_id = item_id
    if reply_to:
        parent = get_item(reply_to)
        if parent and "error" not in parent:
            thread_id = parent.get("thread_id", "") or reply_to

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
    }
    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO items(
                id, type, from_cli, from_agent, from_session, to_recipients, reply_to,
                thread_id, status, created_at, updated_at, approved_at, summary,
                tags_json, comments_json, content
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            INSERT INTO agents(name, cli, description, capabilities_json, registered_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
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
    return [
        {
            "name": row["name"],
            "cli": row["cli"],
            "description": row["description"],
            "capabilities": json.loads(row["capabilities_json"] or "[]"),
            "registered_at": row["registered_at"],
            "last_seen": row["last_seen"],
        }
        for row in rows
    ]


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
