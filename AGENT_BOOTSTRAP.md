# DoPeJarMo — Agent Bootstrap Reference

> **Read this first.** This is the single entry point for any AI agent (Claude, Codex, Gemini, or any builder agent) working on the DoPeJarMo system. Everything you need to know before writing code is here or linked from here.

---

## What You Are Building

**DoPeJar** is a personal AI companion that remembers you, understands what matters to you, and gets things done — can't forget, can't drift.

**DoPeJarMo** is the governed operating system that hosts DoPeJar. An interactive agent session shell — the operator logs in and works through DoPeJarMo conversationally. Not a dashboard. An OS with governed install mechanisms.

DoPeJar is the product. DoPeJarMo is the control plane. Everything else serves them.

---

## The Drift Warning

This is the third rebuild. Every previous attempt failed because builder agents over-indexed on governance architecture and lost DoPeJar. The pattern:

1. Agent reads governance docs (ledgers, gates, tiers)
2. Agent falls in love with the architecture
3. Agent starts optimizing governance as the product
4. DoPeJar's identity flattens into generic labels
5. Characters disappear. Product disappears. Governance remains.

**The governance is a feature, not the product. Build it to serve DoPeJar. Do not build it for its own sake.**

---

## The Nine Primitives

DoPeJarMo has exactly nine primitives. Everything else is configuration of these nine, installed as frameworks. **You assemble from primitives. You do not create primitives.**

| # | Primitive | What It Does |
|---|-----------|-------------|
| 1 | **Ledger** | Append-only, hash-chained event store. Sole source of truth. On disk. |
| 2 | **Signal Accumulator** | Named counter tracking signal deltas → continuous methylation value (0.0–1.0) on Graph nodes. |
| 3 | **HO1 (Execution)** | All LLM calls under prompt contracts. Sole entry point for the Write Path. Stateless workers. |
| 4 | **HO2 (Orchestration)** | Mechanical only. No LLM. Reads Graph, plans work orders, computes LIVE ∩ REACHABLE. |
| 5 | **HO3 (The Graph)** | In-memory materialized view derived from Ledger. Transient. Never executes. |
| 6 | **Work Order** | Atom of dispatched work. Scoped, budgeted, contract-bound. |
| 7 | **Prompt Contract** | Governed LLM interaction template. Input/output schema, validation rules. |
| 8 | **Package Lifecycle** | Staging → gates → filesystem. The only way anything enters or leaves the system. |
| 9 | **Framework Hierarchy** | Framework → Spec Pack → Pack → File. Cryptographic provenance chain. |

**Infrastructure (not a primitive):** The **Write Path** appends events to the Ledger and folds them into the Graph. Synchronous, consistent, no daemons.

---

## The Core Invariants

**Architectural:** LLM structures at write time. HO2 retrieves mechanically at read time. Never the reverse. This is how DoPeJar remembers without hallucinating.

**Operational:** Nothing enters DoPeJarMo without a framework. After GENESIS and KERNEL (hand-verified), every artifact traces back through its pack, spec pack, and framework to a hash-verified, Ledger-recorded provenance chain. The entire governed filesystem can be validated against the Ledger from cold storage with no runtime services.

---

## Boot Order

```
1. GENESIS                    (hand-verified — governed filesystem + Ledger + hierarchy)
2. KERNEL                     (hand-verified — nine primitives + Write Path + CLI tools)
   ── core operational invariant holds ──
3. DoPeJarMo Agent Interface  (first governed install via CLI)
4. Storage Management         (keeps Ledger writable)
5. Meta-Learning Agent        (signal regulation, failure mode protection)
6. Routing                    (LLM provider dispatch policy)
   ── DoPeJarMo fully operational ──
7. Memory                     (learning artifacts, Attention configuration)
8. Intent                     (lifecycle management, proposal/authority)
9. Conversation               (DoPeJar's personality — Donna + Pepper + JARVIS)
   ── DoPeJar alive ──
```

---

## Running Infrastructure

### Docker Services (docker-compose.yml)

