"""Online and offline chain verification for FMWK-001-ledger."""

from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any, Iterable, Mapping

from ledger.errors import LedgerSerializationError
from ledger.models import LedgerEvent, Provenance, VerificationResult
from ledger.serialization import compute_event_hash


def _coerce_event(item: Any) -> LedgerEvent:
    if isinstance(item, LedgerEvent):
        return item
    if isinstance(item, bytes):
        try:
            payload = json.loads(item.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LedgerSerializationError(f"event bytes cannot be parsed: {error}") from error
        return _coerce_event(payload)
    if isinstance(item, Mapping):
        payload = dict(item)
        provenance = payload.get("provenance")
        if isinstance(provenance, Mapping):
            payload["provenance"] = Provenance(**dict(provenance))
        return LedgerEvent(**payload)
    raise LedgerSerializationError("offline verification requires event bytes or event objects")


def verify_events(events: Iterable[Any]) -> VerificationResult:
    materialized = [_coerce_event(item) for item in events]
    if not materialized:
        return VerificationResult(valid=True, start_sequence=0, end_sequence=0)

    previous_hash: str | None = None
    for event in materialized:
        if compute_event_hash(event) != event.hash:
            return VerificationResult(
                valid=False,
                start_sequence=materialized[0].sequence,
                end_sequence=materialized[-1].sequence,
                break_at=event.sequence,
            )
        if previous_hash is not None and event.previous_hash != previous_hash:
            return VerificationResult(
                valid=False,
                start_sequence=materialized[0].sequence,
                end_sequence=materialized[-1].sequence,
                break_at=event.sequence,
            )
        previous_hash = event.hash

    return VerificationResult(
        valid=True,
        start_sequence=materialized[0].sequence,
        end_sequence=materialized[-1].sequence,
    )


def verify_chain(source: Any, start: int | None = None, end: int | None = None, source_mode: str = "online") -> VerificationResult:
    if source_mode == "online":
        tip = source.get_tip()
        actual_start = 0 if start is None else start
        actual_end = tip.sequence_number if end is None else end
        return verify_events(source.read_range(actual_start, actual_end))

    if source_mode == "offline":
        events = [_coerce_event(item) for item in source]
        filtered = [
            event
            for event in events
            if (start is None or event.sequence >= start) and (end is None or event.sequence <= end)
        ]
        return verify_events(filtered)

    raise LedgerSerializationError(f"unsupported source_mode {source_mode}")
