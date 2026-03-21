# ADR-001: Behavioral Holdouts

## Status

Pilot approved for `FMWK-001-ledger`.

## Context

Sawmill repeatedly failed at the Builder-Holdout boundary because executable
holdout scripts required interface knowledge that Holdout isolation rules
forbid. The failures appeared in multiple categories:

- payload/schema mismatches
- behavioral/postcondition mismatches
- public API surface and initialization mismatches

Each patch to D4 revealed the next missing category. The underlying defect was
structural: executable holdouts require implementation-facing interface details,
while Turn C is intentionally restricted to D2 + D4.

## Decision

Holdouts become behavioral scenario specifications, not executable scripts.

Turn C still reads only D2 + D4 and writes D9 as structured behavioral
scenarios. Turn E reads D9 plus staged code, discovers the public API surface,
writes executable tests, and runs them.

This preserves isolation while moving API-surface discovery to the only role
allowed to see the built code.

## Consequences

### Positive

- Eliminates the need for Holdout to invent class names, constructor signatures,
  helper hooks, or setup protocols.
- Keeps Builder isolated from D9.
- Makes evaluator translation auditable through generated test files and mapping
  files.
- Avoids expanding D4 into an overloaded caller+test-harness document.

### Negative

- Evaluator becomes more complex and must reliably translate behavioral
  scenarios into tests.
- Generated tests may vary structurally between evaluator invocations.
- Rollback must be preserved during the pilot.

## Pilot Scope

Pilot only on `FMWK-001-ledger`.

Changed surfaces:
- `Templates/D9_HOLDOUT_SCENARIOS.md`
- `Templates/compressed/D9_HOLDOUT_SCENARIOS.md`
- `.claude/agents/holdout-agent.md`
- `.claude/agents/evaluator.md`
- `sawmill/prompts/turn_c_holdout.txt`
- `sawmill/prompts/turn_e_eval.txt`

Unchanged surfaces:
- runtime/orchestrator implementation
- builder/reviewer roles
- run lifecycle and evidence schema

## Rollback

If the pilot fails:
- restore legacy D9 template shape
- restore executable-script holdout/evaluator behavior
- regenerate D9 from Turn C

## Success Criteria

The class is considered solved when:
- Holdout scenarios are written with zero implementation-specific API knowledge
- Evaluator-generated tests are auditable and reproducible per attempt
- Failures are caused by implementation behavior, not interface invention
- New frameworks do not require adding new categories of D4 completeness for
  Holdout to write valid scenarios
