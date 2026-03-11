# DoPeJarMo Ground-Truth Implementation Audit

**Date**: 2026-03-11
**Auditor**: Claude Opus 4.6 (automated, evidence-driven)
**Scope**: Brain Factory repo, dopejar runtime repo, Sawmill pipeline, running services
**Method**: Filesystem evidence, line counts, artifact presence/absence, process inspection

---

## 1. Executive Truth

DoPeJarMo does not exist yet as a running system. No cognitive capability, no governed memory, no agent interaction, and no product behavior exists in executable form.

What exists:

- **Architecture documents** that are thorough, internally consistent, and version-controlled (NORTH_STAR v3.0, BUILDER_SPEC v3.0, OPERATIONAL_SPEC v3.0, BUILD-PLAN v1.0). These define the system clearly.
- **A bootstrap build pipeline (Sawmill)** validated end-to-end with mock workers against a canary framework. The pipeline machinery works. It has never completed a real framework build.
- **A pre-existing Platform SDK** (7,965 lines, 5 tiers, 44+ modules) built before Sawmill existed. Never passed through the governed build process.
- **A 110-line kernel stub** that accepts WebSocket connections and sends ACK messages. Zero cognitive logic, zero Ledger integration, zero HO1/HO2/HO3 behavior.
- **An incomplete first attempt** to build FMWK-001 Ledger through Sawmill. Spec documents (D1-D10) are complete. The builder produced 374 lines of code, 8 files, and the core file (`ledger.py`) is 33 lines of `NotImplementedError` interface stubs. No RESULTS.md. No evaluation.
- **Docker services defined but not running.** `docker compose ps` shows nothing. Ollama runs natively outside Docker.
- **Backstage developer portal** running via launchd, 17 entities, TechDocs serving static HTML.

The project has invested heavily in architecture and build tooling. The design is solid and the pipeline is real. But the gap between "design complete" and "product exists" is the entire gap.

---

## 2. Intended Build Order vs Actual State

| Phase | ID | Name | Intended Purpose | Dependencies | Actual State | Evidence |
|-------|----|------|-----------------|--------------|--------------|----------|
| 0 GENESIS | FMWK-000 | framework-framework | Define schemas, gates, governed filesystem | None | S1 — documented only | FWK-0-DRAFT.md is self-labeled "ROUGH DRAFT -- NOT AUTHORITY" |
| 1 KERNEL | FMWK-001 | ledger | Append-only hash-chained event store | FMWK-000 | S2 — spec complete, code is stubs | `staging/FMWK-001-ledger/`: 8 files, 374 lines total, no RESULTS.md |
| 1 KERNEL | FMWK-002 | write-path | Synchronous mutation, fold logic | FMWK-001 | S0 — not started | No directory, no spec pack |
| 1 KERNEL | FMWK-003 | orchestration | Work order planning, dispatch | FMWK-002 | S0 — not started | Blocked by write-path |
| 1 KERNEL | FMWK-004 | execution | All LLM calls, prompt contracts | FMWK-002 | S0 — not started | Blocked by write-path |
| 1 KERNEL | FMWK-005 | graph | In-memory materialized view | FMWK-002 | S0 — not started | Blocked by write-path |
| 1 KERNEL | FMWK-006 | package-lifecycle | Gates, install/uninstall | FMWK-001 | S0 — not started | Blocked by ledger completion |
| 2 Layer 1 | FMWK-010+ | DoPeJarMo OS | Agent interface, routing, meta-learning | KERNEL complete | S0 — not started | Blocked by all KERNEL |
| 3 Layer 2 | FMWK-020+ | DoPeJar product | Memory, intent, conversation | Layer 1 complete | S0 — not started | Blocked by everything |
| Canary | FMWK-900 | sawmill-smoke | Pipeline validation | None | S4 — runs locally (mock only) | 11 runs in runs/ directory, latest passed 45/45 checks |

---

## 3. System State Table

