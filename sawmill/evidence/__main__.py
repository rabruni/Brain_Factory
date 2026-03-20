"""CLI entrypoint for sawmill.evidence."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ._core import (
    dir_sha256,
    extract_version_evidence,
    file_sha256,
    load_json,
    parse_evaluation_verdict,
    parse_review_verdict,
    validate_builder,
    validate_evaluator,
    validate_reviewer,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sawmill evidence CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--kind", required=True, choices=("builder", "reviewer", "evaluator"))
    validate_parser.add_argument("--artifact", required=True)
    validate_parser.add_argument("--run-id", required=True)
    validate_parser.add_argument("--attempt", type=int, required=True)
    validate_parser.add_argument("--handoff")
    validate_parser.add_argument("--q13-answers")
    validate_parser.add_argument("--results")
    validate_parser.add_argument("--holdouts")
    validate_parser.add_argument("--staging-root")

    hash_parser = subparsers.add_parser("hash")
    hash_parser.add_argument("kind", choices=("file", "dir"))
    hash_parser.add_argument("path")

    verdict_parser = subparsers.add_parser("verdict")
    verdict_parser.add_argument("kind", choices=("review", "eval"))
    verdict_parser.add_argument("path")

    version_parser = subparsers.add_parser("version")
    version_parser.add_argument("path")
    version_parser.add_argument("label")

    export_parser = subparsers.add_parser("export-hashes")
    export_parser.add_argument("--step", required=True)

    suite_parser = subparsers.add_parser("validate-suite")
    suite_parser.add_argument("--run-id", required=True)
    suite_parser.add_argument("--attempt", type=int, required=True)
    suite_parser.add_argument("--base-dir", required=True)
    suite_parser.add_argument("--holdout-dir")
    suite_parser.add_argument("--staging-dir")

    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            artifact_path = Path(args.artifact)
            data = load_json(artifact_path)
            if args.kind == "builder":
                validate_builder(data, artifact_path, args)
            elif args.kind == "reviewer":
                validate_reviewer(data, artifact_path, args)
            else:
                validate_evaluator(data, artifact_path, args)
            print(f"PASS: {args.kind} evidence valid ({artifact_path})")
        elif args.command == "hash":
            path = Path(args.path)
            print(file_sha256(path) if args.kind == "file" else dir_sha256(path))
        elif args.command == "verdict":
            path = Path(args.path)
            print(parse_review_verdict(path) if args.kind == "review" else parse_evaluation_verdict(path))
        elif args.command == "version":
            print(extract_version_evidence(Path(args.path), args.label))
        elif args.command == "export-hashes":
            if args.step == "turn_d_review":
                print(f"Q13_ANSWERS_HASH={file_sha256(Path(os.environ['Q13_ANSWERS_PATH']))}")
            elif args.step == "turn_d_build":
                print(f"HANDOFF_HASH={file_sha256(Path(os.environ['BUILDER_HANDOFF_PATH']))}")
                print(f"Q13_ANSWERS_HASH={file_sha256(Path(os.environ['Q13_ANSWERS_PATH']))}")
            elif args.step == "turn_e_eval":
                print(f"HOLDOUT_HASH={file_sha256(Path(os.environ['D9_HOLDOUT_SCENARIOS_PATH']))}")
                print(f"STAGING_HASH={dir_sha256(Path(os.environ['STAGING_ROOT_PATH']))}")
            else:
                raise ValueError(f"Unsupported export-hashes step: {args.step}")
        else:
            base_dir = Path(args.base_dir)
            holdout_dir = Path(args.holdout_dir) if args.holdout_dir else None
            staging_dir = Path(args.staging_dir) if args.staging_dir else None
            builder = base_dir / "builder_evidence.json"
            reviewer = base_dir / "reviewer_evidence.json"
            evaluator = base_dir / "evaluator_evidence.json"
            if builder.exists():
                validate_builder(
                    load_json(builder),
                    builder,
                    argparse.Namespace(
                        run_id=args.run_id,
                        attempt=args.attempt,
                        handoff=str(base_dir / "BUILDER_HANDOFF.md"),
                        q13_answers=str(base_dir / "13Q_ANSWERS.md"),
                        results=str(base_dir / "RESULTS.md"),
                    ),
                )
            if reviewer.exists():
                validate_reviewer(
                    load_json(reviewer),
                    reviewer,
                    argparse.Namespace(
                        run_id=args.run_id,
                        attempt=args.attempt,
                        q13_answers=str(base_dir / "13Q_ANSWERS.md"),
                    ),
                )
            if evaluator.exists():
                if holdout_dir is None or staging_dir is None:
                    raise ValueError("validate-suite requires --holdout-dir and --staging-dir when evaluator evidence exists")
                validate_evaluator(
                    load_json(evaluator),
                    evaluator,
                    argparse.Namespace(
                        run_id=args.run_id,
                        attempt=args.attempt,
                        holdouts=str(holdout_dir / "D9_HOLDOUT_SCENARIOS.md"),
                        staging_root=str(staging_dir),
                    ),
                )
            print("PASS: evidence suite valid")
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
