# D6: Gap Analysis — FMWK-001-ledger
Meta: v:1.0.0 (matches D2/D3/D4) | status:Complete | shared gaps:4 | private gaps:0 | unresolved:0 — MUST be 0 before D7

## Boundary Analysis
### 1. Data In
Description: How events and verification requests enter the ledger boundary.

| Boundary | Classification | Status |
| Append request envelope without ledger-owned fields | SHARED | RESOLVED |
| Read/read_range/read_since request shapes | SHARED | RESOLVED |
| Verify-chain request shape for online/offline use | SHARED | RESOLVED |
| Unsupported future event payload schemas | SHARED | ASSUMED |
| Provenance `framework_id` canonical stored format | SHARED | ASSUMED |

Gaps found:
- GAP-1: Data In | What Is Needed: ownership rule for event payload schemas beyond minimum approved set | Existing Contract: IN-001, D3 E-001/E-005/E-006/E-007/E-008/E-009 | Gap Description: Source material defers most payload schemas to owning frameworks | Shared? (YES/NO): YES | Recommendation: Limit FMWK-001 to minimum approved payload schemas and require each owning framework to define the rest | Resolution: ASSUMED — deferred event payload schemas remain owned by their respective frameworks per source material and are outside FMWK-001 scope | Impact If Unresolved: Boundary creep and duplicate schema ownership
- GAP-4: Data In | What Is Needed: canonical event value for `provenance.framework_id` | Existing Contract: IN-001, D3 E-004 | Gap Description: Source material shows schematic `FMWK-NNN` while FWK-0 naming authority uses full identifiers in agent-authored artifacts and path-readable provenance | Shared? (YES/NO): YES | Recommendation: Store full framework identifier `FMWK-NNN-name` in events and treat shorthand references as illustrative placeholders | Resolution: ASSUMED — canonical stored framework IDs use `FMWK-NNN-name` to align ledger provenance with FWK-0 naming authority | Impact If Unresolved: Provenance would drift between ledger records and framework/package filesystem identity

### 2. Data Out
Description: What the ledger produces for consumers.

| Boundary | Classification | Status |
| Stored event envelope output | SHARED | RESOLVED |
| Verification result output | SHARED | RESOLVED |
| Tip output | SHARED | RESOLVED |

Gaps found:
- None.

### 3. Persistence
Description: Where data is stored and what this framework owns.

| What | Where | Owned By | Status |
| Ledger events | immudb `ledger` database | FMWK-001-ledger | RESOLVED |
| Snapshot reference events | ledger event stream | FMWK-001-ledger | RESOLVED |
| Snapshot file contents | `/snapshots/<sequence_number>.snapshot` | FMWK-005-graph | ASSUMED |

Gaps found:
- GAP-2: Persistence | What Is Needed: explicit owner for snapshot file content format | Existing Contract: SC-007, D3 E-009 | Gap Description: Source material marks snapshot format OPEN but approves event marker, path, and replay boundary | Shared? (YES/NO): YES | Recommendation: Keep ledger ownership to snapshot reference event and assign snapshot file content format to FMWK-005 | Resolution: ASSUMED — snapshot file format belongs to FMWK-005 because ledger stores only the marker event, hash, and replay boundary | Impact If Unresolved: Ledger would have to invent graph persistence semantics

### 4. Auth/Authz
Description: Identity, actor provenance, and access assumptions.

| Boundary | Status |
| Event provenance actor enum (`system`, `operator`, `agent`) | RESOLVED |
| Ledger runtime credentials sourced from configuration/secrets, not hardcoded | RESOLVED |
| Caller authorization policy for who may invoke append/read contracts | ASSUMED |

Gaps found:
- GAP-3: Auth/Authz | What Is Needed: caller authorization enforcement owner | Existing Contract: NONE | Gap Description: Authority docs define actor provenance and config-driven credentials but do not assign authorization logic to the ledger framework | Shared? (YES/NO): YES | Recommendation: Treat caller authorization as external to FMWK-001 and enforced by the runtime/package boundary that exposes the ledger abstraction | Resolution: ASSUMED — FMWK-001 validates provenance shape only; authz remains outside ledger scope because no authority assigns policy evaluation to this framework | Impact If Unresolved: Risk of smuggling policy logic into the storage primitive

### 5. External Services
Description: External systems required by the ledger.

| Service | Interface | Status |
| immudb | gRPC-backed ledger persistence through ledger abstraction | RESOLVED |
| platform_sdk config/secrets/logging/errors | SDK imports only | RESOLVED |

