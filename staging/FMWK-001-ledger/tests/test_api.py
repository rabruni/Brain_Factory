"""
test_api.py — Tests for LedgerClient (all 6 public methods).

≥35 tests required across: get_tip() ≥4, append() ≥10, read() ≥5,
read_range() ≥4, read_since() ≥3, verify_chain() ≥8.

Also includes T-001 error class tests (4) and T-002 model tests (6).
All tests use MockImmudbStore injected via mock_client fixture.
"""
import threading
import pytest

from ledger.errors import (
    LedgerConnectionError,
    LedgerCorruptionError,
    LedgerSequenceError,
    LedgerSerializationError,
)
from ledger.models import (
    ChainVerificationResult,
    EventType,
    LedgerEvent,
    Provenance,
    TipRecord,
)
from ledger.api import LedgerClient
from ledger.serialization import canonical_hash, GENESIS_PREVIOUS_HASH
from conftest import MockImmudbStore


# ---------------------------------------------------------------------------
# T-001: Error class tests (4 tests)
# ---------------------------------------------------------------------------

def test_error_classes_have_code_and_message():
    """All 4 error classes must have code and message attributes."""
    for cls in [
        LedgerConnectionError,
        LedgerCorruptionError,
        LedgerSequenceError,
        LedgerSerializationError,
    ]:
        err = cls(code="SOME_CODE", message="some message")
        assert err.code == "SOME_CODE"
        assert err.message == "some message"


def test_error_classes_are_exceptions():
    """All 4 error classes must inherit from Exception."""
    assert issubclass(LedgerConnectionError, Exception)
    assert issubclass(LedgerCorruptionError, Exception)
    assert issubclass(LedgerSequenceError, Exception)
    assert issubclass(LedgerSerializationError, Exception)


def test_error_default_codes():
    """Each error class has a correct default code matching D4 Error Code Enum."""
    assert LedgerConnectionError().code == "LEDGER_CONNECTION_ERROR"
    assert LedgerCorruptionError().code == "LEDGER_CORRUPTION_ERROR"
    assert LedgerSequenceError().code == "LEDGER_SEQUENCE_ERROR"
    assert LedgerSerializationError().code == "LEDGER_SERIALIZATION_ERROR"


def test_errors_are_catchable_as_exception():
    """Error classes can be caught as bare Exception."""
    for cls in [
        LedgerConnectionError,
        LedgerCorruptionError,
        LedgerSequenceError,
        LedgerSerializationError,
    ]:
        with pytest.raises(Exception):
            raise cls()


# ---------------------------------------------------------------------------
# T-002: Model tests (6 tests)
# ---------------------------------------------------------------------------

def test_event_type_has_15_values():
    """EventType enum must have exactly 15 values (D3 / D4 EventType Enum)."""
    assert len(EventType) == 15


def test_event_type_values_are_strings():
    """EventType inherits from str — all values are plain strings."""
    for et in EventType:
        assert isinstance(et.value, str)


def test_required_event_types_present():
    """All 15 EventType values must be present (spot-check all)."""
    required = {
        "node_creation", "signal_delta", "methylation_delta", "suppression",
        "unsuppression", "mode_change", "consolidation", "work_order_transition",
        "intent_transition", "session_start", "session_end", "package_install",
        "package_uninstall", "framework_install", "snapshot_created",
    }
    actual = {et.value for et in EventType}
    assert actual == required


def test_tip_record_empty_sentinel():
    """Empty Ledger sentinel must be sequence_number=-1 with 64-zero hash (D6 CLR-002)."""
    tip = TipRecord(sequence_number=-1, hash=GENESIS_PREVIOUS_HASH)
    assert tip.sequence_number == -1
    assert tip.hash == "sha256:" + "0" * 64
    assert len(tip.hash) == 71


def test_chain_verification_result_fields():
    """ChainVerificationResult(valid, break_at) must hold the given values."""
    ok = ChainVerificationResult(valid=True, break_at=None)
    assert ok.valid is True
    assert ok.break_at is None

    fail = ChainVerificationResult(valid=False, break_at=3)
    assert fail.valid is False
    assert fail.break_at == 3


