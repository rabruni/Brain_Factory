"""
ledger.serialization — Canonical JSON serialization and SHA-256 hashing.

CRITICAL: The canonical JSON format is the foundation of the hash chain.
Any deviation from this exact format breaks verify_chain() for all future
events. Do NOT change without human approval (D1 ASK FIRST boundary).

D3 Canonical JSON Constraint + D4 SIDE-002:
  json.dumps(d, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
  encoded as UTF-8 bytes, then SHA-256.

Rules enforced here:
  - sort_keys=True: deterministic key ordering (alphabetical)
  - separators=(',', ':'): no whitespace in output
  - ensure_ascii=False: literal UTF-8 chars (e.g. "café" not "\\u0063\\u0061\\u0066\\u00e9")
  - Null fields included as "key":null, NOT omitted
  - Float values in payloads MUST be passed as strings "0.1", not numbers 0.1
    (D5 RQ-003 — cross-language IEEE 754 divergence breaks hash matching)
  - The `hash` field is excluded when computing a new event's hash
"""
import hashlib
import json
from typing import Any, Dict

# Empty-Ledger sentinel hash: the genesis event's previous_hash (D6 CLR-002)
GENESIS_PREVIOUS_HASH = "sha256:" + "0" * 64


def canonical_json(event_dict: Dict[str, Any]) -> str:
    """
    Serialize event_dict to canonical JSON string.

    Guarantees:
      - Keys sorted alphabetically at every nesting level
      - No whitespace (compact separators)
      - Literal UTF-8 characters (ensure_ascii=False)
      - null values serialized as JSON null (not omitted)

    Args:
        event_dict: Any dict (may contain nested dicts, lists, nulls).

    Returns:
        Canonical JSON string.
    """
    return json.dumps(event_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(event_dict: Dict[str, Any]) -> str:
    """
    Compute the SHA-256 hash of event_dict's canonical JSON representation,
    EXCLUDING the 'hash' field (which would be circular).

    Args:
        event_dict: Full event dict. If 'hash' key is present, it is excluded
                    from the serialization before hashing.

    Returns:
        str: "sha256:" followed by 64 lowercase hex characters (71 chars total).
    """
    # Exclude the 'hash' field — it would be circular
    d = {k: v for k, v in event_dict.items() if k != "hash"}
    canonical_bytes = canonical_json(d).encode("utf-8")
    digest = hashlib.sha256(canonical_bytes).hexdigest()
    return "sha256:" + digest
