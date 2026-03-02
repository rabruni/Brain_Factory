# Task: FMWK-001-ledger

## Framework
- ID: FMWK-001
- Name: ledger
- Layer: KERNEL

## What to Spec
The Ledger is the append-only, hash-chained event store. It is the sole source of truth for all DoPeJarMo state. Every mutation in the system is recorded as a Ledger event. The in-memory Graph (HO3) is derived entirely from Ledger replay — if the Graph is lost, it is rebuilt from the Ledger.

The Ledger uses immudb as its backing store (gRPC on port 3322). Events are hash-chained: each event includes the hash of the previous event, creating a tamper-evident chain.

## Owns
- Append-only event store
- Event schemas (the canonical shape of every event type)
- Hash chain integrity (each event hashes the previous)
- Event replay (ordered retrieval for Graph reconstruction)

## Dependencies
- FMWK-000 (FWK-0) only. FMWK-001 is the foundation. All other KERNEL frameworks depend on it.

## Constraints
- The Ledger NEVER deletes or modifies events. Append-only is constitutional.
- The Ledger does NOT execute business logic. It stores events. Period.
- Events must be self-describing (include their type, schema version, and provenance).
- The hash chain must be verifiable from cold storage with no runtime services.
- immudb is the backing store. The Ledger abstracts over immudb — callers never interact with immudb directly.
- All access goes through the platform_sdk. Never import immudb libraries directly.

---

## Source Material

Detailed specification material (event schemas, hash chain, immudb integration, serialization contract, etc.) is in `SOURCE_MATERIAL.md` in this directory. The spec agent reads it after this file.
