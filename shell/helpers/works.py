from __future__ import annotations

from pathlib import Path
import yaml

import workspace as ws

from shell.config import (
    BLUEPRINT_FILES,
    FWK_REGISTRY,
    KERNEL_FRAMEWORK_OWNS,
    LAUNCH_MANIFEST_FILENAME,
    SAWMILL_DIR,
    STAGING_DIR,
)
from shell.helpers.manifest import framework_dirs
from shell.helpers.run_state import run_dirs, run_summary


def _framework_dir(framework_id: str) -> Path:
    return SAWMILL_DIR / framework_id


def _staging_dir(framework_id: str) -> Path:
    return STAGING_DIR / framework_id


def _framework_ids() -> list[str]:
    return [row["framework_id"] for row in framework_dirs()]


def _all_known_framework_ids() -> list[str]:
    ids = set(_framework_ids())
    for meta in FWK_REGISTRY.values():
        ids.update(meta.get("framework_ids", []))
    return sorted(ids)


def list_fwk() -> list[dict]:
    return [
        {
            "fwk_id": fwk_id,
            "name": meta.get("name", fwk_id),
            "description": meta.get("description", ""),
            "framework_ids": list(meta.get("framework_ids", [])),
        }
        for fwk_id, meta in FWK_REGISTRY.items()
    ]


def _blueprint_summary(framework_id: str) -> dict:
    framework_dir = _framework_dir(framework_id)
    directory_exists = framework_dir.exists()
    files = []
    complete = 0
    for name in BLUEPRINT_FILES:
        path = framework_dir / name
        exists = path.exists()
        if exists:
            complete += 1
        files.append({"name": name, "path": str(path), "exists": exists})
    d6_path = framework_dir / "D6_GAP_ANALYSIS.md"
    task_md_exists = (framework_dir / "TASK.md").exists()
    source_material_exists = (framework_dir / "SOURCE_MATERIAL.md").exists()
    dependency_details = _dependency_details(framework_id)
    dependencies_met = all(dep["passed"] for dep in dependency_details)
    if not dependencies_met:
        blueprint_state = "blocked"
    elif task_md_exists:
        blueprint_state = "ready"
    elif directory_exists or source_material_exists:
        blueprint_state = "drafting"
    else:
        blueprint_state = "not_started"
    return {
        "directory_exists": directory_exists,
        "task_md_exists": task_md_exists,
        "source_material_exists": source_material_exists,
        "dependencies_met": dependencies_met,
        "dependency_details": dependency_details,
        "blueprint_state": blueprint_state,
        "complete_count": complete,
        "total_count": len(BLUEPRINT_FILES),
        "is_complete": complete == len(BLUEPRINT_FILES),
        "d6_path": str(d6_path),
        "last_updated": max(
            (path.stat().st_mtime for path in (framework_dir / name for name in BLUEPRINT_FILES) if path.exists()),
            default=None,
        ),
        "files": files,
    }


def _stub_summary(framework_id: str) -> dict:
    blueprint = _blueprint_summary(framework_id)
    return {
        "framework_id": framework_id,
        "name": framework_id,
        "owns": KERNEL_FRAMEWORK_OWNS.get(framework_id, ""),
        "manifest_exists": False,
        "blueprint": {
            "directory_exists": blueprint["directory_exists"],
            "task_md_exists": blueprint["task_md_exists"],
            "source_material_exists": blueprint["source_material_exists"],
            "dependencies_met": blueprint["dependencies_met"],
            "dependency_details": blueprint["dependency_details"],
            "blueprint_state": blueprint["blueprint_state"],
            "complete_count": blueprint["complete_count"],
            "total_count": blueprint["total_count"],
            "is_complete": blueprint["is_complete"],
        },
        "latest_run": None,
        "thread_count": 0,
        "agent_count": 0,
        "last_activity": "",
        "artifact_count": 0,
        "state": "not_started",
    }


