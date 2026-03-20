"""CLI entrypoint for sawmill.registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._core import (
    build_artifact_shell_exports,
    build_prompt_shell_exports,
    build_role_shell_exports,
    build_stage_maps,
    build_stage_shell_exports,
    extract_prompt_contract_version,
    load_artifact_registry,
    load_prompt_registry,
    load_role_registry,
    render_prompt,
    validate_artifact_registry,
    validate_prompt_registry,
    validate_role_registry,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sawmill registry CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("kind", choices=("roles", "artifacts", "prompts"))
    validate_parser.add_argument("--registry")
    validate_parser.add_argument("--roles", default="sawmill/ROLE_REGISTRY.yaml")
    validate_parser.add_argument("--artifacts", default="sawmill/ARTIFACT_REGISTRY.yaml")

    exports_parser = subparsers.add_parser("shell-exports")
    exports_parser.add_argument("kind", choices=("roles", "artifacts", "prompts", "stages"))
    exports_parser.add_argument("--registry")
    exports_parser.add_argument("--roles", default="sawmill/ROLE_REGISTRY.yaml")
    exports_parser.add_argument("--artifacts", default="sawmill/ARTIFACT_REGISTRY.yaml")

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("template_path")

    versions_parser = subparsers.add_parser("prompt-contract-versions")
    versions_parser.add_argument("--builder", required=True)
    versions_parser.add_argument("--reviewer", required=True)

    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            if args.kind == "roles":
                registry = Path(args.registry or "sawmill/ROLE_REGISTRY.yaml")
                data = load_role_registry(registry)
                validate_role_registry(data, registry)
                print(f"PASS: role registry valid ({registry})")
            elif args.kind == "artifacts":
                registry = Path(args.registry or "sawmill/ARTIFACT_REGISTRY.yaml")
                data = load_artifact_registry(registry)
                roles_data = load_role_registry(Path(args.roles))
                validate_artifact_registry(data, roles_data)
                print(f"PASS: artifact registry valid ({registry})")
            else:
                registry = Path(args.registry or "sawmill/PROMPT_REGISTRY.yaml")
                data = load_prompt_registry(registry)
                roles_data = load_role_registry(Path(args.roles))
                artifacts_data = load_artifact_registry(Path(args.artifacts))
                validate_prompt_registry(data, roles_data, artifacts_data)
                print(f"PASS: prompt registry valid ({registry})")
        elif args.command == "shell-exports":
            if args.kind == "roles":
                registry = Path(args.registry or "sawmill/ROLE_REGISTRY.yaml")
                data = load_role_registry(registry)
                validate_role_registry(data, registry)
                print(build_role_shell_exports(data))
            elif args.kind == "artifacts":
                registry = Path(args.registry or "sawmill/ARTIFACT_REGISTRY.yaml")
                data = load_artifact_registry(registry)
                roles_data = load_role_registry(Path(args.roles))
                validate_artifact_registry(data, roles_data)
                print(build_artifact_shell_exports(data))
            elif args.kind == "prompts":
                registry = Path(args.registry or "sawmill/PROMPT_REGISTRY.yaml")
                data = load_prompt_registry(registry)
                roles_data = load_role_registry(Path(args.roles))
                artifacts_data = load_artifact_registry(Path(args.artifacts))
                validate_prompt_registry(data, roles_data, artifacts_data)
                print(build_prompt_shell_exports(data))
            else:
                registry = Path(args.registry or "sawmill/ARTIFACT_REGISTRY.yaml")
                data = load_artifact_registry(registry)
                stage_all, stage_required, invalidate_from = build_stage_maps(data)
                print(build_stage_shell_exports(stage_all, stage_required, invalidate_from))
        elif args.command == "render":
            print(render_prompt(Path(args.template_path)), end="")
        else:
            print(
                f"BUILDER_PROMPT_CONTRACT_VERSION={extract_prompt_contract_version(Path(args.builder))}"
            )
            print(
                f"REVIEWER_PROMPT_CONTRACT_VERSION={extract_prompt_contract_version(Path(args.reviewer))}"
            )
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
