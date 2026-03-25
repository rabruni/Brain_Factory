# D6: Gap Analysis — Write Path (FMWK-002)
Meta: v:1.0.0 (matches D2/D3/D4) | status:Complete | shared gaps:3 | private gaps:0 | unresolved:0 — MUST be 0 before D7

---

## Boundary Analysis

### 1. Data In — how data enters

| Boundary | Classification | Status |
|----------|---------------|--------|
| Caller mutation request envelope | CONTROLLED — typed envelope with event type + payload | RESOLVED |
| System-event authoring path | CONTROLLED — limited to `session_start`, `session_end`, `snapshot_created` | RESOLVED |
| FMWK-002-owned payload schemas (`methylation_delta`, `suppression`, `unsuppression`, `mode_change`, `consolidation`) | ASSUMED — minimal schemas chosen from authority-owned semantics | RESOLVED |
| Higher-framework-owned payloads passed through Write Path | PERMISSIVE — must be JSON objects matching owning framework schemas | RESOLVED |
| Direct caller access to Ledger or Graph | FORBIDDEN by constitution | RESOLVED |

Gaps found:

GAP-001: Data In | Need: explicit payload schemas for FMWK-002-owned event types | Existing Contract: NONE in authority docs, deferred from FMWK-001 | Gap Description: authority names the event types but does not spell out field sets | Shared?: YES | Recommendation: define minimal payloads containing only the state required to fold the named event type | Resolution: ASSUMED in D3/D4 with minimal field sets (`node_id`, `delta`, `projection_scope`, `mode`, `source_node_ids`, `consolidated_node_id`) | Impact If Unresolved: Turn C/D could not construct valid write-path requests

### 2. Data Out — what's produced

| Boundary | Classification | Status |
|----------|---------------|--------|
| Successful mutation receipt | TYPED — `MutationReceipt` | RESOLVED |
| Snapshot creation response | TYPED — `SnapshotDescriptor` | RESOLVED |
| Recovery/refold response | TYPED — `RecoveryCursor` | RESOLVED |
| Failed mutation behavior | ENUMERATED — typed errors only, no partial receipt | RESOLVED |

Gaps found: None.

### 3. Persistence — what is persisted and where

| What | Where | Owned By | Status |
|------|-------|----------|--------|
| Durable events | FMWK-001 Ledger / immudb | FMWK-001 truth, FMWK-002 submission path | RESOLVED |
| Live folded state | FMWK-005 Graph in memory | FMWK-005 data model, FMWK-002 mutation path | RESOLVED |
| Snapshot artifacts | `/snapshots/*.snapshot` | FMWK-002 orchestration, FMWK-005 state serialization boundary | RESOLVED |
| Replay/refold boundaries | `snapshot_sequence` / ledger tip | FMWK-002 | RESOLVED |

Gaps found:

GAP-002: Persistence | Need: ownership boundary for snapshot creation vs snapshot contents | Existing Contract: BUILDER_SPEC snapshotting + TASK owns list + FMWK-001 DEF-001 | Gap Description: authority says Write Path owns snapshot creation while Graph owns the state being serialized | Shared?: YES | Recommendation: separate orchestration ownership from state-model ownership | Resolution: ASSUMED and documented: FMWK-002 owns trigger timing, sequence marker, and `snapshot_created`; FMWK-005 exposes save/load interface for its state | Impact If Unresolved: Builder would not know where to place snapshot responsibilities

### 4. Auth/Authz — auth boundary

| Boundary | Status |
|----------|--------|
| Live caller authorization | RESOLVED (assumed upstream) — Write Path trusts declared KERNEL callers; authz is enforced before requests arrive |
| Runtime startup/shutdown system path | RESOLVED — system-internal path, not operator-authenticated |

Gaps found: None.

### 5. External Services — external dependencies

