"""
Chat UI — FastAPI + WebSocket real-time chat for DoPeJarMo workspace.

Reads/writes workspace.py directly. No build step. Single file.

Usage:
    python3 chat.py              # start on port 8503
    python3 chat.py --port 8504  # custom port
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

import workspace as ws

app = FastAPI(title="DoPeJarMo Chat")

# ── WebSocket connection manager ─────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}  # conn_id -> ws
        self.subscriptions: dict[str, set[str]] = {}  # conn_id -> set of thread_ids
        self._poll_task: asyncio.Task | None = None
        self._last_seen: dict[str, str] = {}  # thread_id -> latest created_at

    async def connect(self, ws: WebSocket, conn_id: str):
        await ws.accept()
        self.active[conn_id] = ws

    def disconnect(self, conn_id: str):
        self.active.pop(conn_id, None)
        self.subscriptions.pop(conn_id, None)

    def subscribe(self, conn_id: str, thread_id: str):
        self.subscriptions.setdefault(conn_id, set()).add(thread_id)

    def unsubscribe(self, conn_id: str, thread_id: str):
        if conn_id in self.subscriptions:
            self.subscriptions[conn_id].discard(thread_id)

    async def broadcast_thread_update(self, thread_id: str, messages: list[dict]):
        dead = []
        for conn_id, subs in self.subscriptions.items():
            if thread_id in subs and conn_id in self.active:
                try:
                    await self.active[conn_id].send_json({
                        "type": "thread_update",
                        "thread_id": thread_id,
                        "messages": messages,
                    })
                except Exception:
                    dead.append(conn_id)
        for conn_id in dead:
            self.disconnect(conn_id)

    async def broadcast_thread_list(self):
        threads = _get_threads_summary()
        dead = []
        for conn_id, ws_conn in self.active.items():
            try:
                await ws_conn.send_json({"type": "thread_list", "threads": threads})
            except Exception:
                dead.append(conn_id)
        for conn_id in dead:
            self.disconnect(conn_id)

    async def start_polling(self):
        if self._poll_task is None:
            self._poll_task = asyncio.create_task(self._poll_loop())

    async def _poll_loop(self):
        while True:
            await asyncio.sleep(2.5)
            if not self.active:
                continue
            try:
                threads = ws.list_threads()
                changed = False
                for t in threads:
                    tid = t["thread_id"]
                    latest = t["latest"]
                    if tid not in self._last_seen or self._last_seen[tid] != latest:
                        self._last_seen[tid] = latest
                        changed = True
                        thread_msgs = _format_thread(ws.get_thread(tid))
                        await self.broadcast_thread_update(tid, thread_msgs)
                if changed:
                    await self.broadcast_thread_list()
            except Exception:
                pass


manager = ConnectionManager()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _authenticate(token: str | None) -> dict | None:
    """Validate token. Returns agent info or None. Allow no-token for local human."""
    if not token:
        return {"name": "human", "cli": "human"}
    info = ws.validate_token(token)
    if info:
        return info
    return None


def _format_item(item: dict) -> dict:
    return {
        "id": item.get("id", ""),
        "type": item.get("type", ""),
        "from_agent": item.get("from_agent", item.get("from_cli", "?")),
        "from_cli": item.get("from_cli", "?"),
        "to": item.get("to", ""),
        "reply_to": item.get("reply_to", ""),
        "thread_id": item.get("thread_id", ""),
        "status": item.get("status", ""),
        "created_at": item.get("created_at", ""),
        "summary": item.get("summary", ""),
        "content": item.get("content", ""),
    }


def _format_thread(items: list[dict]) -> list[dict]:
    return [_format_item(it) for it in items]


def _get_threads_summary() -> list[dict]:
    threads = ws.list_threads()
    return [
        {
            "thread_id": t["thread_id"],
            "summary": t["summary"],
            "participants": t["participants"],
            "latest": t["latest"],
            "message_count": t["message_count"],
            "has_active": any(it.get("status") in ("sent", "read") for it in t["items"]),
        }
        for t in threads
    ]


def _resolve_default_route(reply_to: str, from_agent: str) -> str:
    if not reply_to:
        return "any"
    parent = ws.get_item(reply_to)
    if not parent or "error" in parent:
        return "any"
    thread = ws.get_thread(parent.get("thread_id", "") or reply_to)
    for item in reversed(thread):
        candidate = item.get("from_agent", item.get("from_cli", "")).strip()
        if candidate and candidate not in {"human", from_agent}:
            return candidate
    participants = []
    for item in thread:
        participant = item.get("from_agent", item.get("from_cli", "")).strip()
        if participant and participant not in {"human", from_agent} and participant not in participants:
            participants.append(participant)
    return participants[0] if participants else "any"


def _resolve_send_target(explicit_to, reply_to: str, from_agent: str) -> str:
    candidate = str(explicit_to or "").strip()
    valid_targets = set(ws.get_routable_targets())
    if candidate and candidate in valid_targets and candidate not in {"human", "any"}:
        return candidate
    return _resolve_default_route(reply_to, from_agent)


# ── REST API ─────────────────────────────────────────────────────────────────

@app.get("/api/threads")
async def api_threads():
    return _get_threads_summary()


@app.get("/api/thread/{thread_id}")
async def api_thread(thread_id: str):
    items = ws.get_thread(thread_id)
    if not items:
        return JSONResponse({"error": "Thread not found"}, status_code=404)
    return _format_thread(items)


@app.post("/api/send")
async def api_send(request: Request):
    body = await request.json()
    token = body.get("token")
    auth = _authenticate(token)
    if not auth:
        return JSONResponse({"error": "Invalid token"}, status_code=401)

    from_agent = auth.get("name", "human")
    from_cli = auth.get("cli", "human")
    reply_to = body.get("reply_to", "")
    effective_to = _resolve_send_target(body.get("to", ""), reply_to, from_agent)
    item = ws.create_item(
        item_type=body.get("type", "prompt"),
        from_cli=from_cli,
        to=effective_to,
        summary=body.get("summary", body.get("content", "")[:80]),
        content=body.get("content", ""),
        from_agent=from_agent,
        reply_to=reply_to,
    )
    return _format_item(item)


@app.get("/api/agents")
async def api_agents():
    return ws.list_agents()


@app.get("/api/targets")
async def api_targets():
    return ws.get_routable_targets()


# ── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default="")):
    auth = _authenticate(token)
    if not auth:
        await websocket.close(code=4001, reason="Invalid token")
        return

    conn_id = f"{id(websocket)}-{time.time()}"
    await manager.connect(websocket, conn_id)
    await manager.start_polling()

    try:
        # Send initial thread list
        threads = _get_threads_summary()
        await websocket.send_json({"type": "thread_list", "threads": threads})

        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "subscribe":
                tid = data.get("thread_id", "")
                if tid:
                    manager.subscribe(conn_id, tid)
                    items = ws.get_thread(tid)
                    await websocket.send_json({
                        "type": "thread_update",
                        "thread_id": tid,
                        "messages": _format_thread(items),
                    })

            elif action == "unsubscribe":
                tid = data.get("thread_id", "")
                if tid:
                    manager.unsubscribe(conn_id, tid)

            elif action == "send":
                from_agent = auth.get("name", "human")
                from_cli = auth.get("cli", "human")
                reply_to = data.get("reply_to", "")
                effective_to = _resolve_send_target(data.get("to", ""), reply_to, from_agent)
                item = ws.create_item(
                    item_type=data.get("type", "prompt"),
                    from_cli=from_cli,
                    to=effective_to,
                    summary=data.get("summary", data.get("content", "")[:80]),
                    content=data.get("content", ""),
                    from_agent=from_agent,
                    reply_to=reply_to,
                )
                await websocket.send_json({
                    "type": "sent",
                    "message": _format_item(item),
                })

    except WebSocketDisconnect:
        manager.disconnect(conn_id)
    except Exception:
        manager.disconnect(conn_id)


# ── HTML Frontend ────────────────────────────────────────────────────────────

CHAT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DoPeJarMo Chat</title>
<style>
:root {
  --bg: #0e0e10;
  --bg-surface: #1a1a1f;
  --bg-hover: #24242b;
  --bg-active: #2a2a33;
  --border: #2e2e38;
  --text: #e4e4e7;
  --text-dim: #8b8b96;
  --text-muted: #5a5a66;
  --accent: #8b5cf6;
  --accent-dim: #6d28d9;
  --human: #6366f1;
  --claude: #a855f7;
  --codex: #22c55e;
  --gemini: #3b82f6;
  --sent: #eab308;
  --read: #6366f1;
  --complete: #22c55e;
  --radius: 8px;
  --radius-lg: 12px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  overflow: hidden;
}

.app {
  display: grid;
  grid-template-columns: 280px 1fr;
  height: 100vh;
}

/* ── Sidebar ─────────────────────────────────────────────────── */
.sidebar {
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-header h1 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.btn-new {
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius);
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-new:hover { background: var(--accent-dim); }

.thread-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.thread-item {
  padding: 10px 12px;
  border-radius: var(--radius);
  cursor: pointer;
  margin-bottom: 2px;
  transition: background 0.15s;
}
.thread-item:hover { background: var(--bg-hover); }
.thread-item.active { background: var(--bg-active); }

.thread-summary {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.thread-meta {
  font-size: 11px;
  color: var(--text-dim);
  display: flex;
  align-items: center;
  gap: 6px;
}

.thread-participants { display: flex; gap: 3px; }

.participant-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.active-badge {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--sent);
  display: inline-block;
  margin-right: 4px;
}

.sidebar-section {
  padding: 8px 12px 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

/* ── Main panel ──────────────────────────────────────────────── */
.main {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-surface);
}

.chat-title {
  font-size: 15px;
  font-weight: 600;
}

.chat-participants {
  font-size: 12px;
  color: var(--text-dim);
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* ── Chat bubbles ────────────────────────────────────────────── */
.msg-group {
  display: flex;
  gap: 10px;
  padding: 8px 0;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
  margin-top: 2px;
}

.msg-body { flex: 1; min-width: 0; }

.msg-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 3px;
}

.msg-author {
  font-size: 13px;
  font-weight: 600;
}

.msg-time {
  font-size: 11px;
  color: var(--text-muted);
}

.msg-status {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 500;
}
.msg-status.sent { background: rgba(234,179,8,0.15); color: var(--sent); }
.msg-status.read { background: rgba(99,102,241,0.15); color: var(--read); }
.msg-status.complete { background: rgba(34,197,94,0.15); color: var(--complete); }

.msg-content {
  font-size: 14px;
  line-height: 1.55;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-content code {
  background: var(--bg-hover);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 13px;
}

.msg-content pre {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 12px;
  margin: 6px 0;
  overflow-x: auto;
  font-size: 13px;
}

.msg-type {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* ── Input bar ───────────────────────────────────────────────── */
.input-bar {
  padding: 12px 20px 16px;
  border-top: 1px solid var(--border);
  background: var(--bg-surface);
}

.input-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.input-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.route-select {
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 6px 10px;
  font-size: 12px;
  outline: none;
  cursor: pointer;
}
.route-select:focus { border-color: var(--accent); }

.type-select {
  background: var(--bg);
  color: var(--text-dim);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 6px 10px;
  font-size: 12px;
  outline: none;
  cursor: pointer;
}

#msg-input {
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 14px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  outline: none;
  width: 100%;
  min-height: 42px;
  max-height: 160px;
}
#msg-input:focus { border-color: var(--accent); }
#msg-input::placeholder { color: var(--text-muted); }

.btn-send {
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius);
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}
.btn-send:hover { background: var(--accent-dim); }
.btn-send:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── Empty / welcome state ───────────────────────────────────── */
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 15px;
  text-align: center;
  padding: 40px;
}
.empty-state p { margin-bottom: 8px; }
.empty-state .hint { font-size: 13px; color: var(--text-muted); }

/* ── New thread modal ────────────────────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  width: 440px;
  max-width: 90vw;
}

.modal h2 {
  font-size: 16px;
  margin-bottom: 16px;
}

.modal label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-dim);
  margin-bottom: 4px;
  margin-top: 12px;
}

.modal input, .modal textarea, .modal select {
  width: 100%;
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
  outline: none;
}
.modal input:focus, .modal textarea:focus, .modal select:focus {
  border-color: var(--accent);
}

.modal textarea { min-height: 80px; resize: vertical; }

.modal-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 20px;
}

.btn-cancel {
  background: transparent;
  color: var(--text-dim);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
}

/* ── Scrollbar ───────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* ── Connection status ───────────────────────────────────────── */
.conn-status {
  font-size: 11px;
  padding: 4px 10px;
  display: flex;
  align-items: center;
  gap: 5px;
}
.conn-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.conn-dot.connected { background: var(--complete); }
.conn-dot.disconnected { background: #ef4444; }
.conn-dot.connecting { background: var(--sent); }
</style>
</head>
<body>

<div class="app">
  <!-- Sidebar -->
  <div class="sidebar">
    <div class="sidebar-header">
      <h1>DoPeJarMo</h1>
      <button class="btn-new" onclick="showNewThread()">+ New</button>
    </div>
    <div id="thread-list" class="thread-list"></div>
    <div class="conn-status">
      <span id="conn-dot" class="conn-dot connecting"></span>
      <span id="conn-text" style="color:var(--text-muted)">Connecting...</span>
    </div>
  </div>

  <!-- Main -->
  <div class="main">
    <div id="chat-header" class="chat-header" style="display:none">
      <div>
        <div id="chat-title" class="chat-title"></div>
        <div id="chat-participants" class="chat-participants"></div>
      </div>
    </div>
    <div id="messages" class="messages">
      <div class="empty-state">
        <div>
          <p>Select a conversation or start a new one</p>
          <div class="hint">Messages appear in real-time via WebSocket</div>
        </div>
      </div>
    </div>
    <div id="input-bar" class="input-bar" style="display:none">
      <div class="input-row">
        <div class="input-wrapper">
          <div class="input-controls">
            <select id="route-select" class="route-select" onchange="handleRouteChange(this.value)"></select>
            <input type="hidden" id="type-select" value="prompt">
          </div>
          <textarea id="msg-input" placeholder="Type a message..." rows="1"></textarea>
        </div>
        <button id="btn-send" class="btn-send" onclick="sendMessage()">Send</button>
      </div>
    </div>
  </div>
</div>

<!-- New Thread Modal -->
<div id="new-thread-modal" class="modal-overlay" style="display:none" onclick="if(event.target===this)hideNewThread()">
  <div class="modal">
    <h2>New Conversation</h2>
    <label>Send to</label>
    <select id="new-to"></select>
    <label>Type</label>
    <select id="new-type">
      <option value="prompt">prompt</option>
      <option value="context">context</option>
      <option value="question">question</option>
      <option value="plan">plan</option>
      <option value="handoff">handoff</option>
    </select>
    <label>Summary</label>
    <input id="new-summary" placeholder="One-line description">
    <label>Content</label>
    <textarea id="new-content" placeholder="Full message..."></textarea>
    <div class="modal-actions">
      <button class="btn-cancel" onclick="hideNewThread()">Cancel</button>
      <button class="btn-new" onclick="createThread()">Send</button>
    </div>
  </div>
</div>

<script>
// ── State ───────────────────────────────────────────────────────
let ws_conn = null;
let threads = [];
let currentThread = null;
let currentMessages = [];
let targets = [];
let selectedRoute = 'any';
let routePinnedByUser = false;

const CLI_COLORS = {
  claude: '#a855f7', codex: '#22c55e', gemini: '#3b82f6',
  human: '#6366f1', system: '#6b7280',
};

function agentColor(agent, cli) {
  if (CLI_COLORS[cli]) return CLI_COLORS[cli];
  if (CLI_COLORS[agent]) return CLI_COLORS[agent];
  // Stable hash color for unknown agents
  let h = 0;
  for (let i = 0; i < agent.length; i++) h = agent.charCodeAt(i) + ((h << 5) - h);
  return `hsl(${Math.abs(h) % 360}, 60%, 55%)`;
}

function agentInitial(agent) {
  if (agent === 'human') return 'H';
  return (agent || '?')[0].toUpperCase();
}

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
  const now = new Date();
  const diff = now - d;
  if (diff < 86400000 && d.getDate() === now.getDate()) {
    return d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
  }
  return d.toLocaleDateString([], {month: 'short', day: 'numeric'}) + ' ' +
         d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
}

function shortTime(iso) {
  if (!iso) return '';
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return 'now';
  if (diff < 3600000) return Math.floor(diff/60000) + 'm';
  if (diff < 86400000) return Math.floor(diff/3600000) + 'h';
  return d.toLocaleDateString([], {month: 'short', day: 'numeric'});
}

// ── WebSocket ───────────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws_conn = new WebSocket(`${proto}//${location.host}/ws?token=`);

  ws_conn.onopen = () => {
    document.getElementById('conn-dot').className = 'conn-dot connected';
    document.getElementById('conn-text').textContent = 'Connected';
  };

  ws_conn.onclose = () => {
    document.getElementById('conn-dot').className = 'conn-dot disconnected';
    document.getElementById('conn-text').textContent = 'Disconnected';
    setTimeout(connectWS, 3000);
  };

  ws_conn.onerror = () => {
    document.getElementById('conn-dot').className = 'conn-dot disconnected';
    document.getElementById('conn-text').textContent = 'Error';
  };

  ws_conn.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === 'thread_list') {
      threads = data.threads;
      renderThreadList();
    } else if (data.type === 'thread_update') {
      if (currentThread === data.thread_id) {
        currentMessages = data.messages;
        renderMessages();
      }
      // Also refresh thread list
      fetchThreads();
    } else if (data.type === 'sent') {
      // Our own message was accepted
    }
  };
}

// ── Data fetching ───────────────────────────────────────────────
async function fetchThreads() {
  try {
    const r = await fetch('/api/threads');
    threads = await r.json();
    renderThreadList();
  } catch(e) {}
}

async function fetchTargets() {
  try {
    const r = await fetch('/api/targets');
    targets = await r.json();
    populateTargets();
  } catch(e) {}
}

function populateTargets() {
  const sel = document.getElementById('route-select');
  const newTo = document.getElementById('new-to');
  [sel, newTo].forEach(s => {
    s.innerHTML = '';
    targets.forEach(t => {
      const opt = document.createElement('option');
      opt.value = t;
      opt.textContent = t;
      s.appendChild(opt);
    });
  });
  applyRouteState();
}

function computeDefaultRoute() {
  for (let i = currentMessages.length - 1; i >= 0; i--) {
    const agent = currentMessages[i].from_agent || currentMessages[i].from_cli || '';
    if (agent && agent !== 'human') return agent;
  }
  const thread = threads.find(t => t.thread_id === currentThread);
  if (thread) {
    const nonHuman = (thread.participants || []).filter(p => p !== 'human');
    if (nonHuman.length) return nonHuman[0];
  }
  return 'any';
}

function applyRouteState() {
  if (!routePinnedByUser) {
    selectedRoute = computeDefaultRoute();
  }
  syncRouteSelect();
}

// ── Thread list rendering ───────────────────────────────────────
function renderThreadList() {
  const el = document.getElementById('thread-list');
  const active = threads.filter(t => t.has_active);
  const archive = threads.filter(t => !t.has_active);

  let html = '';

  if (active.length) {
    html += '<div class="sidebar-section">Active</div>';
    active.forEach(t => {
      html += renderThreadItem(t);
    });
  }

  if (archive.length) {
    html += '<div class="sidebar-section">Archive</div>';
    archive.forEach(t => {
      html += renderThreadItem(t);
    });
  }

  if (!threads.length) {
    html = '<div style="padding:20px;color:var(--text-muted);font-size:13px;text-align:center">No conversations yet</div>';
  }

  el.innerHTML = html;
}

function renderThreadItem(t) {
  const isActive = currentThread === t.thread_id;
  const dots = (t.participants || []).map(p => {
    const color = CLI_COLORS[p] || agentColor(p, '');
    return `<span class="participant-dot" style="background:${color}" title="${p}"></span>`;
  }).join('');

  return `
    <div class="thread-item ${isActive ? 'active' : ''}" onclick="openThread('${t.thread_id}')">
      <div class="thread-summary">
        ${t.has_active ? '<span class="active-badge"></span>' : ''}
        ${escHtml(t.summary || t.thread_id)}
      </div>
      <div class="thread-meta">
        <span class="thread-participants">${dots}</span>
        <span>${t.message_count} msg${t.message_count !== 1 ? 's' : ''}</span>
        <span>${shortTime(t.latest)}</span>
      </div>
    </div>
  `;
}

// ── Open thread ─────────────────────────────────────────────────
async function openThread(tid) {
  // Unsubscribe old
  if (currentThread && ws_conn && ws_conn.readyState === 1) {
    ws_conn.send(JSON.stringify({action: 'unsubscribe', thread_id: currentThread}));
  }

  currentThread = tid;
  routePinnedByUser = false;
  renderThreadList();

  // Subscribe via WebSocket
  if (ws_conn && ws_conn.readyState === 1) {
    ws_conn.send(JSON.stringify({action: 'subscribe', thread_id: tid}));
  }

  // Also fetch via REST as backup
  try {
    const r = await fetch(`/api/thread/${tid}`);
    currentMessages = await r.json();
    renderMessages();
  } catch(e) {}

  // Show input bar
  document.getElementById('input-bar').style.display = '';
  document.getElementById('chat-header').style.display = '';

  // Update header
  const thread = threads.find(t => t.thread_id === tid);
  if (thread) {
    document.getElementById('chat-title').textContent = thread.summary || tid;
    document.getElementById('chat-participants').textContent = (thread.participants || []).join(', ');
  }
  applyRouteState();
}

// ── Message rendering ───────────────────────────────────────────
function renderMessages() {
  const el = document.getElementById('messages');
  if (!currentMessages.length) {
    el.innerHTML = '<div class="empty-state"><div>No messages in this thread</div></div>';
    return;
  }

  let html = '';
  let lastAgent = null;

  currentMessages.forEach(m => {
    const agent = m.from_agent || m.from_cli || '?';
    const cli = m.from_cli || '';
    const color = agentColor(agent, cli);
    const initial = agentInitial(agent);
    const time = formatTime(m.created_at);
    const status = m.status || '';
    const content = m.content || m.summary || '';

    html += `
      <div class="msg-group">
        <div class="msg-avatar" style="background:${color}">${initial}</div>
        <div class="msg-body">
          <div class="msg-header">
            <span class="msg-author" style="color:${color}">${escHtml(agent)}</span>
            <span class="msg-time">${time}</span>
            ${status ? `<span class="msg-status ${status}">${status}</span>` : ''}
          </div>
          <div class="msg-content">${escHtml(content)}</div>
          <div class="msg-type">${m.type || ''}${m.to ? ' → ' + escHtml(m.to) : ''}</div>
        </div>
      </div>
    `;
    lastAgent = agent;
  });

  el.innerHTML = html;
  el.scrollTop = el.scrollHeight;
  applyRouteState();
}

function handleRouteChange(value) {
  selectedRoute = value || 'any';
  routePinnedByUser = true;
  syncRouteSelect();
}

function syncRouteSelect() {
  const sel = document.getElementById('route-select');
  if (!sel) return;
  if (sel.querySelector(`option[value="${selectedRoute}"]`)) {
    sel.value = selectedRoute;
    return;
  }
  if (sel.querySelector('option[value="any"]')) {
    selectedRoute = 'any';
    sel.value = 'any';
    return;
  }
  if (sel.options.length) {
    selectedRoute = sel.options[0].value;
    sel.value = selectedRoute;
  }
}

async function sendMessage() {
  const input = document.getElementById('msg-input');
  const content = input.value.trim();
  if (!content || !currentThread) return;

  const to = routePinnedByUser ? selectedRoute : '';
  const type = document.getElementById('type-select').value;
  const lastMsg = currentMessages[currentMessages.length - 1];
  const replyTo = lastMsg ? lastMsg.id : '';

  // Send via WebSocket if connected
  if (ws_conn && ws_conn.readyState === 1) {
    ws_conn.send(JSON.stringify({
      action: 'send',
      content: content,
      to: to,
      type: type,
      reply_to: replyTo,
      summary: content.substring(0, 80),
    }));
  } else {
    // Fallback to REST
    await fetch('/api/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        content: content,
        to: to,
        type: type,
        reply_to: replyTo,
        summary: content.substring(0, 80),
      }),
    });
  }

  input.value = '';
  autoResize(input);
}

// ── New thread ──────────────────────────────────────────────────
function showNewThread() {
  document.getElementById('new-thread-modal').style.display = '';
  document.getElementById('new-summary').focus();
}

function hideNewThread() {
  document.getElementById('new-thread-modal').style.display = 'none';
  document.getElementById('new-summary').value = '';
  document.getElementById('new-content').value = '';
}

async function createThread() {
  const to = document.getElementById('new-to').value;
  const type = document.getElementById('new-type').value;
  const summary = document.getElementById('new-summary').value.trim();
  const content = document.getElementById('new-content').value.trim();

  if (!summary || !content) {
    alert('Summary and content are required');
    return;
  }

  try {
    const r = await fetch('/api/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({to, type, summary, content}),
    });
    const item = await r.json();
    hideNewThread();
    await fetchThreads();
    openThread(item.thread_id || item.id);
  } catch(e) {
    alert('Failed to create conversation');
  }
}

// ── Utilities ───────────────────────────────────────────────────
function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

// ── Keyboard shortcuts ──────────────────────────────────────────
document.getElementById('msg-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

document.getElementById('msg-input').addEventListener('input', function() {
  autoResize(this);
});

// ── Init ────────────────────────────────────────────────────────
fetchTargets();
fetchThreads();
connectWS();
</script>

</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    from starlette.responses import HTMLResponse as SHTMLResponse
    return SHTMLResponse(
        content=CHAT_HTML,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


# ── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    await manager.start_polling()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DoPeJarMo Chat")
    parser.add_argument("--port", type=int, default=8503)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