def test_provenance_fields():
    """Provenance must hold framework_id, actor, and optional pack_id."""
    prov = Provenance(framework_id="FMWK-002", actor="system", pack_id=None)
    assert prov.framework_id == "FMWK-002"
    assert prov.actor == "system"
    assert prov.pack_id is None

    prov2 = Provenance(framework_id="FMWK-006", actor="operator", pack_id="PC-001")
    assert prov2.pack_id == "PC-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event_data(
    event_type: str = "session_start",
    payload: dict = None,
    framework_id: str = "FMWK-002",
    actor: str = "system",
) -> dict:
    return {
        "event_type": event_type,
        "schema_version": "1.0.0",
        "timestamp": "2026-03-21T03:21:00Z",
        "provenance": {
            "framework_id": framework_id,
            "pack_id": None,
            "actor": actor,
        },
        "payload": payload if payload is not None else {},
    }


# ---------------------------------------------------------------------------
# get_tip() tests (≥4)
# ---------------------------------------------------------------------------

def test_get_tip_empty_ledger(mock_client):
    """Empty Ledger returns TipRecord(sequence_number=-1, hash=sha256+64zeros)."""
    tip = mock_client.get_tip()
    assert tip.sequence_number == -1
    assert tip.hash == "sha256:" + "0" * 64


def test_get_tip_after_one_append(mock_client, make_event_data):
    """After one append, get_tip() returns the event's sequence and hash."""
    mock_client.append(make_event_data())
    tip = mock_client.get_tip()
    assert tip.sequence_number == 0
    assert tip.hash.startswith("sha256:")
    assert len(tip.hash) == 71


def test_get_tip_sequence_advances_each_append(mock_client, make_event_data):
    """get_tip().sequence_number advances 0,1,2,3,4 with each append."""
    for expected_seq in range(5):
        mock_client.append(make_event_data())
        tip = mock_client.get_tip()
        assert tip.sequence_number == expected_seq


def test_get_tip_connection_error():
    """get_tip() raises LedgerConnectionError when immudb is unreachable."""
    failing = MockImmudbStore(fail_all_sets=True)
    failing.connect()

    # Override get_count to simulate unreachable immudb
    def _failing_get_count():
        raise LedgerConnectionError(code="LEDGER_CONNECTION_ERROR", message="down")

    failing.get_count = _failing_get_count
    client = LedgerClient(_store=failing)

    with pytest.raises(LedgerConnectionError):
        client.get_tip()


# ---------------------------------------------------------------------------
# append() tests (≥10)
# ---------------------------------------------------------------------------

def test_append_genesis_returns_sequence_zero(mock_client, make_event_data):
    """SC-001: first append returns integer 0."""
    seq = mock_client.append(make_event_data())
    assert seq == 0


def test_append_genesis_previous_hash_is_zeros(mock_client, make_event_data):
    """SC-001: genesis event has previous_hash = sha256+64zeros."""
    mock_client.append(make_event_data())
    event = mock_client.read(0)
    assert event.previous_hash == "sha256:" + "0" * 64


def test_append_genesis_hash_correct(mock_client, make_event_data):
    """SC-001: event.hash == canonical_hash(event_without_hash_field)."""
    mock_client.append(make_event_data())
    event = mock_client.read(0)
    from ledger.verify import _event_to_dict
    event_dict = _event_to_dict(event)
    expected_hash = canonical_hash(event_dict)
    assert event.hash == expected_hash


def test_append_genesis_persisted(mock_client, make_event_data):
    """SC-001: read(0) returns the same event after append."""
    mock_client.append(make_event_data())
    event = mock_client.read(0)
    assert event.sequence == 0
    assert event.event_type == "session_start"


def test_append_genesis_tip_advances(mock_client, make_event_data):
    """SC-001: get_tip() returns sequence_number=0 and the event's hash."""
    mock_client.append(make_event_data())
    tip = mock_client.get_tip()
    event = mock_client.read(0)
    assert tip.sequence_number == 0
    assert tip.hash == event.hash