| Service | Interface | Status |
|---------|-----------|--------|
| FMWK-001 Ledger | `append`, `read_since`, `get_tip` and related contracts | RESOLVED |
| FMWK-005 Graph | fold/save/load/reset interface behind package code | RESOLVED |
| Snapshot storage | `platform_sdk` filesystem/storage path | RESOLVED |

Gaps found: None.

### 6. Configuration — configuration items

| Config Item | Source | Status |
|-------------|--------|--------|
| Snapshot directory path | config / constant rooted at `/snapshots/` | RESOLVED |
| Write-path retry/block behavior | fixed by contract, not configurable in this packet | RESOLVED |
| Graph interface binding | dependency injection / package wiring | RESOLVED |

Gaps found: None.

### 7. Error Propagation — error flow

| Error Source | Propagation Path | Status |
|-------------|------------------|--------|
| Ledger append failure | FMWK-001 error → `WRITE_PATH_APPEND_ERROR` → caller | RESOLVED |
| Fold failure after durable append | Graph fold error → `WRITE_PATH_FOLD_ERROR` → caller/runtime recovery | RESOLVED |
| Snapshot artifact failure | snapshot path error → `SNAPSHOT_WRITE_ERROR` | RESOLVED |
| Replay/refold failure | snapshot load or replay error → `REPLAY_RECOVERY_ERROR` | RESOLVED |

Gaps found:

GAP-003: Error Propagation | Need: caller-visible semantics for fold failure after durable append | Existing Contract: TASK atomicity statement + OPERATIONAL_SPEC failure posture | Gap Description: append-only Ledger makes rollback impossible but authority does not specify caller semantics | Shared?: YES | Recommendation: define deterministic failure behavior that preserves durable boundary and blocks further progress | Resolution: ASSUMED and documented in D2/D4/D5: no success receipt, typed fold error, recover from durable sequence boundary before resuming writes | Impact If Unresolved: Turn C/E would have to invent what "atomic" means under partial infrastructure success

### 8. Observability — what is observable

| What | How | Status |
|------|-----|--------|
| Append/fold success boundary | `MutationReceipt` sequence + event hash | RESOLVED |
| Snapshot boundary | `SnapshotDescriptor` + `snapshot_created` event | RESOLVED |
| Recovery mode | `RecoveryCursor` | RESOLVED |
| Failure type | typed error code enum | RESOLVED |

Gaps found: None.

### 9. Resource Accounting — resource use

| Resource | Accounting Method | Status |
|----------|-------------------|--------|
| CPU | fold application and replay cost scale with event count | RESOLVED |
| RAM | Graph size is owned by FMWK-005; Write Path adds transient replay state only | RESOLVED |
| Disk | Ledger owned by FMWK-001; snapshots under `/snapshots/` | RESOLVED |
| Startup time | bounded by snapshot load + replay after marker, or full replay with no snapshot | RESOLVED |

Gaps found: None.

### 10. Testable-surface completeness (BLOCKING)

| Boundary | Classification | Status |
|----------|---------------|--------|
| Ledger failure injection | DECLARED via `TD-001 LedgerPortDouble` | CLEAR |
| Fold failure injection | DECLARED via `TD-002 GraphPortDouble` | CLEAR |
| Snapshot failure injection | DECLARED via `TD-002 GraphPortDouble` | CLEAR |
| Deterministic replay stream control | DECLARED via `TD-001 LedgerPortDouble` | CLEAR |

Gaps found: None. Turn C/D/E can express success, append failure, fold failure, snapshot failure, and replay behavior using D4-declared doubles without inventing substitutes.

## Isolation Completeness Check

### Turn C / Holdout reads D2+D4 only

| Need | Where Defined | Status |
|------|---------------|--------|
| Live mutation scenarios | D2 SC-001 through SC-003 | COMPLETE |
| Snapshot/recovery scenarios | D2 SC-004 through SC-009 | COMPLETE |
| Full request schema for live mutation | D4 IN-001 | COMPLETE |
| Full payload schemas for FMWK-002-owned events | D4 IN-001 | COMPLETE |
| Observable postconditions for success/failure | D4 IN-001 through IN-004 | COMPLETE |
| Error codes and retry posture | D4 ERR-001 through ERR-004 + enum | COMPLETE |

