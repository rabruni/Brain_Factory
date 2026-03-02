# D5: Research — FMWK-001-ledger
Meta: v:1.0.0 (matches D2) | status:Complete | open questions:0

---

## Research Log

### RQ-001: Atomicity of read_tip + write_event
- Prompted By: D4 IN-001 (append contract), D2 SC-EC-002 (sequence conflict edge case)
- Priority: Blocking — must resolve before D7 (builder needs to know which mechanism to implement in `append()`)
- Sources Consulted: SOURCE_MATERIAL.md §immudb Integration §Sequence Numbering, BUILDER_SPEC.md §Ledger (single-writer architecture), immudb v1.9 gRPC API

Findings: The `append()` operation has an inherent read-then-write structure: (1) read current tip to get sequence N, (2) write event at sequence N+1. Without atomicity protection, a concurrent call (design violation, but defensible) could read the same tip and create a duplicate sequence. Three options exist:

Option A — immudb `ExecAll`: Batch the entire read+write in a single atomic immudb gRPC transaction. Server-side atomicity. No process-local state needed.

Option B — In-process mutex: A `threading.Lock()` (or `asyncio.Lock()`) guards the read-then-write sequence. Valid because BUILDER_SPEC.md explicitly declares single-writer architecture — exactly one caller (FMWK-002 Write Path) ever calls `append()` concurrently.

Option C — immudb `VerifiedSet`: Cryptographic server-side proof on every write. Strongest guarantee but adds round-trip latency for proof verification.

| Option | Pros | Cons |
|--------|------|------|
| A: ExecAll | True server-side atomicity; handles multi-writer if architecture evolves | immudb version-sensitive API; more complex implementation; requires understanding ExecAll transaction semantics |
| B: mutex | Simplest correct implementation; no immudb version dependency; sufficient for single-writer design | Breaks if single-writer invariant is violated and the process restarts mid-write; process-local only (no cross-process protection) |
| C: VerifiedSet | Cryptographic guarantee; proof is stored alongside data | Highest latency; most complex; proof overhead not needed at local development scale |

Decision: **Option B (in-process mutex)** for initial build. See D6 CLR-001 for rationale and human confirmation. The single-writer architecture makes B sufficient today. If the design ever introduces multi-writer scenarios, Option A is the migration path.

Rationale: SOURCE_MATERIAL.md lists Option B as acceptable, citing single-writer design. The mutex adds no external dependency and is the simplest correct solution. D1 Article 6 mandates `LedgerSequenceError` on conflict — this is the defense if the mutex assumption breaks.

---

### RQ-002: Event ID format — UUID v7 specifics
- Prompted By: D3 E-001 (event_id field)
- Priority: Blocking
- Sources Consulted: SOURCE_MATERIAL.md §Event Schema (explicitly specifies UUID v7), UUID RFC 9562

Findings: SOURCE_MATERIAL.md explicitly requires UUID v7. UUID v7 is time-ordered (monotonically increasing within millisecond granularity based on Unix timestamp), which means events are naturally sortable by event_id without needing to look at the sequence number. UUID v4 is random — unordered and provides no time context.

Key implication: UUID v7 event_ids can be used as a secondary sort key or as a human-readable creation timestamp. They MUST NOT replace `sequence` as the canonical ordering — `sequence` is the primary order. UUID v7 is for identity, not ordering.

Python library: `uuid7` (PyPI) or `uuid` in Python 3.12+ (which added UUID v7 support via `uuid.uuid7()`).

Decision: UUID v7 as specified. Use `uuid.uuid7()` from Python standard library (3.12+) or `uuid7` package if targeting < 3.12. Builder confirms Python version before choosing import.

Rationale: SOURCE_MATERIAL.md is unambiguous. No decision needed — extracting for builder reference.

---

### RQ-003: Snapshot file format (impact on Ledger)
- Prompted By: D2 SC-008 (snapshot event recording), D3 E-005 (SnapshotCreatedPayload), SOURCE_MATERIAL.md §Snapshots (explicitly marked OPEN)
- Priority: Blocking for FMWK-005 but not for FMWK-001 — the Ledger's payload is format-agnostic
- Sources Consulted: SOURCE_MATERIAL.md §Snapshots

