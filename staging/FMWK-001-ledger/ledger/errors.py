"""Ledger error surface."""


class LedgerConnectionError(Exception):
    """Raised when the ledger cannot reach durable storage."""


class LedgerSerializationError(Exception):
    """Raised when an event cannot be serialized canonically."""


class LedgerSequenceError(Exception):
    """Raised when sequence assignment cannot complete without conflict."""


class LedgerCorruptionError(Exception):
    """Raised when stored ledger data is corrupt."""

