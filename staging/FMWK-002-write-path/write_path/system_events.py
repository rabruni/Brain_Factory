from write_path.models import MutationRequest, Provenance, SnapshotDescriptor


def _build_request(
    *,
    event_type: str,
    timestamp: str,
    framework_id: str,
    payload: dict,
) -> MutationRequest:
    return MutationRequest(
        event_type=event_type,
        schema_version="1.0.0",
        timestamp=timestamp,
        provenance=Provenance(framework_id=framework_id, actor="system", pack_id=None),
        payload=payload,
    )


def build_session_start_request(
    *,
    session_id: str,
    actor_id: str,
    session_type: str,
    timestamp: str,
    framework_id: str = "FMWK-002",
) -> MutationRequest:
    return _build_request(
        event_type="session_start",
        timestamp=timestamp,
        framework_id=framework_id,
        payload={
            "session_id": session_id,
            "actor_id": actor_id,
            "session_type": session_type,
        },
    )


def build_session_end_request(
    *,
    session_id: str,
    reason: str,
    timestamp: str,
    framework_id: str = "FMWK-002",
) -> MutationRequest:
    return _build_request(
        event_type="session_end",
        timestamp=timestamp,
        framework_id=framework_id,
        payload={"session_id": session_id, "reason": reason},
    )


def build_snapshot_created_request(
    *,
    descriptor: SnapshotDescriptor,
    timestamp: str,
    framework_id: str = "FMWK-002",
) -> MutationRequest:
    return _build_request(
        event_type="snapshot_created",
        timestamp=timestamp,
        framework_id=framework_id,
        payload={
            "snapshot_sequence": descriptor.snapshot_sequence,
            "snapshot_file": descriptor.snapshot_file,
            "snapshot_hash": descriptor.snapshot_hash,
        },
    )
