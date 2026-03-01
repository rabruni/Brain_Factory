# D7: Plan — {name}
Meta: v:{ver} (matches D2) | status:{Draft|Review|Final} | constitution: D1 {ver} | gap analysis: D6 {PASS|FAIL} ({N} open)

## Summary
One paragraph: what, why, how, first use case.

## Technical Context
Language/Version | Key Dependencies | Storage | Testing Framework | Platform | Performance Goals | Scale/Scope

## Constitution Check
| Article | Principle | Compliant (YES/NO) | Notes (how architecture satisfies) |
One row per D1 article.

## Architecture Overview
ASCII component diagram + data flow.

### Component Responsibilities
Per component:
- File: `{filename}`
- Responsibility | Implements (D2 SC-###) | Depends On | Exposes (public interface/signatures)

### File Creation Order
Directory tree of all source, test, and supporting files with purpose annotations.

### Testing Strategy
- Unit Tests: what's tested, mocking strategy per component
- Integration Tests: what's tested with real (not mocked) deps
- Smoke Test: minimal E2E verification command + expected result

### Complexity Tracking
| Component | Est. Lines | Risk (Low/Med/High) | Notes |
Totals for source and tests.

### Migration Notes
"Greenfield — no migration." or migration path.
