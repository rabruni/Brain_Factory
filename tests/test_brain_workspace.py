from __future__ import annotations

import importlib
import sys


def _load_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_DIR_OVERRIDE", str(tmp_path))
    sys.modules.pop("workspace", None)
    import workspace  # type: ignore

    module = importlib.reload(workspace)
    return module


def test_workspace_override_rederives_paths(tmp_path, monkeypatch):
    ws = _load_workspace(tmp_path, monkeypatch)

    assert ws.WORKSPACE_DIR == tmp_path
    assert ws.DB_FILE == tmp_path / "workspace.db"
    assert ws.AUDIT_LOG == tmp_path / "audit.jsonl"
    assert ws.TOKENS_FILE == tmp_path / "tokens.json"
    assert ws.AGENT_REGISTRY == tmp_path / "agents.yaml"


def test_capture_and_get_thought(tmp_path, monkeypatch):
    ws = _load_workspace(tmp_path, monkeypatch)

    thought = ws.capture_thought("remember this", tags=["brain", "shell"], source="test")
    fetched = ws.get_thought(thought["id"])

    assert fetched is not None
    assert fetched["content"] == "remember this"
    assert fetched["tags"] == ["brain", "shell"]
    assert fetched["source"] == "test"


def test_list_thoughts_orders_most_recent_first_and_filters_tag(tmp_path, monkeypatch):
    ws = _load_workspace(tmp_path, monkeypatch)

    first = ws.capture_thought("first", tags=["alpha"], source="test")
    second = ws.capture_thought("second", tags=["beta"], source="test")

    rows = ws.list_thoughts()
    filtered = ws.list_thoughts(tag="alpha")

    assert [row["id"] for row in rows][:2] == [second["id"], first["id"]]
    assert [row["id"] for row in filtered] == [first["id"]]


def test_thought_stats_counts_total_and_tags(tmp_path, monkeypatch):
    ws = _load_workspace(tmp_path, monkeypatch)

    ws.capture_thought("one", tags=["alpha", "beta"], source="test")
    ws.capture_thought("two", tags=["alpha"], source="test")

    stats = ws.thought_stats()

    assert stats == {"total": 2, "tags": {"alpha": 2, "beta": 1}}


def test_delete_thought_reports_deleted_state(tmp_path, monkeypatch):
    ws = _load_workspace(tmp_path, monkeypatch)

    thought = ws.capture_thought("remove me", tags=["alpha"], source="test")

    assert ws.delete_thought(thought["id"]) == {"deleted": True}
    assert ws.get_thought(thought["id"]) is None
    assert ws.delete_thought(thought["id"]) == {"deleted": False}
