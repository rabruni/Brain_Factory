# D5: Research — Ledger (FMWK-001)
Meta: v:1.0.0 (matches D2) | status:Complete | open questions:0

---

## Research Log

### RQ-001 — Atomicity strategy for append()

- Prompted By: SOURCE_MATERIAL.md (immudb integration → atomicity section); D4 IN-001 postcondition #5 ("No fork: exactly one event exists at the returned sequence_number")
- Priority: Blocking (must resolve before D7 — the in-process lock strategy must be specified in the builder handoff)
- Sources Consulted: SOURCE_MATERIAL.md (explicit atomicity options), BUILDER_SPEC.md §Ledger (single-writer architecture), OPERATIONAL_SPEC.md §Docker Topology (single kernel process per deployment)

**Problem Statement:** The Ledger's append() method must atomically read the current tip (to determine the next sequence number) and write the new event. A non-atomic read-then-write creates a window where two callers could both read the same tip sequence N, both compute "next sequence = N+1," and both attempt to write at sequence N+1, creating a fork. The Ledger must prevent this.

**Findings:** Three options were identified in SOURCE_MATERIAL.md. The single-writer architecture in BUILDER_SPEC.md is the key constraint that informs the decision.

- Options Considered:

| Option | Pros | Cons |
|--------|------|------|
| A: immudb ExecAll (batch read+write in single transaction) | Server-side atomicity; no application-level lock needed | ExecAll may not exist in immudb v2+ gRPC API; requires API verification; adds complexity |
| B: In-process mutex/lock | Simple; sufficient for single-writer architecture; no gRPC API version risk | Application-level only; fails if multiple kernel processes connect to same immudb database |
| C: immudb VerifiedSet (server-side cryptographic verification) | Server-side atomicity + built-in hash verification | Higher per-append latency (cryptographic proof generation); more complex integration |

- Decision: **Option B — In-process mutex/lock**

