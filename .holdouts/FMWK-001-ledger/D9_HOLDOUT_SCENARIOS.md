# D9: Holdout Scenarios — Ledger (FMWK-001)
Meta: v:1.0.0 | contracts:D4 v:1.0.0 | status:Final | author:holdout-agent | last run:Not yet executed
CRITICAL: Builder MUST NOT see these scenarios before completing work.

## Purpose
Behavioral holdout scenarios for the Ledger (FMWK-001) append-only hash-chained event store.
All assertions derive exclusively from D2 and D4. No executable code. No class names. No method calls.
The evaluator discovers HOW to call the implementation from staged code; this document specifies only WHAT must be true.

---

## Scenarios

### HS-001 — Genesis append assigns sequence 0 with zero previous_hash

```yaml
scenario_id: "HS-001"
title: "Genesis append assigns sequence 0 with zero previous_hash"
priority: P0
authority:
  d2_scenarios: [SC-001]
  d4_contracts: [IN-001, IN-006, OUT-001, SIDE-002]
category: happy-path
setup:
  description: >
    The Ledger contains no events. The tip query before the action confirms the
    ledger is empty (sequence_number=-1).
  preconditions:
    - Ledger has no previously appended events.
    - A tip query confirms sequence_number=-1 and hash="sha256:0000000000000000000000000000000000000000000000000000000000000000".
action:
  description: >
    A caller submits a valid node_creation event to the append operation with all
    required fields populated.
  steps:
    - Submit a node_creation event with event_type="node_creation", schema_version="1.0.0",
      a valid ISO-8601 UTC timestamp with Z suffix, provenance.framework_id="FMWK-002",
      provenance.actor="system", and a payload containing node_id (UUID v7),
      node_type (a non-empty string), initial_methylation ("0.0"), base_weight ("0.5").
    - Record the return value.
expected_outcome:
  description: >
    Append succeeds and returns integer 0. The stored event carries the genesis
    previous_hash. The tip advances to reflect the new event.
  assertions:
    - subject: "return value from the append operation"
      condition: "is the integer 0"
      observable: "The returned sequence number equals 0 exactly."
    - subject: "previous_hash field of the event stored at sequence 0"
      condition: "equals 'sha256:0000000000000000000000000000000000000000000000000000000000000000'"
      observable: >
        Reading the event back at sequence 0 reveals previous_hash is the 64-zero
        sentinel value defined for genesis.
    - subject: "hash field of the event stored at sequence 0"
      condition: >
        equals the SHA-256 of the canonical JSON of the event with the hash field
        excluded (keys sorted alphabetically at every level, no whitespace separators,
        ensure_ascii=False, UTF-8 encoded), formatted as 'sha256:' + lowercase hexdigest
      observable: >
        Independently recomputing SHA-256 over the canonical JSON (hash excluded)
        reproduces the stored hash value.
    - subject: "tip state immediately after the append returns"
      condition: "get_tip() returns sequence_number=0 and hash matching the stored event's hash"
      observable: "A tip query after the append returns sequence_number=0."
  negative_assertions:
    - "Return value is not 1 or any integer other than 0."
    - "previous_hash is not null, empty, or a hash derived from any prior event."
    - "get_tip().sequence_number remains -1 after a successful append."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "Return value from append operation."
  - "previous_hash field of event at sequence 0."
  - "hash field of event at sequence 0."
  - "Independently computed SHA-256 of canonical JSON (hash excluded)."
  - "get_tip() return value immediately after append."
```

**Authority Basis:**
- D2 SC-001: "WHEN append() is called with a valid node_creation event THEN the Ledger assigns sequence=0 AND sets previous_hash=sha256:0000000000000000000000000000000000000000000000000000000000000000 AND computes hash=SHA-256 of the canonical JSON (hash field excluded) AND persists the event to immudb AND returns sequence_number=0."
- D4 IN-001 postcondition 1: "Returns an integer sequence_number ≥ 0."
- D4 IN-001 postcondition 3: "the returned event's previous_hash equals the hash of the event at sequence returned_sequence_number-1 (or 'sha256:'+64zeros if returned_sequence_number=0)."
- D4 IN-001 postcondition 4: "the returned event's hash equals the SHA-256 of its canonical JSON (hash field excluded; see SIDE-002)."
- D4 IN-001 postcondition 7: "immediately after append() returns, get_tip() returns {sequence_number: returned_sequence_number, hash: <hash_of_new_event>}."
- D4 IN-006 postcondition 2: "If Ledger is empty: returns TipRecord{sequence_number: -1, hash: 'sha256:0000000000000000000000000000000000000000000000000000000000000000'} (see D6 CLR-002)."
- D4 SIDE-002: "keys sorted alphabetically at every nesting level; separators=(',',':') — no spaces; ensure_ascii=False; encode to UTF-8 bytes (no BOM); compute SHA-256; format as 'sha256:' + hexdigest in lowercase."

---

### HS-002 — Sequential appends form an unbroken hash chain

