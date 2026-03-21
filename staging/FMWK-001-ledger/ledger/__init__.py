"""
ledger — FMWK-001: Append-only hash-chained event store for DoPeJarMo.

Public API (all symbols exported from here):

  Classes:
    LedgerClient           — 6-method public interface (append, read, read_range,
                             read_since, verify_chain, get_tip)
    LedgerEvent            — Immutable event dataclass (9 fields)
    Provenance             — Provenance dataclass (3 fields)
    TipRecord              — Tip position dataclass (2 fields)
    ChainVerificationResult — Verification result dataclass (2 fields)
    EventType              — 15-value enum of all Ledger event types

  Errors:
    LedgerConnectionError    — immudb unreachable
    LedgerCorruptionError    — hash chain corrupted
    LedgerSequenceError      — concurrent write or out-of-range read
    LedgerSerializationError — invalid or non-serializable event data

  Utilities:
    canonical_json()  — canonical JSON serialization (sort_keys, no whitespace)
    canonical_hash()  — SHA-256 of canonical JSON, "sha256:" + 64hex prefix

Version: 1.0.0
Framework: FMWK-001-ledger (KERNEL phase)
"""

from ledger.api import LedgerClient
from ledger.errors import (
    LedgerConnectionError,
    LedgerCorruptionError,
    LedgerSequenceError,
    LedgerSerializationError,
)
from ledger.models import (
    ChainVerificationResult,
    EventType,
    LedgerEvent,
    Provenance,
    TipRecord,
)
from ledger.serialization import canonical_hash, canonical_json

__all__ = [
    # Primary interface
    "LedgerClient",
    # Data model
    "LedgerEvent",
    "Provenance",
    "TipRecord",
    "ChainVerificationResult",
    "EventType",
    # Errors
    "LedgerConnectionError",
    "LedgerCorruptionError",
    "LedgerSequenceError",
    "LedgerSerializationError",
    # Utilities
    "canonical_json",
    "canonical_hash",
]

__version__ = "1.0.0"
__framework_id__ = "FMWK-001"
__package_id__ = "FMWK-001-ledger"
