"""MkDocs hook: sync source directories into docs/ before every build.

Mirrors:
  architecture/   → docs/architecture/       (hardlinks)
  Templates/      → docs/sawmill-templates/  (hardlinks)

On each build:
  1. New source files are hardlinked into docs/
  2. Stale docs files (no longer in source) are removed
  3. mkdocs.yml nav is regenerated from the current file list

MkDocs calls on_config before file collection (including live reload).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger("mkdocs.hooks.sync_docs")

# Root of the Brain_Factory repo (parent of this hooks/ directory)
REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"

# Source dir → docs subdir mapping
SYNC_MAP = {
    REPO_ROOT / "architecture": DOCS_DIR / "architecture",
    REPO_ROOT / "Templates": DOCS_DIR / "sawmill-templates",
}

# File extensions to sync
SYNC_EXTENSIONS = {".md", ".yaml", ".yml"}

# Files/dirs to skip
SKIP_NAMES = {".DS_Store", "__pycache__", "Archive"}


def _sync_directory(src: Path, dst: Path) -> tuple[int, int]:
    """Sync src → dst using hardlinks. Returns (added, removed) counts."""
    added = 0
    removed = 0

    dst.mkdir(parents=True, exist_ok=True)

    # Collect source files
    source_files: set[str] = set()
    for f in src.iterdir():
        if f.name in SKIP_NAMES:
            continue
        if f.is_file() and f.suffix in SYNC_EXTENSIONS:
            source_files.add(f.name)

    # Add new files (hardlink)
    for name in source_files:
        src_file = src / name
        dst_file = dst / name
        if not dst_file.exists():
            os.link(src_file, dst_file)
            log.info(f"Linked: {name}")
            added += 1
        else:
            # Check if hardlink is stale (different inode = file was replaced)
            if src_file.stat().st_ino != dst_file.stat().st_ino:
                dst_file.unlink()
                os.link(src_file, dst_file)
                log.info(f"Re-linked: {name}")
                added += 1

    # Remove stale files
    for f in dst.iterdir():
        if f.name in SKIP_NAMES:
            continue
        if f.is_file() and f.name not in source_files:
            f.unlink()
            log.info(f"Removed stale: {f.name}")
            removed += 1

    return added, removed


def _generate_nav() -> list:
    """Generate mkdocs nav from current docs/ contents."""
    nav = [{"Home": "index.md"}]

    # Architecture section — fixed order for authority docs, then alphabetical
    arch_dir = DOCS_DIR / "architecture"
    if arch_dir.exists():
        arch_items = []
        # Authority docs in spec order
        authority_order = [
            ("NORTH_STAR.md", "NORTH STAR — Read This First"),
            ("BUILDER_SPEC.md", "BUILDER SPEC — Assembly Instructions"),
            ("OPERATIONAL_SPEC.md", "OPERATIONAL SPEC — How DoPeJarMo Runs"),
            ("SAWMILL_ANALYSIS.md", "Sawmill Analysis"),
        ]
        seen = set()
        for filename, title in authority_order:
            if (arch_dir / filename).exists():
                arch_items.append({title: f"architecture/{filename}"})
                seen.add(filename)

        # Remaining architecture docs alphabetically
        for f in sorted(arch_dir.iterdir()):
            if f.is_file() and f.suffix == ".md" and f.name not in seen:
                title = f.stem.replace("_", " ").replace("-", " ").title()
                arch_items.append({title: f"architecture/{f.name}"})

        if arch_items:
            nav.append({"Architecture": arch_items})

    # Templates section — D-docs in order, then others alphabetically
    tmpl_dir = DOCS_DIR / "sawmill-templates"
    if tmpl_dir.exists():
        tmpl_items = []
        # Guide first
        if (tmpl_dir / "GUIDE.md").exists():
            tmpl_items.append({"Guide": "sawmill-templates/GUIDE.md"})

        # D1-D10 in order
        for i in range(1, 11):
            for f in sorted(tmpl_dir.iterdir()):
                if f.name.startswith(f"D{i}_") and f.suffix == ".md":
                    label = f.stem.replace("_", " — ", 1).replace("_", " ").title()
                    tmpl_items.append({label: f"sawmill-templates/{f.name}"})

        # Remaining templates alphabetically
        seen_tmpl = {"GUIDE.md"} | {
            f.name for f in tmpl_dir.iterdir()
            if f.name.startswith("D") and f.name[1:].split("_")[0].isdigit()
        }
        for f in sorted(tmpl_dir.iterdir()):
            if f.is_file() and f.suffix in {".md", ".yaml", ".yml"} and f.name not in seen_tmpl:
                title = f.stem.replace("_", " ").title()
                tmpl_items.append({title: f"sawmill-templates/{f.name}"})

        if tmpl_items:
            nav.append({"Templates": tmpl_items})

    return nav


def _update_mkdocs_yml(nav: list) -> bool:
    """Rewrite the nav section of mkdocs.yml. Returns True if changed."""
    import yaml

    yml_path = REPO_ROOT / "mkdocs.yml"
    with open(yml_path) as f:
        config = yaml.safe_load(f)

    old_nav = config.get("nav")
    if old_nav == nav:
        return False

    config["nav"] = nav
    with open(yml_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return True


def on_config(config, **kwargs):
    """MkDocs hook — runs before file collection on every build.

    on_config fires before MkDocs scans docs/ for files, so we can
    sync and update nav before it tries to read anything stale.
    """
    total_added = 0
    total_removed = 0

    for src, dst in SYNC_MAP.items():
        if src.exists():
            added, removed = _sync_directory(src, dst)
            total_added += added
            total_removed += removed

    if total_added or total_removed:
        log.info(f"Sync complete: {total_added} added, {total_removed} removed")

    nav = _generate_nav()

    # Update nav in-memory so this build uses the correct file list
    config["nav"] = nav

    # Also persist to disk for Backstage/CLI builds
    _update_mkdocs_yml(nav)

    return config
