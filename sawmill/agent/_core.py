"""Agent invocation, backend adapters, and timeout support."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sawmill.run_state import iso_timestamp, new_event_id

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
TRANSPORT_BLOCKED_SECONDS = 30
STALL_SECONDS = 60


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
    cwd = meta.get("cwd") or str(Path(__file__).resolve().parents[2])
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
            "--dangerously-skip-permissions",
            "--no-session-persistence",
        ]
        if meta.get("model_policy") == "max_capability":
            argv.extend(["--model", "opus", "--effort", "max"])
        else:
            argv.extend(["--model", "sonnet", "--effort", "high"])
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
    return {"argv": argv, "env_additions": env_additions, "cwd": cwd}


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


def heartbeat_mtime(path: Path | str | None) -> float:
    if not path:
        return 0.0
    heartbeat_path = Path(path)
    if not heartbeat_path.exists():
        return 0.0
    try:
        return heartbeat_path.stat().st_mtime
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


def run_once(
    meta: dict[str, Any],
    payload_path: Path,
    liveness_path: Path,
    stdout_log: Path,
    stderr_log: Path,
) -> tuple[int, str, bool, str, str]:
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
                chunk = key.fileobj.read1(4096) if hasattr(key.fileobj, "read1") else key.fileobj.read(4096)
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


def main_backend_adapters(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect backend invocation contract")
    parser.add_argument("--backend", required=True)
    parser.add_argument("--payload-path", required=True)
    parser.add_argument("--meta", required=True)
    args = parser.parse_args(argv)
    meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    result = build_invocation(args.backend, args.payload_path, meta)
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def main_runner(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one Sawmill worker invocation packet")
    parser.add_argument("--meta", required=True, help="Path to invocation meta.json")
    args = parser.parse_args(argv)
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
                    f"[backend] retrying (attempt {attempt_index + 1}/{MAX_ATTEMPTS}) after {BACKOFF_SECONDS[attempt_index - 1]}s\n".encode("utf-8")
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


def _append_runtime_event(outcome: str, summary: str) -> None:
    from sawmill.run_state import append_event as append_run_event, project_status, write_status

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
    run_path = Path(run_dir)
    append_run_event(
        run_path,
        {
            "event_id": new_event_id(),
            "run_id": run_id,
            "timestamp": iso_timestamp(),
            "turn": turn,
            "step": step,
            "role": role,
            "backend": backend,
            "attempt": int(attempt),
            "event_type": "agent_liveness_observed",
            "outcome": outcome,
            "failure_code": "none",
            "causal_parent_event_id": parent_id,
            "evidence_refs": [],
            "contract_refs": [],
            "summary": summary,
        },
    )
    write_status(run_path, project_status(run_path))


def _emit_stream(stream_id: str, chunk: bytes) -> None:
    if stream_id == "stdout":
        sys.stdout.buffer.write(chunk)
        sys.stdout.buffer.flush()
    else:
        sys.stderr.buffer.write(chunk)
        sys.stderr.buffer.flush()


def _run_timeout_once(timeout: int, label: str, command: list[str]) -> tuple[int, str]:
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
    _append_runtime_event("alive", f"Worker process alive for {label}")
    captured: list[str] = []
    while True:
        now = time.monotonic()
        if timeout > 0 and now - start >= timeout:
            child.kill()
            child.wait()
            print(f"FAIL: Timed out after {timeout}s while running {label}", file=sys.stderr)
            return 124, "".join(captured)
        current_hb_mtime = heartbeat_mtime(heartbeat_path)
        if current_hb_mtime > last_heartbeat_mtime:
            last_heartbeat_mtime = current_hb_mtime
            last_progress = now
            if observed_state != "progressing":
                _append_runtime_event("progressing", f"Progress observed for {label}")
                observed_state = "progressing"
            progress_seen = True
        events = selector.select(timeout=POLL_SECONDS)
        for key, _ in events:
            chunk = key.fileobj.read1(4096) if hasattr(key.fileobj, "read1") else key.fileobj.read(4096)
            if not chunk:
                continue
            if isinstance(chunk, str):
                chunk = chunk.encode()
            _emit_stream(key.data, chunk)
            captured.append(chunk.decode(errors="replace"))
            last_progress = time.monotonic()
            if observed_state != "progressing":
                _append_runtime_event("progressing", f"Progress observed for {label}")
                observed_state = "progressing"
            progress_seen = True
        returncode = child.poll()
        if returncode is not None:
            for key, _ in selector.select(timeout=0):
                remainder = key.fileobj.read()
                if remainder:
                    if isinstance(remainder, str):
                        remainder = remainder.encode()
                    _emit_stream(key.data, remainder)
                    captured.append(remainder.decode(errors="replace"))
            selector.close()
            return returncode, "".join(captured)
        idle = now - last_progress
        if not progress_seen and idle >= TRANSPORT_BLOCKED_SECONDS and observed_state != "transport_blocked":
            _append_runtime_event("transport_blocked", f"No progress observed for {label}")
            observed_state = "transport_blocked"
        elif progress_seen and idle >= STALL_SECONDS and observed_state != "stalled":
            _append_runtime_event("stalled", f"No recent progress observed for {label}")
            observed_state = "stalled"


def main_timeout_runner(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a command with a timeout")
    parser.add_argument("--timeout", type=int, required=True, help="Timeout in seconds; <= 0 disables timeout")
    parser.add_argument("--label", default="command", help="Human-readable label for error reporting")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute after --")
    args = parser.parse_args(argv)
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("FAIL: Missing command for timeout runner", file=sys.stderr)
        return 1
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            returncode, combined_output = _run_timeout_once(args.timeout, args.label, command)
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


def _shell_assignments(values: dict[str, str]) -> str:
    return "\n".join(f"{key}={shlex.quote(value)}" for key, value in values.items())


def _write_payload(path: Path, role_content: str, prompt: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{role_content}\n\n{prompt}", encoding="utf-8")


def _write_meta(
    path: Path,
    *,
    run_id: str,
    framework_id: str,
    turn: str,
    step: str,
    role: str,
    backend: str,
    attempt: int,
    timeout_seconds: int,
    stdout_log: Path,
    stderr_log: Path,
    heartbeat_file: Path,
    payload_path: Path,
    prompt_key: str,
    model_policy: str,
    operator_mode: str,
    agent_invoked_event_id: str,
    result_path: Path,
    liveness_path: Path,
) -> None:
    write_json(
        path,
        {
            "run_id": run_id,
            "framework_id": framework_id,
            "turn": turn,
            "step": step,
            "role": role,
            "backend": backend,
            "attempt": attempt,
            "timeout_seconds": timeout_seconds,
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "heartbeat_file": str(heartbeat_file),
            "payload_path": str(payload_path),
            "prompt_key": prompt_key,
            "model_policy": model_policy,
            "operator_mode": operator_mode,
            "agent_invoked_event_id": agent_invoked_event_id,
            "result_path": str(result_path),
            "liveness_path": str(liveness_path),
            "cwd": Path.cwd().as_posix(),
        },
    )


def _append_runtime_event_and_project(run_dir: Path, event: dict[str, Any]) -> None:
    from sawmill.run_state import append_event as append_run_event, project_status, write_status

    append_run_event(run_dir, event)
    write_status(run_dir, project_status(run_dir))


def invoke_full(
    *,
    backend: str,
    role_file: Path,
    prompt_file: Path,
    prompt_key: str,
    prompt_event_id: str,
    turn: str,
    attempt: int,
    run_dir: Path,
    run_id: str,
    framework_id: str,
    timeout_seconds: int,
    operator_mode: str,
    model_policy: str,
    prompt: str,
) -> dict[str, str]:
    role_name = role_file.stem
    step_prefix = run_dir / "logs" / f"{prompt_key}.attempt{attempt}"
    stdout_log = Path(f"{step_prefix}.stdout.log")
    stderr_log = Path(f"{step_prefix}.stderr.log")
    heartbeat_file = run_dir / "heartbeats" / f"{prompt_key}.attempt{attempt}.log"
    invocation_prefix = run_dir / "invocations" / f"{prompt_key}.attempt{attempt}"
    payload_path = Path(f"{invocation_prefix}.payload.txt")
    meta_path = Path(f"{invocation_prefix}.meta.json")
    liveness_path = Path(f"{invocation_prefix}.liveness.jsonl")
    result_path = Path(f"{invocation_prefix}.result.json")
    liveness_state_path = Path(f"{invocation_prefix}.liveness.offset")
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
    for path in (stdout_log, stderr_log, liveness_path, heartbeat_file):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    role_content = role_file.read_text(encoding="utf-8")
    _write_payload(payload_path, role_content, prompt)

    agent_invoked_event_id = new_event_id()
    _append_runtime_event_and_project(
        run_dir,
        {
            "event_id": agent_invoked_event_id,
            "run_id": run_id,
            "timestamp": iso_timestamp(),
            "turn": turn,
            "step": prompt_key,
            "role": role_name,
            "backend": backend,
            "attempt": attempt,
            "event_type": "agent_invoked",
            "outcome": "invoked",
            "failure_code": "none",
            "causal_parent_event_id": prompt_event_id,
            "evidence_refs": [str(stdout_log), str(stderr_log), str(payload_path), str(meta_path)],
            "contract_refs": [str(role_file), str(prompt_file)],
            "summary": f"Invoked {backend} for {prompt_key}",
        },
    )

    _write_meta(
        meta_path,
        run_id=run_id,
        framework_id=framework_id,
        turn=turn,
        step=prompt_key,
        role=role_name,
        backend=backend,
        attempt=attempt,
        timeout_seconds=timeout_seconds,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        heartbeat_file=heartbeat_file,
        payload_path=payload_path,
        prompt_key=prompt_key,
        model_policy=model_policy,
        operator_mode=operator_mode,
        agent_invoked_event_id=agent_invoked_event_id,
        result_path=result_path,
        liveness_path=liveness_path,
    )

    child = subprocess.Popen([sys.executable, "-m", "sawmill.agent", "invoke", "--meta", str(meta_path)])
    while child.poll() is None:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "sawmill.run_state",
                "emit-liveness",
                "--liveness-path",
                str(liveness_path),
                "--run-dir",
                str(run_dir),
                "--parent-id",
                agent_invoked_event_id,
                "--turn",
                turn,
                "--step",
                prompt_key,
                "--role",
                role_name,
                "--backend",
                backend,
                "--attempt",
                str(attempt),
                "--state-file",
                str(liveness_state_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1)
    runner_exit_code = child.wait()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "sawmill.run_state",
            "emit-liveness",
            "--liveness-path",
            str(liveness_path),
            "--run-dir",
            str(run_dir),
            "--parent-id",
            agent_invoked_event_id,
            "--turn",
            turn,
            "--step",
            prompt_key,
            "--role",
            role_name,
            "--backend",
            backend,
            "--attempt",
            str(attempt),
            "--state-file",
            str(liveness_state_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    liveness_state_path.unlink(missing_ok=True)

    if stdout_log.stat().st_size:
        sys.stderr.write(stdout_log.read_text(encoding="utf-8"))
    if stderr_log.stat().st_size:
        sys.stderr.write(stderr_log.read_text(encoding="utf-8"))

    last_agent_exit_event_id = ""
    last_failure_event_id = ""
    last_failure_code = ""
    result_outcome = ""
    result_failure_code = ""
    result_exit_code = ""
    result_timed_out = "false"

    if not result_path.exists():
        last_failure_code = "RUNNER_RESULT_MISSING"
        last_failure_event_id = new_event_id()
        _append_runtime_event_and_project(
            run_dir,
            {
                "event_id": last_failure_event_id,
                "run_id": run_id,
                "timestamp": iso_timestamp(),
                "turn": turn,
                "step": prompt_key,
                "role": role_name,
                "backend": backend,
                "attempt": attempt,
                "event_type": "agent_exited",
                "outcome": "failed",
                "failure_code": last_failure_code,
                "causal_parent_event_id": agent_invoked_event_id,
                "evidence_refs": [str(stdout_log), str(stderr_log), str(meta_path), str(liveness_path)],
                "contract_refs": [str(role_file), str(prompt_file)],
                "summary": f"Runner did not produce result.json for {prompt_key}",
            },
        )
        last_agent_exit_event_id = last_failure_event_id
    else:
        result = load_json(result_path)
        result_outcome = str(result["outcome"])
        result_failure_code = str(result["failure_code"])
        result_exit_code = str(result["exit_code"])
        result_timed_out = "true" if result.get("timed_out") else "false"
        if result_timed_out == "true" or result_outcome == "timeout":
            last_failure_code = "AGENT_TIMEOUT"
            last_failure_event_id = new_event_id()
            _append_runtime_event_and_project(
                run_dir,
                {
                    "event_id": last_failure_event_id,
                    "run_id": run_id,
                    "timestamp": iso_timestamp(),
                    "turn": turn,
                    "step": prompt_key,
                    "role": role_name,
                    "backend": backend,
                    "attempt": attempt,
                    "event_type": "timeout_triggered",
                    "outcome": "timeout",
                    "failure_code": last_failure_code,
                    "causal_parent_event_id": agent_invoked_event_id,
                    "evidence_refs": [str(stdout_log), str(stderr_log), str(result_path), str(liveness_path)],
                    "contract_refs": [str(role_file), str(prompt_file)],
                    "summary": f"Timed out while running {backend}:{role_name}",
                },
            )
        elif runner_exit_code != 0 or result_exit_code != "0" or result_outcome == "failed":
            last_failure_code = result_failure_code or "AGENT_EXIT_NONZERO"
            last_failure_event_id = new_event_id()
            _append_runtime_event_and_project(
                run_dir,
                {
                    "event_id": last_failure_event_id,
                    "run_id": run_id,
                    "timestamp": iso_timestamp(),
                    "turn": turn,
                    "step": prompt_key,
                    "role": role_name,
                    "backend": backend,
                    "attempt": attempt,
                    "event_type": "agent_exited",
                    "outcome": "failed",
                    "failure_code": last_failure_code,
                    "causal_parent_event_id": agent_invoked_event_id,
                    "evidence_refs": [str(stdout_log), str(stderr_log), str(result_path), str(liveness_path)],
                    "contract_refs": [str(role_file), str(prompt_file)],
                    "summary": f"Agent exited non-zero for {prompt_key}",
                },
            )
            last_agent_exit_event_id = last_failure_event_id
        else:
            last_agent_exit_event_id = new_event_id()
            _append_runtime_event_and_project(
                run_dir,
                {
                    "event_id": last_agent_exit_event_id,
                    "run_id": run_id,
                    "timestamp": iso_timestamp(),
                    "turn": turn,
                    "step": prompt_key,
                    "role": role_name,
                    "backend": backend,
                    "attempt": attempt,
                    "event_type": "agent_exited",
                    "outcome": "succeeded",
                    "failure_code": "none",
                    "causal_parent_event_id": agent_invoked_event_id,
                    "evidence_refs": [str(stdout_log), str(stderr_log), str(result_path), str(liveness_path)],
                    "contract_refs": [str(role_file), str(prompt_file)],
                    "summary": f"Agent exited successfully for {prompt_key}",
                },
            )

    return {
        "LAST_AGENT_EXIT_EVENT_ID": last_agent_exit_event_id,
        "LAST_FAILURE_EVENT_ID": last_failure_event_id,
        "LAST_FAILURE_CODE": last_failure_code,
        "RESULT_OUTCOME": result_outcome,
        "RESULT_FAILURE_CODE": result_failure_code,
        "RESULT_EXIT_CODE": result_exit_code,
        "RESULT_TIMED_OUT": result_timed_out,
    }


def main_invoke_full(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a full Sawmill agent invocation")
    parser.add_argument("--backend", required=True)
    parser.add_argument("--role-file", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--prompt-key", required=True)
    parser.add_argument("--prompt-event-id", required=True)
    parser.add_argument("--turn", required=True)
    parser.add_argument("--attempt", type=int, required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--framework-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--operator-mode", required=True)
    parser.add_argument("--model-policy", default="default")
    args = parser.parse_args(argv)

    result = invoke_full(
        backend=args.backend,
        role_file=Path(args.role_file),
        prompt_file=Path(args.prompt_file),
        prompt_key=args.prompt_key,
        prompt_event_id=args.prompt_event_id,
        turn=args.turn,
        attempt=args.attempt,
        run_dir=Path(args.run_dir),
        run_id=args.run_id,
        framework_id=args.framework_id,
        timeout_seconds=args.timeout_seconds,
        operator_mode=args.operator_mode,
        model_policy=args.model_policy,
        prompt=sys.stdin.read(),
    )
    print(_shell_assignments(result))
    return 0
