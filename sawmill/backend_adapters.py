#!/usr/bin/env python3
"""Deterministic backend command builders for Sawmill runner invocations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_payload(payload_path: str) -> str:
    return Path(payload_path).read_text(encoding="utf-8")


def _split_payload(payload: str) -> tuple[str, str]:
    parts = payload.split("\n\n", 1)
    if len(parts) != 2:
        raise ValueError("payload.txt must contain role content, blank line, and rendered prompt text")
    return parts[0], parts[1]


def build_invocation(backend: str, payload_path: str, meta: dict[str, Any]) -> dict[str, Any]:
    payload = _read_payload(payload_path)
    role_content, prompt_text = _split_payload(payload)
    framework_id = meta["framework_id"]
    attempt = str(meta["attempt"])
    role = meta["role"]
    cwd = meta.get("cwd") or str(Path(__file__).resolve().parent.parent)

    env_additions = {
        "SAWMILL_ACTIVE_ROLE": role,
        "SAWMILL_ACTIVE_FMWK": framework_id,
        "SAWMILL_HEARTBEAT_FILE": meta["heartbeat_file"],
    }

    if backend == "codex":
        argv = ["codex", "exec", "--full-auto", payload]
    elif backend == "claude":
        argv = [
            "claude",
            "-p",
            prompt_text,
            "--append-system-prompt",
            role_content,
            "--allowedTools",
            "Read,Edit,Write,Glob,Grep,Bash",
        ]
    elif backend == "gemini":
        argv = ["gemini", "-p", payload, "--yolo"]
    elif backend == "mock":
        argv = [
            "python3",
            "sawmill/workers/mock_worker.py",
            "--prompt-key",
            meta["prompt_key"],
            "--role",
            role,
            "--framework",
            framework_id,
            "--attempt",
            attempt,
        ]
        env_additions["SAWMILL_PROMPT_KEY"] = meta["prompt_key"]
        env_additions["SAWMILL_MOCK_PROMPT"] = prompt_text
    else:
        raise ValueError(f"Unsupported backend '{backend}'")

    return {
        "argv": argv,
        "env_additions": env_additions,
        "cwd": cwd,
    }


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Inspect backend invocation contract")
    parser.add_argument("--backend", required=True)
    parser.add_argument("--payload-path", required=True)
    parser.add_argument("--meta", required=True)
    args = parser.parse_args()

    meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    result = build_invocation(args.backend, args.payload_path, meta)
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