```yaml
scenario_id: "HS-002"
title: "Sequential appends form an unbroken hash chain"
priority: P0
authority:
  d2_scenarios: [SC-002]
  d4_contracts: [IN-001, IN-002, OUT-001, OUT-002, SIDE-002]
category: happy-path
setup:
  description: >
    The Ledger already contains four events at sequences 0 through 3, appended
    sequentially. Tip is at sequence 3.
  preconditions:
    - Four events have been appended successfully (sequences 0, 1, 2, 3).
    - get_tip() returns sequence_number=3.
    - Each event's previous_hash links correctly to the hash of the preceding event.
action:
  description: >
    A caller appends a fifth event. The return value and the chain linkage are inspected.
  steps:
    - Submit a valid signal_delta event (event_type="signal_delta") with all required
      fields. Record the return value (expected: 4).
    - Read back the event at the returned sequence number. Inspect previous_hash and hash.
    - Read back the event at sequence 3. Compare its hash to the new event's previous_hash.
    - Query get_tip().
expected_outcome:
  description: >
    Fifth append returns sequence 4. The new event's previous_hash equals the hash
    stored in the event at sequence 3. The chain is unbroken through all five events.
  assertions:
    - subject: "return value from the fifth append"
      condition: "is the integer 4"
      observable: "Returned sequence_number=4."
    - subject: "previous_hash of the event at sequence 4"
      condition: "equals the hash field of the event at sequence 3"
      observable: >
        Reading event at sequence 4 then event at sequence 3; the previous_hash
        of event 4 matches the hash of event 3 exactly.
    - subject: "hash of the event at sequence 4"
      condition: "equals the SHA-256 of the canonical JSON of that event with hash field excluded"
      observable: >
        Recomputing SHA-256 over the canonical JSON (hash excluded) reproduces the
        stored hash value for event 4.
    - subject: "get_tip() after the fifth append"
      condition: "returns sequence_number=4 and hash matching the hash of event at sequence 4"
      observable: "Tip query returns sequence_number=4 and the correct hash."
    - subject: "chain linkage for all events 0 through 4"
      condition: >
        each event's previous_hash equals the hash of the event at sequence-1
        (or 64-zero hash for sequence 0)
      observable: >
        Iterating read(0) through read(4) and checking previous_hash on each
        reveals an unbroken chain.
    - subject: "monotonicity across all five appends"
      condition: "sequences are exactly 0, 1, 2, 3, 4 with no gaps"
      observable: "read(0) through read(4) all succeed; read(5) raises LedgerSequenceError."
  negative_assertions:
    - "Return value is not 3, 5, or any value other than 4."
    - "previous_hash of event 4 does not equal the hash of any event other than event 3."
    - "get_tip().sequence_number remains 3 after a successful append."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "Return value from the fifth append operation."
  - "previous_hash of the event at sequence 4."
  - "hash of the event at sequence 3 (for comparison)."
  - "hash of the event at sequence 4."
  - "get_tip() return value after fifth append."
```

**Authority Basis:**
- D2 SC-002: "WHEN append() is called with a valid event THEN the Ledger assigns sequence=N AND sets previous_hash=hash_of_event_at_sequence_N-1 AND computes hash=SHA-256 of canonical JSON (hash excluded) AND persists the event AND returns sequence_number=N AND get_tip() returns {sequence_number:N, hash:<hash_of_new_event>}."
- D4 IN-001 postcondition 3: "the returned event's previous_hash equals the hash of the event at sequence returned_sequence_number-1."
- D4 IN-001 postcondition 4: "the returned event's hash equals the SHA-256 of its canonical JSON."
- D4 IN-001 postcondition 5: "Monotonicity: returned sequence_number = (previous tip.sequence_number + 1). No gaps, no skips."
- D4 IN-001 postcondition 7: "immediately after append() returns, get_tip() returns {sequence_number: returned_sequence_number, hash: <hash_of_new_event>}."
- D4 IN-002 postcondition 2: "If sequence_number > tip.sequence_number: raises LedgerSequenceError."

---

### HS-003 — Read operations return complete events in correct order

```yaml
scenario_id: "HS-003"
title: "Read operations return complete events in correct order"
priority: P0
authority:
  d2_scenarios: [SC-003, SC-004, SC-005]
  d4_contracts: [IN-002, IN-003, IN-004, OUT-002, OUT-003]
category: happy-path
setup:
  description: >
    The Ledger contains exactly 11 events at sequences 0 through 10, appended
    sequentially. Tip is at sequence 10.
  preconditions:
    - Eleven events have been successfully appended (sequences 0 through 10).
    - get_tip() returns sequence_number=10.
action:
  description: >
    Three read operations are performed: single-event read, range read, and since read.
    A fourth read_since call uses the tip as the argument to confirm empty-list behavior.
  steps:
    - Perform a single-event read for sequence 5. Record the returned event.
    - Perform a range read for start=3, end=7. Record the returned list.
    - Perform a since read for sequence_number=5. Record the returned list.
    - Perform a since read for sequence_number=10 (tip). Record the returned list.
expected_outcome:
  description: >
    Each read operation returns exactly the events specified by D4 contracts,
    in ascending sequence order, with all fields intact.
  assertions:
    - subject: "event returned by read(5)"
      condition: >
        is a complete LedgerEvent with sequence=5 and all fields present:
        event_id, sequence, event_type, schema_version, timestamp, provenance,
        previous_hash, payload, hash
      observable: "A single complete event is returned; its sequence field equals 5."
    - subject: "hash field of the event returned by read(5)"
      condition: "is identical to what was stored at append time (not recomputed)"
      observable: "hash equals the value stored during append; no recomputation on read."
    - subject: "list returned by read_range(3, 7)"
      condition: "contains exactly 5 events at sequences 3, 4, 5, 6, 7 in ascending order"
      observable: >
        List length is 5; first event has sequence=3; last event has sequence=7;
        sequences are contiguous and ascending.
    - subject: "list returned by read_since(5)"
      condition: >
        contains exactly 5 events at sequences 6, 7, 8, 9, 10 in ascending order
        (sequence > 5, up to and including tip at 10)
      observable: >
        List length is 5; first event has sequence=6; last event has sequence=10;
        event with sequence=5 is NOT present.
    - subject: "list returned by read_since(10)"
      condition: "is an empty list []"
      observable: "No events are returned when sequence_number equals tip.sequence_number."
  negative_assertions:
    - "read(5) does not return more than one event."
    - "read_range(3, 7) does not include events at sequences 2 or 8."
    - "read_since(5) does not include the event at sequence 5."
    - "read_since(5) does not return events in any order other than ascending."
    - "read_since(10) does not return a non-empty list."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "All fields of the event returned by read(5)."
  - "Sequences of all events returned by read_range(3, 7)."
  - "Count and sequences of events returned by read_since(5)."
  - "Return value of read_since(10)."
```

