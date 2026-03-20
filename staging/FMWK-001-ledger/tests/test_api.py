from ledger.api import Ledger
from ledger.errors import LEDGER_CONNECTION_ERROR, LedgerConnectionError
from ledger.store import LedgerStore


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


def test_ledger_api_appends_approved_event_flow() -> None:
    ledger = Ledger(store=LedgerStore(client_factory=lambda: FakeImmudbClient(), sleep=lambda _: None))

    event = ledger.append(
        _request(
            "session_start",
            {
                "session_id": "session-1",
                "session_kind": "operator",
                "subject_id": "ray",
                "started_by": "operator",
            },
        )
    )

    assert event.sequence == 0
    assert ledger.read(0) == event


def test_ledger_api_appends_snapshot_marker_reference_payload() -> None:
    ledger = Ledger(store=LedgerStore(client_factory=lambda: FakeImmudbClient(), sleep=lambda _: None))

    event = ledger.append(
        _request(
            "snapshot_created",
            {
                "snapshot_sequence": 0,
                "snapshot_path": "/snapshots/0.snapshot",
                "snapshot_hash": "sha256:" + ("0" * 64),
            },
        )
    )

    assert event.payload["snapshot_path"] == "/snapshots/0.snapshot"


def test_ledger_api_verify_chain_online_delegates_to_verifier() -> None:
    client = FakeImmudbClient()
    ledger = Ledger(store=LedgerStore(client_factory=lambda: client, sleep=lambda _: None))
    ledger.append(_request("session_start", {"session_id": "session-1", "session_kind": "operator", "subject_id": "ray", "started_by": "operator"}))

    result = ledger.verify_chain()

    assert result.valid is True
    assert result.end_sequence == 0


def test_ledger_api_get_tip_delegates_to_store() -> None:
    client = FakeImmudbClient()
    ledger = Ledger(store=LedgerStore(client_factory=lambda: client, sleep=lambda _: None))
    event = ledger.append(_request("session_start", {"session_id": "session-1", "session_kind": "operator", "subject_id": "ray", "started_by": "operator"}))

    assert ledger.get_tip().hash == event.hash


def test_ledger_api_propagates_explicit_error_codes() -> None:
    class BrokenStore:
        def append_event(self, request: dict) -> None:
            raise LedgerConnectionError("append failed")

    ledger = Ledger(store=BrokenStore())

    try:
        ledger.append(
            _request(
                "session_start",
                {
                    "session_id": "session-1",
                    "session_kind": "operator",
                    "subject_id": "ray",
                    "started_by": "operator",
                },
            )
        )
    except LedgerConnectionError as error:
        assert error.code == LEDGER_CONNECTION_ERROR
    else:
        raise AssertionError("expected connection error")
