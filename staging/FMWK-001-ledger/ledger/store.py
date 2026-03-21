"""
ledger.store — ImmudbStore: immudb access abstraction for FMWK-001-ledger.

All immudb-py access is contained in this module. All other ledger modules
access immudb ONLY through ImmudbStore. This is the abstraction boundary.

Design decisions (from D5):
  - threading.Lock (_lock) lives on ImmudbStore; LedgerClient.append() acquires
    it non-blocking for the entire read-tip → compute → write critical section.
  - Retry policy (D5 RQ-005): one reconnect attempt, one operation retry, then
    raise LedgerConnectionError. The Write Path (FMWK-002) owns further retry.
  - connect() fails fast if database "ledger" does not exist (D6 CLR-001).
    Prevents race conditions when multiple processes attempt simultaneous starts.
  - import immudb is PERMITTED ONLY in this file — it is the abstraction layer.
    All other ledger modules access immudb through ImmudbStore.

ASSUMPTION (D5 RQ-001): Single kernel process per deployment.
  The in-process threading.Lock is sufficient for single-writer enforcement.
  Multi-process deployment would require replacing this with a server-side
  transaction (e.g. immudb ExecAll or VerifiedSet).
"""
import time
import threading
from typing import List, Optional

from ledger.errors import LedgerConnectionError, LedgerSequenceError


