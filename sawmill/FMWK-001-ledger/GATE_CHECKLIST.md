# Turn A Gate Checklist — FMWK-001-ledger

> Answer these five questions before pressing Enter at the gate.
> If any fail: Ctrl+C, `rm D*.md`, re-run.

## 1. Invention check
Open D1 (Constitution). Does every ALWAYS/ASK/NEVER rule trace to SOURCE_MATERIAL.md, BUILDER_SPEC.md, or NORTH_STAR.md? If you find a rule you can't trace, the agent invented it.

## 2. Scope check
Open D2 (Specification). Count the scenarios. SOURCE_MATERIAL defines 6 interface methods (`append`, `read`, `read_range`, `read_since`, `verify_chain`, `get_tip`) and 5 observable hash chain behaviors. If D2 has 30+ scenarios, scope inflated. If it has fewer than the 5 hash chain behaviors, things were dropped.

## 3. Governance smell
Search D1-D6 for: "governance", "compliance", "policy", "oversight", "audit trail". The Ledger is a data structure, not a governance system. If these appear outside of quoting source material, drift started.

## 4. Boundary check
Open D1 "What the Ledger Does NOT Own." Must match SOURCE_MATERIAL.md exactly:
- Fold logic (FMWK-002)
- Graph structure (FMWK-005)
- Signal accumulation (FMWK-002)
- Gate logic (FMWK-006)
- Work order management (FMWK-003)

If the agent added or removed items, it's reinterpreting boundaries.

## 5. Gap honesty
Open D6 (Gap Analysis). Snapshot format is explicitly OPEN in SOURCE_MATERIAL.md, but the packet may resolve or assume it if that resolution is documented. D6 should still end with zero OPEN items. If the snapshot question disappeared without a documented resolution or assumption, the agent is papering over unknowns.

## Recovery

```bash
rm sawmill/FMWK-001-ledger/D*.md
./sawmill/run.sh FMWK-001-ledger
```

If the same drift pattern repeats, the problem is in the inputs — not the agent.
