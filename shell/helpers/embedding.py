from __future__ import annotations

import json
import urllib.request

OLLAMA_BASE = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIMS = 768


def embed_text(text: str) -> list[float]:
    results = embed_texts([text])
    return results[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    payload = json.dumps({"model": EMBEDDING_MODEL, "input": texts}).encode()
    request = urllib.request.Request(
        f"{OLLAMA_BASE}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())
    except Exception as exc:
        raise RuntimeError(f"Ollama embedding failed: {exc}") from exc
    embeddings = data.get("embeddings", [])
    if len(embeddings) != len(texts):
        raise RuntimeError(f"Expected {len(texts)} embeddings, got {len(embeddings)}")
    return [[float(value) for value in vec] for vec in embeddings]
