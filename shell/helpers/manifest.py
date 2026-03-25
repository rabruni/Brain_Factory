from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

from shell.config import ACTIVE_HEARTBEAT_SECONDS, ACTIVE_RUN_STATES, CLAUDE_EFFORTS, CLAUDE_MODELS, CODEX_MODELS, GEMINI_MODELS, LAUNCH_MANIFEST_FILENAME, ROLE_REGISTRY_PATH, SAWMILL_DIR
from shell.helpers.run_state import run_dirs, run_summary


def load_role_registry() -> dict:
    data = yaml.safe_load(ROLE_REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def registry_role_defaults() -> list[dict]:
    registry = load_role_registry()
    roles = registry.get("roles", {})
    if not isinstance(roles, dict):
        return []
    rows = []
    for role_name, meta in roles.items():
        if not isinstance(meta, dict):
            continue
        rows.append(
            {
                "name": role_name,
                "backend": str(meta.get("backend", "")),
                "model": str(meta.get("model", "default")),
                "effort": str(meta.get("effort", "default")),
                "allowed_backends": [str(v) for v in meta.get("allowed_backends", [])],
                "env_override": str(meta.get("env_override", "")),
                "source": "registry default",
                "env_override_active": bool(meta.get("env_override") and os.environ.get(str(meta.get("env_override", "")))),
                "env_override_value": os.environ.get(str(meta.get("env_override", "")), ""),
            }
        )
    return rows


def framework_dirs() -> list[dict]:
    rows = []
    if not SAWMILL_DIR.exists():
        return rows
    for framework_dir in sorted(path for path in SAWMILL_DIR.iterdir() if path.is_dir()):
        task_path = framework_dir / "TASK.md"
        if task_path.exists():
            rows.append(
                {
                    "framework_id": framework_dir.name,
                    "task_path": str(task_path),
                    "manifest_exists": (framework_dir / LAUNCH_MANIFEST_FILENAME).exists(),
                }
            )
    return rows


def manifest_path(fmwk_id: str) -> Path:
    return SAWMILL_DIR / fmwk_id / LAUNCH_MANIFEST_FILENAME


def build_manifest_view(fmwk_id: str) -> dict:
    framework_dir = SAWMILL_DIR / fmwk_id
    if not framework_dir.is_dir() or not (framework_dir / "TASK.md").exists():
        raise ValueError(f"Unknown framework: {fmwk_id}")
    registry_rows = registry_role_defaults()
    path = manifest_path(fmwk_id)
    manifest = {}
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest_roles = manifest.get("roles", {}) if isinstance(manifest, dict) else {}
    rows = []
    for role in registry_rows:
        override = manifest_roles.get(role["name"], {}) if isinstance(manifest_roles, dict) else {}
        row = dict(role)
        if isinstance(override, dict) and override:
            row["backend"] = str(override.get("backend", row["backend"]))
            row["model"] = str(override.get("model", row["model"]))
            row["effort"] = str(override.get("effort", row["effort"]))
            row["source"] = "manifest override"
        rows.append(row)
    return {
        "framework": fmwk_id,
        "label": "Requested config",
        "manifest_exists": path.exists(),
        "manifest_path": str(path),
        "roles": rows,
    }


def validate_manifest_payload(fmwk_id: str, payload: dict) -> dict:
    registry_roles = {row["name"]: row for row in registry_role_defaults()}
    roles = payload.get("roles", {})
    if not isinstance(roles, dict):
        raise ValueError("roles must be an object")
    manifest_roles: dict[str, dict[str, str]] = {}
    for role_name, config in roles.items():
        if role_name not in registry_roles:
            raise ValueError(f"Unknown role '{role_name}'")
        if not isinstance(config, dict):
            raise ValueError(f"Role '{role_name}' config must be an object")
        backend = str(config.get("backend", registry_roles[role_name]["backend"]))
        if backend not in registry_roles[role_name]["allowed_backends"]:
            raise ValueError(
                f"Role '{role_name}' backend '{backend}' is not allowed ({registry_roles[role_name]['allowed_backends']})"
            )
        model = str(config.get("model", registry_roles[role_name]["model"] or "default"))
        effort = str(config.get("effort", registry_roles[role_name]["effort"] or "default"))
        manifest_roles[role_name] = {"backend": backend, "model": model, "effort": effort}
    return {
        "framework": fmwk_id,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_by": "human",
        "roles": manifest_roles,
    }


def write_manifest(fmwk_id: str, payload: dict) -> dict:
    manifest = validate_manifest_payload(fmwk_id, payload)
    path = manifest_path(fmwk_id)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def ensure_manifest(fmwk_id: str) -> dict:
    path = manifest_path(fmwk_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    payload = {
        "roles": {
            role["name"]: {"backend": role["backend"], "model": role["model"], "effort": role["effort"]}
            for role in registry_role_defaults()
        }
    }
    return write_manifest(fmwk_id, payload)


def framework_has_active_run(fmwk_id: str) -> bool:
    for run_dir in run_dirs():
        summary = run_summary(run_dir)
        if (
            summary.get("framework") == fmwk_id
            and summary.get("state") in ACTIVE_RUN_STATES
            and summary.get("heartbeat_age_seconds") is not None
            and summary.get("heartbeat_age_seconds") <= ACTIVE_HEARTBEAT_SECONDS
        ):
            return True
    return False

