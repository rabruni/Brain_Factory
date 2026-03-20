import sys
from pathlib import Path
import json

import pytest

from ledger.errors import LedgerSequenceError
from ledger.serialization import event_key


FRAMEWORK_ROOT = Path(__file__).resolve().parents[1]
if str(FRAMEWORK_ROOT) not in sys.path:
    sys.path.insert(0, str(FRAMEWORK_ROOT))
DOPEJAR_ROOT = Path("/Users/raymondbruni/dopejar")
if str(DOPEJAR_ROOT) not in sys.path:
    sys.path.insert(0, str(DOPEJAR_ROOT))


@pytest.fixture
def zero_hash() -> str:
    return "sha256:" + ("0" * 64)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: opt-in tests that require a real immudb service",
    )


class InMemoryBackend:
    def __init__(self) -> None:
        self.storage = {}
        self.conflict_keys = set()

    def connect(self):
        return self

    def append_bytes(self, key: str, value: bytes) -> None:
        if key in self.conflict_keys or key in self.storage:
            raise LedgerSequenceError("Sequence assignment conflict; append rejected.")
        self.storage[key] = value

    def read_bytes(self, sequence: int) -> bytes:
        return self.storage[event_key(sequence)]

    def read_range_bytes(self, start: int, end: int):
        return [self.storage[event_key(sequence)] for sequence in range(start, end + 1)]

    def read_since_bytes(self, sequence_number: int):
        start = 0 if sequence_number < 0 else sequence_number + 1
        tip = self.get_tip_bytes()
        if tip is None or start > tip[0]:
            return []
        return self.read_range_bytes(start, tip[0])

    def get_tip_bytes(self):
        if not self.storage:
            return None
        last_key = sorted(self.storage.keys())[-1]
        return int(last_key.split(":")[1]), self.storage[last_key]

    def corrupt(self, sequence: int, field: str, value):
        key = event_key(sequence)
        event = json.loads(self.storage[key].decode("utf-8"))
        event[field] = value
        self.storage[key] = json.dumps(
            event,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")


@pytest.fixture
def in_memory_backend() -> InMemoryBackend:
    return InMemoryBackend()


@pytest.fixture
def make_request():
    from ledger.models import LedgerAppendRequest

    def factory(index: int, event_type: str = "node_creation", payload=None):
        request_payload = payload
        if request_payload is None:
            request_payload = {
                "node_id": "node-{:02d}".format(index),
                "node_type": "intent",
                "lifecycle_state": "LIVE",
                "metadata": {"title": "Node {:02d}".format(index)},
            }
        return LedgerAppendRequest(
            event_id="0195b7fc-c29c-7c2f-a4da-{:012x}".format(index + 1),
            event_type=event_type,
            schema_version="1.0.0",
            timestamp="2026-03-19T23:{:02d}:00Z".format(index % 60),
            provenance={
                "framework_id": "FMWK-002",
                "pack_id": "PC-001-fold-engine",
                "actor": "system",
            },
            payload=request_payload,
        )

    return factory
