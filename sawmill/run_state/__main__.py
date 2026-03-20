"""CLI entrypoint for sawmill.run_state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from sawmill.evidence import parse_evaluation_verdict
from sawmill.registry import build_stage_maps, load_artifact_registry

from ._core import (
    append_event,
    build_run_metadata,
    current_status_field,
    iso_timestamp,
    load_json,
    main_extract_heartbeats,
    main_project_run_status,
    new_event_id,
    new_run_id,
    project_status,
    write_status,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_metadata_from_env(output: Path) -> None:
    role_backend_resolution = {
        "spec-agent": os.environ["SPEC_AGENT"],
        "holdout-agent": os.environ["HOLDOUT_AGENT"],
        "builder": os.environ["BUILD_AGENT"],
        "reviewer": os.environ["REVIEW_AGENT"],
        "evaluator": os.environ["EVAL_AGENT"],
        "auditor": os.environ["AUDIT_AGENT"],
    }
    model_policies = {
        "spec-agent": os.environ["SPEC_MODEL_POLICY"],
        "holdout-agent": os.environ["HOLDOUT_MODEL_POLICY"],
        "builder": os.environ["BUILD_MODEL_POLICY"],
        "reviewer": os.environ["REVIEW_MODEL_POLICY"],
        "evaluator": os.environ["EVAL_MODEL_POLICY"],
        "auditor": os.environ["AUDIT_MODEL_POLICY"],
    }
    prompt_contract_versions = {
        "builder_prompt_contract": os.environ["BUILDER_PROMPT_CONTRACT_VERSION"],
        "reviewer_prompt_contract": os.environ["REVIEWER_PROMPT_CONTRACT_VERSION"],
    }
    role_file_hashes = {}
    for key in (
        "SPEC_ROLE_FILE",
        "HOLDOUT_ROLE_FILE",
        "BUILD_ROLE_FILE",
        "REVIEW_ROLE_FILE",
        "EVAL_ROLE_FILE",
        "AUDIT_ROLE_FILE",
    ):
        path = Path(os.environ[key])
        role_file_hashes[path.as_posix()] = _sha256_file(path)
    prompt_file_hashes = {}
    for prompt_key in os.environ["ALL_PROMPT_KEYS"].split():
        env_key = f"PROMPT_{prompt_key.upper()}_PROMPT_FILE"
        path = Path(os.environ[env_key])
        prompt_file_hashes[path.as_posix()] = _sha256_file(path)
    metadata = build_run_metadata(
        run_id=os.environ["RUN_ID"],
        framework_id=os.environ["FMWK"],
        started_at=os.environ["RUN_STARTED_AT"],
        requested_entry_path="./sawmill/run.sh",
        from_turn=os.environ["FROM_TURN"],
        retry_budget=int(os.environ["MAX_ATTEMPTS"]),
        role_backend_resolution=role_backend_resolution,
        model_policies=model_policies,
        prompt_contract_versions=prompt_contract_versions,
        role_file_hashes=role_file_hashes,
        prompt_file_hashes=prompt_file_hashes,
        artifact_registry_version_hash=_sha256_file(Path(os.environ["ARTIFACT_REGISTRY"])),
        graph_version="none",
        operator_mode=os.environ["OPERATOR_MODE"],
    )
    output.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _emit_event_and_project(args: argparse.Namespace) -> int:
    event_id = args.event_id or new_event_id()
    event = {
        "event_id": event_id,
        "run_id": args.run_id,
        "timestamp": args.timestamp or iso_timestamp(),
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
    }
    run_dir = Path(args.run_dir)
    append_event(run_dir, event)
    write_status(run_dir, project_status(run_dir))
    print(event_id)
    return 0


def _emit_liveness(args: argparse.Namespace) -> int:
    liveness_path = Path(args.liveness_path)
    if not liveness_path.exists():
        return 0
    state_file = Path(args.state_file)
    seen = 0
    if state_file.exists():
        raw = state_file.read_text(encoding="utf-8").strip()
        if raw:
            seen = int(raw)
    lines = [line for line in liveness_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    new_lines = lines[seen:]
    if not new_lines:
        return 0
    run_dir = Path(args.run_dir)
    for raw in new_lines:
        record = json.loads(raw)
        append_event(
            run_dir,
            {
                "event_id": new_event_id(),
                "run_id": record["run_id"],
                "timestamp": record["timestamp"],
                "turn": args.turn,
                "step": args.step,
                "role": args.role,
                "backend": args.backend,
                "attempt": args.attempt,
                "event_type": "agent_liveness_observed",
                "outcome": record["observation"],
                "failure_code": "none",
                "causal_parent_event_id": args.parent_id,
                "evidence_refs": [str(liveness_path)],
                "contract_refs": [],
                "summary": f"{record['observation']} observed from {record['source']}",
            },
        )
    write_status(run_dir, project_status(run_dir))
    state_file.write_text(str(len(lines)), encoding="utf-8")
    return 0


def _artifact_path(template: str, framework_id: str) -> Path:
    return Path(template.replace("{FMWK}", framework_id))


def _artifact_exists(kind: str, path: Path) -> bool:
    return path.is_dir() if kind == "dir" else path.is_file()


def _update_status_page(args: argparse.Namespace) -> int:
    status_page = Path(args.status_page)
    status_page.parent.mkdir(parents=True, exist_ok=True)
    if not status_page.exists():
        status_page.write_text(
            "<!-- sawmill:auto-status -->\n# Pending framework status\n\n**Status:** Not started\n",
            encoding="utf-8",
        )
    if "<!-- sawmill:auto-status -->" not in status_page.read_text(encoding="utf-8").splitlines()[0]:
        return 0

    summary = "Not started"
    runtime_state = "running"
    governed_path = "true"
    if args.status_json and Path(args.status_json).exists():
        runtime_state = current_status_field(Path(args.status_json), "state") or "running"
        governed_path = current_status_field(Path(args.status_json), "governed_path_intact") or "true"

    stage_labels = {
        "A": "PENDING",
        "B": "PENDING",
        "C": "PENDING",
        "D": "PENDING",
        "E": "PENDING",
    }
    registry = load_artifact_registry(Path(args.artifact_registry))
    _, stage_required, _ = build_stage_maps(registry)
    artifacts = registry["artifacts"]

    for stage in ("A", "B", "C", "D", "E"):
        required_ids = stage_required[stage]
        complete = all(
            _artifact_exists(
                artifacts[artifact_id]["artifact_kind"],
                _artifact_path(artifacts[artifact_id]["path_template"], args.framework_id),
            )
            for artifact_id in required_ids
        )
        if stage == "E" and complete:
            try:
                verdict = parse_evaluation_verdict(Path(args.evaluation_report))
            except ValueError:
                complete = False
            else:
                stage_labels[stage] = verdict
                summary = "Evaluation PASS" if verdict == "PASS" else "Evaluation FAIL"
                continue
        if complete:
            stage_labels[stage] = "DONE"
            summary = {
                "A": "Spec complete",
                "B": "Plan complete",
                "C": "Holdouts complete",
                "D": "Build complete",
            }.get(stage, summary)

    if runtime_state == "invalidated":
        summary = "Run invalidated"
    elif runtime_state == "failed":
        summary = "Run failed"
    elif runtime_state == "escalated":
        summary = "Run escalated"
    elif runtime_state == "retrying":
        summary = "Retry in progress"
    elif runtime_state == "passed":
        summary = "Evaluation PASS"

    status_page.write_text(
        "\n".join(
            [
                "<!-- sawmill:auto-status -->",
                f"# {args.framework_id} — Build Status",
                "",
                f"**Status:** {summary}",
                f"**Run ID:** {args.run_id}",
                f"**Runtime State:** {runtime_state}",
                f"**Governed Path Intact:** {governed_path}",
                "",
                "---",
                "",
                "## Stage Completion",
                "",
                "| Stage | Status |",
                "|-------|--------|",
                f"| Turn A (Spec) | {stage_labels['A']} |",
                f"| Turn B (Plan) | {stage_labels['B']} |",
                f"| Turn C (Holdout) | {stage_labels['C']} |",
                f"| Turn D (Build) | {stage_labels['D']} |",
                f"| Turn E (Eval) | {stage_labels['E']} |",
                "",
                "---",
                "",
                f"*Updated by sawmill.run_state at {iso_timestamp()}*",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        import sys

        argv = sys.argv[1:]
    if argv and argv[0] == "heartbeats":
        return main_extract_heartbeats(argv[1:])
    if argv and argv[0] == "new-run-id":
        print(new_run_id())
        return 0
    if argv and argv[0] == "new-event-id":
        print(new_event_id())
        return 0
    if argv and argv[0] == "iso-timestamp":
        print(iso_timestamp())
        return 0
    if argv and argv[0] == "status-field":
        parser = argparse.ArgumentParser()
        parser.add_argument("--status-json", required=True)
        parser.add_argument("--field", required=True)
        args = parser.parse_args(argv[1:])
        print(current_status_field(Path(args.status_json), args.field))
        return 0
    if argv and argv[0] == "build-metadata":
        parser = argparse.ArgumentParser()
        parser.add_argument("--output", required=True)
        args = parser.parse_args(argv[1:])
        _build_metadata_from_env(Path(args.output))
        return 0
    if argv and argv[0] == "emit":
        parser = argparse.ArgumentParser()
        parser.add_argument("--run-dir", required=True)
        parser.add_argument("--event-id")
        parser.add_argument("--run-id", required=True)
        parser.add_argument("--timestamp")
        parser.add_argument("--turn", required=True)
        parser.add_argument("--step", required=True)
        parser.add_argument("--role", required=True)
        parser.add_argument("--backend", required=True)
        parser.add_argument("--attempt", required=True, type=int)
        parser.add_argument("--event-type", required=True)
        parser.add_argument("--outcome", required=True)
        parser.add_argument("--failure-code", required=True)
        parser.add_argument("--causal-parent-event-id", default="")
        parser.add_argument("--summary", required=True)
        parser.add_argument("--evidence-ref", action="append", default=[])
        parser.add_argument("--contract-ref", action="append", default=[])
        return _emit_event_and_project(parser.parse_args(argv[1:]))
    if argv and argv[0] == "emit-liveness":
        parser = argparse.ArgumentParser()
        parser.add_argument("--liveness-path", required=True)
        parser.add_argument("--run-dir", required=True)
        parser.add_argument("--parent-id", required=True)
        parser.add_argument("--turn", required=True)
        parser.add_argument("--step", required=True)
        parser.add_argument("--role", required=True)
        parser.add_argument("--backend", required=True)
        parser.add_argument("--attempt", required=True, type=int)
        parser.add_argument("--state-file", required=True)
        return _emit_liveness(parser.parse_args(argv[1:]))
    if argv and argv[0] == "update-status":
        parser = argparse.ArgumentParser()
        parser.add_argument("--framework-id", required=True)
        parser.add_argument("--run-id", required=True)
        parser.add_argument("--status-page", required=True)
        parser.add_argument("--status-json", required=True)
        parser.add_argument("--artifact-registry", required=True)
        parser.add_argument("--evaluation-report", required=True)
        return _update_status_page(parser.parse_args(argv[1:]))
    alias_map = {
        "init-run": "init-run",
        "append-event": "append-event",
        "project-status": "project-status",
    }
    if argv and argv[0] in alias_map:
        return main_project_run_status(argv)
    import sys

    print(
        "FAIL: use one of: init-run, append-event, project-status, heartbeats, new-run-id, new-event-id, iso-timestamp, status-field, build-metadata, emit, emit-liveness",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
