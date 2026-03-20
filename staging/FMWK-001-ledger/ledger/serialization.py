"""Canonical event serialization helpers for FMWK-001-ledger."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
from typing import Any, Mapping

from ledger.errors import LedgerSerializationError


ZERO_HASH = "sha256:" + ("0" * 64)
HASH_PREFIX = "sha256:"
BASE_ENVELOPE_FIELDS = {
    "event_id",
    "sequence",
    "event_type",
    "schema_version",
    "timestamp",
    "provenance",
    "previous_hash",
    "payload",
}


def _to_plain_data(event: Any) -> dict[str, Any]:
    if is_dataclass(event):
        data = asdict(event)
    elif isinstance(event, Mapping):
        data = dict(event)
    else:
        raise LedgerSerializationError("event must be a dataclass or mapping")
    data.pop("hash", None)
    return data


def _ensure_no_base_envelope_floats(data: Mapping[str, Any]) -> None:
    for field in BASE_ENVELOPE_FIELDS:
        if isinstance(data.get(field), float):
            raise LedgerSerializationError(f"float values are not allowed in base envelope field {field}")


def canonical_event_bytes(event: Any) -> bytes:
    data = _to_plain_data(event)
    _ensure_no_base_envelope_floats(data)
    try:
        return json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise LedgerSerializationError(f"event cannot be serialized canonically: {error}") from error


def compute_event_hash(event: Any) -> str:
    digest = hashlib.sha256(canonical_event_bytes(event)).hexdigest()
    return f"{HASH_PREFIX}{digest}"