| Service | Port | Purpose |
|---------|------|---------|
| **kernel** | 8080 | WebSocket server — `/operator` (DoPeJarMo shell), `/user` (DoPeJar), `/health` |
| **ledger** (immudb) | 3322 (gRPC), 9497 (metrics) | Append-only hash-chained truth store |
| **zitadel** | 8085 | OIDC identity + authorization (JWT issuance) |
| **zitadel-db** (PostgreSQL) | 5432 | Zitadel's backing store |

### Host-Native Services

| Service | Port | Purpose |
|---------|------|---------|
| **Ollama** | 11434 | Local LLM (Metal GPU). Models: qwen2.5-coder:14b, qwen3-coder:30b |

Ollama runs natively on macOS for Metal GPU acceleration. Docker containers reach it via `host.docker.internal:11434`.

### Developer Tools

| Tool | Port | Purpose |
|------|------|---------|
| **Backstage** | 3000 (UI), 7007 (API) | Service catalog, TechDocs, entity relationships |
| **MkDocs** | 8000 | Architecture docs (Brain Factory) |

---

## Platform SDK Contract

> **Any concern covered by `platform_sdk` MUST be satisfied through `platform_sdk`. No app, service, or agent may re-implement these concerns directly.**

This is not a suggestion. It is the enforced architectural contract.

### What You Must Do

1. **Check MODULES.md first** — before reaching for any external library
2. **Import from `platform_sdk`** — not from the underlying library
3. **Use MockProvider in tests** — never spin up real services in unit tests
4. **Never add a secret to source code** — use `get_secret("key_name")`
5. **Never silence errors** — let `platform_sdk.errors` capture them

```python
# CORRECT
from platform_sdk import get_logger, complete, verify_token

# WRONG — bypasses the contract
import structlog
import openai
import jwt
```

### Covered Concerns

| Concern | Module | Do NOT |
|---------|--------|--------|
| Authentication | `platform_sdk.tier0_core.identity` | Import `jwt`, provider SDKs |
| Logging | `platform_sdk.tier0_core.logging` | Use `print()`, raw structlog |
| Errors | `platform_sdk.tier0_core.errors` | Import `sentry_sdk`, raise raw Exception |
| Configuration | `platform_sdk.tier0_core.config` | Scatter `os.getenv()` calls |
| Secrets | `platform_sdk.tier0_core.secrets` | Hardcode secrets, `os.getenv()` for secrets |
| Database | `platform_sdk.tier0_core.data` | Import `sqlalchemy` directly |
| Validation | `platform_sdk.tier1_runtime.validate` | Use Pydantic directly in routes |
| Context | `platform_sdk.tier1_runtime.context` | Use `threading.local()` |
| Health | `platform_sdk.tier2_reliability.health` | Write custom /health endpoints |
| Audit | `platform_sdk.tier2_reliability.audit` | Write custom audit tables |
| Permissions | `platform_sdk.tier3_platform.authorization` | Inline `if user.role == "admin"` |
| Notifications | `platform_sdk.tier3_platform.notifications` | Import `smtplib`, `boto3.ses` |
| LLM inference | `platform_sdk.tier4_advanced.inference` | Import `openai`, `anthropic` |
| LLM observability | `platform_sdk.tier4_advanced.llm_obs` | Skip observability |
| Vector search | `platform_sdk.tier3_platform.vector` | Import `qdrant_client` |

### SDK Architecture

5 tiers with strict one-way dependencies: tier0 → tier1 → tier2 → tier3 → tier4.

Every module follows the same pattern:
- **Protocol** interface (the contract)
- **MockProvider** (for tests, selected via env var)
- **Real provider** (selected via env var at runtime)
- Single import path: `from platform_sdk import ...`

Key env vars:
```
PLATFORM_INFERENCE_PROVIDER=mock|openai|anthropic|ollama
PLATFORM_IDENTITY_PROVIDER=mock|zitadel|auth0
PLATFORM_VECTOR_BACKEND=memory|qdrant
PLATFORM_LLM_OBS_BACKEND=mock|langfuse
PLATFORM_ENVIRONMENT=local|test|staging|production
```

### Module Status (46 total, 20 minimal)

