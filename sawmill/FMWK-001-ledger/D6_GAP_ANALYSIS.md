# D6: Gap Analysis — FMWK-001-ledger
Meta: v:1.0.0 (matches D2/D3/D4) | status:Complete | shared gaps:6 | private gaps:1 | unresolved:0

## Boundary Analysis

### 1. Data In
Description: How data enters the Ledger contracts.

| Boundary | Classification | Status |
| Append event envelope without caller sequence | SHARED | RESOLVED |
| Read requests by sequence/range/since | SHARED | RESOLVED |
| Verification request source mode | SHARED | RESOLVED |

Gaps found:
- GAP-1: Data In | Need: explicit append request shape without caller-controlled sequence/hash | Existing: IN-001 | Gap Description: Source material implied this rule but needed contract extraction | Shared?: YES | Recommendation: lock append request to envelope minus sequence/hash fields | Resolution: RESOLVED in D4 IN-001 | Impact If Unresolved: callers could fork the chain

### 2. Data Out
Description: What the Ledger produces.

| Boundary | Classification | Status |
| Persisted event return shape | SHARED | RESOLVED |
| Ordered replay response | SHARED | RESOLVED |
| Verification result shape | SHARED | RESOLVED |

Gaps found:
- GAP-2: Data Out | Need: exact verification result structure | Existing: OUT-004 | Gap Description: `break_at` needed explicit presence rule | Shared?: YES | Recommendation: define `ChainVerificationResult` with first-failure semantics | Resolution: RESOLVED in D3 E-009 and D4 OUT-004 | Impact If Unresolved: holdout tests could not assert corruption position deterministically

### 3. Persistence
Description: Where data is stored and who owns each persistence concern.

| What | Where | Owned By | Status |
| Ledger events | immudb `ledger` database | FMWK-001 | RESOLVED |
| Snapshot metadata event | Ledger event stream | FMWK-001 | RESOLVED |
| Snapshot file contents/format | `/snapshots/` volume | FMWK-005 | ASSUMED |

Gaps found:
- GAP-3: Persistence | Need: snapshot ownership boundary | Existing: SC-006, E-007 | Gap Description: Snapshot format was OPEN in source material | Shared?: YES | Recommendation: keep metadata in Ledger, defer file format to FMWK-005 | Resolution: ASSUMED with source-backed justification in D5 RQ-002 and CLR-001 | Impact If Unresolved: Ledger scope could drift into graph storage

### 4. Auth/Authz
Description: Authentication and authorization boundaries affecting Ledger access.

| Boundary | Status |
| Caller identity is carried as provenance actor category, not enforced by Ledger business logic | RESOLVED |
| immudb credentials come from config/secrets, not hardcoded in production | RESOLVED |

Gaps found:
- None beyond configuration extraction.

### 5. External Services
Description: External dependencies and interfaces.

| Service | Interface | Status |
| immudb | gRPC on configured host/port, database `ledger` | RESOLVED |
| Offline export | Ledger data file / exported bytes for verification | ASSUMED |

Gaps found:
- GAP-4: External Services | Need: offline verification source definition | Existing: IN-005 | Gap Description: Source material says "Ledger data file" but not export packaging mechanics | Shared?: YES | Recommendation: treat offline verification as operating on exported Ledger bytes produced by tooling, not a new service | Resolution: ASSUMED in CLR-002 | Impact If Unresolved: offline verification tooling contract remains ambiguous

### 6. Configuration
Description: Runtime-configured values the Ledger depends on.

| Config Item | Source | Status |
| immudb host/port/database | `platform_sdk.config` | RESOLVED |
| immudb credentials | `platform_sdk.config` / secrets | RESOLVED |
| reconnect delay | source material constant (`1 second`) | RESOLVED |

Gaps found:
- GAP-5: Configuration | Need: local-dev credential handling boundary | Existing: ERR-001 / SIDE-003 | Gap Description: Source material allows default immudb creds locally but forbids production hardcoding | Shared?: NO | Recommendation: document environment-dependent credential sourcing | Resolution: RESOLVED in D4 and CLR-003 | Impact If Unresolved: builder could hardcode production secrets

### 7. Error Propagation
Description: How failures surface to callers.

| Error Source | Propagation Path | Status |
| Connection failure | Ledger -> caller as `LedgerConnectionError` | RESOLVED |
| Serialization failure | Ledger -> caller as `LedgerSerializationError` | RESOLVED |
| Sequence conflict | Ledger -> caller as `LedgerSequenceError` | RESOLVED |
| Chain corruption | Ledger -> caller as `LedgerCorruptionError`/verification result | RESOLVED |

