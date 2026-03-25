"""Run harness state machine and heartbeat extraction."""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_STATES = {
    "running",
    "retrying",
    "interrupted",
    "escalated",
    "failed",
    "passed",
    "invalidated",
}
TERMINAL_STATES = {"escalated", "failed", "passed", "invalidated"}
EVENT_TYPES = {
    "run_started",
    "preflight_passed",
    "turn_started",
    "prompt_rendered",
    "agent_invoked",
    "agent_liveness_observed",
    "agent_exited",
    "output_verified",
    "review_verdict_recorded",
    "evaluation_verdict_recorded",
    "retry_started",
    "escalation_triggered",
    "timeout_triggered",
    "manual_intervention_recorded",
    "turn_completed",
    "run_completed",
    "run_failed",
}
PARENT_RULES: dict[str, set[str]] = {
    "run_started": set(),
    "preflight_passed": {"run_started"},
    "turn_started": {"run_started", "turn_completed", "retry_started"},
    "prompt_rendered": {"turn_started"},
    "agent_invoked": {"prompt_rendered"},
    "agent_liveness_observed": {"agent_invoked"},
    "agent_exited": {"agent_invoked"},
    "output_verified": {"agent_exited"},
    "review_verdict_recorded": {"agent_exited"},
    "evaluation_verdict_recorded": {"agent_exited"},
    "retry_started": {"review_verdict_recorded", "evaluation_verdict_recorded"},
    "escalation_triggered": {"review_verdict_recorded", "evaluation_verdict_recorded"},
    "timeout_triggered": {"agent_invoked"},
    "manual_intervention_recorded": {"timeout_triggered", "agent_exited", "run_failed"},
    "turn_completed": {"review_verdict_recorded", "evaluation_verdict_recorded"},
    "run_completed": {"turn_completed"},
    "run_failed": {
        "timeout_triggered",
        "agent_exited",
        "output_verified",
        "review_verdict_recorded",
        "evaluation_verdict_recorded",
        "prompt_rendered",
        "preflight_passed",
    },
}

HEARTBEAT_PREFIX = "SAWMILL_HEARTBEAT: "
HEARTBEAT_FILE_PATTERN = re.compile(r"^(?P<step>.+)\.attempt(?P<attempt>\d+)\.log$")
STRUCTURED_HEARTBEAT_GLOB = "*.jsonl"
WORKER_HEARTBEAT_SUFFIX = ".worker.jsonl"
ORCHESTRATOR_HEARTBEAT_FILE = "orchestrator.jsonl"
WORKER_STALE_SECONDS = 300
ORCHESTRATOR_STALE_SECONDS = 120
INTERRUPTED_ORCHESTRATOR_STALE_SECONDS = 300


@dataclass
class ProjectionResult:
    status: dict[str, Any]
    events: list[dict[str, Any]]


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}-{uuid.uuid4().hex[:12]}"


def new_event_id() -> str:
    return uuid.uuid4().hex


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}: {exc}") from exc
            if not isinstance(event, dict):
                raise ValueError(f"Event on line {line_number} of {path} must be an object")
            events.append(event)
    return events


def init_run(run_dir: Path, metadata_file: Path) -> None:
    metadata = load_json(metadata_file)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(exist_ok=True)
    run_json_path = run_dir / "run.json"
    status_json_path = run_dir / "status.json"
    events_path = run_dir / "events.jsonl"
    (run_dir / "heartbeats").mkdir(exist_ok=True)
    with run_json_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
        handle.write("\n")
    initial_status = {
        "run_id": metadata["run_id"],
        "framework_id": metadata["framework_id"],
        "resumed_from_run_id": metadata.get("resumed_from_run_id", ""),
        "lineage_root_run_id": metadata.get("lineage_root_run_id", metadata["run_id"]),
        "current_turn": "",
        "current_step": "",
        "current_role": "",
        "current_backend": "",
        "current_attempt": 0,
        "state": "running",
        "governed_path_intact": True,
        "last_successful_event_id": "",
        "latest_failure_code": "none",
        "worker_observation": "unknown",
        "last_worker_observed_at": "",
        "last_worker_progress_at": "",
        "last_worker_phase": "",
        "last_worker_heartbeat_at": "",
        "last_orchestrator_phase": "",
        "last_orchestrator_heartbeat_at": "",
        "worker_stale": False,
        "orchestrator_stale": False,
        "interruption_reason": "",
    }
    with status_json_path.open("w", encoding="utf-8") as handle:
        json.dump(initial_status, handle, indent=2, sort_keys=True)
        handle.write("\n")
    events_path.touch(exist_ok=True)


