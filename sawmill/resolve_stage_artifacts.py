#!/usr/bin/env python3
"""Resolve stage-owned artifact sets from the artifact registry."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    print("FAIL: PyYAML is required to resolve sawmill/ARTIFACT_REGISTRY.yaml", file=sys.stderr)
    raise SystemExit(1) from exc

PIPELINE_STAGES = ("A", "B", "C", "D", "E")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve Sawmill stage artifact sets")
    parser.add_argument("--registry", default="sawmill/ARTIFACT_REGISTRY.yaml")
    parser.add_argument("--shell-exports", action="store_true")
    return parser.parse_args()


def load_yaml(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Registry file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Registry root must be a mapping: {path}")
    return data


def build_stage_maps(data: dict) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    artifacts = data.get("artifacts")
    if data.get("version") is None:
        raise ValueError("Missing top-level 'version'")
    if not isinstance(artifacts, dict):
        raise ValueError("Top-level 'artifacts' must be a mapping")

    stage_all: dict[str, list[str]] = {stage: [] for stage in PIPELINE_STAGES}
    stage_required: dict[str, list[str]] = {stage: [] for stage in PIPELINE_STAGES}

    for artifact_id in sorted(artifacts):
        metadata = artifacts[artifact_id]
        if not isinstance(metadata, dict):
            raise ValueError(f"Artifact '{artifact_id}' must map to an object")

        stage = metadata.get("stage")
        if stage not in PIPELINE_STAGES:
            continue

        stage_all[stage].append(artifact_id)
        if metadata.get("required") is True:
            stage_required[stage].append(artifact_id)

    invalidate_from: dict[str, list[str]] = {}
    for start_stage in PIPELINE_STAGES:
        start_index = PIPELINE_STAGES.index(start_stage)
        invalidate_ids: list[str] = []
        for stage in PIPELINE_STAGES[start_index:]:
            invalidate_ids.extend(stage_all[stage])
        invalidate_from[start_stage] = invalidate_ids

    return stage_all, stage_required, invalidate_from


def build_shell_exports(
    stage_all: dict[str, list[str]],
    stage_required: dict[str, list[str]],
    invalidate_from: dict[str, list[str]],
) -> str:
    lines: list[str] = []
    for stage in PIPELINE_STAGES:
        lines.append(
            f"STAGE_{stage}_ALL_ARTIFACTS={shlex.quote(' '.join(stage_all[stage]))}"
        )
        lines.append(
            f"STAGE_{stage}_REQUIRED_ARTIFACTS={shlex.quote(' '.join(stage_required[stage]))}"
        )
        lines.append(
            f"INVALIDATE_FROM_{stage}_ARTIFACTS={shlex.quote(' '.join(invalidate_from[stage]))}"
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        data = load_yaml(Path(args.registry))
        stage_all, stage_required, invalidate_from = build_stage_maps(data)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.shell_exports:
        print(build_shell_exports(stage_all, stage_required, invalidate_from))
    else:
        print(f"PASS: stage artifact map resolved ({args.registry})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
