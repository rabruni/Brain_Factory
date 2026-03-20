from ledger.errors import (
    LEDGER_CONNECTION_ERROR,
    LEDGER_CORRUPTION_ERROR,
    LEDGER_SEQUENCE_ERROR,
    LEDGER_SERIALIZATION_ERROR,
    LedgerConnectionError,
    LedgerCorruptionError,
    LedgerSequenceError,
    LedgerSerializationError,
)
from ledger.models import LedgerEvent, LedgerTip, Provenance, VerificationResult
from ledger.schemas import validate_append_request
from ledger.serialization import ZERO_HASH
from ledger.store import ClientDisconnectError, DatabaseMissingError, LedgerStore


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


class FakeImmudbClient:
    def __init__(
        self,
        *,
        database_exists: bool = True,
        fail_get: int = 0,
        fail_set: int = 0,
    ) -> None:
        self.database_exists = database_exists
        self.fail_get = fail_get
        self.fail_set = fail_set
        self.records: dict[str, bytes] = {}

    def ensure_database(self) -> None:
        if not self.database_exists:
            raise DatabaseMissingError("ledger database missing")

    def get(self, key: str) -> bytes:
        if self.fail_get:
            self.fail_get -= 1
            raise ClientDisconnectError("get disconnected")
        return self.records[key]

    def set(self, key: str, value: bytes) -> None:
        if self.fail_set:
            self.fail_set -= 1
            raise ClientDisconnectError("set disconnected")
        self.records[key] = value

    def keys(self) -> list[str]:
        return sorted(self.records.keys())


def test_model_construction_accepts_valid_ledger_event() -> None:
    event = LedgerEvent(
        event_id="0195b8d1-6d8d-7ef9-9c6a-4bd29ca2dce4",
        sequence=0,
        event_type="session_start",
        schema_version="1.0.0",
        timestamp="2026-03-20T20:20:00Z",
        provenance=Provenance(
            framework_id="FMWK-001-ledger",
            pack_id="PC-001-ledger-core",
            actor="system",
        ),
        previous_hash="sha256:" + ("0" * 64),
        payload={
            "session_id": "session-0195b8d1",
            "session_kind": "operator",
            "subject_id": "ray",
            "started_by": "operator",
        },
        hash="sha256:b2bbde319c7c9677b6d6816d9b422c8ec9787c6d0ca7f64444f0715a8ca54ac8",
    )

    assert event.sequence == 0
    assert event.provenance.framework_id == "FMWK-001-ledger"


def test_model_construction_accepts_tip_and_verification_result() -> None:
    tip = LedgerTip(
        sequence_number=12,
        hash="sha256:8b6e4791d3035430dc7f00692cfd0d2a59d789ab3ed86855f81044cd22fdfd4d",
    )
    result = VerificationResult(valid=False, start_sequence=0, end_sequence=5, break_at=3)

    assert tip.sequence_number == 12
    assert result.break_at == 3


def test_error_codes_are_stable_for_each_framework_error() -> None:
    assert LedgerConnectionError("connect failed").code == LEDGER_CONNECTION_ERROR
    assert LedgerCorruptionError("chain broken").code == LEDGER_CORRUPTION_ERROR
    assert LedgerSequenceError("tip changed").code == LEDGER_SEQUENCE_ERROR
    assert LedgerSerializationError("bad bytes").code == LEDGER_SERIALIZATION_ERROR


def test_error_messages_are_preserved() -> None:
    error = LedgerSequenceError("tip changed during append")

    assert str(error) == "tip changed during append"


def test_append_rejects_caller_supplied_sequence_fields() -> None:
    request = {
        "event_type": "session_start",
        "schema_version": "1.0.0",
        "timestamp": "2026-03-20T20:20:00Z",
        "sequence": 7,
        "provenance": {
            "framework_id": "FMWK-001-ledger",
            "pack_id": "PC-001-ledger-core",
            "actor": "system",
        },
        "payload": {
            "session_id": "session-0195b8d1",
            "session_kind": "operator",
            "subject_id": "ray",
            "started_by": "operator",
        },
    }

    try:
        validate_append_request(request)
    except LedgerSerializationError as error:
        assert error.code == LEDGER_SERIALIZATION_ERROR
        assert "sequence" in str(error)
    else:
        raise AssertionError("expected serialization error")


