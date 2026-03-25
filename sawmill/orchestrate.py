"""Python orchestrator for the Sawmill runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sawmill.agent._core import invoke_full
from sawmill.evidence import (
    dir_sha256,
    extract_version_evidence,
    file_sha256,
    load_json as load_evidence_json,
    parse_evaluation_verdict,
    parse_review_verdict,
    validate_builder,
    validate_evaluator,
    validate_reviewer,
)
from sawmill.registry import (
    build_stage_maps,
    load_artifact_registry,
    load_prompt_registry,
    load_role_registry,
    render_prompt,
    validate_artifact_registry,
    validate_prompt_registry,
    validate_role_registry,
)
from sawmill.registry._core import extract_prompt_contract_version
from sawmill.run_state import (
    append_heartbeat,
    append_event,
    build_run_metadata,
    init_run,
    iso_timestamp,
    new_event_id,
    new_run_id,
    orchestrator_heartbeat_path,
    project_status,
    write_status,
)


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_STAGES = ("A", "B", "C", "D", "E")
TURN_RANK = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
LAUNCH_MANIFEST_FILENAME = "launch_manifest.json"
RUN_MANIFEST_FILENAME = "run_manifest.json"


@dataclass
class OrchestratorContext:
    framework_id: str
    from_turn: str
    interactive: bool
    operator_mode: str
    sawmill_dir: Path
    holdout_dir: Path
    staging_dir: Path
    branch: str
    max_attempts: int
    role_registry_path: Path
    artifact_registry_path: Path
    prompt_registry_path: Path
    agent_timeout_seconds: int


class PipelineAbort(RuntimeError):
    def __init__(self, code: int = 1) -> None:
        self.code = code
        super().__init__()


class Orchestrator:
    def __init__(self, ctx: OrchestratorContext) -> None:
        self.ctx = ctx
        self.event_lock = threading.Lock()
        self.prompt_sentinels: dict[str, Path] = {}
        self.last_agent_exit_event_id = ""
        self.last_failure_event_id = ""
        self.last_failure_code = ""
        self.last_output_verified_event_id = ""
        self.last_turn_completed_event_id = ""
        self.last_decision_event_id = ""
        self.last_retry_event_id = ""
        self.current_event_turn = "orchestrator"
        self.current_event_step = "run"
        self.current_event_role = "orchestrator"
        self.current_event_backend = "runtime"
        self.current_event_attempt = 0
        self.attempt = 0
        self.build_passed = False
        self.run_started_at = ""
        self.run_id = ""
        self.run_dir = Path()
        self.run_json_path = Path()
        self.status_json_path = Path()
        self.events_json_path = Path()
        self.run_log_dir = Path()
        self.run_invocations_dir = Path()
        self.run_heartbeats_dir = Path()
        self.run_started_event_id = ""
        self.preflight_passed_event_id = ""
        self.last_missing_artifact_path = ""
        self.last_missing_artifact_label = ""
        self.last_prompt_verification_error = ""
        self.launch_manifest_path = self.ctx.sawmill_dir / LAUNCH_MANIFEST_FILENAME
        self.launch_manifest: dict[str, Any] = {}
        self.role_runtime_config: dict[str, dict[str, str]] = {}
        self.resumed_from_run_id = ""
        self.lineage_root_run_id = ""

        self.role_registry = load_role_registry(ctx.role_registry_path)
        validate_role_registry(self.role_registry, ctx.role_registry_path)
        self.artifact_registry = load_artifact_registry(ctx.artifact_registry_path)
        validate_artifact_registry(self.artifact_registry, self.role_registry)
        self.prompt_registry = load_prompt_registry(ctx.prompt_registry_path)
        validate_prompt_registry(self.prompt_registry, self.role_registry, self.artifact_registry)
        self.stage_all, self.stage_required, self.invalidate_from = build_stage_maps(self.artifact_registry)

        self.roles = self.role_registry["roles"]
        self.artifacts = self.artifact_registry["artifacts"]
        self.prompts = self.prompt_registry["prompts"]

        self.builder_prompt_contract_version = extract_prompt_contract_version(
            ROOT / "Templates/BUILDER_PROMPT_CONTRACT.md"
        )
        self.reviewer_prompt_contract_version = extract_prompt_contract_version(
            ROOT / "Templates/REVIEWER_PROMPT_CONTRACT.md"
        )

        self.launch_manifest = self._load_launch_manifest()
        self.role_runtime_config = {
            role_name: self._resolve_role_runtime(role_name)
            for role_name in self.roles
        }

        self.spec_agent = self.role_runtime_config["spec-agent"]["backend"]
        self.build_agent = self.role_runtime_config["builder"]["backend"]
        self.holdout_agent = self.role_runtime_config["holdout-agent"]["backend"]
        self.review_agent = self.role_runtime_config["reviewer"]["backend"]
        self.eval_agent = self.role_runtime_config["evaluator"]["backend"]
        self.audit_agent = self.role_runtime_config["auditor"]["backend"]

        self.spec_role_file = ROOT / self.roles["spec-agent"]["role_file"]
        self.holdout_role_file = ROOT / self.roles["holdout-agent"]["role_file"]
        self.build_role_file = ROOT / self.roles["builder"]["role_file"]
        self.review_role_file = ROOT / self.roles["reviewer"]["role_file"]
        self.eval_role_file = ROOT / self.roles["evaluator"]["role_file"]
        self.audit_role_file = ROOT / self.roles["auditor"]["role_file"]

        self._export_base_environment()

    def heartbeat(self, kind: str, phase: str, summary: str, *, detail: str = "", artifact_refs: list[str] | None = None) -> None:
        if not self.run_dir:
            return
        append_heartbeat(
            orchestrator_heartbeat_path(self.run_dir),
            {
                "timestamp": iso_timestamp(),
                "run_id": self.run_id,
                "turn": self.current_event_turn,
                "step": self.current_event_step,
                "role": self.current_event_role,
                "backend": self.current_event_backend,
                "attempt": self.current_event_attempt,
                "source": "orchestrator",
                "kind": kind,
                "phase": phase,
                "summary": summary,
                "detail": detail,
                "artifact_refs": artifact_refs or [],
            },
        )

    def _default_runtime_for_role(self, role_name: str) -> dict[str, str]:
        metadata = self.roles[role_name]
        return {
            "backend": str(metadata["backend"]),
            "model": str(metadata["model"]),
            "effort": str(metadata["effort"]),
            "source": "registry",
        }

    def _load_launch_manifest(self) -> dict[str, Any]:
        if not self.launch_manifest_path.exists():
            return {}
        manifest = load_evidence_json(self.launch_manifest_path)
        roles = manifest.get("roles", {})
        if not isinstance(roles, dict):
            raise ValueError(f"{self.launch_manifest_path} roles must be an object")
        for role_name, config in roles.items():
            if role_name not in self.roles:
                raise ValueError(f"{self.launch_manifest_path} references unknown role '{role_name}'")
            if not isinstance(config, dict):
                raise ValueError(f"{self.launch_manifest_path} role '{role_name}' must map to an object")
            backend = str(config.get("backend", ""))
            if backend not in self.roles[role_name]["allowed_backends"]:
                raise ValueError(
                    f"{self.launch_manifest_path} role '{role_name}' backend '{backend}' is not allowed ({self.roles[role_name]['allowed_backends']})"
                )
        return manifest

    def _resolve_role_runtime(self, role_name: str) -> dict[str, str]:
        metadata = self.roles[role_name]
        runtime = self._default_runtime_for_role(role_name)
        manifest_roles = self.launch_manifest.get("roles", {})
        manifest_role = manifest_roles.get(role_name) if isinstance(manifest_roles, dict) else None
        if isinstance(manifest_role, dict):
            runtime = {
                "backend": str(manifest_role.get("backend", runtime["backend"])),
                "model": str(manifest_role.get("model", runtime["model"])),
                "effort": str(manifest_role.get("effort", runtime["effort"])),
                "source": "launch_manifest",
            }
        selected = os.environ.get(metadata["env_override"], runtime["backend"])
        if selected not in metadata["allowed_backends"]:
            self.fail(
                f"Role '{role_name}' resolved backend '{selected}' via {metadata['env_override']} is not allowed ({metadata['allowed_backends']})"
            )
            raise PipelineAbort(1)
        if selected != runtime["backend"]:
            runtime["backend"] = selected
            runtime["model"] = "default"
            runtime["effort"] = "default"
            runtime["source"] = f"env_override:{metadata['env_override']}"
        return runtime

    def _sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _export_base_environment(self) -> None:
        os.environ["FMWK"] = self.ctx.framework_id
        os.environ["FROM_TURN"] = self.ctx.from_turn
        os.environ["SAWMILL_DIR"] = str(self.ctx.sawmill_dir)
        os.environ["HOLDOUT_DIR"] = str(self.ctx.holdout_dir)
        os.environ["STAGING_DIR"] = str(self.ctx.staging_dir)
        os.environ["BRANCH"] = self.ctx.branch
        os.environ["MAX_ATTEMPTS"] = str(self.ctx.max_attempts)
        os.environ["ARTIFACT_REGISTRY"] = str(self.ctx.artifact_registry_path)
        os.environ["ROLE_REGISTRY"] = str(self.ctx.role_registry_path)
        os.environ["PROMPT_REGISTRY"] = str(self.ctx.prompt_registry_path)
        os.environ["OPERATOR_MODE"] = self.ctx.operator_mode
        os.environ["SOURCE_MATERIAL_PATH"] = str(self.ctx.sawmill_dir / "SOURCE_MATERIAL.md")
        os.environ["STATUS_PAGE_PATH"] = str(self.artifact_path("status_page"))
        os.environ["SPEC_AGENT"] = self.spec_agent
        os.environ["BUILD_AGENT"] = self.build_agent
        os.environ["HOLDOUT_AGENT"] = self.holdout_agent
        os.environ["REVIEW_AGENT"] = self.review_agent
        os.environ["EVAL_AGENT"] = self.eval_agent
        os.environ["AUDIT_AGENT"] = self.audit_agent
        os.environ["SPEC_ROLE_FILE"] = str(self.spec_role_file)
        os.environ["HOLDOUT_ROLE_FILE"] = str(self.holdout_role_file)
        os.environ["BUILD_ROLE_FILE"] = str(self.build_role_file)
        os.environ["REVIEW_ROLE_FILE"] = str(self.review_role_file)
        os.environ["EVAL_ROLE_FILE"] = str(self.eval_role_file)
        os.environ["AUDIT_ROLE_FILE"] = str(self.audit_role_file)
        os.environ["SPEC_MODEL_POLICY"] = self.role_runtime_config["spec-agent"]["effort"]
        os.environ["HOLDOUT_MODEL_POLICY"] = self.role_runtime_config["holdout-agent"]["effort"]
        os.environ["BUILD_MODEL_POLICY"] = self.role_runtime_config["builder"]["effort"]
        os.environ["REVIEW_MODEL_POLICY"] = self.role_runtime_config["reviewer"]["effort"]
        os.environ["EVAL_MODEL_POLICY"] = self.role_runtime_config["evaluator"]["effort"]
        os.environ["AUDIT_MODEL_POLICY"] = self.role_runtime_config["auditor"]["effort"]
        os.environ["SPEC_MODEL"] = self.role_runtime_config["spec-agent"]["model"]
        os.environ["HOLDOUT_MODEL"] = self.role_runtime_config["holdout-agent"]["model"]
        os.environ["BUILD_MODEL"] = self.role_runtime_config["builder"]["model"]
        os.environ["REVIEW_MODEL"] = self.role_runtime_config["reviewer"]["model"]
        os.environ["EVAL_MODEL"] = self.role_runtime_config["evaluator"]["model"]
        os.environ["AUDIT_MODEL"] = self.role_runtime_config["auditor"]["model"]
        os.environ["BUILDER_PROMPT_CONTRACT_VERSION"] = self.builder_prompt_contract_version
        os.environ["REVIEWER_PROMPT_CONTRACT_VERSION"] = self.reviewer_prompt_contract_version
        os.environ["ALL_PROMPT_KEYS"] = " ".join(sorted(self.prompts))
        for prompt_key, metadata in self.prompts.items():
            os.environ[f"PROMPT_{prompt_key.upper()}_PROMPT_FILE"] = metadata["prompt_file"]
        self.export_artifact_paths()

    def log(self, message: str) -> None:
        print(f"\033[0;34m[sawmill]\033[0m {message}")

    def pass_(self, message: str) -> None:
        print(f"\033[0;32m[PASS]\033[0m {message}")

    def fail(self, message: str) -> None:
        print(f"\033[0;31m[FAIL]\033[0m {message}")

    def checkpoint(self, message: str) -> None:
        print(f"\n\033[1;33m>>> CHECKPOINT: {message}\033[0m")
        if not self.ctx.interactive:
            self.log("Unattended mode: checkpoint recorded, continuing")
            return
        if not sys.stdin.isatty():
            self.fail(
                "Interactive checkpoints require a live TTY. Re-run with --interactive in a terminal or use the default unattended path."
            )
            raise PipelineAbort(1)
        print("\033[1;33m>>> Review the output, then press Enter to continue (or Ctrl+C to abort)\033[0m")
        input()

    def artifact_path(self, artifact_id: str) -> Path:
        return ROOT / self.artifacts[artifact_id]["path_template"].replace("{FMWK}", self.ctx.framework_id)

    def artifact_kind(self, artifact_id: str) -> str:
        return str(self.artifacts[artifact_id]["artifact_kind"])

    def prompt_file(self, prompt_key: str) -> Path:
        return ROOT / self.prompts[prompt_key]["prompt_file"]

    def prompt_expected_artifacts(self, prompt_key: str) -> list[str]:
        return list(self.prompts[prompt_key]["expected_artifacts"])

    def prompt_required_artifacts(self, prompt_key: str) -> list[str]:
        return list(self.prompts[prompt_key]["required_artifacts"])

    def prompt_freshness_policy(self, prompt_key: str) -> str:
        return str(self.prompts[prompt_key]["freshness_policy"])

    def prompt_role(self, prompt_key: str) -> str:
        return str(self.prompts[prompt_key]["role"])

    def prompt_turn(self, prompt_key: str) -> str:
        return {
            "turn_a_spec": "A",
            "turn_b_plan": "B",
            "turn_c_holdout": "C",
            "turn_d_13q": "D",
            "turn_d_review": "D",
            "turn_d_build": "D",
            "turn_e_eval": "E",
        }.get(prompt_key, "orchestrator")

    def export_artifact_paths(self) -> None:
        for artifact_id in self.artifacts:
            os.environ[f"{artifact_id.upper()}_PATH"] = str(self.artifact_path(artifact_id))

    def current_status_field(self, field: str) -> str:
        if not self.status_json_path.exists():
            return ""
        value = json.loads(self.status_json_path.read_text(encoding="utf-8")).get(field, "")
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def build_run_metadata_file(self) -> Path:
        metadata_file = Path(tempfile.mktemp(prefix="sawmill-run-metadata.", dir="/tmp"))
        role_backend_resolution = {
            "spec-agent": self.spec_agent,
            "holdout-agent": self.holdout_agent,
            "builder": self.build_agent,
            "reviewer": self.review_agent,
            "evaluator": self.eval_agent,
            "auditor": self.audit_agent,
        }
        model_policies = {role: runtime["effort"] for role, runtime in self.role_runtime_config.items()}
        role_file_hashes = {
            str(ROOT / metadata["role_file"]): self._sha256_file(ROOT / metadata["role_file"])
            for metadata in self.roles.values()
        }
        prompt_file_hashes = {
            str(ROOT / metadata["prompt_file"]): self._sha256_file(ROOT / metadata["prompt_file"])
            for metadata in self.prompts.values()
        }
        metadata = build_run_metadata(
            run_id=self.run_id,
            framework_id=self.ctx.framework_id,
            started_at=self.run_started_at,
            requested_entry_path="./sawmill/run.sh",
            from_turn=self.ctx.from_turn,
            retry_budget=self.ctx.max_attempts,
            role_backend_resolution=role_backend_resolution,
            model_policies=model_policies,
            prompt_contract_versions={
                "builder_prompt_contract": self.builder_prompt_contract_version,
                "reviewer_prompt_contract": self.reviewer_prompt_contract_version,
            },
            role_runtime_config=self.role_runtime_config,
            role_file_hashes=role_file_hashes,
            prompt_file_hashes=prompt_file_hashes,
            artifact_registry_version_hash=self._sha256_file(self.ctx.artifact_registry_path),
            graph_version="none",
            operator_mode=self.ctx.operator_mode,
            resumed_from_run_id=self.resumed_from_run_id,
            lineage_root_run_id=self.lineage_root_run_id or self.run_id,
            launch_manifest_path=str(self.launch_manifest_path) if self.launch_manifest_path.exists() else "",
            launch_manifest_hash=self._sha256_file(self.launch_manifest_path) if self.launch_manifest_path.exists() else "",
        )
        metadata_file.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return metadata_file

    def emit(
        self,
        event_type: str,
        outcome: str,
        failure_code: str,
        parent_event_id: str,
        turn: str,
        step: str,
        role: str,
        backend: str,
        attempt: int,
        summary: str,
        *,
        evidence_refs: list[str] | None = None,
        contract_refs: list[str] | None = None,
    ) -> str:
        event_id = new_event_id()
        event = {
            "event_id": event_id,
            "run_id": self.run_id,
            "timestamp": iso_timestamp(),
            "turn": turn,
            "step": step,
            "role": role,
            "backend": backend,
            "attempt": attempt,
            "event_type": event_type,
            "outcome": outcome,
            "failure_code": failure_code,
            "causal_parent_event_id": parent_event_id or None,
            "evidence_refs": evidence_refs or [],
            "contract_refs": contract_refs or [],
            "summary": summary,
        }
        with self.event_lock:
            append_event(self.run_dir, event)
            write_status(self.run_dir, project_status(self.run_dir))
        return event_id

    def record_run_failed(self, parent_event_id: str, failure_code: str, summary: str) -> None:
        self.emit(
            "run_failed",
            "failed",
            failure_code,
            parent_event_id,
            self.current_event_turn,
            self.current_event_step,
            self.current_event_role,
            self.current_event_backend,
            self.current_event_attempt,
            summary,
        )

    def fail_preflight(self, failure_code: str, summary: str) -> None:
        self.current_event_turn = "orchestrator"
        self.current_event_step = "preflight"
        self.current_event_role = "orchestrator"
        self.current_event_backend = "runtime"
        self.current_event_attempt = 0
        preflight_failure = self.emit(
            "preflight_passed",
            "failed",
            failure_code,
            self.run_started_event_id,
            "orchestrator",
            "preflight",
            "orchestrator",
            "runtime",
            0,
            summary,
        )
        self.record_run_failed(preflight_failure, failure_code, summary)
        self.fail(summary)
        raise PipelineAbort(1)

    def record_escalation(self, parent_event_id: str, failure_code: str, summary: str) -> None:
        self.emit(
            "escalation_triggered",
            "escalated",
            failure_code,
            parent_event_id,
            self.current_event_turn,
            self.current_event_step,
            self.current_event_role,
            self.current_event_backend,
            self.current_event_attempt,
            summary,
        )

    def initialize_run_harness(self) -> None:
        self.run_started_at = iso_timestamp()
        self.run_id = new_run_id()
        self.resolved_resume_lineage()
        self.run_dir = self.ctx.sawmill_dir / "runs" / self.run_id
        self.run_json_path = self.run_dir / "run.json"
        self.status_json_path = self.run_dir / "status.json"
        self.events_json_path = self.run_dir / "events.jsonl"
        self.run_log_dir = self.run_dir / "logs"
        self.run_invocations_dir = self.run_dir / "invocations"
        self.run_heartbeats_dir = self.run_dir / "heartbeats"
        os.environ["RUN_ID"] = self.run_id
        os.environ["RUN_DIR"] = str(self.run_dir)
        os.environ["RUN_JSON_PATH"] = str(self.run_json_path)
        os.environ["STATUS_JSON_PATH"] = str(self.status_json_path)
        os.environ["EVENTS_JSON_PATH"] = str(self.events_json_path)
        os.environ["RUN_LOG_DIR"] = str(self.run_log_dir)
        os.environ["RUN_INVOCATIONS_DIR"] = str(self.run_invocations_dir)
        os.environ["RUN_HEARTBEATS_DIR"] = str(self.run_heartbeats_dir)
        os.environ["RUN_STARTED_AT"] = self.run_started_at

        metadata_file = self.build_run_metadata_file()
        init_run(self.run_dir, metadata_file)
        metadata_file.unlink(missing_ok=True)
        if self.launch_manifest_path.exists():
            shutil.copy2(self.launch_manifest_path, self.run_dir / RUN_MANIFEST_FILENAME)
        self.run_invocations_dir.mkdir(parents=True, exist_ok=True)
        self.run_heartbeats_dir.mkdir(parents=True, exist_ok=True)
        self.run_started_event_id = self.emit(
            "run_started",
            "started",
            "none",
            "",
            "orchestrator",
            "run",
            "orchestrator",
            "runtime",
            0,
            f"Run started for {self.ctx.framework_id}",
        )

    def resolved_resume_lineage(self) -> None:
        if self.ctx.from_turn == "A":
            self.resumed_from_run_id = ""
            self.lineage_root_run_id = ""
            return
        runs_dir = self.ctx.sawmill_dir / "runs"
        candidates = (
            sorted([path for path in runs_dir.iterdir() if path.is_dir()], key=lambda path: path.name)
            if runs_dir.exists()
            else []
        )
        if not candidates:
            self.resumed_from_run_id = ""
            self.lineage_root_run_id = ""
            return
        interrupted = []
        for candidate in candidates:
            try:
                projected = project_status(candidate)
            except Exception:
                continue
            if projected.status.get("state") == "interrupted":
                interrupted.append(candidate)
        previous = interrupted[-1] if interrupted else candidates[-1]
        previous_run = load_evidence_json(previous / "run.json")
        self.resumed_from_run_id = str(previous_run.get("run_id", previous.name))
        self.lineage_root_run_id = str(previous_run.get("lineage_root_run_id") or self.resumed_from_run_id)

    def scan_interrupted_runs(self) -> None:
        runs_dir = self.ctx.sawmill_dir / "runs"
        if not runs_dir.exists():
            return
        for run_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
            status_path = run_dir / "status.json"
            if not status_path.exists():
                continue
            try:
                result = project_status(run_dir)
            except Exception as exc:
                self.log(f"Skipped interrupted-run scan for {run_dir.name}: {exc}")
                continue
            if result.status.get("state") == "interrupted":
                write_status(run_dir, result)
                self.log(
                    f"Marked interrupted run {run_dir.name}: {result.status.get('interruption_reason', 'unknown')}"
                )

    def _run_cli(self, args: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            cwd=ROOT,
            check=check,
            capture_output=capture,
            text=True,
        )

    def preflight(self) -> None:
        self.heartbeat("phase", "preflight", "Running preflight checks")
        result = self._run_cli(
            [
                "-m",
                "sawmill.audit",
                "preflight",
                "--fmwk",
                self.ctx.framework_id,
                "--task-path",
                str(self.artifact_path("task").relative_to(ROOT)),
                "--role-registry",
                str(self.ctx.role_registry_path.relative_to(ROOT)),
                "--artifact-registry",
                str(self.ctx.artifact_registry_path.relative_to(ROOT)),
                "--prompt-registry",
                str(self.ctx.prompt_registry_path.relative_to(ROOT)),
                "--builder-contract",
                "Templates/BUILDER_PROMPT_CONTRACT.md",
                "--reviewer-contract",
                "Templates/REVIEWER_PROMPT_CONTRACT.md",
            ],
            check=False,
            capture=True,
        )
        if result.returncode != 0:
            self.fail_preflight("PREFLIGHT_FAILED", result.stdout + result.stderr)
        self.current_event_turn = "orchestrator"
        self.current_event_step = "preflight"
        self.current_event_role = "orchestrator"
        self.current_event_backend = "runtime"
        self.current_event_attempt = 0
        self.preflight_passed_event_id = self.emit(
            "preflight_passed",
            "passed",
            "none",
            self.run_started_event_id,
            "orchestrator",
            "preflight",
            "orchestrator",
            "runtime",
            0,
            f"Preflight passed for {self.ctx.framework_id}",
        )
        self.heartbeat("phase", "preflight", "Preflight passed")
        self.log("Preflight passed. Starting pipeline.")
        print("")

    def update_status_page(self) -> None:
        self.heartbeat("phase", "processing_result", "Updating status page")
        self._run_cli(
            [
                "-m",
                "sawmill.run_state",
                "update-status",
                "--framework-id",
                self.ctx.framework_id,
                "--run-id",
                self.run_id or "none",
                "--status-page",
                str(self.artifact_path("status_page")),
                "--status-json",
                str(self.status_json_path),
                "--artifact-registry",
                str(self.ctx.artifact_registry_path),
                "--evaluation-report",
                str(self.artifact_path("evaluation_report")),
            ],
            capture=True,
        )
        self.log(f"Portal updated: {self.artifact_path('status_page').relative_to(ROOT)}")

    def run_stage_audit(self, stage: str) -> bool:
        self.heartbeat("phase", "auditing_stage", f"Running stage audit for {stage}")
        result = self._run_cli(
            [
                "-m",
                "sawmill.audit",
                "stage",
                "--fmwk",
                self.ctx.framework_id,
                "--stage",
                stage,
                "--status-page",
                str(self.artifact_path("status_page")),
                "--artifact-registry",
                str(self.ctx.artifact_registry_path),
                "--review-report",
                str(self.artifact_path("review_report")),
                "--review-errors",
                str(self.artifact_path("review_errors")),
                "--evaluation-report",
                str(self.artifact_path("evaluation_report")),
                "--audit-file",
                str(self.ctx.sawmill_dir / "CANARY_AUDIT.md"),
            ],
            check=False,
            capture=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if output.strip():
            print(output.strip())
        self.heartbeat("decision", "auditing_stage", f"Stage audit {'passed' if result.returncode == 0 else 'failed'} for {stage}")
        return result.returncode == 0

    def validate_convergence(self) -> bool:
        self.heartbeat("phase", "finalizing", "Validating convergence")
        self.update_status_page()
        result = self._run_cli(
            [
                "-m",
                "sawmill.audit",
                "convergence",
                "--fmwk",
                self.ctx.framework_id,
                "--run-id",
                self.run_id,
                "--run-dir",
                str(self.run_dir),
                "--status-page",
                str(self.artifact_path("status_page")),
                "--status-json",
                str(self.status_json_path),
                "--base-dir",
                str(self.ctx.sawmill_dir),
                "--holdout-dir",
                str(self.ctx.holdout_dir),
                "--staging-dir",
                str(self.ctx.staging_dir),
            ],
            check=False,
            capture=True,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if output.strip():
            print(output.strip())
        self.heartbeat("decision", "finalizing", f"Convergence {'passed' if result.returncode == 0 else 'failed'}")
        return result.returncode == 0

    def complete_run(self, parent_event_id: str, summary: str, failure_summary: str) -> None:
        if not self.validate_convergence():
            self.record_run_failed(
                self.last_decision_event_id or parent_event_id or self.run_started_event_id,
                "CONVERGENCE_FAILED",
                failure_summary,
            )
            raise PipelineAbort(1)
        self.heartbeat("phase", "complete", summary)
        self.emit(
            "run_completed",
            "passed",
            "none",
            parent_event_id,
            "orchestrator",
            "run",
            "orchestrator",
            "runtime",
            self.attempt,
            summary,
        )

    def should_run_turn(self, turn: str) -> bool:
        return TURN_RANK[turn] >= TURN_RANK[self.ctx.from_turn]

    def ensure_artifact_exists(self, artifact_id: str, label: str = "artifact") -> bool:
        path = self.artifact_path(artifact_id)
        kind = self.artifact_kind(artifact_id)
        exists = path.is_dir() if kind == "dir" else path.is_file()
        if not exists:
            self.last_missing_artifact_path = str(path)
            self.last_missing_artifact_label = label
        return exists

    def ensure_artifact_ids(self, label: str, *artifact_ids: str) -> bool:
        return all(self.ensure_artifact_exists(artifact_id, label) for artifact_id in artifact_ids)

    def ensure_prompt_inputs(self, prompt_key: str) -> bool:
        for artifact_id in self.prompt_required_artifacts(prompt_key):
            if not self.ensure_artifact_exists(artifact_id, f"input for {prompt_key}"):
                return False
        return True

    def snapshot_prompt_outputs(self, prompt_key: str) -> None:
        self.prompt_sentinels[prompt_key] = Path(tempfile.mktemp(prefix=f"sawmill-{prompt_key}.", dir="/tmp"))
        self.prompt_sentinels[prompt_key].touch()

    def cleanup_prompt_sentinel(self, prompt_key: str) -> None:
        sentinel = self.prompt_sentinels.pop(prompt_key, None)
        if sentinel is not None:
            sentinel.unlink(missing_ok=True)

    def artifact_newer_than(self, artifact_id: str, reference_path: Path) -> bool:
        path = self.artifact_path(artifact_id)
        if self.artifact_kind(artifact_id) == "dir":
            return any(child.stat().st_mtime > reference_path.stat().st_mtime for child in path.rglob("*") if child.exists())
        return path.exists() and path.stat().st_mtime > reference_path.stat().st_mtime

    def verify_prompt_outputs(self, prompt_key: str) -> bool:
        sentinel_path = self.prompt_sentinels.get(prompt_key)
        freshness_policy = self.prompt_freshness_policy(prompt_key)
        for artifact_id in self.prompt_expected_artifacts(prompt_key):
            if not self.ensure_artifact_exists(artifact_id, f"output for {prompt_key}"):
                self.last_prompt_verification_error = f"Missing required output for {prompt_key}: {self.artifact_path(artifact_id)}"
                self.cleanup_prompt_sentinel(prompt_key)
                return False
            if freshness_policy == "required" and sentinel_path is not None and not self.artifact_newer_than(artifact_id, sentinel_path):
                self.last_prompt_verification_error = f"Output for {prompt_key} was not refreshed this run: {self.artifact_path(artifact_id)}"
                self.cleanup_prompt_sentinel(prompt_key)
                return False
            if freshness_policy not in {"required", "allow_unchanged"}:
                self.last_prompt_verification_error = f"Prompt '{prompt_key}' has unsupported freshness policy '{freshness_policy}'"
                self.cleanup_prompt_sentinel(prompt_key)
                return False
        self.cleanup_prompt_sentinel(prompt_key)
        return True

    def validate_prompt_step_success(
        self,
        prompt_key: str,
        parent_event_id: str,
        turn: str,
        role_name: str,
        backend: str,
        attempt: int,
        evidence_paths: list[Path],
    ) -> None:
        if not self.verify_prompt_outputs(prompt_key):
            failure_event_id = self.emit(
                "output_verified",
                "failed",
                "OUTPUT_VERIFICATION_FAILED",
                parent_event_id,
                turn,
                prompt_key,
                role_name,
                backend,
                attempt,
                self.last_prompt_verification_error or f"Output verification failed for {prompt_key}",
            )
            self.record_run_failed(failure_event_id, "OUTPUT_VERIFICATION_FAILED", f"Output verification failed for {prompt_key}")
            self.fail(f"Output verification failed for {prompt_key}")
            raise PipelineAbort(1)
        self.last_output_verified_event_id = self.emit(
            "output_verified",
            "verified",
            "none",
            parent_event_id,
            turn,
            prompt_key,
            role_name,
            backend,
            attempt,
            f"Outputs verified for {prompt_key}",
            evidence_refs=[str(path) for path in evidence_paths],
        )

    def invalidate_artifact(self, artifact_id: str) -> bool:
        path = self.artifact_path(artifact_id)
        if self.artifact_kind(artifact_id) == "dir":
            if not path.is_dir():
                return False
            subprocess.run(["rm", "-rf", str(path)], check=True)
        else:
            if not path.is_file():
                return False
            path.unlink()
        return True

    def invalidate_downstream_artifacts(self) -> None:
        artifact_ids = self.invalidate_from.get(self.ctx.from_turn, [])
        if not artifact_ids:
            return
        self.log(f"Invalidating stage-owned artifacts for rerun from Turn {self.ctx.from_turn}")
        invalidated = 0
        for artifact_id in artifact_ids:
            if self.invalidate_artifact(artifact_id):
                self.log(f"Invalidated {self.artifact_path(artifact_id).relative_to(ROOT)}")
                invalidated += 1
        self.ctx.sawmill_dir.mkdir(parents=True, exist_ok=True)
        self.ctx.holdout_dir.mkdir(parents=True, exist_ok=True)
        self.ctx.staging_dir.mkdir(parents=True, exist_ok=True)
        self.log(f"Invalidation complete ({invalidated} artifact paths removed)")

    def export_evidence_hashes(self, step: str) -> None:
        if step == "turn_d_review":
            os.environ["Q13_ANSWERS_PATH"] = str(self.artifact_path("q13_answers"))
            os.environ["Q13_ANSWERS_HASH"] = file_sha256(self.artifact_path("q13_answers"))
            self.log(f"Pre-computed Q13_ANSWERS_HASH={os.environ['Q13_ANSWERS_HASH']}")
        elif step == "turn_d_build":
            os.environ["BUILDER_HANDOFF_PATH"] = str(self.artifact_path("builder_handoff"))
            os.environ["Q13_ANSWERS_PATH"] = str(self.artifact_path("q13_answers"))
            os.environ["HANDOFF_HASH"] = file_sha256(self.artifact_path("builder_handoff"))
            os.environ["Q13_ANSWERS_HASH"] = file_sha256(self.artifact_path("q13_answers"))
            self.log(f"Pre-computed HANDOFF_HASH={os.environ['HANDOFF_HASH']}")
            self.log(f"Pre-computed Q13_ANSWERS_HASH={os.environ['Q13_ANSWERS_HASH']}")
        elif step == "turn_e_eval":
            os.environ["D9_HOLDOUT_SCENARIOS_PATH"] = str(self.artifact_path("d9_holdout_scenarios"))
            os.environ["STAGING_ROOT_PATH"] = str(self.artifact_path("staging_root"))
            os.environ["HOLDOUT_HASH"] = file_sha256(self.artifact_path("d9_holdout_scenarios"))
            os.environ["STAGING_HASH"] = dir_sha256(self.artifact_path("staging_root"))
            self.log(f"Pre-computed HOLDOUT_HASH={os.environ['HOLDOUT_HASH']}")
            self.log(f"Pre-computed STAGING_HASH={os.environ['STAGING_HASH']}")

    def append_retry_context(self, artifact_id: str, title: str, retry_context: str) -> str:
        path = self.artifact_path(artifact_id)
        if path.is_file() and path.stat().st_size > 0:
            retry_context += f"\n\n{title}:\nRead {path} for the latest failures. Fix ONLY what failed. Do not rewrite passing work."
        return retry_context

    def model_for_role(self, role_name: str) -> str:
        return str(self.role_runtime_config[role_name]["model"])

    def effort_for_role(self, role_name: str) -> str:
        return str(self.role_runtime_config[role_name]["effort"])

    def invoke_agent(self, backend: str, role_file: Path, prompt: str, prompt_key: str, prompt_event_id: str) -> bool:
        role_name = role_file.stem
        self.log(f"Invoking {backend} with role {role_name} ({role_file.relative_to(ROOT)})")
        self.heartbeat("waiting", "waiting_for_worker", f"Waiting for {prompt_key} worker progress")
        result = invoke_full(
            backend=backend,
            role_file=role_file,
            prompt_file=self.prompt_file(prompt_key),
            prompt_key=prompt_key,
            prompt_event_id=prompt_event_id,
            turn=self.prompt_turn(prompt_key),
            attempt=self.attempt or 1,
            run_dir=self.run_dir,
            run_id=self.run_id,
            framework_id=self.ctx.framework_id,
            timeout_seconds=self.ctx.agent_timeout_seconds,
            operator_mode=self.ctx.operator_mode,
            model=self.model_for_role(role_name),
            effort=self.effort_for_role(role_name),
            prompt=prompt,
            orchestrator_heartbeat_path=orchestrator_heartbeat_path(self.run_dir),
        )
        self.last_agent_exit_event_id = result["LAST_AGENT_EXIT_EVENT_ID"]
        self.last_failure_event_id = result["LAST_FAILURE_EVENT_ID"]
        self.last_failure_code = result["LAST_FAILURE_CODE"]
        self.heartbeat("phase", "processing_result", f"Processing result for {prompt_key}")
        if result["RESULT_TIMED_OUT"] == "true" or result["RESULT_OUTCOME"] == "timeout":
            self.last_failure_code = self.last_failure_code or "AGENT_TIMEOUT"
            return False
        if self.last_failure_event_id:
            self.last_failure_code = self.last_failure_code or result["RESULT_FAILURE_CODE"] or "AGENT_EXIT_NONZERO"
            return False
        return True

    def invoke_prompt(self, backend: str, role_file: Path, prompt_key: str, turn_event_id: str) -> None:
        expected_role = role_file.stem
        prompt_owner = self.prompt_role(prompt_key)
        role_name = expected_role
        turn = self.prompt_turn(prompt_key)
        self.current_event_turn = turn
        self.current_event_step = prompt_key
        self.current_event_role = role_name
        self.current_event_backend = backend
        self.current_event_attempt = self.attempt or 1
        os.environ["ATTEMPT"] = str(self.current_event_attempt)
        self.heartbeat("phase", "dispatching", f"Dispatching {prompt_key}")

        if prompt_owner != expected_role:
            ownership_failure = self.emit(
                "prompt_rendered",
                "failed",
                "PROMPT_OWNER_MISMATCH",
                turn_event_id,
                turn,
                prompt_key,
                role_name,
                backend,
                self.current_event_attempt,
                f"Prompt '{prompt_key}' owner '{prompt_owner}' did not match role '{expected_role}'",
                contract_refs=[str(self.prompt_file(prompt_key)), str(role_file)],
            )
            self.record_run_failed(ownership_failure, "PROMPT_OWNER_MISMATCH", f"Prompt '{prompt_key}' owner mismatch")
            self.fail(f"Prompt '{prompt_key}' is owned by '{prompt_owner}', but runtime tried to invoke role '{expected_role}'")
            raise PipelineAbort(1)

        if not self.ensure_prompt_inputs(prompt_key):
            input_failure = self.emit(
                "prompt_rendered",
                "failed",
                "MISSING_INPUT_ARTIFACT",
                turn_event_id,
                turn,
                prompt_key,
                role_name,
                backend,
                self.current_event_attempt,
                f"Missing required input for {prompt_key}: {self.last_missing_artifact_path}",
                contract_refs=[str(self.prompt_file(prompt_key)), str(role_file)],
            )
            self.record_run_failed(input_failure, "MISSING_INPUT_ARTIFACT", f"Missing required input for {prompt_key}: {self.last_missing_artifact_path}")
            self.fail(f"Missing required {self.last_missing_artifact_label}: {self.last_missing_artifact_path}")
            raise PipelineAbort(1)

        self.snapshot_prompt_outputs(prompt_key)
        try:
            rendered_prompt = render_prompt(self.prompt_file(prompt_key), dict(os.environ))
        except ValueError:
            self.cleanup_prompt_sentinel(prompt_key)
            render_failure = self.emit(
                "prompt_rendered",
                "failed",
                "PROMPT_RENDER_FAILED",
                turn_event_id,
                turn,
                prompt_key,
                role_name,
                backend,
                self.current_event_attempt,
                f"Failed to render prompt '{prompt_key}' from {self.prompt_file(prompt_key)}",
                contract_refs=[str(self.prompt_file(prompt_key)), str(role_file)],
            )
            self.record_run_failed(render_failure, "PROMPT_RENDER_FAILED", f"Failed to render prompt '{prompt_key}'")
            self.fail(f"Failed to render prompt '{prompt_key}' from {self.prompt_file(prompt_key)}")
            raise PipelineAbort(1)

        prompt_event_id = self.emit(
            "prompt_rendered",
            "rendered",
            "none",
            turn_event_id,
            turn,
            prompt_key,
            role_name,
            backend,
            self.current_event_attempt,
            f"Rendered prompt '{prompt_key}'",
            contract_refs=[str(self.prompt_file(prompt_key)), str(role_file)],
        )
        if not self.invoke_agent(backend, role_file, rendered_prompt, prompt_key, prompt_event_id):
            failure_code = self.last_failure_code or "AGENT_EXIT_NONZERO"
            failure_parent = self.last_failure_event_id or prompt_event_id
            self.record_run_failed(failure_parent, failure_code, f"Agent execution failed for {prompt_key}")
            self.fail(f"Agent execution failed for {prompt_key}")
            raise PipelineAbort(124 if failure_code == "AGENT_TIMEOUT" else 1)

    def background_prompt(self, backend: str, role_file: Path, prompt_key: str, turn_event_id: str) -> None:
        self.invoke_prompt(backend, role_file, prompt_key, turn_event_id)
        expected_paths = [self.artifact_path(artifact_id) for artifact_id in self.prompt_expected_artifacts(prompt_key)]
        self.validate_prompt_step_success(
            prompt_key,
            self.last_agent_exit_event_id,
            self.prompt_turn(prompt_key),
            role_file.stem,
            backend,
            self.attempt or 1,
            expected_paths,
        )

    def require_version_evidence(self, artifact_id: str, label: str, expected_version: str) -> bool:
        actual = extract_version_evidence(self.artifact_path(artifact_id), label)
        if actual != expected_version:
            self.fail(
                f"Version evidence mismatch in {self.artifact_path(artifact_id)} for '{label}': expected '{expected_version}', found '{actual}'"
            )
            return False
        return True

    def validate_builder_evidence(self) -> bool:
        try:
            validate_builder(
                load_evidence_json(self.artifact_path("builder_evidence")),
                self.artifact_path("builder_evidence"),
                argparse.Namespace(
                    run_id=self.run_id,
                    lineage_run_ids=[value for value in (self.resumed_from_run_id, self.lineage_root_run_id) if value],
                    attempt=self.attempt,
                    handoff=str(self.artifact_path("builder_handoff")),
                    q13_answers=str(self.artifact_path("q13_answers")),
                    results=str(self.artifact_path("results")),
                ),
            )
            return True
        except ValueError:
            return False

    def validate_reviewer_evidence(self) -> bool:
        try:
            validate_reviewer(
                load_evidence_json(self.artifact_path("reviewer_evidence")),
                self.artifact_path("reviewer_evidence"),
                argparse.Namespace(
                    run_id=self.run_id,
                    lineage_run_ids=[value for value in (self.resumed_from_run_id, self.lineage_root_run_id) if value],
                    attempt=self.attempt,
                    q13_answers=str(self.artifact_path("q13_answers")),
                ),
            )
            return True
        except ValueError:
            return False

    def validate_evaluator_evidence(self) -> bool:
        try:
            validate_evaluator(
                load_evidence_json(self.artifact_path("evaluator_evidence")),
                self.artifact_path("evaluator_evidence"),
                argparse.Namespace(
                    run_id=self.run_id,
                    lineage_run_ids=[value for value in (self.resumed_from_run_id, self.lineage_root_run_id) if value],
                    attempt=self.attempt,
                    holdouts=str(self.artifact_path("d9_holdout_scenarios")),
                    staging_root=str(self.artifact_path("staging_root")),
                ),
            )
            return True
        except ValueError:
            return False

    def validate_final_evidence_suite(self) -> None:
        if self.artifact_path("builder_evidence").exists():
            validate_builder(
                load_evidence_json(self.artifact_path("builder_evidence")),
                self.artifact_path("builder_evidence"),
                argparse.Namespace(
                    run_id=self.run_id,
                    lineage_run_ids=[value for value in (self.resumed_from_run_id, self.lineage_root_run_id) if value],
                    attempt=self.attempt,
                    handoff=str(self.artifact_path("builder_handoff")),
                    q13_answers=str(self.artifact_path("q13_answers")),
                    results=str(self.artifact_path("results")),
                ),
            )
        if self.artifact_path("reviewer_evidence").exists():
            validate_reviewer(
                load_evidence_json(self.artifact_path("reviewer_evidence")),
                self.artifact_path("reviewer_evidence"),
                argparse.Namespace(
                    run_id=self.run_id,
                    lineage_run_ids=[value for value in (self.resumed_from_run_id, self.lineage_root_run_id) if value],
                    attempt=self.attempt,
                    q13_answers=str(self.artifact_path("q13_answers")),
                ),
            )
        if self.artifact_path("evaluator_evidence").exists():
            validate_evaluator(
                load_evidence_json(self.artifact_path("evaluator_evidence")),
                self.artifact_path("evaluator_evidence"),
                argparse.Namespace(
                    run_id=self.run_id,
                    lineage_run_ids=[value for value in (self.resumed_from_run_id, self.lineage_root_run_id) if value],
                    attempt=self.attempt,
                    holdouts=str(self.artifact_path("d9_holdout_scenarios")),
                    staging_root=str(self.artifact_path("staging_root")),
                ),
            )

    def run_turn_a(self) -> None:
        self.heartbeat("phase", "dispatching", "Starting Turn A")
        event_id = self.emit("turn_started", "started", "none", self.run_started_event_id, "A", "turn_a_spec", "spec-agent", self.spec_agent, 1, "Turn A started")
        self.log("═══ TURN A: Specification (D1-D6) ═══")
        self.attempt = 1
        self.invoke_prompt(self.spec_agent, self.spec_role_file, "turn_a_spec", event_id)
        self.validate_prompt_step_success(
            "turn_a_spec",
            self.last_agent_exit_event_id,
            "A",
            "spec-agent",
            self.spec_agent,
            1,
            [self.artifact_path(x) for x in ("d1_constitution", "d2_specification", "d3_data_model", "d4_contracts", "d5_research", "d6_gap_analysis")],
        )
        self.pass_("Turn A produced D1-D6")
        self.update_status_page()
        if not self.run_stage_audit("Turn A"):
            self.record_run_failed(self.last_output_verified_event_id or event_id, "STAGE_AUDIT_FAILED", "Stage audit failed after Turn A")
            raise PipelineAbort(1)
        self.checkpoint("Turn A outputs ready for optional review")

    def run_turn_bc(self) -> None:
        self.log("═══ TURN B + C: Plan (D7-D8-D10) + Holdouts (D9) — parallel ═══")
        self.heartbeat("phase", "dispatching", "Starting Turn B/C")
        turn_b_event_id = ""
        turn_c_event_id = ""
        futures = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            if self.should_run_turn("B"):
                if self.ctx.from_turn == "B" and not self.ensure_artifact_ids("Turn A output", "d1_constitution", "d2_specification", "d3_data_model", "d4_contracts", "d5_research", "d6_gap_analysis"):
                    self.record_run_failed(self.run_started_event_id, "MISSING_INPUT_ARTIFACT", f"Missing Turn A output: {self.last_missing_artifact_path}")
                    raise PipelineAbort(1)
                turn_b_event_id = self.emit("turn_started", "started", "none", self.run_started_event_id, "B", "turn_b_plan", "spec-agent", self.spec_agent, 1, "Turn B started")
                futures.append(("B", pool.submit(self.background_prompt, self.spec_agent, self.spec_role_file, "turn_b_plan", turn_b_event_id)))
            else:
                self.log(f"Skipping Turn B (--from-turn {self.ctx.from_turn})")
            if self.should_run_turn("C"):
                if self.ctx.from_turn == "C" and not self.ensure_artifact_ids("Turn A output", "d2_specification", "d4_contracts"):
                    self.record_run_failed(self.run_started_event_id, "MISSING_INPUT_ARTIFACT", f"Missing Turn A output: {self.last_missing_artifact_path}")
                    raise PipelineAbort(1)
                turn_c_event_id = self.emit("turn_started", "started", "none", self.run_started_event_id, "C", "turn_c_holdout", "holdout-agent", self.holdout_agent, 1, "Turn C started")
                futures.append(("C", pool.submit(self.background_prompt, self.holdout_agent, self.holdout_role_file, "turn_c_holdout", turn_c_event_id)))
            else:
                self.log(f"Skipping Turn C (--from-turn {self.ctx.from_turn})")
            for turn, future in futures:
                future.result()
                self.pass_(f"Turn {turn} produced {'D7, D8, D10, BUILDER_HANDOFF' if turn == 'B' else 'D9 holdout scenarios'}")
        self.update_status_page()
        if not self.run_stage_audit("Turn BC"):
            self.record_run_failed(self.last_output_verified_event_id or self.run_started_event_id, "STAGE_AUDIT_FAILED", "Stage audit failed after Turn BC")
            raise PipelineAbort(1)

    def run_turn_d(self) -> None:
        self.log("═══ TURN D: Build ═══")
        self.heartbeat("phase", "dispatching", f"Starting Turn D attempt {self.attempt + 1}")
        if self.attempt < 0:
            self.attempt = 0
        turn_d_parent_id = self.last_retry_event_id or self.last_turn_completed_event_id or self.run_started_event_id
        turn_d_event_id = self.emit("turn_started", "started", "none", turn_d_parent_id, "D", "turn_d_13q", "builder", self.build_agent, self.attempt + 1, "Turn D started")
        self.last_retry_event_id = ""
        self.last_decision_event_id = ""
        while self.attempt < self.ctx.max_attempts:
            self.attempt += 1
            os.environ["ATTEMPT"] = str(self.attempt)
            self.log(f"Build attempt {self.attempt}/{self.ctx.max_attempts}")
            retry_context = ""
            retry_context = self.append_retry_context("review_errors", f"REVIEW RETRY CONTEXT (attempt {self.attempt})", retry_context)
            retry_context = self.append_retry_context("evaluation_errors", f"EVALUATION RETRY CONTEXT (attempt {self.attempt})", retry_context)
            os.environ["RETRY_CONTEXT"] = retry_context

            self.log("Turn D — Step 1: 13Q Gate")
            self.invoke_prompt(self.build_agent, self.build_role_file, "turn_d_13q", turn_d_event_id)
            if not self.require_version_evidence("q13_answers", "Builder Prompt Contract Version", self.builder_prompt_contract_version):
                failure_event_id = self.emit("output_verified", "failed", "VERSION_EVIDENCE_FAILED", self.last_agent_exit_event_id, "D", "turn_d_13q", "builder", self.build_agent, self.attempt, "Builder prompt contract version evidence check failed")
                self.record_run_failed(failure_event_id, "VERSION_EVIDENCE_FAILED", "Builder prompt contract version evidence check failed")
                raise PipelineAbort(1)
            self.validate_prompt_step_success("turn_d_13q", self.last_agent_exit_event_id, "D", "builder", self.build_agent, self.attempt, [self.artifact_path("q13_answers")])
            self.pass_("Builder produced 13Q answers")

            self.log("Turn D — Step 1.5: Review 13Q answers")
            self.export_evidence_hashes("turn_d_review")
            self.invoke_prompt(self.review_agent, self.review_role_file, "turn_d_review", turn_d_event_id)
            review_agent_exit_event_id = self.last_agent_exit_event_id
            if not self.require_version_evidence("review_report", "Builder Prompt Contract Version Reviewed", self.builder_prompt_contract_version):
                failure_event_id = self.emit("output_verified", "failed", "VERSION_EVIDENCE_FAILED", review_agent_exit_event_id, "D", "turn_d_review", "reviewer", self.review_agent, self.attempt, "Reviewer evidence missing builder contract version")
                self.record_run_failed(failure_event_id, "VERSION_EVIDENCE_FAILED", "Reviewer evidence missing builder contract version")
                raise PipelineAbort(1)
            if not self.require_version_evidence("review_report", "Reviewer Prompt Contract Version", self.reviewer_prompt_contract_version):
                failure_event_id = self.emit("output_verified", "failed", "VERSION_EVIDENCE_FAILED", review_agent_exit_event_id, "D", "turn_d_review", "reviewer", self.review_agent, self.attempt, "Reviewer evidence missing reviewer contract version")
                self.record_run_failed(failure_event_id, "VERSION_EVIDENCE_FAILED", "Reviewer evidence missing reviewer contract version")
                raise PipelineAbort(1)
            if not self.validate_reviewer_evidence():
                failure_event_id = self.emit("output_verified", "failed", "EVIDENCE_VALIDATION_FAILED", review_agent_exit_event_id, "D", "turn_d_review", "reviewer", self.review_agent, self.attempt, "Reviewer evidence validation failed")
                self.record_run_failed(failure_event_id, "EVIDENCE_VALIDATION_FAILED", "Reviewer evidence validation failed")
                raise PipelineAbort(1)
            self.validate_prompt_step_success("turn_d_review", review_agent_exit_event_id, "D", "reviewer", self.review_agent, self.attempt, [self.artifact_path("review_report"), self.artifact_path("review_errors"), self.artifact_path("reviewer_evidence")])

            verdict = parse_review_verdict(self.artifact_path("review_report"))
            if verdict == "PASS":
                self.last_decision_event_id = self.emit("review_verdict_recorded", "pass", "none", review_agent_exit_event_id, "D", "turn_d_review", "reviewer", self.review_agent, self.attempt, "Reviewer approved Turn D implementation")
                self.pass_("Review: PASS")
            elif verdict == "RETRY":
                self.last_decision_event_id = self.emit("review_verdict_recorded", "retry", "REVIEW_RETRY", review_agent_exit_event_id, "D", "turn_d_review", "reviewer", self.review_agent, self.attempt, "Reviewer requested retry")
                self.fail(f"Review: RETRY (attempt {self.attempt}/{self.ctx.max_attempts})")
                if self.attempt >= self.ctx.max_attempts:
                    self.record_escalation(self.last_decision_event_id, "REVIEW_RETRY_EXHAUSTED", f"Build failed after {self.ctx.max_attempts} attempts. Reviewer never approved implementation.")
                    self.heartbeat("decision", "retry_decision", "Review retry budget exhausted")
                    raise PipelineAbort(1)
                self.emit("retry_started", "retrying", "REVIEW_RETRY", self.last_decision_event_id, "D", "turn_d_retry", "orchestrator", "runtime", self.attempt, "Retrying Turn D after reviewer RETRY")
                self.heartbeat("decision", "retry_decision", f"Retrying Turn D after reviewer RETRY (attempt {self.attempt})")
                continue
            elif verdict == "ESCALATE":
                self.last_decision_event_id = self.emit("review_verdict_recorded", "escalate", "REVIEW_ESCALATE", review_agent_exit_event_id, "D", "turn_d_review", "reviewer", self.review_agent, self.attempt, "Reviewer escalated the build")
                self.record_escalation(self.last_decision_event_id, "REVIEW_ESCALATE", f"Review: ESCALATE. See {self.artifact_path('review_report')} and {self.artifact_path('review_errors')}")
                self.heartbeat("decision", "retry_decision", "Reviewer escalated")
                raise PipelineAbort(1)
            else:
                failure_event_id = self.emit("output_verified", "failed", "INVALID_REVIEW_VERDICT", review_agent_exit_event_id, "D", "turn_d_review", "reviewer", self.review_agent, self.attempt, "Reviewer did not produce a parseable verdict")
                self.record_run_failed(failure_event_id, "INVALID_REVIEW_VERDICT", f"Reviewer did not produce a parseable verdict in {self.artifact_path('review_report')}")
                raise PipelineAbort(1)

            self.log("Turn D — Step 2: DTT Build")
            self.export_evidence_hashes("turn_d_build")
            self.invoke_prompt(self.build_agent, self.build_role_file, "turn_d_build", turn_d_event_id)
            build_agent_exit_event_id = self.last_agent_exit_event_id
            if not self.validate_builder_evidence():
                failure_event_id = self.emit("output_verified", "failed", "EVIDENCE_VALIDATION_FAILED", build_agent_exit_event_id, "D", "turn_d_build", "builder", self.build_agent, self.attempt, "Builder evidence validation failed")
                self.record_run_failed(failure_event_id, "EVIDENCE_VALIDATION_FAILED", "Builder evidence validation failed")
                raise PipelineAbort(1)
            self.validate_prompt_step_success("turn_d_build", build_agent_exit_event_id, "D", "builder", self.build_agent, self.attempt, [self.artifact_path("results"), self.artifact_path("builder_evidence"), self.artifact_path("staging_root")])
            self.pass_("Builder produced code and RESULTS.md")
            self.update_status_page()
            if not self.run_stage_audit("Turn D"):
                self.record_run_failed(self.last_output_verified_event_id or build_agent_exit_event_id, "STAGE_AUDIT_FAILED", "Stage audit failed after Turn D")
                raise PipelineAbort(1)
            self.last_turn_completed_event_id = self.emit("turn_completed", "completed", "none", self.last_decision_event_id, "D", "turn_d_build", "builder", self.build_agent, self.attempt, "Turn D completed")
            return

    def run_turn_e(self, parent_event_id: str | None = None, standalone: bool = False) -> None:
        self.log("═══ TURN E: Evaluation ═══")
        self.heartbeat("phase", "dispatching", f"Starting Turn E attempt {self.attempt or 1}")
        if standalone and not self.ensure_artifact_ids("Turn E input", "d9_holdout_scenarios", "staging_root", "results"):
            self.record_run_failed(self.run_started_event_id, "MISSING_INPUT_ARTIFACT", f"Missing Turn E input: {self.last_missing_artifact_path}")
            raise PipelineAbort(1)
        turn_e_event_id = self.emit("turn_started", "started", "none", parent_event_id or self.last_turn_completed_event_id or self.run_started_event_id, "E", "turn_e_eval", "evaluator", self.eval_agent, self.attempt or 1, "Turn E started")
        self.export_evidence_hashes("turn_e_eval")
        self.invoke_prompt(self.eval_agent, self.eval_role_file, "turn_e_eval", turn_e_event_id)
        eval_agent_exit_event_id = self.last_agent_exit_event_id
        if not self.validate_evaluator_evidence():
            failure_event_id = self.emit("output_verified", "failed", "EVIDENCE_VALIDATION_FAILED", eval_agent_exit_event_id, "E", "turn_e_eval", "evaluator", self.eval_agent, self.attempt, "Evaluator evidence validation failed")
            self.record_run_failed(failure_event_id, "EVIDENCE_VALIDATION_FAILED", "Evaluator evidence validation failed")
            raise PipelineAbort(1)
        self.validate_prompt_step_success("turn_e_eval", eval_agent_exit_event_id, "E", "evaluator", self.eval_agent, self.attempt, [self.artifact_path("evaluation_report"), self.artifact_path("evaluation_errors"), self.artifact_path("evaluator_evidence")])
        verdict = parse_evaluation_verdict(self.artifact_path("evaluation_report"))
        if verdict == "PASS":
            self.last_decision_event_id = self.emit("evaluation_verdict_recorded", "pass", "none", eval_agent_exit_event_id, "E", "turn_e_eval", "evaluator", self.eval_agent, self.attempt, "Evaluator returned PASS")
            self.build_passed = True
            self.pass_("Evaluation: PASS")
            self.update_status_page()
            if not self.run_stage_audit("Turn E"):
                self.record_run_failed(self.last_output_verified_event_id or eval_agent_exit_event_id, "STAGE_AUDIT_FAILED", f"Stage audit failed after {'standalone ' if standalone else ''}Turn E")
                raise PipelineAbort(1)
            self.last_turn_completed_event_id = self.emit("turn_completed", "completed", "none", self.last_decision_event_id, "E", "turn_e_eval", "evaluator", self.eval_agent, self.attempt, "Turn E completed")
            self.complete_run(
                self.last_turn_completed_event_id,
                "Run completed with PASS verdict",
                "Convergence validation failed at terminal PASS",
            )
            return
        self.last_decision_event_id = self.emit("evaluation_verdict_recorded", "fail", "EVALUATION_FAIL", eval_agent_exit_event_id, "E", "turn_e_eval", "evaluator", self.eval_agent, self.attempt, "Evaluator returned FAIL")
        self.update_status_page()
        if not self.run_stage_audit("Turn E"):
            self.record_run_failed(self.last_output_verified_event_id or eval_agent_exit_event_id, "STAGE_AUDIT_FAILED", f"Stage audit failed after {'standalone ' if standalone else ''}Turn E")
            raise PipelineAbort(1)
        if standalone or self.attempt >= self.ctx.max_attempts:
            self.record_escalation(self.last_decision_event_id, "EVALUATION_FAIL" if standalone else "EVALUATION_FAIL_EXHAUSTED", "Evaluation: FAIL" if standalone else f"Build failed after {self.ctx.max_attempts} attempts. Returning to spec author.")
            self.heartbeat("decision", "retry_decision", "Evaluation failed with no retries remaining")
            raise PipelineAbort(1)
        self.fail(f"Evaluation: FAIL (attempt {self.attempt}/{self.ctx.max_attempts})")
        self.last_retry_event_id = self.emit("retry_started", "retrying", "EVALUATION_FAIL", self.last_decision_event_id, "E", "turn_e_retry", "orchestrator", "runtime", self.attempt, "Retrying after evaluator FAIL")
        self.heartbeat("decision", "retry_decision", f"Retrying after evaluator FAIL (attempt {self.attempt})")
        return

    def run(self) -> int:
        self.ctx.sawmill_dir.mkdir(parents=True, exist_ok=True)
        self.ctx.holdout_dir.mkdir(parents=True, exist_ok=True)
        self.ctx.staging_dir.mkdir(parents=True, exist_ok=True)
        self.scan_interrupted_runs()
        self.initialize_run_harness()
        self.log(f"Sawmill run: {self.ctx.framework_id}")
        self.log(f"From turn:     {self.ctx.from_turn}")
        self.log(f"Interactive:   {str(self.ctx.interactive).lower()}")
        self.log(f"Operator mode: {self.ctx.operator_mode}")
        self.log(f"Spec agent:    {self.spec_agent}")
        self.log(f"Build agent:   {self.build_agent}")
        self.log(f"Holdout agent: {self.holdout_agent}")
        self.log(f"Review agent:  {self.review_agent}")
        self.log(f"Eval agent:    {self.eval_agent}")
        self.log(f"Audit agent:   {self.audit_agent}")
        print("")
        self.preflight()
        self.invalidate_downstream_artifacts()
        self.update_status_page()

        if self.should_run_turn("A"):
            self.run_turn_a()
        else:
            self.log(f"Skipping Turn A (--from-turn {self.ctx.from_turn})")

        if self.should_run_turn("B") or self.should_run_turn("C"):
            self.run_turn_bc()
        else:
            self.log(f"Skipping Turn B + C (--from-turn {self.ctx.from_turn})")

        if self.should_run_turn("D") and TURN_RANK[self.ctx.from_turn] <= TURN_RANK["C"]:
            if not self.ensure_artifact_ids("Turn B/C outputs", "d7_plan", "d8_tasks", "d10_agent_context", "builder_handoff", "d9_holdout_scenarios"):
                self.record_run_failed(self.run_started_event_id, "MISSING_INPUT_ARTIFACT", f"Missing Turn B/C output: {self.last_missing_artifact_path}")
                raise PipelineAbort(1)
            self.checkpoint("Turn B/C outputs ready for optional review")

        if self.should_run_turn("D"):
            if not self.ensure_artifact_ids("Turn D input", "d10_agent_context", "builder_handoff"):
                self.record_run_failed(self.run_started_event_id, "MISSING_INPUT_ARTIFACT", f"Missing Turn D input: {self.last_missing_artifact_path}")
                raise PipelineAbort(1)
            self.run_turn_d()
            if not self.should_run_turn("E"):
                self.build_passed = True
                self.complete_run(
                    self.last_turn_completed_event_id,
                    "Run completed after Turn D",
                    "Convergence validation failed after Turn D",
                )
            else:
                while not self.build_passed and self.attempt <= self.ctx.max_attempts:
                    self.run_turn_e(parent_event_id=self.last_turn_completed_event_id or self.run_started_event_id)
                    if self.build_passed:
                        break
                    if self.attempt >= self.ctx.max_attempts:
                        break
                    self.run_turn_d()
        elif self.should_run_turn("E"):
            self.attempt = int(os.environ.get("ATTEMPT", "1"))
            self.run_turn_e(standalone=True)
        else:
            self.record_escalation(self.preflight_passed_event_id, "NO_WORK", f"Nothing to do: --from-turn {self.ctx.from_turn} skips all pipeline turns")
            raise PipelineAbort(1)

        if self.build_passed:
            print("")
            self.pass_(f"═══ {self.ctx.framework_id} BUILD COMPLETE ═══")
            self.log(f"Done. Framework {self.ctx.framework_id} completed the pipeline with a PASS verdict.")
            return 0
        self.fail(f"═══ {self.ctx.framework_id} BUILD FAILED ═══")
        return 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Sawmill pipeline")
    parser.add_argument("framework_id")
    parser.add_argument("--from-turn", default="A")
    parser.add_argument("--interactive", "--require-human-gates", action="store_true", dest="interactive")
    parser.add_argument("--unattended", "--auto-approve-gates", action="store_false", dest="interactive")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    from_turn = args.from_turn.upper()
    if from_turn not in TURN_RANK:
        print(f"Invalid --from-turn value: {from_turn} (expected A, B, C, D, or E)", file=sys.stderr)
        return 1
    try:
        timeout = int(os.environ.get("SAWMILL_AGENT_TIMEOUT_SECONDS", "1800"))
    except ValueError:
        print(
            f"SAWMILL_AGENT_TIMEOUT_SECONDS must be a non-negative integer (got '{os.environ.get('SAWMILL_AGENT_TIMEOUT_SECONDS', '')}')",
            file=sys.stderr,
        )
        return 1
    operator_mode = os.environ.get("SAWMILL_OPERATOR_MODE") or ("interactive" if args.interactive else "governed")
    if operator_mode not in {"governed", "interactive", "manual_intervention_allowed"}:
        print("SAWMILL_OPERATOR_MODE must be one of: governed, interactive, manual_intervention_allowed", file=sys.stderr)
        return 1
    ctx = OrchestratorContext(
        framework_id=args.framework_id,
        from_turn=from_turn,
        interactive=bool(args.interactive),
        operator_mode=operator_mode,
        sawmill_dir=ROOT / "sawmill" / args.framework_id,
        holdout_dir=ROOT / ".holdouts" / args.framework_id,
        staging_dir=ROOT / "staging" / args.framework_id,
        branch=f"build/{args.framework_id}",
        max_attempts=3,
        role_registry_path=ROOT / "sawmill/ROLE_REGISTRY.yaml",
        artifact_registry_path=ROOT / "sawmill/ARTIFACT_REGISTRY.yaml",
        prompt_registry_path=ROOT / "sawmill/PROMPT_REGISTRY.yaml",
        agent_timeout_seconds=timeout,
    )
    try:
        return Orchestrator(ctx).run()
    except PipelineAbort as exc:
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