Verdict: PASS. Turn C does not need D3/D5 to construct valid scenarios or evaluate outcomes.

### Turn D / Builder reads D10+handoff+D3+D4

| Need | Where Defined | Status |
|------|---------------|--------|
| Request/response entities | D3 E-001 through E-004 | COMPLETE |
| Payload ownership and schemas | D3 payload section + D4 IN-001 | COMPLETE |
| Side-effect ordering guarantees | D4 SIDE-001 through SIDE-003 | COMPLETE |
| Failure injection/test doubles | D4 Testable Surface | COMPLETE |

Verdict: PASS.

### Turn E / Evaluator reads D9+staging only

The spec packet provides all evaluator-needed surfaces through D4-declared doubles and externally observable receipts/errors. No forbidden hidden dependency on D1/D3/D5 is required for evaluation.

Verdict: PASS.

### D4-D3 Restatement Check

| D4 contract | D3 source | Match status |
|------------|-----------|--------------|
| Mutation request envelope | E-001 | MATCHES |
| Mutation receipt | E-002 | MATCHES |
| Snapshot descriptor | E-003 | MATCHES |
| Recovery cursor | E-004 | MATCHES |
| FMWK-002 payload schemas | D3 payload section | MATCHES |

Verdict: PASS.

### Holdout Behavior Check

| Scenario | Tight enough in D2+D4? | Status |
|----------|------------------------|--------|
| SC-001 sync success | append then fold then return | CLEAR |
| SC-003 signal fold | immediate update + range bound | CLEAR |
| SC-007 append failure | no fold, no success | CLEAR |
| SC-008 fold failure | no success, recovery required | CLEAR |
| SC-009 no snapshot | full replay from genesis | CLEAR |

Verdict: PASS.

## Clarification Log

### CLR-001 — Methylation fold rule
- Found During: D3/D5
- Question: How does the primitive turn a delta into a bounded `0.0–1.0` value?
- Options: raw addition, add-and-clamp, framework-policy-driven logic
- Status: ASSUMED
- Blocks: SC-003, D4 postcondition #5
- Resolution: Add delta to current value, then clamp to `0.0–1.0`.

### CLR-002 — Fold failure after durable append
- Found During: D2/D5
- Question: What should the caller observe when append succeeds but fold fails?
- Options: return success anyway, attempt rollback, return failure and recover
- Status: ASSUMED
- Blocks: SC-008, D4 ERR-002
- Resolution: Return `WRITE_PATH_FOLD_ERROR`, do not return success, and recover from the durable sequence boundary before more writes proceed.

### CLR-003 — Snapshot orchestration boundary
- Found During: D2/D5 cross-framework read
- Question: Does Write Path or Graph own snapshot creation?
- Options: Write Path owns all, Graph owns all, split orchestration vs state-model ownership
- Status: ASSUMED
- Blocks: SC-004, SC-005
- Resolution: FMWK-002 owns snapshot timing, sequence marker, and `snapshot_created`; FMWK-005 owns the state-model save/load implementation behind a declared interface.

## Summary

| Category | Gaps Found | Shared | Resolved | Remaining |
|----------|------------|--------|----------|-----------|
| Data In | 1 | 1 | 1 | 0 |
| Data Out | 0 | 0 | 0 | 0 |
| Persistence | 1 | 1 | 1 | 0 |
| Auth/Authz | 0 | 0 | 0 | 0 |
| External Services | 0 | 0 | 0 | 0 |
| Configuration | 0 | 0 | 0 | 0 |
| Error Propagation | 1 | 1 | 1 | 0 |
| Observability | 0 | 0 | 0 | 0 |
| Resource Accounting | 0 | 0 | 0 | 0 |
| Testable Surface | 0 | 0 | 0 | 0 |

Gate verdict: PASS (zero open, including zero isolation-completeness gaps)
