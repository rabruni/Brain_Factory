from __future__ import annotations

from shell.routes.websocket import _brain_context_block


def test_brain_context_block_returns_empty_when_no_results(monkeypatch):
    monkeypatch.setattr("shell.helpers.brain.search", lambda *args, **kwargs: [])

    assert _brain_context_block("hello") == ""


def test_brain_context_block_returns_empty_when_max_results_zero():
    assert _brain_context_block("hello", max_results=0) == ""


def test_brain_context_block_formats_results(monkeypatch):
    monkeypatch.setattr(
        "shell.helpers.brain.search",
        lambda *args, **kwargs: [
            {"content": "Remember the ledger shell notes", "tags": ["brain", "ops"]},
            {"content": "Keep sawmill separate", "tags": []},
        ],
    )

    block = _brain_context_block("ledger")

    assert "[Brain Context — relevant prior knowledge]" in block
    assert "- Remember the ledger shell notes [brain, ops]" in block
    assert "- Keep sawmill separate" in block