| Tier | Modules |
|------|---------|
| **tier0_core** (13) | identity, logging, errors, config, secrets, data, metrics, http, ids, redact, flags, tracing, tasks |
| **tier1_runtime** (8) | context, validate, serialize, retry, ratelimit, clock, runtime, middleware |
| **tier2_reliability** (8) | health, audit, cache, metrics(re-export), circuit, storage, crypto, fallback |
| **tier3_platform** (10) | authorization, notifications, vector, api_client, discovery, policy, experiments, agent, multi_tenancy, clients/ |
| **tier4_advanced** (7) | inference, llm_obs, evals, cost, workflow, messaging, schemas |

Full details: `platform_sdk/MODULES.md`

---

## The Cognitive Stack (How DoPeJar Thinks)

### Three Tiers

**HO1 (Execution)** — All LLM calls. Stateless single-shot workers under prompt contracts. Structures conversations into learning artifacts at write time. Executes work orders at read time. One mouth, one log.

**HO2 (Orchestration)** — Mechanical only. Never calls LLM. Dispatches Prompt Pack Inspection to HO1, reads Graph, computes LIVE ∩ REACHABLE ∩ NOT_SUPPRESSED, plans work orders, resolves intent transitions deterministically.

**HO3 (The Graph)** — Pure storage. In-memory materialized view. Nodes hold methylation values, suppression masks, lifecycle status. HO2 reads it. Write Path updates it. **If you are adding active execution to HO3 — STOP. You are drifting.**

### The Weight Formula

```
score = field_match × base_weight × recency_factor × outcome_reinforcement × (1 - M)
```

Where M is methylation (0.0–1.0). M=0 = fully accessible. M=1 = functionally invisible but still exists in Ledger.

### Per-Turn Dispatch

```
Step 1: Aperture       HO2 reads accumulator state + inspection → depth
Step 2: Planning       HO2 translates intent → work orders
Step 3: Execution      HO1 executes under prompt contracts
Step 4: Verification   HO2 checks against acceptance criteria
Step 5: Feedback       Outcome signal → Write Path → Graph
```

### Context Engineering

```
ELIGIBLE = LIVE ∩ REACHABLE(from active intent)
```

Not RAG. Not sliding windows. Not embedding proximity. Context is computed from explicit causal state: lifecycle reducer + reachability graph + active intent root + policy ruleset.

### Intent Model

Intent is a first-class entity with explicit lifecycle: `DECLARED → SUPERSEDED / CLOSED / FORKED / ABANDONED`. HO1 proposes transitions. HO2 resolves mechanically. One active intent at a time. Block rather than guess.

---

## Sawmill Templates (Build Process)

When building a new framework, follow the Sawmill document chain:

| Doc | Purpose |
|-----|---------|
| **D1 — Constitution** | Why this framework exists, what it governs |
| **D2 — Specification** | What to build, mechanical specs |
| **D3 — Data Model** | Schema, events, Graph nodes |
| **D4 — Contracts** | Prompt contracts, interface contracts |
| **D5 — Research** | Spike findings, technical decisions |
| **D6 — Gap Analysis** | What's missing, what needs resolving |
| **D7 — Plan** | Build plan, phased delivery |
| **D8 — Tasks** | Concrete work items |
| **D9 — Holdout Scenarios** | Edge cases the framework must handle |
| **D10 — Agent Context** | What a builder agent needs to know |

Also see:
- **AGENT_BUILD_PROCESS.yaml** — machine-readable build workflow
- **BUILDER_PROMPT_CONTRACT.md** — how to structure builder agent prompts
- **BUILDER_HANDOFF_STANDARD.md** — how to hand off between agents
- **PRODUCT_SPEC_FRAMEWORK.md** — product-level specification template

Templates: `https://github.com/rabruni/Brain_Factory/tree/main/Templates`

---

## Seven Design Principles

1. **All authority must be explicit.** No inferred permissions, no implicit grants.
2. **All lifecycle transitions must be logged.** If it's not logged, it didn't happen.
3. **No semantic inference at authority boundary.** HO1 proposes. HO2 decides mechanically.
4. **Determinism over cleverness.** Block and ask. Never guess.
5. **Projection must be reversible.** Suppression is a view, not a deletion.
6. **Intent is namespace, not label.** Intent is the root of causal authority.
7. **Time effects must be explicit inputs or excluded.** No wall-clock decay.

---

## Repository Map

### Brain Factory (Architecture Authority)
`https://github.com/rabruni/Brain_Factory`