Findings: SOURCE_MATERIAL.md marks snapshot format as OPEN and explicitly defers it to FMWK-005 (graph). The Ledger's involvement is limited to: (1) appending a `snapshot_created` event when told to, (2) that event contains `snapshot_path`, `snapshot_hash`, and `snapshot_sequence`. The format of the snapshot file (JSON, protobuf, binary) does not affect the Ledger's payload schema because the schema stores path + hash, not content.

Decision: Snapshot format is FMWK-005's decision. The Ledger's E-005 payload schema is format-agnostic. FMWK-001 can be fully built and tested without knowing snapshot format — the builder writes a `snapshot_created` event with whatever path/hash FMWK-005 supplies.

Rationale: Clean ownership boundary. The Ledger records that a snapshot occurred; FMWK-005 defines what a snapshot is.

---

### RQ-004: immudb gRPC library and platform_sdk contract
- Prompted By: D4 IN-007 (connect contract), D4 SIDE-001 (immudb write), D1 Article 7 (immudb abstraction)
- Priority: Blocking
- Sources Consulted: AGENT_BOOTSTRAP.md §Platform SDK Contract, BUILDER_SPEC.md §Constraints

Findings: AGENT_BOOTSTRAP.md states: "Any concern covered by platform_sdk MUST be satisfied through platform_sdk. No app, service, or agent may re-implement these concerns directly." The database concern (`platform_sdk.tier0_core.data`) is explicitly listed. BUILDER_SPEC.md confirms: "All access goes through the platform_sdk."

The question is whether `platform_sdk.tier0_core.data` currently exposes an immudb adapter. If not, the builder adds one following the platform_sdk pattern (Protocol interface + MockProvider + RealProvider). Either way, FMWK-001 imports from `platform_sdk.tier0_core.data` — never directly from any immudb SDK.

Decision: All immudb access through `platform_sdk.tier0_core.data`. If an immudb adapter does not exist in platform_sdk, the builder creates one as part of FMWK-001's implementation work, contributing it to platform_sdk before wiring it into FMWK-001. See D6 CLR-002 for the assumed state.

Rationale: Platform SDK contract is non-negotiable per AGENT_BOOTSTRAP.md. The architectural law is clear; the implementation path depends on platform_sdk's current state, which is resolved by assumption in D6.

---

### RQ-005: Float prohibition — decimal serialization strategy
- Prompted By: D4 SIDE-002 (canonical JSON serialization), D3 E-001 invariants, SOURCE_MATERIAL.md §Canonical JSON rules
- Priority: Blocking
- Sources Consulted: SOURCE_MATERIAL.md §Canonical JSON rules, Python json module documentation, IEEE 754 floating-point standard

Findings: Python, JavaScript, Go, Java, and Rust all implement IEEE 754 double-precision floats, but their `float-to-string` algorithms differ in edge cases. For example, `0.1 + 0.2` in Python produces `0.30000000000000004`, while the same operation in Go may produce a different string representation. If the Ledger stores a float and a CLI tool in a different language recomputes the hash, the canonical JSON will differ and the chain will appear broken.

SOURCE_MATERIAL.md mandates: "if a payload includes floats, they MUST be serialized as strings." This applies everywhere: base schema fields AND payload fields. The Ledger must enforce that no float-type Python value (`float`) appears in any event submitted to `append()`. Detection: walk the event dict recursively and fail with `LedgerSerializationError` if any `float` instance is found.

The primary affected fields:
- `base_weight` and `initial_methylation` in NodeCreationPayload (E-006): stored as decimal strings like `"0.5"`
- `delta` in signal_delta payload (FMWK-002): stored as signed decimal string like `"+0.05"` or `"-0.1"`

