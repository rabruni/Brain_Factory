# RESULTS — FMWK-002-write-path

Date: 2026-03-21
Run ID: 20260322T021641Z-00ae718794cd
Attempt: 2
Prompt Contract Version: 1.0.0

## Summary

- Status: PASS
- Staging root: `staging/FMWK-002-write-path/`
- Package ID: `FMWK-002-write-path`
- Framework ID: `FMWK-002`
- Version: `1.0.0`
- Total tests collected: 57
- Full regression result: `57 passed in 0.19s`
- Deviations from D8/D4: none
- Issues remaining: none known

## Baseline Snapshot

Starting test count:

```text
57 tests collected in 0.18s
```

Packages installed at session baseline:

```text
aiofiles==24.1.0
altair==5.5.0
altgraph==0.17.2
annotated-types==0.7.0
anyio==4.12.1
appier==1.36.0
asyncer==0.0.7
attrs==26.1.0
babel==2.18.0
backports.asyncio.runner==1.2.0
backrefs==6.2
beautifulsoup4==4.14.3
bidict==0.23.1
blinker==1.9.0
bracex==2.6
cachetools==6.2.6
certifi==2026.1.4
cffi==2.0.0
chainlit==2.3.0
charset-normalizer==3.4.4
chevron==0.14.0
click==8.1.8
colorama==0.4.6
cryptography==46.0.5
dataclasses-json==0.6.7
ecdsa==0.19.1
EditorConfig==0.17.1
exceptiongroup==1.3.1
fastapi==0.115.14
filetype==1.2.0
future==0.18.2
ghp-import==2.1.0
gitdb==4.0.12
GitPython==3.1.46
google-api==0.1.12
google-api-core==2.30.0
google-api-python-client==2.190.0
google-auth==2.48.0
google-auth-httplib2==0.3.0
googleapis-common-protos==1.72.0
griffe==1.14.0
grpcio==1.78.1
h11==0.16.0
httpcore==1.0.9
httplib2==0.31.2
httpx==0.28.1
idna==3.11
immudb-py==1.5.0
importlib_metadata==8.7.1
iniconfig==2.1.0
Jinja2==3.1.6
jsbeautifier==1.15.4
jsonschema==4.25.1
jsonschema-specifications==2025.9.1
Lazify==0.4.0
literalai==0.1.103
macholib==1.15.2
Markdown==3.9
markdown_graphviz_inline==1.1.3
MarkupSafe==3.0.3
marshmallow==3.26.2
mdx-truly-sane-lists==1.3
mergedeep==1.3.4
mkdocs==1.6.1
mkdocs-autorefs==1.4.4
mkdocs-get-deps==0.2.0
mkdocs-include-markdown-plugin==7.2.1
mkdocs-material==9.7.1
mkdocs-material-extensions==1.3.1
mkdocs-mermaid2-plugin==1.2.3
mkdocs-monorepo-plugin==1.1.2
mkdocs-redirects==1.2.2
mkdocs-techdocs-core==1.6.1
mkdocstrings==0.30.1
mkdocstrings-python==1.18.2
mypy_extensions==1.1.0
narwhals==2.18.0
nest-asyncio==1.6.0
numpy==2.0.2
opentelemetry-api==1.39.1
opentelemetry-exporter-otlp==1.39.1
opentelemetry-exporter-otlp-proto-common==1.39.1
opentelemetry-exporter-otlp-proto-grpc==1.39.1
opentelemetry-exporter-otlp-proto-http==1.39.1
opentelemetry-instrumentation==0.60b1
opentelemetry-proto==1.39.1
opentelemetry-sdk==1.39.1
opentelemetry-semantic-conventions==0.60b1
packaging==25.0
paginate==0.5.7
pandas==2.3.3
pathspec==1.0.4
pillow==11.3.0
pip==21.2.4
plantuml-markdown==3.11.1
platformdirs==4.4.0
pluggy==1.6.0
prometheus_client==0.24.1
proto-plus==1.27.1
protobuf==6.33.5
pyarrow==21.0.0
pyasn1==0.6.2
pyasn1_modules==0.4.2
pycparser==2.23
pydantic==2.12.5
pydantic_core==2.41.5
pydantic-settings==2.11.0
pydeck==0.9.1
Pygments==2.19.2
PyJWT==2.12.1
pymdown-extensions==10.19.1
pyparsing==3.3.2
pytest==8.4.2
pytest-asyncio==1.2.0
python-dateutil==2.9.0.post0
python-dotenv==1.2.1
python-engineio==4.13.1
python-multipart==0.0.18
python-slugify==8.0.4
python-socketio==5.16.1
pytz==2026.1.post1
PyYAML==6.0.3
pyyaml_env_tag==1.1
referencing==0.36.2
requests==2.32.5
rpds-py==0.27.1
rsa==4.9.1
setuptools==58.0.4
simple-websocket==1.1.0
six==1.17.0
smmap==5.0.3
sniffio==1.3.1
soupsieve==2.8.3
SQLAlchemy==2.0.46
starlette==0.41.3
streamlit==1.50.0
structlog==25.5.0
syncer==2.0.3
tenacity==9.1.2
text-unidecode==1.3
toml==0.10.2
tomli==2.4.0
tornado==6.5.5
typing_extensions==4.15.0
typing-inspect==0.9.0
typing-inspection==0.4.2
tzdata==2025.3
uptrace==1.39.0
uritemplate==4.2.0
urllib3==2.6.3
uvicorn==0.39.0
watchdog==6.0.0
watchfiles==0.20.0
wcmatch==10.1
websockets==15.0.1
wheel==0.37.0
wrapt==1.17.3
wsproto==1.2.0
zensical==0.0.2
zipp==3.23.0
```

