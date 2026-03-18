---
title: "OPERATIONAL SPEC — How DoPeJarMo Runs"
status: OPERATIONAL AUTHORITY
authority_level: "operational authority — NORTH_STAR.md resolves ambiguity. BUILDER_SPEC.md takes precedence for cognitive concerns; this document takes precedence for operational concerns."
version: "3.0"
last_updated: "2026-02-25"
author: Ray Bruni
audience: "Builder agents working on Docker topology, deployment infrastructure, and operational reliability."
resolves_ambiguity_for: []
depends_on:
  - NORTH_STAR.md
  - BUILDER_SPEC.md
---

# OPERATIONAL SPEC — How DoPeJarMo Runs

**Status**: OPERATIONAL AUTHORITY — this document defines what "running" means, how the operator interacts, and how the system behaves under failure, recovery, resource pressure, change, and network exposure. It does not modify cognitive architecture. If ambiguity exists between this document and BUILDER_SPEC, the cognitive architecture in BUILDER_SPEC takes precedence for cognitive concerns; this document takes precedence for operational concerns. NORTH_STAR.md resolves all ambiguity.

**Audience**: Builder agents working on Docker topology, deployment infrastructure, and operational reliability. Humans and agents who need to understand how the system operates as running software. Read BUILDER_SPEC.md first — this document assumes you understand the nine primitives.

**Relationship to other documents:**
- NORTH_STAR.md — design authority (why). Resolves all ambiguity.
- BUILDER_SPEC.md — build authority (what to build)
- This document — operational authority (how it runs)
- FRAMEWORK_REGISTRY.md — framework segregation, build order, coding boundaries

---

## Why This Document Exists

NORTH_STAR defines seven foundational design decisions (Q1–Q7) that scope the cognitive system. BUILDER_SPEC defines the nine primitives and how they connect. Neither document answers the operational questions: what does "running" mean? What happens when power is lost? How does the operator intervene? What's the failure posture?

This document answers eight foundational operational questions. These answers determine the boot sequence, the observability model, the crash consistency guarantee, the degradation model, the operator interface, the resource management strategy, the upgrade path, and the security perimeter. Everything the operational substrate needs to be specified.

---

## The Eight Operational Questions

### Q1 — What does "running" mean?

"Running" means DoPeJarMo is up and accepting operator sessions over WebSocket. DoPeJarMo is an interactive agent — the operator connects via WebSocket to the kernel's `/operator` path, authenticates through Zitadel (OIDC), and works through DoPeJarMo conversationally. The boot prerequisites: Ledger accessible via immudb (gRPC over Docker network), Graph rebuilt from snapshot + replay, Write Path operational, HO1 connected to at least one LLM (Ollama at minimum), Zitadel accepting authentication requests, and the framework chain validated — GENESIS and KERNEL verified, every installed framework's governance rules intact, spec packs resolved, pack manifests matched, file hashes confirmed, ownership clean. That last step isn't a filesystem scan — it's the gate hierarchy running at every layer of the Framework Hierarchy against the Ledger. If any framework's chain is broken, the system knows exactly which framework, which pack, which file, and can report it to the operator through DoPeJarMo. Once DoPeJarMo is accepting sessions, the operator installs DoPeJar's frameworks (Memory, Intent, Conversation) through him. DoPeJar comes to life inside DoPeJarMo. She doesn't boot separately — she exists because her frameworks are installed and running inside DoPeJarMo. Users connect via WebSocket to the kernel's `/user` path.

### Q2 — What does the operator see?

The operator sees DoPeJarMo. Not a dashboard, not a log stream — DoPeJarMo himself. The operator logs in and interacts with him as an agent. DoPeJarMo shows the operator what the system really is: which frameworks are installed and whether their governance rules, scope boundaries, and quality measures are intact. Which packages passed gates and which failed. Whether the framework chain from any file back through pack, spec pack, to framework resolves cleanly against the Ledger. Primitive health (Ledger reachable, Graph built, Write Path responsive, HO1 connected) is the baseline — but the meaningful view is framework state. A framework declares its scope, its authority rules, its quality criteria. The operator sees whether those declarations match reality. When DoPeJar's frameworks are broken, the operator sees which framework, what broke, and what the governance rules say should be true.

### Q3 — What survives a power cut?

