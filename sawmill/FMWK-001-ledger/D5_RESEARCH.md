# D5: Research — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | status:Complete | open questions:0

## Research Log
### RQ-001
- Prompted By: D4 SIDE-001, D2 SC-002, D2 SC-009
- Priority: Blocking (must resolve before D7)
- Sources Consulted: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md, architecture/FWK-0-DRAFT.md, architecture/BUILDER_SPEC.md
- Findings: The ledger must make tip-read plus write atomic. Source material lists three acceptable implementation options and explicitly notes single-writer architecture. No authority requires an immudb-specific transactional primitive, only the atomicity outcome.
- Options Considered:

| Option | Pros | Cons |
| Option A: immudb `ExecAll` transaction | Strong server-side grouping if supported as needed | Ties the contract to a specific immudb transaction shape not otherwise required by authority docs |
| Option B: in-process mutex around append critical section | Matches single-writer architecture, minimal mechanism, easiest to reason about, keeps contract at ledger boundary | Relies on process-local single-writer discipline; less future-proof if the architecture later allows multi-writer runtime |
| Option C: immudb `VerifiedSet` | Strong immudb-assisted write path | Source material does not establish it as necessary for the required sequence-assignment semantics |

- Decision: Option B
- Rationale: Source material explicitly marks an in-process lock as acceptable because the architecture guarantees a single writer. This is the narrowest assumption consistent with current authority while still satisfying atomic sequencing and explicit fork rejection.

### RQ-002
- Prompted By: D2 SC-007, D3 E-009
- Priority: Informational
- Sources Consulted: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md, architecture/BUILDER_SPEC.md, architecture/OPERATIONAL_SPEC.md
- Findings: Snapshot file format is intentionally unresolved at the ledger level because it depends on graph serialization needs. The ledger only needs a stable reference event so replay can resume after a snapshot boundary.
- Options Considered:

| Option | Pros | Cons |
| JSON snapshot owned by ledger | Simple to inspect | Violates graph ownership; ledger would start defining graph persistence format |
| Protobuf snapshot owned by ledger | Compact and versionable | Same ownership violation; adds unnecessary format choice now |
| Ledger stores only snapshot reference event and path/hash | Preserves ledger ownership boundaries and leaves graph format to FMWK-005 | Requires later framework to define actual file contents |

- Decision: Ledger stores only snapshot reference event and path/hash
- Rationale: This matches the approved source material, preserves exclusive ownership boundaries, and closes the current spec without inventing graph serialization.

### RQ-003
- Prompted By: D4 SIDE-002, D2 SC-005, D2 SC-011
- Priority: Blocking (must resolve before D7)
- Sources Consulted: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md
- Findings: Hash-chain integrity is a byte-level contract. The source material specifies exact canonical JSON rules, UTF-8 encoding, null preservation, unicode handling, and float avoidance requirements needed to keep online and offline verification aligned.
- Options Considered:

| Option | Pros | Cons |
| Language-default JSON serialization | Simple to call | Non-deterministic across runtimes and violates source material |
| Canonical UTF-8 JSON with explicit rules | Deterministic, portable, matches approved source | Requires stricter validation and fixtures |

- Decision: Canonical UTF-8 JSON with explicit byte-level rules
- Rationale: It is the only option consistent with the source material and with cross-language hash-chain verification.

## Prior Art Review
### What Worked
- Ledger-first, graph-derived architecture works because replay and audit depend on one immutable truth source.
- Single-writer synchronous append models keep failure boundaries clean: acknowledged means durable, unacknowledged means absent.
- Cold-storage validation works when verification uses only stored data plus deterministic serialization rules.

### What Failed
- Letting storage layers absorb graph logic or business semantics causes framework drift and ownership confusion.
- Allowing serializer defaults or multiple hash formats creates unverifiable cross-runtime chains.
- Hiding provisioning inside runtime connection logic creates race conditions and violates infrastructure ownership boundaries.

### Lessons for This Build
- Keep the ledger contract mechanical and narrow.
- Lock down serialization and hash formatting as exact-string fixtures, not loose semantic checks.
- Treat snapshot contents as graph-owned and keep ledger responsibility limited to ordered reference events.
