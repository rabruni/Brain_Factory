# Dark Factory Template Guide
Audience: humans writing specs, agent orchestrators executing them.

Principle: specs are source of truth, code is derived. Complete spec = deterministic build. Build failure traces to spec gap.

## Pipeline
Phase 1 EXTRACTION (D1-D5): pull from design docs, log gaps to D6. Don't guess — missing answer = D6 gap.
Phase 2 ANALYSIS (D6): resolve all gaps. Gate: zero OPEN before Phase 3.
Phase 3 BUILD PLANNING (D7 architecture, D8 tasks, D10 builder handbook): only after D6 PASS.
Phase 4 VERIFICATION (D9 holdouts): written by spec author, stored separately, builder never sees.

## How to Start
1. `mkdir [component]/` + copy all D templates
2. Fill D1-D5 in order (each builds on previous). Log gaps to D6.
3. Resolve D6 (zero OPEN items).
4. Fill D7-D8-D10.
5. Write D9 holdout scenarios (test what, not how).
6. Generate handoffs from D8 tasks per BUILDER_HANDOFF_STANDARD.md + prompts from BUILDER_PROMPT_CONTRACT.md.

## Cross-References
D1 → referenced by D7 (constitution check), D9 (rule verification), D10 (patterns)
D2 → referenced by D3 (sources), D4 (scenarios), D8 (task scenarios), D9 (holdout coverage)
D3 → referenced by D4 (shapes), D7 (transforms), D8 (acceptance criteria)
D4 → referenced by D8 (contracts per task), D9 (contract verification)
D5 → referenced by D7 (justification), D10 (patterns)
D6 → referenced by D7 (gap resolution), D8 (blocked tasks)
D7 → referenced by D8 (decomposition), D10 (architecture)
D8 → referenced by D9 (responsibility tracing), D10 (components)
D9 → reviewers only, never visible to builders
D10 → builders read first

## Human-in-the-Loop Decision Points
D6 gate (assumptions acceptable?) | D7 architecture choice | D8 task sizing | D9 holdout design | 13Q gate review | Holdout pass/fail

## Metadata Convention
`# D[N]: [Template Name] — [Component Name]` + Component, Spec Version, Status. Version all together.
