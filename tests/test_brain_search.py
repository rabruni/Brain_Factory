from __future__ import annotations

import importlib
import sys


def _load_modules(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_DIR_OVERRIDE", str(tmp_path))
    for name in ["workspace", "shell.helpers.brain"]:
        sys.modules.pop(name, None)
    workspace = importlib.import_module("workspace")
    brain = importlib.import_module("shell.helpers.brain")
    return workspace, brain


def test_capture_stores_searchable_thought_and_stats(tmp_path, monkeypatch):
    ws, brain = _load_modules(tmp_path, monkeypatch)

    vectors = {
        "alpha memory": [1.0] + [0.0] * 767,
    }
    monkeypatch.setattr(brain, "_embed_texts", lambda texts: [vectors[text] for text in texts])

    thought = brain.capture("alpha memory", tags=["alpha"], source="test")
    results = brain.search("alpha memory", limit=5)

    assert thought["id"] == results[0]["id"]
    assert "distance" in results[0]
    assert isinstance(results[0]["distance"], float)
    assert brain.list_recent() == ws.list_thoughts()
    assert brain.stats() == {"total": 1, "tags": {"alpha": 1}}


def test_search_filters_by_tag(tmp_path, monkeypatch):
    _, brain = _load_modules(tmp_path, monkeypatch)

    vectors = {
        "alpha note": [1.0] + [0.0] * 767,
        "beta note": [0.0, 1.0] + [0.0] * 766,
        "alpha query": [1.0] + [0.0] * 767,
    }
    monkeypatch.setattr(brain, "_embed_texts", lambda texts: [vectors[text] for text in texts])

    brain.capture("alpha note", tags=["alpha"], source="test")
    brain.capture("beta note", tags=["beta"], source="test")
    results = brain.search("alpha query", limit=5, tag="alpha")

    assert len(results) == 1
    assert results[0]["content"] == "alpha note"


def test_delete_removes_vector_and_metadata(tmp_path, monkeypatch):
    ws, brain = _load_modules(tmp_path, monkeypatch)

    vectors = {
        "delete me": [1.0] + [0.0] * 767,
        "query": [1.0] + [0.0] * 767,
    }
    monkeypatch.setattr(brain, "_embed_texts", lambda texts: [vectors[text] for text in texts])

    thought = brain.capture("delete me", tags=["alpha"], source="test")

    assert brain.delete(thought["id"]) == {"deleted": True}
    assert ws.get_thought(thought["id"]) is None
    assert brain.search("query", limit=5) == []
    assert brain.delete(thought["id"]) == {"deleted": False}


def test_capture_rolls_back_metadata_on_embedding_failure(tmp_path, monkeypatch):
    ws, brain = _load_modules(tmp_path, monkeypatch)

    def fail(texts):
        raise RuntimeError("embedding broke")

    monkeypatch.setattr(brain, "_embed_texts", fail)

    import pytest

    with pytest.raises(RuntimeError, match="embedding broke"):
        brain.capture("will rollback", tags=["alpha"], source="test")

    assert ws.list_thoughts() == []
