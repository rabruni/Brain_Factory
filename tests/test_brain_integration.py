from __future__ import annotations

import importlib
import json
import sys
import urllib.error
import urllib.request

import pytest


def _ollama_available() -> bool:
    request = urllib.request.Request(
        "http://localhost:11434/api/embed",
        data=json.dumps({"model": "nomic-embed-text", "input": "ping"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return False
    embeddings = data.get("embeddings", [])
    return bool(embeddings and len(embeddings[0]) == 768)


def _load_modules(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_DIR_OVERRIDE", str(tmp_path))
    for name in ["workspace", "shell.helpers.brain"]:
        sys.modules.pop(name, None)
    workspace = importlib.import_module("workspace")
    brain = importlib.import_module("shell.helpers.brain")
    return workspace, brain


@pytest.mark.integration
def test_brain_end_to_end_with_ollama(tmp_path, monkeypatch):
    if not _ollama_available():
        pytest.skip("Ollama embed endpoint unavailable")

    _, brain = _load_modules(tmp_path, monkeypatch)

    brain.capture(
        "FMWK-001-ledger owns the append-only event store, event schemas, and hash chain.",
        tags=["ledger"],
        source="integration",
    )
    brain.capture(
        "FMWK-004-execution owns all LLM calls, prompt contracts, and execution work orders.",
        tags=["execution"],
        source="integration",
    )
    brain.capture(
        "FMWK-006-package-lifecycle owns gates, install and uninstall, and the CLI tooling.",
        tags=["package-lifecycle"],
        source="integration",
    )

    results = brain.search("Which framework handles prompt contracts and LLM execution?", limit=3)
    filtered = brain.search("Which framework handles prompt contracts and LLM execution?", limit=3, tag="execution")

    assert results
    assert "FMWK-004-execution" in results[0]["content"]
    assert filtered
    assert len(filtered) == 1
    assert filtered[0]["tags"] == ["execution"]
