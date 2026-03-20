# Portal Kit — Build Agent Observability for Any System

This document tells you how to build a complete agent observability portal
for any agentic system. It was extracted from the DoPeJarMo Brain Factory
portal. An agent reading this document has everything it needs to replicate
the experience.

## What You Get

A Streamlit web UI + MCP server that provides:

1. **Activity Feed** — unified timeline of pipeline runs, agent conversations, and git activity
2. **Workflow View** — pipeline runs with mermaid flow diagrams showing stage progression
3. **Trace Tree** — parent→child execution hierarchy for debugging
4. **Conversation Viewer** — browse transcripts from any AI CLI (Claude, Codex, Gemini, or custom)
5. **File Explorer** — browse the repo exactly as agents see it
6. **System Catalog** — Backstage entities showing topology, APIs, and dependencies
7. **Latest Changes** — git working tree state with clickable file viewing

All views read directly from disk. No build step, no sync. What humans see is what agents see.

## Prerequisites

- Python 3.9+
- `pip install streamlit pyyaml`
- Git repo
- (Optional) Backstage for system catalog
- (Optional) Cloudflare tunnel for external access

## Step 1: Create the Config

Create `portal_config.yaml` in your repo root:

```yaml
system_name: "Your System Name"
repo_root: "."   # or absolute path

pipeline:
  name: "your-pipeline"        # human-readable name
  runs_dir: "pipeline/runs"    # where run directories live
  run_dir_prefix: ""           # prefix filter for run dirs (empty = all)
  events_file: "events.jsonl"  # name of the event log per run
  status_file: "status.json"   # name of the status file per run

conversations:
  # Map CLI name → directory containing transcript files
  # Supported formats: .jsonl (Claude/Codex style), .json (Gemini style)
  claude: "~/.claude/projects/YOUR_PROJECT"
  codex: "~/.codex/sessions"
  # gemini: "~/.gemini/tmp"
  # custom: "/path/to/your/transcripts"

catalog_files:
  # Backstage catalog-info.yaml files (optional)
  - "catalog-info.yaml"
  # - "/path/to/other/catalog-info.yaml"
```

## Step 2: Pipeline Event Format

Your pipeline must write `events.jsonl` — one JSON object per line:

```json
{
  "event_id": "unique-id",
  "causal_parent_event_id": "parent-id-or-null",
  "event_type": "step_started",
  "role": "agent-name",
  "turn": "stage-name",
  "outcome": "started|passed|failed|complete",
  "summary": "Human-readable description",
  "timestamp": "2026-03-18T05:14:06Z",
  "evidence_refs": ["path/to/output.log"],
  "contract_refs": ["path/to/input/spec.md"]
}
```

**Required fields:** `event_id`, `event_type`, `timestamp`, `summary`

**For trace trees:** include `causal_parent_event_id` linking child events to parents.

**For workflow diagrams:** include `turn` (stage name) and `outcome`.

**For artifact linking:** include `evidence_refs` and `contract_refs` as arrays of relative file paths.

Your pipeline should also write `status.json` per run:

```json
{
  "state": "running|passed|failed",
  "current_turn": "stage-name",
  "current_role": "agent-name",
  "run_id": "run-identifier"
}
```

## Step 3: Conversation Transcript Format

The portal supports three transcript formats natively:

### Claude (.jsonl)
```json
{"type": "user", "message": {"content": "user text"}, "timestamp": "..."}
{"type": "assistant", "message": {"content": [{"type": "text", "text": "..."}]}}
{"type": "tool_result", "content": "..."}
```

### Codex (.jsonl)
```json
{"type": "session_meta", "payload": {"timestamp": "...", "cwd": "..."}}
{"type": "response_item", "payload": {"role": "user|assistant", "content": [...]}}
```

### Gemini (.json)
```json
{"messages": [{"type": "user|model|tool", "content": [{"text": "..."}]}]}
```

### Custom format
Add a `render_custom_transcript()` function to `portal.py` following the pattern
of the existing renderers. Each renderer extracts user messages, assistant messages,
and tool calls from the CLI-specific format and renders them as chat messages.

## Step 4: Copy and Adapt portal.py

Copy `portal.py` from Brain Factory. Modify:

1. **Paths section** — update `BRAIN`, `SAWMILL`, `ARCHITECTURE`, `AGENTS`, transcript paths
2. **Sidebar pages** — remove pages that don't apply, add system-specific ones
3. **Pipeline discovery** — update `discover_all_runs()` and `load_run_events()` to match your directory structure
4. **Conversation discovery** — update or add discover functions for your CLI transcripts