class ImmudbStore:
    """
    Wraps immudb-py for key-value operations required by LedgerClient.

    Key format: zero-padded 20-char string (e.g. "00000000000000000005" for seq 5).
    Value format: canonical JSON bytes of full LedgerEvent dict.

    The _lock attribute is a threading.Lock acquired non-blockingly by
    LedgerClient.append() to enforce single-writer discipline.

    Args:
        config: PlatformConfig — provides immudb_host, immudb_port,
                immudb_database, immudb_username, immudb_password.
        _client: Optional injected immudb client (for tests only). If None,
                 a real ImmudbClient is created in connect().
    """

    def __init__(self, config, _client=None) -> None:
        self._config = config
        self._client = _client          # real or injected-for-tests
        self._lock = threading.Lock()   # single-writer mutex (D5 RQ-001)

    def connect(self) -> None:
        """
        Connect to immudb and select the configured database.

        Fails fast with LedgerConnectionError if:
          - immudb is unreachable
          - the configured database (default: "ledger") does not exist

        D6 CLR-001: fail-fast prevents race when multiple agents start
        simultaneously and the database has not been provisioned yet.
        """
        cfg = self._config
        if self._client is None:
            from immudb import ImmudbClient  # noqa: PLC0415 (only in this file)
            try:
                self._client = ImmudbClient(f"{cfg.immudb_host}:{cfg.immudb_port}")
                self._client.login(cfg.immudb_username, cfg.immudb_password)
            except Exception as exc:
                raise LedgerConnectionError(
                    code="LEDGER_CONNECTION_ERROR",
                    message=(
                        f"Cannot connect to immudb at "
                        f"{cfg.immudb_host}:{cfg.immudb_port}: {exc}"
                    ),
                ) from exc

        # Check that the target database exists (fail-fast, D6 CLR-001)
        try:
            db_list = self._client.databaseListV2()
            db_names = [db.name for db in db_list.databases]
        except Exception as exc:
            raise LedgerConnectionError(
                code="LEDGER_CONNECTION_ERROR",
                message=f"Cannot list immudb databases: {exc}",
            ) from exc

        if cfg.immudb_database not in db_names:
            raise LedgerConnectionError(
                code="LEDGER_CONNECTION_ERROR",
                message=(
                    f"Database {cfg.immudb_database!r} does not exist in immudb. "
                    f"Available: {db_names}. Provision the database before starting."
                ),
            )

        try:
            self._client.useDatabase(cfg.immudb_database.encode())
        except Exception as exc:
            raise LedgerConnectionError(
                code="LEDGER_CONNECTION_ERROR",
                message=f"Cannot select database {cfg.immudb_database!r}: {exc}",
            ) from exc

    def set(self, key: str, value: bytes) -> None:
        """
        Write key → value to immudb.

        Retry policy (D5 RQ-005): on gRPC failure, release lock, sleep 1 second,
        reconnect once, retry the write once, raise LedgerConnectionError if
        retry also fails. The caller (LedgerClient.append) holds _lock during
        the entire sequence; it is NOT re-acquired here.

        Args:
            key:   Zero-padded 20-char sequence string.
            value: Canonical JSON bytes of the full LedgerEvent.

        Raises:
            LedgerConnectionError: If immudb is unreachable after one retry.
        """
        try:
            self._client.set(key.encode(), value)
        except Exception as exc:
            # One reconnect + one retry (D5 RQ-005)
            time.sleep(1)
            try:
                self.connect()
                self._client.set(key.encode(), value)
            except LedgerConnectionError:
                raise
            except Exception as retry_exc:
                raise LedgerConnectionError(
                    code="LEDGER_CONNECTION_ERROR",
                    message=f"Write failed after reconnect+retry: {retry_exc}",
                ) from retry_exc

    def get(self, key: str) -> bytes:
        """
        Retrieve value by key.

        Args:
            key: Zero-padded 20-char sequence string.

        Returns:
            bytes: Canonical JSON bytes stored at this key.

        Raises:
            LedgerSequenceError:  If the key does not exist.
            LedgerConnectionError: If immudb is unreachable.
        """
        from immudb.exceptions import ErrKeyNotFound  # noqa: PLC0415

        try:
            result = self._client.get(key.encode())
            return result.value
        except ErrKeyNotFound:
            raise LedgerSequenceError(
                code="LEDGER_SEQUENCE_ERROR",
                message=f"Sequence key not found: {key!r}",
            )
        except Exception as exc:
            raise LedgerConnectionError(
                code="LEDGER_CONNECTION_ERROR",
                message=f"Read failed for key {key!r}: {exc}",
            ) from exc

    def scan(self, start_key: str, end_key: str) -> List[bytes]:
        """
        Retrieve all values for keys in [start_key, end_key] (inclusive),
        returned in ascending lexicographic order.

        Since keys are zero-padded 20-char sequence numbers, lexicographic
        order = numeric order, so the result is ascending by sequence.

        Args:
            start_key: Zero-padded 20-char string (e.g. "00000000000000000003").
            end_key:   Zero-padded 20-char string (e.g. "00000000000000000007").

        Returns:
            list[bytes]: Ordered list of canonical JSON bytes.

        Raises:
            LedgerConnectionError: If immudb is unreachable.
        """
        try:
            raw: dict = self._client.scan(
                key=start_key.encode(),
                prefix=b"",
                desc=False,
                limit=1000,
            )
            # raw is Dict[bytes, bytes]; filter to [start_key, end_key] and sort
            result = []
            for k_bytes in sorted(raw.keys()):
                k = k_bytes.decode("utf-8")
                if start_key <= k <= end_key:
                    result.append(raw[k_bytes])
            return result
        except Exception as exc:
            raise LedgerConnectionError(
                code="LEDGER_CONNECTION_ERROR",
                message=f"Scan failed for range [{start_key}, {end_key}]: {exc}",
            ) from exc

    def get_count(self) -> int:
        """
        Return the number of events stored in the Ledger.

        Implementation: scan all keys with 20-char numeric prefix and count.
        Limit 1000 — sufficient for unit tests. Integration/production callers
        should derive count from get_tip() for large ledgers.

        Raises:
            LedgerConnectionError: If immudb is unreachable.
        """
        try:
            raw: dict = self._client.scan(
                key=b"00000000000000000000",
                prefix=b"",
                desc=False,
                limit=1000,
            )
            # Count only keys that look like zero-padded sequences (20 digits)
            count = 0
            for k_bytes in raw.keys():
                k = k_bytes.decode("utf-8")
                if len(k) == 20 and k.isdigit():
                    count += 1
            return count
        except Exception as exc:
            raise LedgerConnectionError(
                code="LEDGER_CONNECTION_ERROR",
                message=f"get_count failed: {exc}",
            ) from exc
