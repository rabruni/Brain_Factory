# DoPeJarMo System Topology — dopejar Catalog

> Reference copy of `/Users/raymondbruni/dopejar/catalog-info.yaml` so agents
> can read system topology during builds without leaving Brain_Factory.

## Entities

| Kind | Name | Type | Description |
|------|------|------|-------------|
| Component | `platform-sdk` | library | 46 modules across 5 tiers. Single import path for all infrastructure. |
| Component | `kernel` | service | Cognitive kernel — WebSocket server hosting all nine primitives. |
| API | `kernel-websocket-api` | websocket | `/operator` (agent shell), `/user` (conversational AI), `/health`. |
| API | `platform-sdk-mcp-api` | mcp | MCP server exposing SDK tools for AI agents. |
| Resource | `ledger-immudb` | database | Append-only hash-chained truth store (immudb gRPC :3322). |
| Resource | `zitadel-identity` | identity-provider | OIDC auth, JWT issuance, authorization API. |
| Resource | `ollama-inference` | ai-runtime | Local LLM for HO1 internal calls (Metal GPU). |

## Dependency Graph

```
platform-sdk ──dependsOn──→ ledger-immudb
                          ──→ zitadel-identity
                          ──→ ollama-inference

kernel ──dependsOn──→ ledger-immudb
                   ──→ zitadel-identity
                   ──→ ollama-inference
       ──providesApis──→ kernel-websocket-api

brain-factory ──consumesApis──→ platform-sdk-mcp-api
              ──dependsOn──→ platform-sdk
              ──dependsOn──→ kernel
```

## Local Paths

| What | Path |
|------|------|
| dopejar repo | `/Users/raymondbruni/dopejar/` |
| Platform SDK | `/Users/raymondbruni/dopejar/platform_sdk/` |
| Docker services | `/Users/raymondbruni/dopejar/docker-compose.yml` |
| dopejar catalog | `/Users/raymondbruni/dopejar/catalog-info.yaml` |
| Brain_Factory catalog | `catalog-info.yaml` (this repo) |
