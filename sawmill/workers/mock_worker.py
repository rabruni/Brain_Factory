#!/usr/bin/env python3
"""Compatibility wrapper for the deterministic canary worker."""

from __future__ import annotations

from canary_mock_worker import main


if __name__ == "__main__":
    raise SystemExit(main())
