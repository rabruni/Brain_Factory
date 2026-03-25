"""Registry loading, validation, export, and prompt rendering."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    print("FAIL: PyYAML is required for Sawmill registry operations", file=sys.stderr)
    raise SystemExit(1) from exc

ROLE_REQUIRED_FIELDS = {
    "role_file",
    "execution_scope",
    "backend",
    "model",
    "effort",
    "allowed_backends",
    "env_override",
}
SUPPORTED_BACKENDS = {"claude", "codex", "gemini", "mock"}
VALID_EXECUTION_SCOPES = {"orchestrator", "worker"}
VALID_EFFORTS = {"default", "high", "max"}
REQUIRED_RUNTIME_ROLES = (
    "spec-agent",
    "holdout-agent",
    "builder",
    "reviewer",
    "evaluator",
    "auditor",
)
SHELL_PREFIXES = {
    "orchestrator": "ORCHESTRATOR",
    "spec-agent": "SPEC",
    "holdout-agent": "HOLDOUT",
    "builder": "BUILD",
    "reviewer": "REVIEW",
    "evaluator": "EVAL",
    "auditor": "AUDIT",
}

ARTIFACT_REQUIRED_FIELDS = {
    "owner_role",
    "path_template",
    "stage",
    "required",
    "artifact_kind",
    "standard_ref",
}
VALID_KINDS = {"file", "dir"}
VALID_STAGES = {"orchestrator", "A", "B", "C", "D", "E", "portal", "audit"}
ARTIFACT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

PROMPT_REQUIRED_FIELDS = {
    "role",
    "prompt_file",
    "required_artifacts",
    "expected_artifacts",
    "freshness_policy",
    "retry_behavior",
}
VALID_RETRY_BEHAVIORS = {"none", "review_loop", "build_loop", "evaluation_loop", "maintenance"}
VALID_FRESHNESS_POLICIES = {"required", "allow_unchanged"}
PROMPT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

PIPELINE_STAGES = ("A", "B", "C", "D", "E")
PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
PROMPT_CONTRACT_VERSION_RE = re.compile(
    r"(?:\*\*version\*\*|version):\s*([0-9a-z._-]+)", re.IGNORECASE
)


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


def load_role_registry(path: Path) -> dict:
    data = load_yaml(path)
    version = data.get("version")
    roles = data.get("roles")
    if version is None:
        raise ValueError(f"Missing top-level 'version' in {path}")
    if not isinstance(roles, dict):
        raise ValueError(f"Top-level 'roles' must be a mapping in {path}")
    return data


def validate_role_registry(data: dict, registry_path: Path) -> None:
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
        missing = ROLE_REQUIRED_FIELDS - keys
        extra = keys - ROLE_REQUIRED_FIELDS
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
        backend = metadata["backend"]
        model = metadata["model"]
        effort = metadata["effort"]
        allowed_backends = metadata["allowed_backends"]
        env_override = metadata["env_override"]

        if execution_scope not in VALID_EXECUTION_SCOPES:
            errors.append(f"Role '{role_name}' has invalid execution_scope '{execution_scope}'")
        if not isinstance(model, str) or not model:
            errors.append(f"Role '{role_name}' must define a non-empty model")
        if effort not in VALID_EFFORTS:
            errors.append(f"Role '{role_name}' has invalid effort '{effort}'")

        if not isinstance(allowed_backends, list) or not allowed_backends:
            errors.append(f"Role '{role_name}' must define a non-empty allowed_backends list")
        else:
            invalid_backends = [
                backend for backend in allowed_backends if backend not in SUPPORTED_BACKENDS
            ]
            if invalid_backends:
                errors.append(
                    f"Role '{role_name}' has unsupported backends: {', '.join(invalid_backends)}"
                )
            if backend not in allowed_backends:
                errors.append(
                    f"Role '{role_name}' backend '{backend}' is not in allowed_backends"
                )

        if not isinstance(role_file, str) or not role_file:
            errors.append(f"Role '{role_name}' must define a non-empty role_file")
        else:
            role_path = Path.cwd() / role_file
            if not role_path.is_file():
                errors.append(f"Role '{role_name}' references missing role_file: {role_file}")

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


def build_role_shell_exports(data: dict) -> str:
    roles = data["roles"]
    lines: list[str] = []

    for role_name, prefix in SHELL_PREFIXES.items():
        metadata = roles.get(role_name)
        if metadata is None:
            continue
        lines.append(f"{prefix}_ROLE_FILE={shlex.quote(str(metadata['role_file']))}")
        lines.append(
            f"{prefix}_EXECUTION_SCOPE={shlex.quote(str(metadata['execution_scope']))}"
        )
        lines.append(f"{prefix}_BACKEND={shlex.quote(str(metadata['backend']))}")
        lines.append(f"{prefix}_MODEL={shlex.quote(str(metadata['model']))}")
        lines.append(f"{prefix}_EFFORT={shlex.quote(str(metadata['effort']))}")
        lines.append(
            f"{prefix}_ALLOWED_BACKENDS={shlex.quote(' '.join(metadata['allowed_backends']))}"
        )
        lines.append(f"{prefix}_ENV_OVERRIDE={shlex.quote(str(metadata['env_override']))}")

    return "\n".join(lines)


def load_artifact_registry(path: Path) -> dict:
    data = load_yaml(path)
    artifacts = data.get("artifacts")
    if data.get("version") is None:
        raise ValueError("Missing top-level 'version'")
    if not isinstance(artifacts, dict):
        raise ValueError("Top-level 'artifacts' must be a mapping")
    return data


def validate_artifact_registry(data: dict, roles_data: dict) -> None:
    artifacts = data["artifacts"]
    known_roles = set(roles_data.get("roles", {}))
    errors: list[str] = []

    for artifact_id, metadata in artifacts.items():
        if not ARTIFACT_ID_PATTERN.fullmatch(artifact_id):
            errors.append(f"Artifact id '{artifact_id}' must match {ARTIFACT_ID_PATTERN.pattern}")
        if not isinstance(metadata, dict):
            errors.append(f"Artifact '{artifact_id}' must map to an object")
            continue

        keys = set(metadata)
        missing = ARTIFACT_REQUIRED_FIELDS - keys
        extra = keys - ARTIFACT_REQUIRED_FIELDS
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
            elif not (Path.cwd() / standard_ref).exists():
                errors.append(
                    f"Artifact '{artifact_id}' references missing standard_ref: {standard_ref}"
                )

    if errors:
        raise ValueError("\n".join(errors))


def build_artifact_shell_exports(data: dict) -> str:
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


def load_prompt_registry(path: Path) -> dict:
    data = load_yaml(path)
    prompts = data.get("prompts")
    if data.get("version") is None:
        raise ValueError("Missing top-level 'version'")
    if not isinstance(prompts, dict):
        raise ValueError("Top-level 'prompts' must be a mapping")
    return data


def validate_prompt_registry(data: dict, roles_data: dict, artifacts_data: dict) -> None:
    prompts = data["prompts"]
    known_roles = set(roles_data.get("roles", {}))
    known_artifacts = set(artifacts_data.get("artifacts", {}))
    errors: list[str] = []

    for prompt_key, metadata in prompts.items():
        if not PROMPT_KEY_PATTERN.fullmatch(prompt_key):
            errors.append(f"Prompt key '{prompt_key}' must match {PROMPT_KEY_PATTERN.pattern}")
        if not isinstance(metadata, dict):
            errors.append(f"Prompt '{prompt_key}' must map to an object")
            continue

        keys = set(metadata)
        missing = PROMPT_REQUIRED_FIELDS - keys
        extra = keys - PROMPT_REQUIRED_FIELDS
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
            errors.append(f"Prompt '{prompt_key}' has invalid retry_behavior '{retry_behavior}'")
        if freshness_policy not in VALID_FRESHNESS_POLICIES:
            errors.append(
                f"Prompt '{prompt_key}' has invalid freshness_policy '{freshness_policy}'"
            )

    if errors:
        raise ValueError("\n".join(errors))


def build_prompt_shell_exports(data: dict) -> str:
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


def build_stage_maps(data: dict) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    artifacts = data["artifacts"]
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


def build_stage_shell_exports(
    stage_all: dict[str, list[str]],
    stage_required: dict[str, list[str]],
    invalidate_from: dict[str, list[str]],
) -> str:
    lines: list[str] = []
    for stage in PIPELINE_STAGES:
        lines.append(f"STAGE_{stage}_ALL_ARTIFACTS={shlex.quote(' '.join(stage_all[stage]))}")
        lines.append(
            f"STAGE_{stage}_REQUIRED_ARTIFACTS={shlex.quote(' '.join(stage_required[stage]))}"
        )
        lines.append(
            f"INVALIDATE_FROM_{stage}_ARTIFACTS={shlex.quote(' '.join(invalidate_from[stage]))}"
        )
    return "\n".join(lines)


def render_prompt(template_path: Path, env_vars: dict[str, str] | None = None) -> str:
    try:
        content = template_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Prompt template not found: {template_path}") from exc

    env = os.environ if env_vars is None else env_vars
    missing: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in env:
            missing.add(key)
            return match.group(0)
        return env[key]

    rendered = PLACEHOLDER.sub(replace, content)
    if missing:
        raise ValueError(
            f"Missing prompt variables for {template_path}: {', '.join(sorted(missing))}"
        )
    return rendered


def extract_prompt_contract_version(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Prompt contract file not found: {path}") from exc
    for line in text.splitlines():
        match = PROMPT_CONTRACT_VERSION_RE.search(line)
        if match:
            return match.group(1).lower()
    raise ValueError(f"Unable to determine prompt contract version from {path}")


def main_validate_role_registry(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate sawmill role registry")
    parser.add_argument("--registry", default="sawmill/ROLE_REGISTRY.yaml")
    parser.add_argument("--shell-exports", action="store_true")
    args = parser.parse_args(argv)
    registry_path = Path(args.registry)
    try:
        data = load_role_registry(registry_path)
        validate_role_registry(data, registry_path)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.shell_exports:
        print(build_role_shell_exports(data))
    else:
        print(f"PASS: role registry valid ({registry_path})")
    return 0


def main_validate_artifact_registry(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate sawmill artifact registry")
    parser.add_argument("--registry", default="sawmill/ARTIFACT_REGISTRY.yaml")
    parser.add_argument("--roles", default="sawmill/ROLE_REGISTRY.yaml")
    parser.add_argument("--shell-exports", action="store_true")
    args = parser.parse_args(argv)
    registry_path = Path(args.registry)
    roles_path = Path(args.roles)
    try:
        data = load_artifact_registry(registry_path)
        roles_data = load_role_registry(roles_path)
        validate_artifact_registry(data, roles_data)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.shell_exports:
        print(build_artifact_shell_exports(data))
    else:
        print(f"PASS: artifact registry valid ({registry_path})")
    return 0


def main_validate_prompt_registry(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate sawmill prompt registry")
    parser.add_argument("--registry", default="sawmill/PROMPT_REGISTRY.yaml")
    parser.add_argument("--roles", default="sawmill/ROLE_REGISTRY.yaml")
    parser.add_argument("--artifacts", default="sawmill/ARTIFACT_REGISTRY.yaml")
    parser.add_argument("--shell-exports", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = load_prompt_registry(Path(args.registry))
        roles_data = load_role_registry(Path(args.roles))
        artifacts_data = load_artifact_registry(Path(args.artifacts))
        validate_prompt_registry(data, roles_data, artifacts_data)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.shell_exports:
        print(build_prompt_shell_exports(data))
    else:
        print(f"PASS: prompt registry valid ({args.registry})")
    return 0


def main_resolve_stage_artifacts(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve Sawmill stage artifact sets")
    parser.add_argument("--registry", default="sawmill/ARTIFACT_REGISTRY.yaml")
    parser.add_argument("--shell-exports", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = load_artifact_registry(Path(args.registry))
        stage_all, stage_required, invalidate_from = build_stage_maps(data)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.shell_exports:
        print(build_stage_shell_exports(stage_all, stage_required, invalidate_from))
    else:
        print(f"PASS: stage artifact map resolved ({args.registry})")
    return 0


def main_render_prompt(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a Sawmill prompt template")
    parser.add_argument("template", help="Path to the prompt template file")
    args = parser.parse_args(argv)
    template_path = Path(args.template)
    try:
        print(render_prompt(template_path), end="")
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0