## Mid-Build Checkpoint

- Total tests after all unit files were green: 57
- Files created so far:
  - `staging/FMWK-002-write-path/README.md`
  - `staging/FMWK-002-write-path/tests/conftest.py`
  - `staging/FMWK-002-write-path/tests/test_folds.py`
  - `staging/FMWK-002-write-path/tests/test_models.py`
  - `staging/FMWK-002-write-path/tests/test_recovery.py`
  - `staging/FMWK-002-write-path/tests/test_service_mutations.py`
  - `staging/FMWK-002-write-path/tests/test_system_events.py`
  - `staging/FMWK-002-write-path/write_path/__init__.py`
  - `staging/FMWK-002-write-path/write_path/errors.py`
  - `staging/FMWK-002-write-path/write_path/folds.py`
  - `staging/FMWK-002-write-path/write_path/models.py`
  - `staging/FMWK-002-write-path/write_path/ports.py`
  - `staging/FMWK-002-write-path/write_path/recovery.py`
  - `staging/FMWK-002-write-path/write_path/service.py`
  - `staging/FMWK-002-write-path/write_path/system_events.py`
- D8 deviations: none
- D4 deviations: none
- P0/P1 coverage confirmation: SC-001 through SC-009 all have explicit tests across `test_service_mutations.py`, `test_folds.py`, and `test_recovery.py`

## Failures Encountered And Fixes

1. Initial red phases failed on missing modules as expected for `write_path.errors`, `write_path.models`, `write_path.system_events`, `write_path.folds`, `write_path.service`, and `write_path.recovery`.
2. First green attempt on models/system-events exposed Python 3.9 runtime parsing of `int | None`; fixed by adding `from __future__ import annotations` in `write_path/errors.py`.
3. First green attempt on `tests/test_service_mutations.py` exposed the same Python 3.9 type-union parsing issue in the test helper; fixed by adding `from __future__ import annotations` in that test file.
4. No behavioral regressions remained after these fixes.

## File Hashes

