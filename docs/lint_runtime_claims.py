#!/usr/bin/env python3
"""Fail if runtime-adjacent docs contain banned stale runtime claims."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    Path("architecture/AGENT_CONSTRAINTS.md"),
    Path("architecture/SAWMILL_ANALYSIS.md"),
    Path("docs/agent-onboarding.md"),
    Path("docs/index.md"),
    Path("docs/status.md"),
    Path("docs/sawmill/RUN_VERIFICATION.md"),
    Path("sawmill/EXECUTION_CONTRACT.md"),
    Path("sawmill/COLD_START.md"),
    Path("CLAUDE.md"),
    Path("AGENT_BOOTSTRAP.md"),
    Path(".claude/agents/orchestrator.md"),
]

RULES = [
    (
        "mandatory_human_13q_gate",
        re.compile(r"(?i)(human\s+(reviews?|approves?|greenlights?).*13Q|13Q.*human\s+(review|approval|greenlight))"),
    ),
    (
        "evaluator_pr_branch_runtime_input",
        re.compile(r"(?i)(D9\s*\+\s*PR\s+branch\s+code|PR\s+branch\s+code\s+ONLY|from\s+PR\s+branch)"),
    ),
    (
        "runtime_merge_or_pr_side_effect",
        re.compile(r"(?i)(merge\s+PR|open\s+a\s+PR|tested\s+merged\s+code\s+out)"),
    ),
    (
        "runsh_equivalent_direct_dispatch",
        re.compile(r"(?i)(run\.sh\s+or\s+direct\s+worker\s+dispatch|invoke\s+agents\s+via\s+run\.sh\s+or\s+direct\s+CLI)"),
    ),
]


def main() -> int:
    failures = []

    for rel in TARGETS:
        path = ROOT / rel
        if not path.exists():
            failures.append((str(rel), 0, "missing_target_file", "target file missing"))
            continue

        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()

        for rule_name, pattern in RULES:
            for idx, line in enumerate(lines, start=1):
                if pattern.search(line):
                    failures.append((str(rel), idx, rule_name, line.strip()))

    if failures:
        print("FAIL: stale runtime claims detected")
        for rel, line_no, rule, line in failures:
            print(f"- {rel}:{line_no}: [{rule}] {line}")
        return 1

    print("PASS: runtime claim lint clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
