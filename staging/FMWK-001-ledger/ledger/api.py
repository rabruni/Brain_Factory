"""
ledger.api — LedgerClient: the 6-method public interface for FMWK-001-ledger.

LedgerClient is the ONLY public entry point for the Ledger primitive.
All state mutations in DoPeJarMo enter via LedgerClient.append() from the
Write Path (FMWK-002). All reads (Graph replay, CLI verification) use the
five read/verify methods.

Hash chain construction (append() critical path):
  1. validate_event_data(event_data)     — raises LedgerSerializationError if invalid
  2. acquire store._lock (non-blocking) — raises LedgerSequenceError if contested
  3. tip = _get_tip_unlocked()           — reads current tip
  4. sequence = tip.sequence_number + 1
  5. event_id = new_id(kind="uuid7")    — UUID v7 via platform_sdk
  6. previous_hash = tip.hash
  7. build full event dict (all fields except hash)
  8. hash = canonical_hash(event_dict)
  9. full_event_dict["hash"] = hash
  10. value = canonical_json(full_event_dict).encode("utf-8")
  11. store.set(f"{sequence:020d}", value)
  12. release lock (via finally block)
  13. return sequence

Single-writer invariant (D5 RQ-001):
  The threading.Lock is acquired NON-BLOCKINGLY (blocking=False). If already
  held, LedgerSequenceError is raised immediately. This enforces the
  single-writer contract: FMWK-002 Write Path is the sole caller of append();
  concurrent callers indicate a programming error, not a retry opportunity.

  ASSUMPTION: single kernel process per deployment. Multi-process deployment
  would require replacing the in-process mutex with a server-side transaction
  (e.g. immudb ExecAll or VerifiedSet) — see D5 RQ-001.

Platform SDK contract (D1 Article 10):
  - ID generation: platform_sdk.tier0_core.ids.new_id(kind="uuid7")
  - Config: platform_sdk.tier0_core.config.PlatformConfig
  No direct import of uuid, os.getenv, or immudb outside store.py.
"""
from __future__ import annotations

import json
from typing import List, Optional, TYPE_CHECKING

from ledger.errors import (
    LedgerConnectionError,
    LedgerSequenceError,
    LedgerSerializationError,
)
from ledger.models import (
    ChainVerificationResult,
    LedgerEvent,
    Provenance,
    TipRecord,
)
from ledger.schemas import validate_event_data
from ledger.serialization import canonical_hash, canonical_json, GENESIS_PREVIOUS_HASH
from ledger.verify import walk_chain

# Platform SDK imports — all ID generation through platform_sdk (D1 Article 10)
from platform_sdk.tier0_core.ids import new_id


