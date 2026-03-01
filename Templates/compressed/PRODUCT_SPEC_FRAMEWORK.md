# Product Spec Framework
Meta: status:{Draft|Final} | created:{date} | author:{}

Purpose: Define deliverables required to fully specify a component before agent-executable handoffs.
Principle: extraction-first. Content exists in design docs. Work is consolidation + gap-finding, not invention. Gaps found = D6 clarifications.

## Process Flow
Design docs → Extract D1-D10 → Resolve D6 gaps → Handoff decomposition (H-0 shared contracts, H-1 thinnest pipe, H-2+ layered capabilities)

## D-Template System (7 core → 10 documents)
| Doc | Purpose | Question Answered |
| D1 Constitution | Immutable rules + identity | What is it? |
| D2 Specification | GIVEN/WHEN/THEN scenarios | What does it do? (caller view) |
| D3 Data Model | Entity schemas + relationships | What goes in/comes out? (exact shapes) |
| D4 Contracts | Inbound/outbound/side-effect/error | What's missing? (shared contracts, gaps) |
| D5 Research | Design decisions + prior art | What was investigated? |
| D6 Gap Analysis | Boundary analysis + clarification log | What don't we know? (GATE: zero OPEN before D7) |
| D7 Plan | Architecture + files + testing strategy | How is it built? |
| D8 Tasks | Work decomposition + dependencies + phases | What tasks, in what order? |
| D9 Holdout Scenarios | Acceptance tests (hidden from builders) | How do we prove it works? |
| D10 Agent Context | Builder handbook (commands, conventions) | What does the builder need to know? |

## Phase Sequence
Phase 1 EXTRACTION: D1-D5 (log gaps to D6 as found)
Phase 2 ANALYSIS: D6 (resolve all, gate: zero OPEN)
Phase 3 BUILD PLANNING: D7, D8, D10 (after D6 PASS only)
Phase 4 VERIFICATION: D9 (stored separately, builder never sees)

## Repeatable Process
1. Select component → 2. Identify design doc sources → 3. Extract D1-D3 (log to D6) → 4. Analyze D4 (flag shared gaps) → 5. Scope D5 → 6. Resolve D6 (gate) → 7. Write D9 from D2+D3 → 8. Decompose into handoffs

## Supporting Standards
BUILDER_HANDOFF_STANDARD.md (handoff format), BUILDER_PROMPT_CONTRACT.md (agent prompt + 13Q), AGENT_BUILD_PROCESS.yaml (machine-readable workflow)
