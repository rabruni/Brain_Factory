# Portal Constitution

Rules governing the human-facing documentation surface (`docs/`, `mkdocs.yml`, `catalog-info.yaml`).

Maintained by the **portal-steward** role (`.claude/agents/portal-steward.md`).

## Principles

1. **Source truth always wins.** Architecture, agent roles, and templates are the authority. Portal text cannot override them.
2. **Mirrors track source.** If a mirror page diverges from its source, the mirror is wrong — update the mirror, not the source.
3. **Narrative links down.** Every claim in a narrative page must link to or reference a source artifact. No unsupported claims.
4. **Audits diagnose, they don't rewrite.** Audit findings flag drift with evidence. They never alter source intent.
5. **Every page is classified.** Each file in `docs/` is one of: **mirror**, **narrative**, **status**, or **audit**.
6. **Steward owns the surface; auditor owns the diagnosis.** The portal-steward maintains `docs/`. The auditor writes `sawmill/PORTAL_AUDIT_RESULTS.md`.
7. **Conflicts escalate.** When source contradicts source, neither agent resolves it — escalate to Ray.

## Page Types

| Type | Purpose | Freshness rule |
|------|---------|---------------|
| Mirror | Rendered copy of a source file | Must match source exactly |
| Narrative | Explains, summarizes, orients humans | Must link to source backing |
| Status | Operational state, gaps, timeline | Must reflect current artifacts |
| Audit | Diagnostic findings with evidence | Read-only, auditor-written |

## Source-to-Surface Map

All mappings are declared in `docs/PORTAL_MAP.yaml`. The portal-steward reads this map to detect drift and maintain alignment.

## Authority Resolution

When files disagree, use the rules in [PORTAL_TRUTH_MODEL.md](PORTAL_TRUTH_MODEL.md) to determine which layer wins: source truth, mirror, narrative, or status/audit.