def append_event(run_dir: Path, event: dict[str, Any]) -> None:
    if event["event_type"] not in EVENT_TYPES:
        raise ValueError(f"Unsupported event_type '{event['event_type']}'")
    events_path = run_dir / "events.jsonl"
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True))
        handle.write("\n")


def append_heartbeat(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True))
        handle.write("\n")


def load_heartbeat_records(run_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    heartbeats_dir = run_dir / "heartbeats"
    if not heartbeats_dir.exists():
        return records
    for heartbeat_path in sorted(heartbeats_dir.glob(STRUCTURED_HEARTBEAT_GLOB)):
        for line_number, raw in enumerate(heartbeat_path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {heartbeat_path}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Heartbeat on line {line_number} of {heartbeat_path} must be an object")
            record.setdefault("_path", str(heartbeat_path))
            records.append(record)
    return sorted(records, key=lambda record: (str(record.get("timestamp", "")), str(record.get("_path", ""))))


def latest_heartbeat(records: list[dict[str, Any]], source: str) -> dict[str, Any] | None:
    matches = [record for record in records if str(record.get("source", "")) == source]
    if not matches:
        return None
    return matches[-1]


def _parse_timestamp(timestamp: str) -> datetime | None:
    if not timestamp:
        return None
    try:
        return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def heartbeat_is_stale(timestamp: str, threshold_seconds: int, *, now: datetime | None = None) -> bool:
    parsed = _parse_timestamp(timestamp)
    if parsed is None:
        return False
    baseline = now or datetime.now(timezone.utc)
    return (baseline - parsed).total_seconds() > threshold_seconds


def validate_parent(
    event: dict[str, Any],
    event_index: dict[str, dict[str, Any]],
    event_positions: dict[str, int],
    current_position: int,
) -> None:
    event_type = event["event_type"]
    parent_id = event.get("causal_parent_event_id")
    allowed_parent_types = PARENT_RULES[event_type]
    if not allowed_parent_types:
        if parent_id:
            raise ValueError(f"Event {event['event_id']} ({event_type}) must not have a parent")
        return
    if not parent_id:
        raise ValueError(f"Event {event['event_id']} ({event_type}) is missing a causal parent")
    if parent_id not in event_index:
        raise ValueError(f"Event {event['event_id']} references missing parent {parent_id}")
    parent_event = event_index[parent_id]
    parent_position = event_positions[parent_id]
    if parent_position >= current_position:
        raise ValueError(
            f"Event {event['event_id']} must reference an earlier parent event in the same run"
        )
    parent_type = parent_event["event_type"]
    if parent_type not in allowed_parent_types:
        raise ValueError(
            f"Event {event['event_id']} ({event_type}) has illegal parent type {parent_type}"
        )
    if event_type == "run_failed":
        parent_outcome = str(parent_event.get("outcome", "")).lower()
        parent_failure_code = str(parent_event.get("failure_code") or "none").lower()
        if parent_type != "timeout_triggered" and parent_outcome not in {"fail", "failed", "failure", "error", "timeout"} and parent_failure_code == "none":
            raise ValueError(f"Event {event['event_id']} (run_failed) must parent a failure event")
    if event_type == "review_verdict_recorded" and parent_event.get("role") != "reviewer":
        raise ValueError(f"Event {event['event_id']} must parent a reviewer agent_exited event")
    if event_type == "evaluation_verdict_recorded" and parent_event.get("role") != "evaluator":
        raise ValueError(f"Event {event['event_id']} must parent an evaluator agent_exited event")
    if event_type == "agent_liveness_observed" and parent_type != "agent_invoked":
        raise ValueError(f"Event {event['event_id']} must parent an agent_invoked event")
    if event_type == "manual_intervention_recorded":
        failure_code = parent_event.get("failure_code") or "none"
        if parent_type != "timeout_triggered" and failure_code == "none" and parent_type != "run_failed":
            raise ValueError(f"Event {event['event_id']} must parent a timeout or failure event")


def is_terminal_state(status: dict[str, Any]) -> bool:
    return status["state"] in TERMINAL_STATES


def apply_event(status: dict[str, Any], event: dict[str, Any], operator_mode: str) -> None:
    if is_terminal_state(status):
        raise ValueError(
            f"Illegal transition: terminal state {status['state']} cannot accept event {event['event_id']}"
        )
    status["current_turn"] = event["turn"]
    status["current_step"] = event["step"]
    status["current_role"] = event["role"]
    status["current_backend"] = event["backend"]
    status["current_attempt"] = event["attempt"]
    outcome = str(event.get("outcome", "")).lower()
    failure_code = event.get("failure_code") or "none"
    if failure_code != "none":
        status["latest_failure_code"] = failure_code
    if event["event_type"] == "run_started":
        status["state"] = "running"
        status["governed_path_intact"] = True
        status["worker_observation"] = "unknown"
    elif event["event_type"] == "retry_started":
        status["state"] = "retrying"
        status["worker_observation"] = "unknown"
    elif event["event_type"] == "escalation_triggered":
        status["state"] = "escalated"
    elif event["event_type"] == "run_failed":
        status["state"] = "failed"
    elif event["event_type"] == "manual_intervention_recorded":
        status["governed_path_intact"] = False
    elif event["event_type"] == "agent_invoked":
        status["worker_observation"] = "alive"
        status["last_worker_observed_at"] = event["timestamp"]
    elif event["event_type"] == "agent_liveness_observed":
        status["worker_observation"] = outcome
        status["last_worker_observed_at"] = event["timestamp"]
        if outcome == "progressing":
            status["last_worker_progress_at"] = event["timestamp"]
    elif event["event_type"] in {"agent_exited", "timeout_triggered"}:
        status["worker_observation"] = "exited"
        status["last_worker_observed_at"] = event["timestamp"]
    elif event["event_type"] == "run_completed":
        status["state"] = "passed"
        if not status["governed_path_intact"] and operator_mode != "manual_intervention_allowed":
            status["state"] = "invalidated"
    else:
        if status["state"] == "retrying" and event["event_type"] not in {"prompt_rendered", "agent_invoked", "agent_exited", "output_verified"}:
            status["state"] = "running"
    if event["event_type"] == "run_completed" and outcome not in {"pass", "passed", "success"}:
        raise ValueError(f"run_completed event {event['event_id']} must have a success outcome")
    if event["event_type"] == "run_failed" and outcome not in {"fail", "failed", "failure"}:
        raise ValueError(f"run_failed event {event['event_id']} must have a failure outcome")
    if event["event_type"] not in {"timeout_triggered", "run_failed", "escalation_triggered"} and outcome not in {"fail", "failed", "failure", "error", "timeout", "retry", "escalate", "stalled", "transport_blocked"}:
        status["last_successful_event_id"] = event["event_id"]
    if status["state"] not in ALLOWED_STATES:
        raise ValueError(f"Illegal projected state {status['state']}")


def project_status(run_dir: Path) -> ProjectionResult:
    run_json = load_json(run_dir / "run.json")
    events = load_events(run_dir / "events.jsonl")
    run_id = run_json["run_id"]
    operator_mode = run_json["operator_mode"]
    if operator_mode not in {"governed", "interactive", "manual_intervention_allowed"}:
        raise ValueError(f"Unsupported operator_mode '{operator_mode}'")
    ordered = sorted(enumerate(events), key=lambda pair: (pair[1]["timestamp"], pair[0]))
    seen_ids: set[str] = set()
    event_index: dict[str, dict[str, Any]] = {}
    event_positions: dict[str, int] = {}
    status = {
        "run_id": run_id,
        "framework_id": run_json["framework_id"],
        "resumed_from_run_id": run_json.get("resumed_from_run_id", ""),
        "lineage_root_run_id": run_json.get("lineage_root_run_id", run_id),
        "current_turn": "",
        "current_step": "",
        "current_role": "",
        "current_backend": "",
        "current_attempt": 0,
        "state": "running",
        "governed_path_intact": True,
        "last_successful_event_id": "",
        "latest_failure_code": "none",
        "worker_observation": "unknown",
        "last_worker_observed_at": "",
        "last_worker_progress_at": "",
        "interruption_reason": "",
    }
    for current_position, (_, event) in enumerate(ordered):
        event_id = event.get("event_id")
        if not event_id:
            raise ValueError("Every event must have event_id")
        if event_id in seen_ids:
            raise ValueError(f"Duplicate event_id '{event_id}'")
        seen_ids.add(event_id)
        if event.get("run_id") != run_id:
            raise ValueError(f"Event {event_id} run_id does not match run directory")
        event_type = event.get("event_type")
        if event_type not in EVENT_TYPES:
            raise ValueError(f"Unsupported event_type '{event_type}' in event {event_id}")
        validate_parent(event, event_index, event_positions, current_position)
        event_index[event_id] = event
        event_positions[event_id] = current_position
        apply_event(status, event, operator_mode)
    heartbeat_records = load_heartbeat_records(run_dir)
    latest_worker = latest_heartbeat(heartbeat_records, "worker")
    latest_orchestrator = latest_heartbeat(heartbeat_records, "orchestrator")
    if latest_worker:
        status["last_worker_phase"] = str(latest_worker.get("phase", ""))
        status["last_worker_heartbeat_at"] = str(latest_worker.get("timestamp", ""))
        if str(latest_worker.get("kind", "")) == "progress":
            status["last_worker_progress_at"] = str(latest_worker.get("timestamp", "")) or status["last_worker_progress_at"]
    if latest_orchestrator:
        status["last_orchestrator_phase"] = str(latest_orchestrator.get("phase", ""))
        status["last_orchestrator_heartbeat_at"] = str(latest_orchestrator.get("timestamp", ""))
    status["worker_stale"] = heartbeat_is_stale(str(status.get("last_worker_heartbeat_at", "")), WORKER_STALE_SECONDS)
    status["orchestrator_stale"] = heartbeat_is_stale(
        str(status.get("last_orchestrator_heartbeat_at", "")),
        ORCHESTRATOR_STALE_SECONDS,
    )
    if status["state"] in {"running", "retrying"} and heartbeat_is_stale(
        str(status.get("last_orchestrator_heartbeat_at", "")),
        INTERRUPTED_ORCHESTRATOR_STALE_SECONDS,
    ):
        if status.get("worker_observation") == "exited":
            status["state"] = "interrupted"
            status["interruption_reason"] = "worker_exited_without_completion"
        elif status.get("worker_stale"):
            status["state"] = "interrupted"
            status["interruption_reason"] = "orchestrator_and_worker_stale"
        else:
            status["state"] = "interrupted"
            status["interruption_reason"] = "orchestrator_stale"
    status["governed_path_intact"] = bool(status["governed_path_intact"])
    return ProjectionResult(status=status, events=[event for _, event in ordered])


def write_status(run_dir: Path, result: ProjectionResult) -> None:
    status_path = run_dir / "status.json"
    with status_path.open("w", encoding="utf-8") as handle:
        json.dump(result.status, handle, indent=2, sort_keys=True)
        handle.write("\n")


def current_status_field(status_path: Path, field: str) -> str:
    if not status_path.exists():
        raise ValueError(f"Missing JSON file: {status_path}")
    data = load_json(status_path)
    value = data.get(field, "")
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def build_run_metadata(
    *,
    run_id: str,
    framework_id: str,
    started_at: str,
    requested_entry_path: str,
    from_turn: str,
    retry_budget: int,
    role_backend_resolution: dict[str, str],
    model_policies: dict[str, str],
    prompt_contract_versions: dict[str, str],
    role_file_hashes: dict[str, str],
    prompt_file_hashes: dict[str, str],
    artifact_registry_version_hash: str,
    graph_version: str,
    operator_mode: str,
    role_runtime_config: dict[str, dict[str, str]] | None = None,
    resumed_from_run_id: str = "",
    lineage_root_run_id: str = "",
    launch_manifest_path: str = "",
    launch_manifest_hash: str = "",
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "framework_id": framework_id,
        "resumed_from_run_id": resumed_from_run_id,
        "lineage_root_run_id": lineage_root_run_id or run_id,
        "started_at": started_at,
        "requested_entry_path": requested_entry_path,
        "from_turn": from_turn,
        "retry_budget": retry_budget,
        "role_backend_resolution": role_backend_resolution,
        "model_policies": model_policies,
        "prompt_contract_versions": prompt_contract_versions,
        "role_file_hashes": role_file_hashes,
        "prompt_file_hashes": prompt_file_hashes,
        "artifact_registry_version_hash": artifact_registry_version_hash,
        "graph_version": graph_version,
        "operator_mode": operator_mode,
        "role_runtime_config": role_runtime_config or {},
        "launch_manifest_path": launch_manifest_path,
        "launch_manifest_hash": launch_manifest_hash,
    }


def role_index_by_step_attempt(events: list[dict]) -> dict[tuple[str, int], str]:
    index: dict[tuple[str, int], str] = {}
    for event in events:
        if event.get("event_type") != "agent_invoked":
            continue
        role = event.get("role", "")
        attempt = int(event.get("attempt", 0))
        step = event.get("step", "")
        if step:
            index[(step, attempt)] = role
    return index


def fallback_role(step: str) -> str:
    step_role_map = {
        "turn_a_spec": "spec-agent",
        "turn_b_plan": "spec-agent",
        "turn_c_holdout": "holdout-agent",
        "turn_d_13q": "builder",
        "turn_d_review": "reviewer",
        "turn_d_build": "builder",
        "turn_e_eval": "evaluator",
    }
    return step_role_map.get(step, "unknown")


def parse_sidecar_filename(heartbeat_path: Path) -> tuple[str, int | None]:
    match = HEARTBEAT_FILE_PATTERN.match(heartbeat_path.name)
    if not match:
        return "unknown", None
    return match.group("step"), int(match.group("attempt"))


def worker_heartbeat_path(run_dir: Path, step: str, attempt: int) -> Path:
    return run_dir / "heartbeats" / f"{step}.attempt{attempt}{WORKER_HEARTBEAT_SUFFIX}"


def orchestrator_heartbeat_path(run_dir: Path) -> Path:
    return run_dir / "heartbeats" / ORCHESTRATOR_HEARTBEAT_FILE


def extract_heartbeats(run_dir: Path) -> list[dict]:
    events = load_events(run_dir / "events.jsonl")
    role_index = role_index_by_step_attempt(events)
    records: list[dict] = []
    for heartbeat_path in sorted((run_dir / "heartbeats").glob("*.log")):
        relative_source = heartbeat_path.relative_to(run_dir)
        step, attempt = parse_sidecar_filename(heartbeat_path)
        role = role_index.get((step, attempt if attempt is not None else 0), fallback_role(step))
        for line in heartbeat_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith(HEARTBEAT_PREFIX):
                continue
            records.append(
                {
                    "source": str(relative_source),
                    "type": "agent_heartbeat",
                    "role": role,
                    "attempt": attempt,
                    "message": line[len(HEARTBEAT_PREFIX):].strip(),
                }
            )
    return records


def main_project_run_status(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage Sawmill run harness artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init-run", help="Initialize a run directory and run.json")
    init_parser.add_argument("--run-dir", required=True)
    init_parser.add_argument("--metadata-file", required=True)
    append_parser = subparsers.add_parser("append-event", help="Append one event to events.jsonl")
    append_parser.add_argument("--run-dir", required=True)
    append_parser.add_argument("--event-id", required=True)
    append_parser.add_argument("--run-id", required=True)
    append_parser.add_argument("--timestamp", required=True)
    append_parser.add_argument("--turn", required=True)
    append_parser.add_argument("--step", required=True)
    append_parser.add_argument("--role", required=True)
    append_parser.add_argument("--backend", required=True)
    append_parser.add_argument("--attempt", type=int, required=True)
    append_parser.add_argument("--event-type", required=True)
    append_parser.add_argument("--outcome", required=True)
    append_parser.add_argument("--failure-code", required=True)
    append_parser.add_argument("--causal-parent-event-id", default="")
    append_parser.add_argument("--summary", required=True)
    append_parser.add_argument("--evidence-ref", action="append", default=[])
    append_parser.add_argument("--contract-ref", action="append", default=[])
    project_parser = subparsers.add_parser("project-status", help="Project status.json from events.jsonl")
    project_parser.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)
    run_dir = Path(args.run_dir)
    try:
        if args.command == "init-run":
            init_run(run_dir, Path(args.metadata_file))
        elif args.command == "append-event":
            append_event(
                run_dir,
                {
                    "event_id": args.event_id,
                    "run_id": args.run_id,
                    "timestamp": args.timestamp,
                    "turn": args.turn,
                    "step": args.step,
                    "role": args.role,
                    "backend": args.backend,
                    "attempt": args.attempt,
                    "event_type": args.event_type,
                    "outcome": args.outcome,
                    "failure_code": args.failure_code,
                    "causal_parent_event_id": args.causal_parent_event_id or None,
                    "evidence_refs": args.evidence_ref,
                    "contract_refs": args.contract_ref,
                    "summary": args.summary,
                },
            )
        elif args.command == "project-status":
            write_status(run_dir, project_status(run_dir))
        else:  # pragma: no cover
            raise ValueError(f"Unsupported command {args.command}")
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


def main_extract_heartbeats(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract derived heartbeat records from a Sawmill run")
    parser.add_argument("--run-dir", required=True, help="Path to sawmill/<FMWK>/runs/<run-id>")
    args = parser.parse_args(argv)
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: missing run dir: {run_dir}", file=sys.stderr)
        return 1
    for record in extract_heartbeats(run_dir):
        print(json.dumps(record, sort_keys=True))
    return 0