Decision: Prohibit floats universally. Enforce at serialization time — recursive type check before `json.dumps()`. Any `float` type found raises `LedgerSerializationError`. All decimal values are strings. Builder enforces this in SIDE-002 implementation.

Rationale: Cross-language hash chain verification is a hard requirement (D1 Article 8 cold-storage verifiability). Float serialization drift is a silent bug that breaks verification across language boundaries. String representation is the safe, deterministic choice.

---

### RQ-006: Key format for immudb storage
- Prompted By: D4 SIDE-001 (immudb write shape)
- Priority: Informational (builder reference, not an architectural decision)
- Sources Consulted: SOURCE_MATERIAL.md §immudb Integration (immudb mapping section)

Findings: SOURCE_MATERIAL.md specifies: key = sequence number as zero-padded string. The zero-padding is required because immudb's `Scan` operation uses lexicographic key ordering — without zero-padding, `"10"` sorts before `"9"` alphabetically. With zero-padding to 12 digits: `"000000000009"` sorts before `"000000000010"` correctly.

Decision: Key format: 12-digit zero-padded decimal sequence number string. E.g., sequence 42 → key `"000000000042"`. 12 digits supports up to 999,999,999,999 events — effectively unbounded for foreseeable use.

Rationale: SOURCE_MATERIAL.md specifies this as implementation detail. 12 digits chosen for safety margin. No architectural decision — builder reference only.

---

## Prior Art Review

### What Worked

**Event sourcing with append-only logs (Kafka, EventStore, Axon):** Separating event storage from projection/fold logic is a proven pattern at production scale. The Ledger-stores / Write-Path-folds split follows this pattern. Systems that maintain this separation can replay history with improved fold logic (retroactive healing) without touching the truth store.

**Hash-chained audit logs (Certificate Transparency, Git):** Verifiable by any party holding the data, with no trusted runtime authority needed at verification time. Git's Merkle tree proves content; Certificate Transparency's append-only log proves ordering. Both are verifiable from cold storage — the same property DoPeJarMo needs for operator lockout protection.

**Key-value store as event log (Kafka using log compaction, immudb native):** Using a KV store with monotonic keys for ordered event retrieval is a well-established pattern. The zero-padded sequence key provides scan ordering without immudb needing to understand the semantic ordering of events.

### What Failed

**Event stores with mutable state (UPDATE support):** Any system where events can be modified in place breaks replay determinism. If event 42 is different today than it was at write time, replaying the Ledger produces a different Graph — the invariant "Graph is deterministically derived from Ledger" fails silently. Immutability is not optional.

**Previous DoPeJarMo builds that added execution to the event store:** When the storage layer contains interpretation logic, it becomes coupled to every framework that writes events. The test surface expands with every new event type. Isolated testing becomes impossible. This is the precise pattern D1 Article 2 (MERGING) prohibits.

**Event IDs as primary ordering keys (instead of sequence):** Using UUIDs or timestamps as the canonical order is problematic because UUID v4 is unordered and timestamps can collide or go backward (NTP adjustment, leap seconds). An explicit monotonic sequence assigned by the store is the only reliable ordering primitive.

### Lessons for This Build

1. **The Ledger interface MUST be thin and stable.** Every method added is a surface that every framework depends on. The six methods (append, read, read_range, read_since, verify_chain, get_tip) plus connect cover all known use cases. Do not add methods speculatively.

2. **The canonical JSON serialization contract (SIDE-002) MUST be tested across at least two languages before any cross-language consumer exists.** Write the contract once, test it in Python (canonical implementation) and verify a second implementation (even pseudocode) produces identical output for the same input. Don't leave cross-language compatibility to convention.

3. **The atomicity decision (RQ-001) MUST be made before the builder starts.** It is central to the `append()` implementation. Retrofitting a different atomicity mechanism after the first events are written risks data integrity if the swap is not perfectly clean.

4. **Prohibit floats at the input boundary, not the output boundary.** Checking for floats at `append()` time (SIDE-002 float detection) catches the bug at the caller, not during `verify_chain()` when diagnosing the problem is much harder.
