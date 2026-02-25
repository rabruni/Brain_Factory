# D4: Contracts — [Component Name]

**Component:** [Component Name]
**Spec Version:** [X.Y.Z] (matches D2)
**Data Model:** D3 [version]
**Status:** [Draft | Review | Final]

---

## Inbound Contracts

<!-- Define every way this component can be invoked. Each contract specifies:
     who calls it, what triggers it, what shape the request takes, and constraints. -->

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
