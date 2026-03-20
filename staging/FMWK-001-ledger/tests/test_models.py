from __future__ import annotations

import pytest

from ledger.models import LedgerAppendRequest, SnapshotCreatedPayload


def test_models_rejects_caller_sequence_fields() -> None:
    with pytest.raises(ValueError, match="must not provide caller-controlled fields"):
        LedgerAppendRequest(
            event_id="0195b7fc-c29c-7c2f-a4da-8f6d2eb6d1a1",
            event_type="node_creation",
            schema_version="1.0.0",
            timestamp="2026-03-19T23:50:00Z",
            provenance={
                "framework_id": "FMWK-002",
                "pack_id": "PC-001-fold-engine",
                "actor": "system",
            },
            payload={
                "node_id": "node-intent-dining-recall",
                "node_type": "intent",
                "lifecycle_state": "LIVE",
                "metadata": {"title": "Find Sarah's restaurant recommendation"},
            },
            sequence=5,
        )


def test_models_accepts_snapshot_created_payload(zero_hash: str) -> None:
    payload = SnapshotCreatedPayload(
        snapshot_sequence=128,
        snapshot_path="/snapshots/128.snapshot",
        snapshot_hash=zero_hash,
        created_at="2026-03-19T23:40:00Z",
    )

    assert payload.snapshot_sequence == 128
    assert payload.snapshot_path == "/snapshots/128.snapshot"
    assert payload.snapshot_hash == zero_hash

