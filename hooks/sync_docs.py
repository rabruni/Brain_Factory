"""MkDocs hook: sync source directories into docs/ and auto-generate nav.

Mirrors every significant file in the Brain Factory repo into docs/ so
Backstage TechDocs can render it:

  architecture/          → docs/architecture/          (hardlinks, .md)
  Templates/             → docs/sawmill-templates/     (hardlinks, .md/.yaml)
  sawmill/FMWK-*/        → docs/spec-packs/FMWK-*/    (.md hardlinks + wrappers)
  staging/FMWK-*/        → docs/staging/FMWK-*/        (wrappers for code)
  .holdouts/FMWK-*/      → docs/holdouts/FMWK-*/      (.md hardlinks)
  sawmill/prompts/       → docs/sawmill-source/prompts/  (wrappers for .txt)
  sawmill/workers/       → docs/sawmill-source/workers/  (wrappers for .py)
  sawmill/*.yaml         → docs/sawmill-source/registries/ (wrappers)
  sawmill/*.py|*.sh      → docs/sawmill-source/scripts/   (wrappers)

Non-Markdown files get wrapper .md pages with syntax-highlighted code blocks.
Large files (>500 lines) are truncated with a source-path note.

Nav is generated dynamically — no hand-maintained nav: block needed in mkdocs.yml.
MkDocs calls on_config before file collection, so synced files are picked up.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

log = logging.getLogger("mkdocs.hooks.sync_docs")

# ── Constants ─────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"

# Directory names to skip during recursive walks
SKIP_DIRS = frozenset({
    "runs", "logs", "heartbeats", "__pycache__", "Archive",
    ".DS_Store", "node_modules", "compressed",
})

SKIP_FILES = frozenset({".DS_Store"})

# Max source lines before a wrapper truncates
WRAPPER_MAX_LINES = 500

# Extension → syntax-highlight language
LANG_MAP = {
    ".py": "python",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".txt": "text",
    ".json": "json",
    ".toml": "toml",
}

WRAPPER_EXTENSIONS = frozenset(LANG_MAP.keys())


# ── Sync helpers ──────────────────────────────────────────────────────

def _sync_file_hardlink(src: Path, dst: Path) -> bool:
    """Hardlink src to dst. Returns True if a link was created or refreshed."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        try:
            if src.stat().st_ino == dst.stat().st_ino:
                return False  # already linked
        except OSError:
            pass
        dst.unlink()
    os.link(src, dst)
    return True


def _generate_wrapper(src: Path, dst_md: Path) -> bool:
    """Generate a Markdown wrapper for a non-Markdown source file.

    Returns True if the wrapper was created or updated.
    """
    rel_path = src.relative_to(REPO_ROOT)
    lang = LANG_MAP.get(src.suffix, "text")

    try:
        content = src.read_text(errors="replace")
    except Exception:
        return False

    lines = content.splitlines()
    truncated = len(lines) > WRAPPER_MAX_LINES
    if truncated:
        lines = lines[:WRAPPER_MAX_LINES]

    body = "\n".join(lines)

    wrapper = f"# {src.name}\n\n"
    wrapper += f"> Source: `{rel_path}`\n\n"
    wrapper += f"```{lang}\n{body}\n```\n"
    if truncated:
        wrapper += (
            f"\n*Truncated at {WRAPPER_MAX_LINES} lines "
            f"— see source file for full content.*\n"
        )

    dst_md.parent.mkdir(parents=True, exist_ok=True)

    if dst_md.exists():
        try:
            if dst_md.read_text() == wrapper:
                return False
        except Exception:
            pass

    dst_md.write_text(wrapper)
    return True


