# D5: Research — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | status:Complete | open questions:0

## Research Log

### RQ-001
- Prompted By: SC-002, IN-001, SIDE-001
- Priority: Blocking (must resolve before D7)
- Sources Consulted: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md; architecture/OPERATIONAL_SPEC.md; architecture/BUILD-PLAN.md
- Findings: The source material requires atomic read-tip-then-write behavior and lists three acceptable implementation options. The architecture also states a single-writer model, global monotonic sequence assignment, and hard-fail behavior on conflict.
- Options Considered:

| Option | Pros | Cons |
| Option A: immudb `ExecAll` transaction | Strong datastore-level atomicity | Source material does not confirm a final data shape or read/write sequence under this API |
| Option B: in-process mutex around tip read + append | Matches approved single-writer architecture, simple to verify, minimal moving parts | Relies on the single-writer invariant remaining true |
| Option C: immudb `VerifiedSet` | Strong server-assisted write semantics | Source material does not establish that it covers the full read-tip-assign-write sequence |

- Decision: Option B for v1 as an approved assumption.
- Rationale: The source material explicitly marks Option B acceptable because the architecture guarantees a single writer. That makes it the lowest-risk extraction-compatible choice for the first builder pass. If future concurrency requirements change, the choice can be revisited without changing the D1 scope boundary.

### RQ-002
- Prompted By: SC-006, E-007
- Priority: Blocking (must resolve before D7)
- Sources Consulted: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md; architecture/BUILDER_SPEC.md; architecture/OPERATIONAL_SPEC.md
- Findings: Snapshot existence, file path pattern, and replay semantics are approved, but snapshot file format is explicitly OPEN and depends on FMWK-005 graph needs. The Ledger only needs to record snapshot metadata in `snapshot_created`.
- Options Considered:

| Option | Pros | Cons |
| Option A: define snapshot format in FMWK-001 now | Would fully specify one more event payload context | Violates stated ownership boundary with FMWK-005 |
| Option B: keep format deferred, define only Ledger metadata contract | Matches source material and framework ownership boundaries | Leaves snapshot file contents to a later framework turn |

- Decision: Option B.
- Rationale: The source material explicitly says not to decide snapshot format here. The Ledger framework can be complete for Turn A by owning only the event metadata required for replay boundaries.

### RQ-003
- Prompted By: SC-005, E-005
- Priority: Blocking (must resolve before D7)
- Sources Consulted: sawmill/FMWK-001-ledger/SOURCE_MATERIAL.md; architecture/FWK-0-DRAFT.md
- Findings: The task source material names one lifecycle event `framework_install`, while FWK-0's event catalog names the install event `framework_installed`. FWK-0 is higher in the authority chain than framework-local source notes for install lifecycle naming.
- Options Considered:

| Option | Pros | Cons |
| Option A: use `framework_install` everywhere | Matches local source note wording | Conflicts with FWK-0 install lifecycle catalog |
| Option B: use `framework_installed` for install lifecycle events and record the mismatch | Matches the authoritative catalog for cold-storage validation | Requires explicit clarification logging |

- Decision: Option B.
- Rationale: Install lifecycle event naming must align with FWK-0 for cold-storage validation. The mismatch is recorded in D6 as resolved by authority order.

## Prior Art Review

### What Worked
- Append-only event sourcing with a derived materialized view works because it separates truth from runtime state and makes replay the universal recovery path.
- Exact canonical serialization contracts work because they remove cross-language hash ambiguity and make offline verification reproducible.
- Single-owner storage interfaces work because downstream frameworks can depend on one stable contract instead of ad hoc datastore calls.

### What Failed
- Shared ownership of persistence rules and derived-state interpretation fails because builders start mixing storage, folding, and business logic into one layer.
- Noncanonical JSON hashing fails because equivalent objects can hash differently across languages or libraries.
- Silent repair or hidden retries fail because operators lose the exact point where truth diverged or was unavailable.

### Lessons for This Build
- Keep FMWK-001 narrow: event truth, chain integrity, replay, and nothing more.
- Make byte-level serialization explicit in contracts, not implied by a library default.
- Prefer the simplest approved atomicity mechanism that matches the single-writer invariant, and document the assumption so later concurrency changes are visible.
