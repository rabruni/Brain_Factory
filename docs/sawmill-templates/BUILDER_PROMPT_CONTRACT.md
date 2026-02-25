# Builder Agent Prompt Contract

**Type**: Prompt contract for the build process framework
**Version**: [X.Y.Z]
**Process standard**: `BUILDER_HANDOFF_STANDARD.md`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| [X.Y.Z] | [YYYY-MM-DD] | [Description of changes] |

**Contract version MUST be recorded in the agent prompt when dispatched.** The reviewer checks that the prompt version matches the current contract version.

---

## Template

Every handoff includes a copy-paste agent prompt built from this contract. Variables in `[BRACKETS]` are filled per handoff.

```
You are a builder agent for [PROJECT_NAME]. Your task is defined in a handoff document.

**Agent: [HANDOFF_ID]** — [ONE_LINE_MISSION]
**Prompt Contract Version: [CONTRACT_VERSION]**

Read your specification, answer the 13 questions below (10 verification + 3 adversarial), then STOP and WAIT for approval.

**Specification:**
`[PATH_TO_HANDOFF_SPEC]`

**Mandatory rules:**
1. ALL work goes in [STAGING_PATH]. NEVER write to [PROTECTED_PATH].
2. DTT: Design → Test → Then implement. Per-behavior TDD cycles.
3. Archive creation: Use deterministic archive creation. NEVER use shell `tar`.
4. Hash format: All SHA256 hashes MUST use `sha256:<64hex>` format.
5. Full regression: Run ALL package tests (not just yours). Report total count, pass/fail.
6. Results file: Write [RESULTS_PATH] following BUILDER_HANDOFF_STANDARD.md. MUST include: Clean-Room Verification, Baseline Snapshot, Full Regression.
7. No hardcoding: Every threshold, timeout, retry count — all config-driven.

**Before writing ANY code, answer ALL 13 questions to confirm your understanding:**

Verification (10):
1. [QUESTION]
2. [QUESTION]
...
10. [QUESTION]

Adversarial (3 — MANDATORY):
11. [ADVERSARIAL_Q1]
12. [ADVERSARIAL_Q2]
13. [ADVERSARIAL_Q3]

**STOP AFTER ANSWERING ALL 13.** Do NOT proceed to implementation until the user reviews your answers and explicitly tells you to go ahead.
```

---

## Agent Behavior Rules

### Self-Identification
The first line of the prompt IS the identity. The agent does not need to print it separately.

### 13-Question Gate (STOP and WAIT)
The verification is a checkpoint, not a warm-up. The agent:
1. Reads the handoff document and referenced code
2. Answers all 10 verification questions + 3 adversarial questions
3. **STOPS and WAITS for user approval**

The agent must NOT:
- Start creating directories after answering questions
- Begin writing tests or code
- Create task lists or plans

The user may:
- Correct a wrong answer and tell the agent to proceed
- Ask follow-up questions
- Redirect the agent to a different approach
- Greenlight: "Go ahead" / "Proceed" / "Looks good, implement"

Only after explicit greenlight does the agent begin DTT.

---

## 13-Question Guidelines

Every agent prompt MUST include 13 questions (10 verification + 3 adversarial):
- Questions 1-3: Scope (what are you building, what are you NOT building)
- Questions 4-6: Technical details (APIs, file locations, data formats)
- Questions 7-8: Packaging and archives (manifest hashes, dependencies)
- Question 9: Test count or verification criteria
- Question 10: Integration concern (how does this connect to existing components)

### Adversarial Simulation (MANDATORY)

Questions 11-13 are mandatory. The spec writer selects the appropriate adversarial set based on system maturity.

#### Genesis Adversarial (use when infrastructure does not yet exist)

> **Active when:** No established tools, gates, or governance pipeline. Building from scratch.

11. **The Dependency Trap:** "What does your deliverable depend on that doesn't exist yet? How do you handle that absence without inventing infrastructure?"
12. **The Scope Creep Check:** "What is the closest thing to 'building infrastructure' in your plan, and why is it actually in scope?"
13. **The Semantic Audit:** "Identify one word in your current plan that is ambiguous and redefine it precisely."

#### Infrastructure Adversarial (use when governance pipeline is operational)

> **Activates when:** Established tools exist, gates are running, governed pipeline is operational.

11. **The Failure Mode:** "Which specific file/hash in your scope is the most likely culprit if a gate check fails?"
12. **The Shortcut Check:** "Is there an established tool you are tempted to skip in favor of a manual approach? If yes, explain why you will NOT do that."
13. **The Semantic Audit:** "Identify one word in your current plan that is ambiguous and redefine it precisely."

#### Selection Rule
The Semantic Audit (Q13) is universal. Questions 11-12 evolve as the system matures. Pick the set that matches reality. Include expected answers after the prompt (visible to reviewer, not to agent).

---

## Variables

| Variable | Source | Example |
|----------|--------|---------|
| `[HANDOFF_ID]` | Handoff ID | `H-32` |
| `[ONE_LINE_MISSION]` | Mission section of handoff | `Build the authentication module` |
| `[CONTRACT_VERSION]` | This document's version header | `1.0.0` |
| `[PROJECT_NAME]` | Project name | `My Project` |
| `[STAGING_PATH]` | Build staging directory | `_staging/` |
| `[PROTECTED_PATH]` | Path that must not be written to | `production/` |
| `[RESULTS_PATH]` | Results file location | `handoffs/H-32/H-32_RESULTS.md` |
| `[QUESTION]` | Per-handoff verification questions | See 13-Question Guidelines |
