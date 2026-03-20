from ledger.errors import LedgerSerializationError
from ledger.models import LedgerEvent, Provenance
from ledger.serialization import ZERO_HASH, canonical_event_bytes, compute_event_hash


def _event_with_payload(payload: dict) -> LedgerEvent:
    return LedgerEvent(
        event_id="0195b8d1-6d8d-7ef9-9c6a-4bd29ca2dce4",
        sequence=0,
        event_type="session_start",
        schema_version="1.0.0",
        timestamp="2026-03-20T20:20:00Z",
        provenance=Provenance(
            framework_id="FMWK-001-ledger",
            pack_id="PC-001-ledger-core",
            actor="system",
        ),
        previous_hash=ZERO_HASH,
        payload=payload,
        hash="sha256:b2bbde319c7c9677b6d6816d9b422c8ec9787c6d0ca7f64444f0715a8ca54ac8",
    )


def test_serialization_uses_sorted_keys_without_whitespace() -> None:
    event = _event_with_payload(
        {
            "subject_id": "ray",
            "session_id": "session-0195b8d1",
            "started_by": "operator",
            "session_kind": "operator",
        }
    )

    assert canonical_event_bytes(event) == (
        b'{"event_id":"0195b8d1-6d8d-7ef9-9c6a-4bd29ca2dce4","event_type":"session_start",'
        b'"payload":{"session_id":"session-0195b8d1","session_kind":"operator","started_by":"operator","subject_id":"ray"},'
        b'"previous_hash":"sha256:0000000000000000000000000000000000000000000000000000000000000000",'
        b'"provenance":{"actor":"system","framework_id":"FMWK-001-ledger","pack_id":"PC-001-ledger-core"},'
        b'"schema_version":"1.0.0","sequence":0,"timestamp":"2026-03-20T20:20:00Z"}'
    )


def test_serialization_excludes_hash_field_from_hash_input() -> None:
    event = _event_with_payload({"session_id": "session-0195b8d1", "session_kind": "operator", "subject_id": "ray", "started_by": "operator"})
    changed_hash = LedgerEvent(**{**event.__dict__, "hash": "sha256:" + ("f" * 64)})

    assert canonical_event_bytes(event) == canonical_event_bytes(changed_hash)


def test_serialization_preserves_nulls_and_utf8_literals() -> None:
    event = _event_with_payload(
        {
            "session_id": "session-0195b8d1",
            "session_kind": "operator",
            "subject_id": None,
            "started_by": "opérateur",
        }
    )

    rendered = canonical_event_bytes(event)

    assert b"null" in rendered
    assert "opérateur".encode("utf-8") in rendered
    assert b"\\u00e9" not in rendered


def test_compute_event_hash_returns_sha256_prefixed_lowercase_hex() -> None:
    event = _event_with_payload(
        {
            "session_id": "session-0195b8d1",
            "session_kind": "operator",
            "subject_id": "ray",
            "started_by": "operator",
        }
    )

    assert compute_event_hash(event) == "sha256:ad32f4a54aa9b4275341886715eadfa6a52ad3f1ba83c3e0fc7cae6978bfe0dc"


def test_serialization_rejects_unhashable_float_in_base_envelope() -> None:
    try:
        canonical_event_bytes(
            {
                "event_id": "0195b8d1-6d8d-7ef9-9c6a-4bd29ca2dce4",
                "sequence": 0.5,
                "event_type": "session_start",
                "schema_version": "1.0.0",
                "timestamp": "2026-03-20T20:20:00Z",
                "provenance": {
                    "framework_id": "FMWK-001-ledger",
                    "pack_id": "PC-001-ledger-core",
                    "actor": "system",
                },
                "previous_hash": ZERO_HASH,
                "payload": {"session_id": "session-0195b8d1"},
                "hash": "sha256:b2bbde319c7c9677b6d6816d9b422c8ec9787c6d0ca7f64444f0715a8ca54ac8",
            }
        )
    except LedgerSerializationError as error:
        assert "float" in str(error)
    else:
        raise AssertionError("expected serialization error")
