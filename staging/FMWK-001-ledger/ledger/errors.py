"""Explicit error types for the staged ledger framework."""

LEDGER_CONNECTION_ERROR = "LEDGER_CONNECTION_ERROR"
LEDGER_CORRUPTION_ERROR = "LEDGER_CORRUPTION_ERROR"
LEDGER_SEQUENCE_ERROR = "LEDGER_SEQUENCE_ERROR"
LEDGER_SERIALIZATION_ERROR = "LEDGER_SERIALIZATION_ERROR"


class LedgerError(Exception):
    """Base error carrying the stable framework error code."""

    code = "LEDGER_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class LedgerConnectionError(LedgerError):
    code = LEDGER_CONNECTION_ERROR


class LedgerCorruptionError(LedgerError):
    code = LEDGER_CORRUPTION_ERROR


class LedgerSequenceError(LedgerError):
    code = LEDGER_SEQUENCE_ERROR


class LedgerSerializationError(LedgerError):
    code = LEDGER_SERIALIZATION_ERROR