```text
sha256:e166428cd309e9cbf815e21886a2e9169efe8c738e076cb6df45baa357f1836f  staging/FMWK-002-write-path/README.md
sha256:724ecd99390b2f161f1184c624022e7b35646339ac1d7d2d62fea050de5d416b  staging/FMWK-002-write-path/tests/conftest.py
sha256:9541045a4692a8ac7ac295fc895de1c8d19cd549194c7cd0ea9f398c22832fb0  staging/FMWK-002-write-path/tests/test_folds.py
sha256:b75adbc33c9bcf5558f2f47dd7279f156aade1838c5c2b2ffa1b3cfd06c088f0  staging/FMWK-002-write-path/tests/test_models.py
sha256:d75a189ed7a60eab6289f457dcbfc14e5e1b923212a81b298990c450250dd730  staging/FMWK-002-write-path/tests/test_recovery.py
sha256:29dac436599204f6b86a9d1677cea2d10e170ece623225f14341a2bbdf70c441  staging/FMWK-002-write-path/tests/test_service_mutations.py
sha256:4cea3a07790a2f66ef76c0974539ea68e6e86f4703eb7cbd790d06e6a664549c  staging/FMWK-002-write-path/tests/test_system_events.py
sha256:7d1e08dae0adca45be15fd39b40afd3f1315eb85db419268e58f77e3e1f6897a  staging/FMWK-002-write-path/write_path/__init__.py
sha256:7d7b3f9c41fd739f85fa6214a8d74ccea894e4a30d7550e7f2f8426c08e28cab  staging/FMWK-002-write-path/write_path/errors.py
sha256:1eb2e6d82acc7692ee8044f0ea0bd5f5f5bdf55424be52a58694de71c2fcdbc1  staging/FMWK-002-write-path/write_path/folds.py
sha256:3f61c73a94cfb302dfb323def6a4f2c469a0a15bbf42d2b609f631f4a56bc68d  staging/FMWK-002-write-path/write_path/models.py
sha256:37bcd1951cd48166d04c21106e683fb9826c9e2b2ae267d27a31a7811da2b7b9  staging/FMWK-002-write-path/write_path/ports.py
sha256:e547a707d2ee72bf18f504285e3dba103cb53dcdf2e0913d99ec00d2a4cd9152  staging/FMWK-002-write-path/write_path/recovery.py
sha256:490ef131f1a6f9a2a7184dcc36c683c20fe92f6f138e9cde180199fe1e3ebebb  staging/FMWK-002-write-path/write_path/service.py
sha256:f91d114a524fe993ced9ec6605bda685e355a2ccba73a2bc5e0b45556d26f7b9  staging/FMWK-002-write-path/write_path/system_events.py
```

## Verification Commands And Output

Command:

```bash
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_models.py -v
```

Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Library/Developer/CommandLineTools/usr/bin/python3
cachedir: .pytest_cache
rootdir: /Users/raymondbruni/Cowork/Brain_Factory/staging/FMWK-002-write-path
plugins: anyio-4.12.1, asyncio-1.2.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 11 items

tests/test_models.py::test_mutation_request_preserves_fields PASSED      [  9%]
tests/test_models.py::test_mutation_request_asdict_includes_optional_pack_id PASSED [ 18%]
tests/test_models.py::test_mutation_receipt_represents_folded_success PASSED [ 27%]
tests/test_models.py::test_snapshot_descriptor_preserves_boundary_metadata PASSED [ 36%]
tests/test_models.py::test_recovery_cursor_allows_genesis_sentinel PASSED [ 45%]
tests/test_models.py::test_tip_record_empty_ledger_sentinel_is_supported PASSED [ 54%]
tests/test_models.py::test_typed_errors_expose_expected_codes[WritePathAppendError-WRITE_PATH_APPEND_ERROR] PASSED [ 63%]
tests/test_models.py::test_typed_errors_expose_expected_codes[WritePathFoldError-WRITE_PATH_FOLD_ERROR] PASSED [ 72%]
tests/test_models.py::test_typed_errors_expose_expected_codes[SnapshotWriteError-SNAPSHOT_WRITE_ERROR] PASSED [ 81%]
tests/test_models.py::test_typed_errors_expose_expected_codes[ReplayRecoveryError-REPLAY_RECOVERY_ERROR] PASSED [ 90%]
tests/test_models.py::test_doubles_implement_declared_protocols PASSED   [100%]

============================== 11 passed in 0.20s ==============================
```

Command:

```bash
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_system_events.py -v
```

Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Library/Developer/CommandLineTools/usr/bin/python3
cachedir: .pytest_cache
rootdir: /Users/raymondbruni/Cowork/Brain_Factory/staging/FMWK-002-write-path
plugins: anyio-4.12.1, asyncio-1.2.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 6 items

tests/test_system_events.py::test_build_session_start_request_sets_allowed_event_type PASSED [ 16%]
tests/test_system_events.py::test_build_session_start_request_uses_system_provenance PASSED [ 33%]
tests/test_system_events.py::test_build_session_end_request_sets_allowed_event_type PASSED [ 50%]
tests/test_system_events.py::test_build_session_end_request_preserves_reason PASSED [ 66%]
tests/test_system_events.py::test_build_snapshot_created_request_propagates_descriptor PASSED [ 83%]
tests/test_system_events.py::test_build_snapshot_created_request_uses_system_actor PASSED [100%]

============================== 6 passed in 0.21s ===============================
```