| Subsystem | S-Rating | What Is Real | What Is Doc-Only / Fake-Done | Critical Path? |
|-----------|----------|-------------|------------------------------|---------------|
| Brain Factory | S2 | Architecture docs (v3.0), templates, mkdocs site, Backstage portal | The docs describe a system that does not exist | Yes — design authority |
| Sawmill | S4 | run.sh (2,215 lines), 8 role files, 3 registries, mock workers, canary passing | Has never completed a real agent build. Most default backends are `mock` (orchestrator and auditor default to `claude`). | Yes — build mechanism |
| DoPeJarMo | S0 | Nothing | Specified in BUILD-PLAN as FMWK-010-013 | Yes — the goal |
| DoPeJar | S0 | Nothing | Specified in BUILD-PLAN as FMWK-020-022 | Yes — the product |
| FWK-0 / GENESIS | S1 | FWK-0-DRAFT.md (49KB, detailed). All 7 must-resolve questions approved. | Self-labeled "ROUGH DRAFT." No JSON schemas, no gate runner, no genesis ceremony | Yes — everything depends on it |
| FMWK-001 Ledger | S2 | D1-D10 complete, 13Q answered, 374 lines of scaffolded code | `ledger.py` is interface stubs. No RESULTS.md, no evaluation | Yes — first KERNEL framework |
| FMWK-002 Write-Path | S0 | Nothing | Specified in BUILD-PLAN | Yes — highest-risk critical path item |
| FMWK-003 through FMWK-006 | S0 | Nothing | Specified in BUILD-PLAN | Yes — all KERNEL |
| Platform SDK (pre-existing) | S3 | 7,965 lines Python, 5 tiers, 44+ modules, 582-line LedgerProvider, tests | Never passed through Sawmill. Relationship to governed builds undefined. | Unclear |
| Kernel | S2 | 110-line WebSocket stub, Dockerfile, routes /operator and /user | Sends ACK messages. No cognition, no ledger, no auth, no HO1/HO2/HO3 | Yes |
| Portal / Backstage | S4 | Running via launchd, 17 entities, TechDocs | Documents a system that mostly doesn't exist | No |
| Docker topology | S1 | docker-compose.yml with 5 services, volumes, healthchecks | No containers running | Not yet |
| Governed filesystem | S0 | Referenced in architecture | No `/governed/` directory. No genesis ceremony performed | Yes |
| Verification / acceptance | S2 | 5 validator scripts, canary audit framework | Only tested with mock workers | Yes |

---

## 4. Biggest Drift / Delusion Risks

### 1. Confusing Pipeline Readiness with Product Readiness

The Sawmill canary passes 45/45 checks. This creates a powerful illusion that "the system works." But the canary uses a deterministic mock worker that produces synthetic artifacts. No real framework has completed all 5 turns. The pipeline is a factory with no products coming off the line.

### 2. The Platform SDK Exists Outside Governance

The pre-existing SDK (7,965 lines) contains real implementations of things Sawmill is supposed to build — most notably a 582-line LedgerProvider with Mock, Immudb, and QLDB backends. This code was never specified through D1-D10, never reviewed through 13Q, never evaluated against holdouts. The relationship between pre-existing SDK code and Sawmill-governed rebuilds is architecturally undefined. Will FMWK-001 staging code replace it? Wrap it? Promote it? The answer affects every KERNEL framework's real scope.

### 3. FWK-0 Is Still a Rough Draft

FWK-0-DRAFT.md is self-labeled "ROUGH DRAFT -- NOT AUTHORITY." It defines JSON schemas, gate definitions, and filesystem conventions that all 13 frameworks depend on. None of those schemas or definitions exist as implemented artifacts. All 7 must-resolve questions have been approved, but promotion to authority has not been performed. The governed filesystem doesn't exist. The gates referenced by the Sawmill pipeline are conceptual, not executable.

### 4. The 48-Hour Timeline Was Aspirational

BUILD-PLAN describes building all 13 frameworks within 48 hours. Created 2026-02-26. It is now 2026-03-11 (13 days later). FMWK-001 has 8 files, every method raises `NotImplementedError`, and no RESULTS.md exists. The timeline was aspirational. Treating it as credible creates pressure to skip the governance the system is designed around.

### 5. Governance Complexity as a Self-Reinforcing Loop

The Sawmill infrastructure: 2,215-line run.sh, 8 agent roles, 3 registries, 5 validators, 18 templates in two formats, execution contract, traversal document, portal stewardship, canary audits. This exists to build 13 frameworks. So far it has produced 374 lines of stub code toward one framework. The project's own CLAUDE.md warns: "Previous attempts failed because agents over-indexed on governance and lost the product." This warning describes the current trajectory.

---

## 5. Minimum Clean Path to Start Genuinely Building DoPeJarMo

1. **Freeze Sawmill pipeline improvements.** The pipeline works with mock workers. Further pipeline work is displacement activity until a real framework ships.

2. **Resolve the SDK/Sawmill code relationship.** Decide explicitly: does FMWK-001 replace, wrap, or promote the pre-existing `platform_sdk/tier0_core/ledger.py`? This determines the real scope of every KERNEL framework.

3. **Promote FWK-0 from DRAFT to AUTHORITY.** The schemas and conventions don't need to be perfect. They need to be declared stable enough to build against. "ROUGH DRAFT" gives every downstream agent an excuse to wait. All 7 must-resolve questions are already approved.

