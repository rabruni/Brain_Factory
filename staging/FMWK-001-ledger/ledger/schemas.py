"""
ledger.schemas — Input validation for LedgerClient.append().

validate_event_data() is called BEFORE the write lock is acquired so that
invalid input is rejected without touching Ledger state.

Required fields in event_data dict (fields assigned by Ledger are NOT required):
  event_type   — string, must be one of the 15 EventType values
  schema_version — string
  timestamp      — string (ISO-8601 UTC+Z format)
  provenance     — dict with framework_id (str) and actor (str; "system"|"operator"|"agent")
  payload        — dict, must be JSON-serializable

Raises:
  LedgerSerializationError — any validation failure
"""
import json
from typing import Any, Dict

from ledger.errors import LedgerSerializationError
from ledger.models import EventType

# Valid actor values for provenance
_VALID_ACTORS = {"system", "operator", "agent"}

# EventType valid values (by string value, not enum member name)
_VALID_EVENT_TYPES = {et.value for et in EventType}

# Required top-level keys in event_data
_REQUIRED_KEYS = {"event_type", "schema_version", "timestamp", "provenance", "payload"}

# Required keys in provenance sub-dict
_REQUIRED_PROVENANCE_KEYS = {"framework_id", "actor"}


def validate_event_data(event_data: Dict[str, Any]) -> None:
    """
    Validate event_data dict before appending to the Ledger.

    Checks:
      1. event_data is a dict
      2. All required top-level keys are present
      3. event_type is one of the 15 valid EventType values
      4. provenance is a dict with framework_id and actor
      5. actor is one of "system", "operator", "agent"
      6. payload is a dict
      7. payload is JSON-serializable (catches non-serializable Python objects)
      8. schema_version and timestamp are non-empty strings

    Args:
        event_data: Dict supplied by the caller to LedgerClient.append().

    Raises:
        LedgerSerializationError: On any validation failure.
    """
    # 1. Must be a dict
    if not isinstance(event_data, dict):
        raise LedgerSerializationError(
            code="LEDGER_SERIALIZATION_ERROR",
            message=f"event_data must be a dict, got {type(event_data).__name__}",
        )

    # 2. All required keys present
    missing = _REQUIRED_KEYS - set(event_data.keys())
    if missing:
        raise LedgerSerializationError(
            code="LEDGER_SERIALIZATION_ERROR",
            message=f"Missing required field(s): {sorted(missing)}",
        )

    # 3. event_type must be a valid EventType value
    event_type = event_data["event_type"]
    if not isinstance(event_type, str) or event_type not in _VALID_EVENT_TYPES:
        raise LedgerSerializationError(
            code="LEDGER_SERIALIZATION_ERROR",
            message=(
                f"Invalid event_type: {event_type!r}. "
                f"Must be one of {sorted(_VALID_EVENT_TYPES)}"
            ),
        )

    # 4. schema_version must be a non-empty string
    schema_version = event_data["schema_version"]
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise LedgerSerializationError(
            code="LEDGER_SERIALIZATION_ERROR",
            message=f"schema_version must be a non-empty string, got {schema_version!r}",
        )

    # 5. timestamp must be a non-empty string
    timestamp = event_data["timestamp"]
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise LedgerSerializationError(
            code="LEDGER_SERIALIZATION_ERROR",
            message=f"timestamp must be a non-empty string, got {timestamp!r}",
        )

    # 6. provenance must be a dict with required keys
    provenance = event_data["provenance"]
    if not isinstance(provenance, dict):
        raise LedgerSerializationError(
            code="LEDGER_SERIALIZATION_ERROR",
            message=f"provenance must be a dict, got {type(provenance).__name__}",
        )
    missing_prov = _REQUIRED_PROVENANCE_KEYS - set(provenance.keys())
    if missing_prov:
        raise LedgerSerializationError(
            code="LEDGER_SERIALIZATION_ERROR",
            message=f"provenance missing required field(s): {sorted(missing_prov)}",
        )

    # 7. actor must be one of the valid values
    actor = provenance["actor"]
    if actor not in _VALID_ACTORS:
        raise LedgerSerializationError(
            code="LEDGER_SERIALIZATION_ERROR",
            message=f"provenance.actor must be one of {sorted(_VALID_ACTORS)}, got {actor!r}",
        )

    # 8. payload must be a dict
    payload = event_data["payload"]
    if not isinstance(payload, dict):
        raise LedgerSerializationError(
            code="LEDGER_SERIALIZATION_ERROR",
            message=f"payload must be a dict, got {type(payload).__name__}",
        )

    # 9. payload must be JSON-serializable (catches datetime, set, custom objects, etc.)
    try:
        json.dumps(payload)
    except (TypeError, ValueError) as exc:
        raise LedgerSerializationError(
            code="LEDGER_SERIALIZATION_ERROR",
            message=f"payload is not JSON-serializable: {exc}",
        ) from exc
