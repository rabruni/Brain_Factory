# Portal Status

> Maintained by the **portal-steward** role. Last updated: 2026-03-07.

## Summary

Portal is **healthy**. All 37 mirror pairs aligned. Nav integrity clean. Two mirror drifts and one narrative drift fixed this run.

## Mirror Alignment

| Group | Count | Status |
|-------|-------|--------|
| Architecture | 10 | Aligned |
| Agent roles | 7 | Aligned (builder.md synced this run) |
| Templates | 17 | Aligned |
| Sawmill (COLD_START) | 1 | Aligned (synced this run) |
| Sawmill (DEPENDENCIES.yaml) | 1 | Aligned (added to map this run) |
| CLAUDE.md -> institutional-context | 1 | Aligned |
| **Total mirrors** | **37** | **All aligned** |

Infrastructure mirrors (no docs/ copy, validated by map only):
- `catalog-info.yaml` — exists, valid
- `mkdocs.yml` — exists, valid
- `sawmill/DEPENDENCIES.yaml` — exists, valid (added this run)

## Narrative Coverage

| Page | Type | Source backing |
|------|------|---------------|
| `docs/index.md` | narrative | All claims link to architecture, sawmill, or agent sources |
| `docs/agent-onboarding.md` | narrative | Builder reading order diagram updated this run to include AGENT_BOOTSTRAP.md. All claims now backed. |
| `docs/dopejar-catalog.md` | narrative | All claims backed |
| `docs/sawmill/PIPELINE_VISUAL.md` | narrative | All claims reference existing templates and agents |
| `docs/PORTAL_CONSTITUTION.md` | narrative | Self-referential governance doc, internally consistent |

## Status Pages

| Page | Type | Current |
|------|------|---------|
| `docs/status.md` | status | Last updated 2026-03-06. Reflects known state accurately. |
| `docs/sawmill/FMWK-001-ledger.md` | status | Accurate. Tracks spec/plan/holdout completion, 6 open issues. |
| `docs/sawmill/FMWK-002-write-path.md` | status | Waiting on FMWK-001. |
| `docs/sawmill/FMWK-003-orchestration.md` | status | Waiting on FMWK-002. |
| `docs/sawmill/FMWK-004-execution.md` | status | Waiting. |
| `docs/sawmill/FMWK-005-graph.md` | status | Waiting. |
| `docs/sawmill/FMWK-006-package-lifecycle.md` | status | Waiting. |
| `docs/PORTAL_STATUS.md` | status | This page. |

## Nav Integrity

- **49 nav targets** in `mkdocs.yml` — all exist on disk.
- **2 orphan files** in `docs/`: `PORTAL_MAP.yaml`, `validate_portal_map.py` — portal infrastructure, not rendered content. Expected.
- **No missing pages.**

## Known Drift

None. All drift resolved this run.

## Auditor Findings

`sawmill/PORTAL_AUDIT_RESULTS.md` (2026-03-07): 12 findings, all status "Fixed". No open items requiring steward action.

## Portal Map Validation

```
PASS: 52 entries, 0 errors
```
