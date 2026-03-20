"""Persistence boundary for the staged ledger framework."""

from __future__ import annotations

from dataclasses import asdict
import json
import random
import threading
import time
from typing import Any, Callable, Mapping

from ledger.errors import LedgerConnectionError, LedgerSequenceError, LedgerSerializationError
from ledger.models import LedgerEvent, LedgerTip, Provenance
from ledger.schemas import validate_append_request
from ledger.serialization import ZERO_HASH, compute_event_hash


class ClientDisconnectError(Exception):
    """Raised when the underlying client disconnects mid-operation."""


class DatabaseMissingError(Exception):
    """Raised when the configured ledger database is absent."""


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _uuidv7_like() -> str:
    milliseconds = int(time.time() * 1000)
    time_high = milliseconds & ((1 << 48) - 1)
    rand_a = random.getrandbits(12)
    rand_b = random.getrandbits(62)
    return (
        f"{time_high:012x}"[:8]
        + "-"
        + f"{time_high:012x}"[8:]
        + f"-7{rand_a:03x}"
        + f"-{(0b10 << 14 | (rand_b >> 48)):04x}"
        + f"-{(rand_b & ((1 << 48) - 1)):012x}"
    )


class LedgerStore:
    def __init__(
        self,
        *,
        client_factory: Callable[[], Any] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        lock: threading.Lock | None = None,
    ) -> None:
        self._client_factory = client_factory or self._default_client_factory
        self._sleep = sleep
        self._lock = lock or threading.Lock()
        self._client: Any | None = None
        self.before_commit: Callable[[], None] | None = None

    def append_event(self, request: Mapping[str, Any]) -> LedgerEvent:
        validate_append_request(request)

        with self._lock:
            return self._run_with_retry(lambda: self._append_once(request))

    def read(self, sequence_number: int) -> LedgerEvent:
        return self._run_with_retry(lambda: self._decode_event(self._get_client().get(self._key_for_sequence(sequence_number))))

    def read_range(self, start: int, end: int) -> list[LedgerEvent]:
        return [self.read(sequence) for sequence in range(start, end + 1)]

    def read_since(self, sequence_number: int) -> list[LedgerEvent]:
        start = 0 if sequence_number < 0 else sequence_number + 1
        tip = self._current_tip()
        if tip is None or start > tip.sequence_number:
            return []
        return self.read_range(start, tip.sequence_number)

    def get_tip(self, include_hash: bool = True) -> LedgerTip:
        tip = self._run_with_retry(self._current_tip)
        if tip is None:
            raise LedgerConnectionError("tip unavailable")
        if include_hash:
            return tip
        return LedgerTip(sequence_number=tip.sequence_number, hash=ZERO_HASH)

    def _append_once(self, request: Mapping[str, Any]) -> LedgerEvent:
        tip = self._current_tip()
        sequence = 0 if tip is None else tip.sequence_number + 1
        previous_hash = ZERO_HASH if tip is None else tip.hash

        if self.before_commit is not None:
            self.before_commit()
            current_tip = self._current_tip()
            if current_tip != tip:
                raise LedgerSequenceError("tip changed during append")

        event = self._build_event(request, sequence=sequence, previous_hash=previous_hash)
        self._get_client().set(self._key_for_sequence(sequence), self._encode_event(event))
        return event

    def _build_event(self, request: Mapping[str, Any], *, sequence: int, previous_hash: str) -> LedgerEvent:
        provenance = Provenance(**dict(request["provenance"]))
        event = LedgerEvent(
            event_id=_uuidv7_like(),
            sequence=sequence,
            event_type=str(request["event_type"]),
            schema_version=str(request.get("schema_version", "1.0.0")),
            timestamp=str(request.get("timestamp", _utc_now())),
            provenance=provenance,
            previous_hash=previous_hash,
            payload=dict(request["payload"]),
            hash=ZERO_HASH,
        )
        return LedgerEvent(
            event_id=event.event_id,
            sequence=event.sequence,
            event_type=event.event_type,
            schema_version=event.schema_version,
            timestamp=event.timestamp,
            provenance=provenance,
            previous_hash=event.previous_hash,
            payload=event.payload,
            hash=compute_event_hash(event),
        )

    def _encode_event(self, event: LedgerEvent) -> bytes:
        try:
            return json.dumps(
                asdict(event),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise LedgerSerializationError(f"event cannot be serialized canonically: {error}") from error

    def _decode_event(self, raw: bytes) -> LedgerEvent:
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LedgerSerializationError(f"event bytes cannot be parsed: {error}") from error
        data["provenance"] = Provenance(**data["provenance"])
        return LedgerEvent(**data)

    def _current_tip(self) -> LedgerTip | None:
        client = self._get_client()
        keys = client.keys()
        if not keys:
            return None
        last_key = keys[-1]
        event = self._decode_event(client.get(last_key))
        return LedgerTip(sequence_number=event.sequence, hash=event.hash)

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._client_factory()
            self._client.ensure_database()
        return self._client

    def _run_with_retry(self, operation: Callable[[], Any]) -> Any:
        try:
            return operation()
        except DatabaseMissingError as error:
            raise LedgerConnectionError("ledger database unavailable") from error
        except ClientDisconnectError:
            self._client = None
            self._sleep(1.0)
            try:
                return operation()
            except (ClientDisconnectError, DatabaseMissingError) as error:
                raise LedgerConnectionError("ledger operation failed after reconnect") from error
            except KeyError as error:
                raise LedgerConnectionError("ledger operation failed after reconnect") from error
        except KeyError as error:
            raise LedgerConnectionError("read failed") from error

    def _key_for_sequence(self, sequence: int) -> str:
        return f"{sequence:020d}"

    def _default_client_factory(self) -> Any:
        raise LedgerConnectionError("runtime client factory is not configured for staged tests")