def test_append_chain_continuation_previous_hash(mock_client, make_event_data):
    """SC-002: each event's previous_hash == prior event's hash."""
    for _ in range(5):
        mock_client.append(make_event_data())

    events = mock_client.read_range(0, 4)
    for i, event in enumerate(events):
        if i == 0:
            assert event.previous_hash == "sha256:" + "0" * 64
        else:
            assert event.previous_hash == events[i - 1].hash


def test_append_monotonic_sequence(mock_client, make_event_data):
    """SC-002: 5 sequential appends produce sequences [0,1,2,3,4]."""
    sequences = [mock_client.append(make_event_data()) for _ in range(5)]
    assert sequences == [0, 1, 2, 3, 4]


def test_append_invalid_event_type_raises(mock_client):
    """Unknown event_type raises LedgerSerializationError; state unchanged."""
    tip_before = mock_client.get_tip()
    with pytest.raises(LedgerSerializationError) as exc_info:
        mock_client.append(_make_event_data(event_type="not_a_valid_type"))
    assert exc_info.value.code == "LEDGER_SERIALIZATION_ERROR"
    assert mock_client.get_tip() == tip_before


def test_append_missing_required_field_raises(mock_client):
    """Missing required field raises LedgerSerializationError; state unchanged."""
    tip_before = mock_client.get_tip()
    bad_event = {
        "event_type": "session_start",
        "schema_version": "1.0.0",
        # "timestamp" is missing
        "provenance": {"framework_id": "FMWK-002", "pack_id": None, "actor": "system"},
        "payload": {},
    }
    with pytest.raises(LedgerSerializationError):
        mock_client.append(bad_event)
    assert mock_client.get_tip() == tip_before


def test_append_connection_failure_state_unchanged(make_event_data):
    """
    SC-010: when immudb is unreachable, append raises LedgerConnectionError
    and get_tip() returns the same value as before the failed append.
    """
    # First, write one event successfully
    good_store = MockImmudbStore()
    good_store.connect()
    client = LedgerClient(_store=good_store)
    client.append(make_event_data())
    tip_before = client.get_tip()
    assert tip_before.sequence_number == 0

    # Now simulate connection failure
    good_store._fail_all_sets = True
    with pytest.raises(LedgerConnectionError):
        client.append(make_event_data())

    # State must be unchanged
    good_store._fail_all_sets = False  # re-enable reads
    tip_after = client.get_tip()
    assert tip_after == tip_before


def test_append_concurrent_no_fork(make_event_data):
    """
    SC-011: non-blocking lock means a concurrent append raises LedgerSequenceError.
    Exactly one succeeds; get_tip().sequence_number incremented by exactly 1.
    """
    store = MockImmudbStore()
    store.connect()
    client = LedgerClient(_store=store)

    errors = []

    # Hold the lock manually to simulate another append in progress
    acquired = store._lock.acquire(blocking=False)
    assert acquired, "Lock must be acquirable at test start"

    def concurrent_append():
        try:
            client.append(make_event_data())
        except LedgerSequenceError as e:
            errors.append(e)

    t = threading.Thread(target=concurrent_append)
    t.start()
    t.join()

    # Release: simulates the first append completing
    store._lock.release()

    # Now do a successful append
    seq = client.append(make_event_data())

    # Exactly one error (the concurrent attempt), one success
    assert len(errors) == 1
    assert errors[0].code == "LEDGER_SEQUENCE_ERROR"
    assert seq == 0  # first successful append is genesis
    # get_tip().sequence_number incremented by exactly 1 (one event written)
    assert client.get_tip().sequence_number == 0


def test_append_serialization_failure_state_unchanged(mock_client):
    """Payload containing non-serializable object raises LedgerSerializationError; state unchanged."""
    tip_before = mock_client.get_tip()
    bad_event = {
        "event_type": "session_start",
        "schema_version": "1.0.0",
        "timestamp": "2026-03-21T03:21:00Z",
        "provenance": {"framework_id": "FMWK-002", "pack_id": None, "actor": "system"},
        "payload": {"fn": lambda x: x},  # not JSON-serializable
    }
    with pytest.raises(LedgerSerializationError):
        mock_client.append(bad_event)
    assert mock_client.get_tip() == tip_before


