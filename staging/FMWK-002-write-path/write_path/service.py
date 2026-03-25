from __future__ import annotations

from platform_sdk.tier0_core.logging import get_logger

from write_path.errors import WritePathAppendError, WritePathFoldError
from write_path.models import MutationReceipt, MutationRequest, RecoveryCursor, SnapshotDescriptor
from write_path.ports import GraphPort, LedgerPort


class WritePathService:
    def __init__(self, *, ledger: LedgerPort, graph: GraphPort) -> None:
        self.ledger = ledger
        self.graph = graph
        self.durable_boundary_sequence: int | None = None
        self._log = get_logger(__name__)

    def submit_mutation(self, request: MutationRequest) -> MutationReceipt:
        if self.durable_boundary_sequence is not None:
            raise WritePathFoldError(
                detail="Write path is blocked pending recovery.",
                durable_sequence_number=self.durable_boundary_sequence,
            )

        try:
            event = self.ledger.append(request)
        except Exception as exc:
            raise WritePathAppendError(detail=str(exc)) from exc

        try:
            self.graph.fold_event(event)
        except Exception as exc:
            self.durable_boundary_sequence = event["sequence_number"]
            self._log.error(
                "write_path.fold_failed",
                durable_sequence_number=self.durable_boundary_sequence,
                event_type=event["event_type"],
            )
            raise WritePathFoldError(
                detail=str(exc),
                durable_sequence_number=self.durable_boundary_sequence,
            ) from exc

        return MutationReceipt(
            sequence_number=event["sequence_number"],
            event_hash=event["event_hash"],
            fold_status="folded",
        )

    def create_snapshot(self) -> SnapshotDescriptor:
        from write_path.recovery import create_snapshot

        return create_snapshot(graph=self.graph, ledger=self.ledger, service=self)

    def recover(self, snapshot: SnapshotDescriptor | None = None) -> RecoveryCursor:
        from write_path.recovery import recover_graph

        cursor = recover_graph(graph=self.graph, ledger=self.ledger, snapshot=snapshot)
        self.durable_boundary_sequence = None
        return cursor

    def refold_from_genesis(self) -> RecoveryCursor:
        from write_path.recovery import refold_from_genesis

        cursor = refold_from_genesis(graph=self.graph, ledger=self.ledger)
        self.durable_boundary_sequence = None
        return cursor