```
architecture/
  NORTH_STAR.md          ← Design authority (WHY) — resolves all ambiguity
  BUILDER_SPEC.md        ← Build authority (WHAT) — assembly instructions
  OPERATIONAL_SPEC.md    ← Operational authority (HOW) — runtime behavior
  BUILD-PLAN.md          ← Current build plan
  FWK-0-DRAFT.md         ← Framework 0 draft spec
Templates/
  GUIDE.md               ← How to use Sawmill templates
  D1-D10                 ← Sawmill document chain
  AGENT_BUILD_PROCESS.yaml
  BUILDER_PROMPT_CONTRACT.md
  BUILDER_HANDOFF_STANDARD.md
```

### DoPeJar SDK (Platform + Kernel + Catalog)
`https://github.com/rabruni/dopejar_sdk`

```
kernel/
  main.py                ← WebSocket server (the cognitive process)
  Dockerfile
platform_sdk/
  MODULES.md             ← All 46 modules reference
  docs/CONTRACT.md       ← The enforced platform contract
  docs/ADOPTION.md       ← Migration patterns
  tier0_core/            ← 13 foundational modules
  tier1_runtime/         ← 8 request-level safety modules
  tier2_reliability/     ← 8 production operations modules
  tier3_platform/        ← 10 cross-service pattern modules
  tier4_advanced/        ← 7 advanced capability modules
  tests/                 ← 51 tests, all mock providers
docker-compose.yml       ← 4 Docker services + Ollama host-native
catalog-info.yaml        ← Backstage entities (kernel, APIs, resources)
```

---

## Quick Reference: What NOT to Do

- Do NOT create new primitives — assemble from the nine
- Do NOT add execution logic to HO3 — it is pure storage
- Do NOT import provider libraries directly — go through platform_sdk
- Do NOT use wall-clock time — use session boundaries
- Do NOT build governance for its own sake — it serves DoPeJar
- Do NOT implement concerns in app code and defer the SDK module — the bypass becomes permanent
- Do NOT infer intent — HO1 proposes, HO2 resolves mechanically
- Do NOT write to the Graph directly — submit events, the Write Path handles persistence

---

## MCP Tools Available

The platform SDK exposes tools via Model Context Protocol:

```
python -m platform_sdk.mcp_server
```

| Tool | Description |
|------|-------------|
| `log_event` | Emit a structured log event |
| `emit_metric` | Record a Prometheus metric |
| `get_secret` | Retrieve a secret by key |
| `check_rate_limit` | Check/consume rate limit tokens |
| `query_vector` | Semantic search over vector store |
| `upsert_vector` | Insert/update vectors |
| `call_inference` | LLM completion via LiteLLM |
| `embed_text` | Generate embeddings |
| `check_health` | Platform health status |
| `audit_event` | Write an audit log entry |

---

## Deep Dive Links

| Document | What It Covers | URL |
|----------|---------------|-----|
| NORTH_STAR.md | Design authority — WHY | [GitHub](https://github.com/rabruni/Brain_Factory/blob/main/architecture/NORTH_STAR.md) |
| BUILDER_SPEC.md | Build authority — WHAT | [GitHub](https://github.com/rabruni/Brain_Factory/blob/main/architecture/BUILDER_SPEC.md) |
| OPERATIONAL_SPEC.md | Runtime behavior — HOW | [GitHub](https://github.com/rabruni/Brain_Factory/blob/main/architecture/OPERATIONAL_SPEC.md) |
| CONTRACT.md | Platform SDK contract | [GitHub](https://github.com/rabruni/dopejar_sdk/blob/main/platform_sdk/docs/CONTRACT.md) |
| MODULES.md | All 46 SDK modules | [GitHub](https://github.com/rabruni/dopejar_sdk/blob/main/platform_sdk/MODULES.md) |
| ADOPTION.md | Migration patterns | [GitHub](https://github.com/rabruni/dopejar_sdk/blob/main/platform_sdk/docs/ADOPTION.md) |
| Sawmill Guide | Template usage | [GitHub](https://github.com/rabruni/Brain_Factory/blob/main/Templates/GUIDE.md) |

---

*This document is the starting point. Read it fully before writing any code. When in doubt, NORTH_STAR.md resolves all ambiguity.*
