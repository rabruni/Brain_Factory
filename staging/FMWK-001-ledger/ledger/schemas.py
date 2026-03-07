from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from platform_sdk.tier0_core.config import get_config
from platform_sdk.tier0_core.secrets import get_secret


Actor = Literal["system", "operator", "agent"]
SessionEndReason = Literal[
    "operator_disconnect",
    "user_disconnect",
    "timeout",
    "system_shutdown",
]
GateResultType = Literal["pass", "fail"]


@dataclass(frozen=True)
class Provenance:
    framework_id: str
    pack_id: str
    actor: Actor


@dataclass(frozen=True)
class LedgerEvent:
    event_id: str
    sequence: int
    event_type: str
    schema_version: str
    timestamp: str
    provenance: Provenance
    previous_hash: str
    payload: dict[str, Any]
    hash: str


@dataclass(frozen=True)
class LedgerTip:
    sequence_number: int = -1
    hash: str = ""


@dataclass(frozen=True)
class VerifyChainResult:
    valid: bool
    break_at: int | None = None

    def __post_init__(self) -> None:
        if self.valid and self.break_at is not None:
            raise ValueError("break_at must be None when valid is True")
        if not self.valid and (self.break_at is None or self.break_at < 0):
            raise ValueError("break_at must be set to >= 0 when valid is False")


@dataclass(frozen=True)
class SnapshotCreatedPayload:
    snapshot_path: str
    snapshot_hash: str
    snapshot_sequence: int


@dataclass(frozen=True)
class NodeCreationPayload:
    node_id: str
    node_type: str
    base_weight: str
    initial_methylation: str


@dataclass(frozen=True)
class SessionStartPayload:
    session_id: str
    operator_id: str | None = None
    user_id: str | None = None

    def __post_init__(self) -> None:
        one_present = (self.operator_id is None) ^ (self.user_id is None)
        if not one_present:
            raise ValueError("Exactly one of operator_id or user_id must be set")


@dataclass(frozen=True)
class SessionEndPayload:
    session_id: str
    end_reason: SessionEndReason


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    result: GateResultType


@dataclass(frozen=True)
class PackageInstallPayload:
    package_id: str
    package_version: str
    gate_results: list[GateResult]
    file_hashes: dict[str, str]


EVENT_TYPE_CATALOG = frozenset(
    {
        "node_creation",
        "signal_delta",
        "methylation_delta",
        "suppression",
        "unsuppression",
        "mode_change",
        "consolidation",
        "work_order_transition",
        "intent_transition",
        "session_start",
        "session_end",
        "package_install",
        "package_uninstall",
        "framework_install",
        "snapshot_created",
    }
)


@dataclass(frozen=True)
class LedgerConfig:
    host: str
    port: int
    database: str
    username: str
    password: str

    @classmethod
    def from_env(cls) -> "LedgerConfig":
        # Ensure platform configuration is initialized for compatibility.
        get_config()
        host = os.getenv("IMMUDB_HOST", "localhost")
        port = int(os.getenv("IMMUDB_PORT", "3322"))
        database = os.getenv("IMMUDB_DATABASE", "ledger")
        username = get_secret("immudb_username").get_secret_value()
        password = get_secret("immudb_password").get_secret_value()
        return cls(host=host, port=port, database=database, username=username, password=password)
