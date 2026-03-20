from __future__ import annotations

import pytest

from ledger.errors import LedgerSerializationError, LedgerSequenceError
from ledger.models import GENESIS_PREVIOUS_HASH
from ledger.service import Ledger


def test_genesis_append_assigns_sequence_zero(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)

    sequence, _event = ledger.append(make_request(0))

    assert sequence == 0


def test_genesis_append_uses_zero_previous_hash(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)

    _sequence, event = ledger.append(make_request(0))

    assert event.previous_hash == GENESIS_PREVIOUS_HASH


def test_append_links_previous_hash_to_prior_event(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)

    _sequence, first = ledger.append(make_request(0))
    _sequence, second = ledger.append(make_request(1))

    assert second.previous_hash == first.hash


def test_append_rejects_sequence_conflict(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)
    ledger.append(make_request(0))
    in_memory_backend.conflict_keys.add("ledger:00000000000000000001")

    with pytest.raises(LedgerSequenceError):
        ledger.append(make_request(1))

    assert ledger.get_tip().sequence_number == 0


def test_append_rejects_serialization_failure(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)
    ledger.append(make_request(0))

    with pytest.raises(LedgerSerializationError):
        ledger.append(
            make_request(
                1,
                event_type="custom_event",
                payload={"bad": object()},
            )
        )

    assert ledger.get_tip().sequence_number == 0


def test_append_records_snapshot_created_event(in_memory_backend, make_request, zero_hash) -> None:
    ledger = Ledger(backend=in_memory_backend)

    sequence, event = ledger.append(
        make_request(
            0,
            event_type="snapshot_created",
            payload={
                "snapshot_sequence": 0,
                "snapshot_path": "/snapshots/0.snapshot",
                "snapshot_hash": zero_hash,
                "created_at": "2026-03-19T23:40:00Z",
            },
        )
    )

    assert sequence == 0
    assert event.event_type == "snapshot_created"
    assert event.payload.snapshot_path == "/snapshots/0.snapshot"


def test_read_returns_exact_stored_event(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)
    _sequence, appended = ledger.append(make_request(0))

    read_back = ledger.read(0)

    assert read_back == appended


def test_read_range_returns_ascending_sequence_order(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)
    for index in range(3):
        ledger.append(make_request(index))

    events = ledger.read_range(0, 2)

    assert [event.sequence for event in events] == [0, 1, 2]


def test_read_since_minus_one_replays_from_genesis(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)
    for index in range(3):
        ledger.append(make_request(index))

    events = ledger.read_since(-1)

    assert [event.sequence for event in events] == [0, 1, 2]


def test_read_since_snapshot_boundary_returns_post_snapshot_events(
    in_memory_backend, make_request, zero_hash
) -> None:
    ledger = Ledger(backend=in_memory_backend)
    ledger.append(make_request(0))
    sequence, _snapshot = ledger.append(
        make_request(
            1,
            event_type="snapshot_created",
            payload={
                "snapshot_sequence": 1,
                "snapshot_path": "/snapshots/1.snapshot",
                "snapshot_hash": zero_hash,
                "created_at": "2026-03-19T23:41:00Z",
            },
        )
    )
    ledger.append(make_request(2))

    events = ledger.read_since(sequence)

    assert [event.sequence for event in events] == [2]


def test_get_tip_returns_latest_sequence_and_hash(in_memory_backend, make_request) -> None:
    ledger = Ledger(backend=in_memory_backend)
    _sequence, event = ledger.append(make_request(0))

    tip = ledger.get_tip()

    assert tip.sequence_number == 0
    assert tip.hash == event.hash
