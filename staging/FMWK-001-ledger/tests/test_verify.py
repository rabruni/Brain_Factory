from dataclasses import asdict
import json

from ledger.errors import LedgerSerializationError
from ledger.serialization import ZERO_HASH
from ledger.store import LedgerStore
from ledger.verify import verify_chain, verify_events


class FakeImmudbClient:
    def __init__(self) -> None:
        self.records: dict[str, bytes] = {}

    def ensure_database(self) -> None:
        return None

    def get(self, key: str) -> bytes:
        return self.records[key]

    def set(self, key: str, value: bytes) -> None:
        self.records[key] = value

    def keys(self) -> list[str]:
        return sorted(self.records.keys())


def _request(event_type: str, payload: dict) -> dict:
    return {
        "event_type": event_type,
        "schema_version": "1.0.0",
        "timestamp": "2026-03-20T20:20:00Z",
        "provenance": {
            "framework_id": "FMWK-001-ledger",
            "pack_id": "PC-001-ledger-core",
            "actor": "system",
        },
        "payload": payload,
    }


def _store_with_chain() -> tuple[LedgerStore, FakeImmudbClient]:
    client = FakeImmudbClient()
    store = LedgerStore(client_factory=lambda: client, sleep=lambda _: None)
    store.append_event(_request("session_start", {"session_id": "session-1", "session_kind": "operator", "subject_id": "ray", "started_by": "operator"}))
    store.append_event(_request("signal_delta", {"node_id": "memory-1", "signal_name": "operator_reinforcement", "delta": 1}))
    store.append_event(_request("snapshot_created", {"snapshot_sequence": 2, "snapshot_path": "/snapshots/2.snapshot", "snapshot_hash": ZERO_HASH}))
    return store, client


def test_verify_chain_online_returns_valid_true_for_intact_chain() -> None:
    store, _ = _store_with_chain()

    result = verify_chain(store, source_mode="online")

    assert result.valid is True
    assert result.start_sequence == 0
    assert result.end_sequence == 2


def test_verify_chain_reports_first_corrupted_sequence() -> None:
    store, client = _store_with_chain()
    corrupted = asdict(store.read(1))
    corrupted["hash"] = ZERO_HASH
    client.set("00000000000000000001", json.dumps(corrupted, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))

    result = verify_chain(store, source_mode="online")

    assert result.valid is False
    assert result.break_at == 1


def test_verify_chain_offline_matches_online_result() -> None:
    store, client = _store_with_chain()
    offline_export = [client.get(key) for key in client.keys()]

    online = verify_chain(store, source_mode="online")
    offline = verify_chain(offline_export, source_mode="offline")

    assert offline == online


def test_verify_chain_surfaces_serialization_error_for_unhashable_event() -> None:
    try:
        verify_chain([b'{"bad":'], source_mode="offline")
    except LedgerSerializationError as error:
        assert "parsed" in str(error)
    else:
        raise AssertionError("expected serialization error")


def test_verify_events_detects_previous_hash_break() -> None:
    store, _ = _store_with_chain()
    first = store.read(0)
    second = store.read(1)
    broken = type(second)(
        event_id=second.event_id,
        sequence=second.sequence,
        event_type=second.event_type,
        schema_version=second.schema_version,
        timestamp=second.timestamp,
        provenance=second.provenance,
        previous_hash=ZERO_HASH,
        payload=second.payload,
        hash=second.hash,
    )
    third = store.read(2)

    result = verify_events([first, broken, third])

    assert result.valid is False
    assert result.break_at == 1
