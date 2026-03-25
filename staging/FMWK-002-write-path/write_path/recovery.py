from __future__ import annotations

import asyncio
import hashlib

from platform_sdk.tier2_reliability import storage

from write_path.errors import ReplayRecoveryError, SnapshotWriteError
from write_path.models import RecoveryCursor, SnapshotDescriptor
from write_path.system_events import build_snapshot_created_request


def _snapshot_key(snapshot_file: str) -> str:
    return snapshot_file.lstrip("/")


def create_snapshot(*, graph, ledger, service) -> SnapshotDescriptor:
    try:
        payload = graph.export_snapshot()
        tip = ledger.get_tip()
        snapshot_sequence = max(tip.sequence_number, 0)
        snapshot_file = f"/snapshots/{snapshot_sequence}.snapshot"
        asyncio.run(storage.upload(_snapshot_key(snapshot_file), payload))
        descriptor = SnapshotDescriptor(
            snapshot_sequence=snapshot_sequence,
            snapshot_file=snapshot_file,
            snapshot_hash="sha256:" + hashlib.sha256(payload).hexdigest(),
        )
    except Exception as exc:
        raise SnapshotWriteError(detail=str(exc)) from exc

    service.submit_mutation(
        build_snapshot_created_request(
            descriptor=descriptor,
            timestamp="2026-03-21T19:50:00Z",
        )
    )
    return descriptor


def recover_graph(*, graph, ledger, snapshot: SnapshotDescriptor | None) -> RecoveryCursor:
    tip = ledger.get_tip()
    mode = "full_replay"
    replay_from_sequence = -1

    if snapshot is not None:
        try:
            payload = asyncio.run(storage.download(_snapshot_key(snapshot.snapshot_file)))
            graph.load_snapshot(payload)
            mode = "post_snapshot_replay"
            replay_from_sequence = snapshot.snapshot_sequence
        except Exception:
            graph.reset_state()
            mode = "full_replay"
            replay_from_sequence = -1
    else:
        graph.reset_state()

    try:
        for event in ledger.read_since(replay_from_sequence):
            graph.fold_event(event)
    except Exception as exc:
        raise ReplayRecoveryError(detail=str(exc)) from exc

    return RecoveryCursor(
        mode=mode,
        replay_from_sequence=replay_from_sequence,
        replay_to_sequence=tip.sequence_number,
    )


def refold_from_genesis(*, graph, ledger) -> RecoveryCursor:
    tip = ledger.get_tip()
    try:
        graph.reset_state()
        for event in ledger.read_since(-1):
            graph.fold_event(event)
    except Exception as exc:
        raise ReplayRecoveryError(detail=str(exc)) from exc

    return RecoveryCursor(
        mode="full_refold",
        replay_from_sequence=-1,
        replay_to_sequence=tip.sequence_number,
    )
