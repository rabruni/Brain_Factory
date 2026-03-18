# Sawmill Linter Design

## Why This Exists

The sawmill validates its own output — gates, evidence, holdout evaluation. But nothing validates the sawmill's input: authority documents, TASK.md schemas, and generated planning artifacts. This is the blade guard.

A naming convention contradiction between `FWK-0-DRAFT.md` and `CLAUDE.md` propagated through TASK.md into Turn B documents, causing the builder to write to the wrong staging path. No check caught it until output verification — after the builder had already run. The linter catches this class of bug before lumber enters the mill.

---

## Four Categories of Checks

### Category A: Blueprint Consistency

Do authority documents agree with each other on definitions?

Runs once against the repo. No framework ID needed. Validates blueprints before any lumber enters the mill.

| Check | Source 1 | Source 2 | Comparison |
|-------|----------|----------|------------|
| A-1: Framework identifier definition | `FWK-0-DRAFT.md` L77 | `CLAUDE.md` L200 | Must define the canonical identifier the same way |
| A-2: Primitive list | `NORTH_STAR.md` | `BUILDER_SPEC.md` | Exact names, exact count, exact order |
| A-3: Primitive list | `BUILDER_SPEC.md` | `CLAUDE.md` | Same |
| A-4: KERNEL framework list | `BUILD-PLAN.md` | `CLAUDE.md` | Same 6 IDs, same 6 names |
| A-5: KERNEL framework list | `DEPENDENCIES.yaml` | `BUILD-PLAN.md` | Same |
| A-6: Agent role list | `CLAUDE.md` | `ROLE_REGISTRY.yaml` | Same roles, same files |

### Category B: Schema Validation

Does each TASK.md conform to the blueprints?

Runs per TASK.md. Validates the work order before it enters the sawmill.

| Check | What | How |
|-------|------|-----|
| B-1: ID == directory name | `TASK.md` ID field | Exact string match against parent directory name |
| B-2: ID matches naming convention | `TASK.md` ID field | Must match full identifier regex from blueprints |
| B-3: No orphan fields | `TASK.md` Name field | If ID is the full identifier, separate Name field must not exist |

### Category C: Registry Integrity

Are the machine's gears meshing correctly?

Runs once. Validates the machine itself.

| Check | What | How |
|-------|------|-----|
| C-1: Prompt→Artifact | Every artifact in PROMPT_REGISTRY | Must exist in ARTIFACT_REGISTRY |
| C-2: Role→File | Every role_file in ROLE_REGISTRY | Must exist on disk |
| C-3: Prompt→File | Every prompt_file in PROMPT_REGISTRY | Must exist on disk |
| C-4: Template pairs | Every template in Templates/ | Must have a compressed/ counterpart |
| C-5: Dependency IDs | Every ID in DEPENDENCIES.yaml | Must match a sawmill/ directory name (exact) |

### Category D: Pre-Turn Artifact Consistency

Are the generated plans correct before the next turn uses them?

Runs per-framework, per-turn. Validates intermediate products before the next blade touches them.

| Check | When | What |
|-------|------|------|
| D-1: No wrong staging paths | Before Turn D | Every `staging/FMWK-*` in Turn B docs must exactly equal `artifact_path(staging_root)` |
| D-2: Framework ID propagation | Before Turn D | Framework ID in D7, D8, D10, BUILDER_HANDOFF must match TASK.md ID must match directory name |
| D-3: Required artifacts present | Before each turn | All `required_artifacts` for the next prompt must exist on disk |

---

## CLI Interface

```
sawmill/lint_blueprints.py

  --blueprints     Category A (authority doc consistency)
  --schema         Category B (TASK.md validation)
  --registries     Category C (registry integrity)
  --pre-turn D     Category D for a specific framework before Turn D
  --all            Run everything

  --fmwk FMWK-ID  Framework ID (required for --schema and --pre-turn)

  Exit 0 = clean
  Exit 1 = findings
```

## Output Format

```
FAIL  [A-1]  FWK-0-DRAFT.md:L77   "Framework | FMWK-NNN"
             CLAUDE.md:L200        "Frameworks: FMWK-NNN-name"
      Framework identifier defined differently across authority documents.

FAIL  [B-1]  sawmill/FMWK-900-sawmill-smoke/TASK.md:L4  "ID: FMWK-900"
             directory: FMWK-900-sawmill-smoke
      TASK.md ID does not exactly match directory name.

PASS  [C-1]  All PROMPT_REGISTRY artifacts exist in ARTIFACT_REGISTRY.
```

---

## Integration into run.sh

```bash
# Before any framework enters the sawmill:
python3 sawmill/lint_blueprints.py --blueprints --registries \
    || fail_preflight "Linter failed on blueprints/registries"

# Before Turn A:
python3 sawmill/lint_blueprints.py --schema --fmwk "$FMWK" \
    || fail_preflight "TASK.md failed schema check"

# Before Turn D:
python3 sawmill/lint_blueprints.py --pre-turn D --fmwk "$FMWK" \
    || fail_preflight "Turn B artifacts failed consistency check"
```

---

## What This Catches

Three checks that don't exist anywhere in the system today. Any one would have caught the FMWK-900 naming bug:

**B-1** catches it before Turn A — the work order has a wrong ID.

**A-1** catches it before any TASK.md is written — the blueprints disagree on what an ID is.

**D-1** catches it before Turn D — the generated plans have wrong paths.

The system currently validates cuts (agent output). The linter validates the log before it hits the blade (agent input).

---

## Historical Analogy

1800s sawmills had no blueprints, no pre-commissioning, no safety inspection. Workers were responsible for their own safety. Modern sawmills have six steps before a single log touches a blade: feasibility, design review, permits, construction inspection, pre-commissioning, and factory acceptance testing.

This linter is the pre-commissioning step: verify the built machine against its own blueprints before turning it on.
