from __future__ import annotations

from ledger.models import EventProvenance, LedgerEvent
from ledger.serialization import canonical_event_bytes, compute_event_hash


def _event_with_payload(payload: dict) -> LedgerEvent:
    return LedgerEvent(
        event_id="0195b7fc-c29c-7c2f-a4da-8f6d2eb6d1a1",
        sequence=4,
        event_type="node_creation",
        schema_version="1.0.0",
        timestamp="2026-03-19T23:11:12Z",
        provenance=EventProvenance(
            framework_id="FMWK-004",
            pack_id="PC-002-signal-logging",
            actor="agent",
        ),
        previous_hash="sha256:" + ("1" * 64),
        payload=payload,
        hash="sha256:" + ("2" * 64),
    )


def test_canonical_event_bytes_sorted_keys() -> None:
    event = _event_with_payload(
        {
            "metadata": {"zeta": 1, "alpha": 2},
            "node_type": "intent",
            "node_id": "node-intent-dining-recall",
            "lifecycle_state": "LIVE",
        }
    )

    payload_section = canonical_event_bytes(event).decode("utf-8")
    assert (
        payload_section.index('"lifecycle_state"')
        < payload_section.index('"metadata"')
        < payload_section.index('"node_id"')
        < payload_section.index('"node_type"')
    )
    assert payload_section.index('"alpha"') < payload_section.index('"zeta"')


def test_canonical_event_bytes_uses_utf8_no_ascii_escape() -> None:
    event = _event_with_payload(
        {
            "node_id": "cafe",
            "node_type": "intent",
            "lifecycle_state": "LIVE",
            "metadata": {"title": "caf\u00e9"},
        }
    )

    encoded = canonical_event_bytes(event)
    assert "caf\u00e9" in encoded.decode("utf-8")
    assert b"\\u00e9" not in encoded


def test_canonical_event_bytes_keeps_null_fields() -> None:
    event = _event_with_payload(
        {
            "node_id": "node-intent-dining-recall",
            "node_type": "intent",
            "lifecycle_state": "LIVE",
            "metadata": {"title": None},
        }
    )

    encoded = canonical_event_bytes(event).decode("utf-8")
    assert '"title":null' in encoded


def test_compute_event_hash_exact_prefix_and_length() -> None:
    event = _event_with_payload(
        {
            "node_id": "node-intent-dining-recall",
            "node_type": "intent",
            "lifecycle_state": "LIVE",
            "metadata": {},
        }
    )

    digest = compute_event_hash(event)
    assert digest.startswith("sha256:")
    assert len(digest) == 71
    assert digest[7:].islower()
    assert event.hash == "sha256:" + ("2" * 64)
