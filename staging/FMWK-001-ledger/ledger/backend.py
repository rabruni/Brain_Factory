"""Ledger-owned storage adapter."""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

from ledger.errors import LedgerConnectionError, LedgerSequenceError
from ledger.serialization import event_key


class ImmudbLedgerBackend:
    def __init__(
        self,
        *,
        client_factory: Optional[Callable[[str, int], Any]] = None,
        config_provider: Optional[Callable[[], Any]] = None,
        secret_provider: Optional[Callable[[str], Any]] = None,
        logger: Any = None,
    ) -> None:
        self._client_factory = client_factory or self._default_client_factory
        self._config_provider = config_provider or self._default_config_provider
        self._secret_provider = secret_provider or self._default_secret_provider
        self._logger = logger
        self._client = None

    def _default_config_provider(self) -> Any:
        from platform_sdk import get_config

        return get_config()

    def _default_secret_provider(self, key: str) -> Any:
        from platform_sdk import get_secret

        return get_secret(key)

    def _default_logger(self) -> Any:
        from platform_sdk import get_logger

        return get_logger(__name__)

    def _default_client_factory(self, host: str, port: int) -> Any:
        try:
            from immudb.client import ImmuClient  # type: ignore
        except ImportError as exc:
            raise LedgerConnectionError("immudb client library is not installed") from exc
        return ImmuClient(host=host, port=port)

    def _build_client(self) -> Any:
        config = self._config_provider()
        client = self._client_factory(config.immudb_host, config.immudb_port)
        password = self._secret_provider("immudb_password").get_secret_value()
        client.login(config.immudb_username, password)
        database = config.immudb_database
        if not client.use_database(database):
            raise LedgerConnectionError("database '{}' is unavailable".format(database))
        return client

    def connect(self) -> Any:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _invalidate_client(self) -> None:
        self._client = None

    def _run_with_reconnect(self, operation: Callable[[Any], Any]) -> Any:
        for attempt in range(2):
            client = self.connect()
            try:
                return operation(client)
            except LedgerSequenceError:
                raise
            except LedgerConnectionError:
                raise
            except Exception as exc:
                if attempt == 0:
                    self._invalidate_client()
                    continue
                raise LedgerConnectionError(
                    "Ledger operation failed after one reconnect attempt"
                ) from exc
        raise LedgerConnectionError("Ledger operation failed after one reconnect attempt")

    def append_bytes(self, key: str, value: bytes) -> None:
        def operation(client: Any) -> None:
            if hasattr(client, "storage") and key in client.storage:
                raise LedgerSequenceError("Sequence assignment conflict; append rejected.")
            client.set(key=key, value=value)

        self._run_with_reconnect(operation)

    def read_bytes(self, sequence: int) -> bytes:
        def operation(client: Any) -> bytes:
            key = event_key(sequence)
            if hasattr(client, "storage"):
                return client.storage[key]
            result = client.get(key=key)
            if isinstance(result, bytes):
                return result
            if hasattr(result, "value"):
                return result.value
            raise LedgerConnectionError("Unable to read from immudb.")

        return self._run_with_reconnect(operation)

    def read_range_bytes(self, start: int, end: int) -> List[bytes]:
        def operation(client: Any) -> List[bytes]:
            keys = [event_key(sequence) for sequence in range(start, end + 1)]
            if hasattr(client, "storage"):
                return [client.storage[key] for key in keys if key in client.storage]
            return [self.read_bytes(sequence) for sequence in range(start, end + 1)]

        return self._run_with_reconnect(operation)

    def read_since_bytes(self, sequence_number: int) -> List[bytes]:
        start = 0 if sequence_number < 0 else sequence_number + 1
        tip = self.get_tip_bytes()
        if tip is None or start > tip[0]:
            return []
        return self.read_range_bytes(start, tip[0])

    def get_tip_bytes(self) -> Optional[Tuple[int, bytes]]:
        def operation(client: Any) -> Optional[Tuple[int, bytes]]:
            if hasattr(client, "storage"):
                if not client.storage:
                    return None
                keys = sorted(client.storage.keys())
                last_key = keys[-1]
                sequence = int(last_key.split(":")[1])
                return sequence, client.storage[last_key]
            if hasattr(client, "scan"):
                records = list(client.scan(prefix="ledger:"))
                if not records:
                    return None
                last = records[-1]
                key = getattr(last, "key", "")
                value = getattr(last, "value", None)
                sequence = int(str(key).split(":")[1])
                return sequence, value
            raise LedgerConnectionError("Unable to determine ledger tip.")

        return self._run_with_reconnect(operation)


_DEFAULT_BACKEND = None


def _default_backend() -> ImmudbLedgerBackend:
    global _DEFAULT_BACKEND
    if _DEFAULT_BACKEND is None:
        _DEFAULT_BACKEND = ImmudbLedgerBackend()
    return _DEFAULT_BACKEND


def connect() -> Any:
    return _default_backend().connect()


def append_bytes(key: str, value: bytes) -> None:
    _default_backend().append_bytes(key, value)


def read_bytes(sequence: int) -> bytes:
    return _default_backend().read_bytes(sequence)


def read_range_bytes(start: int, end: int) -> List[bytes]:
    return _default_backend().read_range_bytes(start, end)


def read_since_bytes(sequence_number: int) -> List[bytes]:
    return _default_backend().read_since_bytes(sequence_number)


def get_tip_bytes() -> Optional[Tuple[int, bytes]]:
    return _default_backend().get_tip_bytes()