**Authority Basis:**
- D2 SC-003: "WHEN read(5) is called THEN returns the complete LedgerEvent stored at sequence 5 with all fields: event_id, sequence=5, event_type, schema_version, timestamp, provenance, previous_hash, payload, hash."
- D2 SC-004: "WHEN read_range(3, 7) is called THEN returns exactly 5 events, at sequences 3,4,5,6,7 in ascending order, with all fields intact."
- D2 SC-005: "WHEN read_since(5) is called THEN returns exactly 5 events at sequences 6,7,8,9,10 in ascending order."
- D4 IN-002 postcondition 1: "returns the complete LedgerEvent (E-001) stored at that sequence number, with all fields."
- D4 IN-002 postcondition 4: "The returned event's hash is identical to what was stored at append time — the Ledger does not recompute hashes on read."
- D4 IN-003 postcondition 1: "returns a list of (end - start + 1) LedgerEvents at sequences start, start+1, ..., end inclusive, in ascending order."
- D4 IN-004 postcondition 1: "Returns all events with sequence > sequence_number, in ascending order."
- D4 IN-004 postcondition 2: "If sequence_number = tip.sequence_number: returns an empty list []."

---

### HS-004 — Tip reflects empty-ledger sentinel and advances after each append

```yaml
scenario_id: "HS-004"
title: "Tip reflects empty-ledger sentinel and advances after each append"
priority: P0
authority:
  d2_scenarios: [SC-006]
  d4_contracts: [IN-006, IN-001, OUT-004]
category: edge-case
setup:
  description: >
    The Ledger contains no events. Tip query is performed before any appends to
    confirm the empty-ledger sentinel value.
  preconditions:
    - Ledger has no previously appended events.
action:
  description: >
    The tip is queried before any appends, then after each of two sequential appends.
    After each append the tip is immediately queried and compared to the append result.
  steps:
    - Query get_tip() before any appends. Record the result.
    - Append a first event (any valid event_type). Record the returned sequence_number (expected: 0).
    - Immediately query get_tip(). Record the result.
    - Append a second event (any valid event_type). Record the returned sequence_number (expected: 1).
    - Immediately query get_tip(). Record the result.
    - Read the event at each returned sequence number and compare its hash to get_tip().hash.
expected_outcome:
  description: >
    Tip on empty ledger returns the defined sentinel. After each append, tip
    immediately reflects the new sequence number and hash.
  assertions:
    - subject: "get_tip() before any appends"
      condition: >
        returns TipRecord{sequence_number: -1,
        hash: 'sha256:0000000000000000000000000000000000000000000000000000000000000000'}
      observable: "sequence_number is -1 and hash is the 64-zero sentinel."
    - subject: "get_tip() immediately after first append returning sequence 0"
      condition: "returns TipRecord{sequence_number: 0, hash: <hash_of_event_0>}"
      observable: "sequence_number is 0; hash matches hash field of event at sequence 0."
    - subject: "get_tip() immediately after second append returning sequence 1"
      condition: "returns TipRecord{sequence_number: 1, hash: <hash_of_event_1>}"
      observable: "sequence_number is 1; hash matches hash field of event at sequence 1."
    - subject: "get_tip().hash vs read(N).hash after each append"
      condition: "get_tip().hash equals the hash field of the event returned by read(N)"
      observable: >
        For each appended event at sequence N, the hash from get_tip() matches the
        hash field of the event returned by read(N).
  negative_assertions:
    - "get_tip() returns sequence_number=0 when ledger is empty."
    - "get_tip().hash is null or empty after a successful append."
    - "get_tip().sequence_number stays at a prior value after a successful append."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "get_tip() return value before any appends."
  - "Return value from each append operation."
  - "get_tip() return value immediately after each append."
  - "hash field of read(0) and read(1) for comparison with tip hash."
```

