# Platform SDK Architecture Diagrams

> Visual reference for the DoPeJar platform SDK (46 modules, 5 tiers) and MCP server.

---

## 1. Tier Architecture

The SDK is a strict 5-tier layer cake. Each tier may only import from tiers below it.

```mermaid
flowchart TB
    subgraph tier0["tier0_core (8 modules)"]
        direction LR
        identity[identity]
        logging[logging]
        errors[errors]
        config[config]
        secrets[secrets]
        data[data]
        metrics[metrics]
        ledger[ledger]
    end

    subgraph tier1["tier1_runtime (6 modules)"]
        direction LR
        context[context]
        validate[validate]
        serialize[serialize]
        retry[retry]
        ratelimit[ratelimit]
        middleware[middleware]
    end

    subgraph tier2["tier2_reliability (3 modules)"]
        direction LR
        health[health]
        audit[audit]
        cache[cache]
    end

    subgraph tier3["tier3_platform (3 modules)"]
        direction LR
        authorization[authorization]
        notifications[notifications]
        vector[vector]
    end

    subgraph tier4["tier4_advanced (2 modules)"]
        direction LR
        inference[inference]
        llm_obs[llm_obs]
    end

    tier4 --> tier3
    tier3 --> tier2
    tier2 --> tier1
    tier1 --> tier0

    style tier0 fill:#e8f5e9,stroke:#2e7d32
    style tier1 fill:#e3f2fd,stroke:#1565c0
    style tier2 fill:#fff3e0,stroke:#e65100
    style tier3 fill:#f3e5f5,stroke:#6a1b9a
    style tier4 fill:#fce4ec,stroke:#b71c1c
```

**Takeaway**: Imports flow strictly downward. A tier2 module can use tier1 and tier0, never tier3 or tier4.

---

## 2. Entry Surfaces

Two public APIs gate access to the SDK: a narrow agent surface and a wide service surface.

```mermaid
flowchart LR
    subgraph agent["agent.py (12 exports)"]
        direction TB
        a1[complete]
        a2[embed]
        a3[Message]
        a4[observe]
        a5[get_llm_tracer]
        a6[record_inference]
        a7[vector_search]
        a8[vector_upsert]
        a9[vector_delete]
        a10[get_logger]
        a11[PlatformError]
        a12[RateLimitError<br/>UpstreamError]
    end

    subgraph service["service.py (~40 exports)"]
        direction TB
        s1[everything in agent.py]
        s2[identity / config / secrets]
        s3[data / ledger / metrics]
        s4[context / validate / serialize]
        s5[retry / ratelimit / middleware]
        s6[health / audit / cache]
        s7[authz / notifications]
    end

    agent -- "subset of" --> service

    subgraph consumers["Consumers"]
        ai[AI Agents]
        be[Backend Services]
    end

    ai --> agent
    be --> service

    style agent fill:#e3f2fd,stroke:#1565c0
    style service fill:#fff3e0,stroke:#e65100
```

**Takeaway**: Agents get 12 safe symbols. Services get the full SDK. The agent boundary is intentional — it limits what AI can reach.

---

## 3. Provider Protocol Pattern

Five provider families follow the same pattern: a Protocol defines the interface, concrete implementations fulfill it, and an env var selects which one runs.

