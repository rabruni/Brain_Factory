from __future__ import annotations

import importlib
import sys

from shell.helpers.brain_import import discover_memory_files, parse_memory_file


def _load_modules(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_DIR_OVERRIDE", str(tmp_path / "workspace"))
    for name in ["workspace", "shell.helpers.brain"]:
        sys.modules.pop(name, None)
    workspace = importlib.import_module("workspace")
    brain = importlib.import_module("shell.helpers.brain")
    return workspace, brain


def test_parse_memory_file_with_frontmatter(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("---\ntitle: Brain Note\ntags:\n  - alpha\n---\nRemember this.\n", encoding="utf-8")

    parsed = parse_memory_file(path)

    assert parsed["metadata"] == {"title": "Brain Note", "tags": ["alpha"]}
    assert parsed["content"] == "Remember this."


def test_parse_memory_file_without_frontmatter(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("Remember this.", encoding="utf-8")

    parsed = parse_memory_file(path)

    assert parsed["metadata"] == {}
    assert parsed["content"] == "Remember this."


def test_discover_memory_files_excludes_memory_md(tmp_path):
    keep = tmp_path / "keep.md"
    skip = tmp_path / "MEMORY.md"
    keep.write_text("Keep", encoding="utf-8")
    skip.write_text("Skip", encoding="utf-8")

    files = discover_memory_files(tmp_path)

    assert files == [keep]


def test_import_memory_files_skips_exact_duplicates(tmp_path, monkeypatch):
    _, brain = _load_modules(tmp_path, monkeypatch)
    import_module = importlib.import_module("shell.helpers.brain_import")

    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "one.md").write_text("Repeat me", encoding="utf-8")
    (notes_dir / "two.md").write_text("Repeat me", encoding="utf-8")

    monkeypatch.setattr(import_module, "_brain", lambda: brain)

    imported = import_module.import_memory_files(notes_dir, source="memory-import")
    repeated = import_module.import_memory_files(notes_dir, source="memory-import")

    assert len(imported) == 1
    assert repeated == []
