from __future__ import annotations

from pathlib import Path

import yaml


def _ws():
    import workspace as ws

    return ws


def _brain():
    from shell.helpers import brain

    return brain


def parse_memory_file(path):
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    metadata = {}
    content = text.strip()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            metadata = yaml.safe_load(parts[1]) or {}
            content = parts[2].strip()
    return {
        "path": str(file_path),
        "name": file_path.name,
        "metadata": metadata,
        "content": content,
    }


def discover_memory_files(directory):
    root = Path(directory)
    return sorted(
        path for path in root.rglob("*.md")
        if path.is_file() and path.name != "MEMORY.md"
    )


def import_memory_files(directory, source):
    imported = []
    seen = set()
    for path in discover_memory_files(directory):
        parsed = parse_memory_file(path)
        content = parsed["content"]
        if not content:
            continue
        key = (content, source)
        if key in seen:
            continue
        ws = _ws()
        with ws._connect() as conn:
            ws._ensure_schema(conn)
            existing = conn.execute(
                "SELECT id FROM thoughts WHERE content = ? AND source = ? LIMIT 1",
                (content, source),
            ).fetchone()
        if existing:
            seen.add(key)
            continue
        seen.add(key)
        imported.append(_brain().capture(content=content, tags=[], source=source))
    return imported