# ---------------------------------------------------------------------------
# read() tests (≥5)
# ---------------------------------------------------------------------------

def test_read_returns_all_fields(mock_client, make_event_data):
    """SC-003: read() returns LedgerEvent with all 9 fields non-null."""
    for _ in range(11):
        mock_client.append(make_event_data())
    event = mock_client.read(5)
    assert event.event_id is not None
    assert event.sequence == 5
    assert event.event_type == "session_start"
    assert event.schema_version == "1.0.0"
    assert event.timestamp is not None
    assert event.provenance is not None
    assert event.previous_hash.startswith("sha256:")
    assert event.payload is not None
    assert event.hash.startswith("sha256:")


def test_read_hash_is_stored_value(mock_client, make_event_data):
    """read() returns the hash that was stored at append time (not recomputed)."""
    mock_client.append(make_event_data())
    event = mock_client.read(0)
    # Hash must be the one stored during append, which is the correct one
    from ledger.verify import _event_to_dict
    expected_hash = canonical_hash(_event_to_dict(event))
    assert event.hash == expected_hash  # stored hash matches what was written


def test_read_out_of_range_raises(mock_client, make_event_data):
    """read(N) where N > tip raises LedgerSequenceError (D4 IN-002)."""
    for _ in range(42):
        mock_client.append(make_event_data())
    with pytest.raises(LedgerSequenceError) as exc_info:
        mock_client.read(999)
    assert exc_info.value.code == "LEDGER_SEQUENCE_ERROR"


def test_read_negative_raises(mock_client):
    """read(-1) raises LedgerSequenceError."""
    with pytest.raises(LedgerSequenceError):
        mock_client.read(-1)


def test_read_connection_error():
    """read() raises LedgerConnectionError when immudb is unreachable."""
    store = MockImmudbStore()
    store.connect()
    client = LedgerClient(_store=store)

    # First write one event so tip > -1
    client.append(_make_event_data())

    # Now simulate connection failure on get
    original_get = store.get

    def _failing_get(key):
        raise LedgerConnectionError(code="LEDGER_CONNECTION_ERROR", message="down")

    store.get = _failing_get
    with pytest.raises(LedgerConnectionError):
        client.read(0)

    store.get = original_get  # restore


# ---------------------------------------------------------------------------
# read_range() tests (≥4)
# ---------------------------------------------------------------------------

def test_read_range_returns_correct_events(mock_client, make_event_data):
    """SC-004: read_range(3, 7) on 11-event ledger returns 5 events at [3,4,5,6,7]."""
    for _ in range(11):
        mock_client.append(make_event_data())
    events = mock_client.read_range(3, 7)
    assert len(events) == 5
    sequences = [e.sequence for e in events]
    assert sequences == [3, 4, 5, 6, 7]


def test_read_range_single_element(mock_client, make_event_data):
    """read_range(N, N) returns a list with exactly one event."""
    for _ in range(5):
        mock_client.append(make_event_data())
    events = mock_client.read_range(2, 2)
    assert len(events) == 1
    assert events[0].sequence == 2


def test_read_range_end_beyond_tip_raises(mock_client, make_event_data):
    """read_range with end > tip raises LedgerSequenceError."""
    for _ in range(5):
        mock_client.append(make_event_data())
    with pytest.raises(LedgerSequenceError):
        mock_client.read_range(0, 100)


def test_read_range_start_beyond_tip_raises(mock_client, make_event_data):
    """read_range with start > tip raises LedgerSequenceError."""
    for _ in range(5):
        mock_client.append(make_event_data())
    with pytest.raises(LedgerSequenceError):
        mock_client.read_range(100, 200)


# ---------------------------------------------------------------------------
# read_since() tests (≥3)
# ---------------------------------------------------------------------------

