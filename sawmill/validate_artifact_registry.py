#!/usr/bin/env python3
"""Validate and export Sawmill artifact registry metadata."""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    print("FAIL: PyYAML is required to validate sawmill/ARTIFACT_REGISTRY.yaml", file=sys.stderr)
    raise SystemExit(1) from exc

REQUIRED_FIELDS = {
    "owner_role",
    "path_template",
    "stage",
    "required",
    "artifact_kind",
    "standard_ref",
}
VALID_KINDS = {"file", "dir"}
VALID_STAGES = {"orchestrator", "A", "B", "C", "D", "E", "portal", "audit"}
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate sawmill artifact registry")
    parser.add_argument("--registry", default="sawmill/ARTIFACT_REGISTRY.yaml")
    parser.add_argument("--roles", default="sawmill/ROLE_REGISTRY.yaml")
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


def validate_registry(data: dict, roles_data: dict) -> None:
    artifacts = data.get("artifacts")
    if data.get("version") is None:
        raise ValueError("Missing top-level 'version'")
    if not isinstance(artifacts, dict):
        raise ValueError("Top-level 'artifacts' must be a mapping")

    known_roles = set(roles_data.get("roles", {}))
    errors: list[str] = []

    for artifact_id, metadata in artifacts.items():
        if not ID_PATTERN.fullmatch(artifact_id):
            errors.append(f"Artifact id '{artifact_id}' must match {ID_PATTERN.pattern}")
        if not isinstance(metadata, dict):
            errors.append(f"Artifact '{artifact_id}' must map to an object")
            continue

        keys = set(metadata)
        missing = REQUIRED_FIELDS - keys
        extra = keys - REQUIRED_FIELDS
        if missing:
            errors.append(
                f"Artifact '{artifact_id}' is missing required fields: {', '.join(sorted(missing))}"
            )
        if extra:
            errors.append(
                f"Artifact '{artifact_id}' has unsupported fields: {', '.join(sorted(extra))}"
            )
        if missing or extra:
            continue

        owner_role = metadata["owner_role"]
        path_template = metadata["path_template"]
        stage = metadata["stage"]
        required = metadata["required"]
        artifact_kind = metadata["artifact_kind"]
        standard_ref = metadata["standard_ref"]

        if owner_role not in known_roles:
            errors.append(f"Artifact '{artifact_id}' references unknown owner_role '{owner_role}'")

        if not isinstance(path_template, str) or not path_template:
            errors.append(f"Artifact '{artifact_id}' must define a non-empty path_template")
        elif "{FMWK}" not in path_template and "/" not in path_template:
            errors.append(f"Artifact '{artifact_id}' path_template looks invalid: {path_template}")

        if stage not in VALID_STAGES:
            errors.append(f"Artifact '{artifact_id}' has invalid stage '{stage}'")

        if not isinstance(required, bool):
            errors.append(f"Artifact '{artifact_id}' required must be a boolean")

        if artifact_kind not in VALID_KINDS:
            errors.append(f"Artifact '{artifact_id}' has invalid artifact_kind '{artifact_kind}'")

        if standard_ref not in (None, ""):
            if not isinstance(standard_ref, str):
                errors.append(f"Artifact '{artifact_id}' standard_ref must be a string or null")
            else:
                if not (Path.cwd() / standard_ref).exists():
                    errors.append(
                        f"Artifact '{artifact_id}' references missing standard_ref: {standard_ref}"
                    )

    if errors:
        raise ValueError("\n".join(errors))


def build_shell_exports(data: dict) -> str:
    artifacts = data["artifacts"]
    lines = [f"ALL_ARTIFACT_IDS={shlex.quote(' '.join(sorted(artifacts)))}"]
    for artifact_id in sorted(artifacts):
        metadata = artifacts[artifact_id]
        prefix = f"ARTIFACT_{artifact_id.upper()}"
        lines.append(f"{prefix}_OWNER_ROLE={shlex.quote(str(metadata['owner_role']))}")
        lines.append(f"{prefix}_PATH_TEMPLATE={shlex.quote(str(metadata['path_template']))}")
        lines.append(f"{prefix}_STAGE={shlex.quote(str(metadata['stage']))}")
        lines.append(f"{prefix}_REQUIRED={shlex.quote(str(metadata['required']).lower())}")
        lines.append(f"{prefix}_KIND={shlex.quote(str(metadata['artifact_kind']))}")
        standard_ref = metadata["standard_ref"] or ""
        lines.append(f"{prefix}_STANDARD_REF={shlex.quote(str(standard_ref))}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    registry_path = Path(args.registry)
    roles_path = Path(args.roles)
    try:
        data = load_yaml(registry_path)
        roles_data = load_yaml(roles_path)
        validate_registry(data, roles_data)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.shell_exports:
        print(build_shell_exports(data))
    else:
        print(f"PASS: artifact registry valid ({registry_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
