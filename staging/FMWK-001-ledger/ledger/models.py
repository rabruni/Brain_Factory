"""Ledger data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
import re
from typing import Any, Dict, Mapping, Optional, Type, TypeVar, Union


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
UUID_V7_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
FRAMEWORK_RE = re.compile(r"^FMWK-\d{3}(?:-[a-z0-9-]+)?$")
PACK_RE = re.compile(r"^PC-\d{3}-[a-z0-9-]+$")
SNAKE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

GENESIS_PREVIOUS_HASH = "sha256:" + ("0" * 64)


def _validate_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")


def _validate_hash(value: str, field_name: str) -> None:
    if not HASH_RE.match(value):
        raise ValueError(f"{field_name} must match sha256:<64 lowercase hex>")


def _validate_timestamp(value: str, field_name: str) -> None:
    if not TIMESTAMP_RE.match(value):
        raise ValueError(f"{field_name} must be ISO-8601 UTC")


def _validate_semver(value: str, field_name: str) -> None:
    if not SEMVER_RE.match(value):
        raise ValueError(f"{field_name} must be a semver string")


def _validate_uuid_v7(value: str, field_name: str) -> None:
    if not UUID_V7_RE.match(value):
        raise ValueError(f"{field_name} must be UUIDv7 text")


def _normalize_mapping(value: Any) -> Dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    raise ValueError("payload must be a mapping or dataclass")


@dataclass(frozen=True)
class EventProvenance:
    framework_id: str
    pack_id: str
    actor: str

    def __post_init__(self) -> None:
        if not FRAMEWORK_RE.match(self.framework_id):
            raise ValueError("framework_id must match FMWK authority format")
        if not PACK_RE.match(self.pack_id):
            raise ValueError("pack_id must match PC authority format")
        if self.actor not in {"system", "operator", "agent"}:
            raise ValueError("actor must be one of system, operator, agent")


@dataclass(frozen=True)
class NodeCreationPayload:
    node_id: str
    node_type: str
    lifecycle_state: str
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        _validate_non_empty(self.node_id, "node_id")
        _validate_non_empty(self.node_type, "node_type")
        _validate_non_empty(self.lifecycle_state, "lifecycle_state")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be an object")


@dataclass(frozen=True)
class SignalDeltaPayload:
    node_id: str
    delta: str
    reason: str
    intent_id: Optional[str] = None

    def __post_init__(self) -> None:
        _validate_non_empty(self.node_id, "node_id")
        _validate_non_empty(self.delta, "delta")
        _validate_non_empty(self.reason, "reason")
        if self.intent_id is not None:
            _validate_non_empty(self.intent_id, "intent_id")


@dataclass(frozen=True)
class PackageInstallPayload:
    package_id: str
    framework_ids: list[str]
    version: str
    timestamp: str

    def __post_init__(self) -> None:
        _validate_non_empty(self.package_id, "package_id")
        if not self.framework_ids:
            raise ValueError("framework_ids must contain at least one value")
        for framework_id in self.framework_ids:
            if not FRAMEWORK_RE.match(framework_id):
                raise ValueError("framework_ids must match FMWK authority format")
        _validate_semver(self.version, "version")
        _validate_timestamp(self.timestamp, "timestamp")


@dataclass(frozen=True)
class SessionStartPayload:
    session_id: str
    actor_id: str
    channel: str
    started_at: str

    def __post_init__(self) -> None:
        _validate_non_empty(self.session_id, "session_id")
        _validate_non_empty(self.actor_id, "actor_id")
        _validate_non_empty(self.channel, "channel")
        _validate_timestamp(self.started_at, "started_at")


@dataclass(frozen=True)
class SnapshotCreatedPayload:
    snapshot_sequence: int
    snapshot_path: str
    snapshot_hash: str
    created_at: str

    def __post_init__(self) -> None:
        if self.snapshot_sequence < 0:
            raise ValueError("snapshot_sequence must be >= 0")
        if not re.match(r"^/snapshots/\d+\.snapshot$", self.snapshot_path):
            raise ValueError("snapshot_path must match /snapshots/<sequence>.snapshot")
        _validate_hash(self.snapshot_hash, "snapshot_hash")
        _validate_timestamp(self.created_at, "created_at")


PayloadType = Union[
    NodeCreationPayload,
    SignalDeltaPayload,
    PackageInstallPayload,
    SessionStartPayload,
    SnapshotCreatedPayload,
]

_PAYLOAD_TYPES: Dict[str, Type[PayloadType]] = {
    "node_creation": NodeCreationPayload,
    "signal_delta": SignalDeltaPayload,
    "package_install": PackageInstallPayload,
    "framework_installed": PackageInstallPayload,
    "session_start": SessionStartPayload,
    "snapshot_created": SnapshotCreatedPayload,
}

T = TypeVar("T")


def _coerce_provenance(value: Union[EventProvenance, Mapping[str, Any]]) -> EventProvenance:
    if isinstance(value, EventProvenance):
        return value
    if isinstance(value, Mapping):
        return EventProvenance(**dict(value))
    raise ValueError("provenance must be EventProvenance or a mapping")


def _coerce_payload(
    event_type: str, value: Union[PayloadType, Mapping[str, Any]]
) -> Union[PayloadType, Dict[str, Any]]:
    payload_cls = _PAYLOAD_TYPES.get(event_type)
    if payload_cls is None:
        if isinstance(value, Mapping):
            return dict(value)
        if is_dataclass(value):
            return asdict(value)
        raise ValueError("payload must be a mapping or dataclass")
    if isinstance(value, payload_cls):
        return value
    if isinstance(value, Mapping):
        return payload_cls(**dict(value))
    raise ValueError("payload must be a mapping or matching payload dataclass")


@dataclass(frozen=True)
class LedgerAppendRequest:
    event_id: str
    event_type: str
    schema_version: str
    timestamp: str
    provenance: Union[EventProvenance, Mapping[str, Any]]
    payload: Union[PayloadType, Mapping[str, Any]]
    sequence: Optional[int] = None
    previous_hash: Optional[str] = None
    hash: Optional[str] = None

    def __post_init__(self) -> None:
        if any(value is not None for value in (self.sequence, self.previous_hash, self.hash)):
            raise ValueError("must not provide caller-controlled fields")
        _validate_uuid_v7(self.event_id, "event_id")
        if not SNAKE_RE.match(self.event_type):
            raise ValueError("event_type must be a non-empty snake_case string")
        _validate_semver(self.schema_version, "schema_version")
        _validate_timestamp(self.timestamp, "timestamp")
        object.__setattr__(self, "provenance", _coerce_provenance(self.provenance))
        object.__setattr__(self, "payload", _coerce_payload(self.event_type, self.payload))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "provenance": asdict(self.provenance),
            "payload": _normalize_mapping(self.payload),
        }


@dataclass(frozen=True)
class LedgerEvent:
    event_id: str
    sequence: int
    event_type: str
    schema_version: str
    timestamp: str
    provenance: Union[EventProvenance, Mapping[str, Any]]
    previous_hash: str
    payload: Union[PayloadType, Mapping[str, Any]]
    hash: str

    def __post_init__(self) -> None:
        _validate_uuid_v7(self.event_id, "event_id")
        if self.sequence < 0:
            raise ValueError("sequence must be >= 0")
        if not SNAKE_RE.match(self.event_type):
            raise ValueError("event_type must be a non-empty snake_case string")
        _validate_semver(self.schema_version, "schema_version")
        _validate_timestamp(self.timestamp, "timestamp")
        _validate_hash(self.previous_hash, "previous_hash")
        _validate_hash(self.hash, "hash")
        object.__setattr__(self, "provenance", _coerce_provenance(self.provenance))
        object.__setattr__(self, "payload", _coerce_payload(self.event_type, self.payload))

    def to_dict(self, include_hash: bool = True) -> Dict[str, Any]:
        data = {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "provenance": asdict(self.provenance),
            "previous_hash": self.previous_hash,
            "payload": _normalize_mapping(self.payload),
        }
        if include_hash:
            data["hash"] = self.hash
        return data


@dataclass(frozen=True)
class LedgerTip:
    sequence_number: int
    hash: str

    def __post_init__(self) -> None:
        if self.sequence_number < 0:
            raise ValueError("sequence_number must be >= 0")
        _validate_hash(self.hash, "hash")


@dataclass(frozen=True)
class ChainVerificationResult:
    valid: bool
    break_at: Optional[int] = None
    start: Optional[int] = None
    end: Optional[int] = None

    def __post_init__(self) -> None:
        if self.valid and self.break_at is not None:
            raise ValueError("break_at must be absent when valid is true")
        if not self.valid and self.break_at is None:
            raise ValueError("break_at is required when valid is false")
        if self.start is not None and self.start < 0:
            raise ValueError("start must be >= 0 when present")
        if self.end is not None and self.start is not None and self.end < self.start:
            raise ValueError("end must be >= start")


def event_from_dict(data: Mapping[str, Any]) -> LedgerEvent:
    return LedgerEvent(**dict(data))