The Ledger in immudb (persisted to the ledger_data volume) and the last Graph snapshot (persisted to the snapshots volume). The Write Path is synchronous: append to immudb over gRPC (sub-millisecond on Docker bridge network), fold into local RAM, acknowledge. If acknowledged — in immudb on disk. If not — lost. Clean cut. Recovery: load last snapshot, replay post-snapshot Ledger events from immudb, rebuild Graph. Then validate the framework chain — every installed framework's governance rules, spec pack declarations, pack manifests, and file hashes against the Ledger. The core operational invariant guarantees this is possible with no cognitive runtime — CLI tools connect directly to immudb, bypassing the kernel entirely. If the framework chain validates, DoPeJarMo can accept operator sessions. If something is inconsistent, the operator knows exactly which framework and which layer of the hierarchy broke — and can use Package Lifecycle tools to repair, rollback, or reinstall. In-flight work orders that weren't acknowledged don't exist in the Ledger, so HO2 won't find their results and knows they were lost.

### Q4 — What's the failure posture?

NORTH_STAR Principle 4: "Block rather than guess. Determinism over cleverness." Ollama down — HO1 blocks local dispatches. External API down — HO1 blocks external dispatches. Graph corrupt — rebuild from Ledger. Ledger hash chain breaks — catastrophic, system stops. immudb down — Write Path blocks, system hard-stops (cannot write means nothing can happen). Zitadel down — no new sessions can authenticate, existing sessions continue on cached permissions until session boundary. A framework failing doesn't take down the OS — frameworks are scoped (single responsibility, explicit interfaces, own your data), so a broken framework is contained within its scope and authority boundaries. The operator diagnoses through DoPeJarMo. If DoPeJarMo himself can't accept sessions, the operator is not locked out — the Package Lifecycle tools work from the command line because they validate the framework chain, not the agent layer. CLI tools connect directly to immudb (bypassing the kernel) to validate framework governance rules, pack manifests, file hashes, and ownership records against the Ledger — no Graph, no HO1, no HO2, no LLM required. The only truly unrecoverable case is Ledger corruption, and even there the hash chain tells you where it broke.

### Q5 — How does the operator intervene?

Through DoPeJarMo. He IS the intervention interface. The operator doesn't manage files or containers — they manage frameworks and packages. Install a framework. Upgrade a framework (new version = new package through gates). Rollback a framework. Inspect a framework's governance rules, scope boundaries, quality measures. See which packages passed gates and which failed. Validate the framework chain against the Ledger. All through interactive sessions with DoPeJarMo. DoPeJarMo has his own availability requirement separate from DoPeJar's. DoPeJar down but DoPeJarMo up = operator diagnoses and fixes at the framework level. DoPeJarMo down = operator falls back to command-line package tools, which validate the same framework chain with no agent layer required.

### Q6 — What's the resource contract?

Four resource dimensions. Disk: Ledger grows append-only. RAM: Graph scales with active state. Tokens: every work order has a bounded budget, every LLM call logs cost. CPU: Write Path folds, HO2 scoring. Docker Compose gives container-level resource limits (NORTH_STAR Q5). But resource consumption is framework-scoped — each framework declares its dependencies, owns its data, and its work orders carry bounded budgets. When a limit is hit, Q4's posture applies: detect, report through DoPeJarMo at the framework level (which framework is consuming what), block operations that would exceed the limit. Ledger filling disk is addressed by the Storage Management framework (Layer 1, required) — trims oldest + least used artifacts using methylation values, at write rate, under disk pressure. Trimming is a Ledger event — logged, governed, auditable. Truth can't be pruned arbitrarily, but the cognitive system already knows what's cold. The operator sees resource state through DoPeJarMo and intervenes at the framework level.

### Q7 — How does the system change over time?

The Ledger never changes. All change is framework-scoped. The operator installs, upgrades, and removes frameworks by interacting with DoPeJarMo through the Package Lifecycle. A framework upgrade is a new package — new governance rules, new scope declarations, new quality measures, new spec packs, new packs, new files — all carried through gates that validate at every layer of the hierarchy. Rollback is governed: the previous package's framework chain is still in the Ledger. Retroactive Healing lets you re-fold the entire Ledger with improved logic: delete Graph, replay from Genesis. The nine primitives don't change — they're the OS. Framework upgrades go through Package Lifecycle (normal, governed, operator-driven through DoPeJarMo). The constraint: upgrades must not break replay. The core operational invariant holds across all changes — every artifact still traces back through the provenance chain.

### Q8 — What's the network posture?

Four services on a local-only Docker Compose network (see Docker Topology below). The kernel exposes WebSocket on :8080 — `/operator` for DoPeJarMo sessions, `/user` for DoPeJar sessions. immudb exposes gRPC on :3322 (kernel and CLI tools connect here). Ollama exposes HTTP on :11434 (HO1 internal calls only). Zitadel exposes OIDC on :8080 (its default — operator/agent authentication and authorization). No public ports. Outbound connections are LLM API calls only. User data stays local (trust boundary 4). User provides API keys.