def _dependency_map() -> dict[str, list[str]]:
    path = SAWMILL_DIR / "DEPENDENCIES.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    grouped: dict[str, list[str]] = {}
    for section in data.values():
        if isinstance(section, dict):
            for framework_id, deps in section.items():
                grouped[framework_id] = list(deps or [])
    return grouped


def _dependency_passed(framework_id: str) -> bool:
    report_path = _framework_dir(framework_id) / "EVALUATION_REPORT.md"
    if not report_path.exists():
        return False
    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "Final verdict: PASS" in content


def _dependency_details(framework_id: str) -> list[dict]:
    dependency_map = _dependency_map()
    return [
        {"framework_id": dependency_id, "passed": _dependency_passed(dependency_id)}
        for dependency_id in dependency_map.get(framework_id, [])
    ]


def _run_summaries_by_framework() -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for run_dir in run_dirs():
        summary = run_summary(run_dir)
        framework_id = summary.get("framework") or run_dir.parent.parent.name
        grouped.setdefault(framework_id, []).append(summary)
    return grouped


def _thread_framework_id(thread: dict, framework_ids: list[str]) -> tuple[str | None, str]:
    thread_items = thread.get("items", [])
    for item in thread_items:
        tags = item.get("tags") or []
        if isinstance(tags, list):
            for tag in tags:
                if tag in framework_ids:
                    return tag, "tag"
        for key in ("summary", "content"):
            value = str(item.get(key, "") or "")
            for framework_id in framework_ids:
                if framework_id in value:
                    return framework_id, "heuristic"
    summary = str(thread.get("summary", "") or "")
    for framework_id in framework_ids:
        if framework_id in summary:
            return framework_id, "heuristic"
    return None, ""


def _threads_by_framework() -> tuple[dict[str, list[dict]], list[dict]]:
    framework_ids = _all_known_framework_ids()
    grouped: dict[str, list[dict]] = {framework_id: [] for framework_id in framework_ids}
    scratchpad: list[dict] = []
    for thread in ws.list_threads():
        framework_id, source = _thread_framework_id(thread, framework_ids)
        summary = {
            "thread_id": thread["thread_id"],
            "summary": thread["summary"],
            "participants": thread["participants"],
            "latest": thread["latest"],
            "message_count": thread["message_count"],
            "has_active": any(it.get("status") in ("sent", "read") for it in thread.get("items", [])),
            "binding_source": source or "scratchpad",
        }
        if framework_id:
            grouped.setdefault(framework_id, []).append(summary)
        else:
            scratchpad.append(summary)
    return grouped, scratchpad


def _works_agents(framework_id: str, thread_summaries: list[dict]) -> list[dict]:
    thread_participants = {
        participant
        for thread in thread_summaries
        for participant in thread.get("participants", [])
        if participant and participant != "human"
    }
    agents = []
    for agent in ws.list_agent_configs(enabled=True):
        is_active = agent["name"] in thread_participants
        agents.append(
            {
                "name": agent["name"],
                "cli": agent["cli"],
                "agent_type": agent.get("agent_type", ""),
                "enabled": agent.get("enabled", True),
                "last_seen": agent.get("last_seen", ""),
                "active_in_works": is_active,
                "presence_source": "thread_activity" if is_active else "global_capability",
            }
        )
    return agents


def _artifact_summary(framework_id: str) -> dict:
    staging_dir = _staging_dir(framework_id)
    if not staging_dir.exists():
        return {"exists": False, "path": str(staging_dir), "file_count": 0}
    file_count = sum(1 for path in staging_dir.rglob("*") if path.is_file())
    return {"exists": True, "path": str(staging_dir), "file_count": file_count}


def _latest_run(run_summaries: list[dict]) -> dict | None:
    if not run_summaries:
        return None
    return sorted(
        run_summaries,
        key=lambda summary: (
            summary.get("latest_event_timestamp", ""),
            summary.get("started_at", ""),
            summary.get("run_id", ""),
        ),
        reverse=True,
    )[0]


