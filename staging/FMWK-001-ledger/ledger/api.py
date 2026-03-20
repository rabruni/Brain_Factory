"""Thin public ledger facade for FMWK-001-ledger."""

from __future__ import annotations

from typing import Any

from ledger.schemas import validate_append_request
from ledger.store import LedgerStore
from ledger.verify import verify_chain as run_verify_chain


class Ledger:
    def __init__(self, *, store: Any | None = None, offline_source: list[Any] | None = None) -> None:
        self._store = store or LedgerStore()
        self._offline_source = offline_source

    def append(self, request: dict) -> Any:
        validate_append_request(request)
        return self._store.append_event(request)

    def read(self, sequence_number: int) -> Any:
        return self._store.read(sequence_number)

    def read_range(self, start: int, end: int) -> list[Any]:
        return self._store.read_range(start, end)

    def read_since(self, sequence_number: int) -> list[Any]:
        return self._store.read_since(sequence_number)

    def verify_chain(self, start: int | None = None, end: int | None = None, source_mode: str = "online") -> Any:
        if source_mode == "offline":
            return run_verify_chain(self._offline_source or [], start=start, end=end, source_mode="offline")
        return run_verify_chain(self._store, start=start, end=end, source_mode="online")

    def get_tip(self, include_hash: bool = True) -> Any:
        return self._store.get_tip(include_hash=include_hash)
