from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sawmill.run_state import load_events, load_heartbeat_records, load_json, project_status

from shell.config import ACTIVE_HEARTBEAT_SECONDS, ACTIVE_RUN_STATES, SAWMILL_DIR


def run_dirs() -> list[Path]:
    runs: list[Path] = []
    if not SAWMILL_DIR.exists():
        return runs
    for framework_dir in SAWMILL_DIR.iterdir():
        if not framework_dir.is_dir():
            continue
        runs_dir = framework_dir / "runs"
        if not runs_dir.exists():
            continue
        for run_dir in runs_dir.iterdir():
            if (run_dir / "status.json").exists():
                runs.append(run_dir)
    runs.sort(key=lambda path: (path / "status.json").stat().st_mtime, reverse=True)
    return runs


def heartbeat_age_seconds(run_dir: Path) -> int | None:
    records = load_heartbeat_records(run_dir)
    if not records:
        return None
    latest = records[-1].get("timestamp", "")
    if not latest:
        return None
    try:
        parsed = datetime.strptime(latest, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return max(0, int((datetime.now(timezone.utc) - parsed).total_seconds()))


def effective_run_status(run_dir: Path) -> tuple[dict, str]:
    raw_status = load_json(run_dir / "status.json")
    heartbeat_age = heartbeat_age_seconds(run_dir)
    try:
        status = dict(project_status(run_dir).status)
        source = "projected"
    except Exception as exc:
        status = dict(raw_status)
        source = f"raw_fallback:{type(exc).__name__}"
    if status.get("state") in ACTIVE_RUN_STATES:
        if heartbeat_age is None or heartbeat_age > ACTIVE_HEARTBEAT_SECONDS:
            status["state"] = "interrupted"
            status.setdefault("interruption_reason", "")
            if not status["interruption_reason"]:
                status["interruption_reason"] = "stale_or_missing_heartbeat"
    return status, source


def run_summary(run_dir: Path) -> dict:
    status, status_source = effective_run_status(run_dir)
    run_meta = load_json(run_dir / "run.json") if (run_dir / "run.json").exists() else {}
    events = load_events(run_dir / "events.jsonl")
    latest_event = events[-1] if events else {}
    heartbeat_age = heartbeat_age_seconds(run_dir)
    return {
        "run_id": status.get("run_id", run_dir.name),
        "framework": status.get("framework_id", run_dir.parent.parent.name),
        "state": status.get("state", ""),
        "current_turn": status.get("current_turn", ""),
        "current_step": status.get("current_step", ""),
        "current_role": status.get("current_role", ""),
        "started_at": run_meta.get("started_at", run_meta.get("timestamp", "")),
        "latest_event_summary": latest_event.get("summary", ""),
        "latest_event_timestamp": latest_event.get("timestamp", ""),
        "heartbeat_age_seconds": heartbeat_age,
        "worker_observation": status.get("worker_observation", ""),
        "last_worker_phase": status.get("last_worker_phase", ""),
        "last_orchestrator_phase": status.get("last_orchestrator_phase", ""),
        "interruption_reason": status.get("interruption_reason", ""),
        "status_source": status_source,
    }


def get_latest_run_summary() -> dict | None:
    runs = run_dirs()
    if not runs:
        return None
    detail = run_detail(runs[0])
    summary = run_summary(runs[0])
    summary["events"] = detail["events"][-5:]
    return summary


def run_detail(run_dir: Path) -> dict:
    status, status_source = effective_run_status(run_dir)
    events = load_events(run_dir / "events.jsonl")
    return {
        "status": status,
        "events": events[-30:],
        "heartbeat_age_seconds": heartbeat_age_seconds(run_dir),
        "framework": status.get("framework_id", run_dir.parent.parent.name),
        "run_id": status.get("run_id", run_dir.name),
        "status_source": status_source,
    }

