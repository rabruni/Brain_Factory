from __future__ import annotations

from platform_sdk.tier0_core.errors import PlatformError


class WritePathAppendError(PlatformError):
    code = "WRITE_PATH_APPEND_ERROR"

    def __init__(self, detail: str) -> None:
        super().__init__(code=self.code, user_message="Ledger append failed.", detail=detail)


class WritePathFoldError(PlatformError):
    code = "WRITE_PATH_FOLD_ERROR"

    def __init__(self, detail: str, durable_sequence_number: int | None = None) -> None:
        super().__init__(
            code=self.code,
            user_message="Graph fold failed after durable append.",
            detail=detail,
            durable_sequence_number=durable_sequence_number,
        )


class SnapshotWriteError(PlatformError):
    code = "SNAPSHOT_WRITE_ERROR"

    def __init__(self, detail: str) -> None:
        super().__init__(code=self.code, user_message="Snapshot creation failed.", detail=detail)


class ReplayRecoveryError(PlatformError):
    code = "REPLAY_RECOVERY_ERROR"

    def __init__(self, detail: str) -> None:
        super().__init__(code=self.code, user_message="Recovery or refold failed.", detail=detail)
