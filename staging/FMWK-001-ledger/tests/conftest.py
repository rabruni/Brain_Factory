"""
conftest.py — Test fixtures for FMWK-001-ledger.

Sets up:
- sys.path so platform_sdk and ledger are importable
- PLATFORM_ENVIRONMENT=test env var
- MockImmudbStore: in-memory drop-in for ImmudbStore
- Common fixtures: mock_store, mock_client, make_event_data
"""
import os
import sys
import threading

# --- Path setup ---------------------------------------------------------------
# Add dopejar root so platform_sdk is importable without installing it.
_DOPEJAR_ROOT = "/Users/raymondbruni/dopejar"
if _DOPEJAR_ROOT not in sys.path:
    sys.path.insert(0, _DOPEJAR_ROOT)

# Add staging root so `ledger` package is importable.
_STAGING_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STAGING_ROOT not in sys.path:
    sys.path.insert(0, _STAGING_ROOT)

# Set test environment before any platform_sdk imports resolve config.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("PLATFORM_ENVIRONMENT", "test")

# --- Imports ------------------------------------------------------------------
import pytest

from ledger.errors import LedgerConnectionError, LedgerSequenceError


# --- MockImmudbStore ----------------------------------------------------------

class MockImmudbStore:
    """
    In-memory drop-in for ImmudbStore used in all unit tests.

    Attributes:
        _lock: threading.Lock — same API as ImmudbStore._lock; LedgerClient
               acquires this lock (non-blocking) to enforce single-writer order.
        _fail_connect: bool — set True to simulate "ledger" DB absent.
        _fail_next_set: bool — set True to make the next set() raise an error.
        _fail_all_sets: bool — set True to make all set() calls fail.
    """

    def __init__(
        self,
        has_database: bool = True,
        fail_all_sets: bool = False,
    ) -> None:
        self._store: dict = {}
        self._lock = threading.Lock()
        self._has_database = has_database
        self._fail_all_sets = fail_all_sets
        self._fail_next_n_sets: int = 0  # fail this many set() calls, then succeed
        self._connected = False

    def connect(self) -> None:
        """
        Simulate connect to immudb. Raises LedgerConnectionError if the
        'ledger' database is absent (D6 CLR-001 fail-fast).
        """
        if not self._has_database:
            raise LedgerConnectionError(
                code="LEDGER_CONNECTION_ERROR",
                message="Database 'ledger' does not exist",
            )
        self._connected = True

    def set(self, key: str, value: bytes) -> None:
        """Store key → value bytes."""
        if self._fail_all_sets:
            raise LedgerConnectionError(
                code="LEDGER_CONNECTION_ERROR",
                message="Simulated connection failure on set()",
            )
        if self._fail_next_n_sets > 0:
            self._fail_next_n_sets -= 1
            raise LedgerConnectionError(
                code="LEDGER_CONNECTION_ERROR",
                message="Simulated transient failure on set()",
            )
        self._store[key] = value

    def get(self, key: str) -> bytes:
        """Retrieve value by key. Raises LedgerSequenceError if not found."""
        if key not in self._store:
            raise LedgerSequenceError(
                code="LEDGER_SEQUENCE_ERROR",
                message=f"Key not found: {key!r}",
            )
        return self._store[key]

    def scan(self, start_key: str, end_key: str) -> list:
        """
        Return list[bytes] for keys in [start_key, end_key] (inclusive),
        sorted in ascending lexicographic order (= ascending sequence order
        for zero-padded 20-char keys).
        """
        result = []
        for k in sorted(self._store.keys()):
            if start_key <= k <= end_key:
                result.append(self._store[k])
        return result

    def get_count(self) -> int:
        """Return the number of stored keys."""
        return len(self._store)


# --- Fixtures -----------------------------------------------------------------

@pytest.fixture
def mock_store() -> MockImmudbStore:
    """Fresh MockImmudbStore per test."""
    store = MockImmudbStore()
    store.connect()
    return store


@pytest.fixture
def failing_store() -> MockImmudbStore:
    """MockImmudbStore where all set() calls fail."""
    store = MockImmudbStore(fail_all_sets=True)
    store.connect()
    return store


@pytest.fixture
def absent_db_store() -> MockImmudbStore:
    """MockImmudbStore where connect() fails (database absent)."""
    return MockImmudbStore(has_database=False)


@pytest.fixture
def mock_client(mock_store):
    """LedgerClient wired with MockImmudbStore (no real immudb)."""
    from ledger.api import LedgerClient
    client = LedgerClient(_store=mock_store)
    return client


@pytest.fixture
def make_event_data():
    """Factory for valid event_data dicts (input to LedgerClient.append)."""
    def _factory(
        event_type: str = "session_start",
        schema_version: str = "1.0.0",
        timestamp: str = "2026-03-21T03:21:00Z",
        framework_id: str = "FMWK-002",
        actor: str = "system",
        pack_id=None,
        payload: dict = None,
    ) -> dict:
        return {
            "event_type": event_type,
            "schema_version": schema_version,
            "timestamp": timestamp,
            "provenance": {
                "framework_id": framework_id,
                "pack_id": pack_id,
                "actor": actor,
            },
            "payload": payload if payload is not None else {},
        }
    return _factory
