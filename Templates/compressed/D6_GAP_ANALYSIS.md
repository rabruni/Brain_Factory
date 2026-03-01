# D6: Gap Analysis — {name}
Meta: v:{ver} (matches D2/D3/D4) | status:{In Progress|Complete} | shared gaps:{N} | private gaps:{N} | unresolved:{N} — MUST be 0 before D7

## Boundary Analysis (9 categories)
For each category: description, boundary table (| Boundary | Classification | Status |), gaps found.

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

## Clarification Log (CLR-### IDs)
Per clarification: Found During (D1-D5) | Question | Options | Status (OPEN|RESOLVED|ASSUMED) | Blocks

## Summary
| Category | Gaps Found | Shared | Resolved | Remaining |
Gate verdict: PASS (zero open) or FAIL (N open items remain)
