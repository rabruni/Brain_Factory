# D6: Gap Analysis — {name}
Meta: v:{ver} (matches D2/D3/D4) | status:{In Progress|Complete} | shared gaps:{N} | private gaps:{N} | unresolved:{N} — MUST be 0 before D7

## Boundary Analysis (9 categories)
For each category: description, boundary table (| Boundary | Classification | Status |), gaps found.

Isolation boundary completeness check is mandatory before closing D6:
- Turn C / Holdout reads D2+D4 only
- Turn D / Builder reads D10+handoff+D3+D4
- Turn E / Evaluator reads D9+staging only
For each boundary, verify every field definition, payload schema, enum, error code, format convention,
response shape, behavioral postcondition, temporal invariant, and failure-routing instruction needed by that consumer is fully defined in allowed docs.
If any consumer would need a forbidden document, record an OPEN gap. Any OPEN isolation-completeness gap
blocks D7.
D4-D3 restatement check: verify every D4 inline payload schema matches D3 exactly — same fields, same
types, same required/optional. D4 restates D3; it does not invent. Divergence = OPEN gap.
Holdout behavior check: verify D2+D4 define pass/fail behavior tightly enough that Turn C does not need to
invent temporal assertions or stronger semantics. If D9 would require inference beyond D2+D4, record OPEN.
10. Testable-surface completeness (BLOCKING): every D9 scenario needing non-production setup has a D4-declared test double in package code (not tests/); failure modes match D4 errors; concurrent scenarios have deterministic reproduction mechanism. CLEAR|OPEN. If OPEN: blocks Turn C/D/E.

Categories:
1. Data In — how data enters
2. Data Out — what's produced
3. Persistence — | What | Where | Owned By | Status |
4. Auth/Authz — | Boundary | Status |
5. External Services — | Service | Interface | Status |
6. Configuration — | Config Item | Source | Status |
7. Error Propagation — | Error Source | Propagation Path | Status |
8. Observability — | What | How | Status |
9. Resource Accounting — | Resource | Accounting Method | Status |

Per gap (GAP-N): Category | What Is Needed | Existing Contract (ref or NONE) | Gap Description | Shared? (YES/NO) | Recommendation | Resolution | Impact If Unresolved
Canonical: `GAP-1: Data In | Need:event schema | Existing:NONE | Shared:YES | Impact:builder blocks`

## Clarification Log (CLR-### IDs)
Per clarification: Found During (D1-D5) | Question | Options | Status (OPEN|RESOLVED|ASSUMED) | Blocks

## Summary
| Category | Gaps Found | Shared | Resolved | Remaining |
Gate verdict: PASS (zero open, including zero isolation-completeness gaps) or FAIL (N open items remain)
