#!/usr/bin/env python3
"""Run a command with timeout, live streaming, transport retries, and liveness observation."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (1, 2, 4)
TRANSPORT_FAILURE_SUBSTRINGS = (
    "stream disconnected",
    "connection reset",
    "unexpected eof",
    "network timeout",
    "timed out",
)
TRANSPORT_FAILURE_EXIT_CODES = {6, 7, 28, 35, 52, 56}
TRANSPORT_BLOCKED_SECONDS = 30
STALL_SECONDS = 60
POLL_SECONDS = 1.0

PROJECTOR = Path(__file__).resolve().parent / "project_run_status.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a command with a timeout")
    parser.add_argument("--timeout", type=int, required=True, help="Timeout in seconds; <= 0 disables timeout")
    parser.add_argument("--label", default="command", help="Human-readable label for error reporting")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute after --")
    return parser.parse_args()


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_event_id() -> str:
    return uuid.uuid4().hex


def append_runtime_event(outcome: str, summary: str) -> None:
    run_dir = os.environ.get("RUN_DIR")
    run_id = os.environ.get("RUN_ID")
    turn = os.environ.get("SAWMILL_LIVENESS_TURN")
    step = os.environ.get("SAWMILL_LIVENESS_STEP")
    role = os.environ.get("SAWMILL_LIVENESS_ROLE")
    backend = os.environ.get("SAWMILL_LIVENESS_BACKEND")
    attempt = os.environ.get("SAWMILL_LIVENESS_ATTEMPT")
    parent_id = os.environ.get("SAWMILL_AGENT_INVOKED_EVENT_ID")

    if not all([run_dir, run_id, turn, step, role, backend, attempt, parent_id]):
        return

    cmd = [
        "python3",
        str(PROJECTOR),
        "append-event",
        "--run-dir",
        run_dir,
        "--event-id",
        new_event_id(),
        "--run-id",
        run_id,
        "--timestamp",
        iso_timestamp(),
        "--turn",
        turn,
        "--step",
        step,
        "--role",
        role,
        "--backend",
        backend,
        "--attempt",
        attempt,
        "--event-type",
        "agent_liveness_observed",
        "--outcome",
        outcome,
        "--failure-code",
        "none",
        "--causal-parent-event-id",
        parent_id,
        "--summary",
        summary,
    ]
    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(
        ["python3", str(PROJECTOR), "project-status", "--run-dir", run_dir],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def is_transport_failure(returncode: int, combined_output: str) -> bool:
    lowered = combined_output.lower()
    if returncode in TRANSPORT_FAILURE_EXIT_CODES:
        return True
    return any(marker in lowered for marker in TRANSPORT_FAILURE_SUBSTRINGS)


def heartbeat_mtime(path: str | None) -> float:
    if not path:
        return 0.0
    hb = Path(path)
    if not hb.exists():
        return 0.0
    try:
        return hb.stat().st_mtime
    except OSError:
        return 0.0


def emit_stream(stream_id: str, chunk: bytes) -> None:
    if stream_id == "stdout":
        sys.stdout.buffer.write(chunk)
        sys.stdout.buffer.flush()
    else:
        sys.stderr.buffer.write(chunk)
        sys.stderr.buffer.flush()


def run_once(args: argparse.Namespace, command: list[str]) -> tuple[int, str]:
    heartbeat_path = os.environ.get("SAWMILL_HEARTBEAT_FILE")
    child = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        env=os.environ.copy(),
    )

    assert child.stdout is not None
    assert child.stderr is not None

    selector = selectors.DefaultSelector()
    selector.register(child.stdout, selectors.EVENT_READ, "stdout")
    selector.register(child.stderr, selectors.EVENT_READ, "stderr")

    start = time.monotonic()
    last_progress = start
    last_heartbeat_mtime = heartbeat_mtime(heartbeat_path)
    progress_seen = False
    observed_state = "alive"
    append_runtime_event("alive", f"Worker process alive for {args.label}")
    captured: list[str] = []

    while True:
        now = time.monotonic()
        if args.timeout > 0 and now - start >= args.timeout:
            child.kill()
            child.wait()
            print(f"FAIL: Timed out after {args.timeout}s while running {args.label}", file=sys.stderr)
            return 124, "".join(captured)

        current_hb_mtime = heartbeat_mtime(heartbeat_path)
        if current_hb_mtime > last_heartbeat_mtime:
            last_heartbeat_mtime = current_hb_mtime
            last_progress = now
            if observed_state != "progressing":
                append_runtime_event("progressing", f"Progress observed for {args.label}")
                observed_state = "progressing"
            progress_seen = True

        events = selector.select(timeout=POLL_SECONDS)
        for key, _ in events:
            chunk = key.fileobj.read1(4096) if hasattr(key.fileobj, "read1") else key.fileobj.read(4096)
            if not chunk:
                continue
            if isinstance(chunk, str):
                chunk = chunk.encode()
            emit_stream(key.data, chunk)
            text = chunk.decode(errors="replace")
            captured.append(text)
            last_progress = time.monotonic()
            if observed_state != "progressing":
                append_runtime_event("progressing", f"Progress observed for {args.label}")
                observed_state = "progressing"
            progress_seen = True

        returncode = child.poll()
        if returncode is not None:
            for key, _ in selector.select(timeout=0):
                remainder = key.fileobj.read()
                if remainder:
                    if isinstance(remainder, str):
                        remainder = remainder.encode()
                    emit_stream(key.data, remainder)
                    captured.append(remainder.decode(errors="replace"))
            selector.close()
            return returncode, "".join(captured)

        idle = now - last_progress
        if not progress_seen and idle >= TRANSPORT_BLOCKED_SECONDS and observed_state != "transport_blocked":
            append_runtime_event("transport_blocked", f"No progress observed for {args.label}")
            observed_state = "transport_blocked"
        elif progress_seen and idle >= STALL_SECONDS and observed_state != "stalled":
            append_runtime_event("stalled", f"No recent progress observed for {args.label}")
            observed_state = "stalled"


def main() -> int:
    args = parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("FAIL: Missing command for timeout runner", file=sys.stderr)
        return 1

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            returncode, combined_output = run_once(args, command)
        except FileNotFoundError as exc:
            print(f"FAIL: Unable to execute {args.label}: {exc}", file=sys.stderr)
            return 127

        if returncode == 0:
            return 0

        if attempt < MAX_ATTEMPTS and is_transport_failure(returncode, combined_output):
            print("[backend] transport failure detected", file=sys.stderr)
            print(
                f"[backend] retrying (attempt {attempt + 1}/{MAX_ATTEMPTS}) after {BACKOFF_SECONDS[attempt - 1]}s",
                file=sys.stderr,
            )
            time.sleep(BACKOFF_SECONDS[attempt - 1])
            continue

        return returncode

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