def test_append_validates_minimum_node_creation_payload() -> None:
    validate_append_request(
        {
            "event_type": "node_creation",
            "schema_version": "1.0.0",
            "timestamp": "2026-03-20T20:20:00Z",
            "provenance": {
                "framework_id": "FMWK-001-ledger",
                "pack_id": "PC-001-ledger-core",
                "actor": "system",
            },
            "payload": {
                "node_id": "intent-0195b8d1",
                "node_type": "intent",
                "initial_state": {"status": "DECLARED"},
                "associated_entities": ["session-0195b8d1"],
                "session_id": "session-0195b8d1",
            },
        }
    )


def test_append_validates_minimum_signal_delta_payload() -> None:
    validate_append_request(
        {
            "event_type": "signal_delta",
            "schema_version": "1.0.0",
            "timestamp": "2026-03-20T20:20:00Z",
            "provenance": {
                "framework_id": "FMWK-001-ledger",
                "pack_id": "PC-001-ledger-core",
                "actor": "system",
            },
            "payload": {
                "node_id": "memory-0195b8d1",
                "signal_name": "operator_reinforcement",
                "delta": 1,
                "reason": "operator confirmed importance",
                "session_id": "session-0195b8d1",
            },
        }
    )

    invalid = {
        "event_type": "signal_delta",
        "schema_version": "1.0.0",
        "timestamp": "2026-03-20T20:20:00Z",
        "provenance": {
            "framework_id": "FMWK-001-ledger",
            "pack_id": "PC-001-ledger-core",
            "actor": "system",
        },
        "payload": {
            "node_id": "memory-0195b8d1",
            "signal_name": "operator_reinforcement",
            "delta": 1.5,
        },
    }

    try:
        validate_append_request(invalid)
    except LedgerSerializationError as error:
        assert "delta" in str(error)
    else:
        raise AssertionError("expected serialization error")


def test_append_validates_minimum_package_install_payload() -> None:
    validate_append_request(
        {
            "event_type": "package_install",
            "schema_version": "1.0.0",
            "timestamp": "2026-03-20T20:20:00Z",
            "provenance": {
                "framework_id": "FMWK-001-ledger",
                "pack_id": "PC-001-ledger-core",
                "actor": "system",
            },
            "payload": {
                "package_id": "PKG-0001-kernel",
                "framework_id": "FMWK-001-ledger",
                "version": "1.0.0",
                "install_scope": "kernel",
                "manifest_hash": "sha256:06dfb23ab8cf9c6621fe58f465bf6f6a2e4698af1c8d8de7c093b2b26a3e5fb7",
            },
        }
    )


def test_append_validates_minimum_session_start_payload() -> None:
    validate_append_request(
        {
            "event_type": "session_start",
            "schema_version": "1.0.0",
            "timestamp": "2026-03-20T20:20:00Z",
            "provenance": {
                "framework_id": "FMWK-001-ledger",
                "pack_id": "PC-001-ledger-core",
                "actor": "system",
            },
            "payload": {
                "session_id": "session-0195b8d1",
                "session_kind": "operator",
                "subject_id": "ray",
                "started_by": "operator",
            },
        }
    )


def test_append_validates_snapshot_created_reference_payload() -> None:
    validate_append_request(
        {
            "event_type": "snapshot_created",
            "schema_version": "1.0.0",
            "timestamp": "2026-03-20T20:20:00Z",
            "provenance": {
                "framework_id": "FMWK-001-ledger",
                "pack_id": "PC-001-ledger-core",
                "actor": "system",
            },
            "payload": {
                "snapshot_sequence": 42,
                "snapshot_path": "/snapshots/42.snapshot",
                "snapshot_hash": "sha256:5c1f3ed4c95346f1dc3ddca6ca9ea6240cfa0b8455174a8c4363130f0f2387cc",
            },
        }
    )


def test_append_genesis_assigns_sequence_zero_and_zero_previous_hash() -> None:
    store = LedgerStore(client_factory=lambda: FakeImmudbClient(), sleep=lambda _: None)

    event = store.append_event(
        _request(
            "session_start",
            {
                "session_id": "session-0195b8d1",
                "session_kind": "operator",
                "subject_id": "ray",
                "started_by": "operator",
            },
        )
    )

    assert event.sequence == 0
    assert event.previous_hash == ZERO_HASH