```mermaid
classDiagram
    class IdentityProvider {
        <<Protocol>>
        +authenticate()
        +get_principal()
    }
    class MockIdentity {
        +authenticate()
        +get_principal()
    }
    class ZitadelIdentity {
        +authenticate()
        +get_principal()
    }
    class Auth0Identity {
        +authenticate()
        +get_principal()
    }
    IdentityProvider <|.. MockIdentity
    IdentityProvider <|.. ZitadelIdentity
    IdentityProvider <|.. Auth0Identity

    class LedgerProvider {
        <<Protocol>>
        +append()
        +verify_chain()
        +get_tip()
    }
    class MockLedger {
        +append()
        +verify_chain()
        +get_tip()
    }
    class ImmudbLedger {
        +append()
        +verify_chain()
        +get_tip()
    }
    LedgerProvider <|.. MockLedger
    LedgerProvider <|.. ImmudbLedger

    class AuthzProvider {
        <<Protocol>>
        +check()
        +grant()
    }
    class SimpleAuthz {
        +check()
        +grant()
    }
    class SpiceDBAuthz {
        +check()
        +grant()
    }
    AuthzProvider <|.. SimpleAuthz
    AuthzProvider <|.. SpiceDBAuthz

    class InferenceProvider {
        <<Protocol>>
        +complete()
        +embed()
    }
    class MockInference {
        +complete()
        +embed()
    }
    class LiteLLMInference {
        +complete()
        +embed()
    }
    InferenceProvider <|.. MockInference
    InferenceProvider <|.. LiteLLMInference

    class VectorProvider {
        <<Protocol>>
        +search()
        +upsert()
    }
    class MemoryVector {
        +search()
        +upsert()
    }
    class QdrantVector {
        +search()
        +upsert()
    }
    VectorProvider <|.. MemoryVector
    VectorProvider <|.. QdrantVector
```

| Protocol | Env Var | Default |
|----------|---------|---------|
| IdentityProvider | `PLATFORM_IDENTITY_PROVIDER` | Mock |
| LedgerProvider | `PLATFORM_LEDGER_BACKEND` | Mock |
| AuthzProvider | `PLATFORM_AUTHZ_BACKEND` | Simple |
| InferenceProvider | `PLATFORM_INFERENCE_PROVIDER` | Mock |
| VectorProvider | `PLATFORM_VECTOR_BACKEND` | Memory |

**Takeaway**: Every external dependency is behind a Protocol. Mock implementations exist for every provider, enabling full offline testing.

---

## 4. Shared Interfaces

Four types cross tier boundaries. They are defined low and consumed high.

```mermaid
flowchart LR
    subgraph defines["Defined In"]
        PC[PlatformConfig<br/>tier0 config]
        PE[PlatformError<br/>+ 9 subtypes<br/>tier0 errors]
        PR[Principal<br/>tier0 identity]
        RC[RequestContext<br/>tier1 context]
        LE[LedgerEntry<br/>tier0 ledger]
    end

    subgraph consumes["Consumed By"]
        all_tiers[all tiers]
        t1_ctx[tier1 context]
        t2_aud[tier2 audit]
        t3_authz[tier3 authz]
        t3_notif[tier3 notifications]
        t4_obs[tier4 llm_obs]
        t4_inf[tier4 inference]
        t2_health[tier2 health]
    end

    PC --> all_tiers
    PE --> all_tiers
    PR --> t1_ctx
    PR --> t2_aud
    PR --> t3_authz
    PR --> t3_notif
    PR --> t4_obs
    RC --> t2_aud
    RC --> t2_health
    RC --> t3_authz
    RC --> t4_obs
    RC --> t4_inf
    LE --> t4_obs

    style defines fill:#e8f5e9,stroke:#2e7d32
    style consumes fill:#e3f2fd,stroke:#1565c0
```

**Takeaway**: `PlatformConfig` and `PlatformError` are universal. `Principal` and `RequestContext` thread identity and request state upward through the tiers.

---

## 5. Request Flow

An HTTP request through the full middleware stack, showing how each tier contributes.

```mermaid
sequenceDiagram
    participant Client
    participant Middleware as middleware<br/>(tier1)
    participant Identity as identity<br/>(tier0)
    participant Context as context<br/>(tier1)
    participant Validate as validate<br/>(tier1)
    participant Audit as audit<br/>(tier2)
    participant Authz as authz<br/>(tier3)
    participant Inference as inference<br/>(tier4)

    Client->>Middleware: HTTP request
    Middleware->>Identity: authenticate(token)
    Identity-->>Middleware: Principal
    Middleware->>Context: build(Principal, request)
    Context-->>Middleware: RequestContext
    Middleware->>Validate: validate(request body)
    Validate-->>Middleware: validated input
    Middleware->>Audit: audit_event(RequestContext, action)
    Middleware->>Authz: check(Principal, resource, action)
    Authz-->>Middleware: allowed / denied
    Middleware->>Inference: complete(prompt, RequestContext)
    Inference-->>Middleware: response
    Middleware-->>Client: HTTP response
```

