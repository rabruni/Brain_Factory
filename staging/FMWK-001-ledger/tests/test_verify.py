"""
test_verify.py — Tests for walk_chain() in ledger.verify.

All tests use constructed LedgerEvent lists (no immudb, no LedgerClient).
≥8 tests required.

Helper: build_valid_chain(n) constructs a correct n-event chain using
canonical_hash() so the hashes are real and consistent.
"""
import pytest

from ledger.errors import LedgerCorruptionError
from ledger.models import (
    ChainVerificationResult,
    LedgerEvent,
    Provenance,
)
from ledger.serialization import canonical_hash, GENESIS_PREVIOUS_HASH
from ledger.verify import walk_chain, _event_to_dict


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_provenance(framework_id: str = "FMWK-002") -> Provenance:
    return Provenance(framework_id=framework_id, actor="system", pack_id=None)


def _make_event(
    sequence: int,
    previous_hash: str,
    event_type: str = "session_start",
    event_id_suffix: str = "",
) -> LedgerEvent:
    """Build a LedgerEvent with a correct hash given the other fields."""
    event_id = f"00000000-0000-7000-0000-{sequence:012d}{event_id_suffix}"
    prov = _make_provenance()
    # Build partial event dict (without hash) to compute canonical hash
    partial = {
        "event_id": event_id,
        "event_type": event_type,
        "payload": {},
        "previous_hash": previous_hash,
        "provenance": {
            "actor": prov.actor,
            "framework_id": prov.framework_id,
            "pack_id": prov.pack_id,
        },
        "schema_version": "1.0.0",
        "sequence": sequence,
        "timestamp": "2026-03-21T03:21:00Z",
    }
    h = canonical_hash(partial)
    return LedgerEvent(
        event_id=event_id,
        sequence=sequence,
        event_type=event_type,
        schema_version="1.0.0",
        timestamp="2026-03-21T03:21:00Z",
        provenance=prov,
        previous_hash=previous_hash,
        payload={},
        hash=h,
    )


def build_valid_chain(n: int) -> list:
    """Build a correctly-hashed chain of n LedgerEvents starting at sequence 0."""
    events = []
    prev_hash = GENESIS_PREVIOUS_HASH
    for seq in range(n):
        event = _make_event(sequence=seq, previous_hash=prev_hash)
        prev_hash = event.hash
        events.append(event)
    return events


# ---------------------------------------------------------------------------
# walk_chain tests
# ---------------------------------------------------------------------------

def test_empty_list_returns_valid():
    """walk_chain([]) must return valid=True, break_at=None (D4 IN-005)."""
    result = walk_chain([])
    assert result == ChainVerificationResult(valid=True, break_at=None)


def test_single_intact_genesis_event():
    """A single correctly-hashed genesis event must be valid."""
    chain = build_valid_chain(1)
    result = walk_chain(chain)
    assert result == ChainVerificationResult(valid=True, break_at=None)


def test_intact_chain_six_events():
    """A 6-event chain with correct hashes and links must be valid."""
    chain = build_valid_chain(6)
    result = walk_chain(chain)
    assert result == ChainVerificationResult(valid=True, break_at=None)


def test_corrupted_hash_at_sequence_3():
    """
    If the stored hash of event at sequence 3 is wrong, walk_chain returns
    valid=False, break_at=3.
    """
    chain = build_valid_chain(6)
    # Corrupt the hash at index 3 (sequence 3)
    chain[3] = LedgerEvent(
        event_id=chain[3].event_id,
        sequence=chain[3].sequence,
        event_type=chain[3].event_type,
        schema_version=chain[3].schema_version,
        timestamp=chain[3].timestamp,
        provenance=chain[3].provenance,
        previous_hash=chain[3].previous_hash,
        payload=chain[3].payload,
        hash="sha256:" + "b" * 64,  # wrong hash
    )
    result = walk_chain(chain)
    assert result.valid is False
    assert result.break_at == 3


def test_broken_link_at_sequence_3():
    """
    If event at sequence 3 has a wrong previous_hash (broken link), walk_chain
    returns valid=False, break_at=3.
    """
    chain = build_valid_chain(6)
    # Recompute event 3 with a wrong previous_hash
    bad_prev = "sha256:" + "c" * 64
    bad_event = _make_event(sequence=3, previous_hash=bad_prev)
    chain[3] = bad_event
    result = walk_chain(chain)
    assert result.valid is False
    assert result.break_at == 3


def test_returns_lowest_failure_sequence():
    """
    When multiple events are corrupted, break_at is the LOWEST sequence.
    """
    chain = build_valid_chain(8)
    # Corrupt events at sequences 2 and 5
    chain[2] = LedgerEvent(
        event_id=chain[2].event_id, sequence=2, event_type=chain[2].event_type,
        schema_version=chain[2].schema_version, timestamp=chain[2].timestamp,
        provenance=chain[2].provenance, previous_hash=chain[2].previous_hash,
        payload=chain[2].payload, hash="sha256:" + "d" * 64,
    )
    chain[5] = LedgerEvent(
        event_id=chain[5].event_id, sequence=5, event_type=chain[5].event_type,
        schema_version=chain[5].schema_version, timestamp=chain[5].timestamp,
        provenance=chain[5].provenance, previous_hash=chain[5].previous_hash,
        payload=chain[5].payload, hash="sha256:" + "e" * 64,
    )
    result = walk_chain(chain)
    assert result.valid is False
    assert result.break_at == 2  # lowest failure


def test_single_event_wrong_hash():
    """A single event with a wrong hash returns valid=False, break_at=0."""
    prov = _make_provenance()
    event = LedgerEvent(
        event_id="test-id", sequence=0, event_type="session_start",
        schema_version="1.0.0", timestamp="2026-03-21T03:21:00Z",
        provenance=prov, previous_hash=GENESIS_PREVIOUS_HASH,
        payload={}, hash="sha256:" + "f" * 64,  # wrong
    )
    result = walk_chain([event])
    assert result.valid is False
    assert result.break_at == 0


def test_genesis_wrong_previous_hash():
    """
    Genesis event (sequence=0) with a wrong previous_hash (not the sentinel)
    returns valid=False, break_at=0.
    """
    wrong_prev = "sha256:" + "a" * 64  # not the genesis sentinel
    event = _make_event(sequence=0, previous_hash=wrong_prev)
    result = walk_chain([event])
    assert result.valid is False
    assert result.break_at == 0


def test_walk_chain_partial_range():
    """
    walk_chain() on a subrange (e.g. events 3–6 of a 10-event chain) must
    verify the internal links but not require sequence 3 to have the genesis sentinel.
    """
    chain = build_valid_chain(10)
    # Walk only events 3–6 (subrange — first event in slice is not genesis)
    subrange = chain[3:7]
    result = walk_chain(subrange)
    assert result == ChainVerificationResult(valid=True, break_at=None)
