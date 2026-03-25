from __future__ import annotations

from fastapi.testclient import TestClient

from shell.app import app


client = TestClient(app)


def test_brain_stats_endpoint(monkeypatch):
    monkeypatch.setattr("shell.routes.brain.ws.thought_stats", lambda: {"total": 2, "tags": {"alpha": 1}})

    response = client.get("/api/brain/stats")

    assert response.status_code == 200
    assert response.json() == {"total": 2, "tags": {"alpha": 1}}


def test_brain_thoughts_endpoint(monkeypatch):
    monkeypatch.setattr(
        "shell.routes.brain.ws.list_thoughts",
        lambda limit=50, tag=None: [{"id": "a1", "content": "note", "tags": [], "source": "test", "created_at": "now"}],
    )

    response = client.get("/api/brain/thoughts?limit=10&tag=alpha")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "a1"


def test_brain_capture_and_list_round_trip(monkeypatch):
    state = []

    def fake_capture(content, tags=None, source=""):
        thought = {"id": "t1", "content": content, "tags": tags or [], "source": source, "created_at": "now"}
        state.append(thought)
        return thought

    monkeypatch.setattr("shell.routes.brain.brain.capture", fake_capture)
    monkeypatch.setattr("shell.routes.brain.ws.list_thoughts", lambda limit=50, tag=None: state)

    create_response = client.post("/api/brain/capture", json={"content": "remember me", "tags": ["alpha"], "source": "test"})
    list_response = client.get("/api/brain/thoughts")

    assert create_response.status_code == 200
    assert list_response.status_code == 200
    assert list_response.json()[0]["content"] == "remember me"


def test_brain_capture_requires_content():
    response = client.post("/api/brain/capture", json={"content": "   "})

    assert response.status_code == 400


def test_brain_capture_maps_backend_failure(monkeypatch):
    monkeypatch.setattr("shell.routes.brain.brain.capture", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ollama down")))

    response = client.post("/api/brain/capture", json={"content": "remember me"})

    assert response.status_code == 502
    assert response.json()["error"] == "ollama down"


def test_brain_search_requires_query():
    response = client.post("/api/brain/search", json={"query": ""})

    assert response.status_code == 400


def test_brain_search_maps_backend_failure(monkeypatch):
    monkeypatch.setattr("shell.routes.brain.brain.search", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ollama down")))

    response = client.post("/api/brain/search", json={"query": "alpha"})

    assert response.status_code == 502


def test_brain_delete_routes(monkeypatch):
    monkeypatch.setattr("shell.routes.brain.brain.delete", lambda thought_id: {"deleted": thought_id == "t1"})

    found = client.delete("/api/brain/thoughts/t1")
    missing = client.delete("/api/brain/thoughts/missing")

    assert found.status_code == 200
    assert found.json() == {"deleted": True}
    assert missing.status_code == 404
