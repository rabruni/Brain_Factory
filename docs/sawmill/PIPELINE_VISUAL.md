# Sawmill Pipeline Visual

## A. What Gets Built Now

File dependency diagram showing how gap analysis drives the new templates.

```mermaid
graph TD
    GAP[SUPERPOWERS_GAP_ANALYSIS.md<br/>7 gaps identified] --> TDD[Templates/TDD_AND_DEBUGGING.md<br/>NEW — gaps 1,3,6,7]
    GAP --> BHS[Templates/BUILDER_HANDOFF_STANDARD.md<br/>UPDATED — gaps 2,4,5]
    TDD --> CTDD[compressed/TDD_AND_DEBUGGING.md]
    BHS --> CBHS[compressed/BUILDER_HANDOFF_STANDARD.md]
    TDD --> BUILDER[.claude/agents/builder.md<br/>UPDATED — model routing]
    BHS --> BUILDER
    BUILDER --> MKDOCS[mkdocs.yml<br/>UPDATED — new nav entries]
```

<details>
<summary>ASCII fallback</summary>

```
SUPERPOWERS_GAP_ANALYSIS.md (7 gaps)
  |
  +---> Templates/TDD_AND_DEBUGGING.md [NEW — gaps 1,3,6,7]
  |       |
  |       +---> compressed/TDD_AND_DEBUGGING.md
  |       +---> .claude/agents/builder.md [UPDATED — model routing]
  |
  +---> Templates/BUILDER_HANDOFF_STANDARD.md [UPDATED — gaps 2,4,5]
          |
          +---> compressed/BUILDER_HANDOFF_STANDARD.md
          +---> .claude/agents/builder.md
                  |
                  +---> mkdocs.yml [UPDATED — new nav entries]
```

</details>

---

## B. The Sawmill Pipeline

Full turn flow with new pieces highlighted.

```mermaid
flowchart LR
    subgraph "Spec Writing (A)"
        SA[Spec Agent] --> D1[D1-D6]
    end
    subgraph "Build Planning (B)"
        PA[Plan Agent] --> D7[D7,D8,D10]
    end
    subgraph "Acceptance Test Writing (C)"
        HA[Holdout Agent] --> D9[D9]
    end
    subgraph "Code Building (D)"
        direction TB
        B13Q[13Q Gate] --> BTDD[TDD Iron Law ★NEW]
        BTDD --> BDBG[Debug Protocol ★NEW]
        BDBG --> BCHK[Mid-Build Checkpoint ★NEW]
        BCHK --> BREF[Self-Reflection ★NEW]
        BREF --> BVER[Verification Discipline ★NEW]
        BVER --> RESULTS[RESULTS.md]
    end
    subgraph "Evaluation (E)"
        EV[Evaluator] --> REPORT[EVALUATION_REPORT.md]
    end
    D1 --> PA
    D1 --> HA
    D7 --> B13Q
    D9 --> EV
    RESULTS --> EV
```

<details>
<summary>ASCII fallback</summary>

```
Spec Writing (A)  Build Planning (B)  Acceptance Test Writing (C)
  Spec Agent        Plan Agent          Holdout Agent
  D1-D6 ------+--> D7,D8,D10           D9
              |                          |
              |    Code Building (D)     |
              |      13Q Gate            |
              |        |                 |
              |      TDD Iron Law ★      |
              |        |                 |
              |      Debug Protocol ★    |
              |        |                 |
              |      Mid-Build Chk ★     |
              |        |                 |
              |      Self-Reflect ★      |
              |        |                 |
              |      Verify Disc. ★      |
              |        |                 |
              |      RESULTS.md ---------+---> Evaluation (E)
              |                                Evaluator
              +--------------------------------> EVALUATION_REPORT.md
```

</details>

---

## C. The Three Layers — Roadmap

```mermaid
gantt
    title Sawmill Hardening Roadmap
    dateFormat YYYY-MM-DD
    section Layer 1 — Prompt
        TDD_AND_DEBUGGING.md          :a1, 2026-03-06, 1d
        BUILDER_HANDOFF_STANDARD.md   :a2, 2026-03-06, 1d
        Compressed versions           :a3, after a2, 1d
        Agent model routing           :a4, after a3, 1d
    section Layer 2 — Infrastructure
        Promptfoo for Evaluation (E)  :b1, after a4, 5d
        DeepEval for RESULTS.md       :b2, after a4, 5d
    section Layer 3 — Self-Correction
        LangGraph verification loop   :c1, after b1, 7d
```

<details>
<summary>ASCII fallback</summary>

```
Layer 1 — Prompt (NOW)
  [Mar 6]  TDD_AND_DEBUGGING.md
  [Mar 6]  BUILDER_HANDOFF_STANDARD.md
  [Mar 7]  Compressed versions
  [Mar 8]  Agent model routing

Layer 2 — Infrastructure (NEXT, after FMWK-001 Code Building (D))
  [Mar 9-13]  Promptfoo for Evaluation (E) holdout automation
  [Mar 9-13]  DeepEval for RESULTS.md faithfulness checks

Layer 3 — Self-Correction (LATER, after FMWK-002)
  [Mar 14-20]  LangGraph verification loop
```

</details>

---

## What Each Layer Does

**Layer 1 (Prompt)**: Templates that tell builders HOW to code. Works immediately. Honor-system enforcement — the builder is told to follow TDD, verify claims, and debug systematically.

**Layer 2 (Infrastructure)**: Mechanical enforcement. Promptfoo automates Evaluation (E) holdout execution. DeepEval verifies that RESULTS.md claims match actual test output. Layer 1's rules become machine-checked.

**Layer 3 (Self-Correction)**: Feedback loops. Builder output routes through a verification node before proceeding. Replaces the mid-build checkpoint (human review) with mechanical review for routine checks. Human review stays for architectural decisions.
