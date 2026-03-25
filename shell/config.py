from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAWMILL_DIR = ROOT / "sawmill"
STAGING_DIR = ROOT / "staging"
ROLE_REGISTRY_PATH = SAWMILL_DIR / "ROLE_REGISTRY.yaml"
LAUNCH_MANIFEST_FILENAME = "launch_manifest.json"
BLUEPRINT_FILES = [
    "D1_CONSTITUTION.md",
    "D2_SPECIFICATION.md",
    "D3_DATA_MODEL.md",
    "D4_CONTRACTS.md",
    "D5_RESEARCH.md",
    "D6_GAP_ANALYSIS.md",
]

ACTIVE_RUN_STATES = {"running", "retrying"}
ACTIVE_HEARTBEAT_SECONDS = 600

CLAUDE_MODELS = [
    {"id": "claude-opus-4-6", "name": "Opus 4.6", "context": 1_000_000, "max_output": 128_000},
    {"id": "claude-sonnet-4-6", "name": "Sonnet 4.6", "context": 1_000_000, "max_output": 64_000},
    {"id": "claude-opus-4-5", "name": "Opus 4.5", "context": 200_000, "max_output": 64_000},
    {"id": "claude-sonnet-4-5", "name": "Sonnet 4.5", "context": 200_000, "max_output": 64_000},
    {"id": "claude-haiku-4-5", "name": "Haiku 4.5", "context": 200_000, "max_output": 64_000},
]
CLAUDE_EFFORTS = ["low", "medium", "high", "max"]

OPENAI_MODELS = [
    {"id": "gpt-5.4", "name": "GPT-5.4", "context": 1_050_000, "max_output": 128_000},
    {"id": "gpt-5.4-mini", "name": "GPT-5.4 Mini", "context": 400_000, "max_output": 128_000},
    {"id": "gpt-5.4-nano", "name": "GPT-5.4 Nano", "context": 400_000, "max_output": 128_000},
    {"id": "o3", "name": "o3", "context": 200_000, "max_output": 100_000},
    {"id": "o3-mini", "name": "o3 Mini", "context": 200_000, "max_output": 100_000},
    {"id": "o4-mini", "name": "o4 Mini", "context": 200_000, "max_output": 100_000},
    {"id": "gpt-4.1", "name": "GPT-4.1", "context": 1_000_000, "max_output": 32_768},
    {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini", "context": 1_000_000, "max_output": 32_768},
    {"id": "gpt-4.1-nano", "name": "GPT-4.1 Nano", "context": 1_000_000, "max_output": 32_768},
    {"id": "gpt-4o", "name": "GPT-4o", "context": 128_000, "max_output": 16_000},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "context": 128_000, "max_output": 16_000},
]

GEMINI_MODELS = [
    {"id": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro Preview", "context": 1_000_000, "max_output": 64_000},
    {"id": "gemini-3-flash-preview", "name": "Gemini 3 Flash Preview", "context": 1_000_000, "max_output": 64_000},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "context": 1_048_576, "max_output": 65_536},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "context": 1_048_576, "max_output": 65_536},
    {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash-Lite", "context": 1_048_576, "max_output": 65_536},
    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "context": 1_000_000, "max_output": 8_192},
]

CODEX_MODELS = OPENAI_MODELS

FWK_REGISTRY = {
    "FWK-0": {
        "name": "The Framework Framework",
        "description": "KERNEL — 6 core frameworks for DoPeJarMo",
        "framework_ids": [
            "FMWK-001-ledger",
            "FMWK-002-write-path",
            "FMWK-003-orchestration",
            "FMWK-004-execution",
            "FMWK-005-graph",
            "FMWK-006-package-lifecycle",
        ],
    },
}

KERNEL_FRAMEWORK_OWNS = {
    "FMWK-001-ledger": "Append-only store, event schemas, hash chain",
    "FMWK-002-write-path": "Synchronous mutation, fold logic, snapshot",
    "FMWK-003-orchestration": "Mechanical planning, work order dispatch, LIVE ∩ REACHABLE, aperture",
    "FMWK-004-execution": "All LLM calls, prompt contract enforcement, signal delta submission",
    "FMWK-005-graph": "In-memory directed graph, node/edge schemas, query interface",
    "FMWK-006-package-lifecycle": "Gates, install/uninstall, composition registry, CLI tools",
}
