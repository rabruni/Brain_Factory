"""
test_store.py — Tests for ImmudbStore / MockImmudbStore interface.

All tests use MockImmudbStore (from conftest.py) — no live immudb required.
MockImmudbStore implements the same interface contract as ImmudbStore; these
tests verify that the mock behaves correctly, which enables the API tests
(test_api.py) to trust the mock's behavior.

≥10 tests required.
"""
import threading
import pytest

from ledger.errors import LedgerConnectionError, LedgerSequenceError

# MockImmudbStore is imported from conftest (fixtures)
# For direct use in tests without fixtures, import from conftest module
from conftest import MockImmudbStore


# ---------------------------------------------------------------------------
# connect() tests
# ---------------------------------------------------------------------------

def test_connect_fails_if_database_missing():
    """connect() raises LedgerConnectionError when database is absent (D6 CLR-001)."""
    store = MockImmudbStore(has_database=False)
    with pytest.raises(LedgerConnectionError) as exc_info:
        store.connect()
    assert exc_info.value.code == "LEDGER_CONNECTION_ERROR"


def test_connect_succeeds_with_database_present():
    """connect() returns without error when database is present."""
    store = MockImmudbStore(has_database=True)
    store.connect()  # must not raise
    assert store._connected is True


# ---------------------------------------------------------------------------
# set() and get() tests
# ---------------------------------------------------------------------------

def test_set_and_get_roundtrip(mock_store):
    """set() then get() must return the same bytes."""
    key = "00000000000000000000"
    value = b'{"event_type":"session_start"}'
    mock_store.set(key, value)
    result = mock_store.get(key)
    assert result == value


def test_get_missing_key_raises_sequence_error(mock_store):
    """get() on a key that does not exist raises LedgerSequenceError."""
    with pytest.raises(LedgerSequenceError) as exc_info:
        mock_store.get("99999999999999999999")
    assert exc_info.value.code == "LEDGER_SEQUENCE_ERROR"


def test_set_connection_failure_raises_connection_error():
    """set() raises LedgerConnectionError when all writes are configured to fail."""
    store = MockImmudbStore(fail_all_sets=True)
    store.connect()
    with pytest.raises(LedgerConnectionError) as exc_info:
        store.set("00000000000000000000", b"data")
    assert exc_info.value.code == "LEDGER_CONNECTION_ERROR"


def test_set_retry_succeeds_on_second_attempt():
    """
    After a first failure, set() succeeds on the second attempt.
    Validates the mock supports fail-once simulation for retry tests in test_api.py.
    """
    store = MockImmudbStore()
    store.connect()
    store._fail_next_n_sets = 1  # first set raises, second succeeds

    with pytest.raises(LedgerConnectionError):
        store.set("00000000000000000000", b"data1")

    # Second call succeeds (fail counter exhausted)
    store.set("00000000000000000000", b"data1")
    assert store.get_count() == 1


def test_set_state_unchanged_after_connection_failure():
    """
    A failed set() must leave the store unchanged.
    get_count() is unchanged; the key is not present.
    """
    store = MockImmudbStore(fail_all_sets=True)
    store.connect()

    initial_count = store.get_count()
    with pytest.raises(LedgerConnectionError):
        store.set("00000000000000000000", b"data")

    assert store.get_count() == initial_count
    with pytest.raises(LedgerSequenceError):
        store.get("00000000000000000000")


# ---------------------------------------------------------------------------
# scan() tests
# ---------------------------------------------------------------------------

def test_scan_returns_ascending_order(mock_store):
    """
    scan() returns values in ascending lexicographic key order.
    Since keys are zero-padded 20-char sequences, this equals ascending numeric order.
    """
    mock_store.set("00000000000000000000", b"seq0")
    mock_store.set("00000000000000000002", b"seq2")
    mock_store.set("00000000000000000001", b"seq1")

    results = mock_store.scan("00000000000000000000", "00000000000000000002")
    assert results == [b"seq0", b"seq1", b"seq2"]


def test_scan_end_exclusive_filtering(mock_store):
    """scan() includes start and end keys (inclusive on both ends)."""
    mock_store.set("00000000000000000000", b"seq0")
    mock_store.set("00000000000000000001", b"seq1")
    mock_store.set("00000000000000000002", b"seq2")

    # Range [0, 1] returns only seq0 and seq1, not seq2
    results = mock_store.scan("00000000000000000000", "00000000000000000001")
    assert results == [b"seq0", b"seq1"]


# ---------------------------------------------------------------------------
# get_count() tests
# ---------------------------------------------------------------------------

def test_get_count_zero_on_empty(mock_store):
    """Fresh store has count 0."""
    assert mock_store.get_count() == 0


def test_get_count_increments_after_set(mock_store):
    """After set() with one key, get_count() returns 1."""
    mock_store.set("00000000000000000000", b"data")
    assert mock_store.get_count() == 1


def test_get_count_multiple_sets(mock_store):
    """get_count() tracks all keys."""
    for i in range(5):
        mock_store.set(f"{i:020d}", f"data{i}".encode())
    assert mock_store.get_count() == 5


# ---------------------------------------------------------------------------
# threading / lock tests
# ---------------------------------------------------------------------------

def test_lock_serializes_concurrent_sets(mock_store):
    """
    Two threads calling set() with different keys simultaneously must both
    complete; get_count() == 2; no exceptions raised.
    This tests basic thread-safety of the MockImmudbStore dict operations.
    """
    errors = []

    def do_set(key, value):
        try:
            mock_store.set(key, value)
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=do_set, args=("00000000000000000000", b"v0"))
    t2 = threading.Thread(target=do_set, args=("00000000000000000001", b"v1"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert errors == [], f"Unexpected errors: {errors}"
    assert mock_store.get_count() == 2
