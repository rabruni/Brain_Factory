# D5: Research — FMWK-900-sawmill-smoke
Meta: v:1.0.0 (matches D2) | status:Complete | open questions:0

## Research Log
RQ-001
- Prompted By: Overall framework scope in `TASK.md`
- Priority: Informational
- Sources Consulted: `sawmill/FMWK-900-sawmill-smoke/TASK.md`
- Findings: No research needed — trivial system test.
- Options Considered:

| Option | Pros | Cons |
| No additional research | Matches the task's explicit minimal scope | None |

- Decision: No additional research
- Rationale: The assignment fully specifies the build target, owned files, dependencies, and constraints.

## Prior Art Review
### What Worked
Minimal ping/pong smoke tests work because they provide a binary signal with almost no interpretation cost.

### What Failed
Past smoke tests fail as canaries when they expand into architecture, service wiring, or reusable scaffolds.

### Lessons for This Build
Keep the framework strictly to one function, one test, no dependencies, and no extra abstractions.
