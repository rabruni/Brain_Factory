from __future__ import annotations

import pytest

from write_path.errors import WritePathAppendError, WritePathFoldError
from write_path.models import MutationRequest, Provenance
from write_path.service import WritePathService
from write_path.system_events import (
    build_session_end_request,
    build_session_start_request,
    build_snapshot_created_request,
)


NODE_ID = "0195b4e0-4f2a-7000-8000-000000000042"


def make_request(event_type: str = "signal_delta", payload: dict | None = None) -> MutationRequest:
    return MutationRequest(
        event_type=event_type,
        schema_version="1.0.0",
        timestamp="2026-03-21T19:40:00Z",
        provenance=Provenance(framework_id="FMWK-004", actor="agent", pack_id="PC-001"),
        payload=payload
        or {"node_id": NODE_ID, "signal_type": "entity", "delta": "0.10"},
    )


def test_submit_mutation_success_returns_receipt_after_fold(ledger_double, graph_double) -> None:
    graph_double.nodes[NODE_ID] = {"methylation": 0, "signals": {}}
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    receipt = service.submit_mutation(make_request())

    assert receipt.sequence_number == 0
    assert receipt.fold_status == "folded"
    assert graph_double.folded_events[0]["sequence_number"] == 0


def test_submit_mutation_appends_before_fold(ledger_double, graph_double) -> None:
    graph_double.nodes[NODE_ID] = {"methylation": 0, "signals": {}}
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    service.submit_mutation(make_request())

    assert ledger_double.call_log == ["append"]
    assert graph_double.call_log[0] == "fold"


def test_submit_mutation_immediate_visibility_after_success(ledger_double, graph_double) -> None:
    graph_double.nodes[NODE_ID] = {"methylation": 0, "signals": {}}
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    service.submit_mutation(make_request())

    assert str(graph_double.nodes[NODE_ID]["methylation"]) == "0.10"


def test_submit_mutation_append_failure_no_fold(ledger_double, graph_double) -> None:
    ledger_double.fail_append = RuntimeError("append down")
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    with pytest.raises(WritePathAppendError):
        service.submit_mutation(make_request())

    assert graph_double.folded_events == []


def test_submit_mutation_fold_failure_returns_typed_error_and_boundary(ledger_double, graph_double) -> None:
    graph_double.fail_fold = RuntimeError("fold down")
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    with pytest.raises(WritePathFoldError) as exc_info:
        service.submit_mutation(make_request())

    assert exc_info.value.metadata["durable_sequence_number"] == 0


def test_submit_mutation_blocks_further_writes_after_fold_failure(ledger_double, graph_double) -> None:
    graph_double.fail_fold = RuntimeError("fold down")
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    with pytest.raises(WritePathFoldError):
        service.submit_mutation(make_request())

    graph_double.fail_fold = None
    with pytest.raises(WritePathFoldError):
        service.submit_mutation(make_request())


def test_submit_mutation_uses_appended_event_for_fold(ledger_double, graph_double) -> None:
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    service.submit_mutation(make_request(event_type="session_start", payload={"session_id": "s1", "actor_id": "u1", "session_type": "operator"}))

    assert graph_double.folded_events[0]["event_hash"].startswith("sha256:")


def test_submit_mutation_preserves_event_hash_in_receipt(ledger_double, graph_double) -> None:
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    receipt = service.submit_mutation(make_request(event_type="session_start", payload={"session_id": "s1", "actor_id": "u1", "session_type": "operator"}))

    assert receipt.event_hash == ledger_double.events[0]["event_hash"]


def test_submit_mutation_accepts_session_start_system_event(ledger_double, graph_double) -> None:
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    receipt = service.submit_mutation(
        build_session_start_request(
            session_id="s1",
            actor_id="u1",
            session_type="operator",
            timestamp="2026-03-21T19:40:00Z",
        )
    )

    assert receipt.sequence_number == 0


def test_submit_mutation_accepts_session_end_system_event(ledger_double, graph_double) -> None:
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    receipt = service.submit_mutation(
        build_session_end_request(
            session_id="s1",
            reason="normal",
            timestamp="2026-03-21T19:45:00Z",
        )
    )

    assert receipt.sequence_number == 0


def test_submit_mutation_accepts_snapshot_created_system_event(ledger_double, graph_double) -> None:
    from write_path.models import SnapshotDescriptor

    service = WritePathService(ledger=ledger_double, graph=graph_double)

    receipt = service.submit_mutation(
        build_snapshot_created_request(
            descriptor=SnapshotDescriptor(
                snapshot_sequence=0,
                snapshot_file="/snapshots/0.snapshot",
                snapshot_hash="sha256:" + ("a" * 64),
            ),
            timestamp="2026-03-21T19:45:00Z",
        )
    )

    assert receipt.sequence_number == 0


def test_submit_mutation_records_durable_boundary_on_service(ledger_double, graph_double) -> None:
    graph_double.fail_fold = RuntimeError("fold down")
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    with pytest.raises(WritePathFoldError):
        service.submit_mutation(make_request())

    assert service.durable_boundary_sequence == 0


def test_submit_mutation_starts_unblocked_when_clean(ledger_double, graph_double) -> None:
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    assert service.durable_boundary_sequence is None


def test_submit_mutation_append_failure_does_not_record_boundary(ledger_double, graph_double) -> None:
    ledger_double.fail_append = RuntimeError("append down")
    service = WritePathService(ledger=ledger_double, graph=graph_double)

    with pytest.raises(WritePathAppendError):
        service.submit_mutation(make_request())

    assert service.durable_boundary_sequence is None
