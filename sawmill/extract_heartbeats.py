#!/usr/bin/env python3
"""Extract derived heartbeat records from Sawmill run sidecar heartbeat files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HEARTBEAT_PREFIX = "SAWMILL_HEARTBEAT: "
HEARTBEAT_FILE_PATTERN = re.compile(r"^(?P<step>.+)\.attempt(?P<attempt>\d+)\.log$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract derived heartbeat records from a Sawmill run")
    parser.add_argument("--run-dir", required=True, help="Path to sawmill/<FMWK>/runs/<run-id>")
    return parser.parse_args()


def load_events(events_path: Path) -> list[dict]:
    events: list[dict] = []
    if not events_path.exists():
        return events
    for line in events_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        events.append(json.loads(raw))
    return events


def role_index_by_step_attempt(events: list[dict]) -> dict[tuple[str, int], str]:
    index: dict[tuple[str, int], str] = {}
    for event in events:
        if event.get("event_type") != "agent_invoked":
            continue
        role = event.get("role", "")
        attempt = int(event.get("attempt", 0))
        step = event.get("step", "")
        if step:
            index[(step, attempt)] = role
    return index


def fallback_role(step: str) -> str:
    step_role_map = {
        "turn_a_spec": "spec-agent",
        "turn_b_plan": "spec-agent",
        "turn_c_holdout": "holdout-agent",
        "turn_d_13q": "builder",
        "turn_d_review": "reviewer",
        "turn_d_build": "builder",
        "turn_e_eval": "evaluator",
        "portal_stage": "portal-steward",
    }
    return step_role_map.get(step, "unknown")


def parse_sidecar_filename(heartbeat_path: Path) -> tuple[str, int | None]:
    match = HEARTBEAT_FILE_PATTERN.match(heartbeat_path.name)
    if not match:
        return "unknown", None
    return match.group("step"), int(match.group("attempt"))


def extract(run_dir: Path) -> list[dict]:
    events = load_events(run_dir / "events.jsonl")
    role_index = role_index_by_step_attempt(events)
    records: list[dict] = []

    for heartbeat_path in sorted((run_dir / "heartbeats").glob("*.log")):
        relative_source = heartbeat_path.relative_to(run_dir)
        step, attempt = parse_sidecar_filename(heartbeat_path)
        role = role_index.get((step, attempt if attempt is not None else 0), fallback_role(step))

        for line in heartbeat_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith(HEARTBEAT_PREFIX):
                continue
            message = line[len(HEARTBEAT_PREFIX):].strip()
            records.append(
                {
                    "source": str(relative_source),
                    "type": "agent_heartbeat",
                    "role": role,
                    "attempt": attempt,
                    "message": message,
                }
            )
    return records


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: missing run dir: {run_dir}", file=sys.stderr)
        return 1
    for record in extract(run_dir):
        print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
