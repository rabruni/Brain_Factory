HS-002: schemas.py validate_payload("node_creation") rejects holdout payload — requires initial_state (Mapping) but holdout provides {node_id, node_type, subject_id} only
HS-004: schemas.py validate_payload("package_install") rejects holdout payload — requires framework_id/install_scope/manifest_hash but holdout provides {package_id, version, action} only
HS-003: schemas.py validate_payload("package_install") rejects holdout payload — same root cause as HS-004
