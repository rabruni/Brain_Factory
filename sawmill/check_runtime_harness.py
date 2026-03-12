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


def check_invocation_artifacts(run_dir: Path) -> None:
    invocations_dir = run_dir / "invocations"
    assert_condition(invocations_dir.exists(), f"{run_dir}: missing invocations directory")

    result_files = sorted(invocations_dir.glob("*.result.json"))
    if not result_files:
        return

    required_suffixes = (".payload.txt", ".meta.json", ".liveness.jsonl", ".result.json")
    for result_file in result_files:
        prefix = result_file.as_posix()[: -len(".result.json")]
        for suffix in required_suffixes:
            sibling = Path(prefix + suffix)
            assert_condition(sibling.exists(), f"{run_dir}: missing invocation artifact {sibling.name}")

        result = load_json(result_file)
        assert_condition("run_id" in result, f"{result_file}: missing run_id")
        assert_condition("step" in result, f"{result_file}: missing step")
        assert_condition("attempt" in result, f"{result_file}: missing attempt")
        assert_condition("outcome" in result, f"{result_file}: missing outcome")
        assert_condition("failure_code" in result, f"{result_file}: missing failure_code")
        assert_condition("liveness_path" in result, f"{result_file}: missing liveness_path")


def validate_run_dir(run_dir: Path) -> None:
    required = ["run.json", "status.json", "events.jsonl", "logs"]
    for name in required:
        assert_condition((run_dir / name).exists(), f"{run_dir}: missing required harness artifact {name}")
    check_invocation_artifacts(run_dir)
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


