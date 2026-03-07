from __future__ import annotations

from platform_sdk.tier0_core.errors import PlatformError


class LedgerConnectionError(PlatformError):
    code = "LEDGER_CONNECTION_ERROR"

    def __init__(
        self,
        detail: str = "Unable to reach Ledger storage backend.",
        **metadata: object,
    ) -> None:
        super().__init__(
            code=self.code,
            user_message="Ledger connection failed.",
            detail=detail,
            retryable=False,
            **metadata,
        )


class LedgerCorruptionError(PlatformError):
    code = "LEDGER_CORRUPTION_ERROR"

    def __init__(
        self,
        break_at: int,
        detail: str = "Ledger corruption detected.",
        **metadata: object,
    ) -> None:
        self.break_at = break_at
        super().__init__(
            code=self.code,
            user_message="Ledger corruption detected.",
            detail=detail,
            break_at=break_at,
            retryable=False,
            **metadata,
        )


class LedgerSequenceError(PlatformError):
    code = "LEDGER_SEQUENCE_ERROR"

    def __init__(
        self,
        detail: str = "Ledger sequence conflict detected.",
        **metadata: object,
    ) -> None:
        super().__init__(
            code=self.code,
            user_message="Ledger sequence conflict.",
            detail=detail,
            retryable=False,
            **metadata,
        )


class LedgerSerializationError(PlatformError):
    code = "LEDGER_SERIALIZATION_ERROR"

    def __init__(
        self,
        detail: str = "Event cannot be serialized to canonical JSON.",
        **metadata: object,
    ) -> None:
        super().__init__(
            code=self.code,
            user_message="Ledger serialization failed.",
            detail=detail,
            retryable=False,
            **metadata,
        )
