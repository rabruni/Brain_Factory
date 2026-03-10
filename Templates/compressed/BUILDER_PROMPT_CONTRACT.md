# Builder Prompt Contract
Type: automated builder comprehension + implementation | version: 1.0.0 | standard: BUILDER_HANDOFF_STANDARD.md

Runtime evidence (required):
- 13Q_ANSWERS.md must contain exactly one line:
  Builder Prompt Contract Version: [CONTRACT_VERSION]

Template (core):
1. Include prompt header with `Prompt Contract Version: [CONTRACT_VERSION]`.
2. Read handoff/context, answer all 13 questions, STOP.
3. Do not start implementation before reviewer PASS.
4. Include `[CRITICAL_REVIEW_REQUIRED]` where interpretation is loose.

Adversarial sets:
- Genesis: Dependency Trap, Scope Creep Check, Semantic Audit
- Infrastructure: Failure Mode, Shortcut Check, Semantic Audit
