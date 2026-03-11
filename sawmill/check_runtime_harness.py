#!/usr/bin/env python3
"""Acceptance checks for the Sawmill runtime harness."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROJECTOR = ROOT / "sawmill" / "project_run_status.py"
EVIDENCE_VALIDATOR = ROOT / "sawmill" / "validate_evidence_artifacts.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Sawmill runtime harness invariants")
    parser.add_argument("--run-dir", help="Run directory to validate")
    parser.add_argument("--self-test", action="store_true", help="Run synthetic harness self-test")
    args = parser.parse_args()
    if not args.self_test and not args.run_dir:
        parser.error("either --run-dir or --self-test is required")
    return args


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if line:
                events.append(json.loads(line))
    return events


def ordered_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = list(enumerate(events))
    indexed.sort(key=lambda pair: (pair[1]["timestamp"], pair[0]))
    return [event for _, event in indexed]


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check_event_order(run_dir: Path) -> None:
    ordered = ordered_events(load_events(run_dir / "events.jsonl"))
    positions = {event["event_id"]: idx for idx, event in enumerate(ordered)}
    index = {event["event_id"]: event for event in ordered}

    for event in ordered:
        parent_id = event.get("causal_parent_event_id")
        if parent_id:
            assert_condition(parent_id in index, f"{run_dir}: missing parent event {parent_id}")
            assert_condition(
                positions[parent_id] < positions[event["event_id"]],
                f"{run_dir}: parent {parent_id} is not earlier than child {event['event_id']}",
            )

        event_type = event["event_type"]
        if event_type == "agent_exited":
            parent = index[event["causal_parent_event_id"]]
            assert_condition(parent["event_type"] == "agent_invoked", f"{run_dir}: agent_exited must parent agent_invoked")
        elif event_type == "timeout_triggered":
            parent = index[event["causal_parent_event_id"]]
            assert_condition(parent["event_type"] == "agent_invoked", f"{run_dir}: timeout_triggered must parent agent_invoked")
        elif event_type == "output_verified":
            parent = index[event["causal_parent_event_id"]]
            assert_condition(parent["event_type"] == "agent_exited", f"{run_dir}: output_verified must parent agent_exited")


def rebuild_status(run_dir: Path) -> None:
    status_path = run_dir / "status.json"
    before = load_json(status_path)
    backup = run_dir / "status.json.bak"
    shutil.copy2(status_path, backup)
    status_path.unlink()
    subprocess.run(
        ["python3", str(PROJECTOR), "project-status", "--run-dir", str(run_dir)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    after = load_json(status_path)
    backup.unlink(missing_ok=True)
    assert_condition(before == after, f"{run_dir}: status.json rebuild changed projected state")


def check_evidence_isolation(run_dir: Path) -> None:
    run_json = load_json(run_dir / "run.json")
    run_id = run_json["run_id"]
    framework_id = run_json["framework_id"]
    base_dir = ROOT / "sawmill" / framework_id
    holdout_dir = ROOT / ".holdouts" / framework_id
    staging_dir = ROOT / "staging" / framework_id

    cases: list[tuple[str, Path, list[str]]] = []
    builder = base_dir / "builder_evidence.json"
    reviewer = base_dir / "reviewer_evidence.json"
    evaluator = base_dir / "evaluator_evidence.json"
    if builder.exists():
        attempt = str(load_json(builder)["attempt"])
        cases.append(
            (
                "builder",
                builder,
                [
                    "--handoff",
                    str(base_dir / "BUILDER_HANDOFF.md"),
                    "--q13-answers",
                    str(base_dir / "13Q_ANSWERS.md"),
                    "--results",
                    str(base_dir / "RESULTS.md"),
                ],
            )
        )
    if reviewer.exists():
        attempt = str(load_json(reviewer)["attempt"])
        cases.append(
            (
                "reviewer",
                reviewer,
                [
                    "--q13-answers",
                    str(base_dir / "13Q_ANSWERS.md"),
                ],
            )
        )
    if evaluator.exists():
        attempt = str(load_json(evaluator)["attempt"])
        cases.append(
            (
                "evaluator",
                evaluator,
                [
                    "--holdouts",
                    str(holdout_dir / "D9_HOLDOUT_SCENARIOS.md"),
                    "--staging-root",
                    str(staging_dir),
                ],
            )
        )

    for kind, artifact_path, extra_args in cases:
        attempt_value = str(load_json(artifact_path)["attempt"])
        subprocess.run(
            [
                "python3",
                str(EVIDENCE_VALIDATOR),
                "--kind",
                kind,
                "--artifact",
                str(artifact_path),
                "--run-id",
                run_id,
                "--attempt",
                attempt_value,
                *extra_args,
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        mismatch = subprocess.run(
            [
                "python3",
                str(EVIDENCE_VALIDATOR),
                "--kind",
                kind,
                "--artifact",
                str(artifact_path),
                "--run-id",
                f"{run_id}-WRONG",
                "--attempt",
                attempt_value,
                *extra_args,
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert_condition(mismatch.returncode != 0, f"{run_dir}: {kind} evidence accepted wrong run_id")


def validate_run_dir(run_dir: Path) -> None:
    required = ["run.json", "status.json", "events.jsonl", "logs"]
    for name in required:
        assert_condition((run_dir / name).exists(), f"{run_dir}: missing required harness artifact {name}")
    check_event_order(run_dir)
    rebuild_status(run_dir)
    check_evidence_isolation(run_dir)


def append_event(run_dir: Path, **kwargs: str | int) -> None:
    cmd = [
        "python3",
        str(PROJECTOR),
        "append-event",
        "--run-dir",
        str(run_dir),
        "--event-id",
        str(kwargs["event_id"]),
        "--run-id",
        str(kwargs["run_id"]),
        "--timestamp",
        str(kwargs["timestamp"]),
        "--turn",
        str(kwargs["turn"]),
        "--step",
        str(kwargs["step"]),
        "--role",
        str(kwargs["role"]),
        "--backend",
        str(kwargs["backend"]),
        "--attempt",
        str(kwargs["attempt"]),
        "--event-type",
        str(kwargs["event_type"]),
        "--outcome",
        str(kwargs["outcome"]),
        "--failure-code",
        str(kwargs["failure_code"]),
        "--summary",
        str(kwargs["summary"]),
    ]
    parent = kwargs.get("causal_parent_event_id")
    if parent:
        cmd.extend(["--causal-parent-event-id", str(parent)])
    subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="sawmill-harness-selftest.") as tmp:
        run_dir = Path(tmp) / "run"
        metadata = {
            "run_id": "self-test-run",
            "framework_id": "FMWK-TEST",
            "started_at": "2026-03-10T00:00:00Z",
            "requested_entry_path": "./sawmill/run.sh",
            "from_turn": "A",
            "retry_budget": 3,
            "role_backend_resolution": {},
            "model_policies": {},
            "prompt_contract_versions": {},
            "role_file_hashes": {},
            "prompt_file_hashes": {},
            "artifact_registry_version_hash": "selftest",
            "graph_version": "none",
            "operator_mode": "governed",
        }
        meta_path = Path(tmp) / "metadata.json"
        meta_path.write_text(json.dumps(metadata), encoding="utf-8")
        subprocess.run(
            ["python3", str(PROJECTOR), "init-run", "--run-dir", str(run_dir), "--metadata-file", str(meta_path)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        append_event(
            run_dir,
            event_id="e1",
            run_id="self-test-run",
            timestamp="2026-03-10T00:00:00Z",
            turn="orchestrator",
            step="run",
            role="orchestrator",
            backend="runtime",
            attempt=0,
            event_type="run_started",
            outcome="started",
            failure_code="none",
            summary="run started",
        )
        append_event(
            run_dir,
            event_id="e2",
            run_id="self-test-run",
            timestamp="2026-03-10T00:00:01Z",
            turn="orchestrator",
            step="preflight",
            role="orchestrator",
            backend="runtime",
            attempt=0,
            event_type="preflight_passed",
            outcome="passed",
            failure_code="none",
            causal_parent_event_id="e1",
            summary="preflight",
        )
        append_event(
            run_dir,
            event_id="e3",
            run_id="self-test-run",
            timestamp="2026-03-10T00:00:02Z",
            turn="D",
            step="turn_d_review",
            role="reviewer",
            backend="claude",
            attempt=1,
            event_type="turn_started",
            outcome="started",
            failure_code="none",
            causal_parent_event_id="e1",
            summary="turn d",
        )
        append_event(
            run_dir,
            event_id="e4",
            run_id="self-test-run",
            timestamp="2026-03-10T00:00:03Z",
            turn="D",
            step="turn_d_review",
            role="reviewer",
            backend="claude",
            attempt=1,
            event_type="prompt_rendered",
            outcome="rendered",
            failure_code="none",
            causal_parent_event_id="e3",
            summary="prompt",
        )
        append_event(
            run_dir,
            event_id="e5",
            run_id="self-test-run",
            timestamp="2026-03-10T00:00:04Z",
            turn="D",
            step="turn_d_review",
            role="reviewer",
            backend="claude",
            attempt=1,
            event_type="agent_invoked",
            outcome="invoked",
            failure_code="none",
            causal_parent_event_id="e4",
            summary="invoked",
        )
        append_event(
            run_dir,
            event_id="e6",
            run_id="self-test-run",
            timestamp="2026-03-10T00:00:05Z",
            turn="D",
            step="turn_d_review",
            role="reviewer",
            backend="claude",
            attempt=1,
            event_type="timeout_triggered",
            outcome="timeout",
            failure_code="AGENT_TIMEOUT",
            causal_parent_event_id="e5",
            summary="timeout",
        )
        append_event(
            run_dir,
            event_id="e7",
            run_id="self-test-run",
            timestamp="2026-03-10T00:00:06Z",
            turn="D",
            step="manual_intervention",
            role="human",
            backend="manual",
            attempt=1,
            event_type="manual_intervention_recorded",
            outcome="recorded",
            failure_code="MANUAL_INTERVENTION",
            causal_parent_event_id="e6",
            summary="manual",
        )
        append_event(
            run_dir,
            event_id="e8",
            run_id="self-test-run",
            timestamp="2026-03-10T00:00:07Z",
            turn="E",
            step="turn_e_eval",
            role="evaluator",
            backend="claude",
            attempt=1,
            event_type="agent_exited",
            outcome="succeeded",
            failure_code="none",
            causal_parent_event_id="e5",
            summary="evaluator exited",
        )
        append_event(
            run_dir,
            event_id="e9",
            run_id="self-test-run",
            timestamp="2026-03-10T00:00:08Z",
            turn="E",
            step="turn_e_eval",
            role="evaluator",
            backend="claude",
            attempt=1,
            event_type="evaluation_verdict_recorded",
            outcome="pass",
            failure_code="none",
            causal_parent_event_id="e8",
            summary="eval pass",
        )
        append_event(
            run_dir,
            event_id="e10",
            run_id="self-test-run",
            timestamp="2026-03-10T00:00:09Z",
            turn="E",
            step="turn_e_eval",
            role="evaluator",
            backend="claude",
            attempt=1,
            event_type="turn_completed",
            outcome="completed",
            failure_code="none",
            causal_parent_event_id="e9",
            summary="completed",
        )
        append_event(
            run_dir,
            event_id="e11",
            run_id="self-test-run",
            timestamp="2026-03-10T00:00:10Z",
            turn="orchestrator",
            step="run",
            role="orchestrator",
            backend="runtime",
            attempt=1,
            event_type="run_completed",
            outcome="passed",
            failure_code="none",
            causal_parent_event_id="e10",
            summary="done",
        )
        subprocess.run(
            ["python3", str(PROJECTOR), "project-status", "--run-dir", str(run_dir)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        status = load_json(run_dir / "status.json")
        assert_condition(status["state"] == "invalidated", "self-test did not coerce manual-intervention PASS to invalidated")
        print(f"PASS: harness self-test ({run_dir})")


def main() -> int:
    args = parse_args()
    try:
        if args.self_test:
            self_test()
        else:
            validate_run_dir(Path(args.run_dir))
            print(f"PASS: runtime harness valid ({args.run_dir})")
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