The portal is ~900 lines. Most of it is generic. The system-specific parts are:
- Path constants (lines 18-27)
- Catalog file list (lines 30-36)
- Conversation discovery functions (lines 180-280)
- Mermaid diagram generation in the Workflow view (turn names, stage semantics)

## Step 5: Copy and Adapt mcp_portal.py

Copy `mcp_portal.py`. Modify `DEFAULT_CONFIG` to match your system, or use `--config`:

```bash
python3 mcp_portal.py --config portal_config.yaml
```

The MCP server exposes the same data the portal reads. Register it in your
Claude Code settings:

```json
{
  "mcpServers": {
    "portal": {
      "command": "python3",
      "args": ["/path/to/mcp_portal.py", "--config", "/path/to/portal_config.yaml"]
    }
  }
}
```

### Workspace Protocol

If you copy the Brain Factory workspace system, document and preserve these
runtime rules:

- Status model: `sent -> read -> complete`
- Only humans can mark items `complete`
- Agents must reply after marking an item `read`
- Items read without a reply show up in `needs_response` on heartbeat
- All replies must include `reply_to` so the conversation stays threaded

Recommended HTTP flow for remote agents:

1. Create a token in the portal UI.
2. Onboard with `POST /onboard`.
3. Start polling `POST /heartbeat` every 30 seconds.
4. If `new_work` is non-empty, immediately mark the item `read`, fetch it, execute it, and reply in-thread.

Every direct HTTP call to `/heartbeat` or `/tools/*` should include the same
agent token, either in the JSON body:

```json
{"agent_token": "your-token"}
```

or as an `Authorization: Bearer your-token` header.

For a reply, post a new workspace item instead of mutating the original:

```json
{
  "type": "results",
  "to": "requesting-agent",
  "summary": "what you completed",
  "content": "full response",
  "reply_to": "workspace-item-id",
  "agent_token": "your-token"
}
```

This keeps the portal UI, heartbeat contract, and audit log aligned around one
conversation primitive: threaded workspace items.

## Step 6: Register in Backstage (Optional)

Add to your `catalog-info.yaml`:

```yaml
---
apiVersion: backstage.io/v1alpha1
kind: API
metadata:
  name: your-system-portal-mcp-api
  description: Portal MCP server for your system
  tags: [mcp, portal, observability]
spec:
  type: mcp
  owner: your-team
  lifecycle: production
  system: your-system
  definition:
    $text: apis/portal-mcp.yaml
```

## Step 7: Cloudflare Tunnel (Optional)

To expose the portal externally:

```bash
cloudflared tunnel route dns YOUR_TUNNEL portal.yourdomain.com
```

Add to `/etc/cloudflared/config.yml`:

```yaml
- hostname: portal.yourdomain.com
  service: http://localhost:8501
  originRequest:
    httpHostHeader: localhost
```

Start Streamlit with external access flags:

```bash
streamlit run portal.py --server.headless true --server.enableCORS false \
  --server.enableXsrfProtection false --server.address 0.0.0.0
```

## Architecture

```
Source files on disk (git-tracked, auditable)
              │
    ┌─────────┴─────────┐
    ▼                    ▼
Streamlit Portal    MCP Server
(humans browse)    (agents query)
    │                    │
    │              ┌─────┴─────┐
    ▼              ▼           ▼
  Browser      Claude      Codex/Gemini
              (MCP tools)  (MCP tools)
```

Both surfaces read the same files. No transformation layer. No sync.
The MCP server is the reusable component. The Streamlit portal is one frontend.

## System Catalog (without Backstage)

You do NOT need to install Backstage. The portal reads `catalog-info.yaml` files
directly from disk. Backstage is just a web UI on top of those same YAML files.

### What the catalog gives you

The System Catalog page in the portal shows:
- **Components** — what services/libraries exist, who owns them
- **APIs** — machine-readable specs (OpenAPI, AsyncAPI, MCP tool definitions)
- **Resources** — databases, identity providers, inference runtimes
- **Dependencies** — what depends on what

Agents query the same data via the MCP server's `list_catalog_entities` and
`get_api_spec` tools.

### Create your catalog

Create `catalog-info.yaml` in your repo root. Use Backstage's entity format —
it's just YAML, no runtime needed:

