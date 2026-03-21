# D4: Contracts — {name}
Meta: v:{ver} (matches D2) | data model: D3 {ver} | status:{Draft|Review|Final}

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).
Every contract MUST reference at least one D2 scenario. No source scenario = gap, add to D6.

## Inbound (IN-###)
Per contract: Caller | Trigger | Scenarios (D2 SC-###) | Request Shape (fields table) | Constraints | Example
Requirement: for every D2-referenced event/request, inline the complete caller-visible field schema here.
Include field name, type, required/optional, constraints, enums, and format rules. Do NOT delegate payload
definitions to D3 by reference. Turn C reads D2+D4 only and must be able to reconstruct valid requests from
D4 alone. RESTATE from D3, do NOT invent. D3 is the design authority for field names/types/required status.
Copy D3 definitions verbatim. If D3 lacks a payload schema for a D2 event type, flag OPEN in D6.
Do NOT add/rename/remove fields or change required/optional relative to D3. Divergence = blocking D6 gap.
Also inline observable postconditions for every holdout-visible D2 scenario. Do not make Holdout infer
temporal semantics. Operationalize terms like "no fork", "no extra write", "unchanged tip", and "no partial
write" into concrete caller-visible invariants. If authority is insufficient, mark OPEN in D6 instead of
inventing behavior.

## Outbound (OUT-###)
Per contract: Consumer | Scenarios | Response Shape (D3 entity ref) | Example success | Example failure

## Side-Effects (SIDE-###)
Per contract: Target System | Trigger | Scenarios | Write Shape | Ordering Guarantee | Failure Behavior

## Errors (ERR-###)
Per contract: Condition | Scenarios | Caller Action

## Error Code Enum
| Code | Meaning | Retryable |

## Testable Surface
If evaluation requires test doubles/failure injectors not in production API, declare each:
double_id | name | purpose | location (package code only, never tests/) | api_contract | failure_modes | invariants | intentional_simplifications.
If none required: `No test doubles required`.
If Turn D/E needs an undeclared double: ESCALATE.
