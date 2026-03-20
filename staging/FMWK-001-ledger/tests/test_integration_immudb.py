from __future__ import annotations

import pytest

from ledger.backend import ImmudbLedgerBackend
from ledger.errors import LedgerConnectionError
from ledger.service import Ledger


pytestmark = pytest.mark.integration


@pytest.fixture
def integration_backend():
    try:
        backend = ImmudbLedgerBackend()
        backend.connect()
    except LedgerConnectionError as exc:
        pytest.skip(str(exc))
    return backend


def test_integration_append_read_verify_round_trip(integration_backend, make_request) -> None:
    ledger = Ledger(backend=integration_backend)
    sequence, appended = ledger.append(make_request(20))

    assert ledger.read(sequence) == appended
    assert ledger.verify_chain().valid is True


def test_integration_missing_database_contract() -> None:
    class BadConfig:
        immudb_host = "localhost"
        immudb_port = 3322
        immudb_database = "missing"
        immudb_username = "immudb"
        environment = "test"
        is_production = False

    backend = ImmudbLedgerBackend(config_provider=lambda: BadConfig())

    with pytest.raises(LedgerConnectionError):
        backend.connect()


def test_integration_reconnect_once_contract(make_request) -> None:
    pytest.skip("Environment-specific reconnect simulation is not available in this workspace")