Gaps found:
- GAP-6: Error Propagation | Need: corruption reporting semantics | Existing: ERR-004, OUT-004 | Gap Description: source material provided validity/break position but not enum mapping | Shared?: YES | Recommendation: keep verification result plus `LEDGER_CORRUPTION_ERROR` enum for callers that surface typed failures | Resolution: RESOLVED in D4 | Impact If Unresolved: callers cannot consistently halt on corruption

### 8. Observability
Description: What must be measurable or inspectable about Ledger behavior.

| What | How | Status |
| Append success/failure by contract outcome | Returned result/error, higher-layer logging | RESOLVED |
| Chain validity and first break point | `verify_chain` result | RESOLVED |
| Tip visibility | `get_tip` contract | RESOLVED |

Gaps found:
- None. The Ledger owns contract outputs, not a separate operational log format.

### 9. Resource Accounting
Description: Storage and connection resources the Ledger consumes.

| Resource | Accounting Method | Status |
| Disk growth | Append-only Ledger size; managed externally by Storage Management | RESOLVED |
| Connection count | Single persistent gRPC connection | RESOLVED |
| Write latency | Synchronous append acknowledgment | RESOLVED |

Gaps found:
- GAP-7: Resource Accounting | Need: atomic append mechanism selection | Existing: SIDE-001 | Gap Description: source material allowed multiple implementation options | Shared?: YES | Recommendation: choose the simplest approved v1 option and record it | Resolution: ASSUMED as Option B in D5 RQ-001 and CLR-004 | Impact If Unresolved: builder blocks on atomicity choice

## Clarification Log

### CLR-001
- Found During: D2, D3, D5
- Question: Does FMWK-001 define snapshot file format or only record snapshot metadata?
- Options: A) Ledger defines snapshot format now; B) Ledger records metadata only and FMWK-005 owns file format
- Status (OPEN|RESOLVED|ASSUMED): RESOLVED
- Blocks: No

Resolution:
- Option B. Source material explicitly marks snapshot format OPEN and tied to FMWK-005 needs. FMWK-001 owns the `snapshot_created` event payload only.

### CLR-002
- Found During: D2, D4, D6
- Question: What exactly does "offline verification" operate on?
- Options: A) Running immudb instance only; B) exported Ledger data/bytes with no runtime services
- Status (OPEN|RESOLVED|ASSUMED): ASSUMED
- Blocks: No

Resolution:
- Option B. NORTH_STAR and OPERATIONAL_SPEC require cold-storage validation without cognitive runtime, and source material says offline verification requires only the Ledger data file. The exact export packaging is left to tooling, not to FMWK-001.

### CLR-003
- Found During: D1, D4, D6
- Question: How should immudb credentials be handled across local and production environments?
- Options: A) Hardcode defaults everywhere; B) allow local defaults, require config/secrets for production
- Status (OPEN|RESOLVED|ASSUMED): RESOLVED
- Blocks: No

Resolution:
- Option B. Source material explicitly approves default credentials for local development only and requires config-driven credentials in production.

### CLR-004
- Found During: D4, D5, D6
- Question: Which atomic append strategy is the v1 default?
- Options: A) `ExecAll`; B) in-process mutex; C) `VerifiedSet`
- Status (OPEN|RESOLVED|ASSUMED): ASSUMED
- Blocks: No

Resolution:
- Option B for v1. The source material explicitly marks it acceptable under the single-writer architecture, which is itself stated in the authority docs. This assumption is recorded for builder execution and can be revisited if concurrency requirements change.

### CLR-005
- Found During: D3, D5
- Question: Should install lifecycle event naming use `framework_install` or `framework_installed`?
- Options: A) `framework_install`; B) `framework_installed`
- Status (OPEN|RESOLVED|ASSUMED): RESOLVED
- Blocks: No

Resolution:
- Option B. FWK-0's Ledger event catalog is the authoritative source for install lifecycle naming, so `framework_installed` is adopted and the local wording mismatch is treated as a source-material inconsistency.

## Summary
| Category | Gaps Found | Shared | Resolved | Remaining |
| Data In | 1 | 1 | 1 | 0 |
| Data Out | 1 | 1 | 1 | 0 |
| Persistence | 1 | 1 | 1 | 0 |
| Auth/Authz | 0 | 0 | 0 | 0 |
| External Services | 1 | 1 | 1 | 0 |
| Configuration | 1 | 0 | 1 | 0 |
| Error Propagation | 1 | 1 | 1 | 0 |
| Observability | 0 | 0 | 0 | 0 |
| Resource Accounting | 1 | 1 | 1 | 0 |

Gate verdict: PASS (zero open)