Command:

```bash
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_folds.py -v
```

Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Library/Developer/CommandLineTools/usr/bin/python3
cachedir: .pytest_cache
rootdir: /Users/raymondbruni/Cowork/Brain_Factory/staging/FMWK-002-write-path
plugins: anyio-4.12.1, asyncio-1.2.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 14 items

tests/test_folds.py::test_signal_delta_clamps_at_upper_bound PASSED      [  7%]
tests/test_folds.py::test_signal_delta_clamps_at_lower_bound PASSED      [ 14%]
tests/test_folds.py::test_signal_delta_updates_signal_accumulator PASSED [ 21%]
tests/test_folds.py::test_methylation_delta_updates_value_directly PASSED [ 28%]
tests/test_folds.py::test_methylation_delta_clamps_at_upper_bound PASSED [ 35%]
tests/test_folds.py::test_suppression_adds_scope_to_mask PASSED          [ 42%]
tests/test_folds.py::test_unsuppression_removes_scope_from_mask PASSED   [ 50%]
tests/test_folds.py::test_mode_change_sets_node_mode PASSED              [ 57%]
tests/test_folds.py::test_consolidation_creates_traceable_consolidated_node PASSED [ 64%]
tests/test_folds.py::test_node_creation_creates_initial_node PASSED      [ 71%]
tests/test_folds.py::test_system_events_do_not_apply_policy_side_effects PASSED [ 78%]
tests/test_folds.py::test_clamp_methylation_returns_midpoint_unchanged PASSED [ 85%]
tests/test_folds.py::test_clamp_methylation_clamps_below_zero PASSED     [ 92%]
tests/test_folds.py::test_clamp_methylation_clamps_above_one PASSED      [100%]

============================== 14 passed in 0.22s ==============================
```

Command:

```bash
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_service_mutations.py -v
```

Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Library/Developer/CommandLineTools/usr/bin/python3
cachedir: .pytest_cache
rootdir: /Users/raymondbruni/Cowork/Brain_Factory/staging/FMWK-002-write-path
plugins: anyio-4.12.1, asyncio-1.2.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 14 items

tests/test_service_mutations.py::test_submit_mutation_success_returns_receipt_after_fold PASSED [  7%]
tests/test_service_mutations.py::test_submit_mutation_appends_before_fold PASSED [ 14%]
tests/test_service_mutations.py::test_submit_mutation_immediate_visibility_after_success PASSED [ 21%]
tests/test_service_mutations.py::test_submit_mutation_append_failure_no_fold PASSED [ 28%]
tests/test_service_mutations.py::test_submit_mutation_fold_failure_returns_typed_error_and_boundary PASSED [ 35%]
tests/test_service_mutations.py::test_submit_mutation_blocks_further_writes_after_fold_failure PASSED [ 42%]
tests/test_service_mutations.py::test_submit_mutation_uses_appended_event_for_fold PASSED [ 50%]
tests/test_service_mutations.py::test_submit_mutation_preserves_event_hash_in_receipt PASSED [ 57%]
tests/test_service_mutations.py::test_submit_mutation_accepts_session_start_system_event PASSED [ 64%]
tests/test_service_mutations.py::test_submit_mutation_accepts_session_end_system_event PASSED [ 71%]
tests/test_service_mutations.py::test_submit_mutation_accepts_snapshot_created_system_event PASSED [ 78%]
tests/test_service_mutations.py::test_submit_mutation_records_durable_boundary_on_service PASSED [ 85%]
tests/test_service_mutations.py::test_submit_mutation_starts_unblocked_when_clean PASSED [ 92%]
tests/test_service_mutations.py::test_submit_mutation_append_failure_does_not_record_boundary PASSED [100%]

============================== 14 passed in 0.19s ==============================
```

Command:

```bash
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/test_recovery.py -v
```

Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Library/Developer/CommandLineTools/usr/bin/python3
cachedir: .pytest_cache
rootdir: /Users/raymondbruni/Cowork/Brain_Factory/staging/FMWK-002-write-path
plugins: anyio-4.12.1, asyncio-1.2.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 12 items

