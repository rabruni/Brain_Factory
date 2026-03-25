from __future__ import annotations

import io
import json
import urllib.error

import pytest

from shell.helpers.embedding import EMBEDDING_DIMS, embed_text, embed_texts


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_embed_text_returns_expected_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    vector = [0.5] * EMBEDDING_DIMS

    def fake_urlopen(request, timeout=30):
        return _FakeResponse({"embeddings": [vector]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = embed_text("test")

    assert len(result) == EMBEDDING_DIMS
    assert result[:3] == [0.5, 0.5, 0.5]


def test_embed_texts_handles_multiple_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    first = [1.0] * EMBEDDING_DIMS
    second = [2.0] * EMBEDDING_DIMS

    def fake_urlopen(request, timeout=30):
        return _FakeResponse({"embeddings": [first, second]})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = embed_texts(["a", "b"])

    assert len(result) == 2
    assert len(result[0]) == EMBEDDING_DIMS
    assert len(result[1]) == EMBEDDING_DIMS
    assert result[0][0] == 1.0
    assert result[1][0] == 2.0


def test_embed_texts_raises_runtime_error_on_transport_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout=30):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="Ollama embedding failed"):
        embed_texts(["a"])


def test_embed_texts_raises_runtime_error_on_mismatched_count(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request, timeout=30):
        return _FakeResponse({"embeddings": []})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="Expected 1 embeddings, got 0"):
        embed_texts(["a"])
