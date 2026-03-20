from __future__ import annotations

import pytest

from ledger.backend import ImmudbLedgerBackend
from ledger.errors import LedgerConnectionError


class FakeTransportError(Exception):
    pass


class FakeClient:
    def __init__(
        self,
        *,
        append_failures: int = 0,
        database_exists: bool = True,
    ) -> None:
        self.append_failures = append_failures
        self.database_exists = database_exists
        self.storage = {}

    def login(self, username: str, password: str) -> None:
        return None

    def use_database(self, database: str) -> bool:
        return self.database_exists and database == "ledger"

    def set(self, *, key: str, value: bytes) -> None:
        if self.append_failures > 0:
            self.append_failures -= 1
            raise FakeTransportError("transport down")
        self.storage[key] = value


def _config_provider():
    class Config:
        immudb_host = "localhost"
        immudb_port = 3322
        immudb_database = "ledger"
        immudb_username = "immudb"
        environment = "test"
        is_production = False

    return Config()


def _secret_provider(key: str):
    class Secret:
        def get_secret_value(self) -> str:
            return "immudb"

    return Secret()


def test_backend_reconnect_once_then_succeeds() -> None:
    clients = [FakeClient(append_failures=1), FakeClient()]

    backend = ImmudbLedgerBackend(
        client_factory=lambda host, port: clients.pop(0),
        config_provider=_config_provider,
        secret_provider=_secret_provider,
    )

    backend.append_bytes("ledger:00000000000000000000", b"payload")

    assert backend._client is not None
    assert backend._client.storage["ledger:00000000000000000000"] == b"payload"


def test_backend_reconnect_once_then_fails_closed() -> None:
    clients = [FakeClient(append_failures=1), FakeClient(append_failures=1)]

    backend = ImmudbLedgerBackend(
        client_factory=lambda host, port: clients.pop(0),
        config_provider=_config_provider,
        secret_provider=_secret_provider,
    )

    with pytest.raises(LedgerConnectionError, match="after one reconnect attempt"):
        backend.append_bytes("ledger:00000000000000000000", b"payload")


def test_backend_missing_database_fails_fast() -> None:
    backend = ImmudbLedgerBackend(
        client_factory=lambda host, port: FakeClient(database_exists=False),
        config_provider=_config_provider,
        secret_provider=_secret_provider,
    )

    with pytest.raises(LedgerConnectionError, match="database 'ledger' is unavailable"):
        backend.connect()
