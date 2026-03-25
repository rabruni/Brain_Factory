import os
import sys
from dataclasses import asdict

import pytest


_DOPEJAR_ROOT = "/Users/raymondbruni/dopejar"
if _DOPEJAR_ROOT not in sys.path:
    sys.path.insert(0, _DOPEJAR_ROOT)

_STAGING_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _STAGING_ROOT not in sys.path:
    sys.path.insert(0, _STAGING_ROOT)

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("PLATFORM_ENVIRONMENT", "test")


class LedgerPortDouble:
    def __init__(self) -> None:
        self.appended_requests: list[dict] = []
        self.events: list[dict] = []
        self.tip_sequence = -1
        self.tip_hash = "sha256:" + ("0" * 64)
        self.fail_append: Exception | None = None
        self.call_log: list[str] = []

    def append(self, request) -> dict:
        self.call_log.append("append")
        if self.fail_append is not None:
            raise self.fail_append
        payload = asdict(request) if hasattr(request, "__dataclass_fields__") else dict(request)
        self.tip_sequence += 1
        event = {
            "sequence_number": self.tip_sequence,
            "event_hash": "sha256:" + f"{self.tip_sequence:064x}",
            **payload,
        }
        self.appended_requests.append(payload)
        self.events.append(event)
        self.tip_hash = event["event_hash"]
        return event

    def read_since(self, sequence_number: int) -> list[dict]:
        return [event for event in self.events if event["sequence_number"] > sequence_number]

    def get_tip(self):
        from write_path.models import TipRecord

        return TipRecord(sequence_number=self.tip_sequence, hash=self.tip_hash)


class GraphPortDouble:
    def __init__(self) -> None:
        self.folded_events: list[dict] = []
        self.nodes: dict[str, dict] = {}
        self.fail_fold: Exception | None = None
        self.fail_export: Exception | None = None
        self.fail_load: Exception | None = None
        self.snapshot_bytes = b'{"nodes":{}}'
        self.loaded_payloads: list[bytes] = []
        self.reset_calls = 0
        self.call_log: list[str] = []

    def fold_event(self, event: dict) -> None:
        self.call_log.append("fold")
        if self.fail_fold is not None:
            raise self.fail_fold
        self.folded_events.append(event)
        from write_path.folds import fold_live_event

        fold_live_event(self, event)

    def export_snapshot(self) -> bytes:
        self.call_log.append("export_snapshot")
        if self.fail_export is not None:
            raise self.fail_export
        return self.snapshot_bytes

    def load_snapshot(self, payload: bytes) -> None:
        self.call_log.append("load_snapshot")
        if self.fail_load is not None:
            raise self.fail_load
        self.loaded_payloads.append(payload)

    def reset_state(self) -> None:
        self.call_log.append("reset_state")
        self.reset_calls += 1
        self.nodes = {}


@pytest.fixture
def ledger_double() -> LedgerPortDouble:
    return LedgerPortDouble()


@pytest.fixture
def graph_double() -> GraphPortDouble:
    return GraphPortDouble()
