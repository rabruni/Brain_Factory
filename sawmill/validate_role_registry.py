#!/usr/bin/env python3
"""Validate and export Sawmill role registry metadata."""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment error
    print("FAIL: PyYAML is required to validate sawmill/ROLE_REGISTRY.yaml", file=sys.stderr)
    raise SystemExit(1) from exc

REQUIRED_FIELDS = {
    "role_file",
    "execution_scope",
    "default_backend",
    "model_policy",
    "allowed_backends",
    "env_override",
}
SUPPORTED_BACKENDS = {"claude", "codex", "gemini"}
VALID_EXECUTION_SCOPES = {"orchestrator", "worker"}
VALID_MODEL_POLICIES = {"default", "max_capability"}
REQUIRED_RUNTIME_ROLES = (
    "spec-agent",
    "holdout-agent",
    "builder",
    "reviewer",
    "evaluator",
    "auditor",
    "portal-steward",
)
SHELL_PREFIXES = {
    "orchestrator": "ORCHESTRATOR",
    "spec-agent": "SPEC",
    "holdout-agent": "HOLDOUT",
    "builder": "BUILD",
    "reviewer": "REVIEW",
    "evaluator": "EVAL",
    "auditor": "AUDIT",
    "portal-steward": "PORTAL",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate sawmill role registry")
    parser.add_argument(
        "--registry",
        default="sawmill/ROLE_REGISTRY.yaml",
        help="Path to the role registry YAML file",
    )
    parser.add_argument(
        "--shell-exports",
        action="store_true",
        help="Print shell-safe exports for known roles after validation",
    )
    return parser.parse_args()


def load_registry(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Registry file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Registry root must be a mapping: {path}")

    version = data.get("version")
    roles = data.get("roles")

    if version is None:
        raise ValueError(f"Missing top-level 'version' in {path}")
    if not isinstance(roles, dict):
        raise ValueError(f"Top-level 'roles' must be a mapping in {path}")

    return data


def validate_registry(data: dict, registry_path: Path) -> None:
    roles = data["roles"]
    errors: list[str] = []
    seen_env_overrides: dict[str, str] = {}

    for role_name in REQUIRED_RUNTIME_ROLES:
        if role_name not in roles:
            errors.append(f"Missing required runtime role: {role_name}")

    for role_name, metadata in roles.items():
        if not isinstance(metadata, dict):
            errors.append(f"Role '{role_name}' must map to an object")
            continue

        keys = set(metadata)
        missing = REQUIRED_FIELDS - keys
        extra = keys - REQUIRED_FIELDS
        if missing:
            errors.append(
                f"Role '{role_name}' is missing required fields: {', '.join(sorted(missing))}"
            )
        if extra:
            errors.append(
                f"Role '{role_name}' has unsupported fields: {', '.join(sorted(extra))}"
            )
        if missing or extra:
            continue

        role_file = metadata["role_file"]
        execution_scope = metadata["execution_scope"]
        default_backend = metadata["default_backend"]
        model_policy = metadata["model_policy"]
        allowed_backends = metadata["allowed_backends"]
        env_override = metadata["env_override"]

        if execution_scope not in VALID_EXECUTION_SCOPES:
            errors.append(
                f"Role '{role_name}' has invalid execution_scope '{execution_scope}'"
            )
        if model_policy not in VALID_MODEL_POLICIES:
            errors.append(
                f"Role '{role_name}' has invalid model_policy '{model_policy}'"
            )

        if not isinstance(allowed_backends, list) or not allowed_backends:
            errors.append(f"Role '{role_name}' must define a non-empty allowed_backends list")
        else:
            invalid_backends = [
                backend
                for backend in allowed_backends
                if backend not in SUPPORTED_BACKENDS
            ]
            if invalid_backends:
                errors.append(
                    f"Role '{role_name}' has unsupported backends: {', '.join(invalid_backends)}"
                )
            if default_backend not in allowed_backends:
                errors.append(
                    f"Role '{role_name}' default_backend '{default_backend}' is not in allowed_backends"
                )

        if not isinstance(role_file, str) or not role_file:
            errors.append(f"Role '{role_name}' must define a non-empty role_file")
        else:
            role_path = Path.cwd() / role_file
            if not role_path.is_file():
                errors.append(
                    f"Role '{role_name}' references missing role_file: {role_file}"
                )

        if not isinstance(env_override, str) or not env_override:
            errors.append(f"Role '{role_name}' must define a non-empty env_override")
        else:
            prior_role = seen_env_overrides.get(env_override)
            if prior_role is not None:
                errors.append(
                    f"Role '{role_name}' reuses env_override '{env_override}' already claimed by '{prior_role}'"
                )
            else:
                seen_env_overrides[env_override] = role_name

    if errors:
        raise ValueError("\n".join(errors))


def build_shell_exports(data: dict) -> str:
    roles = data["roles"]
    lines: list[str] = []

    for role_name, prefix in SHELL_PREFIXES.items():
        metadata = roles.get(role_name)
        if metadata is None:
            continue

        lines.append(
            f"{prefix}_ROLE_FILE={shlex.quote(str(metadata['role_file']))}"
        )
        lines.append(
            f"{prefix}_EXECUTION_SCOPE={shlex.quote(str(metadata['execution_scope']))}"
        )
        lines.append(
            f"{prefix}_DEFAULT_BACKEND={shlex.quote(str(metadata['default_backend']))}"
        )
        lines.append(
            f"{prefix}_MODEL_POLICY={shlex.quote(str(metadata['model_policy']))}"
        )
        lines.append(
            f"{prefix}_ALLOWED_BACKENDS={shlex.quote(' '.join(metadata['allowed_backends']))}"
        )
        lines.append(
            f"{prefix}_ENV_OVERRIDE={shlex.quote(str(metadata['env_override']))}"
        )

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    registry_path = Path(args.registry)

    try:
        data = load_registry(registry_path)
        validate_registry(data, registry_path)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.shell_exports:
        print(build_shell_exports(data))
    else:
        print(f"PASS: role registry valid ({registry_path})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
