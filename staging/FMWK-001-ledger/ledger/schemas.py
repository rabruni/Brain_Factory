"""Append request and payload validation for FMWK-001-ledger."""

from __future__ import annotations

import re
from typing import Any, Mapping

from ledger.errors import LedgerSerializationError
from ledger.models import HASH_PATTERN, Provenance


SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
SNAPSHOT_PATH_PATTERN = re.compile(r"^/snapshots/\d+\.snapshot$")
APPROVED_EVENT_TYPES = {
    "node_creation",
    "signal_delta",
    "package_install",
    "session_start",
    "snapshot_created",
}


def _fail(message: str) -> None:
    raise LedgerSerializationError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _require_non_empty_string(value: Any, field: str) -> None:
    _require(isinstance(value, str) and bool(value), f"{field} must be a non-empty string")


def _require_hash(value: Any, field: str) -> None:
    _require(isinstance(value, str) and HASH_PATTERN.match(value) is not None, f"{field} must be sha256 hash")


def validate_append_request(request: Mapping[str, Any]) -> None:
    forbidden = {"sequence", "previous_hash", "hash"} & set(request.keys())
    if forbidden:
        _fail(f"caller must not supply {', '.join(sorted(forbidden))}")

    _require(request.get("event_type") in APPROVED_EVENT_TYPES, "event_type must be approved")
    _require(request.get("schema_version") == "1.0.0", "schema_version must be 1.0.0")
    _require_non_empty_string(request.get("timestamp"), "timestamp")
    _require(str(request["timestamp"]).endswith("Z"), "timestamp must be UTC ISO-8601")
    _require(isinstance(request.get("provenance"), Mapping), "provenance must be an object")
    _require(isinstance(request.get("payload"), Mapping), "payload must be an object")

    Provenance(**dict(request["provenance"]))
    validate_payload(str(request["event_type"]), request["payload"])


def validate_payload(event_type: str, payload: Mapping[str, Any]) -> None:
    if event_type == "node_creation":
        _require_non_empty_string(payload.get("node_id"), "node_id")
        _require_non_empty_string(payload.get("node_type"), "node_type")
        _require(isinstance(payload.get("initial_state"), Mapping), "initial_state must be an object")
        associated = payload.get("associated_entities")
        if associated is not None:
            _require(isinstance(associated, list), "associated_entities must be an array")
            _require(all(isinstance(item, str) and bool(item) for item in associated), "associated_entities entries must be strings")
        session_id = payload.get("session_id")
        if session_id is not None:
            _require_non_empty_string(session_id, "session_id")
        return

    if event_type == "signal_delta":
        _require_non_empty_string(payload.get("node_id"), "node_id")
        _require_non_empty_string(payload.get("signal_name"), "signal_name")
        delta = payload.get("delta")
        _require(isinstance(delta, int) and not isinstance(delta, bool) and delta != 0, "delta must be non-zero integer")
        if "reason" in payload and payload["reason"] is not None:
            _require(isinstance(payload["reason"], str), "reason must be a string")
        if "session_id" in payload and payload["session_id"] is not None:
            _require_non_empty_string(payload["session_id"], "session_id")
        return

    if event_type == "package_install":
        _require_non_empty_string(payload.get("package_id"), "package_id")
        _require_non_empty_string(payload.get("framework_id"), "framework_id")
        _require(isinstance(payload.get("version"), str) and SEMVER_PATTERN.match(payload["version"]) is not None, "version must be semver")
        _require_non_empty_string(payload.get("install_scope"), "install_scope")
        _require_hash(payload.get("manifest_hash"), "manifest_hash")
        return

    if event_type == "session_start":
        _require_non_empty_string(payload.get("session_id"), "session_id")
        _require(payload.get("session_kind") in {"operator", "user"}, "session_kind must be approved")
        _require_non_empty_string(payload.get("subject_id"), "subject_id")
        _require(payload.get("started_by") in {"system", "operator", "agent"}, "started_by must be approved")
        return

    if event_type == "snapshot_created":
        _require(isinstance(payload.get("snapshot_sequence"), int) and payload["snapshot_sequence"] >= 0, "snapshot_sequence must be >= 0")
        _require(isinstance(payload.get("snapshot_path"), str) and SNAPSHOT_PATH_PATTERN.match(payload["snapshot_path"]) is not None, "snapshot_path must match snapshot contract")
        _require_hash(payload.get("snapshot_hash"), "snapshot_hash")
        return

    _fail(f"unsupported event_type {event_type}")
