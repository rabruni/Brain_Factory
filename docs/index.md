# Brain Factory

**Status**: NARRATIVE OVERVIEW
**Authority label**: narrative
**Date**: 2026-03-10

Brain Factory hosts architecture authorities, Sawmill runtime contracts, and
framework factory artifacts.

## Canonical Sawmill Entry

```bash
./sawmill/run.sh <FMWK-ID>
```

`--interactive` is exception-only for explicit live checkpoints.

## What Sawmill Produces

A-E pipeline outputs for a framework task:

- specification artifacts (Turns A/B)
- holdout artifacts (Turn C)
- build and review artifacts (Turn D)
- evaluation artifacts and verdict (Turn E)

Runtime endpoint is PASS or FAIL.

## Runtime Source of Truth

- `sawmill/run.sh`
- `sawmill/EXECUTION_CONTRACT.md`
- `sawmill/ROLE_REGISTRY.yaml`
- `sawmill/PROMPT_REGISTRY.yaml`
- `sawmill/ARTIFACT_REGISTRY.yaml`

Narrative pages support operator/agent discovery but do not override runtime.

## Primary Navigation

- How It Works: onboarding, cold start, execution contract, verification
- Architecture: design/build/operational authorities
- Agent Roles: runtime role behavior files and mirrors
- Templates and Build Standards: framework/spec artifacts and standards
- Framework Builds and Portal Governance: state and evidence surfaces
