# D5: Research — sawmill smoke canary
Meta: v:1.0.0 (matches D2) | status:Complete | open questions:0

## Research Log
### RQ-001
- Prompted By: D2 overall scope
- Priority: Informational
- Sources Consulted: sawmill/FMWK-900-sawmill-smoke/TASK.md
- Findings: No research needed — trivial system test.
- Options Considered: | Option | Pros | Cons |
  | Keep canary minimal | Matches task exactly | None |
  | Expand architecture | None | Violates task |
- Decision: Keep canary minimal
- Rationale: The task defines the full scope and explicitly forbids expansion.

## Prior Art Review
### What Worked
Minimal canary code with a single deterministic test works because it proves the pipeline without adding noise.

### What Failed
Adding framework architecture to a smoke canary would fail because the task explicitly prohibits it.

### Lessons for This Build
Extract only the explicit task requirements and keep every artifact short.