4. **Complete FMWK-001 Ledger (Turn D).** Replace the `NotImplementedError` stubs with real implementations. Produce RESULTS.md. This proves the factory can produce real code.

5. **Evaluate FMWK-001 Ledger (Turn E).** Run holdout evaluation. Get a PASS/FAIL verdict. Close the loop on the first governed build.

6. **Start Docker services.** Run `docker compose up`. Get immudb, kernel, and zitadel running. Establish the runtime environment.

7. **Build FMWK-002 Write-Path (Turns A-E).** Critical-path item. Implements the core invariant (synchronous Ledger append + Graph fold). Nothing else composes without it.

8. **Build FMWK-005 Graph and FMWK-006 Package-Lifecycle.** Can run in parallel after Write-Path interfaces exist. Both are KERNEL prerequisites.

9. **Build FMWK-003 Orchestration and FMWK-004 Execution.** Depend on Write-Path and Ledger. Completes KERNEL.

10. **Assemble KERNEL, run genesis, start FMWK-010 Agent-Interface.** Hand-verify KERNEL as a package. Then — and only then — begin Layer 1, which IS DoPeJarMo.

---

## 6. What Should NOT Be Worked On Yet

- **More Sawmill pipeline tooling.** No new validators, registries, or audit scripts. Use the pipeline, don't improve it.
- **Layer 1 or Layer 2 frameworks (FMWK-010+).** Blocked by KERNEL. Starting specs is premature.
- **Portal / TechDocs polish.** Backstage works. The docs describe a system that doesn't exist. Making them prettier doesn't help.
- **Zitadel integration.** Auth adds complexity with zero benefit until there's something to authenticate against.
- **Multi-backend agent routing.** ROLE_REGISTRY defines Claude, Codex, Gemini, and mock. Pick one and use it.
- **Additional canary scenarios.** The canary proved the pipeline works. More variants don't build frameworks.
- **Governance documents about governance.** EXECUTION_CONTRACT, AGENT_TRAVERSAL, SAWMILL_ANALYSIS, RUNTIME_SPEC, HARNESS_INVARIANTS, CANARY_BACKEND_POLICY — the volume of meta-governance is already high. Do not add more.

---

## 7. Confidence and Unknowns

### High Confidence

- Architecture docs are well-designed, internally consistent, and represent genuine product thinking. NORTH_STAR v3.0 is clear.
- Sawmill machinery is real. run.sh orchestrates 5 turns with retry, gating, and event logging. Canary proves it end-to-end with mocks.
- The 9 primitives and 3-layer architecture are sound. HO1/HO2/HO3 separation is clean. Ledger-as-truth-store is well-motivated.
- Platform SDK is real, tested code (7,965 lines, 677 lines of tests).

### Uncertain

- **Whether Sawmill can produce real code with real agents.** Only mock workers have succeeded. FMWK-001 builder produced stubs. The pipeline may be too complex for current agent capabilities.
- **SDK/Sawmill boundary.** The pre-existing SDK and Sawmill-governed builds target overlapping functionality. How they reconcile is not documented.
- **Whether the 48-hour timeline was ever realistic.** 5 agent turns and 20+ artifacts per framework, times 13 frameworks, with agents that haven't completed even one.

### Unknown

- Whether Ray has made SDK/Sawmill reconciliation decisions captured outside these repos.
- Whether agent workers (Codex in production mode) can complete Turn D at all.
- Whether Docker services have ever been started together as a stack. Definitions exist, no runtime evidence.

### Bottom Line

Zero of the 9 primitives are implemented as governed code. Zero of the 13 frameworks have passed all 5 Sawmill turns. The kernel is a stub. DoPeJar does not exist. The single most important next step is completing one real framework build (FMWK-001 Ledger) through all 5 turns with real agents, proving the factory can produce output.

---

## Critical Files

| File | Why It Matters |
|------|---------------|
| `staging/FMWK-001-ledger/ledger/ledger.py` | 33-line interface stub that must become real — completing this unblocks everything |
| `architecture/FWK-0-DRAFT.md` | Must be promoted from ROUGH DRAFT to AUTHORITY |
| `sawmill/run.sh` | Must execute Turn D+E with real agents, not just mocks |
| `dopejar/platform_sdk/tier0_core/ledger.py` | Pre-existing 582-line LedgerProvider whose relationship to governed rebuild must be resolved |
| `dopejar/kernel/main.py` | 110-line stub that will eventually become DoPeJarMo's entry point |
| `sawmill/FMWK-001-ledger/BUILDER_HANDOFF.md` | The handoff document — builder's incomplete output suggests this may need refinement |
