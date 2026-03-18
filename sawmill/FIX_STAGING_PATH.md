# Fix: Staging Path Contract

## Context

Read `CLAUDE.md` first. Then read this document.

The FMWK-900-sawmill-smoke run fails at Turn D output verification with:

```
Output for turn_d_build was not refreshed this run: staging/FMWK-900-sawmill-smoke
```

Root cause: `TASK.md` defines `ID: FMWK-900` (short form). The spec agent read
that and authored `staging/FMWK-900/` into D7, D8, D10, and BUILDER_HANDOFF. The
runtime resolves `staging/{FMWK}` from the artifact registry using the full
framework identifier `FMWK-900-sawmill-smoke`. The builder followed the Turn B
docs and wrote to `staging/FMWK-900/`. Verification checked `staging/FMWK-900-sawmill-smoke/` — empty — and failed.

Current state on disk:
- `staging/FMWK-900/` — has smoke.py and test_smoke.py (builder output, wrong place)
- `staging/FMWK-900-sawmill-smoke/` — empty (correct place, nothing here)

Three-part fix in order: (1) prevent recurrence, (2) add a preflight guard, (3) fix
the current run.

---

## Part 1: Systemic Fix — Prevent Recurrence

### 1a. Fix TASK.md — ID field must be the full framework identifier

**File:** `sawmill/FMWK-900-sawmill-smoke/TASK.md`

Change:
```
## Framework
- ID: FMWK-900
- Name: sawmill-smoke
- Layer: SYSTEM-TEST
```

To:
```
## Framework
- ID: FMWK-900-sawmill-smoke
- Layer: SYSTEM-TEST
```

Reason: the `ID` field is what the spec agent reads to construct staging paths.
It must be the full `FMWK-NNN-name` identifier matching the directory name. A
separate `Name` field invites agents to use the ID alone.

### 1b. Update spec-agent and plan-agent role files

**File:** `.claude/agents/spec-agent.md`

Find the section that describes what to write into D7/D8/D10/BUILDER_HANDOFF (or
any output document). Add the following constraint under the output instructions:

```
STAGING PATH RULE: Do NOT author literal staging directory paths in any output
document (D7, D8, D10, BUILDER_HANDOFF, or any other artifact). Reference files
by their name only (e.g., smoke.py, test_smoke.py). The runtime injects
{{STAGING_ROOT_PATH}} into the builder's prompt — that is the only authoritative
staging path. If you write staging/FMWK-anything into a document, you are wrong.
```

**File:** `.claude/agents/builder.md`

Find the section describing where to write output. Confirm it says to use the
path from the injected prompt ({{STAGING_ROOT_PATH}}) and NOT any path from D10
or BUILDER_HANDOFF if they conflict. If no such precedence rule exists, add:

```
PATH PRECEDENCE: The staging root path injected in this prompt ({{STAGING_ROOT_PATH}})
is authoritative. If D10 or BUILDER_HANDOFF reference a different staging path,
ignore them and use the injected path. Never derive the staging path from document
text — only from the injected value.
```

### 1c. Add preflight check in run.sh before Turn D

**File:** `sawmill/run.sh`

Add a new function after `load_artifact_registry()` (around line 703):

```bash
preflight_staging_path_check() {
    local expected
    expected="$(artifact_path staging_root)"
    local doc failed=0
    for doc in \
        "${SAWMILL_DIR}/D7_PLAN.md" \
        "${SAWMILL_DIR}/D8_TASKS.md" \
        "${SAWMILL_DIR}/D10_AGENT_CONTEXT.md" \
        "${SAWMILL_DIR}/BUILDER_HANDOFF.md"; do
        [ -f "$doc" ] || continue
        if grep -qE 'staging/FMWK-[a-z0-9-]+' "$doc"; then
            local found
            found="$(grep -oE 'staging/FMWK-[a-z0-9-]+' "$doc" | sort -u | head -1)"
            if [ "$found" != "$expected" ]; then
                log_error "PREFLIGHT: staging path mismatch in $(basename "$doc")"
                log_error "  found:    $found"
                log_error "  expected: $expected"
                failed=1
            fi
        fi
    done
    [ "$failed" -eq 0 ] || {
        fail_preflight "Staging path mismatch in Turn B documents. Fix Turn B docs before proceeding to Turn D."
    }
}
```

Call this function in the Turn D block, before `turn_d_13q` is invoked. Find
where Turn D starts (around line 2200) and add:

```bash
preflight_staging_path_check
```

as the first line of Turn D execution, after state checks but before any agent
invocation.

---

## Part 2: Fix the Current FMWK-900 Run

### 2a. Fix Turn B documents — replace wrong staging path

In each of the following files, replace every occurrence of `staging/FMWK-900/`
(with or without trailing slash) with `staging/FMWK-900-sawmill-smoke/`:

- `sawmill/FMWK-900-sawmill-smoke/D7_PLAN.md`
- `sawmill/FMWK-900-sawmill-smoke/D8_TASKS.md`
- `sawmill/FMWK-900-sawmill-smoke/D10_AGENT_CONTEXT.md`
- `sawmill/FMWK-900-sawmill-smoke/BUILDER_HANDOFF.md`

Also check for `staging/FMWK-900` without trailing slash and fix those too.

Verify after: `grep -r 'staging/FMWK-900[^-]' sawmill/FMWK-900-sawmill-smoke/`
should return nothing.

### 2b. Move builder output to the correct staging directory

```bash
cp -r staging/FMWK-900/. staging/FMWK-900-sawmill-smoke/
rm -rf staging/FMWK-900
```

Verify after:
- `staging/FMWK-900-sawmill-smoke/smoke.py` exists
- `staging/FMWK-900-sawmill-smoke/test_smoke.py` exists
- `staging/FMWK-900/` no longer exists

---

## Part 3: Test the Fix

### 3a. Verify the preflight passes

Run the new preflight check manually to confirm it finds no mismatches:

```bash
grep -r 'staging/FMWK-900[^-]' sawmill/FMWK-900-sawmill-smoke/
```

Should return empty.

### 3b. Rerun Turn D

```bash
./sawmill/run.sh FMWK-900-sawmill-smoke --from-turn D
```

### 3c. Success criteria

The run passes when ALL of the following are true:

1. Turn D build completes without `OUTPUT_VERIFICATION_FAILED`
2. `staging/FMWK-900-sawmill-smoke/smoke.py` is present and was modified during this run
3. `staging/FMWK-900-sawmill-smoke/test_smoke.py` is present and was modified during this run
4. `sawmill/FMWK-900-sawmill-smoke/RESULTS.md` is present and was modified during this run
5. `sawmill/FMWK-900-sawmill-smoke/builder_evidence.json` is valid JSON containing the correct `run_id`
6. Turn E (evaluator) runs and produces a verdict
7. `./sawmill/run.sh FMWK-900-sawmill-smoke` from a clean state completes all turns without error

### 3d. Regression test — confirm the preflight catches future drift

After the fix is in, manually introduce a bad staging path into a test copy of
D10 and confirm `preflight_staging_path_check` fires and stops Turn D before any
agent is invoked. Then restore D10 to the correct state.

---

## Do NOT

- Touch `.holdouts/FMWK-900-sawmill-smoke/D9_HOLDOUT_SCENARIOS.md` — D9 already
  uses the correct full framework identifier and will work once the builder output
  is in the right place.
- Modify the artifact registry or prompt registry — path resolution is already
  correct.
- Rerun Turn A, B, or C — all prior turns passed. The fix is in Turn B document
  content and builder output location only.
- Auto-approve or simulate checkpoints — use `run.sh` as-is.