def _sync_tree(
    src_dir: Path,
    dst_dir: Path,
    *,
    hardlink_exts: frozenset[str] = frozenset({".md"}),
    wrapper_exts: frozenset[str] = frozenset(),
) -> tuple[int, int]:
    """Recursively sync src_dir → dst_dir.

    - Files with extensions in hardlink_exts are hardlinked as-is.
    - Files with extensions in wrapper_exts get a .md wrapper generated.
    - SKIP_DIRS are pruned during the walk.

    Returns (added, removed) counts.
    """
    if not src_dir.exists():
        return 0, 0

    added = 0
    removed = 0
    source_rels: set[str] = set()

    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        root_path = Path(root)

        for fname in files:
            if fname in SKIP_FILES:
                continue
            src_file = root_path / fname
            rel = src_file.relative_to(src_dir)

            if src_file.suffix in hardlink_exts:
                dst_file = dst_dir / rel
                source_rels.add(str(rel))
                if _sync_file_hardlink(src_file, dst_file):
                    log.info("Linked: %s", rel)
                    added += 1

            elif src_file.suffix in wrapper_exts:
                wrapper_rel = str(rel) + ".md"
                dst_file = dst_dir / wrapper_rel
                source_rels.add(wrapper_rel)
                if _generate_wrapper(src_file, dst_file):
                    log.info("Wrapper: %s", rel)
                    added += 1

    # Remove stale files in dst that no longer have sources
    if dst_dir.exists():
        for root, dirs, files in os.walk(dst_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            root_path = Path(root)
            for fname in files:
                dst_file = root_path / fname
                rel = str(dst_file.relative_to(dst_dir))
                if rel not in source_rels:
                    dst_file.unlink()
                    log.info("Removed stale: %s", rel)
                    removed += 1

        _cleanup_empty_dirs(dst_dir)

    return added, removed


def _sync_flat_files(
    src_dir: Path,
    patterns: list[str],
    dst_dir: Path,
) -> tuple[int, int]:
    """Sync top-level files matching glob patterns from src_dir as wrappers.

    All patterns share the same dst_dir, so stale cleanup happens once
    after all patterns are collected.

    Returns (added, removed) counts.
    """
    if not src_dir.exists():
        return 0, 0

    added = 0
    removed = 0
    source_wrappers: set[str] = set()

    for pattern in patterns:
        for src_file in sorted(src_dir.glob(pattern)):
            if not src_file.is_file() or src_file.name in SKIP_FILES:
                continue
            # Only top-level files (not in subdirectories)
            if src_file.parent != src_dir:
                continue

            wrapper_name = src_file.name + ".md"
            dst_file = dst_dir / wrapper_name
            source_wrappers.add(wrapper_name)

            if _generate_wrapper(src_file, dst_file):
                log.info("Wrapper: %s", src_file.name)
                added += 1

    # Clean up stale wrappers
    if dst_dir.exists():
        for f in dst_dir.iterdir():
            if f.is_file() and f.name not in source_wrappers:
                f.unlink()
                log.info("Removed stale wrapper: %s", f.name)
                removed += 1

    return added, removed


def _cleanup_empty_dirs(base: Path) -> None:
    """Remove empty directories under base, bottom-up."""
    if not base.exists():
        return
    for root, dirs, _files in os.walk(base, topdown=False):
        root_path = Path(root)
        if root_path == base:
            continue
        try:
            if not any(root_path.iterdir()):
                root_path.rmdir()
        except OSError:
            pass


# ── Nav helpers ───────────────────────────────────────────────────────

def _title_from_stem(stem: str) -> str:
    """Convert a filename stem to a human-readable title."""
    return stem.replace("_", " ").replace("-", " ").title()


def _is_code_wrapper(name: str) -> bool:
    """True if filename looks like a wrapper (e.g. run.sh.md, ledger.py.md)."""
    stem = Path(name).stem  # removes final .md
    return any(stem.endswith(ext) for ext in LANG_MAP)


def _fmwk_title(fmwk_id: str) -> str:
    """Convert 'FMWK-001-ledger' → 'FMWK-001 Ledger'."""
    parts = fmwk_id.split("-", 2)
    if len(parts) >= 3:
        return f"{parts[0]}-{parts[1]} {parts[2].replace('-', ' ').title()}"
    return fmwk_id


def _collect_tree_items(base_dir: Path, nav_prefix: str) -> list:
    """Collect nav items from a directory tree.

    Top-level files are listed first, then subdirectories are grouped.
    """
    if not base_dir.exists():
        return []

    items = []

    # Top-level files
    for f in sorted(base_dir.iterdir()):
        if f.is_file() and f.suffix == ".md":
            title = f.stem if _is_code_wrapper(f.name) else _title_from_stem(f.stem)
            items.append({title: f"{nav_prefix}/{f.name}"})

    # Subdirectories — group them
    for sub in sorted(base_dir.iterdir()):
        if not sub.is_dir() or sub.name in SKIP_DIRS:
            continue
        sub_items = []
        for root, dirs, files in os.walk(sub):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            root_path = Path(root)
            for fname in sorted(files):
                f = root_path / fname
                if f.suffix != ".md":
                    continue
                rel = f.relative_to(base_dir)
                title = f.stem if _is_code_wrapper(f.name) else _title_from_stem(f.stem)
                sub_items.append({title: f"{nav_prefix}/{rel}"})
        if sub_items:
            sub_title = _title_from_stem(sub.name)
            items.append({sub_title: sub_items})

    return items


def _spec_pack_items(pack_dir: Path, nav_prefix: str) -> list:
    """Nav items for a spec pack — D1-D10 first, then remaining alpha."""
    if not pack_dir.exists():
        return []

    items = []
    seen: set[str] = set()

    # D1-D10 in order
    for i in range(1, 11):
        d_prefix = f"D{i}_"
        for f in sorted(pack_dir.iterdir()):
            if f.is_file() and f.suffix == ".md" and f.name.startswith(d_prefix):
                title = f"D{i} — " + _title_from_stem(f.stem[len(d_prefix):])
                items.append({title: f"{nav_prefix}/{f.name}"})
                seen.add(f.name)

    # Everything else alpha
    for f in sorted(pack_dir.iterdir()):
        if f.is_file() and f.suffix == ".md" and f.name not in seen:
            title = f.stem if _is_code_wrapper(f.name) else _title_from_stem(f.stem)
            items.append({title: f"{nav_prefix}/{f.name}"})

    return items


# ── Nav sections ──────────────────────────────────────────────────────

AUDIT_RE = re.compile(r"(AUDIT|READINESS|CLEANUP|SAFETY)", re.IGNORECASE)


def _nav_audits() -> dict | None:
    """Audits section — auto-discovered by filename pattern."""
    items = []

    for search_dir, prefix in [
        (DOCS_DIR / "sawmill", "sawmill/"),
        (DOCS_DIR / "architecture", "architecture/"),
    ]:
        if not search_dir.exists():
            continue
        for f in sorted(search_dir.iterdir()):
            if f.is_file() and f.suffix == ".md" and AUDIT_RE.search(f.name):
                title = f.stem.replace("-", " ").replace("_", " ")
                title = re.sub(r"\s+", " ", title).strip()
                items.append({title: f"{prefix}{f.name}"})

    return {"Audits": items} if items else None


def _nav_how_it_works() -> dict | None:
    """How It Works section — fixed order."""
    ordered = [
        ("Pipeline Overview", "sawmill/PIPELINE_VISUAL.md"),
        ("Agent Onboarding", "agent-onboarding.md"),
        ("Cold Start Protocol", "sawmill/COLD_START.md"),
        ("Execution Contract", "sawmill/EXECUTION_CONTRACT.md"),
        ("Agent Traversal", "sawmill/AGENT_TRAVERSAL.md"),
        ("Sawmill Role Registry", "sawmill/ROLE_REGISTRY.md"),
        ("Run Verification", "sawmill/RUN_VERIFICATION.md"),
        ("Institutional Context", "institutional-context.md"),
    ]
    items = [
        {title: path}
        for title, path in ordered
        if (DOCS_DIR / path).exists()
    ]
    return {"How It Works": items} if items else None


def _nav_architecture() -> dict | None:
    """Architecture section — authority docs first, then alphabetical."""
    arch_dir = DOCS_DIR / "architecture"
    if not arch_dir.exists():
        return None

    authority_order = [
        ("NORTH_STAR.md", "NORTH STAR — Why"),
        ("BUILDER_SPEC.md", "BUILDER SPEC — What"),
        ("OPERATIONAL_SPEC.md", "OPERATIONAL SPEC — How"),
        ("BUILD-PLAN.md", "Build Plan"),
        ("SDK_DIAGRAMS.md", "Platform SDK Diagrams"),
        ("FRAMEWORK_REGISTRY.md", "Framework Registry"),
        ("AGENT_CONSTRAINTS.md", "Agent Constraints"),
        ("SAWMILL_ANALYSIS.md", "Sawmill Analysis"),
    ]

    items = []
    seen = set()
    for filename, title in authority_order:
        if (arch_dir / filename).exists():
            items.append({title: f"architecture/{filename}"})
            seen.add(filename)

    for f in sorted(arch_dir.iterdir()):
        if f.is_file() and f.suffix == ".md" and f.name not in seen:
            if AUDIT_RE.search(f.name):
                continue  # audits go in the Audits section
            title = _title_from_stem(f.stem)
            items.append({title: f"architecture/{f.name}"})

    return {"Architecture": items} if items else None


def _nav_agent_roles() -> dict | None:
    """Agent Roles section — alphabetical with known role titles."""
    agents_dir = DOCS_DIR / "agents"
    if not agents_dir.exists():
        return None

    role_titles = {
        "orchestrator.md": "Orchestrator (Pipeline Manager)",
        "spec-agent.md": "Spec Agent (A — Spec Writing + B — Build Planning)",
        "holdout-agent.md": "Holdout Agent (C — Acceptance Test Writing)",
        "builder.md": "Builder (D — Code Building)",
        "reviewer.md": "Reviewer (D — 13Q Review)",
        "evaluator.md": "Evaluator (E — Evaluation)",
        "auditor.md": "Auditor (Portal Coherence)",
        "portal-steward.md": "Portal Steward (Documentation Alignment)",
    }

    items = []
    for f in sorted(agents_dir.iterdir()):
        if f.is_file() and f.suffix == ".md":
            title = role_titles.get(
                f.name, _title_from_stem(f.stem)
            )
            items.append({title: f"agents/{f.name}"})

    return {"Agent Roles": items} if items else None


def _nav_templates() -> dict | None:
    """Templates — Guide, D1-D10 in order, then build standards alpha."""
    tmpl_dir = DOCS_DIR / "sawmill-templates"
    if not tmpl_dir.exists():
        return None

    items = []
    seen: set[str] = set()

    # Guide first
    if (tmpl_dir / "GUIDE.md").exists():
        items.append({"Guide — How to Use D1-D10": "sawmill-templates/GUIDE.md"})
        seen.add("GUIDE.md")

    # D1-D10 in order
    for i in range(1, 11):
        prefix = f"D{i}_"
        for f in sorted(tmpl_dir.iterdir()):
            if f.name.startswith(prefix) and f.suffix == ".md":
                label = f"D{i} — " + _title_from_stem(f.stem[len(prefix):])
                items.append({label: f"sawmill-templates/{f.name}"})
                seen.add(f.name)

    # Remaining files alphabetically (build standards, YAML, etc.)
    for f in sorted(tmpl_dir.iterdir()):
        if f.is_file() and f.name not in seen:
            if f.suffix in {".md", ".yaml", ".yml"}:
                title = _title_from_stem(f.stem)
                items.append({title: f"sawmill-templates/{f.name}"})
                seen.add(f.name)

    # Compression standard (lives in docs/compressed/)
    comp_dir = DOCS_DIR / "compressed"
    if comp_dir.exists():
        for f in sorted(comp_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                title = _title_from_stem(f.stem)
                items.append({title: f"compressed/{f.name}"})

    return {"Templates": items} if items else None


def _nav_frameworks() -> dict | None:
    """Frameworks section — per-framework grouping of all artifacts.

    Each framework gets status page + spec pack + staging code + holdouts
    grouped together. Frameworks with only a status page get a direct link.
    """
    sawmill_dir = DOCS_DIR / "sawmill"
    fmwk_re = re.compile(r"^(FMWK-\d{3}-[a-z][a-z0-9-]*)\.md$")

    # Discover all framework IDs across all sources
    fmwk_ids: dict[str, str] = {}  # dirname → nice title

    if sawmill_dir.exists():
        for f in sorted(sawmill_dir.iterdir()):
            m = fmwk_re.match(f.name)
            if m and not AUDIT_RE.search(f.name):
                fmwk_id = m.group(1)
                fmwk_ids[fmwk_id] = _fmwk_title(fmwk_id)

    for subdir in ["spec-packs", "staging", "holdouts"]:
        base = DOCS_DIR / subdir
        if base.exists():
            for d in sorted(base.iterdir()):
                if d.is_dir() and d.name.startswith("FMWK-"):
                    fmwk_ids.setdefault(d.name, _fmwk_title(d.name))

    if not fmwk_ids:
        return None

    items = []
    for fmwk_id in sorted(fmwk_ids):
        title = fmwk_ids[fmwk_id]
        fmwk_items: list = []

        # Status page
        status_path = f"sawmill/{fmwk_id}.md"
        if (DOCS_DIR / status_path).exists():
            fmwk_items.append({"Status": status_path})

        # Spec pack (D1-D10 ordered)
        spec_dir = DOCS_DIR / "spec-packs" / fmwk_id
        if spec_dir.exists():
            spec_items = _spec_pack_items(spec_dir, f"spec-packs/{fmwk_id}")
            if spec_items:
                fmwk_items.append({"Spec Pack": spec_items})

        # Staging code (grouped by subdir)
        stg_dir = DOCS_DIR / "staging" / fmwk_id
        if stg_dir.exists():
            stg_items = _collect_tree_items(stg_dir, f"staging/{fmwk_id}")
            if stg_items:
                fmwk_items.append({"Staging Code": stg_items})

        # Holdouts
        hold_dir = DOCS_DIR / "holdouts" / fmwk_id
        if hold_dir.exists():
            hold_items = _collect_tree_items(hold_dir, f"holdouts/{fmwk_id}")
            if hold_items:
                fmwk_items.append({"Holdouts": hold_items})

        if not fmwk_items:
            continue

        # Single-entry frameworks (status only) get a direct link
        if (
            len(fmwk_items) == 1
            and isinstance(fmwk_items[0], dict)
            and "Status" in fmwk_items[0]
        ):
            items.append({title: fmwk_items[0]["Status"]})
        else:
            items.append({title: fmwk_items})

    return {"Frameworks": items} if items else None


def _nav_sawmill_source() -> dict | None:
    """Sawmill Source — registries, scripts, prompts, workers."""
    base = DOCS_DIR / "sawmill-source"
    if not base.exists():
        return None

    items = []

    # Top-level files first
    for f in sorted(base.iterdir()):
        if f.is_file() and f.suffix == ".md":
            title = f.stem if _is_code_wrapper(f.name) else _title_from_stem(f.stem)
            items.append({title: f"sawmill-source/{f.name}"})

    # Subdirectories (registries, scripts, prompts, workers)
    for sub in sorted(base.iterdir()):
        if not sub.is_dir() or sub.name in SKIP_DIRS:
            continue
        sub_items = []
        for f in sorted(sub.iterdir()):
            if f.is_file() and f.suffix == ".md":
                title = f.stem if _is_code_wrapper(f.name) else _title_from_stem(f.stem)
                sub_items.append({title: f"sawmill-source/{sub.name}/{f.name}"})
        if sub_items:
            sub_title = _title_from_stem(sub.name)
            items.append({sub_title: sub_items})

    return {"Sawmill Source": items} if items else None


def _nav_reference() -> dict | None:
    """Reference — portal governance + system topology merged."""
    ordered = [
        ("Portal Truth Model", "PORTAL_TRUTH_MODEL.md"),
        ("System Execution Plan", "SYSTEM_EXECUTION_PLAN.md"),
        ("Portal Constitution", "PORTAL_CONSTITUTION.md"),
        ("Portal Status", "PORTAL_STATUS.md"),
        ("DoPeJarMo Catalog", "dopejar-catalog.md"),
        ("TechDocs URL Registry", "TECHDOCS_URLS.md"),
    ]
    items = [
        {title: path}
        for title, path in ordered
        if (DOCS_DIR / path).exists()
    ]
    return {"Reference": items} if items else None


# ── Nav assembly ──────────────────────────────────────────────────────

def _generate_nav() -> list:
    """Generate the full mkdocs nav from current docs/ contents."""
    nav: list = []

    # Home (flat entries, not a section)
    nav.append({"Home": "index.md"})
    if (DOCS_DIR / "status.md").exists():
        nav.append({"Status and Gaps": "status.md"})

    sections = [
        _nav_audits(),
        _nav_architecture(),
        _nav_how_it_works(),
        _nav_agent_roles(),
        _nav_templates(),
        _nav_frameworks(),
        _nav_sawmill_source(),
        _nav_reference(),
    ]

    for section in sections:
        if section is not None:
            nav.append(section)

    return nav


# ── Main sync logic ──────────────────────────────────────────────────

def _run_sync() -> tuple[int, int]:
    """Run all sync operations. Returns (total_added, total_removed)."""
    total_a = 0
    total_r = 0

    def _accum(result: tuple[int, int]) -> None:
        nonlocal total_a, total_r
        total_a += result[0]
        total_r += result[1]

    sawmill_dir = REPO_ROOT / "sawmill"

    # 1. Architecture — hardlink .md only
    _accum(_sync_tree(
        REPO_ROOT / "architecture",
        DOCS_DIR / "architecture",
        hardlink_exts=frozenset({".md"}),
    ))

    # 2. Templates — hardlink .md and .yaml (existing behavior)
    _accum(_sync_tree(
        REPO_ROOT / "Templates",
        DOCS_DIR / "sawmill-templates",
        hardlink_exts=frozenset({".md", ".yaml", ".yml"}),
    ))

    # 3. Spec packs — hardlink .md, wrap code/json
    for fmwk_dir in sorted(sawmill_dir.glob("FMWK-*")):
        if fmwk_dir.is_dir():
            _accum(_sync_tree(
                fmwk_dir,
                DOCS_DIR / "spec-packs" / fmwk_dir.name,
                hardlink_exts=frozenset({".md"}),
                wrapper_exts=WRAPPER_EXTENSIONS,
            ))

    # 4. Staging — hardlink .md, wrap code
    staging_dir = REPO_ROOT / "staging"
    if staging_dir.exists():
        for fmwk_dir in sorted(staging_dir.glob("FMWK-*")):
            if fmwk_dir.is_dir():
                _accum(_sync_tree(
                    fmwk_dir,
                    DOCS_DIR / "staging" / fmwk_dir.name,
                    hardlink_exts=frozenset({".md"}),
                    wrapper_exts=WRAPPER_EXTENSIONS,
                ))

    # 5. Holdouts — hardlink .md only
    holdouts_dir = REPO_ROOT / ".holdouts"
    if holdouts_dir.exists():
        for fmwk_dir in sorted(holdouts_dir.glob("FMWK-*")):
            if fmwk_dir.is_dir():
                _accum(_sync_tree(
                    fmwk_dir,
                    DOCS_DIR / "holdouts" / fmwk_dir.name,
                    hardlink_exts=frozenset({".md"}),
                ))

    # 6. Sawmill prompts
    _accum(_sync_tree(
        sawmill_dir / "prompts",
        DOCS_DIR / "sawmill-source" / "prompts",
        wrapper_exts=WRAPPER_EXTENSIONS,
    ))

    # 7. Sawmill workers
    _accum(_sync_tree(
        sawmill_dir / "workers",
        DOCS_DIR / "sawmill-source" / "workers",
        wrapper_exts=WRAPPER_EXTENSIONS,
    ))

    # 8. Sawmill top-level registries
    _accum(_sync_flat_files(
        sawmill_dir,
        ["*.yaml", "*.yml"],
        DOCS_DIR / "sawmill-source" / "registries",
    ))

    # 9. Sawmill top-level scripts
    _accum(_sync_flat_files(
        sawmill_dir,
        ["*.py", "*.sh"],
        DOCS_DIR / "sawmill-source" / "scripts",
    ))

    return total_a, total_r


# ── MkDocs hook entry point ──────────────────────────────────────────

def on_config(config, **kwargs):
    """MkDocs hook — runs before file collection on every build.

    1. Syncs source files into docs/ (hardlinks + wrappers).
    2. Generates nav from docs/ contents and sets it in-memory.
    """
    try:
        total_added, total_removed = _run_sync()

        if total_added or total_removed:
            log.info(
                "Sync complete: %d added, %d removed",
                total_added, total_removed,
            )

        config["nav"] = _generate_nav()

    except Exception:
        log.exception("sync_docs hook failed — building with existing state")

    return config
