"""Canonical ledger serialization."""

from __future__ import annotations

import hashlib
import json

from ledger.errors import LedgerSerializationError
from ledger.models import LedgerEvent


def canonical_event_bytes(event: LedgerEvent) -> bytes:
    try:
        payload = event.to_dict(include_hash=False)
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise LedgerSerializationError("Unable to serialize ledger event canonically") from exc
    return encoded.encode("utf-8")


def compute_event_hash(event: LedgerEvent) -> str:
    digest = hashlib.sha256(canonical_event_bytes(event)).hexdigest()
    return "sha256:" + digest


def event_key(sequence: int) -> str:
    return "ledger:{:020d}".format(sequence)