```yaml
# System — the top-level grouping
---
apiVersion: backstage.io/v1alpha1
kind: System
metadata:
  name: your-system
  description: What this system does
spec:
  owner: your-team

# Component — a service, library, or application
---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: your-service
  description: What this service does
  tags: [python, api]
spec:
  type: service          # service | library | website
  owner: your-team
  lifecycle: production
  system: your-system
  providesApis:
    - your-api
  dependsOn:
    - resource:your-database

# API — a machine-readable interface definition
---
apiVersion: backstage.io/v1alpha1
kind: API
metadata:
  name: your-api
  description: What this API does
  tags: [rest, mcp]
spec:
  type: openapi          # openapi | asyncapi | mcp | grpc
  owner: your-team
  lifecycle: production
  system: your-system
  definition:
    $text: apis/your-api.yaml    # path to spec file

# Resource — infrastructure dependency
---
apiVersion: backstage.io/v1alpha1
kind: Resource
metadata:
  name: your-database
  description: What this database stores
spec:
  type: database
  owner: your-team
  lifecycle: production
  system: your-system
```

### API spec files

Put machine-readable specs in an `apis/` directory:

- **REST APIs** → OpenAPI YAML (`apis/your-api.openapi.yaml`)
- **WebSocket APIs** → AsyncAPI YAML (`apis/your-api.asyncapi.yaml`)
- **MCP servers** → Tool definition YAML (`apis/your-mcp.yaml`):

```yaml
mcp_version: "1.0"
server:
  name: your-mcp-server
  command: "python3 your_mcp_server.py"
tools:
  - name: tool_name
    description: What this tool does
    parameters:
      - name: param_name
        type: string
        required: true
        description: What this parameter is
```

The portal renders these specs inline when you view an API entity.
Agents read them via `get_api_spec` to discover what tools are available.

### If you already have Backstage

Keep it. Register the portal MCP server as an API entity (see Step 6).
The portal reads the same catalog YAML files Backstage reads — they stay in sync
because they're the same files.

### If you don't have Backstage

Don't install it. The catalog-info.yaml files + the portal + the MCP server
give you everything Backstage provides except the web UI. The portal IS your
web UI. The MCP server IS your API.

## Serving the Kit to Remote Systems

If the target system only has network access (no shared filesystem), run the
MCP server in HTTP mode:

```bash
python3 mcp_portal.py --http --port 8502
```

This serves:
- `GET /` — server info and full tool list
- `GET /kit` — list of downloadable kit files
- `GET /kit/PORTAL_KIT.md` — this document
- `GET /kit/portal.py` — portal template
- `GET /kit/mcp_portal.py` — MCP server template
- `GET /kit/portal_config.template.yaml` — blank config
- `GET /kit/catalog-info.yaml` — catalog template
- `POST /tools/<name>` — call any tool with JSON body
- `POST /mcp` — full MCP JSON-RPC endpoint

To bootstrap a new system from a remote kit server:

```
1. Fetch https://mcp.yourdomain.com/kit/PORTAL_KIT.md     → read the instructions
2. Fetch https://mcp.yourdomain.com/kit/portal.py           → save as portal.py
3. Fetch https://mcp.yourdomain.com/kit/mcp_portal.py       → save as mcp_portal.py
4. Fetch https://mcp.yourdomain.com/kit/portal_config.template.yaml → save as portal_config.yaml
5. Edit portal_config.yaml for your system
6. pip install streamlit pyyaml
7. streamlit run portal.py
```

No private data crosses the network. Only the code templates and instructions.

## What to Tell the Agent

If you're handing this to an agent on another system, the prompt is:

> "Fetch the portal kit from https://mcp.yourdomain.com/kit/PORTAL_KIT.md
> and follow its instructions. Download all kit files from /kit/. Create a
> portal_config.yaml for this system. Adapt portal.py and mcp_portal.py per
> the kit. The goal is a Streamlit portal that shows our pipeline runs,
> agent conversations, and system catalog."

The agent reads the kit, downloads the templates, creates the config, and builds.
No human intervention needed beyond the initial prompt.

## What Makes This Work

1. **Disk is the source of truth** — no database, no API layer between data and viewer
2. **Event logs are append-only** — `events.jsonl` per run, one line per event
3. **Trace trees from causal links** — `causal_parent_event_id` gives you debugging hierarchy for free
4. **Artifacts are file paths** — `evidence_refs` and `contract_refs` point to real files you can read
5. **Config-driven** — one YAML file adapts the whole system to a new project
6. **Paginated at the data level** — discover runs cheaply, load events only when displayed
7. **No Backstage runtime needed** — catalog YAML files work standalone
8. **Portable over HTTP** — kit files served by the MCP server itself
