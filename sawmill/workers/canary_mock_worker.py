#!/usr/bin/env python3
"""Deterministic local worker for end-to-end canary pipeline validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic canary mock Sawmill worker")
    parser.add_argument("--prompt-key", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--framework", required=True)
    parser.add_argument("--attempt", type=int, required=True)
    return parser.parse_args()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _raw_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_sha256(path: Path) -> str:
    return f"sha256:{_raw_file_sha256(path)}"


def dir_sha256(path: Path) -> str:
    entries: list[str] = []
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        entries.append(f"{child.relative_to(path).as_posix()}:{_raw_file_sha256(child)}")
    digest = hashlib.sha256()
    digest.update("\n".join(entries).encode("utf-8"))
    return f"sha256:{digest.hexdigest()}"


def env_path(name: str) -> Path:
    return Path(os.environ[name])


def sawmill_dir() -> Path:
    return env_path("SAWMILL_DIR")


def holdout_dir() -> Path:
    return env_path("HOLDOUT_DIR")


def staging_dir() -> Path:
    return env_path("STAGING_DIR")


def task_name(framework: str) -> str:
    task_path = sawmill_dir() / "TASK.md"
    if not task_path.exists():
        return framework
    for line in task_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("- Name:"):
            return line.split(":", 1)[1].strip()
    return framework


def contract_version_from_prompt(var_name: str, fallback: str) -> str:
    value = os.environ.get(var_name, "").strip()
    return value or fallback


def run_id() -> str:
    return os.environ.get("RUN_ID", "unknown-run")


def write_turn_a(framework: str) -> None:
    fw_name = task_name(framework)
    root = sawmill_dir()
    write_text(
        root / "D1_CONSTITUTION.md",
        f"# D1: Constitution — {fw_name}\n\n"
        "## Articles\n\n"
        "1. The canary mock worker writes the minimum governed specification outputs.\n"
        "2. Scope remains intentionally tiny and deterministic.\n"
        "3. No external runtime dependencies are required.\n",
    )
    write_text(
        root / "D2_SPECIFICATION.md",
        f"# D2: Specification — {fw_name}\n\n"
        "## Scenarios\n\n"
        "- SC-001: The framework can be specified deterministically.\n"
        "- SC-002: The framework can progress through the Sawmill pipeline.\n",
    )
    write_text(
        root / "D3_DATA_MODEL.md",
        f"# D3: Data Model — {fw_name}\n\n"
        "No persistent data model is required for this canary validation path.\n",
    )
    write_text(
        root / "D4_CONTRACTS.md",
        f"# D4: Contracts — {fw_name}\n\n"
        "## Inputs\n\n"
        "- IN-001: TASK.md exists.\n\n"
        "## Outputs\n\n"
        "- OUT-001: D1-D6 files are written.\n",
    )
    write_text(
        root / "D5_RESEARCH.md",
        f"# D5: Research — {fw_name}\n\n"
        "No external research required for deterministic canary validation.\n",
    )
    write_text(
        root / "D6_GAP_ANALYSIS.md",
        f"# D6: Gap Analysis — {fw_name}\n\n"
        "Status: PASS\n\n"
        "All gaps are resolved or intentionally bounded for deterministic canary validation.\n"
        "OPEN items: 0\n",
    )


def write_turn_b(framework: str) -> None:
    fw_name = task_name(framework)
    root = sawmill_dir()
    write_text(
        root / "D7_PLAN.md",
        f"# D7: Plan — {fw_name}\n\n"
        "## Constitution Check\n\n"
        "PASS: The canary build plan satisfies the deterministic constitution.\n",
    )
    write_text(
        root / "D8_TASKS.md",
        f"# D8: Tasks — {fw_name}\n\n"
        "- T-001: Produce deterministic canary outputs.\n"
        "- T-002: Preserve harness truth and runtime flow.\n",
    )
    write_text(
        root / "D10_AGENT_CONTEXT.md",
        f"# D10: Agent Context — {fw_name}\n\n"
        "Tool Rules: Use the governed Sawmill runtime and write only expected outputs.\n",
    )
    write_text(
        root / "BUILDER_HANDOFF.md",
        f"# Builder Handoff — {fw_name}\n\n"
        "Mission: Build the smallest valid implementation consistent with the spec.\n\n"
        "Critical constraints:\n"
        "- Preserve governed runtime truth.\n"
        "- Produce only expected artifacts.\n"
        "- Keep the implementation to smoke.py and test_smoke.py.\n",
    )


def write_turn_c(framework: str) -> None:
    fw_name = task_name(framework)
    root = holdout_dir()
    write_text(
        root / "D9_HOLDOUT_SCENARIOS.md",
        f"# D9: Holdout Scenarios — {fw_name}\n\n"
        "## HS-001\n"
        "- Execute: import smoke.ping and assert return value is exactly `pong`\n\n"
        "## HS-002\n"
        "- Execute: run pytest against test_smoke.py\n",
    )


def write_portal_stage(framework: str) -> None:
    status_path = env_path("PORTAL_STATUS_PATH")
    changeset_path = env_path("PORTAL_CHANGESET_PATH")
    stage = os.environ.get("STAGE", "unknown-stage")
    write_text(
        status_path,
        "# Portal Status\n\n"
        f"- Framework: {framework}\n"
        f"- Stage: {stage}\n"
        f"- Run ID: {run_id()}\n"
        "- Status: healthy\n",
    )
    write_text(
        changeset_path,
        "# Portal Changeset\n\n"
        f"- Run ID: {run_id()}\n"
        f"- Applied stage: {stage}\n"
        "- Deterministic canary portal sync completed.\n",
    )


def write_turn_d_13q(args: argparse.Namespace) -> None:
    version = contract_version_from_prompt("BUILDER_PROMPT_CONTRACT_VERSION", "unknown")
    write_text(
        sawmill_dir() / "13Q_ANSWERS.md",
        "# 13Q Answers\n\n"
        f"Builder Prompt Contract Version: {version}\n\n"
        "1. Mission understood: build smoke.py and test_smoke.py.\n"
        "2. Inputs reviewed: D10_AGENT_CONTEXT and BUILDER_HANDOFF.\n"
        "3. TDD plan: write and pass the minimal test.\n",
    )


def write_turn_d_review(args: argparse.Namespace) -> None:
    root = sawmill_dir()
    builder_version = contract_version_from_prompt("BUILDER_PROMPT_CONTRACT_VERSION", "unknown")
    reviewer_version = contract_version_from_prompt("REVIEWER_PROMPT_CONTRACT_VERSION", "unknown")
    q13_path = root / "13Q_ANSWERS.md"
    review_report = root / "REVIEW_REPORT.md"
    review_errors = root / "REVIEW_ERRORS.md"

    write_text(
        review_report,
        "# Review Report\n\n"
        f"Builder Prompt Contract Version Reviewed: {builder_version}\n"
        f"Reviewer Prompt Contract Version: {reviewer_version}\n\n"
        "- All 13Q answers are concrete and aligned to the canary handoff.\n\n"
        "Review verdict: PASS\n",
    )
    write_text(review_errors, "# Review Errors\n\nNone.\n")
    write_json(
        root / "reviewer_evidence.json",
        {
            "run_id": run_id(),
            "attempt": args.attempt,
            "q13_answers_hash": file_sha256(q13_path),
            "builder_prompt_contract_version_reviewed": builder_version,
            "reviewer_prompt_contract_version": reviewer_version,
            "findings": [],
            "verdict": "PASS",
            "failure_code": "",
        },
    )


def write_turn_d_build(args: argparse.Namespace) -> None:
    root = sawmill_dir()
    staging = staging_dir()
    handoff_path = root / "BUILDER_HANDOFF.md"
    q13_path = root / "13Q_ANSWERS.md"
    smoke_path = staging / "smoke.py"
    test_path = staging / "test_smoke.py"
    results_path = root / "RESULTS.md"

    write_text(
        smoke_path,
        "def ping() -> str:\n"
        "    return \"pong\"\n",
    )
    write_text(
        test_path,
        "from smoke import ping\n\n\n"
        "def test_ping_returns_pong() -> None:\n"
        "    assert ping() == \"pong\"\n",
    )
    write_text(
        results_path,
        "# Results\n\n"
        "Pytest: 1 passed\n"
        "Function output: pong\n"
        "Artifacts written: smoke.py, test_smoke.py\n",
    )
    write_json(
        root / "builder_evidence.json",
        {
            "run_id": run_id(),
            "attempt": args.attempt,
            "handoff_hash": file_sha256(handoff_path),
            "q13_answers_hash": file_sha256(q13_path),
            "behaviors": [
                {
                    "behavior_id": "ping_returns_pong",
                    "failing_test_command": "pytest -q staging/FMWK-900-sawmill-smoke/test_smoke.py",
                    "failing_observation": "Behavior defined before implementation in deterministic canary path",
                    "passing_test_command": "pytest -q staging/FMWK-900-sawmill-smoke/test_smoke.py",
                    "passing_observation": "1 passed",
                    "files_touched": [
                        "staging/FMWK-900-sawmill-smoke/smoke.py",
                        "staging/FMWK-900-sawmill-smoke/test_smoke.py",
                    ],
                }
            ],
            "full_test_command": "pytest -q staging/FMWK-900-sawmill-smoke/test_smoke.py",
            "full_test_result": "1 passed",
            "files_changed": [
                "staging/FMWK-900-sawmill-smoke/smoke.py",
                "staging/FMWK-900-sawmill-smoke/test_smoke.py",
                "sawmill/FMWK-900-sawmill-smoke/RESULTS.md",
            ],
            "results_hash": file_sha256(results_path),
        },
    )


def write_turn_e_eval(args: argparse.Namespace) -> None:
    root = sawmill_dir()
    holdout_path = holdout_dir() / "D9_HOLDOUT_SCENARIOS.md"
    staging = staging_dir()
    evaluation_report = root / "EVALUATION_REPORT.md"
    evaluation_errors = root / "EVALUATION_ERRORS.md"

    write_text(
        evaluation_report,
        "# Evaluation Report\n\n"
        "Scenario HS-001: PASS (3/3)\n"
        "Scenario HS-002: PASS (3/3)\n\n"
        "Final verdict: PASS\n",
    )
    write_text(evaluation_errors, "# Evaluation Errors\n\nNone.\n")
    write_json(
        root / "evaluator_evidence.json",
        {
            "run_id": run_id(),
            "attempt": args.attempt,
            "holdout_hash": file_sha256(holdout_path),
            "staging_hash": dir_sha256(staging),
            "scenarios": [
                {
                    "scenario_id": "HS-001",
                    "run_results": ["PASS", "PASS", "PASS"],
                    "aggregate_result": "PASS",
                },
                {
                    "scenario_id": "HS-002",
                    "run_results": ["PASS", "PASS", "PASS"],
                    "aggregate_result": "PASS",
                },
            ],
            "verdict": "PASS",
            "pass_rate": 100.0,
        },
    )


def dispatch(args: argparse.Namespace) -> None:
    if args.prompt_key == "turn_a_spec":
        write_turn_a(args.framework)
    elif args.prompt_key == "turn_b_plan":
        write_turn_b(args.framework)
    elif args.prompt_key == "turn_c_holdout":
        write_turn_c(args.framework)
    elif args.prompt_key == "portal_stage":
        write_portal_stage(args.framework)
    elif args.prompt_key == "turn_d_13q":
        write_turn_d_13q(args)
    elif args.prompt_key == "turn_d_review":
        write_turn_d_review(args)
    elif args.prompt_key == "turn_d_build":
        write_turn_d_build(args)
    elif args.prompt_key == "turn_e_eval":
        write_turn_e_eval(args)
    else:
        raise ValueError(f"unsupported prompt_key: {args.prompt_key}")


def main() -> int:
    args = parse_args()
    _prompt = os.environ.get("SAWMILL_MOCK_PROMPT", "")
    try:
        time.sleep(1.5)
        dispatch(args)
    except Exception as exc:  # pragma: no cover - deterministic worker error path
        print(
            json.dumps(
                {
                    "backend": "mock",
                    "role": args.role,
                    "prompt_key": args.prompt_key,
                    "framework": args.framework,
                    "attempt": args.attempt,
                    "status": "error",
                    "error": str(exc),
                }
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "backend": "mock",
                "role": args.role,
                "prompt_key": args.prompt_key,
                "framework": args.framework,
                "attempt": args.attempt,
                "status": "ok",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
