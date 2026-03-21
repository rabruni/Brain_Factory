"""
ledger.__main__ — Cold-storage CLI for FMWK-001-ledger.

Usage:
    python -m ledger --verify [--start N] [--end N]
    python -m ledger --help

Connects directly to immudb (no kernel process required) and verifies the
hash chain. Designed for cold-storage integrity checks — the entire governed
filesystem can be verified against the Ledger from a machine that only has
immudb access (D1 Article 8: Cold-Storage Verifiability).

Output (stdout, JSON):
    {"valid": true, "break_at": null, "tip": {"sequence_number": N, "hash": "sha256:..."}}
    {"valid": false, "break_at": N, "tip": {"sequence_number": M, "hash": "sha256:..."}}

Exit codes:
    0 — chain is valid
    1 — chain is invalid, or any error occurred (LedgerConnectionError, etc.)
"""
import argparse
import json
import sys


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m ledger",
        description="Verify the Ledger hash chain (cold-storage, no kernel required).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the hash chain and print a JSON result.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="First sequence number to verify (default: 0).",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="Last sequence number to verify (default: tip).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """
    Entry point. Returns exit code (0=valid, 1=invalid or error).
    """
    # Ensure dopejar root is on sys.path for platform_sdk
    import os
    _DOPEJAR_ROOT = "/Users/raymondbruni/dopejar"
    if _DOPEJAR_ROOT not in sys.path:
        sys.path.insert(0, _DOPEJAR_ROOT)

    args = _parse_args(argv)

    if not args.verify:
        print(
            json.dumps({"error": "No action specified. Use --verify."}),
            file=sys.stderr,
        )
        return 1

    try:
        from platform_sdk.tier0_core.config import get_config
        from ledger.api import LedgerClient
        from ledger.errors import LedgerConnectionError

        config = get_config()
        client = LedgerClient(config=config)
        client.connect()

        tip = client.get_tip()

        result = client.verify_chain(start=args.start, end=args.end)

        output = {
            "valid": result.valid,
            "break_at": result.break_at,
            "tip": {
                "sequence_number": tip.sequence_number,
                "hash": tip.hash,
            },
        }
        print(json.dumps(output))
        return 0 if result.valid else 1

    except LedgerConnectionError as exc:
        output = {
            "valid": False,
            "break_at": None,
            "error": str(exc),
        }
        print(json.dumps(output), file=sys.stderr)
        return 1

    except Exception as exc:  # noqa: BLE001
        output = {
            "valid": False,
            "break_at": None,
            "error": f"Unexpected error: {exc}",
        }
        print(json.dumps(output), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