tests/test_recovery.py::test_create_snapshot_writes_artifact_before_snapshot_created PASSED [  8%]
tests/test_recovery.py::test_create_snapshot_hash_matches_payload PASSED [ 16%]
tests/test_recovery.py::test_create_snapshot_uses_current_tip_sequence PASSED [ 25%]
tests/test_recovery.py::test_create_snapshot_export_failure_raises_typed_error PASSED [ 33%]
tests/test_recovery.py::test_create_snapshot_fold_failure_surfaces_from_service PASSED [ 41%]
tests/test_recovery.py::test_recover_uses_post_snapshot_replay_only PASSED [ 50%]
tests/test_recovery.py::test_recover_without_snapshot_replays_from_genesis PASSED [ 58%]
tests/test_recovery.py::test_recover_unusable_snapshot_falls_back_to_full_replay PASSED [ 66%]
tests/test_recovery.py::test_recover_replay_failure_raises_typed_error PASSED [ 75%]
tests/test_recovery.py::test_refold_from_genesis_resets_graph_and_preserves_ledger PASSED [ 83%]
tests/test_recovery.py::test_refold_from_genesis_replays_through_tip PASSED [ 91%]
tests/test_recovery.py::test_service_recover_clears_durable_boundary_after_fold_failure PASSED [100%]

