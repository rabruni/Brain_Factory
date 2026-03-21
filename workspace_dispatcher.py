#!/usr/bin/env python3
"""
Workspace dispatcher for headless Codex workers.

Polls the workspace for claimable items addressed to configured worker names,
claims them, runs `codex exec`, and posts results back into the thread.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import tempfile
import textwrap
import threading
import time
from typing import Any

import workspace as ws


REPO_DIR = pathlib.Path(__file__).parent

WORKER_PROFILES: dict[str, dict[str, Any]] = {
    "codex-builder": {
        "instructions": "You are a code builder. Implement the requested change in the current repository. Verify your work before replying.",
        "description": "Headless Codex builder worker",
        "capabilities": ["workspace-dispatch", "build", "code-editing"],
        "task_types": ["plan", "handoff", "prompt", "results", "question"],
        "context_mode": "full_thread",
        "context_n": 0,
        "timeout": 300,
        "sandbox": "workspace-write",
        "max_retries": 3,
    },
    "codex-reviewer": {
        "instructions": "You are a code reviewer. Review the task and current code changes. Focus on bugs, regressions, and missing tests.",
        "description": "Headless Codex reviewer worker",
        "capabilities": ["workspace-dispatch", "review", "code-review"],
        "task_types": ["review", "results", "prompt", "question"],
        "context_mode": "last_n",
        "context_n": 3,
        "timeout": 180,
        "sandbox": "read-only",
        "max_retries": 2,
    },
    "codex-researcher": {
        "instructions": "You are a researcher. Analyze the repository and answer the question directly and concretely.",
        "description": "Headless Codex researcher worker",
        "capabilities": ["workspace-dispatch", "research", "analysis"],
        "task_types": ["question", "prompt", "results"],
        "context_mode": "task_only",
        "context_n": 0,
        "timeout": 120,
        "sandbox": "read-only",
        "max_retries": 1,
    },
}


OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "content": {"type": "string"},
        "route_to": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
        },
        "needs_human": {"type": "boolean", "default": False},
    },
    "required": ["summary", "content", "route_to", "needs_human"],
}


def build_prompt(item: dict[str, Any], profile: dict[str, Any]) -> str:
    parts = [
        f"WORKER PROFILE: {profile['instructions']}",
        "Return your final answer strictly as JSON matching the provided output schema.",
        "If you are unsure where the result should go, route it back to the original sender.",
        "Use needs_human=true only when you cannot complete the task safely.",
    ]

    mode = profile["context_mode"]
    if mode == "full_thread":
        turns = ws.get_thread(item["thread_id"])
    elif mode == "last_n":
        turns = ws.get_thread(item["thread_id"])[-profile["context_n"] :]
    else:
        turns = [item]

    context_lines = []
    for turn in turns:
        content = (turn.get("content", "") or "").strip()
        if len(content) > 1500:
            content = content[:1500] + "\n...[truncated]"
        context_lines.append(
            f"[{turn.get('created_at', '')}] {turn.get('from_agent', turn.get('from_cli', '?'))}"
            f" -> {turn.get('to', '?')} ({turn.get('type', '?')} / {turn.get('status', '?')})\n"
            f"Summary: {turn.get('summary', '')}\n"
            f"{content}"
        )

    parts.append("THREAD CONTEXT:\n" + "\n\n".join(context_lines))
    parts.append(
        textwrap.dedent(
            f"""
            ACTIVE TASK
            - workspace item id: {item['id']}
            - reply_to: {item['id']}
            - original sender: {item.get('from_agent', item.get('from_cli', 'human'))}
            - current recipients: {item.get('to', '')}
            - execution_depth: {item.get('execution_depth', item.get('depth', 0))}
            - max_depth: {item.get('max_depth', ws.DEFAULT_MAX_DEPTH)}

            TASK CONTENT:
            {item.get('content', '')}
            """
        ).strip()
    )
    return "\n\n".join(parts)


def parse_output(output_path: pathlib.Path) -> dict[str, Any]:
    raw = output_path.read_text(encoding="utf-8").strip()
    data = json.loads(raw)
    data["summary"] = data.get("summary", "").strip() or "Codex worker result"
    data["content"] = data.get("content", "").strip()
    data["route_to"] = [r.strip() for r in data.get("route_to", []) if str(r).strip()]
    data["needs_human"] = bool(data.get("needs_human", False))
    return data


def run_worker(worker_name: str, profile: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    prompt = build_prompt(item, profile)
    with tempfile.TemporaryDirectory(prefix="codex-dispatch-") as tmpdir:
        tmp = pathlib.Path(tmpdir)
        schema_path = tmp / "output_schema.json"
        last_message_path = tmp / "last_message.json"
        schema_path.write_text(json.dumps(OUTPUT_SCHEMA), encoding="utf-8")

        command = [
            "codex",
            "exec",
            "--full-auto",
            "--json",
            f"--sandbox={profile['sandbox']}",
            "--cd",
            str(REPO_DIR),
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(last_message_path),
            prompt,
        ]
        process = subprocess.Popen(
            command,
            cwd=str(REPO_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stop_event = threading.Event()

        def _lease_watchdog():
            while not stop_event.wait(60):
                ws.renew_claim(item["id"], worker_name, lease_seconds=profile["timeout"])

        watchdog = threading.Thread(target=_lease_watchdog, daemon=True)
        watchdog.start()
        try:
            stdout, stderr = process.communicate(timeout=profile["timeout"])
        finally:
            stop_event.set()
            watchdog.join(timeout=1)
        result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"codex exec failed: {result.returncode}")
        if not last_message_path.exists():
            raise RuntimeError("codex exec did not produce an output file")
        return parse_output(last_message_path)


def deliver_result(worker_name: str, item: dict[str, Any], payload: dict[str, Any]) -> None:
    route_to = payload.get("route_to") or [item.get("from_agent", item.get("from_cli", "human"))]
    current_execution_depth = int(item.get("execution_depth", item.get("depth", 0)) or 0)
    next_execution_depth = current_execution_depth + 1
    max_depth = int(item.get("max_depth", ws.DEFAULT_MAX_DEPTH) or ws.DEFAULT_MAX_DEPTH)
    next_depth = int(item.get("depth", 0) or 0) + 1
    non_human_targets = [target for target in route_to if target not in {"human", "any"}]

    if next_execution_depth >= max_depth and non_human_targets:
        route_to = ["human"]
        payload["content"] += "\n\nDispatcher note: rerouted to human because max depth was reached."

    if payload.get("needs_human"):
        route_to = ["human"]

    ws.create_item(
        item_type="results",
        from_cli="codex",
        from_agent=worker_name,
        to=route_to,
        summary=payload["summary"],
        content=payload["content"],
        reply_to=item["id"],
        depth=next_depth,
        max_depth=max_depth,
        work_root_id=item.get("work_root_id") or item.get("id"),
        work_parent_id=item.get("id") if any(target not in {"human", "any"} for target in route_to) else item.get("work_parent_id", ""),
        execution_depth=next_execution_depth if any(target not in {"human", "any"} for target in route_to) else current_execution_depth,
    )
    ws.update_status(item["id"], "read", actor=worker_name)
    ws.record_run_result(item["id"], 0, "", increment_retry=False)
    ws.release_claim(item["id"], worker_name=worker_name)


def handle_item(worker_name: str, profile: dict[str, Any], item: dict[str, Any]) -> None:
    max_retries = profile["max_retries"]
    ws.set_max_retries(item["id"], max_retries)
    if int(item.get("retry_count", 0) or 0) >= max_retries:
        ws.mark_needs_human(item["id"], actor=worker_name, reason="Retry limit exhausted")
        return
    if int(item.get("execution_depth", item.get("depth", 0)) or 0) >= int(item.get("max_depth", ws.DEFAULT_MAX_DEPTH) or ws.DEFAULT_MAX_DEPTH):
        ws.mark_needs_human(item["id"], actor=worker_name, reason="Max depth reached")
        return
    if not ws.claim_item(item["id"], worker_name, lease_seconds=profile["timeout"]):
        return

    # list_items strips content — fetch full item for prompt assembly
    full_item = ws.get_item(item["id"])
    if "error" in full_item:
        ws.release_claim(item["id"], worker_name=worker_name)
        return

    try:
        payload = run_worker(worker_name, profile, full_item)
        deliver_result(worker_name, item, payload)
    except subprocess.TimeoutExpired:
        ws.record_run_result(item["id"], 124, "codex exec timed out", increment_retry=True)
        ws.release_claim(item["id"], worker_name=worker_name)
        ws.add_comment(item["id"], worker_name, "Dispatcher note: worker timed out.")
    except Exception as exc:
        ws.record_run_result(item["id"], 1, str(exc), increment_retry=True)
        ws.release_claim(item["id"], worker_name=worker_name)
        ws.add_comment(item["id"], worker_name, f"Dispatcher note: {str(exc)[:400]}")


def run_once(worker_names: list[str] | None = None) -> None:
    ws.expire_stale_claims()
    profiles = WORKER_PROFILES
    for worker_name, profile in profiles.items():
        if worker_names and worker_name not in worker_names:
            continue
        allowed_types = set(profile["task_types"])
        items = ws.get_claimable_items(worker_name)
        for item in items:
            if item.get("type") not in allowed_types:
                continue
            handle_item(worker_name, profile, item)


def ensure_workers_registered(worker_names: list[str] | None = None) -> None:
    existing_tokens = {tok.get("label", ""): tok for tok in ws.list_agent_tokens()}
    for worker_name, profile in WORKER_PROFILES.items():
        if worker_names and worker_name not in worker_names:
            continue
        if worker_name not in existing_tokens:
            ws.create_token(worker_name)
        ws.register_agent(
            worker_name,
            "codex",
            profile.get("description", f"Headless worker for {worker_name}"),
            profile.get("capabilities", ["workspace-dispatch"]),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Workspace dispatcher for Codex workers")
    parser.add_argument("--once", action="store_true", help="Run a single polling pass and exit")
    parser.add_argument("--poll-seconds", type=int, default=10, help="Polling interval in seconds")
    parser.add_argument("--worker", action="append", dest="workers", help="Only run specific worker profile(s)")
    args = parser.parse_args()

    ensure_workers_registered(worker_names=args.workers)

    if args.once:
        run_once(worker_names=args.workers)
        return

    while True:
        run_once(worker_names=args.workers)
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
