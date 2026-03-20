"""CLI entrypoint for sawmill.agent."""

from __future__ import annotations

import sys

from ._core import main_backend_adapters, main_invoke_full, main_runner, main_timeout_runner


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "invoke":
        return main_runner(argv[1:])
    if argv and argv[0] == "invoke-full":
        return main_invoke_full(argv[1:])
    if argv and argv[0] == "inspect":
        return main_backend_adapters(argv[1:])
    if argv and argv[0] == "timeout-runner":
        return main_timeout_runner(argv[1:])
    print("FAIL: use one of: invoke, invoke-full, inspect, timeout-runner", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
