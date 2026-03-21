"""
test_serialization.py — Tests for canonical_json() and canonical_hash().

≥8 tests required. Tests use hardcoded vectors — any deviation in the
serialization format breaks the hash chain and must be caught here.

Pre-computed test vector (verified externally):
  d = {"event_type": "session_start", "payload": {},
       "provenance": {"actor": "system", "framework_id": "FMWK-001", "pack_id": null},
       "schema_version": "1.0.0", "timestamp": "2026-03-21T03:21:00Z"}
  canonical: {"event_type":"session_start","payload":{},"provenance":{"actor":"system","framework_id":"FMWK-001","pack_id":null},"schema_version":"1.0.0","timestamp":"2026-03-21T03:21:00Z"}
  sha256: d91bae1c03bc2d1b2c97d45a5c2053de73731e3b84120f251c4ca6e28c14bafb
"""
import pytest

from ledger.serialization import canonical_json, canonical_hash


# ---------------------------------------------------------------------------
# canonical_json tests
# ---------------------------------------------------------------------------

def test_canonical_json_sorts_keys():
    """Keys must appear alphabetically regardless of insertion order."""
    d = {"z_field": 1, "a_field": 2, "m_field": 3}
    result = canonical_json(d)
    assert result == '{"a_field":2,"m_field":3,"z_field":1}'


def test_canonical_json_no_whitespace():
    """Output must have no spaces, tabs, or newlines."""
    d = {"event_type": "session_start", "payload": {}}
    result = canonical_json(d)
    assert " " not in result
    assert "\t" not in result
    assert "\n" not in result


def test_canonical_json_ensure_ascii_false():
    """UTF-8 strings must appear as literal characters, not escape sequences."""
    d = {"description": "café"}
    result = canonical_json(d)
    assert "café" in result
    # The unicode escape form must NOT appear
    assert "\\u00e9" not in result


def test_canonical_json_nested_keys_sorted():
    """Nested object keys must also appear alphabetically."""
    d = {
        "provenance": {
            "pack_id": None,
            "framework_id": "FMWK-001",
            "actor": "system",
        }
    }
    result = canonical_json(d)
    # actor < framework_id < pack_id alphabetically
    assert '"actor"' in result
    actor_pos = result.index('"actor"')
    framework_pos = result.index('"framework_id"')
    pack_pos = result.index('"pack_id"')
    assert actor_pos < framework_pos < pack_pos


def test_canonical_json_null_is_serialized():
    """Null values must appear as JSON null, not be omitted."""
    d = {"pack_id": None, "event_type": "session_start"}
    result = canonical_json(d)
    assert '"pack_id":null' in result


# ---------------------------------------------------------------------------
# canonical_hash tests
# ---------------------------------------------------------------------------

def test_canonical_hash_excludes_hash_field():
    """
    canonical_hash(d) must equal canonical_hash({k:v for k,v if k!='hash'}).
    The hash field is excluded to avoid circular computation.
    """
    d_with_hash = {
        "event_type": "session_start",
        "hash": "sha256:" + "a" * 64,
        "payload": {},
    }
    d_without_hash = {
        "event_type": "session_start",
        "payload": {},
    }
    assert canonical_hash(d_with_hash) == canonical_hash(d_without_hash)


def test_canonical_hash_test_vector():
    """Hardcoded reference vector — must match exactly (chain integrity depends on this)."""
    d = {
        "event_type": "session_start",
        "payload": {},
        "provenance": {"actor": "system", "framework_id": "FMWK-001", "pack_id": None},
        "schema_version": "1.0.0",
        "timestamp": "2026-03-21T03:21:00Z",
    }
    expected = "sha256:d91bae1c03bc2d1b2c97d45a5c2053de73731e3b84120f251c4ca6e28c14bafb"
    assert canonical_hash(d) == expected


def test_canonical_hash_any_field_change_changes_hash():
    """Changing any field must produce a different hash (avalanche property)."""
    base = {
        "event_type": "session_start",
        "schema_version": "1.0.0",
        "timestamp": "2026-03-21T03:21:00Z",
        "provenance": {"actor": "system", "framework_id": "FMWK-001", "pack_id": None},
        "payload": {},
    }
    base_hash = canonical_hash(base)

    for field, alt_value in [
        ("event_type", "session_end"),
        ("schema_version", "2.0.0"),
        ("timestamp", "2026-03-21T03:22:00Z"),
        ("payload", {"key": "value"}),
    ]:
        modified = dict(base)
        modified[field] = alt_value
        assert canonical_hash(modified) != base_hash, f"Changing {field!r} did not change hash"


def test_canonical_hash_null_fields_included():
    """
    A dict with {"field": null} must hash differently from a dict missing
    the field entirely. Null is NOT the same as absent (D3 Constraint).
    """
    with_null = {"event_type": "session_start", "pack_id": None}
    without_field = {"event_type": "session_start"}
    assert canonical_hash(with_null) != canonical_hash(without_field)


def test_float_string_vs_float_number_hash_differs():
    """
    Float as string ("0.1") must hash differently from float as number (0.1).
    D5 RQ-003: cross-language IEEE 754 divergence makes raw floats unsafe.
    The string form is the canonical representation.
    """
    string_form = {"val": "0.1"}
    number_form = {"val": 0.1}
    assert canonical_hash(string_form) != canonical_hash(number_form)


def test_canonical_hash_returns_sha256_prefix():
    """Return value must start with 'sha256:' and be exactly 71 chars."""
    d = {"event_type": "session_start", "payload": {}}
    result = canonical_hash(d)
    assert result.startswith("sha256:")
    assert len(result) == 71  # len("sha256:") + 64 hex chars


def test_canonical_hash_deterministic():
    """Same input always produces same output (no randomness)."""
    d = {"event_type": "session_start", "payload": {"key": "value"}}
    results = {canonical_hash(d) for _ in range(10)}
    assert len(results) == 1, "canonical_hash is not deterministic"
