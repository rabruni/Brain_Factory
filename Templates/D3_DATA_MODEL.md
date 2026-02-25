# D3: Data Model — [Component Name]

**Component:** [Component Name]
**Spec Version:** [X.Y.Z] (matches D2)
**Status:** [Draft | Review | Final]
**Shared Entities:** [Count of SHARED-scope entities]

---

## Entities

<!-- Define every data entity this component creates, consumes, or transforms.
     Scope: PRIVATE (only this component uses it) or SHARED (other components consume it).
     Each entity needs: fields table, example, and invariants. -->

### E-001: [Entity Name] ([PRIVATE | SHARED])

**Scope:** [PRIVATE | SHARED] — [brief explanation of who uses this entity]
**Used By:** [List of consumers — components, operators, other systems] <!-- For SHARED only -->
**Source:** [Which D2 scenarios produce or consume this entity]
**Description:** [One-paragraph description of what this entity represents]

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| [field_name] | [type] | [yes/no] | [What this field means] | [Validation rules, patterns, enums, etc.] |
| [field_name] | [type] | [yes/no] | [Description] | [Constraints] |

**Example:**
```json
{
  "field_name": "realistic_value",
  "field_name": "realistic_value"
}
```

**Invariants:**
<!-- Rules that must always be true for this entity to be valid -->
- [Invariant 1 — e.g., "field_x must reference a valid entity in collection_y"]
- [Invariant 2]

### E-002: [Entity Name] ([PRIVATE | SHARED])

**Scope:** [PRIVATE | SHARED] — [explanation]
**Source:** [D2 scenario references]
**Description:** [Description]

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| [field_name] | [type] | [yes/no] | [Description] | [Constraints] |

**Example:**
```json
{
  "field_name": "realistic_value"
}
```

**Invariants:**
- [Invariant]

<!-- Add more entities as needed (E-003, E-004, etc.) -->

---

## Entity Relationship Map

<!-- Show how entities relate to each other. Use ASCII art or text-based diagram. -->

```
[Entity A]
  |
  |-- [relationship] --> [Entity B]
  |
  |-- [relationship] --> [Entity C]
  |       |
  |       |-- [relationship] --> [Entity D]
  |
  |-- [relationship] --> [Entity E]
```

---

## Migration Notes

<!-- If this replaces or extends a prior model, describe migration.
     If greenfield, state "No prior model — greenfield." -->

[Migration notes or "No prior model — greenfield."]