**Takeaway**: Identity establishes who. Context captures what. Validate checks input. Audit records the action. Authz gates access. Inference does the work.

---

## 6. MCP Server Tools

The MCP server discovers tools at startup via `__sdk_export__["mcp_tools"]` in each module.

```mermaid
flowchart TB
    subgraph mcp["mcp_server.py"]
        server[MCP Server<br/>stdio transport]
        registry[_registry<br/>module scanner]
    end

    server --> registry

    subgraph tier0_tools["tier0_core"]
        log_event["log_event<br/>(logging)"]
        emit_metric["emit_metric<br/>(metrics)"]
        get_secret["get_secret<br/>(secrets)"]
        append_turn["append_turn<br/>(ledger)"]
    end

    subgraph tier1_tools["tier1_runtime"]
        check_rate_limit["check_rate_limit<br/>(ratelimit)"]
    end

    subgraph tier2_tools["tier2_reliability"]
        audit_event["audit_event<br/>(audit)"]
        check_health["check_health<br/>(health)"]
    end

    subgraph tier3_tools["tier3_platform"]
        query_vector["query_vector<br/>(vector)"]
        upsert_vector["upsert_vector<br/>(vector)"]
    end

    subgraph tier4_tools["tier4_advanced"]
        call_inference["call_inference<br/>(inference)"]
        embed_text["embed_text<br/>(inference)"]
    end

    registry --> tier0_tools
    registry --> tier1_tools
    registry --> tier2_tools
    registry --> tier3_tools
    registry --> tier4_tools

    subgraph surface["Entry Surface"]
        agent_surf[agent surface]
        service_surf[service surface]
    end

    log_event -.- agent_surf
    call_inference -.- agent_surf
    embed_text -.- agent_surf
    query_vector -.- agent_surf
    upsert_vector -.- agent_surf
    emit_metric -.- service_surf
    get_secret -.- service_surf
    append_turn -.- service_surf
    check_rate_limit -.- service_surf
    audit_event -.- service_surf
    check_health -.- service_surf

    style mcp fill:#f5f5f5,stroke:#424242
    style tier0_tools fill:#e8f5e9,stroke:#2e7d32
    style tier1_tools fill:#e3f2fd,stroke:#1565c0
    style tier2_tools fill:#fff3e0,stroke:#e65100
    style tier3_tools fill:#f3e5f5,stroke:#6a1b9a
    style tier4_tools fill:#fce4ec,stroke:#b71c1c
    style surface fill:#fff9c4,stroke:#f9a825
```

**Takeaway**: 11 tools across 8 modules. 5 tools on the agent surface, 6 on the service surface. The MCP server uses stdio transport and discovers tools from `__sdk_export__` metadata.

---

## 7. Runtime Topology

How the SDK sits in the deployed system: shared by the host and Docker containers.

```mermaid
flowchart TB
    subgraph host["Host Machine"]
        claude[Claude Desktop]
        mcp[MCP Server<br/>stdio]
        ollama[Ollama<br/>local inference]
    end

    subgraph docker["Docker Compose"]
        kernel[Kernel<br/>FastAPI]
        immudb[(immudb<br/>ledger store)]
        zitadel[Zitadel<br/>identity]
    end

    subgraph sdk["platform_sdk (shared)"]
        agent_api[agent.py]
        service_api[service.py]
        tiers[5 tiers<br/>22 registered modules]
    end

    claude --> mcp
    mcp --> sdk
    kernel --> sdk
    kernel --> immudb
    kernel --> zitadel
    ollama -.- sdk

    agent_api --> tiers
    service_api --> tiers

    style host fill:#e3f2fd,stroke:#1565c0
    style docker fill:#fff3e0,stroke:#e65100
    style sdk fill:#e8f5e9,stroke:#2e7d32
```

**Takeaway**: The platform SDK is the shared layer. Claude Desktop reaches it via MCP. The kernel reaches it directly. Docker provides the stateful backends (immudb for ledger, Zitadel for identity).
