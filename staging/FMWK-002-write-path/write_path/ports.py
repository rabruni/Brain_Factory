from __future__ import annotations

from typing import Protocol, runtime_checkable

from write_path.models import MutationRequest, TipRecord


@runtime_checkable
class LedgerPort(Protocol):
    def append(self, request: MutationRequest | dict) -> dict:
        ...

    def read_since(self, sequence_number: int) -> list[dict]:
        ...

    def get_tip(self) -> TipRecord:
        ...


@runtime_checkable
class GraphPort(Protocol):
    def fold_event(self, event: dict) -> None:
        ...

    def export_snapshot(self) -> bytes:
        ...

    def load_snapshot(self, payload: bytes) -> None:
        ...

    def reset_state(self) -> None:
        ...
