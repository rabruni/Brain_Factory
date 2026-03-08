# D5: Research - FMWK-900-sawmill-smoke
Meta: v:1.0.0 (matches D2) | status:Complete | open questions:0

## Research Log

### RQ-001
- Prompted By: Entire framework scope
- Priority: Informational
- Sources Consulted: `sawmill/FMWK-900-sawmill-smoke/TASK.md`
- Findings: No research needed - trivial system test.
- Options Considered: | Option | Pros | Cons |
  | Keep scope exactly at one function + one test | Matches assignment, lowest drift risk | None for this canary |
  | Expand into richer framework scaffolding | None for this assignment | Violates `TASK.md` minimality |
- Decision: Keep scope exactly at one function + one test.
- Rationale: The assignment already defines the complete target and explicitly forbids expansion.

## Prior Art Review

### What Worked
Minimal ping/pong smoke canaries clearly separate pipeline failures from product failures.

### What Failed
Expanding smoke tests into framework-shaped mini-products adds noise and defeats the purpose of a canary.

### Lessons for This Build
Keep the spec and the build target at the exact two-file scope in `TASK.md`.
