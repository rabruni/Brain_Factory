from dataclasses import asdict

import pytest

from write_path.errors import (
    ReplayRecoveryError,
    SnapshotWriteError,
    WritePathAppendError,
    WritePathFoldError,
)
from write_path.models import (
    MutationReceipt,
    MutationRequest,
    RecoveryCursor,
    SnapshotDescriptor,
    TipRecord,
    Provenance,
)
from write_path.ports import GraphPort, LedgerPort


def test_mutation_request_preserves_fields() -> None:
    request = MutationRequest(
        event_type="signal_delta",
        schema_version="1.0.0",
        timestamp="2026-03-21T19:40:00Z",
        provenance=Provenance(framework_id="FMWK-004", actor="agent", pack_id="PC-001"),
        payload={"node_id": "n1", "signal_type": "entity", "delta": "0.10"},
    )

    assert request.event_type == "signal_delta"
    assert request.provenance.framework_id == "FMWK-004"
    assert request.payload["delta"] == "0.10"


def test_mutation_request_asdict_includes_optional_pack_id() -> None:
    request = MutationRequest(
        event_type="session_start",
        schema_version="1.0.0",
        timestamp="2026-03-21T19:40:00Z",
        provenance=Provenance(framework_id="FMWK-002", actor="system", pack_id=None),
        payload={"session_id": "s1", "actor_id": "operator-1", "session_type": "operator"},
    )

    assert asdict(request)["provenance"]["pack_id"] is None


def test_mutation_receipt_represents_folded_success() -> None:
    receipt = MutationReceipt(
        sequence_number=41,
        event_hash="sha256:" + ("a" * 64),
        fold_status="folded",
    )

    assert receipt.fold_status == "folded"


def test_snapshot_descriptor_preserves_boundary_metadata() -> None:
    descriptor = SnapshotDescriptor(
        snapshot_sequence=41,
        snapshot_file="/snapshots/41.snapshot",
        snapshot_hash="sha256:" + ("b" * 64),
    )

    assert descriptor.snapshot_sequence == 41
    assert descriptor.snapshot_file.endswith(".snapshot")


def test_recovery_cursor_allows_genesis_sentinel() -> None:
    cursor = RecoveryCursor(mode="full_replay", replay_from_sequence=-1, replay_to_sequence=4)

    assert cursor.replay_from_sequence == -1
    assert cursor.mode == "full_replay"


def test_tip_record_empty_ledger_sentinel_is_supported() -> None:
    tip = TipRecord(sequence_number=-1, hash="sha256:" + ("0" * 64))

    assert tip.sequence_number == -1


@pytest.mark.parametrize(
    ("error_type", "expected_code"),
    [
        (WritePathAppendError, "WRITE_PATH_APPEND_ERROR"),
        (WritePathFoldError, "WRITE_PATH_FOLD_ERROR"),
        (SnapshotWriteError, "SNAPSHOT_WRITE_ERROR"),
        (ReplayRecoveryError, "REPLAY_RECOVERY_ERROR"),
    ],
)
def test_typed_errors_expose_expected_codes(error_type, expected_code: str) -> None:
    error = error_type(detail="boom")

    assert error.code == expected_code


def test_doubles_implement_declared_protocols(ledger_double, graph_double) -> None:
    assert isinstance(ledger_double, LedgerPort)
    assert isinstance(graph_double, GraphPort)
