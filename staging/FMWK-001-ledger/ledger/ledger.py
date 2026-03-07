from __future__ import annotations

from typing import Any

from .schemas import LedgerConfig, LedgerEvent, LedgerTip, VerifyChainResult


class Ledger:
    def __init__(self) -> None:
        self._adapter: Any = None
        self._mutex: Any = None
        self._config: LedgerConfig | None = None

    def connect(self, config: LedgerConfig) -> None:
        raise NotImplementedError

    def append(self, event: dict) -> int:
        raise NotImplementedError

    def read(self, sequence_number: int) -> LedgerEvent:
        raise NotImplementedError

    def read_range(self, start: int, end: int) -> list[LedgerEvent]:
        raise NotImplementedError

    def read_since(self, sequence_number: int) -> list[LedgerEvent]:
        raise NotImplementedError

    def get_tip(self) -> LedgerTip:
        raise NotImplementedError

    def verify_chain(self, start: int = 0, end: int | None = None) -> VerifyChainResult:
        raise NotImplementedError