class LedgerClient:
    """
    Public interface for the Ledger primitive (FMWK-001).

    Exposes 6 methods:
      append(event_data) -> int
      read(sequence_number) -> LedgerEvent
      read_range(start, end) -> list[LedgerEvent]
      read_since(sequence_number) -> list[LedgerEvent]
      verify_chain(start, end) -> ChainVerificationResult
      get_tip() -> TipRecord

    Args:
        config: PlatformConfig — provides immudb connection params. Used to
                create a real ImmudbStore when _store is None.
        _store: Optional injected store for testing. If provided, config
                is not required. The store must already be connected.
    """

    def __init__(self, config=None, _store=None) -> None:
        if _store is not None:
            self._store = _store
        else:
            if config is None:
                from platform_sdk.tier0_core.config import get_config
                config = get_config()
            from ledger.store import ImmudbStore
            self._store = ImmudbStore(config=config)

    def connect(self) -> None:
        """
        Connect the underlying store to immudb.
        Not required when _store is injected (test mode).
        Raises LedgerConnectionError if immudb is unreachable or database absent.
        """
        self._store.connect()

    # ------------------------------------------------------------------
    # get_tip() — T-007
    # ------------------------------------------------------------------

    def get_tip(self) -> TipRecord:
        """
        Return the current tip of the Ledger.

        Empty Ledger sentinel (D6 CLR-002):
            TipRecord(sequence_number=-1, hash="sha256:" + "0" * 64)
        This sentinel lets the Write Path compute next_sequence = 0 for the
        genesis event without a special case.

        Returns:
            TipRecord: Current highest sequence and its hash.

        Raises:
            LedgerConnectionError: If immudb is unreachable.
        """
        return self._get_tip_unlocked()

    def _get_tip_unlocked(self) -> TipRecord:
        """
        Internal: get tip WITHOUT acquiring the lock.
        Called from within append()'s locked critical section.
        """
        count = self._store.get_count()
        if count == 0:
            return TipRecord(
                sequence_number=-1,
                hash=GENESIS_PREVIOUS_HASH,
            )
        # The tip is at the highest sequence: count - 1
        tip_key = f"{count - 1:020d}"
        value = self._store.get(tip_key)
        event_dict = json.loads(value.decode("utf-8"))
        return TipRecord(
            sequence_number=event_dict["sequence"],
            hash=event_dict["hash"],
        )

    # ------------------------------------------------------------------
    # append() — T-008
    # ------------------------------------------------------------------

    def append(self, event_data: dict) -> int:
        """
        Append a new event to the Ledger.

        Validates event_data, computes hash chain fields, and writes to immudb.
        Returns the assigned sequence number (0 for genesis).

        The write lock (store._lock) is acquired NON-BLOCKINGLY. If already
        held by another caller, LedgerSequenceError is raised immediately.
        The lock wraps the entire tip-read → sequence-compute → write sequence
        to prevent concurrent callers from forking the sequence space.

        Args:
            event_data: dict with required fields:
                event_type, schema_version, timestamp, provenance, payload.
                Fields assigned by Ledger: event_id, sequence, previous_hash, hash.

        Returns:
            int: Assigned sequence number (≥0).

        Raises:
            LedgerSerializationError: Invalid event_data (raised before lock).
            LedgerSequenceError:      Concurrent append detected (lock contended).
            LedgerConnectionError:    immudb unreachable after reconnect+retry.
        """
        # Step 1: Validate BEFORE acquiring lock (D4 ERR-004)
        validate_event_data(event_data)

        # Step 2: Acquire lock NON-BLOCKINGLY (D5 RQ-001 single-writer)
        acquired = self._store._lock.acquire(blocking=False)
        if not acquired:
            raise LedgerSequenceError(
                code="LEDGER_SEQUENCE_ERROR",
                message=(
                    "Concurrent append() detected. "
                    "FMWK-002 Write Path is the sole permitted caller of append(). "
                    "This indicates a programming error."
                ),
            )

        try:
            # Step 3: Read current tip (inside lock — prevents sequence fork)
            tip = self._get_tip_unlocked()

            # Step 4: Compute sequence number
            sequence = tip.sequence_number + 1

            # Step 5: Generate UUID v7 event_id (via platform_sdk — D1 Article 10)
            event_id = new_id(kind="uuid7")

            # Step 6: previous_hash from tip
            previous_hash = tip.hash

            # Step 7: Build full event dict (all fields except hash)
            prov = event_data["provenance"]
            full_event = {
                "event_id": event_id,
                "event_type": event_data["event_type"],
                "payload": event_data["payload"],
                "previous_hash": previous_hash,
                "provenance": {
                    "actor": prov.get("actor"),
                    "framework_id": prov.get("framework_id"),
                    "pack_id": prov.get("pack_id"),  # may be None
                },
                "schema_version": event_data["schema_version"],
                "sequence": sequence,
                "timestamp": event_data["timestamp"],
            }

            # Step 8: Compute hash from canonical JSON (excluding hash field)
            h = canonical_hash(full_event)

            # Step 9: Add hash field
            full_event["hash"] = h

            # Step 10: Encode as canonical JSON bytes
            value = canonical_json(full_event).encode("utf-8")

            # Step 11: Write to store
            key = f"{sequence:020d}"
            self._store.set(key, value)

        finally:
            # Step 12: Always release the lock (even if an exception occurred)
            self._store._lock.release()

        # Step 13: Return assigned sequence number
        return sequence

    # ------------------------------------------------------------------
    # read() — T-009
    # ------------------------------------------------------------------

    def read(self, sequence_number: int) -> LedgerEvent:
        """
        Read a single event by sequence number.

        Args:
            sequence_number: Non-negative integer ≤ tip.sequence_number.

        Returns:
            LedgerEvent with all 9 fields as stored.

        Raises:
            LedgerSequenceError:   sequence_number < 0 or > tip.
            LedgerConnectionError: immudb unreachable.
        """
        if sequence_number < 0:
            raise LedgerSequenceError(
                code="LEDGER_SEQUENCE_ERROR",
                message=f"sequence_number must be ≥ 0, got {sequence_number}",
            )

        tip = self._get_tip_unlocked()
        if sequence_number > tip.sequence_number:
            raise LedgerSequenceError(
                code="LEDGER_SEQUENCE_ERROR",
                message=(
                    f"sequence_number {sequence_number} is beyond tip "
                    f"{tip.sequence_number}"
                ),
            )

        key = f"{sequence_number:020d}"
        value = self._store.get(key)
        return _dict_to_event(json.loads(value.decode("utf-8")))

    # ------------------------------------------------------------------
    # read_range() — T-009
    # ------------------------------------------------------------------

    def read_range(self, start: int, end: int) -> List[LedgerEvent]:
        """
        Read events from sequence `start` to `end`, inclusive on both ends.
        D6 CLR-004: bounds are INCLUSIVE (read_range(3, 7) returns 5 events).

        Args:
            start: First sequence number (inclusive).
            end:   Last sequence number (inclusive).

        Returns:
            list[LedgerEvent]: Events in ascending sequence order.

        Raises:
            LedgerSequenceError:   start or end beyond tip, or start > end.
            LedgerConnectionError: immudb unreachable.
        """
        tip = self._get_tip_unlocked()

        if start > tip.sequence_number:
            raise LedgerSequenceError(
                code="LEDGER_SEQUENCE_ERROR",
                message=f"start {start} is beyond tip {tip.sequence_number}",
            )
        if end > tip.sequence_number:
            raise LedgerSequenceError(
                code="LEDGER_SEQUENCE_ERROR",
                message=f"end {end} is beyond tip {tip.sequence_number}",
            )
        if start > end:
            raise LedgerSequenceError(
                code="LEDGER_SEQUENCE_ERROR",
                message=f"start {start} > end {end}",
            )

        start_key = f"{start:020d}"
        end_key = f"{end:020d}"
        raw_values = self._store.scan(start_key, end_key)
        return [_dict_to_event(json.loads(v.decode("utf-8"))) for v in raw_values]

    # ------------------------------------------------------------------
    # read_since() — T-009
    # ------------------------------------------------------------------

    def read_since(self, sequence_number: int) -> List[LedgerEvent]:
        """
        Read all events with sequence > sequence_number (exclusive lower bound).
        D4 IN-004: read_since(5) returns events at sequences [6, 7, 8, ...].

        Args:
            sequence_number: Lower bound (exclusive). Must be ≤ tip.sequence_number.

        Returns:
            list[LedgerEvent]: Events from sequence_number+1 to tip, inclusive.
                               Empty list if sequence_number == tip.sequence_number.

        Raises:
            LedgerSequenceError:   sequence_number > tip.
            LedgerConnectionError: immudb unreachable.
        """
        tip = self._get_tip_unlocked()

        if sequence_number > tip.sequence_number:
            raise LedgerSequenceError(
                code="LEDGER_SEQUENCE_ERROR",
                message=(
                    f"sequence_number {sequence_number} is beyond tip "
                    f"{tip.sequence_number}"
                ),
            )

        # read_since(tip) → empty list (D4 IN-004 postcondition 2)
        if sequence_number == tip.sequence_number:
            return []

        # Return events (sequence_number+1) through tip (inclusive)
        return self.read_range(sequence_number + 1, tip.sequence_number)

    # ------------------------------------------------------------------
    # verify_chain() — T-010
    # ------------------------------------------------------------------

    def verify_chain(
        self, start: int = 0, end: Optional[int] = None
    ) -> ChainVerificationResult:
        """
        Verify the hash chain integrity for events in [start, end].

        Fetches events from immudb via read_range(), then delegates to
        walk_chain() for pure hash verification (no storage access there).

        Args:
            start: First sequence to verify (default: 0).
            end:   Last sequence to verify (default: tip.sequence_number).

        Returns:
            ChainVerificationResult:
              valid=True, break_at=None  — chain intact.
              valid=False, break_at=N   — first corrupted sequence.

        Raises:
            LedgerConnectionError: immudb unreachable (NOT returned as
                                   ChainVerificationResult(valid=False) — this
                                   is an infrastructure failure, not corruption).
                                   D4 IN-005 postcondition 6.
        """
        # Raises LedgerConnectionError if immudb is down
        tip = self._get_tip_unlocked()

        # Empty Ledger is trivially valid
        if tip.sequence_number < 0:
            return ChainVerificationResult(valid=True, break_at=None)

        if end is None:
            end = tip.sequence_number

        # read_range raises LedgerConnectionError if immudb is down
        # (propagated directly — NOT converted to ChainVerificationResult)
        events = self.read_range(start, end)

        # Pure function — no immudb access
        return walk_chain(events)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _dict_to_event(d: dict) -> LedgerEvent:
    """Deserialize a canonical JSON dict into a LedgerEvent dataclass."""
    prov_dict = d["provenance"]
    prov = Provenance(
        framework_id=prov_dict["framework_id"],
        actor=prov_dict["actor"],
        pack_id=prov_dict.get("pack_id"),
    )
    return LedgerEvent(
        event_id=d["event_id"],
        sequence=d["sequence"],
        event_type=d["event_type"],
        schema_version=d["schema_version"],
        timestamp=d["timestamp"],
        provenance=prov,
        previous_hash=d["previous_hash"],
        payload=d["payload"],
        hash=d["hash"],
    )
