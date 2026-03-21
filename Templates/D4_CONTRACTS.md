# D4: Contracts — [Component Name]

**Component:** [Component Name]
**Spec Version:** [X.Y.Z] (matches D2)
**Data Model:** D3 [version]
**Status:** [Draft | Review | Final]

---

<!-- MANDATORY: All contracts MUST use standardized IDs for cross-document traceability:
     IN-NNN (inbound), OUT-NNN (outbound), SIDE-NNN (side-effect), ERR-NNN (error).
     Every contract MUST reference at least one D2 scenario in its Scenarios field.
     Contracts with no source scenario indicate a gap — add to D6. -->

## Inbound Contracts

<!-- Define every way this component can be invoked. Each contract specifies:
     who calls it, what triggers it, what shape the request takes, and constraints. -->

<!-- CONTRACT COMPLETENESS REQUIREMENT:
     For every event type or request shape referenced in D2 scenarios, this document MUST include the
     complete caller-visible field schema inline: field name, type, required/optional status, constraints,
     and any enums or format rules the caller must satisfy.
     Do NOT delegate caller-visible payload definitions to D3 by reference.
     Turn C/Holdout agents read D2 + D4 only and must be able to reconstruct valid requests from D4 alone.

     RESTATE, DO NOT INVENT: The inline schemas here MUST be restated from D3 entity definitions.
     D3 is the design authority for field names, types, and required/optional status.
     D4 copies those definitions verbatim for consumer self-containment.
     If D3 does not define a payload schema for a D2-referenced event type, flag it as OPEN in D6.
     Do NOT invent fields, rename fields, add fields, or change required/optional status relative to D3.
     Any divergence between D4 inline schemas and D3 entity definitions is a blocking D6 gap.

     BEHAVIORAL COMPLETENESS REQUIREMENT:
     For every D2 scenario that Holdout may encode, D4 MUST also define the observable postconditions needed
     for black-box verification. Do not rely on Holdout inference for temporal semantics.
     If a scenario depends on operation ordering or mixed success/failure sequences, D4 must state the exact
     invariant across that sequence.
     Terms such as "no fork", "unchanged tip", "no extra write", "no partial write", "unchanged prior
     records", and "range remains N events" must be operationalized into concrete caller-visible conditions.
     If D2/D3/source authority is not precise enough to state those postconditions, flag the gap as OPEN in D6
     rather than inventing behavior in D4 or D9. -->

#### IN-001: [Contract Name]

**Caller:** [Who invokes this — e.g., Operator (CLI), another component, API client]
**Trigger:** [What causes invocation — e.g., CLI command, API call, event]
**Scenarios:** [D2 scenario IDs this contract serves — e.g., SC-001, SC-006]

**Request Shape:** [Format — e.g., CLI arguments, JSON body, function parameters]

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| [field_name] | [type] | [yes/no] | [Description] |

**Constraints:**
- [Validation rule 1]
- [Validation rule 2]

**Example:** [Concrete invocation example]

<!-- Add more inbound contracts as needed (IN-002, IN-003, etc.) -->

---

## Outbound Contracts

<!-- Define everything this component produces as output. -->

#### OUT-001: [Contract Name]

**Consumer:** [Who reads this output — e.g., Operator, downstream component]
**Scenarios:** [D2 scenario IDs]

**Response Shape:** [D3 entity reference or format description]

**Example Response (success):**
```json
{
  "field": "value"
}
```

**Example Response (failure):**
```json
{
  "field": "value"
}
```

<!-- Add more outbound contracts as needed (OUT-002, OUT-003, etc.) -->

---

## Side-Effect Contracts

<!-- Define writes to external systems that happen as a consequence of execution.
     These are NOT return values — they are observable effects (logs, ledger entries, file writes, etc.) -->

#### SIDE-001: [Contract Name]

**Target System:** [What gets written to — e.g., ledger file, database, message queue]
**Trigger:** [What causes this side effect]
**Scenarios:** [D2 scenario IDs]

**Write Shape:** [D3 entity reference or format description]

**Ordering Guarantee:** [When the write happens relative to the operation]
**Failure Behavior:** [What happens if this write fails — does it block the operation?]

<!-- Add more side-effect contracts as needed -->

---

## Error Contracts

<!-- Define every failure mode and its error code. Each error should specify:
     what condition triggers it, which scenarios it relates to, and what the caller should do. -->

#### ERR-001: [ERROR_CODE_NAME]

**Condition:** [What causes this error]
**Scenarios:** [D2 scenario IDs]
**Caller Action:** [What the caller should do when receiving this error]

<!-- Add more error contracts as needed (ERR-002, ERR-003, etc.) -->

---

## Error Code Enum

<!-- Summary table of all error codes for quick reference. -->

| Code | Meaning | Retryable |
|------|---------|-----------|
| [ERROR_CODE] | [Brief description] | [yes/no (with note)] |
| [ERROR_CODE] | [Brief description] | [yes/no (with note)] |

---

## Testable Surface Declaration

If black-box evaluation of this framework requires test doubles, failure injectors, or observable hooks
that are not part of the production API, they MUST be declared here.

For each declared test double:

| Field | Description |
|-------|-------------|
| double_id | Unique identifier (e.g., TD-001) |
| name | Human-readable name |
| purpose | What it replaces and why |
| location | Where the builder MUST place it — MUST be in package code, NOT under `tests/` |
| api_contract | Which production API it must faithfully implement |
| failure_modes | Which failure scenarios it must support |
| invariants | What MUST be true about the double's behavior relative to the real provider |
| intentional_simplifications | What is deliberately different from the real provider and why |

If no test doubles are required, state: `No test doubles required — all scenarios can be evaluated using the production API surface alone.`

### Escalation Rule

If during Turn D or Turn E a role discovers it needs a test double that is NOT declared here, it MUST escalate rather than invent one ad hoc. The escalation triggers a D6 gap re-evaluation.
