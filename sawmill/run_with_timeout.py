#!/usr/bin/env python3
"""Run a command with an optional timeout, streaming stdout/stderr directly."""

from __future__ import annotations

import argparse
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a command with a timeout")
    parser.add_argument("--timeout", type=int, required=True, help="Timeout in seconds; <= 0 disables timeout")
    parser.add_argument("--label", default="command", help="Human-readable label for error reporting")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute after --")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("FAIL: Missing command for timeout runner", file=sys.stderr)
        return 1

    try:
        completed = subprocess.run(command, timeout=None if args.timeout <= 0 else args.timeout)
    except subprocess.TimeoutExpired:
        print(
            f"FAIL: Timed out after {args.timeout}s while running {args.label}",
            file=sys.stderr,
        )
        return 124
    except FileNotFoundError as exc:
        print(f"FAIL: Unable to execute {args.label}: {exc}", file=sys.stderr)
        return 127
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