**Authority Basis:**
- D2 SC-006: "GIVEN a Ledger with events at sequences 0 through N WHEN get_tip() is called THEN returns TipRecord with sequence_number=N and hash=hash_of_event_at_sequence_N AND a subsequent append followed by get_tip() returns sequence_number=N+1."
- D4 IN-006 postcondition 1: "If Ledger is non-empty: returns TipRecord{sequence_number: N, hash: <hash_of_event_at_N>} where N is the sequence number of the most recently appended event."
- D4 IN-006 postcondition 2: "If Ledger is empty: returns TipRecord{sequence_number: -1, hash: 'sha256:0000000000000000000000000000000000000000000000000000000000000000'} (see D6 CLR-002)."
- D4 IN-006 postcondition 3: "The returned hash equals the hash field of the event returned by read(N)."
- D4 IN-006 postcondition 4: "After a successful append() returning sequence_number=K, an immediate get_tip() returns TipRecord{sequence_number: K, hash: <hash_of_event_K>}."

---

### HS-005 — Hash chain verification detects intact chain and locates corruption

```yaml
scenario_id: "HS-005"
title: "Hash chain verification detects intact chain and locates corruption"
priority: P0
authority:
  d2_scenarios: [SC-007, SC-008]
  d4_contracts: [IN-005, OUT-005, ERR-002]
category: integrity
setup:
  description: >
    The Ledger contains 10 events at sequences 0 through 9, all appended cleanly.
    No corruption has been introduced.
  preconditions:
    - Ten events appended successfully (sequences 0 through 9).
    - No artificial modification of stored events.
action:
  description: >
    Two verification calls are made. First on the intact chain. Then after corruption
    is injected at sequence 3 in the test harness (the stored hash no longer matches
    the recomputed SHA-256), the verification is repeated.
  steps:
    - Call verify_chain() with no arguments on the intact 10-event chain. Record result.
    - Using the test harness, inject corruption at sequence 3 so that the stored hash
      for that event no longer matches the SHA-256 of its canonical JSON.
    - Call verify_chain() with no arguments again. Record result.
expected_outcome:
  description: >
    Intact chain returns valid=true. Corrupted chain returns valid=false and
    identifies sequence 3 as the first failure point.
  assertions:
    - subject: "ChainVerificationResult from verify_chain() on intact chain"
      condition: "valid=true, break_at=null"
      observable: "First verification call returns valid=True and break_at is null/None."
    - subject: "ChainVerificationResult from verify_chain() after corruption at sequence 3"
      condition: "valid=false, break_at=3"
      observable: >
        Second verification call returns valid=False; break_at equals 3 (the lowest
        sequence with hash or linkage failure).
    - subject: "break_at value when corruption is at sequence 3"
      condition: "is 3, not a sequence number greater than 3"
      observable: >
        Verification stops at the first detected failure; break_at is the LOWEST
        sequence with any failure.
  negative_assertions:
    - "Intact chain does not return valid=false."
    - "Intact chain does not return a non-null break_at."
    - "Corrupted chain at sequence 3 does not return valid=true."
    - "break_at is not a sequence number > 3 when corruption is at sequence 3."
    - "verify_chain() does not raise LedgerConnectionError for a hash mismatch; it returns ChainVerificationResult{valid:false}."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "ChainVerificationResult from intact chain verification (valid and break_at)."
  - "ChainVerificationResult after corruption injection at sequence 3."
  - "Sequence number of first corrupted event (must equal break_at)."
```

**Authority Basis:**
- D2 SC-007: "WHEN verify_chain(0, 5) is called THEN returns {valid: true, break_at: null}."
- D2 SC-008: "WHEN verify_chain() is called with no arguments THEN returns {valid: false, break_at: 3}."
- D4 IN-005 postcondition 3: "If all checks pass: returns ChainVerificationResult{valid: true, break_at: null}."
- D4 IN-005 postcondition 4: "If any check fails: returns ChainVerificationResult{valid: false, break_at: N} where N is the lowest sequence number with a hash mismatch or chain linkage failure."
- D4 IN-005 postcondition 5: "Verification stops at the first detected failure (break_at is returned immediately; subsequent events are not verified)."
- D4 IN-005 postcondition 1: "Walks all events from start to end inclusive, recomputing SHA-256 of each event's canonical JSON (hash field excluded per SIDE-002) and comparing to the stored hash field."
- D4 IN-005 postcondition 2: "Also verifies chain linkage: each event's previous_hash must equal the hash field of the event at sequence-1."

---

### HS-006 — immudb unreachable on append raises LedgerConnectionError and leaves state unchanged

