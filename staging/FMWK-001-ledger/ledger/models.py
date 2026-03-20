"""Typed models for FMWK-001-ledger."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
UUIDV7_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class Provenance:
    framework_id: str
    pack_id: str
    actor: str

    def __post_init__(self) -> None:
        _require(self.framework_id.startswith("FMWK-"), "framework_id must be a framework id")
        _require(bool(self.pack_id), "pack_id must be non-empty")
        _require(self.actor in {"system", "operator", "agent"}, "actor must be approved")


@dataclass(frozen=True)
class LedgerEvent:
    event_id: str
    sequence: int
    event_type: str
    schema_version: str
    timestamp: str
    provenance: Provenance
    previous_hash: str
    payload: dict[str, Any]
    hash: str

    def __post_init__(self) -> None:
        _require(UUIDV7_PATTERN.match(self.event_id) is not None, "event_id must be UUIDv7")
        _require(self.sequence >= 0, "sequence must be >= 0")
        _require(bool(self.event_type), "event_type must be non-empty")
        _require(self.schema_version == "1.0.0", "schema_version must be 1.0.0")
        _require(self.timestamp.endswith("Z"), "timestamp must be UTC ISO-8601")
        _require(isinstance(self.provenance, Provenance), "provenance must be typed")
        _require(HASH_PATTERN.match(self.previous_hash) is not None, "previous_hash must be sha256")
        _require(isinstance(self.payload, dict), "payload must be an object")
        _require(HASH_PATTERN.match(self.hash) is not None, "hash must be sha256")


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    start_sequence: int
    end_sequence: int
    break_at: int | None = None

    def __post_init__(self) -> None:
        _require(self.start_sequence >= 0, "start_sequence must be >= 0")
        _require(self.end_sequence >= self.start_sequence, "end_sequence must be >= start_sequence")
        if self.valid:
            _require(self.break_at is None, "break_at must be omitted for valid results")
        else:
            _require(self.break_at is not None, "break_at is required for invalid results")


@dataclass(frozen=True)
class LedgerTip:
    sequence_number: int
    hash: str

    def __post_init__(self) -> None:
        _require(self.sequence_number >= 0, "sequence_number must be >= 0")
        _require(HASH_PATTERN.match(self.hash) is not None, "hash must be sha256")