============================== 12 passed in 0.21s ==============================
```

Command:

```bash
cd staging/FMWK-002-write-path && PLATFORM_ENVIRONMENT=test pytest tests/ -v --tb=short
```

Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Library/Developer/CommandLineTools/usr/bin/python3
cachedir: .pytest_cache
rootdir: /Users/raymondbruni/Cowork/Brain_Factory/staging/FMWK-002-write-path
plugins: anyio-4.12.1, asyncio-1.2.0
asyncio: mode=strict, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 57 items

tests/test_folds.py::test_signal_delta_clamps_at_upper_bound PASSED      [  1%]
tests/test_folds.py::test_signal_delta_clamps_at_lower_bound PASSED      [  3%]
tests/test_folds.py::test_signal_delta_updates_signal_accumulator PASSED [  5%]
tests/test_folds.py::test_methylation_delta_updates_value_directly PASSED [  7%]
tests/test_folds.py::test_methylation_delta_clamps_at_upper_bound PASSED [  8%]
tests/test_folds.py::test_suppression_adds_scope_to_mask PASSED          [ 10%]
tests/test_folds.py::test_unsuppression_removes_scope_from_mask PASSED   [ 12%]
tests/test_folds.py::test_mode_change_sets_node_mode PASSED              [ 14%]
tests/test_folds.py::test_consolidation_creates_traceable_consolidated_node PASSED [ 15%]
tests/test_folds.py::test_node_creation_creates_initial_node PASSED      [ 17%]
tests/test_folds.py::test_system_events_do_not_apply_policy_side_effects PASSED [ 19%]
tests/test_folds.py::test_clamp_methylation_returns_midpoint_unchanged PASSED [ 21%]
tests/test_folds.py::test_clamp_methylation_clamps_below_zero PASSED     [ 22%]
tests/test_folds.py::test_clamp_methylation_clamps_above_one PASSED      [ 24%]
tests/test_models.py::test_mutation_request_preserves_fields PASSED      [ 26%]
tests/test_models.py::test_mutation_request_asdict_includes_optional_pack_id PASSED [ 28%]
tests/test_models.py::test_mutation_receipt_represents_folded_success PASSED [ 29%]
tests/test_models.py::test_snapshot_descriptor_preserves_boundary_metadata PASSED [ 31%]
tests/test_models.py::test_recovery_cursor_allows_genesis_sentinel PASSED [ 33%]
tests/test_models.py::test_tip_record_empty_ledger_sentinel_is_supported PASSED [ 35%]
tests/test_models.py::test_typed_errors_expose_expected_codes[WritePathAppendError-WRITE_PATH_APPEND_ERROR] PASSED [ 36%]
tests/test_models.py::test_typed_errors_expose_expected_codes[WritePathFoldError-WRITE_PATH_FOLD_ERROR] PASSED [ 38%]
tests/test_models.py::test_typed_errors_expose_expected_codes[SnapshotWriteError-SNAPSHOT_WRITE_ERROR] PASSED [ 40%]
tests/test_models.py::test_typed_errors_expose_expected_codes[ReplayRecoveryError-REPLAY_RECOVERY_ERROR] PASSED [ 42%]
tests/test_models.py::test_doubles_implement_declared_protocols PASSED   [ 43%]
tests/test_recovery.py::test_create_snapshot_writes_artifact_before_snapshot_created PASSED [ 45%]
tests/test_recovery.py::test_create_snapshot_hash_matches_payload PASSED [ 47%]
tests/test_recovery.py::test_create_snapshot_uses_current_tip_sequence PASSED [ 49%]
tests/test_recovery.py::test_create_snapshot_export_failure_raises_typed_error PASSED [ 50%]
tests/test_recovery.py::test_create_snapshot_fold_failure_surfaces_from_service PASSED [ 52%]
tests/test_recovery.py::test_recover_uses_post_snapshot_replay_only PASSED [ 54%]
tests/test_recovery.py::test_recover_without_snapshot_replays_from_genesis PASSED [ 56%]
tests/test_recovery.py::test_recover_unusable_snapshot_falls_back_to_full_replay PASSED [ 57%]
tests/test_recovery.py::test_recover_replay_failure_raises_typed_error PASSED [ 59%]
tests/test_recovery.py::test_refold_from_genesis_resets_graph_and_preserves_ledger PASSED [ 61%]
tests/test_recovery.py::test_refold_from_genesis_replays_through_tip PASSED [ 63%]
tests/test_recovery.py::test_service_recover_clears_durable_boundary_after_fold_failure PASSED [ 64%]
tests/test_service_mutations.py::test_submit_mutation_success_returns_receipt_after_fold PASSED [ 66%]
tests/test_service_mutations.py::test_submit_mutation_appends_before_fold PASSED [ 68%]
tests/test_service_mutations.py::test_submit_mutation_immediate_visibility_after_success PASSED [ 70%]
tests/test_service_mutations.py::test_submit_mutation_append_failure_no_fold PASSED [ 71%]
tests/test_service_mutations.py::test_submit_mutation_fold_failure_returns_typed_error_and_boundary PASSED [ 73%]
tests/test_service_mutations.py::test_submit_mutation_blocks_further_writes_after_fold_failure PASSED [ 75%]
tests/test_service_mutations.py::test_submit_mutation_uses_appended_event_for_fold PASSED [ 77%]
tests/test_service_mutations.py::test_submit_mutation_preserves_event_hash_in_receipt PASSED [ 78%]
tests/test_service_mutations.py::test_submit_mutation_accepts_session_start_system_event PASSED [ 80%]
tests/test_service_mutations.py::test_submit_mutation_accepts_session_end_system_event PASSED [ 82%]
tests/test_service_mutations.py::test_submit_mutation_accepts_snapshot_created_system_event PASSED [ 84%]
tests/test_service_mutations.py::test_submit_mutation_records_durable_boundary_on_service PASSED [ 85%]
tests/test_service_mutations.py::test_submit_mutation_starts_unblocked_when_clean PASSED [ 87%]
tests/test_service_mutations.py::test_submit_mutation_append_failure_does_not_record_boundary PASSED [ 89%]
tests/test_system_events.py::test_build_session_start_request_sets_allowed_event_type PASSED [ 91%]
tests/test_system_events.py::test_build_session_start_request_uses_system_provenance PASSED [ 92%]
tests/test_system_events.py::test_build_session_end_request_sets_allowed_event_type PASSED [ 94%]
tests/test_system_events.py::test_build_session_end_request_preserves_reason PASSED [ 96%]
tests/test_system_events.py::test_build_snapshot_created_request_propagates_descriptor PASSED [ 98%]
tests/test_system_events.py::test_build_snapshot_created_request_uses_system_actor PASSED [100%]

============================== 57 passed in 0.19s ==============================
```

## Session Log

1. Read `AGENT_BOOTSTRAP.md`, `D10_AGENT_CONTEXT.md`, `Templates/TDD_AND_DEBUGGING.md`, `BUILDER_HANDOFF.md`, approved `13Q_ANSWERS.md`, and `REVIEW_REPORT.md`.
2. Read D2/D3/D4/D6 plus reference package and relevant `platform_sdk` modules before implementation.
3. Wrote tests first for models, system events, folds, service, and recovery.
4. Ran red phases and implemented minimum code to satisfy each behavior.
5. Fixed Python 3.9 type-union parsing issues exposed during green.
6. Ran the exact staged verification commands and captured their output.
7. Wrote this results file and prepared builder evidence.
