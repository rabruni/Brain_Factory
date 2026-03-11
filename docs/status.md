# Status and Gaps

**Status**: STATUS SURFACE
**Authority label**: status
**Last updated**: 2026-03-10

This page tracks current documentation and runtime-directionality status.
It is a portal/status view, not runtime authority.

## Current Directionality State

| Area | State | Notes |
|------|-------|-------|
| Runtime authority (`run.sh` + execution contract + registries) | Current | Canonical runtime behavior is unattended-by-default and registry-governed |
| Startup authority (`CLAUDE.md`, `AGENT_BOOTSTRAP.md`) | Current | Entry chain is explicit and aligned |
| Main-nav narrative guidance | Updated | Entry path and turn semantics aligned to runtime |
| Source-authority architecture docs | Updated | Old PR/human-gate runtime semantics removed from active guidance |
| Verification checklist parity | Updated | Turn D version evidence checks included |
| Drift guardrails | Added | Runtime claim lint + portal map validator required in run verification |

## Open Residual Risks

| ID | Risk | Impact | Next hardening step |
|----|------|--------|---------------------|
| R-001 | Artifact policy fields still partly metadata | Incomplete policy enforcement from registry fields alone | Incrementally promote metadata fields to runtime checks |
| R-002 | Freshness checks are mtime-based | Regeneration proof is weaker than content attestations | Add hash/content-based regeneration evidence |
| R-003 | Narrative drift can reappear over time | Agents may get mixed signals later | Keep lint check mandatory for runtime-adjacent doc updates |

## Required Verification Before Declaring Runtime-Doc Pass

1. `python3 docs/lint_runtime_claims.py`
2. `python3 docs/validate_portal_map.py`
3. Role/artifact/prompt registry validators
4. `bash -n sawmill/run.sh`

## Notes

- Merge/release actions remain outside Sawmill runtime pass/fail semantics.
- Direct worker dispatch remains exception-only when `run.sh` path is requested.
