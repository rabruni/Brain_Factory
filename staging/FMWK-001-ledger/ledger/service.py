"""Public ledger service."""

from __future__ import annotations

import json
from threading import Lock
from typing import Iterable, List, Optional

from ledger import backend as backend_module
from ledger.errors import LedgerCorruptionError, LedgerSerializationError
from ledger.models import (
    ChainVerificationResult,
    GENESIS_PREVIOUS_HASH,
    LedgerAppendRequest,
    LedgerEvent,
    LedgerTip,
    event_from_dict,
)
from ledger.serialization import canonical_event_bytes, compute_event_hash, event_key


class Ledger:
    def __init__(self, backend=None) -> None:
        self._backend = backend or backend_module
        self._append_lock = Lock()

    def append(self, request: LedgerAppendRequest):
        with self._append_lock:
            tip = self.get_tip()
            sequence = 0 if tip is None else tip.sequence_number + 1
            previous_hash = GENESIS_PREVIOUS_HASH if tip is None else tip.hash
            event = LedgerEvent(
                event_id=request.event_id,
                sequence=sequence,
                event_type=request.event_type,
                schema_version=request.schema_version,
                timestamp=request.timestamp,
                provenance=request.provenance,
                previous_hash=previous_hash,
                payload=request.payload,
                hash=GENESIS_PREVIOUS_HASH,
            )
            event_hash = compute_event_hash(event)
            event = LedgerEvent(
                event_id=event.event_id,
                sequence=event.sequence,
                event_type=event.event_type,
                schema_version=event.schema_version,
                timestamp=event.timestamp,
                provenance=event.provenance,
                previous_hash=event.previous_hash,
                payload=event.payload,
                hash=event_hash,
            )
            payload = self._serialize_event(event)
            self._backend.append_bytes(event_key(sequence), payload)
            return sequence, event

    def read(self, sequence_number: int) -> LedgerEvent:
        return self._event_from_bytes(self._backend.read_bytes(sequence_number))

    def read_range(self, start: int, end: int) -> List[LedgerEvent]:
        return [self._event_from_bytes(item) for item in self._backend.read_range_bytes(start, end)]

    def read_since(self, sequence_number: int) -> List[LedgerEvent]:
        return [self._event_from_bytes(item) for item in self._backend.read_since_bytes(sequence_number)]

    def get_tip(self) -> Optional[LedgerTip]:
        tip = self._backend.get_tip_bytes()
        if tip is None:
            return None
        sequence_number, payload = tip
        event = self._event_from_bytes(payload)
        return LedgerTip(sequence_number=sequence_number, hash=event.hash)

    def verify_chain(
        self,
        start: Optional[int] = None,
        end: Optional[int] = None,
        source_mode: str = "online",
        offline_events: Optional[List[LedgerEvent]] = None,
    ) -> ChainVerificationResult:
        events = self._verification_events(start=start, end=end, source_mode=source_mode, offline_events=offline_events)
        if not events:
            return ChainVerificationResult(valid=True, start=start, end=end)
        for index, event in enumerate(events):
            expected_previous_hash = GENESIS_PREVIOUS_HASH if index == 0 else events[index - 1].hash
            if start not in (None, 0) and index == 0:
                expected_previous_hash = event.previous_hash
            if event.previous_hash != expected_previous_hash:
                return ChainVerificationResult(valid=False, break_at=event.sequence, start=events[0].sequence, end=events[-1].sequence)
            if compute_event_hash(event) != event.hash:
                return ChainVerificationResult(valid=False, break_at=event.sequence, start=events[0].sequence, end=events[-1].sequence)
        return ChainVerificationResult(valid=True, start=events[0].sequence, end=events[-1].sequence)

    def _verification_events(
        self,
        *,
        start: Optional[int],
        end: Optional[int],
        source_mode: str,
        offline_events: Optional[List[LedgerEvent]],
    ) -> List[LedgerEvent]:
        if source_mode == "online":
            tip = self.get_tip()
            if tip is None:
                return []
            effective_start = 0 if start is None else start
            effective_end = tip.sequence_number if end is None else end
            return self.read_range(effective_start, effective_end)
        if source_mode != "offline_export":
            raise ValueError("source_mode must be 'online' or 'offline_export'")
        if offline_events is None:
            raise ValueError("offline_events are required for offline_export verification")
        events = offline_events
        if start is not None:
            events = [event for event in events if event.sequence >= start]
        if end is not None:
            events = [event for event in events if event.sequence <= end]
        return events

    def _serialize_event(self, event: LedgerEvent) -> bytes:
        try:
            return json.dumps(
                event.to_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise LedgerSerializationError("Unable to serialize persisted ledger event") from exc

    def _event_from_bytes(self, payload: bytes) -> LedgerEvent:
        try:
            data = json.loads(payload.decode("utf-8"))
            return event_from_dict(data)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise LedgerCorruptionError("Stored ledger event is corrupt") from exc
