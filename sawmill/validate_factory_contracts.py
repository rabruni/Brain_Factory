#!/usr/bin/env python3
"""Validate cross-layer factory artifact contracts before runtime."""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    print("FAIL: PyYAML is required to validate factory contracts", file=sys.stderr)
    raise SystemExit(1) from exc


COVERED_ROLES = (
    "spec-agent",
    "holdout-agent",
    "builder",
    "reviewer",
    "evaluator",
    "portal-steward",
    "auditor",
)

ROLE_FILE_BY_ROLE = {
    "spec-agent": ".claude/agents/spec-agent.md",
    "holdout-agent": ".claude/agents/holdout-agent.md",
    "builder": ".claude/agents/builder.md",
    "reviewer": ".claude/agents/reviewer.md",
    "evaluator": ".claude/agents/evaluator.md",
    "portal-steward": ".claude/agents/portal-steward.md",
    "auditor": ".claude/agents/auditor.md",
}

INTERNAL_GUARD_PATTERNS = {
    "orchestrator": {"sawmill/.active-role"},
    "portal-steward": {"docs/*", "mkdocs.yml", "catalog-info.yaml"},
    "auditor": {"sawmill/*/CANARY_AUDIT.md"},
}

OUTPUT_SECTION_RE = re.compile(r"^## Declared Output Artifacts\s*$", re.MULTILINE)
OUTPUT_LINE_RE = re.compile(r"^- `([a-z][a-z0-9_]*)` -> `([^`]+)`\s*$")
PROMPT_STEP_RE = re.compile(r"validate_prompt_step_success\s+([a-z0-9_]+)")
LAUNCH_BACKGROUND_RE = re.compile(r'launch_prompt_background\s+"[^"]+"\s+"[^"]+"\s+([a-z0-9_]+)\s+')
ARTIFACT_PATH_RE = re.compile(r"artifact_path\s+([a-z][a-z0-9_]*)")
EVIDENCE_ARTIFACT_RE = re.compile(r"validate_evidence_artifact\s+([a-z-]+)\s+([a-z][a-z0-9_]*)")
CASE_ROLE_RE = re.compile(r"^\s*([a-z-]+)\)\s*$")
GUARD_PATTERN_RE = re.compile(r'\[\[\s+"\$path"\s+==\s+([^\s]+)\s+\]\]')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Sawmill factory contracts")
    parser.add_argument("--roles", default="sawmill/ROLE_REGISTRY.yaml")
    parser.add_argument("--artifacts", default="sawmill/ARTIFACT_REGISTRY.yaml")
    parser.add_argument("--prompts", default="sawmill/PROMPT_REGISTRY.yaml")
    parser.add_argument("--guard", default=".claude/hooks/sawmill-guard.sh")
    parser.add_argument("--run-sh", default="sawmill/run.sh")
    parser.add_argument("--role-dir", default=".claude/agents")
    return parser.parse_args()


