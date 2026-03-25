from __future__ import annotations

import hashlib

import pytest

from write_path.errors import ReplayRecoveryError, SnapshotWriteError, WritePathFoldError
from write_path.models import MutationRequest, Provenance, SnapshotDescriptor
from write_path.recovery import create_snapshot, recover_graph, refold_from_genesis
from write_path.service import WritePathService


NODE_ID = "0195b4e0-4f2a-7000-8000-000000000042"


@pytest.fixture
def storage_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PLATFORM_STORAGE_BACKEND", "mock")
    monkeypatch.setenv("PLATFORM_STORAGE_LOCAL_PATH", str(tmp_path))
    from platform_sdk.tier2_reliability import storage

    storage._provider = None
    yield tmp_path
    storage._provider = None


def test_create_snapshot_writes_artifact_before_snapshot_created(
    ledger_double, graph_double, storage_env
) -> None:
    service = WritePathService(ledger=ledger_double, graph=graph_double)
    ledger_double.append(
        {
            "event_type": "session_start",
            "schema_version": "1.0.0",
            "timestamp": "2026-03-21T19:40:00Z",
            "provenance": {"framework_id": "FMWK-002", "actor": "system", "pack_id": None},
            "payload": {"session_id": "s1", "actor_id": "u1", "session_type": "operator"},
        }
    )
    graph_double.snapshot_bytes = b'{"nodes":{"n1":{"methylation":"0.5"}}}'

    descriptor = create_snapshot(graph=graph_double, ledger=ledger_double, service=service)

    expected_path = storage_env / "snapshots" / "0.snapshot"
    assert expected_path.exists()
    assert descriptor.snapshot_file == "/snapshots/0.snapshot"
    assert ledger_double.events[-1]["event_type"] == "snapshot_created"


def test_create_snapshot_hash_matches_payload(ledger_double, graph_double, storage_env) -> None:
    service = WritePathService(ledger=ledger_double, graph=graph_double)
    graph_double.snapshot_bytes = b"abc"

    descriptor = create_snapshot(graph=graph_double, ledger=ledger_double, service=service)

    assert descriptor.snapshot_hash == "sha256:" + hashlib.sha256(b"abc").hexdigest()


def test_create_snapshot_uses_current_tip_sequence(ledger_double, graph_double, storage_env) -> None:
    service = WritePathService(ledger=ledger_double, graph=graph_double)
    ledger_double.append({"event_type": "session_start", "schema_version": "1.0.0", "timestamp": "2026-03-21T19:40:00Z", "provenance": {"framework_id": "FMWK-002", "actor": "system", "pack_id": None}, "payload": {}})
    ledger_double.append({"event_type": "session_end", "schema_version": "1.0.0", "timestamp": "2026-03-21T19:41:00Z", "provenance": {"framework_id": "FMWK-002", "actor": "system", "pack_id": None}, "payload": {}})

    descriptor = create_snapshot(graph=graph_double, ledger=ledger_double, service=service)

    assert descriptor.snapshot_sequence == 1


def test_create_snapshot_export_failure_raises_typed_error(ledger_double, graph_double, storage_env) -> None:
    service = WritePathService(ledger=ledger_double, graph=graph_double)
    graph_double.fail_export = RuntimeError("export down")

    with pytest.raises(SnapshotWriteError):
        create_snapshot(graph=graph_double, ledger=ledger_double, service=service)


def test_create_snapshot_fold_failure_surfaces_from_service(ledger_double, graph_double, storage_env) -> None:
    service = WritePathService(ledger=ledger_double, graph=graph_double)
    graph_double.fail_fold = RuntimeError("fold down")

    with pytest.raises(WritePathFoldError):
        create_snapshot(graph=graph_double, ledger=ledger_double, service=service)


def test_recover_uses_post_snapshot_replay_only(ledger_double, graph_double, storage_env) -> None:
    graph_double.snapshot_bytes = b'{"nodes":{"seed":{"methylation":"0.3"}}}'
    service = WritePathService(ledger=ledger_double, graph=graph_double)
    create_snapshot(graph=graph_double, ledger=ledger_double, service=service)
    ledger_double.append(
        {
            "event_type": "node_creation",
            "schema_version": "1.0.0",
            "timestamp": "2026-03-21T19:50:00Z",
            "provenance": {"framework_id": "FMWK-004", "actor": "agent", "pack_id": "PC-001"},
            "payload": {"node_id": NODE_ID, "node_type": "memory", "initial_methylation": "0.2", "base_weight": "1.0"},
        }
    )

    descriptor = SnapshotDescriptor(
        snapshot_sequence=0,
        snapshot_file="/snapshots/0.snapshot",
        snapshot_hash="sha256:" + hashlib.sha256(graph_double.snapshot_bytes).hexdigest(),
    )
    cursor = recover_graph(graph=graph_double, ledger=ledger_double, snapshot=descriptor)

    assert cursor.mode == "post_snapshot_replay"
    assert cursor.replay_from_sequence == 0
    assert graph_double.folded_events[-1]["sequence_number"] == 1


