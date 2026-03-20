"""
Brain Factory Portal — Streamlit viewer for sawmill runs, architecture, and conversations.

Reads the same files agents read. No transformation layer. What you see is what they see.

Usage:
    streamlit run portal.py
"""

import json
import pathlib
import datetime
import subprocess
import yaml

import streamlit as st

# ── Paths ─────────────────────────────────────────────────────────────────────
BRAIN = pathlib.Path(__file__).parent
SAWMILL = BRAIN / "sawmill"
ARCHITECTURE = BRAIN / "architecture"
AGENTS = BRAIN / ".claude" / "agents"
HOLDOUTS = BRAIN / ".holdouts"
DOPEJAR = pathlib.Path.home() / "dopejar"
CLAUDE_TRANSCRIPTS = pathlib.Path.home() / ".claude" / "projects" / "-Users-raymondbruni-Cowork-Brain-Factory"
CODEX_SESSIONS = pathlib.Path.home() / ".codex" / "sessions"
CODEX_INDEX = pathlib.Path.home() / ".codex" / "session_index.jsonl"
GEMINI_CHATS = pathlib.Path.home() / ".gemini" / "tmp"

# Backstage catalog files
CATALOG_FILES = [
    DOPEJAR / "catalog-info.yaml",
    DOPEJAR / "platform_sdk" / "catalog-info.yaml",
    DOPEJAR / "examples" / "org.yaml",
    BRAIN / "catalog-info.yaml",
]

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Brain Factory",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ══════════════════════════════════════════════════════════════════════════════
# ALL HELPER / DATA FUNCTIONS (defined before page routing)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=5)
def read_file(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"⚠ Could not read {path}: {e}"


def read_json(path: pathlib.Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_jsonl(path: pathlib.Path) -> list[dict]:
    lines = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    lines.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return lines


def file_mtime(path: pathlib.Path) -> datetime.datetime:
    try:
        return datetime.datetime.fromtimestamp(path.stat().st_mtime)
    except Exception:
        return datetime.datetime.min


def format_mtime(path: pathlib.Path) -> str:
    dt = file_mtime(path)
    if dt == datetime.datetime.min:
        return "?"
    return dt.strftime("%Y-%m-%d %H:%M")


def discover_frameworks() -> list[str]:
    return sorted(
        d.name for d in SAWMILL.iterdir()
        if d.is_dir() and d.name.startswith("FMWK-")
    )


def discover_runs(fw: str) -> list[pathlib.Path]:
    runs_dir = SAWMILL / fw / "runs"
    if not runs_dir.exists():
        return []
    return sorted(runs_dir.iterdir(), reverse=True)


def format_timestamp(ts: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ts


# ── Git helpers ───────────────────────────────────────────────────────────────

def git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=str(BRAIN),
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout
    except Exception as e:
        return f"⚠ git error: {e}"


@st.cache_data(ttl=10)
def git_log(n: int = 30) -> list[dict]:
    raw = git("log", f"-{n}", "--format=%H\t%aI\t%an\t%s")
    commits = []
    for line in raw.strip().splitlines():
        parts = line.split("\t", 3)
        if len(parts) == 4:
            commits.append({"hash": parts[0], "date": parts[1], "author": parts[2], "subject": parts[3]})
    return commits


@st.cache_data(ttl=10)
def git_diff_stat(ref: str = "HEAD") -> str:
    return git("diff", "--stat", ref)


@st.cache_data(ttl=10)
def git_working_changes() -> tuple[list[dict], list[dict]]:
    staged_raw = git("diff", "--cached", "--name-status")
    unstaged_raw = git("diff", "--name-status")
    untracked_raw = git("ls-files", "--others", "--exclude-standard")

    def parse(raw):
        files = []
        for line in raw.strip().splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                files.append({"status": parts[0], "path": parts[1]})
        return files

    staged = parse(staged_raw)
    unstaged = parse(unstaged_raw)
    for path in untracked_raw.strip().splitlines():
        if path.strip():
            unstaged.append({"status": "?", "path": path.strip()})
    return staged, unstaged


@st.cache_data(ttl=10)
def git_show_commit(sha: str) -> str:
    return git("show", "--stat", "--format=full", sha)


@st.cache_data(ttl=10)
def git_diff_file(path: str) -> str:
    return git("diff", "--", path)


# ── Backstage catalog ────────────────────────────────────────────────────────

@st.cache_data(ttl=10)
def load_catalog_entities() -> list[dict]:
    """Load all Backstage entities from catalog YAML files on disk."""
    entities = []
    for cat_file in CATALOG_FILES:
        if not cat_file.exists():
            continue
        try:
            content = cat_file.read_text(encoding="utf-8")
            for doc in yaml.safe_load_all(content):
                if doc and isinstance(doc, dict) and "kind" in doc:
                    doc["_source_file"] = str(cat_file)
                    entities.append(doc)
        except Exception:
            pass
    return entities


def get_api_spec_content(entity: dict):
    """Resolve an API entity's definition — inline or $text file reference."""
    defn = entity.get("spec", {}).get("definition")
    if not defn:
        return None
    if isinstance(defn, str):
        return defn
    if isinstance(defn, dict) and "$text" in defn:
        ref = defn["$text"]
        source = pathlib.Path(entity.get("_source_file", ""))
        spec_path = source.parent / ref
        if spec_path.exists():
            return spec_path.read_text(encoding="utf-8")
        return f"⚠ Spec file not found: {spec_path}"
    return str(defn)


# ── Transcript discovery (all 3 CLIs) ────────────────────────────────────────

@st.cache_data(ttl=10)
def discover_claude_sessions() -> list[dict]:
    index = []
    if not CLAUDE_TRANSCRIPTS.exists():
        return index
    for f in sorted(CLAUDE_TRANSCRIPTS.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        first_user_msg = ""
        timestamp = ""
        for line in f.read_text().splitlines()[:20]:
            try:
                rec = json.loads(line)
                if rec.get("type") == "user":
                    msg = rec.get("message", {})
                    content = msg.get("content", "")
                    if isinstance(content, str) and content:
                        first_user_msg = content[:80]
                    timestamp = rec.get("timestamp", "")
                    break
            except Exception:
                pass
        index.append({"cli": "claude", "path": str(f), "session": f.stem[:8],
                       "preview": first_user_msg or "(no preview)", "timestamp": timestamp})
    return index


@st.cache_data(ttl=10)
def discover_codex_sessions() -> list[dict]:
    index = []
    if not CODEX_SESSIONS.exists():
        return index
    for f in sorted(CODEX_SESSIONS.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        first_user_msg = ""
        timestamp = ""
        cwd = ""
        for line in f.read_text().splitlines()[:30]:
            try:
                rec = json.loads(line)
                if rec.get("type") == "session_meta":
                    timestamp = rec.get("payload", {}).get("timestamp", rec.get("timestamp", ""))
                    cwd = rec.get("payload", {}).get("cwd", "")
                if rec.get("type") == "response_item":
                    payload = rec.get("payload", {})
                    if payload.get("role") == "user":
                        for block in payload.get("content", []):
                            text = block.get("text", "")
                            if text and not text.startswith("<") and len(text) > 5:
                                first_user_msg = text[:80]
                                break
                    if first_user_msg:
                        break
            except Exception:
                pass
        index.append({"cli": "codex", "path": str(f), "session": f.stem[:20],
                       "preview": first_user_msg or cwd or "(no preview)", "timestamp": timestamp})
    return index


@st.cache_data(ttl=10)
def discover_gemini_sessions() -> list[dict]:
    index = []
    if not GEMINI_CHATS.exists():
        return index
    for f in sorted(GEMINI_CHATS.rglob("chats/session-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        first_user_msg = ""
        timestamp = ""
        project = f.parent.parent.name
        try:
            data = json.loads(f.read_text())
            timestamp = data.get("startTime", "")
            for msg in data.get("messages", []):
                if msg.get("type") == "user":
                    for block in msg.get("content", []):
                        text = block.get("text", "")
                        if text and len(text) > 3:
                            first_user_msg = text[:80]
                            break
                    if first_user_msg:
                        break
        except Exception:
            pass
        index.append({"cli": "gemini", "path": str(f), "session": f.stem[:20],
                       "preview": first_user_msg or f"({project})", "timestamp": timestamp, "project": project})
    return index


# ── Transcript renderers ─────────────────────────────────────────────────────

def render_claude_transcript(path: str, reverse: bool = False):
    records = read_jsonl(pathlib.Path(path))
    if reverse:
        records = list(reversed(records))
    for rec in records:
        rtype = rec.get("type", "")
        msg = rec.get("message", {})
        if rtype == "user":
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                with st.chat_message("user"):
                    st.markdown(content)
        elif rtype == "assistant":
            content_blocks = msg.get("content", [])
            text_parts, tool_parts = [], []
            for block in content_blocks:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_parts.append(block)
                elif isinstance(block, str):
                    text_parts.append(block)
            if text_parts:
                with st.chat_message("assistant"):
                    st.markdown("\n".join(text_parts))
            for tool in tool_parts:
                with st.expander(f"🔧 {tool.get('name', 'tool')}"):
                    st.json(tool.get("input", {}))
        elif rtype == "tool_result":
            content = rec.get("content", "")
            if content and isinstance(content, str):
                with st.expander("📎 Tool result"):
                    st.code(content[:2000], language="text")


def render_codex_transcript(path: str, reverse: bool = False):
    records = read_jsonl(pathlib.Path(path))
    if reverse:
        records = list(reversed(records))
    for rec in records:
        rtype = rec.get("type", "")
        payload = rec.get("payload", {})
        if rtype == "response_item":
            role = payload.get("role", "")
            content_blocks = payload.get("content", [])
            if role in ("user", "developer"):
                text_parts = [b.get("text", "") for b in content_blocks
                              if b.get("text") and not b["text"].startswith("<permissions") and not b["text"].startswith("<instructions")]
                if text_parts:
                    with st.chat_message("user"):
                        st.markdown("\n".join(text_parts))
            elif role == "assistant":
                text_parts, tool_parts = [], []
                for block in content_blocks:
                    btype = block.get("type", "")
                    if btype == "output_text":
                        text_parts.append(block.get("text", ""))
                    elif btype in ("tool_call", "function_call"):
                        tool_parts.append(block)
                if text_parts:
                    with st.chat_message("assistant"):
                        st.markdown("\n".join(text_parts))
                for tool in tool_parts:
                    name = tool.get("name", tool.get("function", {}).get("name", "tool"))
                    with st.expander(f"🔧 {name}"):
                        args = tool.get("arguments", tool.get("function", {}).get("arguments", ""))
                        if isinstance(args, str):
                            try:
                                st.json(json.loads(args))
                            except Exception:
                                st.code(args[:2000], language="text")
                        else:
                            st.json(args)
        elif rtype == "event_msg":
            etype = payload.get("type", "")
            if etype in ("task_started", "task_complete"):
                st.caption(f"⚡ {etype}")


def render_gemini_transcript(path: str, reverse: bool = False):
    try:
        data = json.loads(pathlib.Path(path).read_text())
    except Exception:
        st.error(f"Could not read {path}")
        return
    messages = data.get("messages", [])
    if reverse:
        messages = list(reversed(messages))
    for msg in messages:
        mtype = msg.get("type", "")
        content_blocks = msg.get("content", [])
        if mtype == "user":
            text_parts = [b.get("text", "") for b in content_blocks if b.get("text")]
            if text_parts:
                with st.chat_message("user"):
                    st.markdown("\n".join(text_parts))
        elif mtype == "model":
            text_parts, tool_parts = [], []
            for block in content_blocks:
                if "text" in block:
                    text_parts.append(block["text"])
                elif "functionCall" in block:
                    tool_parts.append(block["functionCall"])
            if text_parts:
                with st.chat_message("assistant"):
                    st.markdown("\n".join(text_parts))
            for tool in tool_parts:
                with st.expander(f"🔧 {tool.get('name', 'tool')}"):
                    st.json(tool.get("args", {}))
        elif mtype == "tool":
            for block in content_blocks:
                if "functionResponse" in block:
                    resp = block["functionResponse"]
                    with st.expander(f"📎 {resp.get('name', 'result')}"):
                        result = resp.get("response", {})
                        st.json(result) if isinstance(result, dict) else st.code(str(result)[:2000])


# ── File rendering helper ────────────────────────────────────────────────────

def render_file(full_path: pathlib.Path, rel_label: str = ""):
    content = read_file(full_path)
    size = len(content)
    label = rel_label or full_path.name
    mtime = format_mtime(full_path)
    st.markdown(f"**Reading:** `{label}` ({size:,} bytes) — modified {mtime}")
    if full_path.suffix == ".json":
        try:
            st.json(json.loads(content))
        except Exception:
            st.code(content, language="json")
    elif full_path.suffix in (".yaml", ".yml"):
        st.code(content, language="yaml")
    elif full_path.suffix in (".py",):
        st.code(content, language="python")
    elif full_path.suffix in (".sh",):
        st.code(content, language="bash")
    elif full_path.suffix in (".js", ".ts", ".tsx"):
        st.code(content, language=full_path.suffix.lstrip("."))
    elif full_path.suffix == ".md":
        st.markdown(content)
        with st.expander("Raw"):
            st.code(content, language="markdown")
    elif full_path.suffix == ".jsonl":
        st.code(content[:5000], language="json")
        if size > 5000:
            st.caption(f"(showing first 5,000 of {size:,} bytes)")
    else:
        st.code(content, language="text")


# ── Activity Feed helpers ─────────────────────────────────────────────────────

@st.cache_data(ttl=10)
def discover_all_runs():
    """Lightweight index of all sawmill runs — just metadata, no events loaded."""
    runs = []
    for fw_dir in SAWMILL.iterdir():
        if not fw_dir.is_dir() or not fw_dir.name.startswith("FMWK-"):
            continue
        runs_dir = fw_dir / "runs"
        if not runs_dir.exists():
            continue
        for run_dir in sorted(runs_dir.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue
            status_file = run_dir / "status.json"
            run_status = read_json(status_file) if status_file.exists() else {}
            events_file = run_dir / "events.jsonl"
            # Count events without parsing
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
                "path": str(run_dir),
                "state": run_status.get("state", "?"),
                "event_count": event_count,
                "timestamp": first_ts,
            })
    runs.sort(key=lambda r: r.get("timestamp", "0"), reverse=True)
    return runs


@st.cache_data(ttl=10)
def load_run_events(run_path):
    """Load events for a single run — called only when that run is displayed."""
    events_file = pathlib.Path(run_path) / "events.jsonl"
    status_file = pathlib.Path(run_path) / "status.json"
    run_status = read_json(status_file) if status_file.exists() else {}
    fw_name = pathlib.Path(run_path).parent.parent.name
    events = []
    if not events_file.exists():
        return events
    for line in events_file.read_text().splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
            events.append({
                "type": "sawmill",
                "timestamp": ev.get("timestamp", ""),
                "summary": ev.get("summary", ""),
                "event_type": ev.get("event_type", ""),
                "role": ev.get("role", ""),
                "turn": ev.get("turn", ""),
                "run_id": ev.get("run_id", ""),
                "framework": fw_name,
                "event_id": ev.get("event_id", ""),
                "parent_id": ev.get("causal_parent_event_id"),
                "outcome": ev.get("outcome", ""),
                "evidence_refs": ev.get("evidence_refs", []),
                "contract_refs": ev.get("contract_refs", []),
                "run_state": run_status.get("state", "?"),
                "raw": ev,
            })
        except Exception:
            pass
    return events


# ── Event classification for Activity Feed ───────────────────────────────────

SIGNIFICANT_EVENTS = {
    "run_started", "preflight_passed", "preflight_failed",
    "turn_started", "prompt_rendered", "agent_invoked", "agent_exited",
    "output_verified", "evidence_validated", "gate_passed",
    "turn_completed", "turn_failed",
    "run_completed", "run_failed",
    "review_verdict_recorded", "evaluation_verdict_recorded",
    "retry_started",
}

NOISE_EVENTS = {"agent_liveness_observed"}


def classify_events(events):
    """Split events into significant and noise (heartbeat spam)."""
    significant = []
    noise = []
    for ev in events:
        if ev.get("event_type") in NOISE_EVENTS:
            noise.append(ev)
        else:
            significant.append(ev)
    return significant, noise


def aggregate_heartbeats(noise_events):
    """Aggregate heartbeat noise into one summary per step."""
    by_step = {}
    for ev in noise_events:
        step = ev.get("raw", {}).get("step", ev.get("turn", "?"))
        role = ev.get("role", "?")
        key = f"{step}:{role}"
        if key not in by_step:
            by_step[key] = {
                "step": step,
                "role": role,
                "count": 0,
                "progress_count": 0,
                "first_ts": ev.get("timestamp", ""),
                "last_ts": ev.get("timestamp", ""),
                "last_summary": "",
            }
        by_step[key]["count"] += 1
        by_step[key]["last_ts"] = ev.get("timestamp", "")
        summary = ev.get("summary", "")
        by_step[key]["last_summary"] = summary
        if "progressing" in summary or "progress" in summary:
            by_step[key]["progress_count"] += 1
    return list(by_step.values())


def compute_duration(start_ts, end_ts):
    """Compute human-readable duration between two ISO timestamps."""
    try:
        start = datetime.datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
        end = datetime.datetime.fromisoformat(end_ts.replace("Z", "+00:00"))
        delta = end - start
        secs = int(delta.total_seconds())
        if secs < 60:
            return f"{secs}s"
        elif secs < 3600:
            return f"{secs // 60}m {secs % 60}s"
        else:
            return f"{secs // 3600}h {(secs % 3600) // 60}m"
    except Exception:
        return "?"


def clean_preview(text):
    """Clean up conversation preview text — strip prompt fragments and formatting artifacts."""
    if not text:
        return "(no preview)"
    # Strip leading underscores, markdown artifacts
    text = text.strip().strip("_").strip()
    # Truncate at first newline
    if "\n" in text:
        text = text.split("\n")[0].strip()
    # Strip common prompt prefixes
    for prefix in ["# AGENTS.md", "<INSTRUCT", "<local-command", "YOUR TASK:", "YOU ARE THE"]:
        if text.startswith(prefix):
            text = text[:60] + "…"
            break
    # Limit length
    if len(text) > 80:
        text = text[:77] + "…"
    return text or "(no preview)"


def render_conversation_inline(path, cli, key_prefix):
    """Render a conversation transcript inline when clicked."""
    p = pathlib.Path(path)
    if not p.exists():
        st.warning(f"File not found: {path}")
        return
    if cli == "claude":
        render_claude_transcript(path, reverse=True)
    elif cli == "codex":
        render_codex_transcript(path, reverse=True)
    elif cli == "gemini":
        render_gemini_transcript(path, reverse=True)


def render_artifact_links(refs, label, key_prefix):
    """Render file references as expanders — no rerun needed."""
    if not refs:
        return
    st.markdown(f"**{label}:**")
    for ref in refs:
        p = BRAIN / ref
        if p.exists() and p.is_file():
            with st.expander(f"📄 {ref}"):
                render_file(p, ref)
        else:
            st.caption(f"  `{ref}` _(not on disk)_")


def build_trace_tree(events):
    """Build parent→children map from sawmill events for trace tree view."""
    by_id = {}
    children = {}
    roots = []
    for ev in events:
        eid = ev.get("event_id", "")
        pid = ev.get("parent_id")
        by_id[eid] = ev
        if pid and pid in by_id:
            children.setdefault(pid, []).append(eid)
        else:
            roots.append(eid)
    return by_id, children, roots


def render_trace_node(eid, by_id, children, depth=0):
    """Recursively render a trace tree node with visual tree lines."""
    ev = by_id.get(eid, {})
    etype = ev.get("event_type", "?")
    role = ev.get("role", "?")
    summary = ev.get("summary", "")
    outcome = ev.get("outcome", "")
    ts = format_timestamp(ev.get("timestamp", ""))
    time_only = ts[11:19] if len(ts) > 11 else ""

    icon = {"run_started": "🚀", "preflight_passed": "✅", "turn_started": "▶️",
            "prompt_rendered": "📝", "agent_invoked": "🤖", "evidence_validated": "🔍",
            "gate_passed": "🚪", "turn_completed": "✔️", "run_completed": "🏁",
            "turn_failed": "❌", "run_failed": "❌"}.get(etype, "•")

    ob = ""
    if outcome == "failed":
        ob = " 🔴"
    elif outcome in ("passed", "complete"):
        ob = " 🟢"

    # Visual tree prefix
    prefix = "  " * depth
    if depth > 0:
        prefix = "│ " * (depth - 1) + "├─"

    has_refs = ev.get("evidence_refs") or ev.get("contract_refs")

    # Render the node — if it has refs, make it expandable; otherwise just a line
    if has_refs:
        with st.expander(f"`{prefix}` {icon} `{time_only}` **{etype}** ({role}){ob} — {summary}"):
            render_artifact_links(ev.get("evidence_refs", []), "Evidence", f"trace_ev_{eid[:8]}")
            render_artifact_links(ev.get("contract_refs", []), "Contracts", f"trace_cr_{eid[:8]}")
    else:
        st.markdown(f"`{prefix}` {icon} `{time_only}` **{etype}** ({role}){ob} — {summary}")

    # Render children
    for child_id in children.get(eid, []):
        render_trace_node(child_id, by_id, children, depth + 1)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.title("Brain Factory")

page = st.sidebar.radio(
    "Navigate",
    [
        "📋 Workspace",
        "📊 Activity Feed",
        "🔄 Latest Changes",
        "🏭 Sawmill Runs",
        "📐 Architecture",
        "🤖 Agent Roles",
        "🏗️ System Catalog",
        "💬 Conversations",
        "📁 File Explorer",
    ],
    label_visibility="collapsed",
)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Workspace
# ══════════════════════════════════════════════════════════════════════════════
if page == "📋 Workspace":
    import workspace as ws

    st.title("Workspace")
    st.caption("Shared surface for cross-agent conversations. Send prompts, route work, read responses.")

    # ── New item form ─────────────────────────────────────────────────────
    with st.expander("➕ New Conversation", expanded=False):
        nc1, nc2 = st.columns(2)
        with nc1:
            new_type = st.selectbox("Type", list(ws.VALID_TYPES), key="new_type")
            new_to = st.multiselect("Send to", ws.get_routable_targets(), key="new_to")
        with nc2:
            new_summary = st.text_input("Summary", key="new_summary", placeholder="One-line description")
            new_tags = st.text_input("Tags (comma separated)", key="new_tags", placeholder="e.g. cleanup, review")
        new_content = st.text_area("Content", key="new_content", placeholder="Full prompt, plan, or instructions...", height=200)
        if st.button("📨 Send", key="send_new_item"):
            if new_summary and new_content and new_to:
                tags = [t.strip() for t in new_tags.split(",") if t.strip()] if new_tags else []
                ws.create_item(
                    item_type=new_type, from_cli="human", to=new_to,
                    summary=new_summary, content=new_content,
                    tags=tags, from_agent="human")
                st.rerun()
            else:
                st.warning("Summary, content, and recipient are required.")

    # ── Sidebar filters ───────────────────────────────────────────────────
    ws_status_filter = st.sidebar.selectbox("Status", ["all", "sent", "read", "complete"], key="ws_status")
    ws_type_filter = st.sidebar.selectbox("Type", ["all", "plan", "results", "review", "prompt", "handoff", "question", "context"], key="ws_type")

    # ── Summary metrics ───────────────────────────────────────────────────
    all_items = ws.list_items()
    agents = ws.list_agents()
    agent_counts = {}
    for it in all_items:
        fr = it.get("from_agent", it.get("from_cli", "?"))
        agent_counts[fr] = agent_counts.get(fr, 0) + 1
    total_comments = sum(len(ws.get_item(it.get("id", "")).get("comments", [])) for it in all_items)

    mcols = st.columns(4)
    mcols[0].metric("Conversations", len(all_items))
    mcols[1].metric("Messages", total_comments)
    mcols[2].metric("Agents", len(agents))
    mcols[3].metric("Active Tokens", len([t for t in ws.list_agent_tokens() if t.get("active")]))

    status_icons = {"sent": "📨", "read": "👁️", "complete": "✅", "pending": "📨", "approved": "📨", "in_progress": "👁️"}
    st.divider()

    cli_icon_map = {"claude": "🟣", "codex": "🟢", "gemini": "🔵", "human": "👤"}
    cli_avatar_map = {"claude": "🟣", "codex": "🟢", "gemini": "🔵", "human": "👤"}

    # ── Render as threads ────────────────────────────────────────────────
    threads = ws.list_threads()

    # Split active vs archive
    active_threads = []
    archive_threads = []
    for t in threads:
        has_active = any(it.get("status") in ("sent", "read") for it in t["items"])
        if has_active:
            active_threads.append(t)
        else:
            archive_threads.append(t)

    if active_threads:
        st.subheader(f"Active ({len(active_threads)})")

    if archive_threads:
        with st.expander(f"Archive ({len(archive_threads)} completed)"):
            for t in archive_threads:
                st.caption(f"💬 {t['summary'][:50]} — {', '.join(t['participants'])} · {t['latest'][:16]}")

    if active_threads:
        # Thread selector in sidebar
        thread_names = [f"{t['summary'][:40]} ({len(t['items'])} msgs)" for t in active_threads]
        selected_idx = st.sidebar.selectbox("Conversation", range(len(active_threads)),
            format_func=lambda i: thread_names[i], key="ws_thread_select")

        thread = active_threads[selected_idx]
        tid = thread["thread_id"]
        participants = ", ".join(thread["participants"])
        msg_count = thread["message_count"]

        st.markdown(f"**{thread['summary']}** — {participants} · {msg_count} messages")
        st.divider()

        # ── Chat messages (auto-refreshing fragment) ──────────────────
        @st.fragment(run_every=5)
        def render_chat():
            # Re-fetch thread on every fragment run
            fresh_thread = ws.get_thread(tid)
            for it in fresh_thread:
                from_agent = it.get("from_agent", it.get("from_cli", "?"))
                from_cli = it.get("from_cli", "?")
                content = it.get("content", "")
                summary = it.get("summary", "")
                created = it.get("created_at", "")[:16]
                status = it.get("status", "?")
                si = status_icons.get(status, "•")
                avatar = cli_avatar_map.get(from_cli, "🤖")

                role = "user" if from_agent == "human" else "assistant"
                with st.chat_message(role, avatar=avatar):
                    with st.expander(f"**{from_agent}** · {created} · {si}", expanded=True):
                        st.markdown(content or summary)

        render_chat()

        # ── Reply controls ────────────────────────────────────────────
        st.divider()
        default_route = [p for p in thread["participants"] if p != "human"]
        route_to = st.multiselect("Route to", ws.get_routable_targets(), default=default_route, key=f"route_{tid}")

        last_item = thread["items"][-1] if thread["items"] else None
        last_id = last_item.get("id", "") if last_item else ""

        if reply_text := st.chat_input("Type a message...", key=f"chat_{tid}"):
            to_str = ",".join(route_to) if route_to else "any"
            ws.create_item(
                item_type="prompt", from_cli="human", to=to_str,
                summary=reply_text[:80], content=reply_text,
                from_agent="human", reply_to=last_id)
            st.rerun()

    elif not archive_threads:
        st.info("No conversations yet. Create one above or tell an agent to post to the workspace.")

    # ── Invite Tokens ─────────────────────────────────────────────────────
    st.divider()
    with st.expander("🔑 Agent Tokens"):
        st.caption("Create tokens for agents. One token = one agent identity. Revoke to disable, reactivate to re-enable.")
        col1, col2 = st.columns([3, 1])
        with col1:
            token_label = st.text_input("Label", placeholder="e.g. gemini-reviewer", key="token_label")
        with col2:
            st.markdown("")
            st.markdown("")
            if st.button("Create Token", key="create_token"):
                if token_label:
                    result = ws.create_token(token_label)
                    st.success(f"Token created: `{result['token']}`")
                    st.code(f"Register at mcp.dopejarmo.com/onboard with token: {result['token']}")
                    st.rerun()

        tokens = ws.list_agent_tokens()
        if tokens:
            for tok in tokens:
                token = tok.get("token", "")
                label = tok.get("label", "")
                name = tok.get("name", "")
                active = tok.get("active", True)
                cli = tok.get("cli", "")
                last_seen = tok.get("last_seen", "")

                badge = "🟢" if active else "🔴"
                seen = f" · Last seen: {last_seen[:16]}" if last_seen else ""
                cli_display = f" ({cli})" if cli else ""
                if name:
                    display = f"**{name}**{cli_display}{seen}"
                else:
                    display = f"**{label}** — not yet registered"

                st.markdown(f"  {badge} {display}")

                onboard_url = f"GET https://mcp.dopejarmo.com/onboard?token={token}"
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    st.code(onboard_url, language="text")
                with col2:
                    if active:
                        if st.button("Revoke", key=f"revoke_{token}"):
                            ws.revoke_token(token)
                            st.rerun()
                    else:
                        if st.button("Reactivate", key=f"reactivate_{token}"):
                            ws.reactivate_token(token)
                            st.rerun()
                with col3:
                    st.code(token, language="text")

    # ── Registered Agents ─────────────────────────────────────────────────
    agents = ws.list_agents()
    with st.expander(f"🤖 Registered Agents ({len(agents)})"):
        if agents:
            cli_icons_ws = {"claude": "🟣", "codex": "🟢", "gemini": "🔵"}
            for a in agents:
                ci = cli_icons_ws.get(a["cli"], "•")
                caps = ", ".join(a.get("capabilities", [])) if a.get("capabilities") else ""
                st.markdown(
                    f"{ci} **{a['name']}** ({a['cli']}) — {a['description']}  \n"
                    f"  _Last seen: {a.get('last_seen', '?')[:16]}_"
                    + (f" · Capabilities: {caps}" if caps else "")
                )
        else:
            st.caption("No agents registered yet. Create a token above, then tell the agent to register.")

    # ── Audit log ─────────────────────────────────────────────────────────
    with st.expander("📜 Audit Log"):
        log = ws.get_audit_log(limit=50)
        if log:
            for entry in log:
                ts = entry.get("timestamp", "")[:16]
                event = entry.get("event", "")
                actor = entry.get("actor", "")
                detail = entry.get("detail", "")
                iid = entry.get("item_id", "")[:8]
                st.markdown(f"`{ts}` **{event}** by {actor} on `{iid}…` — {detail}")
        else:
            st.caption("No audit events yet.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Activity Feed
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Activity Feed":
    st.title("Activity Feed")
    st.caption("Unified timeline — pipeline events, agent conversations, and code changes.")

    view_mode = st.sidebar.radio("View", ["Workflow", "Timeline", "Trace Tree"], key="feed_view")

    cli_icons_feed = {"claude": "🟣", "codex": "🟢", "gemini": "🔵"}
    event_icons = {
        "run_started": "🚀", "preflight_passed": "✅", "turn_started": "▶️",
        "prompt_rendered": "📝", "agent_invoked": "🤖", "evidence_validated": "🔍",
        "gate_passed": "🚪", "turn_completed": "✔️", "run_completed": "🏁",
        "turn_failed": "❌", "run_failed": "❌",
    }

    # ── Lightweight run index (no event loading yet) ──────────────────────
    all_runs = discover_all_runs()
    claude_s = discover_claude_sessions()
    codex_s = discover_codex_sessions()
    gemini_s = discover_gemini_sessions()
    all_convos = claude_s + codex_s + gemini_s
    all_commits = git_log(50)

    # Summary
    c1, c2, c3 = st.columns(3)
    c1.metric("🏭 Runs", len(all_runs))
    c2.metric("💬 Sessions", len(all_convos))
    c3.metric("🔀 Commits", len(all_commits))
    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    # VIEW: Workflow
    # ══════════════════════════════════════════════════════════════════════
    if view_mode == "Workflow":

        # ── Pipeline Runs (paginated at run level) ────────────────────────
        if all_runs:
            st.header("🏭 Pipeline Runs")
            runs_per_page = st.sidebar.slider("Runs per page", 5, 30, 10, key="wf_runs_per_page")
            total_runs = len(all_runs)
            run_page = st.sidebar.number_input("Run page", 1, max(1, (total_runs // runs_per_page) + 1), 1, key="wf_run_page")
            run_start = (run_page - 1) * runs_per_page
            page_runs = all_runs[run_start:run_start + runs_per_page]
            st.caption(f"Showing runs {run_start + 1}–{min(run_start + runs_per_page, total_runs)} of {total_runs}")

            for run_info in page_runs:
                rid = run_info["run_id"]
                fw = run_info["framework"]
                run_ts = format_timestamp(run_info.get("timestamp", ""))
                run_state = run_info.get("state", "?")
                ev_count = run_info.get("event_count", 0)
                state_icon = {"running": "🟡", "passed": "🟢", "failed": "🔴"}.get(run_state, "⚪")

                with st.expander(f"{state_icon} **{fw}** — `{rid[:16]}…` — {run_ts} — {ev_count} events"):
                    events = load_run_events(run_info["path"])
                    significant, noise = classify_events(events)
                    heartbeat_agg = aggregate_heartbeats(noise)

                    # ── Stage cards ───────────────────────────────────
                    turns = []
                    seen_turns = set()
                    for ev in events:
                        t = ev.get("turn", "")
                        if t and t not in seen_turns and t != "orchestrator":
                            seen_turns.add(t)
                            turn_outcome = "pending"
                            turn_role = ev.get("role", "")
                            turn_start = ""
                            turn_end = ""
                            for e2 in events:
                                if e2.get("turn") == t:
                                    if e2.get("event_type") == "turn_started":
                                        turn_start = e2.get("timestamp", "")
                                    if e2.get("event_type") in ("turn_completed", "turn_failed"):
                                        turn_outcome = "passed" if e2.get("event_type") == "turn_completed" else "failed"
                                        turn_end = e2.get("timestamp", "")
                            duration = compute_duration(turn_start, turn_end) if turn_start and turn_end else "..."
                            turns.append({"turn": t, "role": turn_role, "outcome": turn_outcome, "duration": duration})

                    if turns:
                        stage_cols = st.columns(len(turns))
                        for col, t in zip(stage_cols, turns):
                            with col:
                                bg = {"passed": "🟢", "failed": "🔴", "pending": "🟡"}.get(t["outcome"], "⚪")
                                st.markdown(f"### {bg} Turn {t['turn']}")
                                st.caption(f"{t['role']} · {t['duration']}")

                    # ── Run summary header ────────────────────────────
                    if events:
                        first_ts = events[0].get("timestamp", "")
                        last_ts = events[-1].get("timestamp", "")
                        total_duration = compute_duration(first_ts, last_ts)
                        current_turn = ""
                        current_role = ""
                        latest_failure = ""
                        for ev in reversed(events):
                            if ev.get("turn") and ev.get("turn") != "orchestrator" and not current_turn:
                                current_turn = ev.get("turn", "")
                                current_role = ev.get("role", "")
                            if ev.get("outcome") == "failed" and not latest_failure:
                                latest_failure = ev.get("summary", "")

                        hcol1, hcol2, hcol3, hcol4 = st.columns(4)
                        hcol1.metric("Duration", total_duration)
                        hcol2.metric("Events", f"{len(significant)} + {len(noise)} heartbeats")
                        hcol3.metric("Current", f"Turn {current_turn}" if current_turn else "—")
                        if latest_failure:
                            hcol4.metric("Last Error", latest_failure[:30])
                        else:
                            hcol4.metric("Status", run_state)

                    st.divider()

                    # ── Heartbeat summaries (aggregated) ──────────────
                    if heartbeat_agg:
                        for hb in heartbeat_agg:
                            duration = compute_duration(hb["first_ts"], hb["last_ts"])
                            st.markdown(
                                f"💓 **{hb['step']}** ({hb['role']}) — "
                                f"{hb['count']} heartbeats, {hb['progress_count']} progress signals, "
                                f"{duration}"
                            )

                    # ── Significant events ─────────────────────────────
                    st.subheader("Events")
                    for ev in significant:
                        etype = ev.get("event_type", "?")
                        ei = event_icons.get(etype, "•")
                        role = ev.get("role", "")
                        summary = ev.get("summary", "")
                        outcome = ev.get("outcome", "")
                        ts_raw = ev.get("timestamp", "")
                        time_only = format_timestamp(ts_raw)[11:19] if len(ts_raw) > 11 else ""
                        ob = " 🔴" if outcome == "failed" else (" 🟢" if outcome in ("passed", "complete") else "")
                        eid = ev.get("event_id", "")
                        has_refs = ev.get("evidence_refs") or ev.get("contract_refs")

                        line = f"{ei} `{time_only}` **{etype}** ({role}){ob} — {summary}"
                        if has_refs:
                            with st.expander(f"📎 {line}"):
                                render_artifact_links(ev.get("evidence_refs", []), "Evidence", f"wf_ev_{eid[:8]}")
                                render_artifact_links(ev.get("contract_refs", []), "Contracts", f"wf_cr_{eid[:8]}")
                        else:
                            st.markdown(line)

                    # ── Raw heartbeats behind expander ─────────────────
                    if noise:
                        with st.expander(f"💓 Show all {len(noise)} heartbeat events"):
                            for ev in noise:
                                ts_raw = ev.get("timestamp", "")
                                time_only = format_timestamp(ts_raw)[11:19] if len(ts_raw) > 11 else ""
                                st.caption(f"`{time_only}` {ev.get('summary', '')}")

        # ── Agent Sessions ────────────────────────────────────────────────
        st.header(f"💬 Agent Sessions ({len(all_convos)})")
        by_cli = {}
        for s in all_convos:
            by_cli.setdefault(s.get("cli", "?"), []).append(s)

        for cli_name, sessions in sorted(by_cli.items()):
            ci = cli_icons_feed.get(cli_name, "•")
            with st.expander(f"{ci} **{cli_name.title()}** — {len(sessions)} sessions"):
                pg_size = 25
                total_s = len(sessions)
                pg = st.number_input("Page", 1, max(1, (total_s // pg_size) + 1), 1, key=f"conv_pg_{cli_name}")
                start_s = (pg - 1) * pg_size
                st.caption(f"Showing {start_s + 1}–{min(start_s + pg_size, total_s)} of {total_s}")
                for idx, s in enumerate(sessions[start_s:start_s + pg_size]):
                    ts = format_timestamp(s.get("timestamp", ""))
                    preview = clean_preview(s.get("summary", ""))
                    session_id = s.get("session", "")
                    spath = s.get("path", "")
                    with st.expander(f"`{ts[:16]}` **{session_id}…** {preview}"):
                        render_conversation_inline(spath, cli_name, f"wf_{cli_name}_{start_s + idx}")

        # ── Git ───────────────────────────────────────────────────────────
        st.header(f"🔀 Git Commits ({len(all_commits)})")
        with st.expander(f"**{len(all_commits)} commits**"):
            for g in all_commits:
                ts = format_timestamp(g.get("date", ""))
                short = g.get("hash", "")[:8]
                subject = g.get("summary", "")
                author = g.get("author", "")
                st.markdown(f"  `{ts[:16]}` `{short}` {subject} — _{author}_")

    # ══════════════════════════════════════════════════════════════════════
    # VIEW: Trace Tree
    # ══════════════════════════════════════════════════════════════════════
    elif view_mode == "Trace Tree":
        st.subheader("Pipeline Trace Tree")
        st.caption("Parent → child execution flow. Expand nodes to see evidence and contracts.")

        if not all_runs:
            st.info("No pipeline runs found.")
            st.stop()

        runs_per_page = st.sidebar.slider("Runs per page", 5, 30, 10, key="tt_runs_per_page")
        total_runs = len(all_runs)
        run_page = st.sidebar.number_input("Run page", 1, max(1, (total_runs // runs_per_page) + 1), 1, key="tt_run_page")
        run_start = (run_page - 1) * runs_per_page
        page_runs = all_runs[run_start:run_start + runs_per_page]
        st.caption(f"Showing runs {run_start + 1}–{min(run_start + runs_per_page, total_runs)} of {total_runs}")

        for run_info in page_runs:
            rid = run_info["run_id"]
            fw = run_info["framework"]
            run_ts = format_timestamp(run_info.get("timestamp", ""))
            ev_count = run_info.get("event_count", 0)
            state = run_info.get("state", "?")
            si = {"running": "🟡", "passed": "🟢", "failed": "🔴"}.get(state, "⚪")

            with st.expander(f"{si} **{fw}** — `{rid[:16]}…` — {run_ts} — {ev_count} events"):
                events = load_run_events(run_info["path"])
                by_id, children_map, roots = build_trace_tree(events)
                for root_id in roots:
                    render_trace_node(root_id, by_id, children_map, depth=0)

    # ══════════════════════════════════════════════════════════════════════
    # VIEW: Timeline
    # ══════════════════════════════════════════════════════════════════════
    elif view_mode == "Timeline":
        # Build feed from paginated runs + all convos + all git
        runs_to_include = st.sidebar.slider("Runs to include", 1, len(all_runs) if all_runs else 1, min(5, len(all_runs)) if all_runs else 1, key="tl_runs")
        feed = []
        for run_info in all_runs[:runs_to_include]:
            feed.extend(load_run_events(run_info["path"]))
        for s in all_convos:
            feed.append({"type": "conversation", "timestamp": s.get("timestamp", ""),
                          "summary": s.get("preview", ""), "cli": s.get("cli", "?"),
                          "session": s.get("session", ""), "path": s.get("path", "")})
        for c in all_commits:
            feed.append({"type": "git", "timestamp": c.get("date", ""),
                          "summary": c.get("subject", ""), "author": c.get("author", ""),
                          "hash": c.get("hash", "")})
        feed.sort(key=lambda x: x.get("timestamp", "0"), reverse=True)

        page_size = 50
        total = len(feed)
        tl_page = st.sidebar.number_input("Page", 1, max(1, (total // page_size) + 1), 1, key="tl_page")
        start = (tl_page - 1) * page_size
        page_items = feed[start:start + page_size]
        st.caption(f"Showing {start + 1}–{min(start + page_size, total)} of {total}")

        current_date = ""
        for entry in page_items:
            ts = entry.get("timestamp", "")
            date_str = ts[:10] if len(ts) >= 10 else "Unknown"
            if date_str != current_date:
                current_date = date_str
                st.markdown(f"### {current_date}")

            etype = entry["type"]
            time_str = format_timestamp(ts)[11:19] if len(ts) > 11 else ""

            if etype == "sawmill":
                ev_type = entry.get("event_type", "")
                ei = event_icons.get(ev_type, "•")
                role = entry.get("role", "")
                summary = entry.get("summary", "")
                outcome = entry.get("outcome", "")
                turn = entry.get("turn", "")
                ob = " 🔴" if outcome == "failed" else (" 🟢" if outcome in ("passed", "complete") else "")
                eid = entry.get("event_id", "")
                header = f"🏭 `{time_str}` {ei} **{ev_type}** — {role}"
                if turn:
                    header += f" (Turn {turn})"
                header += ob
                has_refs = entry.get("evidence_refs") or entry.get("contract_refs")
                if has_refs:
                    with st.expander(f"📎 {header} — {summary}"):
                        render_artifact_links(entry.get("evidence_refs", []), "Evidence", f"tl_ev_{eid[:8]}")
                        render_artifact_links(entry.get("contract_refs", []), "Contracts", f"tl_cr_{eid[:8]}")
                else:
                    st.markdown(f"{header} — {summary}")

            elif etype == "conversation":
                cli = entry.get("cli", "?")
                ci = cli_icons_feed.get(cli, "•")
                preview = clean_preview(entry.get("summary", ""))
                session = entry.get("session", "")
                spath = entry.get("path", "")
                with st.expander(f"💬 `{time_str}` {ci} **{cli.title()}** `{session}…` — {preview}"):
                    render_conversation_inline(spath, cli, f"tl_{session}_{cli}")

            elif etype == "git":
                short = entry.get("hash", "")[:8]
                subject = entry.get("summary", "")
                st.markdown(f"🔀 `{time_str}` `{short}` — {subject}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Latest Changes
# ══════════════════════════════════════════════════════════════════════════════
if page == "🔄 Latest Changes":
    st.title("Latest Changes")
    st.caption("Live git state — uncommitted work and recent commits.")

    # ── File viewer (renders at top when a file is selected) ──────────
    if st.session_state.get("_view_file"):
        vf = st.session_state["_view_file"]
        vp = BRAIN / vf
        if vp.exists():
            if st.button("✕ Close file viewer"):
                del st.session_state["_view_file"]
                st.rerun()
            render_file(vp, vf)
            st.divider()
        else:
            del st.session_state["_view_file"]

    st.header("Working Tree")
    staged, unstaged = git_working_changes()

    if not staged and not unstaged:
        st.success("Clean working tree — no uncommitted changes.")
    else:
        status_icons = {"M": "✏️", "A": "➕", "D": "🗑️", "R": "🔄", "?": "🆕"}
        new_files = [f for f in unstaged if f["status"] == "?"]
        modified_files = [f for f in unstaged if f["status"] != "?"]

        if new_files:
            st.subheader(f"🆕 New Files ({len(new_files)})")
            new_files_with_time = []
            for f in new_files:
                p = BRAIN / f["path"]
                mt = format_mtime(p) if p.exists() else "?"
                new_files_with_time.append((f, mt, file_mtime(p) if p.exists() else datetime.datetime.min))
            new_files_with_time.sort(key=lambda x: x[2], reverse=True)
            for f, mt, _ in new_files_with_time:
                p = BRAIN / f["path"]
                col1, col2 = st.columns([5, 1])
                with col1:
                    if p.exists() and p.is_file():
                        if st.button(f"🆕 {f['path']}", key=f"new_{f['path']}"):
                            st.session_state["_view_file"] = f["path"]
                            st.rerun()
                    else:
                        st.text(f"  🆕  {f['path']}")
                with col2:
                    st.caption(mt)

        if staged:
            st.subheader(f"Staged ({len(staged)} files)")
            for f in staged:
                icon = status_icons.get(f["status"][0], "•")
                p = BRAIN / f["path"]
                if p.exists() and p.is_file() and f["status"] != "D":
                    if st.button(f"{icon} {f['status']}  {f['path']}", key=f"staged_{f['path']}"):
                        st.session_state["_view_file"] = f["path"]
                        st.rerun()
                else:
                    st.text(f"  {icon} {f['status']}  {f['path']}")

        if modified_files:
            st.subheader(f"Modified / Deleted ({len(modified_files)} files)")
            changes_sort = st.radio("Sort", ["By folder", "Newest first"], key="changes_sort", horizontal=True)

            if changes_sort == "Newest first":
                with_time = []
                for f in modified_files:
                    p = BRAIN / f["path"]
                    mt = file_mtime(p) if p.exists() else datetime.datetime.min
                    with_time.append((f, mt))
                with_time.sort(key=lambda x: x[1], reverse=True)
                for f, mt in with_time:
                    icon = status_icons.get(f["status"][0], "•")
                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        p = BRAIN / f["path"]
                        if p.exists() and p.is_file() and f["status"] != "D":
                            if st.button(f"{icon} {f['status']}  {f['path']}", key=f"mod_{f['path']}"):
                                st.session_state["_view_file"] = f["path"]
                                st.rerun()
                        else:
                            st.text(f"  {icon} {f['status']}  {f['path']}")
                    with col2:
                        st.caption(mt.strftime("%Y-%m-%d %H:%M") if mt != datetime.datetime.min else "?")
                    with col3:
                        if f["status"] != "D":
                            if st.button("diff", key=f"diff_{f['path']}"):
                                st.code(git_diff_file(f["path"]), language="diff")
            else:
                groups: dict[str, list[dict]] = {}
                for f in modified_files:
                    top = f["path"].split("/")[0] if "/" in f["path"] else "(root)"
                    groups.setdefault(top, []).append(f)
                for group, files in sorted(groups.items()):
                    with st.expander(f"**{group}/** — {len(files)} files"):
                        for f in files:
                            icon = status_icons.get(f["status"][0], "•")
                            p = BRAIN / f["path"]
                            mt = format_mtime(p) if p.exists() else "?"
                            col1, col2, col3 = st.columns([4, 1, 1])
                            with col1:
                                if p.exists() and p.is_file() and f["status"] != "D":
                                    if st.button(f"{icon} {f['status']}  {f['path']}", key=f"grp_{f['path']}"):
                                        st.session_state["_view_file"] = f["path"]
                                        st.rerun()
                                else:
                                    st.text(f"  {icon} {f['status']}  {f['path']}")
                            with col2:
                                st.caption(mt)
                            with col3:
                                if f["status"] != "D":
                                    if st.button("diff", key=f"diff_{f['path']}"):
                                        st.code(git_diff_file(f["path"]), language="diff")


    st.divider()

    st.header("Recent Commits")
    n_commits = st.sidebar.slider("Commits to show", 5, 50, 20)
    commits = git_log(n_commits)
    if not commits:
        st.info("No commits found.")
    else:
        for c in commits:
            ts = format_timestamp(c["date"])
            short = c["hash"][:8]
            with st.expander(f"`{short}` {ts} — {c['subject']}"):
                st.markdown(f"**Author:** {c['author']}  \n**Hash:** `{c['hash']}`")
                st.code(git_show_commit(c["hash"]), language="text")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Sawmill Runs
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏭 Sawmill Runs":
    st.title("Sawmill Runs")
    frameworks = discover_frameworks()
    if not frameworks:
        st.warning("No FMWK-* directories found under sawmill/")
        st.stop()

    fw = st.sidebar.selectbox("Framework", frameworks)

    st.header(f"{fw} — Spec Pack")
    spec_dir = SAWMILL / fw
    docs = sorted((f for f in spec_dir.iterdir() if f.is_file() and f.suffix == ".md"),
                  key=lambda f: f.stat().st_mtime, reverse=True)
    if docs:
        tabs = st.tabs([f"{f.stem}  ({format_mtime(f)})" for f in docs])
        for tab, doc in zip(tabs, docs):
            with tab:
                content = read_file(doc)
                st.markdown(content)
                with st.expander("Raw"):
                    st.code(content, language="markdown")
    else:
        st.info("No spec documents found.")

    st.header("Run History")
    runs = discover_runs(fw)
    if not runs:
        st.info("No runs recorded yet.")
    else:
        run_id = st.selectbox("Select run", [r.name for r in runs],
                              format_func=lambda r: f"{r[:15].replace('T', ' ')} — {r[16:]}")
        run_dir = SAWMILL / fw / "runs" / run_id

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("run.json")
            run_meta = read_json(run_dir / "run.json")
            if run_meta:
                st.json(run_meta)
        with col2:
            st.subheader("status.json")
            status = read_json(run_dir / "status.json")
            if status:
                state = status.get("state", "unknown")
                color = {"running": "🟡", "passed": "🟢", "failed": "🔴"}.get(state, "⚪")
                st.metric("State", f"{color} {state}")
                st.metric("Turn", status.get("current_turn", "—"))
                st.metric("Role", status.get("current_role", "—"))
                st.metric("Step", status.get("current_step", "—"))
                st.json(status)

        st.subheader("Event Timeline")
        events_file = run_dir / "events.jsonl"
        if events_file.exists():
            events = read_jsonl(events_file)
            for ev in events:
                ts = format_timestamp(ev.get("timestamp", ""))
                etype = ev.get("event_type", "?")
                role = ev.get("role", "?")
                summary = ev.get("summary", "")
                icon = {"run_started": "🚀", "preflight_passed": "✅", "turn_started": "▶️",
                        "prompt_rendered": "📝", "agent_invoked": "🤖", "evidence_validated": "🔍",
                        "gate_passed": "🚪", "turn_completed": "✔️", "run_completed": "🏁",
                        "turn_failed": "❌", "run_failed": "❌"}.get(etype, "•")
                with st.expander(f"{icon} {ts} — {etype} ({role}): {summary}"):
                    st.json(ev)
        else:
            st.info("No events.jsonl found for this run.")

        logs_dir = run_dir / "logs"
        if logs_dir.exists() and list(logs_dir.iterdir()):
            st.subheader("Logs")
            log_files = sorted(logs_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
            log_file = st.selectbox("Log file", [f.name for f in log_files])
            st.code(read_file(logs_dir / log_file), language="text")

        inv_dir = run_dir / "invocations"
        if inv_dir.exists() and list(inv_dir.iterdir()):
            st.subheader("Invocations")
            inv_files = sorted(inv_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
            inv_file = st.selectbox("Invocation", [f.name for f in inv_files])
            content = read_file(inv_dir / inv_file)
            if inv_file.endswith(".json"):
                st.json(json.loads(content))
            else:
                st.code(content, language="text")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Architecture
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📐 Architecture":
    st.title("Architecture — Authority Documents")
    st.caption("These are the same files agents read from architecture/")

    priority = ["NORTH_STAR.md", "BUILDER_SPEC.md", "OPERATIONAL_SPEC.md",
                "FWK-0-DRAFT.md", "BUILD-PLAN.md", "AGENT_CONSTRAINTS.md"]

    arch_files = sorted(ARCHITECTURE.glob("*.md"))
    ordered = []
    for p in priority:
        path = ARCHITECTURE / p
        if path.exists():
            ordered.append(path)
    for f in arch_files:
        if f not in ordered:
            ordered.append(f)

    if not ordered:
        st.warning("No architecture docs found.")
        st.stop()

    sort_arch = st.sidebar.radio("Sort by", ["Priority", "Newest first", "Name"], key="arch_sort")
    if sort_arch == "Newest first":
        ordered = sorted(ordered, key=lambda f: f.stat().st_mtime, reverse=True)
    elif sort_arch == "Name":
        ordered = sorted(ordered, key=lambda f: f.name)

    doc_name = st.sidebar.selectbox("Document",
        [f.name for f in ordered],
        format_func=lambda n: f"{n}  ({format_mtime(ARCHITECTURE / n)})")
    doc_path = ARCHITECTURE / doc_name
    content = read_file(doc_path)

    st.markdown(f"**File:** `architecture/{doc_name}` — modified {format_mtime(doc_path)}")
    st.markdown(content)
    with st.expander("Raw markdown"):
        st.code(content, language="markdown")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Agent Roles
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 Agent Roles":
    st.title("Agent Role Definitions")
    st.caption("These are the .claude/agents/*.md files that define each role.")

    role_files = sorted(AGENTS.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not role_files:
        st.warning("No agent role files found.")
        st.stop()

    role_name = st.sidebar.selectbox("Role", [f.stem for f in role_files],
        format_func=lambda n: f"{n}  ({format_mtime(AGENTS / f'{n}.md')})")
    role_path = AGENTS / f"{role_name}.md"
    content = read_file(role_path)

    st.markdown(f"**File:** `.claude/agents/{role_name}.md` — modified {format_mtime(role_path)}")
    st.markdown(content)
    with st.expander("Raw markdown"):
        st.code(content, language="markdown")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: System Catalog (Backstage)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏗️ System Catalog":
    st.title("System Catalog")
    st.caption("Backstage entities from catalog-info.yaml files — the system topology.")

    entities = load_catalog_entities()
    if not entities:
        st.warning("No catalog entities found.")
        st.stop()

    # Summary metrics
    kinds = {}
    for e in entities:
        k = e.get("kind", "?")
        kinds[k] = kinds.get(k, 0) + 1
    cols = st.columns(len(kinds))
    for col, (kind, count) in zip(cols, sorted(kinds.items())):
        col.metric(kind, count)

    st.divider()

    # Filter by kind
    kind_filter = st.sidebar.multiselect("Kind", sorted(kinds.keys()), default=sorted(kinds.keys()))
    filtered = [e for e in entities if e.get("kind") in kind_filter]

    for entity in filtered:
        kind = entity.get("kind", "?")
        meta = entity.get("metadata", {})
        spec = entity.get("spec", {})
        name = meta.get("name", "unnamed")
        desc = meta.get("description", "").strip()

        kind_icon = {"System": "🌐", "Component": "📦", "API": "🔌", "Resource": "💾",
                     "User": "👤", "Group": "👥"}.get(kind, "•")

        with st.expander(f"{kind_icon} **{kind}** / `{name}`  —  {desc[:80]}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Name:** `{name}`")
                st.markdown(f"**Kind:** {kind}")
                st.markdown(f"**Type:** {spec.get('type', '—')}")
                st.markdown(f"**Owner:** {spec.get('owner', '—')}")
                st.markdown(f"**Lifecycle:** {spec.get('lifecycle', '—')}")
                st.markdown(f"**System:** {spec.get('system', '—')}")
            with col2:
                tags = meta.get("tags", [])
                if tags:
                    st.markdown(f"**Tags:** {', '.join(tags)}")
                links = meta.get("links", [])
                for link in links:
                    st.markdown(f"🔗 [{link.get('title', link.get('url', ''))}]({link.get('url', '')})")
                deps = spec.get("dependsOn", [])
                if deps:
                    st.markdown("**Depends on:**")
                    for d in deps:
                        st.markdown(f"  - `{d}`")
                provides = spec.get("providesApis", [])
                if provides:
                    st.markdown("**Provides APIs:**")
                    for a in provides:
                        st.markdown(f"  - `{a}`")

            # If it's an API, show the spec
            if kind == "API":
                spec_content = get_api_spec_content(entity)
                if spec_content:
                    api_type = spec.get("type", "")
                    st.subheader("API Definition")
                    if api_type in ("asyncapi", "openapi", "mcp"):
                        st.code(spec_content, language="yaml")
                    else:
                        st.markdown(spec_content)

            # Source file
            src = entity.get("_source_file", "")
            if src:
                st.caption(f"Source: `{src}`")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Conversations
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💬 Conversations":
    st.title("Conversations")
    st.caption("All agent transcripts — Claude, Codex, and Gemini — from disk.")

    claude_sessions = discover_claude_sessions()
    codex_sessions = discover_codex_sessions()
    gemini_sessions = discover_gemini_sessions()
    all_sessions = claude_sessions + codex_sessions + gemini_sessions

    # Sort newest first by default (using file mtime as fallback for missing timestamps)
    for s in all_sessions:
        if not s.get("timestamp"):
            s["timestamp"] = file_mtime(pathlib.Path(s["path"])).isoformat()

    all_sessions.sort(key=lambda s: s.get("timestamp", "0"), reverse=True)

    if not all_sessions:
        st.warning("No transcripts found from any CLI.")
        st.stop()

    cli_filter = st.sidebar.multiselect("CLI", ["claude", "codex", "gemini"],
                                        default=["claude", "codex", "gemini"])
    filtered = [s for s in all_sessions if s["cli"] in cli_filter]

    if not filtered:
        st.info("No sessions match the filter.")
        st.stop()

    conv_sort = st.sidebar.radio("Sort by", ["Newest first", "Oldest first", "CLI"], key="conv_sort")
    if conv_sort == "Oldest first":
        filtered.sort(key=lambda s: s.get("timestamp", "0"))
    elif conv_sort == "CLI":
        filtered.sort(key=lambda s: (s["cli"], s.get("timestamp", "0")), reverse=True)
    # else already newest first

    cli_icons = {"claude": "🟣", "codex": "🟢", "gemini": "🔵"}

    selected = st.sidebar.selectbox(
        "Session", range(len(filtered)),
        format_func=lambda i: (
            f"{cli_icons.get(filtered[i]['cli'], '•')} "
            f"{format_timestamp(filtered[i].get('timestamp', ''))[:16]}  "
            f"{filtered[i]['preview'][:30]}"
        ),
    )

    entry = filtered[selected]
    cli = entry["cli"]
    st.markdown(
        f"**CLI:** {cli_icons.get(cli, '')} **{cli.title()}**  \n"
        f"**Session:** `{entry['session']}`  \n"
        f"**Started:** {format_timestamp(entry.get('timestamp', '?'))}  \n"
        f"**File:** `{entry['path']}`"
    )

    newest_first = st.toggle("Newest first", value=True)
    st.divider()

    if cli == "claude":
        render_claude_transcript(entry["path"], reverse=newest_first)
    elif cli == "codex":
        render_codex_transcript(entry["path"], reverse=newest_first)
    elif cli == "gemini":
        render_gemini_transcript(entry["path"], reverse=newest_first)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: File Explorer
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📁 File Explorer":
    st.title("File Explorer")
    st.caption("Browse the repo the way agents see it. Click to navigate.")

    if "browser_path" not in st.session_state:
        st.session_state.browser_path = str(BRAIN)

    current = pathlib.Path(st.session_state.browser_path)

    # Sort control for directories
    file_sort = st.sidebar.radio("Sort files by", ["Name", "Newest first", "Size"], key="file_sort")

    # Breadcrumb navigation
    try:
        rel = current.relative_to(BRAIN)
        parts = ["."] + list(rel.parts) if str(rel) != "." else ["."]
    except ValueError:
        parts = [str(current)]

    breadcrumb_cols = st.columns(len(parts) + 1)
    with breadcrumb_cols[0]:
        if st.button("🏠 root", key="nav_root"):
            st.session_state.browser_path = str(BRAIN)
            st.rerun()
    for i, part in enumerate(parts):
        if part == "." and i == 0:
            continue
        with breadcrumb_cols[i + 1]:
            nav_to = BRAIN / pathlib.Path(*parts[1:i+1]) if i > 0 else BRAIN
            if st.button(f"📂 {part}", key=f"bread_{i}"):
                st.session_state.browser_path = str(nav_to)
                st.rerun()

    st.divider()

    if current.is_file():
        if st.button("⬅ Back to folder"):
            st.session_state.browser_path = str(current.parent)
            st.rerun()
        try:
            rel_label = str(current.relative_to(BRAIN))
        except ValueError:
            rel_label = str(current)
        render_file(current, rel_label)

    elif current.is_dir():
        try:
            rel_display = str(current.relative_to(BRAIN))
        except ValueError:
            rel_display = str(current)
        st.markdown(f"**Directory:** `{rel_display}/`")

        items = list(current.iterdir())
        dirs = [p for p in items if p.is_dir()]
        files = [p for p in items if p.is_file()]

        # Sort dirs by name always
        dirs.sort(key=lambda p: p.name.lower())

        # Sort files based on user preference
        if file_sort == "Newest first":
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        elif file_sort == "Size":
            files.sort(key=lambda f: f.stat().st_size, reverse=True)
        else:
            files.sort(key=lambda f: f.name.lower())

        if current != BRAIN:
            if st.button("⬆ ..", key="nav_parent"):
                st.session_state.browser_path = str(current.parent)
                st.rerun()

        for d in dirs:
            try:
                count = sum(1 for _ in d.iterdir())
            except PermissionError:
                count = "?"
            dtime = format_mtime(d)
            if st.button(f"📁 {d.name}/  ({count} items · {dtime})", key=f"dir_{d.name}"):
                st.session_state.browser_path = str(d)
                st.rerun()

        st.divider()
        for f in files:
            size = f.stat().st_size
            mtime = format_mtime(f)

            ext = f.suffix.lower()
            icon = {".md": "📝", ".py": "🐍", ".sh": "⚙️", ".json": "📋",
                    ".yaml": "📋", ".yml": "📋", ".jsonl": "📋", ".txt": "📄",
                    ".toml": "📋", ".pdf": "📕"}.get(ext, "📄")

            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size // 1024}KB"
            else:
                size_str = f"{size // (1024*1024)}MB"

            col1, col2 = st.columns([5, 2])
            with col1:
                if st.button(f"{icon} {f.name}", key=f"file_{f.name}"):
                    st.session_state.browser_path = str(f)
                    st.rerun()
            with col2:
                st.caption(f"{size_str} · {mtime}")

    else:
        st.error(f"Path not found: {current}")
        if st.button("Reset to repo root"):
            st.session_state.browser_path = str(BRAIN)
            st.rerun()

    st.divider()
    quick = st.text_input("Quick jump (relative path)", placeholder="e.g. sawmill/FMWK-001-ledger/D1_CONSTITUTION.md")
    if quick:
        target = BRAIN / quick
        if target.exists():
            st.session_state.browser_path = str(target)
            st.rerun()
        else:
            st.error(f"Not found: {quick}")
