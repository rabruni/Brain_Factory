from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Provenance:
    framework_id: str
    actor: str
    pack_id: str | None = None


@dataclass(frozen=True)
class MutationRequest:
    event_type: str
    schema_version: str
    timestamp: str
    provenance: Provenance
    payload: dict[str, Any]


@dataclass(frozen=True)
class MutationReceipt:
    sequence_number: int
    event_hash: str
    fold_status: str


@dataclass(frozen=True)
class SnapshotDescriptor:
    snapshot_sequence: int
    snapshot_file: str
    snapshot_hash: str


@dataclass(frozen=True)
class RecoveryCursor:
    mode: str
    replay_from_sequence: int
    replay_to_sequence: int


@dataclass(frozen=True)
class TipRecord:
    sequence_number: int
    hash: str
