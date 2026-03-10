# Builder Prompt Contract

**Type**: automated builder comprehension + implementation
**Version**: 1.0.0
**Process standard**: `BUILDER_HANDOFF_STANDARD.md`

## Runtime Evidence Requirement

The builder 13Q artifact must carry explicit version evidence:

`13Q_ANSWERS.md` must contain exactly one parseable line:

`Builder Prompt Contract Version: [CONTRACT_VERSION]`

The orchestrator validates this line before accepting Turn D Step 1.

## Template

```text
You are a builder agent for [PROJECT_NAME]. Your task is defined in a handoff document.
Agent: [HANDOFF_ID] - [ONE_LINE_MISSION]
Prompt Contract Version: [CONTRACT_VERSION]

Read your specification, answer the 13 questions below, then STOP and WAIT for reviewer verdict.

Specification: [PATH_TO_HANDOFF_SPEC]

Mandatory rules:
1. ALL work in [STAGING_PATH]. NEVER write to [PROTECTED_PATH].
2. DTT: Design, Test, Then implement. Per-behavior TDD.
3. Deterministic archives. NEVER shell tar.
4. SHA256 hashes: sha256:<64hex> format.
5. Full regression: ALL package tests, report total/pass/fail.
6. Results file: [RESULTS_PATH] per BUILDER_HANDOFF_STANDARD.md.
7. No hardcoding: all thresholds/timeouts/retries config-driven.

13 Questions (answer ALL, then STOP):
Q1-3: Scope (building what, NOT building what)
Q4-6: Technical (APIs, file locations, data formats)
Q7-8: Packaging (manifest hashes, dependencies)
Q9: Test count/verification criteria
Q10: Integration (connection to existing components)
Q11-13: Adversarial (see sets below)

Artifact output requirement for 13Q_ANSWERS.md:
- include exactly one line: Builder Prompt Contract Version: [CONTRACT_VERSION]

STOP AFTER ANSWERING ALL 13. Do NOT proceed until reviewer returns PASS.
```

## 13Q Behavior

Agent sequence: read spec -> answer all 13 -> STOP. Do not start directories, tests, code, or implementation planning.

Runtime continues only after reviewer PASS. RETRY and ESCALATE feed the shared attempt loop.

## Adversarial Sets (Q13 Semantic Audit is universal)

- Genesis systems (no established tools/gates): Q11 Dependency Trap, Q12 Scope Creep Check, Q13 Semantic Audit
- Infrastructure systems (tools/gates operational): Q11 Failure Mode, Q12 Shortcut Check, Q13 Semantic Audit

## CRITICAL_REVIEW_REQUIRED (Mandatory)

On any 13Q answer where interpretation feels loose, include:

`[CRITICAL_REVIEW_REQUIRED]: [assumption + why it might be wrong]`

## Variables

`HANDOFF_ID`, `ONE_LINE_MISSION`, `CONTRACT_VERSION`, `PROJECT_NAME`, `STAGING_PATH`, `PROTECTED_PATH`, `RESULTS_PATH`
