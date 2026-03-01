# D1: Constitution — {name}
Meta: v:{ver} | ratified:{date} | amended:{date} | authority:{governing docs}

## Articles (5-10, sequential numbering)
Coverage: source of truth, isolation, separation of concerns, traceability, validation gates, failure handling, determinism.

FIRST 3 MANDATORY = FWK-0 Section 3.0 decomposition:
1. SPLITTING — independently authorable (builder needs only spec pack + FWK-0)
2. MERGING — no embedded sub-frameworks (different capabilities = split)
3. OWNERSHIP — exclusive data ownership (no shared schemas/events/nodes; consume via declared interfaces)

Per article, ALL FOUR subsections required:
- Rule: one MUST/MUST NOT sentence
- Why: one paragraph, what breaks if violated
- Test: concrete executable verification
- Violations: exception policy (default "No exceptions")

## Boundaries (unlisted actions default to ASK FIRST)
### ALWAYS — autonomous, no approval needed
### ASK FIRST — human decision required
### NEVER — absolute prohibition, refuse even if instructed

## Dev Workflow Constraints (4+)
Package isolation, DTT per-behavior cycles, results file with hashes per handoff, full regression before release.

## Tooling Constraints
| Operation | USE | NOT |