```yaml
scenario_id: "HS-006"
title: "immudb unreachable on append raises LedgerConnectionError and leaves state unchanged"
priority: P1
authority:
  d2_scenarios: [SC-010]
  d4_contracts: [IN-001, IN-006, ERR-001, SIDE-001]
category: failure-injection
setup:
  description: >
    The Ledger contains 5 events (sequences 0 through 4). Tip is at sequence 4.
    immudb is then made unreachable (connection refused or timeout).
  preconditions:
    - Five events appended successfully (sequences 0 through 4).
    - get_tip() returns sequence_number=4.
    - immudb is unreachable for the next operation (simulated via MockProvider or
      network disruption in the test environment).
action:
  description: >
    A caller attempts to append a valid event while immudb is unreachable.
  steps:
    - Attempt to append a valid event (any valid event_type with all required fields).
    - Capture the raised error type.
    - Query get_tip() after the failed append attempt.
    - Attempt to read the event at sequence 5.
expected_outcome:
  description: >
    The append raises LedgerConnectionError. No event is written. The tip is unchanged.
  assertions:
    - subject: "error raised by the append attempt"
      condition: "is LedgerConnectionError"
      observable: "A LedgerConnectionError is raised; no sequence_number is returned."
    - subject: "get_tip() after the failed append"
      condition: "returns sequence_number=4 (unchanged from before the failed attempt)"
      observable: "Tip sequence_number is still 4; tip hash is unchanged."
    - subject: "read(5) after the failed append"
      condition: "raises LedgerSequenceError (sequence 5 does not exist)"
      observable: "No event exists at sequence 5; read(5) raises LedgerSequenceError."
    - subject: "Ledger chain integrity after the failure"
      condition: "chain is intact through sequence 4"
      observable: "verify_chain(0, 4) returns {valid: true, break_at: null} once immudb is reachable again."
  negative_assertions:
    - "The append does not return a sequence_number when immudb is unreachable."
    - "LedgerConnectionError is not silently swallowed or converted to a success."
    - "get_tip().sequence_number does not advance to 5 after a failed append."
    - "The error raised is not LedgerSerializationError."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "Type of error raised by the append attempt."
  - "get_tip() return value after the failed append."
  - "Outcome of read(5) after the failed attempt."
```

**Authority Basis:**
- D2 SC-010: "GIVEN immudb is unreachable WHEN append() is called THEN raises LedgerConnectionError AND the Ledger state is unchanged (no partial write, tip unchanged, chain intact) AND the caller receives the error immediately after one reconnect attempt."
- D4 IN-001 postcondition 8: "Atomicity on failure: if LedgerConnectionError or LedgerSerializationError is raised, the Ledger state is unchanged — tip is unchanged, no new event exists, chain is intact."
- D4 ERR-001: "Condition: immudb unreachable; gRPC connection refused; gRPC timeout; retry (one reconnect + one retry) exhausted."
- D4 SIDE-001 failure behavior: "If the immudb gRPC call fails, the Ledger closes the connection, waits 1 second, reconnects once, and retries the operation once. If the retry fails, LedgerConnectionError is raised. The Ledger state is unchanged (no partial write)."
- D4 IN-002 postcondition 2: "If sequence_number > tip.sequence_number: raises LedgerSequenceError."

---

### HS-007 — Concurrent append raises LedgerSequenceError and creates no fork

```yaml
scenario_id: "HS-007"
title: "Concurrent append raises LedgerSequenceError and creates no fork"
priority: P1
authority:
  d2_scenarios: [SC-011]
  d4_contracts: [IN-001, IN-006, ERR-003]
category: failure-injection
setup:
  description: >
    The Ledger is in a known state. Two append operations are initiated simultaneously
    (concurrently) from the same process using threads or equivalent concurrency.
  preconditions:
    - Ledger has a known tip at sequence N.
    - Two concurrent append calls are prepared but not yet dispatched.
action:
  description: >
    Two append() calls are initiated at the same time (concurrent). Results from both
    are captured.
  steps:
    - Initiate two concurrent append calls, each with a distinct valid event.
    - Record the result of each call (sequence_number or raised error).
    - Query get_tip() after both calls complete.
    - Attempt to read the event at sequence N+1 and N+2.
expected_outcome:
  description: >
    Exactly one append succeeds. The other raises LedgerSequenceError.
    The tip advances by exactly 1. No fork or duplicate exists.
  assertions:
    - subject: "outcomes of the two concurrent append calls"
      condition: "exactly one returns a sequence_number and exactly one raises LedgerSequenceError"
      observable: "One call succeeds; one raises LedgerSequenceError."
    - subject: "get_tip().sequence_number after both calls complete"
      condition: "equals N+1 (prior tip + 1)"
      observable: "Tip advanced by exactly 1, not by 2."
    - subject: "event at sequence N+1"
      condition: "exists and is the event from the one successful append"
      observable: "read(N+1) returns a complete event without error."
    - subject: "event at sequence N+2"
      condition: "does not exist — raises LedgerSequenceError"
      observable: "read(N+2) raises LedgerSequenceError."
    - subject: "chain integrity after concurrent attempt"
      condition: "chain is intact; no fork at sequence N+1"
      observable: >
        verify_chain(0, N+1) returns {valid: true, break_at: null}. There is
        exactly one event at sequence N+1, not two competing events.
  negative_assertions:
    - "Both concurrent appends do not both return sequence numbers."
    - "Tip does not advance by 2."
    - "Two different events do not both claim sequence N+1."
    - "LedgerSequenceError is not raised for the successful append."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "Result of each concurrent append call (sequence_number or error type)."
  - "get_tip() return value after both calls complete."
  - "Outcome of read(N+1) and read(N+2)."
```

**Authority Basis:**
- D2 SC-011: "WHEN two append() calls arrive concurrently THEN exactly one append succeeds AND the other receives LedgerSequenceError AND the Ledger state contains exactly one new event (no fork, no duplicate sequence number, chain intact)."
- D4 IN-001 constraints: "Callers MUST NOT call append() concurrently. Single-writer architecture. Concurrent calls result in LedgerSequenceError (see ERR-003)."
- D4 IN-001 postcondition 6: "No fork: exactly one event exists at the returned sequence_number. Calling read(returned_sequence_number) always returns this same event."
- D4 IN-001 postcondition 5: "Monotonicity: returned sequence_number = (previous tip.sequence_number + 1). No gaps, no skips."
- D4 ERR-003: "Condition: (a) Concurrent append() call detected (design violation — single-writer architecture guarantees this should be impossible)."