- Rationale: The BUILDER_SPEC.md single-writer architecture guarantees exactly one kernel process. Only the Write Path (FMWK-002) calls append(), and there is exactly one Write Path instance. An in-process mutex (threading.Lock() or asyncio.Lock() depending on the implementation's concurrency model) is sufficient to serialize all append() calls within the single kernel process. This eliminates gRPC API compatibility risk (Option A depends on ExecAll availability) and avoids the per-append latency cost of Option C. The assumption (single kernel process) is explicitly documented so it can be revisited if multi-process deployment is ever needed.

**Architectural assumption recorded:** If DoPeJarMo ever deploys with multiple kernel processes sharing a single immudb instance, Option B fails and must be replaced with Option A or C. This constraint must be in the builder's context (D10) and the BUILDER_HANDOFF.

---

### RQ-002 — UUID version for event_id generation

- Prompted By: D3 E-001 LedgerEvent.event_id field (specified as UUID v7)
- Priority: Blocking (builder must use correct UUID version and correct SDK module)
- Sources Consulted: AGENT_BOOTSTRAP.md §Platform SDK (platform_sdk.tier0_core.ids), SOURCE_MATERIAL.md (event schema shows "uuid-v7" as type)

**Findings:** UUID v7 is time-ordered, which ensures that event_ids from the same session are naturally sortable by creation time. The platform_sdk.tier0_core.ids module provides ID generation. The builder MUST NOT import a raw uuid library — all ID generation goes through platform_sdk.

- Decision: Use platform_sdk.tier0_core.ids for all event_id generation.
- Rationale: Platform SDK contract requires all concerns covered by the SDK to be satisfied through the SDK. ID generation is covered. Direct uuid library imports bypass the MockProvider mechanism and make the Ledger untestable without live services.

---

### RQ-003 — Canonical JSON cross-language compatibility

- Prompted By: SOURCE_MATERIAL.md (canonical JSON rules section), D3 Canonical JSON Serialization Constraint
- Priority: Blocking (the hash chain only works if every implementation produces identical bytes)
- Sources Consulted: SOURCE_MATERIAL.md (explicit Python reference implementation)

**Problem Statement:** The canonical JSON serialization used for hash computation must produce identical byte sequences regardless of which language or library implementation uses it. If Python's json.dumps and a future Go or Rust implementation produce different byte orderings, the hash chain breaks across language boundaries.

**Findings:** The SOURCE_MATERIAL.md provides a precise Python reference: `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`. The key invariants are: (1) alphabetical key sort at every nesting level, (2) no whitespace, (3) literal UTF-8 characters (not \uNNNN escapes), (4) floats stored as strings (eliminating floating-point representation differences), (5) hash field excluded from input.

- Decision: The Python reference implementation in SOURCE_MATERIAL.md is canonical. The builder implements it exactly. Test suite MUST include a test vector: given a known event dict, the canonical hash must equal a hardcoded expected value. This test vector validates cross-language correctness.
- Rationale: Explicit test vectors are the only reliable way to guarantee byte-level correctness. The D4 SIDE-002 contract specifies the full rules; the test vector enforces them.

---

### RQ-004 — Empty Ledger get_tip() behavior

- Prompted By: D2 SC-006 (get_tip) — what does the Ledger return when no events have been appended yet?
- Priority: Blocking (builder must handle this case; it affects Write Path bootstrap logic)
- Sources Consulted: SOURCE_MATERIAL.md (does not explicitly specify the empty case)

**Findings:** The Write Path calls get_tip() before every append() to determine the next sequence number and the previous_hash for the new event. On first startup (genesis event not yet written), get_tip() must return something that lets the Write Path correctly construct the genesis event: sequence=0 and previous_hash="sha256:"+64zeros.

- Decision: get_tip() on an empty Ledger returns TipRecord{sequence_number: -1, hash: "sha256:0000000000000000000000000000000000000000000000000000000000000000"}.
- Rationale: sequence_number=-1 signals "empty" to the Write Path. The Write Path computes next_sequence = -1 + 1 = 0 (genesis). The returned hash is the genesis previous_hash sentinel value — so the Write Path can use it directly as the genesis event's previous_hash without a special case. This ensures the Write Path's append logic is uniform: "read tip, set previous_hash=tip.hash, set sequence=tip.sequence_number+1, write event." See D6 CLR-002 for the resolved clarification.

---

### RQ-005 — Connection retry policy

- Prompted By: SOURCE_MATERIAL.md (connection handling section), D4 ERR-001 definition
- Priority: Blocking (retry behavior must be specified precisely for the builder)
- Sources Consulted: SOURCE_MATERIAL.md (explicit: "close, wait 1 second, reconnect, retry once")

**Findings:** SOURCE_MATERIAL.md specifies the exact retry policy: on disconnect, close the connection, wait 1 second, reconnect, retry the operation once. If the retry fails, return LedgerConnectionError.

- Decision: Implement exactly as specified. One reconnect attempt, one operation retry, 1-second wait. No exponential backoff, no additional retries. The Write Path (FMWK-002) owns retry policy above this level.
- Rationale: The Ledger's retry is a connection-level recovery, not a business-level retry. Keeping it minimal (one attempt) ensures the Write Path gets a fast failure signal and can implement appropriate backoff or blocking at the appropriate level.

---

## Prior Art Review

### What Worked

**Append-only event sourcing with immudb**: immudb is designed exactly for this use case — append-only, hash-chained, tamper-evident. Its built-in hash verification (immudb's `VerifiedGet`) can serve as an additional integrity layer. The pattern of using a monotonic sequence number as the immudb key (zero-padded string) enables range scans that immudb's Scan operation supports efficiently.

**Hash chain design (blockchain pattern)**: The linear hash chain where each event's previous_hash references the prior event's hash is well-proven for tamper detection. The genesis sentinel value ("sha256:"+64zeros) is a clean convention that eliminates special-casing the first event.

**Canonical JSON for deterministic hashing**: The pattern of sorting keys and removing whitespace before hashing is used in JSON Web Signatures (JWS/RFC 7515) and JSON Canonicalization Scheme (RFC 8785). The choice to store floats as strings eliminates the most common cross-language hashing divergence.

### What Failed

**Direct LLM/service imports in previous builds**: Previous DoPeJarMo iterations had agents import immudb or other service libraries directly. This made tests impossible without live services and created tight coupling that broke during SDK updates. This build enforces the platform_sdk contract to prevent recurrence.

**Adding query capabilities to the Ledger**: Previous builds drifted by adding field-level filtering to the Ledger (e.g., "get all signal_delta events for node X"). This broke the Ledger's single-responsibility boundary and created a pseudo-database with no query optimization. All query capability belongs in the Graph (FMWK-005) which is built specifically for it.

**Wall-clock time for sequence ordering**: Using wall-clock timestamps as the primary ordering mechanism failed when two events were written in the same millisecond. This build uses monotonic sequence numbers as the ordering primitive; timestamps are metadata only.

**Storing floats as JSON numbers**: Previous attempts to store methylation values as raw JSON floats (e.g., 0.1) produced hash divergence because Python, JavaScript, and Go represent 0.1 differently in IEEE 754 float64. This build serializes all floats as strings.

### Lessons for This Build

1. **Keep the Ledger interface to exactly 6 methods.** Every addition to the interface is a scope creep risk. All query capability belongs in the Graph.
2. **Specify the canonical JSON contract byte-for-byte with a test vector.** Never assume two implementations will produce the same bytes without a concrete test.
3. **The in-process mutex (RQ-001) is an architectural assumption.** Document it explicitly in D10 so the builder understands the constraint and future maintainers can revisit if deployment changes.
4. **Empty Ledger get_tip() must be consistent with the genesis event construction.** An off-by-one in the empty case breaks the genesis event's previous_hash, which cascades to break the entire chain.
