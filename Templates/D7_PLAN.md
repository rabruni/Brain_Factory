# D7: Plan — [Component Name]

**Component:** [Component Name]
**Spec Version:** [X.Y.Z] (matches D2)
**Status:** [Draft | Review | Final]
**Constitution:** D1 [version]
**Gap Analysis:** D6 — [PASS/FAIL] ([N] open items)

---

## Summary

<!-- One paragraph: what this component is, what it does, how it's built, and its first use case. -->

[Summary paragraph]

## Technical Context

```
Language/Version:    [e.g., Python 3.10+]
Key Dependencies:   [e.g., stdlib only, or list external deps]
Storage:            [e.g., filesystem, database, etc.]
Testing Framework:  [e.g., pytest, jest, etc.]
Platform:           [e.g., macOS / Linux]
Performance Goals:  [e.g., validation < 5 seconds]
Scale/Scope:        [e.g., single operator, no concurrency]
```

## Constitution Check

<!-- Verify every D1 article can be satisfied by this architecture. -->

| Article | Principle | Compliant | Notes |
|---------|-----------|-----------|-------|
| Art 1 | [Principle name] | [YES/NO] | [How the architecture satisfies this] |
| Art 2 | [Principle name] | [YES/NO] | [Notes] |

<!-- Add rows for every D1 article -->

---

## Architecture Overview

<!-- ASCII diagram showing major components and data flow. -->

```
[Component diagram here]
```

### Component Responsibilities

<!-- One section per major component/module. Define what it does, what it implements,
     what it depends on, and what interface it exposes. -->

#### [ComponentName] (`[filename]`)

**Responsibility:** [What this component does]
**Implements:** [D2 scenario IDs]
**Depends On:** [Other components or external dependencies]
**Exposes:** [Public interface — function signatures]

#### [ComponentName] (`[filename]`)

**Responsibility:** [What this component does]
**Implements:** [D2 scenario IDs]
**Depends On:** [Dependencies]
**Exposes:** [Public interface]

<!-- Add more components as needed -->

### File Creation Order

<!-- Complete directory tree of all source files, tests, and supporting files. -->

```
[package-name]/
├── [source_dir]/
│   ├── [file1]          ← [purpose]
│   ├── [file2]          ← [purpose]
│   └── [file3]          ← [purpose]
├── tests/
│   ├── [test_file1]     ← [what it tests]
│   └── [test_file2]     ← [what it tests]
└── [supporting_files]/
    └── [file]           ← [purpose]
```

### Testing Strategy

#### Unit Tests
<!-- What gets unit tested and how. Include mocking strategy. -->
- [Component 1]: [What's tested, how filesystem/deps are mocked]
- [Component 2]: [What's tested]

#### Integration Tests
<!-- What gets tested with real (not mocked) dependencies. -->
- [Integration test 1: description]
- [Integration test 2: description]

#### Smoke Test
<!-- Minimal end-to-end verification that the component works. -->
- [Smoke test command and expected result]

### Complexity Tracking

| Component | Estimated Lines | Risk | Notes |
|-----------|----------------|------|-------|
| [component 1] | [N-N] | [Low/Medium/High] | [Risk notes] |
| [component 2] | [N-N] | [Low/Medium/High] | [Notes] |
| **Total source** | **[N-N]** | | |
| **Total tests** | **[N-N]** | | [N]+ test methods |

### Migration Notes

<!-- If replacing an existing system, describe migration path.
     If greenfield, state "Greenfield — no migration." -->

[Migration notes or "Greenfield — no migration."]
