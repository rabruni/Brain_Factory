from __future__ import annotations

import re

import pytest

from ledger.errors import LedgerSerializationError
from ledger.serializer import (
    GENESIS_SENTINEL,
    canonical_bytes,
    check_no_floats,
    compute_hash,
)


def _event() -> dict:
    return {
        "event_id": "018e3b2a-4f6c-7e8d-9012-3456789abcde",
        "event_type": "session_start",
        "schema_version": "1.0.0",
        "timestamp": "2026-03-01T14:22:00Z",
        "provenance": {
            "framework_id": "FMWK-001",
            "pack_id": "PC-001-ledger",
            "actor": "system",
        },
        "payload": {"k": "v"},
        "sequence": 0,
        "previous_hash": GENESIS_SENTINEL,
        "hash": "sha256:" + "f" * 64,
    }


def test_canonical_json_excludes_hash_field() -> None:
    output = canonical_bytes(_event()).decode("utf-8")
    assert '"hash"' not in output


def test_canonical_json_sorted_keys() -> None:
    payload = {"z": 1, "a": 2}
    event = _event()
    event["payload"] = payload
    output = canonical_bytes(event).decode("utf-8")
    assert output.index('"event_id"') < output.index('"event_type"')
    assert output.index('"a"') < output.index('"z"')


def test_canonical_json_no_whitespace_between_tokens() -> None:
    output = canonical_bytes(_event()).decode("utf-8")
    assert ", " not in output
    assert ": " not in output


def test_canonical_json_ensure_ascii_false_literal_utf8() -> None:
    event = _event()
    event["payload"] = {"title": "café"}
    output = canonical_bytes(event)
    assert b"caf\xc3\xa9" in output
    assert b"\\u00e9" not in output


def test_canonical_json_null_field_included() -> None:
    event = _event()
    event["payload"] = {"field": None}
    output = canonical_bytes(event).decode("utf-8")
    assert '"field":null' in output


def test_canonical_json_integer_no_decimal() -> None:
    event = _event()
    event["payload"] = {"n": 42}
    output = canonical_bytes(event).decode("utf-8")
    assert '"n":42' in output
    assert '"n":42.0' not in output


def test_hash_format_matches_regex() -> None:
    value = compute_hash(_event())
    assert re.match(r"^sha256:[0-9a-f]{64}$", value)


def test_hash_lowercase_hex_only() -> None:
    value = compute_hash(_event())
    assert value == value.lower()


def test_float_detection_top_level_raises() -> None:
    with pytest.raises(LedgerSerializationError):
        check_no_floats({"v": 0.5})


def test_float_detection_nested_dict_raises() -> None:
    with pytest.raises(LedgerSerializationError):
        check_no_floats({"a": {"b": 0.1}})


def test_float_detection_in_list_raises() -> None:
    with pytest.raises(LedgerSerializationError):
        check_no_floats({"a": [1, 0.1, 2]})


def test_genesis_sentinel_exact_string() -> None:
    assert GENESIS_SENTINEL == "sha256:" + "0" * 64