def test_recover_without_snapshot_replays_from_genesis(ledger_double, graph_double, storage_env) -> None:
    ledger_double.append(
        {
            "event_type": "node_creation",
            "schema_version": "1.0.0",
            "timestamp": "2026-03-21T19:50:00Z",
            "provenance": {"framework_id": "FMWK-004", "actor": "agent", "pack_id": "PC-001"},
            "payload": {"node_id": NODE_ID, "node_type": "memory", "initial_methylation": "0.2", "base_weight": "1.0"},
        }
    )

    cursor = recover_graph(graph=graph_double, ledger=ledger_double, snapshot=None)

    assert cursor.mode == "full_replay"
    assert cursor.replay_from_sequence == -1
    assert graph_double.folded_events[-1]["sequence_number"] == 0


def test_recover_unusable_snapshot_falls_back_to_full_replay(ledger_double, graph_double, storage_env) -> None:
    ledger_double.append(
        {
            "event_type": "node_creation",
            "schema_version": "1.0.0",
            "timestamp": "2026-03-21T19:50:00Z",
            "provenance": {"framework_id": "FMWK-004", "actor": "agent", "pack_id": "PC-001"},
            "payload": {"node_id": NODE_ID, "node_type": "memory", "initial_methylation": "0.2", "base_weight": "1.0"},
        }
    )
    graph_double.fail_load = RuntimeError("bad snapshot")

    cursor = recover_graph(
        graph=graph_double,
        ledger=ledger_double,
        snapshot=SnapshotDescriptor(
            snapshot_sequence=0,
            snapshot_file="/snapshots/0.snapshot",
            snapshot_hash="sha256:" + ("a" * 64),
        ),
    )

    assert cursor.mode == "full_replay"
    assert cursor.replay_from_sequence == -1


def test_recover_replay_failure_raises_typed_error(ledger_double, graph_double, storage_env) -> None:
    ledger_double.append(
        {
            "event_type": "node_creation",
            "schema_version": "1.0.0",
            "timestamp": "2026-03-21T19:50:00Z",
            "provenance": {"framework_id": "FMWK-004", "actor": "agent", "pack_id": "PC-001"},
            "payload": {"node_id": NODE_ID, "node_type": "memory", "initial_methylation": "0.2", "base_weight": "1.0"},
        }
    )
    graph_double.fail_fold = RuntimeError("replay down")

    with pytest.raises(ReplayRecoveryError):
        recover_graph(graph=graph_double, ledger=ledger_double, snapshot=None)


def test_refold_from_genesis_resets_graph_and_preserves_ledger(ledger_double, graph_double) -> None:
    ledger_double.append(
        {
            "event_type": "node_creation",
            "schema_version": "1.0.0",
            "timestamp": "2026-03-21T19:50:00Z",
            "provenance": {"framework_id": "FMWK-004", "actor": "agent", "pack_id": "PC-001"},
            "payload": {"node_id": NODE_ID, "node_type": "memory", "initial_methylation": "0.2", "base_weight": "1.0"},
        }
    )
    prior_events = list(ledger_double.events)

    cursor = refold_from_genesis(graph=graph_double, ledger=ledger_double)

    assert graph_double.reset_calls == 1
    assert ledger_double.events == prior_events
    assert cursor.mode == "full_refold"


def test_refold_from_genesis_replays_through_tip(ledger_double, graph_double) -> None:
    for node_id in ("n1", "n2"):
        ledger_double.append(
            {
                "event_type": "node_creation",
                "schema_version": "1.0.0",
                "timestamp": "2026-03-21T19:50:00Z",
                "provenance": {"framework_id": "FMWK-004", "actor": "agent", "pack_id": "PC-001"},
                "payload": {"node_id": node_id, "node_type": "memory", "initial_methylation": "0.2", "base_weight": "1.0"},
            }
        )

    cursor = refold_from_genesis(graph=graph_double, ledger=ledger_double)

    assert cursor.replay_to_sequence == 1
    assert len(graph_double.folded_events) == 2


def test_service_recover_clears_durable_boundary_after_fold_failure(ledger_double, graph_double, storage_env) -> None:
    service = WritePathService(ledger=ledger_double, graph=graph_double)
    graph_double.fail_fold = RuntimeError("fold down")

    with pytest.raises(WritePathFoldError):
        service.submit_mutation(
            MutationRequest(
                event_type="node_creation",
                schema_version="1.0.0",
                timestamp="2026-03-21T19:50:00Z",
                provenance=Provenance(framework_id="FMWK-004", actor="agent", pack_id="PC-001"),
                payload={
                    "node_id": NODE_ID,
                    "node_type": "memory",
                    "initial_methylation": "0.2",
                    "base_weight": "1.0",
                },
            )
        )

    graph_double.fail_fold = None
    cursor = service.recover(snapshot=None)

    assert cursor.mode == "full_replay"
    assert service.durable_boundary_sequence is None
