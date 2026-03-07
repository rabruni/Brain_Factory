#!/usr/bin/env python3
"""Validate docs/PORTAL_MAP.yaml against its schema.

Exit 0 = all checks pass. Exit 1 = validation errors found.
Run from repo root: python3 docs/validate_portal_map.py
"""

import os
import sys
import yaml

MAP_PATH = os.path.join(os.path.dirname(__file__), "PORTAL_MAP.yaml")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VALID_SYNC = {"mirror", "narrative", "status"}
VALID_KEYS = {"source", "mirror", "narrative", "sync"}


def validate():
    with open(MAP_PATH) as f:
        data = yaml.safe_load(f)

    entries = data.get("entries")
    if not isinstance(entries, list):
        return ["top-level 'entries' must be a list"]

    errors = []
    for i, entry in enumerate(entries, 1):
        pfx = f"entry {i}"

        if not isinstance(entry, dict):
            errors.append(f"{pfx}: not a dict")
            continue

        # Unknown keys
        extra = set(entry.keys()) - VALID_KEYS
        if extra:
            errors.append(f"{pfx}: unknown keys {extra}")

        # sync required
        sync = entry.get("sync")
        if sync not in VALID_SYNC:
            errors.append(f"{pfx}: sync must be one of {VALID_SYNC}, got {sync!r}")
            continue

        has_source = "source" in entry
        has_narrative = "narrative" in entry
        has_mirror = "mirror" in entry

        # Exactly one of source or narrative
        if has_source == has_narrative:
            errors.append(f"{pfx}: must have exactly one of source or narrative")
            continue

        # sync-specific rules
        if sync == "mirror":
            if not has_source:
                errors.append(f"{pfx}: sync=mirror requires source")
            if has_narrative:
                errors.append(f"{pfx}: sync=mirror forbids narrative")
        else:
            if not has_narrative:
                errors.append(f"{pfx}: sync={sync} requires narrative")
            if has_source:
                errors.append(f"{pfx}: sync={sync} forbids source")
            if has_mirror:
                errors.append(f"{pfx}: sync={sync} forbids mirror")

        # Path existence
        for key in ("source", "mirror", "narrative"):
            path = entry.get(key)
            if path and not os.path.exists(os.path.join(REPO_ROOT, path)):
                errors.append(f"{pfx}: {key} path does not exist: {path}")

    return errors


if __name__ == "__main__":
    errors = validate()
    if errors:
        print(f"FAIL: {len(errors)} validation error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        with open(MAP_PATH) as f:
            count = len(yaml.safe_load(f)["entries"])
        print(f"PASS: {count} entries, 0 errors")
        sys.exit(0)
