"""CLI entrypoint for sawmill.audit."""

from __future__ import annotations

import sys

from . import _contracts, _core, _harness


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "contracts":
        return _contracts.main(argv[1:])
    if argv and argv[0] == "stage":
        return _core.main_stage(argv[1:])
    if argv and argv[0] == "convergence":
        return _core.main_convergence(argv[1:])
    if argv and argv[0] == "preflight":
        return _core.main_preflight(argv[1:])
    if argv and argv[0] == "self-test":
        return _harness.main(["--self-test"])
    if argv and argv[0] == "harness":
        return _harness.main(argv[1:])
    print("FAIL: use one of: contracts, stage, convergence, preflight, self-test, harness", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