Gaps found:
- None.

### 6. Configuration
Description: Config values the ledger depends on.

| Config Item | Source | Status |
| immudb host | platform_sdk config | RESOLVED |
| immudb port | platform_sdk config | RESOLVED |
| database name (`ledger`) | platform_sdk config / bootstrap convention | RESOLVED |
| credentials | platform_sdk config + secrets | RESOLVED |
| reconnect delay (`1 second`) | framework contract | RESOLVED |

Gaps found:
- None.

### 7. Error Propagation
Description: How ledger failures travel to callers.

| Error Source | Propagation Path | Status |
| Connection/database absent/disconnect failure | ledger -> caller as `LEDGER_CONNECTION_ERROR` | RESOLVED |
| Chain corruption | ledger -> caller as `LEDGER_CORRUPTION_ERROR` | RESOLVED |
| Sequence race/fork risk | ledger -> caller as `LEDGER_SEQUENCE_ERROR` | RESOLVED |
| Serialization failure | ledger -> caller as `LEDGER_SERIALIZATION_ERROR` | RESOLVED |

Gaps found:
- None.

### 8. Observability
Description: What the ledger must expose for diagnostics.

| What | How | Status |
| Chain validity and first break point | `verify_chain` result | RESOLVED |
| Tip sequence/hash | `get_tip` result | RESOLVED |
| Provenance on every event | E-001/E-004 fields | RESOLVED |

Gaps found:
- None.

### 9. Resource Accounting
Description: How ledger resource use is bounded or reported.

| Resource | Accounting Method | Status |
| Write durability latency | synchronous append acknowledgement boundary | RESOLVED |
| Connection count | single persistent gRPC connection | RESOLVED |
| Disk growth | external storage-management framework under pressure | RESOLVED |

Gaps found:
- None.

## Clarification Log
### CLR-001
- Found During: D4, D5
- Question: Which atomicity mechanism should satisfy the required tip-read plus write critical section?
- Options: `ExecAll`; in-process mutex; `VerifiedSet`
- Status (OPEN|RESOLVED|ASSUMED): ASSUMED
- Blocks: No

Resolution note: Source material lists all three as acceptable options and explicitly marks in-process locking acceptable under the single-writer architecture. D5 selects the mutex assumption to close the spec without expanding runtime scope.

### CLR-002
- Found During: D2, D3, D6
- Question: Who owns snapshot file contents and format?
- Options: Ledger; Graph; shared ownership
- Status (OPEN|RESOLVED|ASSUMED): ASSUMED
- Blocks: No

Resolution note: Snapshot reference event, path convention, and replay boundary are approved for FMWK-001. Snapshot file contents remain FMWK-005-owned because source material marks format OPEN and ties it to graph needs.

### CLR-003
- Found During: D1, D2, D6
- Question: Who enforces caller authorization for ledger operations?
- Options: Ledger; runtime boundary exposing ledger; package-lifecycle
- Status (OPEN|RESOLVED|ASSUMED): ASSUMED
- Blocks: No

Resolution note: No authority document assigns policy evaluation to the ledger primitive. FMWK-001 validates provenance shape only and leaves authz to the runtime boundary that exposes ledger contracts.

### CLR-004
- Found During: D3, D6
- Question: What exact identifier format should `provenance.framework_id` use in stored events?
- Options: short `FMWK-NNN`; full `FMWK-NNN-name`; allow both
- Status (OPEN|RESOLVED|ASSUMED): ASSUMED
- Blocks: No

Resolution note: FWK-0 names `FMWK-NNN-name` as the full framework identifier for agent-authored artifacts and provenance-readable paths. Stored event provenance therefore uses the full identifier, while shorter forms in source examples are treated as schematic shorthand.

## Summary
| Category | Gaps Found | Shared | Resolved | Remaining |
| Data In | 2 | 2 | 2 | 0 |
| Data Out | 0 | 0 | 0 | 0 |
| Persistence | 1 | 1 | 1 | 0 |
| Auth/Authz | 1 | 1 | 1 | 0 |
| External Services | 0 | 0 | 0 | 0 |
| Configuration | 0 | 0 | 0 | 0 |
| Error Propagation | 0 | 0 | 0 | 0 |
| Observability | 0 | 0 | 0 | 0 |
| Resource Accounting | 0 | 0 | 0 | 0 |

Gate verdict: PASS (zero open)
