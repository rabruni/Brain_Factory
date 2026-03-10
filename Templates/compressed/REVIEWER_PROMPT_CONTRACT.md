# Reviewer Prompt Contract
Type: automated 13Q review | version: 1.0.0 | standard: BUILDER_HANDOFF_STANDARD.md

Runtime evidence (required in REVIEW_REPORT.md):
- Exactly one line: Builder Prompt Contract Version Reviewed: [BUILDER_CONTRACT_VERSION]
- Exactly one line: Reviewer Prompt Contract Version: [REVIEWER_CONTRACT_VERSION]
- Last line exactly one of:
  Review verdict: PASS
  Review verdict: RETRY
  Review verdict: ESCALATE

Review scope:
- Judge builder readiness only (no implementation work).
- Check scope/paths/contracts/tests/integration and all [CRITICAL_REVIEW_REQUIRED] flags.

REVIEW_ERRORS.md:
- PASS -> NONE
- RETRY/ESCALATE -> concise bullet list of issues
