# Legacy D9 Holdout Scenarios Template

This file preserves the pre-behavioral D9 format for rollback during the
behavioral-holdout pilot.

The legacy format used executable holdout scripts with Setup / Execute / Verify /
Cleanup sections and concrete commands. It is intentionally retained only as a
rollback artifact while the pilot is evaluated.

If rollback is required:
- restore `Templates/D9_HOLDOUT_SCENARIOS.md` from this legacy shape
- restore `Templates/compressed/D9_HOLDOUT_SCENARIOS.md` to its legacy format
- restore holdout/evaluator role files to executable-script mode
- regenerate D9 from Turn C

For the authoritative legacy body, see repository history immediately prior to
the behavioral-holdout pilot.
