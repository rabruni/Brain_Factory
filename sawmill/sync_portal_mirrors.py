#!/usr/bin/env python3
"""Synchronize docs mirror files declared in docs/PORTAL_MAP.yaml."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    print("FAIL: PyYAML is required to sync docs/PORTAL_MAP.yaml mirrors", file=sys.stderr)
    raise SystemExit(1) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synchronize mirror entries from docs/PORTAL_MAP.yaml")
    parser.add_argument("--map", default="docs/PORTAL_MAP.yaml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--sources", nargs="*", default=None)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def load_map(path: Path) -> list[dict]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Portal map not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise ValueError("Portal map must contain a top-level 'entries' list")
    return data["entries"]


def file_bytes(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read()


def sync_mirrors(repo_root: Path, entries: list[dict], sources: set[str] | None) -> list[str]:
    changed: list[str] = []
    for entry in entries:
        if entry.get("sync") != "mirror":
            continue
        source = entry.get("source")
        mirror = entry.get("mirror")
        if not source or not mirror:
            continue
        if sources is not None and source not in sources:
            continue

        source_path = repo_root / source
        mirror_path = repo_root / mirror

        if not source_path.exists():
            raise ValueError(f"Mirror source is missing: {source}")

        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        if mirror_path.exists() and file_bytes(source_path) == file_bytes(mirror_path):
            continue

        shutil.copy2(source_path, mirror_path)
        changed.append(mirror)

    return changed


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    map_path = (repo_root / args.map).resolve()
    try:
        entries = load_map(map_path)
        source_filter = set(args.sources) if args.sources else None
        changed = sync_mirrors(repo_root, entries, source_filter)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        for path in changed:
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