def make_run_dir(base_dir: Path, name: str, operator_mode: str = "governed") -> Path:
    run_dir = base_dir / name
    metadata = {
        "run_id": name,
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
        "operator_mode": operator_mode,
    }
    meta_path = base_dir / f"{name}.metadata.json"
    meta_path.write_text(json.dumps(metadata), encoding="utf-8")
    subprocess.run(
        ["python3", str(PROJECTOR), "init-run", "--run-dir", str(run_dir), "--metadata-file", str(meta_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return run_dir


def project_and_load_status(run_dir: Path) -> dict[str, Any]:
    subprocess.run(
        ["python3", str(PROJECTOR), "project-status", "--run-dir", str(run_dir)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return load_json(run_dir / "status.json")


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="sawmill-harness-selftest.") as tmp:
        base_dir = Path(tmp)

        # Case 1: observed alive/progressing, then successful completion.
        run_success = make_run_dir(base_dir, "self-test-success")
        append_event(run_success, event_id="s1", run_id="self-test-success", timestamp="2026-03-10T00:00:00Z", turn="orchestrator", step="run", role="orchestrator", backend="runtime", attempt=0, event_type="run_started", outcome="started", failure_code="none", summary="run started")
        append_event(run_success, event_id="s2", run_id="self-test-success", timestamp="2026-03-10T00:00:01Z", turn="orchestrator", step="preflight", role="orchestrator", backend="runtime", attempt=0, event_type="preflight_passed", outcome="passed", failure_code="none", causal_parent_event_id="s1", summary="preflight")
        append_event(run_success, event_id="s3", run_id="self-test-success", timestamp="2026-03-10T00:00:02Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="turn_started", outcome="started", failure_code="none", causal_parent_event_id="s1", summary="turn a")
        append_event(run_success, event_id="s4", run_id="self-test-success", timestamp="2026-03-10T00:00:03Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="prompt_rendered", outcome="rendered", failure_code="none", causal_parent_event_id="s3", summary="prompt")
        append_event(run_success, event_id="s5", run_id="self-test-success", timestamp="2026-03-10T00:00:04Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="agent_invoked", outcome="invoked", failure_code="none", causal_parent_event_id="s4", summary="invoked")
        append_event(run_success, event_id="s6", run_id="self-test-success", timestamp="2026-03-10T00:00:05Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="agent_liveness_observed", outcome="alive", failure_code="none", causal_parent_event_id="s5", summary="alive")
        append_event(run_success, event_id="s7", run_id="self-test-success", timestamp="2026-03-10T00:00:06Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="agent_liveness_observed", outcome="progressing", failure_code="none", causal_parent_event_id="s5", summary="progressing")
        append_event(run_success, event_id="s8", run_id="self-test-success", timestamp="2026-03-10T00:00:07Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="agent_exited", outcome="succeeded", failure_code="none", causal_parent_event_id="s5", summary="exited ok")
        append_event(run_success, event_id="s9", run_id="self-test-success", timestamp="2026-03-10T00:00:08Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="output_verified", outcome="verified", failure_code="none", causal_parent_event_id="s8", summary="verified")
        append_event(run_success, event_id="s10", run_id="self-test-success", timestamp="2026-03-10T00:00:09Z", turn="E", step="turn_e_eval", role="evaluator", backend="claude", attempt=1, event_type="agent_exited", outcome="succeeded", failure_code="none", causal_parent_event_id="s5", summary="evaluator exited")
        append_event(run_success, event_id="s11", run_id="self-test-success", timestamp="2026-03-10T00:00:10Z", turn="E", step="turn_e_eval", role="evaluator", backend="claude", attempt=1, event_type="evaluation_verdict_recorded", outcome="pass", failure_code="none", causal_parent_event_id="s10", summary="eval pass")
        append_event(run_success, event_id="s12", run_id="self-test-success", timestamp="2026-03-10T00:00:11Z", turn="E", step="turn_e_eval", role="evaluator", backend="claude", attempt=1, event_type="turn_completed", outcome="completed", failure_code="none", causal_parent_event_id="s11", summary="turn completed")
        append_event(run_success, event_id="s13", run_id="self-test-success", timestamp="2026-03-10T00:00:12Z", turn="orchestrator", step="run", role="orchestrator", backend="runtime", attempt=1, event_type="run_completed", outcome="passed", failure_code="none", causal_parent_event_id="s12", summary="run passed")
        inv = run_success / "invocations" / "turn_a_spec.attempt1"
        payload_file = Path(str(inv) + ".payload.txt")
        meta_file = Path(str(inv) + ".meta.json")
        liveness_file = Path(str(inv) + ".liveness.jsonl")
        result_file = Path(str(inv) + ".result.json")
        inv.parent.mkdir(parents=True, exist_ok=True)
        payload_file.write_text("role\n\nprompt\n", encoding="utf-8")
        meta_file.write_text(
            json.dumps(
                {
                    "run_id": "self-test-success",
                    "framework_id": "FMWK-TEST",
                    "turn": "A",
                    "step": "turn_a_spec",
                    "role": "spec-agent",
                    "backend": "codex",
                    "attempt": 1,
                    "timeout_seconds": 60,
                    "stdout_log": str(run_success / "logs" / "turn_a_spec.attempt1.stdout.log"),
                    "stderr_log": str(run_success / "logs" / "turn_a_spec.attempt1.stderr.log"),
                    "heartbeat_file": str(run_success / "heartbeats" / "turn_a_spec.attempt1.log"),
                    "payload_path": str(payload_file),
                }
            ),
            encoding="utf-8",
        )
        liveness_file.write_text(
            json.dumps(
                {
                    "timestamp": "2026-03-10T00:00:05Z",
                    "run_id": "self-test-success",
                    "step": "turn_a_spec",
                    "role": "spec-agent",
                    "backend": "codex",
                    "attempt": 1,
                    "observation": "progressing",
                    "source": "stdout",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        result_file.write_text(
            json.dumps(
                {
                    "run_id": "self-test-success",
                    "framework_id": "FMWK-TEST",
                    "turn": "A",
                    "step": "turn_a_spec",
                    "role": "spec-agent",
                    "backend": "codex",
                    "attempt": 1,
                    "started_at": "2026-03-10T00:00:04Z",
                    "ended_at": "2026-03-10T00:00:07Z",
                    "exit_code": 0,
                    "outcome": "succeeded",
                    "failure_code": "none",
                    "stdout_log": str(run_success / "logs" / "turn_a_spec.attempt1.stdout.log"),
                    "stderr_log": str(run_success / "logs" / "turn_a_spec.attempt1.stderr.log"),
                    "heartbeat_file": str(run_success / "heartbeats" / "turn_a_spec.attempt1.log"),
                    "last_output_at": "2026-03-10T00:00:06Z",
                    "last_worker_progress_at": "2026-03-10T00:00:06Z",
                    "liveness_path": str(liveness_file),
                }
            ),
            encoding="utf-8",
        )
        status = project_and_load_status(run_success)
        assert_condition(status["state"] == "passed", "success case did not project to passed")
        assert_condition(status["worker_observation"] == "exited", "success case did not end with exited worker observation")
        assert_condition(status["last_worker_progress_at"] == "2026-03-10T00:00:06Z", "success case did not preserve last worker progress timestamp")
        rebuild_status(run_success)

        # Case 2: observed then timeout.
        run_timeout = make_run_dir(base_dir, "self-test-timeout")
        append_event(run_timeout, event_id="t1", run_id="self-test-timeout", timestamp="2026-03-10T00:01:00Z", turn="orchestrator", step="run", role="orchestrator", backend="runtime", attempt=0, event_type="run_started", outcome="started", failure_code="none", summary="run started")
        append_event(run_timeout, event_id="t2", run_id="self-test-timeout", timestamp="2026-03-10T00:01:01Z", turn="orchestrator", step="preflight", role="orchestrator", backend="runtime", attempt=0, event_type="preflight_passed", outcome="passed", failure_code="none", causal_parent_event_id="t1", summary="preflight")
        append_event(run_timeout, event_id="t3", run_id="self-test-timeout", timestamp="2026-03-10T00:01:02Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="turn_started", outcome="started", failure_code="none", causal_parent_event_id="t1", summary="turn d")
        append_event(run_timeout, event_id="t4", run_id="self-test-timeout", timestamp="2026-03-10T00:01:03Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="prompt_rendered", outcome="rendered", failure_code="none", causal_parent_event_id="t3", summary="prompt")
        append_event(run_timeout, event_id="t5", run_id="self-test-timeout", timestamp="2026-03-10T00:01:04Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="agent_invoked", outcome="invoked", failure_code="none", causal_parent_event_id="t4", summary="invoked")
        append_event(run_timeout, event_id="t6", run_id="self-test-timeout", timestamp="2026-03-10T00:01:05Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="agent_liveness_observed", outcome="alive", failure_code="none", causal_parent_event_id="t5", summary="alive")
        append_event(run_timeout, event_id="t7", run_id="self-test-timeout", timestamp="2026-03-10T00:01:06Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="agent_liveness_observed", outcome="stalled", failure_code="none", causal_parent_event_id="t5", summary="stalled")
        append_event(run_timeout, event_id="t8", run_id="self-test-timeout", timestamp="2026-03-10T00:01:07Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="timeout_triggered", outcome="timeout", failure_code="AGENT_TIMEOUT", causal_parent_event_id="t5", summary="timeout")
        append_event(run_timeout, event_id="t9", run_id="self-test-timeout", timestamp="2026-03-10T00:01:08Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="run_failed", outcome="failed", failure_code="AGENT_TIMEOUT", causal_parent_event_id="t8", summary="run failed")
        status = project_and_load_status(run_timeout)
        assert_condition(status["state"] == "failed", "timeout case did not project to failed")
        assert_condition(status["worker_observation"] == "exited", "timeout case did not end with exited worker observation")
        rebuild_status(run_timeout)

        # Case 3: observed then non-zero exit.
        run_nonzero = make_run_dir(base_dir, "self-test-nonzero")
        append_event(run_nonzero, event_id="n1", run_id="self-test-nonzero", timestamp="2026-03-10T00:02:00Z", turn="orchestrator", step="run", role="orchestrator", backend="runtime", attempt=0, event_type="run_started", outcome="started", failure_code="none", summary="run started")
        append_event(run_nonzero, event_id="n2", run_id="self-test-nonzero", timestamp="2026-03-10T00:02:01Z", turn="orchestrator", step="preflight", role="orchestrator", backend="runtime", attempt=0, event_type="preflight_passed", outcome="passed", failure_code="none", causal_parent_event_id="n1", summary="preflight")
        append_event(run_nonzero, event_id="n3", run_id="self-test-nonzero", timestamp="2026-03-10T00:02:02Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="turn_started", outcome="started", failure_code="none", causal_parent_event_id="n1", summary="turn a")
        append_event(run_nonzero, event_id="n4", run_id="self-test-nonzero", timestamp="2026-03-10T00:02:03Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="prompt_rendered", outcome="rendered", failure_code="none", causal_parent_event_id="n3", summary="prompt")
        append_event(run_nonzero, event_id="n5", run_id="self-test-nonzero", timestamp="2026-03-10T00:02:04Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="agent_invoked", outcome="invoked", failure_code="none", causal_parent_event_id="n4", summary="invoked")
        append_event(run_nonzero, event_id="n6", run_id="self-test-nonzero", timestamp="2026-03-10T00:02:05Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="agent_liveness_observed", outcome="progressing", failure_code="none", causal_parent_event_id="n5", summary="progressing")
        append_event(run_nonzero, event_id="n7", run_id="self-test-nonzero", timestamp="2026-03-10T00:02:06Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="agent_exited", outcome="failed", failure_code="AGENT_EXIT_NONZERO", causal_parent_event_id="n5", summary="failed exit")
        append_event(run_nonzero, event_id="n8", run_id="self-test-nonzero", timestamp="2026-03-10T00:02:07Z", turn="A", step="turn_a_spec", role="spec-agent", backend="codex", attempt=1, event_type="run_failed", outcome="failed", failure_code="AGENT_EXIT_NONZERO", causal_parent_event_id="n7", summary="run failed")
        status = project_and_load_status(run_nonzero)
        assert_condition(status["state"] == "failed", "nonzero case did not project to failed")
        assert_condition(status["worker_observation"] == "exited", "nonzero case did not end with exited worker observation")
        rebuild_status(run_nonzero)

        # Case 4: no liveness observed before timeout.
        run_no_liveness = make_run_dir(base_dir, "self-test-no-liveness")
        append_event(run_no_liveness, event_id="l1", run_id="self-test-no-liveness", timestamp="2026-03-10T00:03:00Z", turn="orchestrator", step="run", role="orchestrator", backend="runtime", attempt=0, event_type="run_started", outcome="started", failure_code="none", summary="run started")
        append_event(run_no_liveness, event_id="l2", run_id="self-test-no-liveness", timestamp="2026-03-10T00:03:01Z", turn="orchestrator", step="preflight", role="orchestrator", backend="runtime", attempt=0, event_type="preflight_passed", outcome="passed", failure_code="none", causal_parent_event_id="l1", summary="preflight")
        append_event(run_no_liveness, event_id="l3", run_id="self-test-no-liveness", timestamp="2026-03-10T00:03:02Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="turn_started", outcome="started", failure_code="none", causal_parent_event_id="l1", summary="turn d")
        append_event(run_no_liveness, event_id="l4", run_id="self-test-no-liveness", timestamp="2026-03-10T00:03:03Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="prompt_rendered", outcome="rendered", failure_code="none", causal_parent_event_id="l3", summary="prompt")
        append_event(run_no_liveness, event_id="l5", run_id="self-test-no-liveness", timestamp="2026-03-10T00:03:04Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="agent_invoked", outcome="invoked", failure_code="none", causal_parent_event_id="l4", summary="invoked")
        append_event(run_no_liveness, event_id="l6", run_id="self-test-no-liveness", timestamp="2026-03-10T00:03:05Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="timeout_triggered", outcome="timeout", failure_code="AGENT_TIMEOUT", causal_parent_event_id="l5", summary="timeout")
        append_event(run_no_liveness, event_id="l7", run_id="self-test-no-liveness", timestamp="2026-03-10T00:03:06Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="run_failed", outcome="failed", failure_code="AGENT_TIMEOUT", causal_parent_event_id="l6", summary="run failed")
        status = project_and_load_status(run_no_liveness)
        assert_condition(status["state"] == "failed", "no-liveness timeout case did not project to failed")
        assert_condition(status["worker_observation"] == "exited", "no-liveness timeout case did not end with exited worker observation")
        assert_condition(status["last_worker_progress_at"] == "", "no-liveness timeout case should not set progress timestamp")
        rebuild_status(run_no_liveness)

        # Case 5: manual intervention still invalidates PASS even with liveness events present.
        run_invalidated = make_run_dir(base_dir, "self-test-invalidated")
        append_event(run_invalidated, event_id="i1", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:00Z", turn="orchestrator", step="run", role="orchestrator", backend="runtime", attempt=0, event_type="run_started", outcome="started", failure_code="none", summary="run started")
        append_event(run_invalidated, event_id="i2", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:01Z", turn="orchestrator", step="preflight", role="orchestrator", backend="runtime", attempt=0, event_type="preflight_passed", outcome="passed", failure_code="none", causal_parent_event_id="i1", summary="preflight")
        append_event(run_invalidated, event_id="i3", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:02Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="turn_started", outcome="started", failure_code="none", causal_parent_event_id="i1", summary="turn d")
        append_event(run_invalidated, event_id="i4", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:03Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="prompt_rendered", outcome="rendered", failure_code="none", causal_parent_event_id="i3", summary="prompt")
        append_event(run_invalidated, event_id="i5", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:04Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="agent_invoked", outcome="invoked", failure_code="none", causal_parent_event_id="i4", summary="invoked")
        append_event(run_invalidated, event_id="i6", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:05Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="agent_liveness_observed", outcome="progressing", failure_code="none", causal_parent_event_id="i5", summary="progressing")
        append_event(run_invalidated, event_id="i7", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:06Z", turn="D", step="turn_d_review", role="reviewer", backend="claude", attempt=1, event_type="timeout_triggered", outcome="timeout", failure_code="AGENT_TIMEOUT", causal_parent_event_id="i5", summary="timeout")
        append_event(run_invalidated, event_id="i8", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:07Z", turn="D", step="manual_intervention", role="human", backend="manual", attempt=1, event_type="manual_intervention_recorded", outcome="recorded", failure_code="MANUAL_INTERVENTION", causal_parent_event_id="i7", summary="manual")
        append_event(run_invalidated, event_id="i9", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:08Z", turn="E", step="turn_e_eval", role="evaluator", backend="claude", attempt=1, event_type="agent_exited", outcome="succeeded", failure_code="none", causal_parent_event_id="i5", summary="evaluator exited")
        append_event(run_invalidated, event_id="i10", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:09Z", turn="E", step="turn_e_eval", role="evaluator", backend="claude", attempt=1, event_type="evaluation_verdict_recorded", outcome="pass", failure_code="none", causal_parent_event_id="i9", summary="eval pass")
        append_event(run_invalidated, event_id="i11", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:10Z", turn="E", step="turn_e_eval", role="evaluator", backend="claude", attempt=1, event_type="turn_completed", outcome="completed", failure_code="none", causal_parent_event_id="i10", summary="completed")
        append_event(run_invalidated, event_id="i12", run_id="self-test-invalidated", timestamp="2026-03-10T00:04:11Z", turn="orchestrator", step="run", role="orchestrator", backend="runtime", attempt=1, event_type="run_completed", outcome="passed", failure_code="none", causal_parent_event_id="i11", summary="done")
        status = project_and_load_status(run_invalidated)
        assert_condition(status["state"] == "invalidated", "manual-intervention PASS case did not coerce to invalidated")
        rebuild_status(run_invalidated)

        print(f"PASS: harness self-test ({base_dir})")


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