Identity and authorization are handled by Zitadel — architecturally separate from the cognitive kernel (NORTH_STAR Q2). Zitadel runs locally as a Docker service. Authentication: OIDC flow on WebSocket connect — Zitadel issues JWT, kernel validates. Authorization: kernel loads agent permission set (namespaces, scoped capabilities) from Zitadel once at session start, caches for the session. HO2 checks permissions against cached session permissions during work order dispatch — no external call per check. Permission changes take effect at next session. This keeps authorization checks fast and deterministic during cognitive operations while maintaining architectural separation.

DoPeJarMo accepts operator sessions locally. DoPeJar accepts user sessions locally. Nothing listens on public ports unless the operator explicitly exposes it through DoPeJarMo. Frameworks declare their dependencies and external needs explicitly — a framework that requires external API access declares it in its governance rules, and that declaration goes through gates. The perimeter: local-only internal network, outbound LLM calls as the sole external surface, framework-declared external dependencies governed through the package chain. Zitadel supports OIDC federation — when the system needs to connect to Azure AD, Okta, or other cloud IAM providers, Zitadel federates upstream. No provider swap required.

---

## Boot Sequence

The boot sequence implements Q1. See BUILDER_SPEC Boot Order for the full install sequence and FRAMEWORK_REGISTRY for dependency details.

```
1. GENESIS                    (hand-verified, creates governed filesystem + Ledger + hierarchy)
2. KERNEL                     (hand-verified, creates nine primitives + Write Path + Package Lifecycle tools incl. CLI)
   ── core operational invariant now holds ──
3. DoPeJarMo Agent Interface  (first governed install, via CLI package tools — DoPeJarMo can now accept operator sessions)
4. Storage Management         (keeps Ledger writable — installed through DoPeJarMo)
5. Meta-Learning Agent        (signal regulation, cognitive failure mode protection)
6. Routing                    (LLM provider dispatch policy)
   ── DoPeJarMo fully operational, operator can work ──
7. Memory                     (learning artifacts, Attention configuration)
8. Intent                     (lifecycle management, proposal/authority)
9. Conversation               (DoPeJar's personality, user-facing behavior)
   ── DoPeJar alive, users can interact ──
```

**Startup from crash or power loss:** Docker restart → Ledger on disk → load last Graph snapshot → replay post-snapshot Ledger events → rebuild Graph → validate framework chain against Ledger → DoPeJarMo Agent Interface available → operator can log in.

**Shutdown:** Stop accepting WebSocket connections → drain in-flight work orders → snapshot Graph → append SESSION_END event to Ledger via immudb → close connections.

---

## Docker Topology

Four services, six volumes. This is the decided topology — no alternatives, no optional services.

### Services

**kernel** — The DoPeJarMo core process.
- Contains: nine primitives, Write Path, frameworks (Layer 1 + Layer 2 installed at runtime)
- WebSocket server on :8080 — `/operator` for DoPeJarMo sessions, `/user` for DoPeJar sessions
- gRPC client to immudb (Ledger reads/writes)
- HTTP client to Ollama (HO1 LLM calls)
- OIDC client to Zitadel (JWT validation on session connect, permission loading at session start)
- Outbound HTTPS to external LLM APIs (user-provided keys)

**ledger** (immudb) — Append-only hash-chained truth store.
- gRPC on :3322, metrics on :9497
- The sole source of truth for all state
- The Write Path appends events here synchronously over Docker bridge network (sub-millisecond latency)
- CLI fallback tools connect directly to immudb, bypassing the kernel, for framework chain validation
- Persists to ledger_data volume

**ollama** — Local LLM for HO1 internal calls.
- HTTP on :11434
- Used for Prompt Pack Inspection (constrained, no context, local) and other HO1 work orders routed locally by the Routing framework
- Persists downloaded models to ollama_models volume

**zitadel** — Identity and authorization.
- OIDC + authorization API on :8080 (Zitadel default)
- Operator authenticates via OIDC flow → JWT issued → kernel validates
- Agent permission sets (namespaces, scoped capabilities) loaded by kernel at session start, cached per session
- Supports OIDC federation upstream to Azure AD, Okta, Auth0, Google Workspace for future cloud/SaaS integration
- Persists to zitadel_data volume

### Volumes

| Volume | Purpose | Accessed By |
|---|---|---|
| governed_fs | Frameworks, spec packs, packs, files — the governed filesystem | kernel |
| staging | Ungoverned build workbench — where builders work before package install | kernel |
| snapshots | Serialized Graph state at session boundaries | kernel |
| ledger_data | immudb data (append-only event log) | ledger, CLI tools (direct read) |
| ollama_models | Persists downloaded LLM models across restarts | ollama |
| zitadel_data | Zitadel identity/authorization state | zitadel |

### Protocols

