from __future__ import annotations

from ledger.service import Ledger


def test_verify_chain_online_valid_chain(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)
    for index in range(3):
        ledger.append(make_request(index))

    result = ledger.verify_chain()

    assert result.valid is True
    assert result.start == 0
    assert result.end == 2


def test_verify_chain_online_offline_matches(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)
    for index in range(3):
        ledger.append(make_request(index))

    online = ledger.verify_chain()
    offline = ledger.verify_chain(
        source_mode="offline_export",
        offline_events=ledger.read_since(-1),
    )

    assert offline == online


def test_verify_chain_returns_first_break_at_sequence(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)
    for index in range(3):
        ledger.append(make_request(index))
    in_memory_backend.corrupt(1, "previous_hash", "sha256:" + ("f" * 64))

    result = ledger.verify_chain()

    assert result.valid is False
    assert result.break_at == 1