def load_yaml(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Missing YAML file: {path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def artifact_glob(path_template: str) -> str:
    return path_template.replace("{FMWK}", "*")


def parse_role_outputs(role: str, role_path: Path) -> dict[str, str]:
    try:
        text = role_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Missing role file for {role}: {role_path}") from exc

    match = OUTPUT_SECTION_RE.search(text)
    if not match:
        raise ValueError(f"Role file missing '## Declared Output Artifacts': {role_path}")

    outputs: dict[str, str] = {}
    lines = text[match.end() :].splitlines()
    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            continue
        if stripped.startswith("## "):
            break
        output_match = OUTPUT_LINE_RE.match(stripped)
        if output_match:
            artifact_id, path = output_match.groups()
            outputs[artifact_id] = path
            continue
        raise ValueError(f"Unparseable output declaration in {role_path}: {line}")

    if not outputs:
        raise ValueError(f"No declared output artifacts found in {role_path}")
    return outputs


def parse_guard_patterns(path: Path) -> dict[str, set[str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise ValueError(f"Missing guard hook: {path}") from exc

    patterns: dict[str, set[str]] = defaultdict(set)
    current_role: str | None = None
    in_check_allowed = False

    for line in lines:
        if line.startswith("check_allowed()"):
            in_check_allowed = True
            continue
        if not in_check_allowed:
            continue
        if line.strip() == "esac":
            current_role = None
            continue
        role_match = CASE_ROLE_RE.match(line)
        if role_match:
            current_role = role_match.group(1)
            continue
        if current_role is None:
            continue
        pattern_match = GUARD_PATTERN_RE.search(line)
        if pattern_match:
            patterns[current_role].add(pattern_match.group(1))
    return patterns


def parse_runtime_prompt_expectations(path: Path) -> tuple[dict[str, set[str]], set[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Missing run.sh: {path}") from exc
    lines = text.splitlines()

    prompt_artifacts: dict[str, set[str]] = defaultdict(set)
    background_prompts = set(LAUNCH_BACKGROUND_RE.findall(text))
    i = 0
    while i < len(lines):
        line = lines[i]
        prompt_match = PROMPT_STEP_RE.search(line)
        if not prompt_match:
            i += 1
            continue
        prompt_key = prompt_match.group(1)
        block = [line]
        i += 1
        while i < len(lines):
            block.append(lines[i])
            joined = "\n".join(block)
            if not lines[i].rstrip().endswith("\\"):
                break
            i += 1
        for artifact_id in ARTIFACT_PATH_RE.findall("\n".join(block)):
            prompt_artifacts[prompt_key].add(artifact_id)
        i += 1
    return prompt_artifacts, background_prompts


def parse_runtime_evidence_artifacts(path: Path) -> dict[str, set[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Missing run.sh: {path}") from exc
    evidence: dict[str, set[str]] = defaultdict(set)
    for role, artifact_id in EVIDENCE_ARTIFACT_RE.findall(text):
        evidence[role].add(artifact_id)
    return evidence


def same_pattern_or_match(artifact_pattern: str, guard_pattern: str) -> bool:
    return fnmatch.fnmatch(artifact_pattern, guard_pattern) or fnmatch.fnmatch(guard_pattern, artifact_pattern)


def check_guard_covers_artifact(role: str, artifact_pattern: str, guard_patterns: set[str]) -> bool:
    return any(same_pattern_or_match(artifact_pattern, guard_pattern) for guard_pattern in guard_patterns)


def source_list(*sources: str) -> str:
    return ", ".join(source for source in sources if source)


def record_failure(
    failures: list[tuple[str, str, str, str]],
    role: str,
    artifact_label: str,
    declared_by: str,
    missing_from: str,
) -> None:
    failures.append((role, artifact_label, declared_by, missing_from))


def main() -> int:
    args = parse_args()
    try:
        roles_data = load_yaml(Path(args.roles))
        artifacts_data = load_yaml(Path(args.artifacts))
        prompts_data = load_yaml(Path(args.prompts))
        guard_patterns = parse_guard_patterns(Path(args.guard))
        runtime_prompt_expectations, background_prompts = parse_runtime_prompt_expectations(Path(args.run_sh))
        runtime_evidence_artifacts = parse_runtime_evidence_artifacts(Path(args.run_sh))
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    known_roles = set(roles_data.get("roles", {}))
    artifact_registry = artifacts_data.get("artifacts", {})
    prompt_registry = prompts_data.get("prompts", {})
    if not isinstance(artifact_registry, dict) or not isinstance(prompt_registry, dict):
        print("FAIL: Invalid registry structure", file=sys.stderr)
        return 1

    role_outputs: dict[str, dict[str, str]] = {}
    try:
        for role in COVERED_ROLES:
            if role not in known_roles:
                continue
            role_outputs[role] = parse_role_outputs(role, Path(ROLE_FILE_BY_ROLE[role]))
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    prompt_expected_by_role: dict[str, set[str]] = defaultdict(set)
    prompt_sources_by_role_artifact: dict[tuple[str, str], set[str]] = defaultdict(set)
    for prompt_key, metadata in prompt_registry.items():
        role = metadata["role"]
        for artifact_id in metadata["expected_artifacts"]:
            prompt_expected_by_role[role].add(artifact_id)
            prompt_sources_by_role_artifact[(role, artifact_id)].add(f"prompt({prompt_key})")

    artifact_owner_by_id = {
        artifact_id: metadata["owner_role"] for artifact_id, metadata in artifact_registry.items()
    }
    artifact_globs = {
        artifact_id: artifact_glob(metadata["path_template"]) for artifact_id, metadata in artifact_registry.items()
    }

    failures: list[tuple[str, str, str, str]] = []

    # Each required artifact must have exactly one owner role.
    owners_per_artifact: dict[str, set[str]] = defaultdict(set)
    for artifact_id, owner_role in artifact_owner_by_id.items():
        owners_per_artifact[artifact_id].add(owner_role)
    for artifact_id, owners in owners_per_artifact.items():
        if len(owners) != 1:
            record_failure(
                failures,
                "/".join(sorted(owners)),
                artifact_id,
                "artifact_registry",
                "exactly-one-owner-role",
            )

    # Prompt declared artifacts -> registry, role file, guard, runtime.
    for role in COVERED_ROLES:
        if role not in known_roles:
            continue
        role_declared = set(role_outputs.get(role, {}))
        role_guard_patterns = guard_patterns.get(role, set())
        runtime_prompt_union = {
            artifact_id
            for prompt_key, metadata in prompt_registry.items()
            if metadata["role"] == role
            for artifact_id in (
                set(metadata["expected_artifacts"])
                if prompt_key in background_prompts
                else runtime_prompt_expectations.get(prompt_key, set())
            )
        }

        for artifact_id in sorted(prompt_expected_by_role.get(role, set())):
            declared_sources = source_list(
                *sorted(prompt_sources_by_role_artifact[(role, artifact_id)]),
                f"runtime(PROMPT_REGISTRY:{artifact_id})",
            )
            if artifact_id not in artifact_registry:
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    declared_sources,
                    "artifact_registry(ARTIFACT_REGISTRY.yaml)",
                )
                continue
            if artifact_owner_by_id[artifact_id] != role:
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    source_list(
                        *sorted(prompt_sources_by_role_artifact[(role, artifact_id)]),
                        f"artifact_registry(owner={artifact_owner_by_id[artifact_id]})",
                    ),
                    f"artifact_registry(owner_role for {role})",
                )
            if artifact_id not in role_declared:
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    declared_sources,
                    f"role({ROLE_FILE_BY_ROLE[role]})",
                )
            if artifact_id not in runtime_prompt_union:
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    source_list(*sorted(prompt_sources_by_role_artifact[(role, artifact_id)])),
                    "runtime(run.sh validate_prompt_step_success)",
                )
            if not check_guard_covers_artifact(role, artifact_globs[artifact_id], role_guard_patterns):
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    source_list(
                        *sorted(prompt_sources_by_role_artifact[(role, artifact_id)]),
                        f"role({ROLE_FILE_BY_ROLE[role]})",
                        "runtime(PROMPT_REGISTRY/ARTIFACT_REGISTRY)",
                    ),
                    f"guard({args.guard})",
                )

        # Role-declared artifacts must exist, be prompt-owned, and be guard-writable.
        for artifact_id in sorted(role_declared):
            declared_by = f"role({ROLE_FILE_BY_ROLE[role]})"
            if artifact_id not in artifact_registry:
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    declared_by,
                    "artifact_registry(ARTIFACT_REGISTRY.yaml)",
                )
                continue
            if artifact_owner_by_id[artifact_id] != role:
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    source_list(
                        declared_by,
                        f"artifact_registry(owner={artifact_owner_by_id[artifact_id]})",
                    ),
                    f"artifact_registry(owner_role for {role})",
                )
            if artifact_id not in prompt_expected_by_role.get(role, set()):
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    declared_by,
                    "prompt_registry(PROMPT_REGISTRY.yaml)",
                )
            if not check_guard_covers_artifact(role, artifact_globs[artifact_id], role_guard_patterns):
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    declared_by,
                    f"guard({args.guard})",
                )

        # Runtime prompt expectations in run.sh must align with prompt registry.
        for prompt_key, metadata in prompt_registry.items():
            if metadata["role"] != role:
                continue
            declared_expected = set(metadata["expected_artifacts"])
            runtime_expected = runtime_prompt_expectations.get(prompt_key, set())
            if prompt_key in background_prompts:
                runtime_expected = set(declared_expected)
            for artifact_id in sorted(declared_expected - runtime_expected):
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    f"prompt({prompt_key})",
                    "runtime(run.sh validate_prompt_step_success)",
                )
            for artifact_id in sorted(runtime_expected - declared_expected):
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    "runtime(run.sh validate_prompt_step_success)",
                    f"prompt({prompt_key})",
                )

        # Runtime evidence artifacts must align with prompt + artifact registry + guard.
        for artifact_id in sorted(runtime_evidence_artifacts.get(role, set())):
            if artifact_id not in artifact_registry:
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    "runtime(validate_evidence_artifact)",
                    "artifact_registry(ARTIFACT_REGISTRY.yaml)",
                )
                continue
            if artifact_owner_by_id[artifact_id] != role:
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    source_list(
                        "runtime(validate_evidence_artifact)",
                        f"artifact_registry(owner={artifact_owner_by_id[artifact_id]})",
                    ),
                    f"artifact_registry(owner_role for {role})",
                )
            if artifact_id not in prompt_expected_by_role.get(role, set()):
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    "runtime(validate_evidence_artifact)",
                    "prompt_registry(PROMPT_REGISTRY.yaml)",
                )
            if not check_guard_covers_artifact(role, artifact_globs[artifact_id], role_guard_patterns):
                record_failure(
                    failures,
                    role,
                    artifact_id,
                    source_list(
                        "runtime(validate_evidence_artifact)",
                        f"artifact_registry({artifact_id})",
                    ),
                    f"guard({args.guard})",
                )

    # Guard allows -> artifact registry ownership or explicit internal.
    for role, patterns in guard_patterns.items():
        if role not in known_roles:
            continue
        internal_patterns = INTERNAL_GUARD_PATTERNS.get(role, set())
        for pattern in sorted(patterns):
            if pattern in internal_patterns:
                continue
            matching_artifacts = [
                artifact_id
                for artifact_id, owner_role in artifact_owner_by_id.items()
                if owner_role == role and same_pattern_or_match(artifact_globs[artifact_id], pattern)
            ]
            if not matching_artifacts:
                record_failure(
                    failures,
                    role,
                    pattern,
                    f"guard({args.guard})",
                    "artifact_registry(owner-matched artifact or explicit internal guard rule)",
                )

    if failures:
        seen: set[tuple[str, str, str, str]] = set()
        for failure in failures:
            if failure in seen:
                continue
            seen.add(failure)
            role, artifact_label, declared_by, missing_from = failure
            print(f"FAIL {role} {artifact_label}")
            print(f"- declared by: {declared_by}")
            print(f"- missing from: {missing_from}")
        return 1

    print("PASS: factory contracts aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
