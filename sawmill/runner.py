#!/usr/bin/env python3
"""Execute one Sawmill worker invocation from an explicit packet."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend_adapters import build_invocation


MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (1, 2, 4)
TRANSPORT_FAILURE_SUBSTRINGS = (
    "stream disconnected",
    "connection reset",
    "unexpected eof",
    "network timeout",
    "timed out",
    "failed to lookup address information",
)
TRANSPORT_FAILURE_EXIT_CODES = {6, 7, 28, 35, 52, 56}
POLL_SECONDS = 1.0
ALIVE_HEARTBEAT_SECONDS = 5.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one Sawmill worker invocation packet")
    parser.add_argument("--meta", required=True, help="Path to invocation meta.json")
    return parser.parse_args()


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_liveness(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def heartbeat_mtime(path: Path) -> float:
    if not path.exists():
        return 0.0
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def is_transport_failure(returncode: int, combined_output: str) -> bool:
    lowered = combined_output.lower()
    if returncode in TRANSPORT_FAILURE_EXIT_CODES:
        return True
    return any(marker in lowered for marker in TRANSPORT_FAILURE_SUBSTRINGS)


def liveness_record(meta: dict[str, Any], observation: str, source: str) -> dict[str, Any]:
    return {
        "timestamp": iso_timestamp(),
        "run_id": meta["run_id"],
        "step": meta["step"],
        "role": meta["role"],
        "backend": meta["backend"],
        "attempt": meta["attempt"],
        "observation": observation,
        "source": source,
    }


def run_once(meta: dict[str, Any], payload_path: Path, liveness_path: Path, stdout_log: Path, stderr_log: Path) -> tuple[int, str, bool, str, str]:
    invocation = build_invocation(meta["backend"], str(payload_path), meta)
    env = os.environ.copy()
    env.update(invocation["env_additions"])

    heartbeat_path = Path(meta["heartbeat_file"])
    command = invocation["argv"]
    timeout_seconds = int(meta["timeout_seconds"])

    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    stderr_log.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = stdout_log.open("ab")
    stderr_handle = stderr_log.open("ab")
    selector = selectors.DefaultSelector()
    child: subprocess.Popen[bytes] | None = None
    try:
        child = subprocess.Popen(
            command,
            cwd=invocation["cwd"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        assert child.stdout is not None
        assert child.stderr is not None

        append_liveness(liveness_path, liveness_record(meta, "started", "process_alive"))
        selector.register(child.stdout, selectors.EVENT_READ, "stdout")
        selector.register(child.stderr, selectors.EVENT_READ, "stderr")

        start = time.monotonic()
        last_output_at = ""
        last_progress_at = ""
        last_heartbeat_seen = heartbeat_mtime(heartbeat_path)
        last_alive_emit = start
        captured: list[str] = []

        while True:
            now = time.monotonic()
            if timeout_seconds > 0 and now - start >= timeout_seconds:
                child.kill()
                child.wait()
                append_liveness(liveness_path, liveness_record(meta, "timed_out", "timeout"))
                stderr_handle.write(
                    f"FAIL: Timed out after {timeout_seconds}s while running {meta['backend']}:{meta['role']}\n".encode("utf-8")
                )
                stderr_handle.flush()
                return 124, "".join(captured), True, last_output_at, last_progress_at

            if now - last_alive_emit >= ALIVE_HEARTBEAT_SECONDS:
                append_liveness(liveness_path, liveness_record(meta, "alive", "process_alive"))
                last_alive_emit = now

            current_hb = heartbeat_mtime(heartbeat_path)
            if current_hb > last_heartbeat_seen:
                last_heartbeat_seen = current_hb
                last_progress_at = iso_timestamp()
                append_liveness(liveness_path, liveness_record(meta, "heartbeat_seen", "heartbeat_file"))
                append_liveness(liveness_path, liveness_record(meta, "progressing", "heartbeat_file"))

            events = selector.select(timeout=POLL_SECONDS)
            for key, _ in events:
                if hasattr(key.fileobj, "read1"):
                    chunk = key.fileobj.read1(4096)
                else:
                    chunk = key.fileobj.read(4096)
                if not chunk:
                    continue
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                if key.data == "stdout":
                    stdout_handle.write(chunk)
                    stdout_handle.flush()
                    append_liveness(liveness_path, liveness_record(meta, "output_seen", "stdout"))
                    append_liveness(liveness_path, liveness_record(meta, "progressing", "stdout"))
                    last_output_at = iso_timestamp()
                    last_progress_at = last_output_at
                else:
                    stderr_handle.write(chunk)
                    stderr_handle.flush()
                captured.append(chunk.decode(errors="replace"))

            returncode = child.poll()
            if returncode is not None:
                for key, _ in selector.select(timeout=0):
                    remainder = key.fileobj.read()
                    if not remainder:
                        continue
                    if isinstance(remainder, str):
                        remainder = remainder.encode("utf-8")
                    if key.data == "stdout":
                        stdout_handle.write(remainder)
                        stdout_handle.flush()
                        last_output_at = iso_timestamp()
                        if not last_progress_at:
                            last_progress_at = last_output_at
                    else:
                        stderr_handle.write(remainder)
                        stderr_handle.flush()
                    captured.append(remainder.decode(errors="replace"))
                append_liveness(liveness_path, liveness_record(meta, "exited", "process_alive"))
                return returncode, "".join(captured), False, last_output_at, last_progress_at
    finally:
        selector.close()
        if child is not None and child.poll() is None:
            child.kill()
            child.wait()
        stdout_handle.close()
        stderr_handle.close()


def main() -> int:
    args = parse_args()
    meta_path = Path(args.meta)
    meta = load_json(meta_path)
    payload_path = Path(meta["payload_path"])
    liveness_path = Path(meta["liveness_path"])
    stdout_log = Path(meta["stdout_log"])
    stderr_log = Path(meta["stderr_log"])
    result_path = Path(meta["result_path"])

    started_at = iso_timestamp()
    combined_output = ""
    final_returncode = 1
    timed_out = False
    last_output_at = ""
    last_progress_at = ""
    transport_retries = 0

    for attempt_index in range(1, MAX_ATTEMPTS + 1):
        final_returncode, combined_output, timed_out, last_output_at, last_progress_at = run_once(
            meta, payload_path, liveness_path, stdout_log, stderr_log
        )
        if final_returncode == 0:
            break
        if attempt_index < MAX_ATTEMPTS and is_transport_failure(final_returncode, combined_output):
            transport_retries += 1
            with stderr_log.open("ab") as handle:
                handle.write(b"[backend] transport failure detected\n")
                handle.write(
                    f"[backend] retrying (attempt {attempt_index + 1}/{MAX_ATTEMPTS}) after {BACKOFF_SECONDS[attempt_index - 1]}s\n".encode(
                        "utf-8"
                    )
                )
            time.sleep(BACKOFF_SECONDS[attempt_index - 1])
            continue
        break

    failure_code = "none"
    outcome = "succeeded"
    if timed_out or final_returncode == 124:
        failure_code = "AGENT_TIMEOUT"
        outcome = "timeout"
    elif final_returncode != 0:
        failure_code = "AGENT_EXIT_NONZERO"
        outcome = "failed"

    write_json(
        result_path,
        {
            "run_id": meta["run_id"],
            "framework_id": meta["framework_id"],
            "turn": meta["turn"],
            "step": meta["step"],
            "role": meta["role"],
            "backend": meta["backend"],
            "attempt": meta["attempt"],
            "started_at": started_at,
            "ended_at": iso_timestamp(),
            "exit_code": final_returncode,
            "outcome": outcome,
            "failure_code": failure_code,
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "heartbeat_file": meta["heartbeat_file"],
            "last_output_at": last_output_at,
            "last_worker_progress_at": last_progress_at,
            "timed_out": timed_out,
            "transport_retries": transport_retries,
            "payload_path": str(payload_path),
            "meta_path": str(meta_path),
            "liveness_path": str(liveness_path),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
