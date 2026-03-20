"""Runtime audit, convergence, and preflight helpers."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from sawmill.evidence import (
    load_json as load_evidence_json,
    parse_evaluation_verdict,
    parse_review_verdict,
    validate_builder,
    validate_evaluator,
    validate_reviewer,
)
from sawmill.registry import build_stage_maps, load_artifact_registry
from sawmill.run_state import current_status_field, project_status, write_status

from . import _contracts


ROOT = Path(__file__).resolve().parents[2]


def _artifact_path(template: str, framework_id: str) -> Path:
    return ROOT / template.replace("{FMWK}", framework_id)


def _artifact_exists(kind: str, path: Path) -> bool:
    return path.is_dir() if kind == "dir" else path.is_file()


def _artifact_present(kind: str, path: Path) -> bool:
    if kind == "dir":
        return path.is_dir() and any(path.iterdir())
    return path.is_file()


def _stage_context(framework_id: str, artifact_registry: Path) -> tuple[dict, dict[str, list[str]], dict[str, list[str]]]:
    registry = load_artifact_registry(artifact_registry)
    stage_all, stage_required, _ = build_stage_maps(registry)
    return registry["artifacts"], stage_all, stage_required


def _stage_complete(stage: str, framework_id: str, artifacts: dict, stage_required: dict[str, list[str]], evaluation_report: Path) -> bool:
    for artifact_id in stage_required[stage]:
        metadata = artifacts[artifact_id]
        if not _artifact_exists(metadata["artifact_kind"], _artifact_path(metadata["path_template"], framework_id)):
            return False
    if stage == "E":
        try:
            verdict = parse_evaluation_verdict(evaluation_report)
        except ValueError:
            return False
        return verdict in {"PASS", "FAIL"}
    return True


def _stage_has_any(stage: str, framework_id: str, artifacts: dict, stage_all: dict[str, list[str]]) -> bool:
    for artifact_id in stage_all[stage]:
        metadata = artifacts[artifact_id]
        if _artifact_present(metadata["artifact_kind"], _artifact_path(metadata["path_template"], framework_id)):
            return True
    return False


def main_stage(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a stage audit")
    parser.add_argument("--fmwk", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--status-page", required=True)
    parser.add_argument("--artifact-registry", default="sawmill/ARTIFACT_REGISTRY.yaml")
    parser.add_argument("--review-report", required=True)
    parser.add_argument("--review-errors", required=True)
    parser.add_argument("--evaluation-report", required=True)
    parser.add_argument("--audit-file", required=True)
    args = parser.parse_args(argv)

    try:
        artifacts, stage_all, stage_required = _stage_context(args.fmwk, Path(args.artifact_registry))
        status_page = Path(args.status_page)
        review_report = Path(args.review_report)
        review_errors = Path(args.review_errors)
        evaluation_report = Path(args.evaluation_report)
        results: list[tuple[bool, str]] = []

        def ck(description: str, condition: bool) -> None:
            results.append((condition, description))

        ck("Status page exists", status_page.is_file())
        for stage in ("A", "B", "C"):
            if _stage_has_any(stage, args.fmwk, artifacts, stage_all):
                for artifact_id in stage_required[stage]:
                    metadata = artifacts[artifact_id]
                    ck(
                        f"{artifact_id} exists",
                        _artifact_exists(
                            metadata["artifact_kind"],
                            _artifact_path(metadata["path_template"], args.fmwk),
                        ),
                    )
                ck(
                    f"Portal: Turn {stage} {'DONE' if stage != 'E' else 'PASS'}",
                    f"Turn {stage} " in status_page.read_text(encoding="utf-8", errors="replace"),
                )

        q13_path = _artifact_path(artifacts["q13_answers"]["path_template"], args.fmwk)
        if q13_path.is_file():
            ck("13Q answers exist", True)
        if review_report.is_file():
            ck("REVIEW_REPORT.md exists", True)
            ck("REVIEW_ERRORS.md exists", review_errors.is_file())
            try:
                ck("Review verdict parseable", parse_review_verdict(review_report) != "UNKNOWN")
            except ValueError:
                ck("Review verdict parseable", False)

        for stage in ("D", "E"):
            if _stage_has_any(stage, args.fmwk, artifacts, stage_all):
                for artifact_id in stage_required[stage]:
                    metadata = artifacts[artifact_id]
                    ck(
                        f"{artifact_id} exists",
                        _artifact_exists(
                            metadata["artifact_kind"],
                            _artifact_path(metadata["path_template"], args.fmwk),
                        ),
                    )
                if stage == "D":
                    ck("Portal: Turn D DONE", "Turn D (Build) | DONE" in status_page.read_text(encoding="utf-8", errors="replace"))
                else:
                    try:
                        verdict = parse_evaluation_verdict(evaluation_report)
                    except ValueError:
                        ck("Evaluation verdict parseable", False)
                    else:
                        ck(f"Portal: Turn E {verdict}", f"Turn E (Eval) | {verdict}" in status_page.read_text(encoding="utf-8", errors="replace"))

        page_text = status_page.read_text(encoding="utf-8", errors="replace") if status_page.exists() else ""
        if "Turn A (Spec) | DONE" in page_text:
            ck("Portal says A DONE → Turn A complete", _stage_complete("A", args.fmwk, artifacts, stage_required, evaluation_report))
        if "Turn B (Plan) | DONE" in page_text:
            ck("Portal says B DONE → Turn B complete", _stage_complete("B", args.fmwk, artifacts, stage_required, evaluation_report))
        if "Turn C (Holdout) | DONE" in page_text:
            ck("Portal says C DONE → Turn C complete", _stage_complete("C", args.fmwk, artifacts, stage_required, evaluation_report))
        if "Turn D (Build) | DONE" in page_text:
            ck("Portal says D DONE → Turn D complete", _stage_complete("D", args.fmwk, artifacts, stage_required, evaluation_report))
        if "Turn E (Eval) | PASS" in page_text:
            ck("Portal says E PASS → Turn E complete", _stage_complete("E", args.fmwk, artifacts, stage_required, evaluation_report))
            ck("Portal says E PASS → evaluation verdict PASS", parse_evaluation_verdict(evaluation_report) == "PASS")
        if "Turn E (Eval) | FAIL" in page_text:
            ck("Portal says E FAIL → Turn E complete", _stage_complete("E", args.fmwk, artifacts, stage_required, evaluation_report))
            ck("Portal says E FAIL → evaluation verdict FAIL", parse_evaluation_verdict(evaluation_report) == "FAIL")

        ck("catalog-info.yaml exists", (ROOT / "catalog-info.yaml").is_file())

        passed = sum(1 for ok, _ in results if ok)
        failed = sum(1 for ok, _ in results if not ok)
        lines = [
            f"# Canary Audit — {args.fmwk}",
            "",
            f"Stage: {args.stage}",
            f"Date: {subprocess.run([sys.executable, '-m', 'sawmill.run_state', 'iso-timestamp'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()}",
            f"Pass: {passed}",
            f"Fail: {failed}",
            "",
            "## Results",
            "",
            "| Status | Check |",
            "|--------|-------|",
        ]
        for ok, desc in results:
            lines.append(f"| {'PASS' if ok else '**FAIL**'} | {desc} |")
        lines.extend(
            [
                "## Verdict",
                "",
                f"{'**PASS**' if failed == 0 else '**FAIL**'} — {'all ' + str(passed) + ' checks passed' if failed == 0 else str(failed) + ' check(s) failed'}",
                "",
            ]
        )
        audit_file = Path(args.audit_file)
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        audit_file.write_text("\n".join(lines), encoding="utf-8")
        if failed:
            print(f"FAIL: Stage audit FAILED ({failed} failures). See {audit_file}", file=sys.stderr)
            return 1
        print(f"PASS: Stage audit PASSED ({passed} checks)")
        return 0
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


def main_convergence(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate run convergence")
    parser.add_argument("--fmwk", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--status-page", required=True)
    parser.add_argument("--status-json", required=True)
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--holdout-dir", required=True)
    parser.add_argument("--staging-dir", required=True)
    args = parser.parse_args(argv)
    try:
        run_dir = Path(args.run_dir)
        write_status(run_dir, project_status(run_dir))

        base_dir = Path(args.base_dir)
        reviewer = base_dir / "reviewer_evidence.json"
        builder = base_dir / "builder_evidence.json"
        evaluator = base_dir / "evaluator_evidence.json"
        attempt = 1
        if reviewer.exists():
            attempt = int(load_evidence_json(reviewer)["attempt"])
            validate_reviewer(
                load_evidence_json(reviewer),
                reviewer,
                argparse.Namespace(run_id=args.run_id, attempt=attempt, q13_answers=str(base_dir / "13Q_ANSWERS.md")),
            )
        if builder.exists():
            attempt = int(load_evidence_json(builder)["attempt"])
            validate_builder(
                load_evidence_json(builder),
                builder,
                argparse.Namespace(
                    run_id=args.run_id,
                    attempt=attempt,
                    handoff=str(base_dir / "BUILDER_HANDOFF.md"),
                    q13_answers=str(base_dir / "13Q_ANSWERS.md"),
                    results=str(base_dir / "RESULTS.md"),
                ),
            )
        if evaluator.exists():
            attempt = int(load_evidence_json(evaluator)["attempt"])
            validate_evaluator(
                load_evidence_json(evaluator),
                evaluator,
                argparse.Namespace(
                    run_id=args.run_id,
                    attempt=attempt,
                    holdouts=str(Path(args.holdout_dir) / "D9_HOLDOUT_SCENARIOS.md"),
                    staging_root=str(Path(args.staging_dir)),
                ),
            )

        status_page = Path(args.status_page)
        if status_page.exists():
            runtime_state = current_status_field(Path(args.status_json), "state")
            governed_path = current_status_field(Path(args.status_json), "governed_path_intact")
            text = status_page.read_text(encoding="utf-8")
            if f"**Run ID:** {args.run_id}" not in text:
                raise ValueError(f"Status page does not reflect current run id {args.run_id}")
            if f"**Runtime State:** {runtime_state}" not in text:
                raise ValueError(f"Status page does not reflect runtime state {runtime_state}")
            if f"**Governed Path Intact:** {governed_path}" not in text:
                raise ValueError(f"Status page does not reflect governed path state {governed_path}")
        print("PASS: convergence valid")
        return 0
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


def main_preflight(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run preflight checks")
    parser.add_argument("--fmwk", required=True)
    parser.add_argument("--task-path", required=True)
    parser.add_argument("--role-registry", required=True)
    parser.add_argument("--artifact-registry", required=True)
    parser.add_argument("--prompt-registry", required=True)
    parser.add_argument("--builder-contract", required=True)
    parser.add_argument("--reviewer-contract", required=True)
    args = parser.parse_args(argv)
    required_files = [
        ROOT / "CLAUDE.md",
        ROOT / "AGENT_BOOTSTRAP.md",
        ROOT / args.role_registry,
        ROOT / args.artifact_registry,
        ROOT / args.prompt_registry,
        ROOT / args.builder_contract,
        ROOT / args.reviewer_contract,
        ROOT / args.task_path,
    ]
    for path in required_files:
        if not path.is_file():
            print(f"FAIL: Missing required file: {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
    for link_name in ("AGENTS.md", "GEMINI.md"):
        link_path = ROOT / link_name
        if not link_path.exists():
            link_path.symlink_to("CLAUDE.md")
    for agent_var in ("SPEC_AGENT", "BUILD_AGENT", "HOLDOUT_AGENT", "REVIEW_AGENT", "EVAL_AGENT"):
        backend = os.environ.get(agent_var, "")
        if backend in {"claude", "codex", "gemini"} and shutil.which(backend) is None:
            print(f"FAIL: Missing required agent CLI for {agent_var}={backend}", file=sys.stderr)
            return 1
        if backend == "mock" and not (ROOT / "sawmill/workers/mock_worker.py").is_file():
            print(f"FAIL: Missing required agent CLI for {agent_var}=mock", file=sys.stderr)
            return 1
    if _contracts.main([]) != 0:
        print("FAIL: factory contracts mismatch", file=sys.stderr)
        return 1
    print(f"PASS: Preflight passed for {args.fmwk}")
    return 0
