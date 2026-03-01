# D3: Data Model — {name}
Meta: v:{ver} (matches D2) | status:{Draft|Review|Final} | shared entities:{count}

## Entities (E-### IDs, e.g. E-001)
Per entity:
- Scope: PRIVATE (this component only) or SHARED (other components consume)
- Used By: consumers list (SHARED only)
- Source: which D2 scenarios produce/consume this
- Description: one paragraph

Fields table: | Field | Type | Required | Description | Constraints |
Canonical: `| field_name:string | Type:uuid-v7 | Req:yes | Desc:text | Constraint:pattern |`
JSON example with realistic values.
Invariants: rules that must always hold for this entity.

## Entity Relationship Map
ASCII diagram showing relationships between entities.

## Migration Notes
"No prior model — greenfield." or describe migration from prior model.