---

### HS-008 — Cold-storage offline verification produces identical results to online verification

```yaml
scenario_id: "HS-008"
title: "Cold-storage offline verification produces identical results to online verification"
priority: P0
authority:
  d2_scenarios: [SC-009]
  d4_contracts: [IN-005, OUT-005]
category: lifecycle
setup:
  description: >
    The Ledger contains events 0 through N, all appended cleanly. Online verification
    is run first to establish the baseline result. Then the kernel process is stopped.
  preconditions:
    - Ledger has events 0 through N (at least 5 events).
    - Online verify_chain() has been run and its result recorded.
    - The kernel process is then stopped; no DoPeJarMo runtime is running.
    - The immudb service remains accessible on its port.
action:
  description: >
    verify_chain() is invoked from a separate process that connects directly to
    immudb without the kernel running. The result is compared to the online result.
  steps:
    - Record the result of online verify_chain() (baseline).
    - Stop the kernel process.
    - Invoke verify_chain() from a process that accesses immudb directly
      (no kernel dependency). Record the result.
    - Compare the two results.
expected_outcome:
  description: >
    The offline verification result is identical to the online result: same valid
    value, same break_at value (null for an intact chain).
  assertions:
    - subject: "ChainVerificationResult from offline verify_chain() vs online result"
      condition: "both valid and break_at fields are identical between the two calls"
      observable: >
        offline result.valid equals online result.valid;
        offline result.break_at equals online result.break_at.
    - subject: "offline verify_chain() result on intact chain"
      condition: "returns ChainVerificationResult{valid: true, break_at: null}"
      observable: "Offline verification confirms the chain is intact."
    - subject: "no kernel runtime required"
      condition: "the offline verification call completes without starting or contacting the kernel"
      observable: "Verification completes with kernel stopped; no kernel startup error occurs."
  negative_assertions:
    - "Offline verification does not return a different break_at than online verification."
    - "Offline verification does not raise LedgerConnectionError when immudb is reachable."
    - "Offline verification does not require the kernel process to be running."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "ChainVerificationResult from online verify_chain() (baseline)."
  - "ChainVerificationResult from offline verify_chain() (kernel stopped)."
  - "Evidence that kernel was stopped during the offline run."
```

**Authority Basis:**
- D2 SC-009: "WHEN verify_chain() is called from a CLI tool connecting directly to immudb (kernel process stopped) THEN returns the same {valid, break_at} result as the online verification."
- D4 IN-005 postcondition 7: "Produces identical results whether called from the kernel process or from the cold-storage CLI tool connecting directly to immudb. No kernel runtime required."

---

### HS-009 — Non-serializable payload raises LedgerSerializationError before any write

```yaml
scenario_id: "HS-009"
title: "Non-serializable payload raises LedgerSerializationError before any write"
priority: P1
authority:
  d2_scenarios: [SC-001, SC-002]
  d4_contracts: [IN-001, IN-006, ERR-004, SIDE-002]
category: failure-injection
setup:
  description: >
    The Ledger contains 3 events (sequences 0 through 2). Tip is at sequence 2.
    A payload is prepared that cannot be serialized to canonical JSON (e.g.,
    contains a value type that json.dumps cannot handle).
  preconditions:
    - Three events have been appended successfully (sequences 0 through 2).
    - get_tip() returns sequence_number=2.
action:
  description: >
    A caller attempts to append an event with a non-JSON-serializable payload value.
  steps:
    - Attempt to append a node_creation event where the payload contains a field
      with a non-JSON-serializable value (a value type that json.dumps raises on).
    - Capture the raised error type.
    - Query get_tip() after the failed attempt.
    - Attempt to read the event at sequence 3.
expected_outcome:
  description: >
    A LedgerSerializationError is raised before any write to immudb.
    The Ledger state is unchanged; the tip remains at sequence 2.
  assertions:
    - subject: "error raised by the append attempt"
      condition: "is LedgerSerializationError"
      observable: "LedgerSerializationError is raised; no sequence_number is returned."
    - subject: "get_tip() after the failed attempt"
      condition: "returns sequence_number=2 (unchanged)"
      observable: "Tip sequence_number is still 2; tip hash is unchanged."
    - subject: "read(3) after the failed attempt"
      condition: "raises LedgerSequenceError (sequence 3 does not exist)"
      observable: "No event was written at sequence 3."
    - subject: "timing of the error"
      condition: "LedgerSerializationError is raised before any write to immudb"
      observable: >
        The error occurs during hash computation (serialization phase); immudb is
        not contacted for this event.
  negative_assertions:
    - "The append does not return a sequence_number for a non-serializable payload."
    - "LedgerConnectionError is not raised for a serialization failure."
    - "Tip does not advance to 3 after a LedgerSerializationError."
    - "A partial or corrupt event is not written to immudb."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "Type of error raised by the append attempt."
  - "get_tip() return value after the failed attempt."
  - "Outcome of read(3) after the failed attempt."
```

