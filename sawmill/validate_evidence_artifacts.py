#!/usr/bin/env python3
"""Validate builder/reviewer/evaluator evidence artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

TRANSIENT_DIR_NAMES = {".pytest_cache", "__pycache__"}
TRANSIENT_SUFFIXES = {".pyc", ".pyo"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Sawmill evidence artifacts")
    parser.add_argument("--kind", required=True, choices=("builder", "reviewer", "evaluator"))
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", type=int, required=True)
    parser.add_argument("--handoff")
    parser.add_argument("--q13-answers")
    parser.add_argument("--results")
    parser.add_argument("--review-report")
    parser.add_argument("--holdouts")
    parser.add_argument("--staging-root")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Missing evidence artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Evidence artifact must be a JSON object: {path}")
    return data


def _raw_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
    except FileNotFoundError as exc:
        raise ValueError(f"Missing referenced file: {path}") from exc
    return digest.hexdigest()


def file_sha256(path: Path) -> str:
    return f"sha256:{_raw_file_sha256(path)}"


def dir_sha256(path: Path) -> str:
    if not path.is_dir():
        raise ValueError(f"Missing referenced directory: {path}")
    entries: list[str] = []
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        if any(part in TRANSIENT_DIR_NAMES for part in child.parts):
            continue
        if child.suffix in TRANSIENT_SUFFIXES:
            continue
        relative = child.relative_to(path).as_posix()
        entries.append(f"{relative}:{_raw_file_sha256(child)}")
    digest = hashlib.sha256()
    digest.update("\n".join(entries).encode("utf-8"))
    return f"sha256:{digest.hexdigest()}"


def require_fields(data: dict[str, Any], path: Path, fields: list[str]) -> None:
    missing = [field for field in fields if field not in data]
    if missing:
        raise ValueError(f"{path} is missing required fields: {', '.join(missing)}")


def expect_string(value: Any, field_name: str, path: Path) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} field '{field_name}' must be a non-empty string")
    return value


def expect_list(value: Any, field_name: str, path: Path) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} field '{field_name}' must be a list")
    return value


def validate_common(data: dict[str, Any], path: Path, run_id: str, attempt: int) -> None:
    if data.get("run_id") != run_id:
        raise ValueError(f"{path} run_id mismatch: expected {run_id}, found {data.get('run_id')}")
    if data.get("attempt") != attempt:
        raise ValueError(f"{path} attempt mismatch: expected {attempt}, found {data.get('attempt')}")


def validate_builder(data: dict[str, Any], path: Path, args: argparse.Namespace) -> None:
    require_fields(
        data,
        path,
        [
            "run_id",
            "attempt",
            "handoff_hash",
            "q13_answers_hash",
            "behaviors",
            "full_test_command",
            "full_test_result",
            "files_changed",
            "results_hash",
        ],
    )
    validate_common(data, path, args.run_id, args.attempt)
    expect_string(data["handoff_hash"], "handoff_hash", path)
    expect_string(data["q13_answers_hash"], "q13_answers_hash", path)
    expect_string(data["full_test_command"], "full_test_command", path)
    expect_string(data["full_test_result"], "full_test_result", path)
    files_changed = expect_list(data["files_changed"], "files_changed", path)
    behaviors = expect_list(data["behaviors"], "behaviors", path)
    if not behaviors:
        raise ValueError(f"{path} behaviors must contain at least one entry")
    for index, behavior in enumerate(behaviors):
        if not isinstance(behavior, dict):
            raise ValueError(f"{path} behaviors[{index}] must be an object")
        require_fields(
            behavior,
            path,
            [
                "behavior_id",
                "failing_test_command",
                "failing_observation",
                "passing_test_command",
                "passing_observation",
                "files_touched",
            ],
        )
        for field in (
            "behavior_id",
            "failing_test_command",
            "failing_observation",
            "passing_test_command",
            "passing_observation",
        ):
            expect_string(behavior[field], f"behaviors[{index}].{field}", path)
        files_touched = expect_list(behavior["files_touched"], f"behaviors[{index}].files_touched", path)
        if not files_touched:
            raise ValueError(f"{path} behaviors[{index}].files_touched must not be empty")
    if not files_changed:
        raise ValueError(f"{path} files_changed must not be empty")

    if not args.handoff or not args.q13_answers or not args.results:
        raise ValueError("Builder evidence validation requires --handoff, --q13-answers, and --results")
    if data["handoff_hash"] != file_sha256(Path(args.handoff)):
        raise ValueError(f"{path} handoff_hash does not match {args.handoff}")
    if data["q13_answers_hash"] != file_sha256(Path(args.q13_answers)):
        raise ValueError(f"{path} q13_answers_hash does not match {args.q13_answers}")
    if data["results_hash"] != file_sha256(Path(args.results)):
        raise ValueError(f"{path} results_hash does not match {args.results}")


def validate_reviewer(data: dict[str, Any], path: Path, args: argparse.Namespace) -> None:
    require_fields(
        data,
        path,
        [
            "run_id",
            "attempt",
            "q13_answers_hash",
            "builder_prompt_contract_version_reviewed",
            "reviewer_prompt_contract_version",
            "findings",
            "verdict",
            "failure_code",
        ],
    )
    validate_common(data, path, args.run_id, args.attempt)
    expect_string(data["q13_answers_hash"], "q13_answers_hash", path)
    expect_string(data["builder_prompt_contract_version_reviewed"], "builder_prompt_contract_version_reviewed", path)
    expect_string(data["reviewer_prompt_contract_version"], "reviewer_prompt_contract_version", path)
    findings = expect_list(data["findings"], "findings", path)
    if data["verdict"] not in {"PASS", "RETRY", "ESCALATE"}:
        raise ValueError(f"{path} verdict must be PASS, RETRY, or ESCALATE")
    if data["verdict"] == "PASS" and findings:
        pass
    elif data["verdict"] != "PASS" and not findings:
        raise ValueError(f"{path} findings must not be empty when verdict is {data['verdict']}")
    if not isinstance(data["failure_code"], str):
        raise ValueError(f"{path} failure_code must be a string")

    if not args.q13_answers:
        raise ValueError("Reviewer evidence validation requires --q13-answers")
    if data["q13_answers_hash"] != file_sha256(Path(args.q13_answers)):
        raise ValueError(f"{path} q13_answers_hash does not match {args.q13_answers}")


def validate_evaluator(data: dict[str, Any], path: Path, args: argparse.Namespace) -> None:
    require_fields(
        data,
        path,
        [
            "run_id",
            "attempt",
            "holdout_hash",
            "staging_hash",
            "scenarios",
            "verdict",
            "pass_rate",
        ],
    )
    validate_common(data, path, args.run_id, args.attempt)
    expect_string(data["holdout_hash"], "holdout_hash", path)
    expect_string(data["staging_hash"], "staging_hash", path)
    scenarios = expect_list(data["scenarios"], "scenarios", path)
    if not scenarios:
        raise ValueError(f"{path} scenarios must contain at least one entry")
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ValueError(f"{path} scenarios[{index}] must be an object")
        require_fields(scenario, path, ["scenario_id", "run_results", "aggregate_result"])
        expect_string(scenario["scenario_id"], f"scenarios[{index}].scenario_id", path)
        run_results = expect_list(scenario["run_results"], f"scenarios[{index}].run_results", path)
        if not run_results:
            raise ValueError(f"{path} scenarios[{index}].run_results must not be empty")
        expect_string(scenario["aggregate_result"], f"scenarios[{index}].aggregate_result", path)
    if data["verdict"] not in {"PASS", "FAIL"}:
        raise ValueError(f"{path} verdict must be PASS or FAIL")
    try:
        pass_rate = float(data["pass_rate"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} pass_rate must be numeric") from exc
    if not 0.0 <= pass_rate <= 100.0:
        raise ValueError(f"{path} pass_rate must be between 0 and 100")

    if not args.holdouts or not args.staging_root:
        raise ValueError("Evaluator evidence validation requires --holdouts and --staging-root")
    if data["holdout_hash"] != file_sha256(Path(args.holdouts)):
        raise ValueError(f"{path} holdout_hash does not match {args.holdouts}")
    if data["staging_hash"] != dir_sha256(Path(args.staging_root)):
        raise ValueError(f"{path} staging_hash does not match {args.staging_root}")


def main() -> int:
    args = parse_args()
    artifact_path = Path(args.artifact)
    try:
        data = load_json(artifact_path)
        if args.kind == "builder":
            validate_builder(data, artifact_path, args)
        elif args.kind == "reviewer":
            validate_reviewer(data, artifact_path, args)
        else:
            validate_evaluator(data, artifact_path, args)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"PASS: {args.kind} evidence valid ({artifact_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
