# D4: Contracts — {name}
Meta: v:{ver} (matches D2) | data model: D3 {ver} | status:{Draft|Review|Final}

IDs: IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).
Every contract MUST reference at least one D2 scenario. No source scenario = gap, add to D6.

## Inbound (IN-###)
Per contract: Caller | Trigger | Scenarios (D2 SC-###) | Request Shape (fields table) | Constraints | Example

## Outbound (OUT-###)
Per contract: Consumer | Scenarios | Response Shape (D3 entity ref) | Example success | Example failure

## Side-Effects (SIDE-###)
Per contract: Target System | Trigger | Scenarios | Write Shape | Ordering Guarantee | Failure Behavior

## Errors (ERR-###)
Per contract: Condition | Scenarios | Caller Action

## Error Code Enum
| Code | Meaning | Retryable |