**Authority Basis:**
- D4 ERR-004: "Condition: The event payload (or any other event field) cannot be serialized to canonical JSON using SIDE-002 rules (e.g., contains a non-serializable Python object, or json.dumps raises)."
- D4 SIDE-002 failure behavior: "If json.dumps raises (e.g., non-serializable object in payload), raises LedgerSerializationError before any write to immudb. The Ledger state is unchanged."
- D4 IN-001 postcondition 8: "Atomicity on failure: if LedgerConnectionError or LedgerSerializationError is raised, the Ledger state is unchanged — tip is unchanged, no new event exists, chain is intact."
- D4 ERR-004: "Caller Action: Surface to Write Path (FMWK-002). The event is not appended. The Ledger state is unchanged."

---

### HS-010 — Out-of-range and negative sequence reads raise LedgerSequenceError

```yaml
scenario_id: "HS-010"
title: "Out-of-range and negative sequence reads raise LedgerSequenceError"
priority: P1
authority:
  d2_scenarios: [SC-003, SC-004, SC-005]
  d4_contracts: [IN-002, IN-003, IN-004, ERR-003]
category: edge-case
setup:
  description: >
    The Ledger contains 5 events (sequences 0 through 4). Tip is at sequence 4.
  preconditions:
    - Five events appended successfully (sequences 0 through 4).
    - get_tip() returns sequence_number=4.
action:
  description: >
    Three boundary-violation reads are attempted: single read beyond tip, single read
    at negative sequence, and range read where end exceeds tip.
  steps:
    - Attempt read(999) where tip is at 4. Capture the error.
    - Attempt read(-1). Capture the error.
    - Attempt read_range(3, 999) where tip is at 4. Capture the error.
    - Attempt read_since(999) where tip is at 4. Capture the error.
expected_outcome:
  description: >
    All four boundary-violation reads raise LedgerSequenceError.
    No partial results are returned.
  assertions:
    - subject: "read(999) when tip is at 4"
      condition: "raises LedgerSequenceError"
      observable: "LedgerSequenceError is raised; no event is returned."
    - subject: "read(-1)"
      condition: "raises LedgerSequenceError"
      observable: "LedgerSequenceError is raised; no event is returned."
    - subject: "read_range(3, 999) when tip is at 4"
      condition: "raises LedgerSequenceError"
      observable: "LedgerSequenceError is raised; no partial list is returned."
    - subject: "read_since(999) when tip is at 4"
      condition: "raises LedgerSequenceError"
      observable: "LedgerSequenceError is raised; no list is returned."
  negative_assertions:
    - "read(999) does not return None or an empty result instead of raising."
    - "read(-1) does not return an event."
    - "read_range(3, 999) does not return a partial list ending at the current tip."
    - "No LedgerConnectionError is raised for out-of-range inputs."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "Error type raised by read(999)."
  - "Error type raised by read(-1)."
  - "Error type raised by read_range(3, 999)."
  - "Error type raised by read_since(999)."
```

**Authority Basis:**
- D4 IN-002 postcondition 2: "If sequence_number > tip.sequence_number: raises LedgerSequenceError (ERR-003)."
- D4 IN-002 postcondition 3: "If sequence_number < 0: raises LedgerSequenceError (ERR-003)."
- D4 IN-003 postcondition 2: "If end > tip.sequence_number: raises LedgerSequenceError (ERR-003)."
- D4 IN-004 postcondition 3: "If sequence_number > tip.sequence_number: raises LedgerSequenceError (ERR-003)."
- D4 ERR-003: "Condition: (b) read()/read_range()/read_since() called with a sequence number beyond tip.sequence_number."

---

### HS-011 — Multi-type append sequence with bulk read and end-to-end chain verification (integration)

```yaml
scenario_id: "HS-011"
title: "Multi-type append sequence with bulk read and end-to-end chain verification"
priority: P0
authority:
  d2_scenarios: [SC-001, SC-002, SC-004, SC-007]
  d4_contracts: [IN-001, IN-003, IN-005, IN-006, OUT-001, OUT-003, OUT-005, SIDE-001, SIDE-002]
category: lifecycle
setup:
  description: >
    The Ledger is empty. Five events of distinct types will be appended in sequence
    to exercise the full write-read-verify path.
  preconditions:
    - Ledger is empty; get_tip() returns sequence_number=-1.
action:
  description: >
    Five events of different event types are appended sequentially. Then a bulk range
    read retrieves all five. Then end-to-end chain verification is run.
  steps:
    - Append a node_creation event. Record returned sequence_number (expected: 0).
    - Append a signal_delta event. Record returned sequence_number (expected: 1).
    - Append a session_start event. Record returned sequence_number (expected: 2).
    - Append a session_end event. Record returned sequence_number (expected: 3).
    - Append a snapshot_created event. Record returned sequence_number (expected: 4).
    - Call read_range(0, 4). Record the returned list.
    - Call verify_chain(0, 4). Record the result.
    - Query get_tip().
expected_outcome:
  description: >
    All five appends succeed with monotonically increasing sequence numbers 0-4.
    read_range returns all five events in order. verify_chain confirms the chain is
    intact. Tip reflects the final state.
  assertions:
    - subject: "sequence numbers returned by the five sequential appends"
      condition: "are exactly 0, 1, 2, 3, 4 in that order"
      observable: "Each append returns the next integer; no gaps."
    - subject: "list returned by read_range(0, 4)"
      condition: >
        contains exactly 5 LedgerEvents at sequences 0, 1, 2, 3, 4 in ascending order,
        with all fields intact, and each event_type matching what was appended
      observable: >
        List has 5 elements; sequences are 0,1,2,3,4; event_type of each matches
        the type submitted at that position.
    - subject: "ChainVerificationResult from verify_chain(0, 4)"
      condition: "valid=true, break_at=null"
      observable: "All hash and linkage checks pass across all five events."
    - subject: "each event's hash in the chain"
      condition: >
        event at sequence N has previous_hash equal to the hash of event at sequence N-1
        (or 64-zero hash for N=0)
      observable: >
        Iterating through the five read events, each previous_hash links correctly
        to the preceding event's hash.
    - subject: "get_tip() after all five appends"
      condition: "returns sequence_number=4 and hash matching the hash of event 4"
      observable: "Tip is at 4; tip hash matches read(4).hash."
  negative_assertions:
    - "Any append does not skip a sequence number."
    - "read_range(0, 4) does not omit any of the five events."
    - "verify_chain(0, 4) does not return valid=false for a clean append sequence."
    - "Different event_types do not cause chain breaks or hash computation failures."
pass_criteria:
  runs_required: 3
  pass_threshold: "2 of 3"
evidence_to_collect:
  - "Return values from all five append operations."
  - "Sequences and event_types from read_range(0, 4)."
  - "ChainVerificationResult from verify_chain(0, 4)."
  - "get_tip() return value after all five appends."
  - "previous_hash of event at sequence 1 vs hash of event at sequence 0 (spot check)."
```