def _passing_run(run_summaries: list[dict]) -> bool:
    latest = _latest_run(run_summaries)
    if not latest:
        return False
    state = latest.get("state", "")
    event = (latest.get("latest_event_summary", "") or "").lower()
    return state == "complete" and ("pass" in event or "passed" in event)


def _failed_run(run_summaries: list[dict]) -> bool:
    latest = _latest_run(run_summaries)
    if not latest:
        return False
    state = latest.get("state", "")
    event = (latest.get("latest_event_summary", "") or "").lower()
    return state in {"failed", "escalated"} or (state == "complete" and "fail" in event)


def derive_works_status(framework_id: str, blueprint: dict, run_summaries: list[dict]) -> str:
    latest = _latest_run(run_summaries)
    if latest and latest.get("state") == "running" and latest.get("heartbeat_age_seconds") is not None:
        return "running"
    if latest and latest.get("state") == "interrupted":
        return "interrupted"
    if _passing_run(run_summaries):
        return "passed"
    if _failed_run(run_summaries):
        return "failed"
    if blueprint.get("is_complete"):
        return "ready"
    return "not_started"


def works_summary(framework_id: str) -> dict:
    framework_rows = {row["framework_id"]: row for row in framework_dirs()}
    if framework_id not in framework_rows:
        if any(framework_id in meta.get("framework_ids", []) for meta in FWK_REGISTRY.values()):
            return _stub_summary(framework_id)
        raise ValueError(f"Unknown framework: {framework_id}")
    run_groups = _run_summaries_by_framework()
    threads_by_framework, _ = _threads_by_framework()
    blueprint = _blueprint_summary(framework_id)
    runs = run_groups.get(framework_id, [])
    latest = _latest_run(runs)
    threads = threads_by_framework.get(framework_id, [])
    agents = _works_agents(framework_id, threads)
    artifact = _artifact_summary(framework_id)
    return {
        "framework_id": framework_id,
        "name": framework_id,
        "owns": KERNEL_FRAMEWORK_OWNS.get(framework_id, ""),
        "manifest_exists": (_framework_dir(framework_id) / LAUNCH_MANIFEST_FILENAME).exists(),
        "blueprint": {
            "directory_exists": blueprint["directory_exists"],
            "task_md_exists": blueprint["task_md_exists"],
            "source_material_exists": blueprint["source_material_exists"],
            "dependencies_met": blueprint["dependencies_met"],
            "dependency_details": blueprint["dependency_details"],
            "blueprint_state": blueprint["blueprint_state"],
            "complete_count": blueprint["complete_count"],
            "total_count": blueprint["total_count"],
            "is_complete": blueprint["is_complete"],
        },
        "latest_run": latest,
        "thread_count": len(threads),
        "agent_count": len([agent for agent in agents if agent["active_in_works"]]),
        "last_activity": (latest or {}).get("latest_event_timestamp", "") or (latest or {}).get("started_at", ""),
        "artifact_count": artifact["file_count"],
        "state": derive_works_status(framework_id, blueprint, runs),
    }


def list_works() -> list[dict]:
    rows = [works_summary(framework_id) for framework_id in _framework_ids()]
    rows.sort(key=lambda row: (row.get("last_activity", ""), row.get("framework_id", "")), reverse=True)
    return rows


def get_works_threads(framework_id: str) -> list[dict]:
    known_frameworks = set(_all_known_framework_ids())
    if framework_id not in known_frameworks:
        raise ValueError(f"Unknown framework: {framework_id}")
    threads_by_framework, _ = _threads_by_framework()
    return threads_by_framework.get(framework_id, [])


def list_scratchpad_threads() -> list[dict]:
    _, scratchpad = _threads_by_framework()
    return scratchpad


