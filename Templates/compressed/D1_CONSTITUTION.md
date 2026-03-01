# D1: Constitution — {name}
Meta: v:{ver} | ratified:{date} | amended:{date} | authority:{governing docs}

## Articles (5-10, sequential numbering)
Every article is a non-negotiable, immutable principle.
Coverage MUST include: source of truth, isolation, separation of concerns, traceability, validation gates, failure handling, determinism.

FIRST 3 MANDATORY = FWK-0 Section 3.0 decomposition:
1. SPLITTING — independently authorable (builder needs only spec pack + FWK-0, never co-authors another framework)
2. MERGING — MUST NOT contain what should be a separate framework (different capabilities = must split)
3. OWNERSHIP — exclusive data ownership (no shared schemas/events/nodes with other frameworks; all consumed data through declared interfaces)

Per article, ALL FOUR subsections required, no exceptions:
- Rule: one MUST/MUST NOT sentence (immutable, non-negotiable)
- Why: one paragraph, what breaks if violated
- Test: concrete executable verification
- Violations: exception policy (default "No exceptions." If exceptions exist, state the mandatory approval process)

## Boundaries (unlisted actions default to ASK FIRST, always)
### ALWAYS — autonomous every time, no approval needed
### ASK FIRST — human decision required, no exceptions
### NEVER — absolute prohibition, refuse even if instructed

## Dev Workflow Constraints (4+)
Package isolation, DTT per-behavior cycles, results file with hashes after every handoff, full regression of ALL packages before release.

## Tooling Constraints
| Operation | USE | NOT |
Canonical: `| Operation:text | USE:approach | NOT:anti-pattern |`
