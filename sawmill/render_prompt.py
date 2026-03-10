#!/usr/bin/env python3
"""Render a prompt template using environment-variable placeholders."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Sawmill prompt template")
    parser.add_argument("template", help="Path to the prompt template file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    template_path = Path(args.template)
    try:
        content = template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"FAIL: Prompt template not found: {template_path}", file=sys.stderr)
        return 1

    missing: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in os.environ:
            missing.add(key)
            return match.group(0)
        return os.environ[key]

    rendered = PLACEHOLDER.sub(replace, content)
    if missing:
        print(
            f"FAIL: Missing prompt variables for {template_path}: {', '.join(sorted(missing))}",
            file=sys.stderr,
        )
        return 1

    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