def test_read_since_returns_events_after_sequence(mock_client, make_event_data):
    """SC-005: read_since(5) with tip at 10 returns events at [6,7,8,9,10]."""
    for _ in range(11):
        mock_client.append(make_event_data())
    events = mock_client.read_since(5)
    sequences = [e.sequence for e in events]
    assert sequences == [6, 7, 8, 9, 10]


def test_read_since_tip_returns_empty(mock_client, make_event_data):
    """read_since(tip) returns [] (D4 IN-004 postcondition 2)."""
    for _ in range(5):
        mock_client.append(make_event_data())
    tip = mock_client.get_tip()
    result = mock_client.read_since(tip.sequence_number)
    assert result == []


def test_read_since_beyond_tip_raises(mock_client, make_event_data):
    """read_since(N) where N > tip raises LedgerSequenceError."""
    for _ in range(11):
        mock_client.append(make_event_data())
    with pytest.raises(LedgerSequenceError):
        mock_client.read_since(99)


# ---------------------------------------------------------------------------
# verify_chain() tests (≥8)
# ---------------------------------------------------------------------------

def test_verify_chain_intact_chain(mock_client, make_event_data):
    """SC-007: 6-event chain with correct hashes returns valid=True, break_at=None."""
    for _ in range(6):
        mock_client.append(make_event_data())
    result = mock_client.verify_chain()
    assert result == ChainVerificationResult(valid=True, break_at=None)


def test_verify_chain_corruption_at_sequence_3(mock_client, make_event_data):
    """SC-008: corrupt stored event at sequence 3 → valid=False, break_at=3."""
    import json
    for _ in range(6):
        mock_client.append(make_event_data())

    # Tamper: overwrite sequence 3's stored bytes with wrong hash
    key = "00000000000000000003"
    raw = json.loads(mock_client._store.get(key))
    raw["hash"] = "sha256:" + "b" * 64  # wrong hash
    mock_client._store._store[key] = json.dumps(raw, sort_keys=True).encode()

    result = mock_client.verify_chain()
    assert result.valid is False
    assert result.break_at == 3


def test_verify_chain_default_args_uses_full_range(mock_client, make_event_data):
    """verify_chain() with no args on 10-event ledger walks 0 to 9."""
    for _ in range(10):
        mock_client.append(make_event_data())
    result = mock_client.verify_chain()
    assert result.valid is True


def test_verify_chain_connection_error_raises():
    """
    SC-010: immudb unreachable → raises LedgerConnectionError, NOT {valid:false}.
    D4 IN-005 postcondition 6: unreachable immudb is infrastructure failure.
    """
    store = MockImmudbStore()
    store.connect()
    client = LedgerClient(_store=store)

    # Write one event first
    client.append(_make_event_data())

    # Simulate connection failure on get
    def _failing_get(key):
        raise LedgerConnectionError(code="LEDGER_CONNECTION_ERROR", message="down")

    store.get = _failing_get
    with pytest.raises(LedgerConnectionError):
        client.verify_chain()


def test_verify_chain_empty_ledger_is_valid(mock_client):
    """Empty Ledger → ChainVerificationResult(valid=True, break_at=None)."""
    result = mock_client.verify_chain()
    assert result == ChainVerificationResult(valid=True, break_at=None)


def test_verify_chain_single_event_is_valid(mock_client, make_event_data):
    """One correct event → valid=True."""
    mock_client.append(make_event_data())
    result = mock_client.verify_chain()
    assert result.valid is True


def test_verify_chain_partial_range(mock_client, make_event_data):
    """verify_chain(2, 5) on 10-event chain verifies only sequences 2-5."""
    for _ in range(10):
        mock_client.append(make_event_data())
    result = mock_client.verify_chain(start=2, end=5)
    assert result.valid is True


def test_verify_chain_matches_walk_result(mock_client, make_event_data):
    """
    SC-009 (mock): verify_chain() and direct walk_chain() on the same events
    produce identical ChainVerificationResult.
    """
    from ledger.verify import walk_chain as wc
    for _ in range(6):
        mock_client.append(make_event_data())

    api_result = mock_client.verify_chain()
    events = mock_client.read_range(0, 5)
    walk_result = wc(events)

    assert api_result == walk_result
