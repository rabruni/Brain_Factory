#!/usr/bin/env python3
"""Validate and export Sawmill prompt registry metadata."""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    print("FAIL: PyYAML is required to validate sawmill/PROMPT_REGISTRY.yaml", file=sys.stderr)
    raise SystemExit(1) from exc

REQUIRED_FIELDS = {
    "role",
    "prompt_file",
    "required_artifacts",
    "expected_artifacts",
    "freshness_policy",
    "retry_behavior",
}
VALID_RETRY_BEHAVIORS = {"none", "review_loop", "build_loop", "evaluation_loop", "maintenance"}
VALID_FRESHNESS_POLICIES = {"required", "allow_unchanged"}
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate sawmill prompt registry")
    parser.add_argument("--registry", default="sawmill/PROMPT_REGISTRY.yaml")
    parser.add_argument("--roles", default="sawmill/ROLE_REGISTRY.yaml")
    parser.add_argument("--artifacts", default="sawmill/ARTIFACT_REGISTRY.yaml")
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


def validate_registry(data: dict, roles_data: dict, artifacts_data: dict) -> None:
    prompts = data.get("prompts")
    if data.get("version") is None:
        raise ValueError("Missing top-level 'version'")
    if not isinstance(prompts, dict):
        raise ValueError("Top-level 'prompts' must be a mapping")

    known_roles = set(roles_data.get("roles", {}))
    known_artifacts = set(artifacts_data.get("artifacts", {}))
    errors: list[str] = []

    for prompt_key, metadata in prompts.items():
        if not KEY_PATTERN.fullmatch(prompt_key):
            errors.append(f"Prompt key '{prompt_key}' must match {KEY_PATTERN.pattern}")
        if not isinstance(metadata, dict):
            errors.append(f"Prompt '{prompt_key}' must map to an object")
            continue

        keys = set(metadata)
        missing = REQUIRED_FIELDS - keys
        extra = keys - REQUIRED_FIELDS
        if missing:
            errors.append(
                f"Prompt '{prompt_key}' is missing required fields: {', '.join(sorted(missing))}"
            )
        if extra:
            errors.append(
                f"Prompt '{prompt_key}' has unsupported fields: {', '.join(sorted(extra))}"
            )
        if missing or extra:
            continue

        role = metadata["role"]
        prompt_file = metadata["prompt_file"]
        required_artifacts = metadata["required_artifacts"]
        expected_artifacts = metadata["expected_artifacts"]
        freshness_policy = metadata["freshness_policy"]
        retry_behavior = metadata["retry_behavior"]

        if role not in known_roles:
            errors.append(f"Prompt '{prompt_key}' references unknown role '{role}'")

        if not isinstance(prompt_file, str) or not prompt_file:
            errors.append(f"Prompt '{prompt_key}' must define a non-empty prompt_file")
        elif not (Path.cwd() / prompt_file).is_file():
            errors.append(f"Prompt '{prompt_key}' references missing prompt_file: {prompt_file}")

        for field_name, artifact_ids in (
            ("required_artifacts", required_artifacts),
            ("expected_artifacts", expected_artifacts),
        ):
            if not isinstance(artifact_ids, list):
                errors.append(f"Prompt '{prompt_key}' field '{field_name}' must be a list")
                continue
            for artifact_id in artifact_ids:
                if artifact_id not in known_artifacts:
                    errors.append(
                        f"Prompt '{prompt_key}' references unknown artifact '{artifact_id}' in {field_name}"
                    )

        if retry_behavior not in VALID_RETRY_BEHAVIORS:
            errors.append(
                f"Prompt '{prompt_key}' has invalid retry_behavior '{retry_behavior}'"
            )
        if freshness_policy not in VALID_FRESHNESS_POLICIES:
            errors.append(
                f"Prompt '{prompt_key}' has invalid freshness_policy '{freshness_policy}'"
            )

    if errors:
        raise ValueError("\n".join(errors))


def build_shell_exports(data: dict) -> str:
    prompts = data["prompts"]
    lines = [f"ALL_PROMPT_KEYS={shlex.quote(' '.join(sorted(prompts)))}"]
    for prompt_key in sorted(prompts):
        metadata = prompts[prompt_key]
        prefix = f"PROMPT_{prompt_key.upper()}"
        lines.append(f"{prefix}_ROLE={shlex.quote(str(metadata['role']))}")
        lines.append(f"{prefix}_PROMPT_FILE={shlex.quote(str(metadata['prompt_file']))}")
        lines.append(
            f"{prefix}_REQUIRED_ARTIFACTS={shlex.quote(' '.join(metadata['required_artifacts']))}"
        )
        lines.append(
            f"{prefix}_EXPECTED_ARTIFACTS={shlex.quote(' '.join(metadata['expected_artifacts']))}"
        )
        lines.append(
            f"{prefix}_FRESHNESS_POLICY={shlex.quote(str(metadata['freshness_policy']))}"
        )
        lines.append(
            f"{prefix}_RETRY_BEHAVIOR={shlex.quote(str(metadata['retry_behavior']))}"
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        data = load_yaml(Path(args.registry))
        roles_data = load_yaml(Path(args.roles))
        artifacts_data = load_yaml(Path(args.artifacts))
        validate_registry(data, roles_data, artifacts_data)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.shell_exports:
        print(build_shell_exports(data))
    else:
        print(f"PASS: prompt registry valid ({args.registry})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