def test_append_uses_previous_tip_hash_and_next_sequence() -> None:
    client = FakeImmudbClient()
    store = LedgerStore(client_factory=lambda: client, sleep=lambda _: None)
    first = store.append_event(
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

    second = store.append_event(
        _request(
            "signal_delta",
            {
                "node_id": "memory-0195b8d1",
                "signal_name": "operator_reinforcement",
                "delta": 1,
            },
        )
    )

    assert second.sequence == 1
    assert second.previous_hash == first.hash


def test_read_returns_single_event_by_sequence() -> None:
    client = FakeImmudbClient()
    store = LedgerStore(client_factory=lambda: client, sleep=lambda _: None)
    event = store.append_event(
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

    assert store.read(event.sequence) == event


def test_read_range_returns_ascending_inclusive_sequence_order() -> None:
    client = FakeImmudbClient()
    store = LedgerStore(client_factory=lambda: client, sleep=lambda _: None)
    store.append_event(_request("session_start", {"session_id": "session-1", "session_kind": "operator", "subject_id": "ray", "started_by": "operator"}))
    second = store.append_event(_request("signal_delta", {"node_id": "memory-1", "signal_name": "operator_reinforcement", "delta": 1}))
    third = store.append_event(_request("signal_delta", {"node_id": "memory-1", "signal_name": "operator_reinforcement", "delta": 2}))

    assert store.read_range(1, 2) == [second, third]


def test_read_since_excludes_boundary_sequence() -> None:
    client = FakeImmudbClient()
    store = LedgerStore(client_factory=lambda: client, sleep=lambda _: None)
    store.append_event(_request("session_start", {"session_id": "session-1", "session_kind": "operator", "subject_id": "ray", "started_by": "operator"}))
    second = store.append_event(_request("signal_delta", {"node_id": "memory-1", "signal_name": "operator_reinforcement", "delta": 1}))
    third = store.append_event(_request("signal_delta", {"node_id": "memory-1", "signal_name": "operator_reinforcement", "delta": 2}))

    assert store.read_since(1) == [third]
    assert store.read_since(-1) == [store.read(0), second, third]


def test_get_tip_returns_latest_sequence_and_hash() -> None:
    client = FakeImmudbClient()
    store = LedgerStore(client_factory=lambda: client, sleep=lambda _: None)
    store.append_event(_request("session_start", {"session_id": "session-1", "session_kind": "operator", "subject_id": "ray", "started_by": "operator"}))
    second = store.append_event(_request("signal_delta", {"node_id": "memory-1", "signal_name": "operator_reinforcement", "delta": 1}))

    assert store.get_tip() == LedgerTip(sequence_number=1, hash=second.hash)


def test_append_rejects_tip_mismatch_with_sequence_error() -> None:
    client = FakeImmudbClient()
    store = LedgerStore(client_factory=lambda: client, sleep=lambda _: None)
    store.append_event(_request("session_start", {"session_id": "session-1", "session_kind": "operator", "subject_id": "ray", "started_by": "operator"}))

    def mutate_tip() -> None:
        rogue = store._build_event(  # noqa: SLF001
            _request("signal_delta", {"node_id": "memory-rogue", "signal_name": "operator_reinforcement", "delta": 9}),
            sequence=1,
            previous_hash=store.get_tip().hash,
        )
        client.set(store._key_for_sequence(1), store._encode_event(rogue))  # noqa: SLF001

    store.before_commit = mutate_tip

    try:
        store.append_event(_request("signal_delta", {"node_id": "memory-1", "signal_name": "operator_reinforcement", "delta": 1}))
    except LedgerSequenceError as error:
        assert error.code == LEDGER_SEQUENCE_ERROR
    else:
        raise AssertionError("expected sequence error")


def test_connect_fails_fast_when_database_absent() -> None:
    store = LedgerStore(client_factory=lambda: FakeImmudbClient(database_exists=False), sleep=lambda _: None)

    try:
        store.get_tip()
    except LedgerConnectionError as error:
        assert error.code == LEDGER_CONNECTION_ERROR
    else:
        raise AssertionError("expected connection error")


def test_disconnect_retries_once_then_succeeds() -> None:
    clients = [FakeImmudbClient(fail_set=1), FakeImmudbClient()]

    def factory() -> FakeImmudbClient:
        return clients.pop(0)

    store = LedgerStore(client_factory=factory, sleep=lambda _: None)
    event = store.append_event(
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


def test_disconnect_retries_once_then_fails() -> None:
    clients = [FakeImmudbClient(fail_set=1), FakeImmudbClient(fail_set=1)]

    def factory() -> FakeImmudbClient:
        return clients.pop(0)

    store = LedgerStore(client_factory=factory, sleep=lambda _: None)

    try:
        store.append_event(
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
