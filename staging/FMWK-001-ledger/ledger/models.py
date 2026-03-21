"""
ledger.models — Data model for FMWK-001-ledger.

Four @dataclass entities + EventType enum (15 values).
All entities from D3 (E-001 through E-004).

Canonical JSON note: null fields (pack_id=None) MUST appear as `"pack_id":null`
in canonical JSON, NOT be omitted. This is enforced in serialization.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """
    15 Ledger-owned event types. All state mutations in DoPeJarMo
    enter the Ledger as one of these types (D3 / D4 EventType Enum).

    Stored as string values in canonical JSON.
    """
    NODE_CREATION = "node_creation"
    SIGNAL_DELTA = "signal_delta"
    METHYLATION_DELTA = "methylation_delta"
    SUPPRESSION = "suppression"
    UNSUPPRESSION = "unsuppression"
    MODE_CHANGE = "mode_change"
    CONSOLIDATION = "consolidation"
    WORK_ORDER_TRANSITION = "work_order_transition"
    INTENT_TRANSITION = "intent_transition"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PACKAGE_INSTALL = "package_install"
    PACKAGE_UNINSTALL = "package_uninstall"
    FRAMEWORK_INSTALL = "framework_install"
    SNAPSHOT_CREATED = "snapshot_created"


@dataclass
class Provenance:
    """
    E-002: Identifies the framework, pack, and actor responsible for an event.

    Attributes:
        framework_id: Required. E.g. "FMWK-002".
        pack_id:      Optional. May be None.
        actor:        Required. One of "system", "operator", "agent".
    """
    framework_id: str
    actor: str
    pack_id: Optional[str]


@dataclass
class LedgerEvent:
    """
    E-001: A single immutable event in the Ledger. All 9 fields required.

    Fields assigned by the Ledger (not by the caller):
        event_id, sequence, previous_hash, hash

    Fields supplied by the caller (via event_data dict):
        event_type, schema_version, timestamp, provenance, payload

    Hash chain invariants:
        event[0].previous_hash = "sha256:" + "0" * 64   (genesis sentinel)
        event[N].previous_hash = event[N-1].hash
        event[N].hash          = canonical_hash(event[N] without hash field)
    """
    event_id: str
    sequence: int
    event_type: str          # EventType enum value as string
    schema_version: str
    timestamp: str           # ISO-8601 UTC+Z, e.g. "2026-03-21T03:21:00Z"
    provenance: Provenance
    previous_hash: str       # "sha256:" + 64 hex chars
    payload: Dict[str, Any]
    hash: str                # "sha256:" + 64 hex chars


@dataclass
class TipRecord:
    """
    E-003: The current tip of the Ledger (highest sequence and its hash).

    Empty Ledger sentinel (D6 CLR-002):
        TipRecord(sequence_number=-1, hash="sha256:" + "0" * 64)

    This sentinel lets the Write Path compute next_sequence = -1 + 1 = 0
    for the genesis event without a special case.
    """
    sequence_number: int     # -1 if Ledger is empty
    hash: str                # "sha256:" + 64 hex chars


@dataclass
class ChainVerificationResult:
    """
    E-004: Result of verify_chain() or walk_chain().

    Attributes:
        valid:    True if every event's hash and previous_hash are correct.
        break_at: None if valid; the LOWEST corrupted sequence number otherwise.
    """
    valid: bool
    break_at: Optional[int]  # None when valid=True