**Authority Basis:**
- D2 SC-001: Genesis append returns sequence=0 with previous_hash=64zeros.
- D2 SC-002: "WHEN append() is called with a valid event THEN the Ledger assigns sequence=N AND sets previous_hash=hash_of_event_at_sequence_N-1."
- D2 SC-004: "WHEN read_range(3, 7) is called THEN returns exactly 5 events, at sequences 3,4,5,6,7 in ascending order." (Pattern applies to read_range(0,4).)
- D2 SC-007: "WHEN verify_chain(0, 5) is called THEN returns {valid: true, break_at: null}." (Pattern applies to verify_chain(0,4).)
- D4 IN-001 postcondition 5: "Monotonicity: returned sequence_number = (previous tip.sequence_number + 1). No gaps, no skips."
- D4 IN-003 postcondition 1: "returns a list of (end - start + 1) LedgerEvents at sequences start, start+1, ..., end inclusive, in ascending order."
- D4 IN-005 postcondition 3: "If all checks pass: returns ChainVerificationResult{valid: true, break_at: null}."
- D4 SIDE-002: canonical JSON serialization contract governs hash computation across all event types.

---

## Coverage Matrix

All D2 P0 and P1 scenarios have holdout coverage. Zero gaps.

| D2 Scenario | Priority | Holdout Coverage | Notes |
|-------------|----------|-----------------|-------|
| SC-001 — Append first event (genesis) | P0 | HS-001, HS-011 | Genesis path covered in isolation and in multi-type integration |
| SC-002 — Append subsequent event (chain continuation) | P0 | HS-002, HS-011 | Chain linkage covered in isolation (5 events) and integration |
| SC-003 — Read event by sequence number | P0 | HS-003, HS-010 | Happy path and out-of-range error path |
| SC-004 — Read range of events | P1 | HS-003, HS-011 | read_range happy path + integration read_range(0,4) |
| SC-005 — Read all events since a sequence number | P1 | HS-003 | read_since happy path including empty-result case |
| SC-006 — Get tip (latest sequence and hash) | P0 | HS-004 | Empty-ledger sentinel and per-append tip advance |
| SC-007 — Verify intact hash chain | P0 | HS-005, HS-011 | Isolated verification + integration end-to-end verify |
| SC-008 — Detect corruption at specific sequence | P0 | HS-005 | Corruption injected at sequence 3; break_at verified |
| SC-009 — Offline cold-storage verification | P0 | HS-008 | Kernel stopped; direct immudb connection; result parity |
| SC-010 — immudb unreachable on append | P1 | HS-006 | LedgerConnectionError; state unchanged; tip unaffected |
| SC-011 — Concurrent append attempt | P1 | HS-007 | One success, one LedgerSequenceError; no fork |

**Additional coverage (not explicitly in D2 but required by D4 error contracts):**

| D4 Contract | Priority | Holdout Coverage | Notes |
|-------------|----------|-----------------|-------|
| ERR-004 — LedgerSerializationError | — | HS-009 | Non-serializable payload; state unchanged |
| IN-002/IN-003/IN-004 out-of-range | — | HS-010 | LedgerSequenceError on negative and beyond-tip reads |

## Evaluator Contract

Evaluator writes, per scenario per attempt:
- `eval_tests/attemptN/HS-NNN.py`
- `eval_tests/attemptN/HS-NNN.mapping.md`
- `eval_tests/attemptN/HS-NNN.run{1,2,3}.json`

Mapping file MUST cite D9 fields used + staged code paths used for API discovery.
Evaluator may use staged code to learn HOW to call the implementation; never WHAT behavior to expect.

## Run Protocol

Order: P0 first, then P1, then P2.
Scenario pass: 2 of 3 runs.
Overall pass: all P0 pass, all P1 pass, overall >= 90%.