| Connection | Protocol | Why |
|---|---|---|
| Operator/User → Kernel | WebSocket (:8080) | Persistent bidirectional session — DoPeJarMo is conversational. Connection drop = session boundary. |
| Kernel → immudb | gRPC (:3322) | immudb's native protocol. Sub-millisecond on Docker bridge. Synchronous write guarantee preserved. |
| Kernel → Ollama | HTTP (:11434) | Ollama's native REST API. HO1 dispatches work orders here. |
| Kernel → Zitadel | OIDC/HTTP (:8080) | JWT validation on connect. Permission load at session start. No per-operation calls. |
| Kernel → External APIs | HTTPS (outbound) | DoPeJar conversation LLM calls. User-provided API keys. Sole external surface. |
| CLI tools → immudb | gRPC (:3322) | Direct Ledger access for framework chain validation when kernel is down. |

### What Does NOT Need a Separate Service

| Concern | Where It Lives | Why Not Separate |
|---|---|---|
| Graph (HO3) | RAM inside kernel | Materialized view, not a database. Transient — destroy and rebuild from Ledger. |
| Write Path | Code in kernel | Synchronous I/O path, not a message queue. Appends to immudb, folds into local Graph. |
| Storage Management | Framework on kernel | Trims Ledger at write rate under disk pressure. Framework logic, not a daemon. |
| Monitoring | DoPeJarMo himself | The operator talks to the agent, not a dashboard. (Implementation deferred.) |
| CLI fallback | Binary in kernel image | Package Lifecycle tools. Connects directly to immudb — no kernel needed. |
| Session management | Code in kernel | HO2 detects session boundaries. WebSocket connection lifecycle is the session. |

---

## Failure Recovery Matrix

| Failure | Detection | Posture | Recovery |
|---|---|---|---|
| Ollama down | HO1 connection failure | Block local dispatches, continue external | Operator restarts Ollama container, HO1 reconnects |
| External API down | HO1 timeout/error | Block external dispatches, continue local | Operator checks API keys/connectivity through DoPeJarMo |
| immudb down | Write Path gRPC connection failure | System hard stop — cannot write means nothing can happen | Restart ledger container. Write Path reconnects. Existing sessions resume. |
| Zitadel down | OIDC endpoint unreachable | No new sessions can authenticate. Existing sessions continue on cached permissions until session boundary. | Restart zitadel container. New sessions can authenticate. |
| Graph corrupt | Hash mismatch on read | Block all queries | Rebuild from Ledger via immudb (delete Graph, replay from Genesis or last snapshot) |
| Framework chain broken | Gate validation failure at any layer | Block operations for that framework, continue others | Operator uses DoPeJarMo (or CLI tools connecting directly to immudb) to rollback/reinstall |
| DoPeJar frameworks broken | Framework-level health check | DoPeJar unavailable to users, DoPeJarMo still up | Operator diagnoses and fixes through DoPeJarMo |
| DoPeJarMo Agent Interface down | Cannot accept operator sessions | Operator falls back to CLI package tools | CLI tools connect directly to immudb, validate framework chain, repair/reinstall Agent Interface |
| Disk full (Ledger) | Write Path cannot append to immudb | System hard stop — cannot write means nothing can happen | Storage Management framework trims oldest + least used under disk pressure. If Storage Management itself failed, operator uses CLI tools to diagnose |
| Ledger hash chain broken | Hash verification failure in immudb | Catastrophic — system stops | Hash chain identifies where corruption occurred. Manual investigation required |

---

## The Two Invariants (Operational Relevance)

**The Core Architectural Invariant** (from NORTH_STAR): LLM structures at write time. HO2 retrieves mechanically at read time. Never the reverse. Operational implication: the Write Path must be synchronous and acknowledged before the system proceeds.

**The Core Operational Invariant** (from NORTH_STAR): Nothing enters DoPeJarMo without a framework. Every artifact traces back through the provenance chain to a hash-verified, Ledger-recorded entry. Operational implication: the entire governed filesystem can be validated against the Ledger with no cognitive runtime — no Graph, no HO1, no HO2, no LLM. CLI tools connect directly to immudb (bypassing the kernel) to validate the framework chain. immudb must be running for CLI validation, but the kernel does not — immudb is infrastructure, not cognitive runtime. This is what makes command-line recovery possible and guarantees the operator is never locked out.

---

## Schemas Deferred

The following are required for implementation but are not decided here:

- Zitadel configuration details (roles, permission schema shape, namespace structure for agents)
- Operational log format and transport (separate from Ledger — infrastructure health, not cognitive state)
- Health endpoint schema (what fields, what thresholds trigger alerts)
- Resource limit defaults (disk quotas, RAM caps, token budgets per framework)
- Network policy implementation (Docker network configuration, TLS for outbound LLM calls)
- Secrets management (API key storage, rotation)
- Monitoring and alerting implementation (how DoPeJarMo surfaces resource and health state to the operator)
