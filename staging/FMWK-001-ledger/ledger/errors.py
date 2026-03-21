"""
ledger.errors — Typed error classes for FMWK-001-ledger.

Four error classes, each with:
  code: str  — matches D4 Error Code Enum exactly
  message: str  — human-readable description

Error Code Enum (from D4):
  LEDGER_CONNECTION_ERROR    — immudb unreachable after one reconnect+retry
  LEDGER_CORRUPTION_ERROR    — hash chain verification failure
  LEDGER_SEQUENCE_ERROR      — concurrent write attempt or out-of-range read
  LEDGER_SERIALIZATION_ERROR — event payload not JSON-serializable
"""


class LedgerConnectionError(Exception):
    """
    Raised when immudb is unreachable and the built-in reconnect+retry
    (one reconnect, one operation retry — D5 RQ-005) has been exhausted.
    The caller (Write Path FMWK-002) decides whether to retry further.
    """

    def __init__(self, code: str = "LEDGER_CONNECTION_ERROR", message: str = "") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class LedgerCorruptionError(Exception):
    """
    Raised when hash-chain verification detects a tampered or corrupted event.
    Not retryable — requires manual intervention.
    """

    def __init__(self, code: str = "LEDGER_CORRUPTION_ERROR", message: str = "") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class LedgerSequenceError(Exception):
    """
    Raised in two situations:
      1. Concurrent write attempt detected (non-blocking lock acquisition failed).
         Single-writer architecture (D5 RQ-001): FMWK-002 Write Path is the sole
         caller of append(). Concurrent callers indicate a programming error.
      2. Out-of-range read (sequence_number beyond tip or negative).
    """

    def __init__(self, code: str = "LEDGER_SEQUENCE_ERROR", message: str = "") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class LedgerSerializationError(Exception):
    """
    Raised when event_data fails validation:
      - event_type not in EventType enum
      - Missing required field (event_type, schema_version, timestamp,
        provenance, payload)
      - payload is not JSON-serializable
    Raised BEFORE the write lock is acquired — Ledger state remains unchanged.
    Not retryable — fix the payload.
    """

    def __init__(self, code: str = "LEDGER_SERIALIZATION_ERROR", message: str = "") -> None:
        self.code = code
        self.message = message
        super().__init__(message)
