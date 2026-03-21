"""
ledger.verify — Hash chain integrity verification.

walk_chain() is a pure function: no storage access, no network calls.
It accepts a list of LedgerEvent objects and verifies:
  1. Each event's hash equals canonical_hash(event without 'hash' field).
  2. Each event's previous_hash equals the prior event's hash.
  3. The genesis event's previous_hash equals the empty-Ledger sentinel.

Returns ChainVerificationResult:
  - valid=True, break_at=None if the chain is intact.
  - valid=False, break_at=N where N is the LOWEST corrupted sequence.

This function is called from:
  - LedgerClient.verify_chain() after fetching events from immudb.
  - python -m ledger --verify (cold-storage CLI, no kernel process required).

Hash chain invariants (D3):
  event[0].previous_hash = "sha256:" + "0" * 64  (genesis sentinel)
  event[N].previous_hash = event[N-1].hash
  event[N].hash          = canonical_hash(event[N] as dict, excluding 'hash' field)
"""
from __future__ import annotations

from dataclasses import asdict
from typing import List, Optional

from ledger.models import ChainVerificationResult, LedgerEvent, Provenance
from ledger.serialization import canonical_hash, GENESIS_PREVIOUS_HASH


def _event_to_dict(event: LedgerEvent) -> dict:
    """
    Convert LedgerEvent to a flat dict suitable for canonical hashing.
    Provenance is serialized as a nested dict with fields in their canonical form.
    The 'hash' field is included — canonical_hash() excludes it automatically.
    """
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "hash": event.hash,
        "payload": event.payload,
        "previous_hash": event.previous_hash,
        "provenance": {
            "actor": event.provenance.actor,
            "framework_id": event.provenance.framework_id,
            "pack_id": event.provenance.pack_id,
        },
        "schema_version": event.schema_version,
        "sequence": event.sequence,
        "timestamp": event.timestamp,
    }


def walk_chain(events: List[LedgerEvent]) -> ChainVerificationResult:
    """
    Verify the integrity of a sequence of LedgerEvents.

    For each event:
      - Recomputes canonical_hash(event_dict_without_hash_field)
      - Checks recomputed hash == event.hash
      - Checks event.previous_hash == prior event's hash
        (or genesis sentinel for the first event)

    Args:
        events: List of LedgerEvents in ascending sequence order.
                May be a subrange (e.g. sequences 2–5 of a 10-event chain);
                the first event in the list is treated as the chain anchor.

    Returns:
        ChainVerificationResult:
          valid=True, break_at=None  — all events pass
          valid=False, break_at=N   — first corrupted event's sequence number
    """
    if not events:
        return ChainVerificationResult(valid=True, break_at=None)

    prev_hash: Optional[str] = None  # Will be set after first event

    for i, event in enumerate(events):
        event_dict = _event_to_dict(event)
        expected_hash = canonical_hash(event_dict)

        # Check: stored hash matches recomputed hash
        if event.hash != expected_hash:
            return ChainVerificationResult(valid=False, break_at=event.sequence)

        # Check: previous_hash links correctly
        if i == 0:
            # First event in the walked range: check genesis sentinel
            # (only meaningful when walking from sequence 0)
            if event.sequence == 0 and event.previous_hash != GENESIS_PREVIOUS_HASH:
                return ChainVerificationResult(valid=False, break_at=event.sequence)
        else:
            # Subsequent events: previous_hash must equal prior event's hash
            if event.previous_hash != prev_hash:
                return ChainVerificationResult(valid=False, break_at=event.sequence)

        prev_hash = event.hash

    return ChainVerificationResult(valid=True, break_at=None)
