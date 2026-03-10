# Sawmill Role Registry

This page exposes the Sawmill role registry in a standard TechDocs-rendered
format.

The filesystem source of truth remains:

- `sawmill/ROLE_REGISTRY.yaml`

The passive portal mirror is:

- [docs/sawmill/ROLE_REGISTRY.yaml](ROLE_REGISTRY.yaml)

## What It Defines

The registry is the canonical role/backend map for Sawmill runtime routing.
Each role entry defines:

- `role_file`
- `execution_scope`
- `default_backend`
- `allowed_backends`
- `env_override`

## Notes

- The portal does not own or edit the registry.
- `run.sh` consumes the filesystem source of truth at runtime.
- The YAML mirror exists so humans can inspect the exact registry content from
  TechDocs without guessing.