def get_works_detail(framework_id: str) -> dict:
    known_frameworks = set(_all_known_framework_ids())
    if framework_id not in known_frameworks:
        raise ValueError(f"Unknown framework: {framework_id}")
    if framework_id not in _framework_ids():
        stub = _stub_summary(framework_id)
        return {
            "framework_id": framework_id,
            "name": framework_id,
            "owns": KERNEL_FRAMEWORK_OWNS.get(framework_id, ""),
            "state": "not_started",
            "blueprint": _blueprint_summary(framework_id),
            "manifest": {
                "exists": False,
                "path": str(_framework_dir(framework_id) / LAUNCH_MANIFEST_FILENAME),
            },
            "runs": [],
            "latest_run": None,
            "threads": [],
            "agents": _works_agents(framework_id, []),
            "artifacts": _artifact_summary(framework_id),
        }
    blueprint = _blueprint_summary(framework_id)
    run_groups = _run_summaries_by_framework()
    runs = run_groups.get(framework_id, [])
    latest = _latest_run(runs)
    threads = get_works_threads(framework_id)
    agents = _works_agents(framework_id, threads)
    artifact = _artifact_summary(framework_id)
    return {
        "framework_id": framework_id,
        "name": framework_id,
        "owns": KERNEL_FRAMEWORK_OWNS.get(framework_id, ""),
        "state": derive_works_status(framework_id, blueprint, runs),
        "blueprint": blueprint,
        "manifest": {
            "exists": (_framework_dir(framework_id) / LAUNCH_MANIFEST_FILENAME).exists(),
            "path": str(_framework_dir(framework_id) / LAUNCH_MANIFEST_FILENAME),
        },
        "runs": runs,
        "latest_run": latest,
        "threads": threads,
        "agents": agents,
        "artifacts": artifact,
    }


def list_works_by_lifecycle(fwk_id: str) -> dict:
    registry = FWK_REGISTRY.get(fwk_id)
    if not registry:
        raise ValueError(f"Unknown FWK: {fwk_id}")

    grouped = {"blueprints": [], "sawmill": [], "factory": []}
    promoted_frameworks: set[str] = set()

    for framework_id in registry.get("framework_ids", []):
        summary = works_summary(framework_id)
        latest_run = summary.get("latest_run") or {}
        state = summary.get("state", "not_started")
        has_runs = bool(latest_run)
        is_promoted = framework_id in promoted_frameworks

        if is_promoted:
            section = "factory"
            sidebar_summary = "production · healthy"
        elif has_runs or state in {"running", "interrupted", "passed", "failed", "ready"}:
            section = "sawmill"
            if state in {"passed", "ready"} and has_runs:
                sidebar_summary = "passed · awaiting promotion"
            elif state == "ready":
                sidebar_summary = "passed"
            elif state == "interrupted":
                turn = latest_run.get("current_turn") or latest_run.get("current_step") or "unknown"
                sidebar_summary = f"interrupted · {turn}"
            elif state == "running":
                turn = latest_run.get("current_turn") or latest_run.get("current_step") or "running"
                role = latest_run.get("current_role") or "worker"
                sidebar_summary = f"{turn} · {role}"
            elif state == "failed":
                sidebar_summary = "failed"
            else:
                sidebar_summary = state
        else:
            section = "blueprints"
            blueprint_state = summary["blueprint"].get("blueprint_state", "not_started")
            if blueprint_state == "blocked":
                sidebar_summary = "blocked"
            elif blueprint_state == "ready":
                sidebar_summary = "ready for sawmill"
            elif blueprint_state == "drafting":
                sidebar_summary = "TASK.md missing"
            else:
                sidebar_summary = "not started"

        grouped[section].append(
            {
                **summary,
                "lifecycle_section": section,
                "sidebar_summary": sidebar_summary,
                "awaiting_promotion": section == "sawmill" and has_runs and state in {"passed", "ready"},
            }
        )

    return grouped
