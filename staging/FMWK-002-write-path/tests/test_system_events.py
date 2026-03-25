from write_path.models import SnapshotDescriptor
from write_path.system_events import (
    build_session_end_request,
    build_session_start_request,
    build_snapshot_created_request,
)


def test_build_session_start_request_sets_allowed_event_type() -> None:
    request = build_session_start_request(
        session_id="0195b4e0-4f2a-7000-8000-000000000042",
        actor_id="operator-1",
        session_type="operator",
        timestamp="2026-03-21T19:40:00Z",
    )

    assert request.event_type == "session_start"


def test_build_session_start_request_uses_system_provenance() -> None:
    request = build_session_start_request(
        session_id="0195b4e0-4f2a-7000-8000-000000000042",
        actor_id="operator-1",
        session_type="operator",
        timestamp="2026-03-21T19:40:00Z",
        framework_id="FMWK-003",
    )

    assert request.provenance.framework_id == "FMWK-003"
    assert request.provenance.actor == "system"


def test_build_session_end_request_sets_allowed_event_type() -> None:
    request = build_session_end_request(
        session_id="0195b4e0-4f2a-7000-8000-000000000042",
        reason="normal",
        timestamp="2026-03-21T19:45:00Z",
    )

    assert request.event_type == "session_end"


def test_build_session_end_request_preserves_reason() -> None:
    request = build_session_end_request(
        session_id="0195b4e0-4f2a-7000-8000-000000000042",
        reason="timeout",
        timestamp="2026-03-21T19:45:00Z",
    )

    assert request.payload["reason"] == "timeout"


def test_build_snapshot_created_request_propagates_descriptor() -> None:
    descriptor = SnapshotDescriptor(
        snapshot_sequence=41,
        snapshot_file="/snapshots/41.snapshot",
        snapshot_hash="sha256:" + ("a" * 64),
    )

    request = build_snapshot_created_request(
        descriptor=descriptor,
        timestamp="2026-03-21T19:50:00Z",
    )

    assert request.event_type == "snapshot_created"
    assert request.payload["snapshot_sequence"] == 41
    assert request.payload["snapshot_file"] == "/snapshots/41.snapshot"


def test_build_snapshot_created_request_uses_system_actor() -> None:
    descriptor = SnapshotDescriptor(
        snapshot_sequence=41,
        snapshot_file="/snapshots/41.snapshot",
        snapshot_hash="sha256:" + ("a" * 64),
    )

    request = build_snapshot_created_request(
        descriptor=descriptor,
        timestamp="2026-03-21T19:50:00Z",
    )

    assert request.provenance.actor == "system"
