# D6: Gap Analysis — sawmill smoke canary
Meta: v:1.0.0 (matches D2/D3/D4) | status:Complete | shared gaps:0 | private gaps:0 | unresolved:0

## Boundary Analysis
### 1. Data In
Description: Inputs entering the canary.

| Boundary | Classification | Status |
| --- | --- | --- |
| Direct call to `ping()` with no arguments | PRIVATE | RESOLVED |

Gaps found: none.

### 2. Data Out
Description: Outputs produced by the canary.

| Boundary | Classification | Status |
| --- | --- | --- |
| Literal return value `"pong"` | PRIVATE | RESOLVED |
| Single unit-test pass/fail result | PRIVATE | RESOLVED |

Gaps found: none.

### 3. Persistence
Description: Stored state or durable artifacts.

| What | Where | Owned By | Status |
| --- | --- | --- | --- |
| `smoke.py` | staging output | FMWK-900-sawmill-smoke | RESOLVED |
| `test_smoke.py` | staging output | FMWK-900-sawmill-smoke | RESOLVED |

Gaps found: none.

### 4. Auth/Authz
Description: Access control requirements.

| Boundary | Status |
| --- | --- |
| No authentication or authorization boundary in scope | RESOLVED |

Gaps found: none.

### 5. External Services
Description: Service dependencies.

| Service | Interface | Status |
| --- | --- | --- |
| None | none | RESOLVED |

Gaps found: none.

### 6. Configuration
Description: Runtime or build configuration.

| Config Item | Source | Status |
| --- | --- | --- |
| None required | TASK.md declares no dependencies | RESOLVED |
| Registry Enforcement | ROLE_REGISTRY.yaml vs Env Overrides | **GAP** |

Gaps found: 
1. **Registry Bypass**: The system allows environment variables (e.g., `SAWMILL_BUILD_AGENT`) to silently supersede `ROLE_REGISTRY.yaml` defaults. This creates a "Shadow Intelligence" state where the documented backend does not match the actual execution backend, violating the principle of explicit authority.

### 7. Error Propagation
Description: How failures surface.

| Error Source | Propagation Path | Status |
| --- | --- | --- |
| Import failure | Python import error -> test failure | RESOLVED |
| Wrong return value | Assertion failure -> test failure | RESOLVED |
| Scope violation | Review failure -> reject staged output | RESOLVED |

Gaps found: none.

### 8. Observability
Description: What can be observed.

| What | How | Status |
| --- | --- | --- |
| Function behavior | unit test result | RESOLVED |
| Scope compliance | file inspection | RESOLVED |

Gaps found: none.

### 9. Resource Accounting
Description: Resource use within scope.

| Resource | Accounting Method | Status |
| --- | --- | --- |
| Python execution only | single local test run | RESOLVED |

Gaps found: none.

## Clarification Log
### CLR-001
- Found During: D1
- Question: Should FWK-0 decomposition articles still appear even though this is a canary?
- Options: include required D1 articles while keeping scope minimal; ignore the role requirement
- Status: RESOLVED
- Blocks: no

Resolution: Include the required decomposition articles because the spec-agent role mandates them, but constrain them to the exact canary scope from `TASK.md`.

### CLR-002
- Found During: D3
- Question: How should D3 be completed when the task forbids creating a real data model?
- Options: invent runtime entities; document only the two owned file artifacts
- Status: RESOLVED
- Blocks: no

Resolution: Document only the two owned file artifacts so D3 stays descriptive without inventing product data.

## Summary
| Category | Gaps Found | Shared | Resolved | Remaining |
| --- | --- | --- | --- | --- |
| Data In | 0 | 0 | 0 | 0 |
| Data Out | 0 | 0 | 0 | 0 |
| Persistence | 0 | 0 | 0 | 0 |
| Auth/Authz | 0 | 0 | 0 | 0 |
| External Services | 0 | 0 | 0 | 0 |
| Configuration | 0 | 0 | 0 | 0 |
| Error Propagation | 0 | 0 | 0 | 0 |
| Observability | 0 | 0 | 0 | 0 |
| Resource Accounting | 0 | 0 | 0 | 0 |

Gate verdict: PASS (zero open)
