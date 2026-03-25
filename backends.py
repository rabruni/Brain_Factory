from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


ANTHROPIC_MODELS = [
    {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "context_window": 1000000},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "context_window": 1000000},
    {"id": "claude-opus-4-5", "name": "Claude Opus 4.5", "context_window": 200000},
    {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5", "context_window": 200000},
    {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5", "context_window": 200000},
]
GOOGLE_MODELS = [
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "context_window": 1048576},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "context_window": 1048576},
    {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash-Lite", "context_window": 1048576},
]
CODEX_MODELS = [
    {"id": "codex", "name": "Codex CLI", "context_window": 128000},
]

_sessions: dict[str, list[dict[str, str]]] = {}
SECRETS_PATH = Path(__file__).resolve().parent / "workspace" / "secrets.json"
ROOT = Path(__file__).resolve().parent


def _load_secrets() -> dict[str, str]:
    if not SECRETS_PATH.exists():
        return {}
    try:
        data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(name): str(secret) for name, secret in data.items() if str(secret)}


def _write_secrets(data: dict[str, str]) -> None:
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SECRETS_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(SECRETS_PATH, 0o600)


def save_secret(agent_name: str, api_key: str) -> dict[str, bool]:
    name = str(agent_name or "").strip()
    secret = str(api_key or "").strip()
    if not name:
        raise ValueError("Agent name is required")
    if not secret:
        raise ValueError("API key is required")
    data = _load_secrets()
    data[name] = secret
    _write_secrets(data)
    return {"ok": True, "has_secret": True}


def has_secret(agent_name: str) -> bool:
    return str(agent_name or "").strip() in _load_secrets()


def _env_secret(credentials_ref: str, agent_name: str = "") -> str:
    name = str(agent_name or "").strip()
    if name:
        secret = _load_secrets().get(name, "").strip()
        if secret:
            return secret
    ref = str(credentials_ref or "").strip()
    if not ref:
        return ""
    return os.environ.get(ref, "").strip()


def _json_request(url: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 30, method: str | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers or {},
        method=method or ("POST" if data is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{exc.code} {body[:400]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc
    return json.loads(raw) if raw else {}


def _normalize_output(raw_text: str, fallback_summary: str) -> dict[str, Any]:
    text = str(raw_text or "").strip()
    if text:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                summary = str(parsed.get("summary", "") or fallback_summary).strip()
                content = str(parsed.get("content", "") or text).strip()
                route_to = parsed.get("route_to", [])
                if not isinstance(route_to, list):
                    route_to = []
                return {
                    "summary": summary or fallback_summary,
                    "content": content,
                    "route_to": [str(v).strip() for v in route_to if str(v).strip()],
                    "needs_human": bool(parsed.get("needs_human", False)),
                }
        except json.JSONDecodeError:
            pass
    return {
        "summary": fallback_summary or (text.splitlines()[0][:80] if text else "Worker result"),
        "content": text,
        "route_to": [],
        "needs_human": False,
    }


def create_session(session_id: str, agent_config: dict[str, Any], initial_context: str = "") -> str:
    if session_id in _sessions:
        return session_id
    messages: list[dict[str, str]] = []
    context = str(initial_context or "").strip()
    if context:
        messages.append({"role": "user", "content": context})
    _sessions[session_id] = messages
    return session_id


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def send_to_session(session_id: str, user_message: str, agent_config: dict[str, Any]) -> str:
    provider = str(agent_config.get("provider", "") or "").strip()
    if provider != "anthropic":
        raise ValueError(f"Unsupported interactive provider: {provider}")
    messages = _sessions.setdefault(session_id, [])
    messages.append({"role": "user", "content": str(user_message or "")})
    return _send_anthropic_session(messages, agent_config)


def invoke_agent(agent_config: dict[str, Any], prompt: str) -> dict[str, Any]:
    provider = str(agent_config.get("provider", "") or "").strip()
    if provider == "ollama":
        return _invoke_ollama(agent_config, prompt)
    if provider == "anthropic":
        return _invoke_anthropic(agent_config, prompt)
    if provider == "openai":
        return _invoke_openai(agent_config, prompt)
    if provider == "google":
        return _invoke_google(agent_config, prompt)
    raise ValueError(f"Unsupported provider: {provider}")


def list_models(provider: str, api_base: str = "", credentials_ref: str = "") -> list[dict[str, Any]]:
    provider = str(provider or "").strip()
    if provider == "ollama":
        base = str(api_base or "http://localhost:11434").rstrip("/")
        data = _json_request(f"{base}/api/tags", timeout=15)
        models = []
        for item in data.get("models", []):
            models.append({
                "id": item.get("name", ""),
                "name": item.get("name", ""),
                "context_window": item.get("details", {}).get("context_length"),
            })
        return models
    if provider == "anthropic":
        return ANTHROPIC_MODELS
    if provider == "google":
        return GOOGLE_MODELS
    if provider == "codex-cli":
        return CODEX_MODELS
    if provider == "openai":
        base = str(api_base or "https://api.openai.com").rstrip("/")
        api_key = _env_secret(credentials_ref)
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        data = _json_request(f"{base}/v1/models", headers=headers, timeout=20)
        models = []
        for item in data.get("data", []):
            mid = item.get("id", "")
            if mid:
                models.append({"id": mid, "name": mid, "context_window": None})
        return models
    return []


def test_connection(provider: str, model: str, api_base: str = "", credentials_ref: str = "", instructions: str = "", tools: list[str] | None = None, agent_name: str = "") -> dict[str, Any]:
    provider = str(provider or "").strip()
    model = str(model or "").strip()
    if not model:
        return {"ok": False, "error": "Model is required"}
    try:
        if provider == "ollama":
            base = str(api_base or "http://localhost:11434").rstrip("/")
            data = _json_request(
                f"{base}/api/chat",
                payload={"model": model, "messages": [{"role": "user", "content": "ping"}], "stream": False},
                headers={"Content-Type": "application/json"},
                timeout=20,
            )
            return {"ok": True, "context_window": data.get("context", None)}
        if provider == "openai":
            api_key = _env_secret(credentials_ref, agent_name)
            if not api_key:
                return {"ok": False, "error": f"Missing env var: {credentials_ref}"}
            base = str(api_base or "https://api.openai.com").rstrip("/")
            _json_request(
                f"{base}/v1/chat/completions",
                payload={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                timeout=20,
            )
            return {"ok": True, "context_window": None}
        if provider == "anthropic":
            api_key = _env_secret(credentials_ref, agent_name)
            if not api_key:
                return {"ok": False, "error": f"Missing env var: {credentials_ref}"}
            _json_request(
                "https://api.anthropic.com/v1/messages",
                payload={
                    "model": model,
                    "max_tokens": 5,
                    "system": instructions or "You are a test assistant.",
                    "messages": [{"role": "user", "content": "ping"}],
                    "tools": _anthropic_tools(tools or []),
                },
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                timeout=20,
            )
            return {"ok": True, "context_window": next((m["context_window"] for m in ANTHROPIC_MODELS if m["id"] == model), None)}
        if provider == "google":
            api_key = _env_secret(credentials_ref, agent_name)
            if not api_key:
                return {"ok": False, "error": f"Missing env var: {credentials_ref}"}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(api_key)}"
            _json_request(
                url,
                payload={"contents": [{"parts": [{"text": "ping"}]}]},
                headers={"Content-Type": "application/json"},
                timeout=20,
            )
            return {"ok": True, "context_window": next((m["context_window"] for m in GOOGLE_MODELS if m["id"] == model), None)}
        if provider == "codex-cli":
            return {"ok": True, "context_window": CODEX_MODELS[0]["context_window"]}
        return {"ok": False, "error": f"Unsupported provider: {provider}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _invoke_ollama(agent_config: dict[str, Any], prompt: str) -> dict[str, Any]:
    base = str(agent_config.get("api_base", "") or "http://localhost:11434").rstrip("/")
    data = _json_request(
        f"{base}/api/chat",
        payload={
            "model": agent_config["model"],
            "messages": [
                {"role": "system", "content": agent_config.get("instructions", "")},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        },
        headers={"Content-Type": "application/json"},
        timeout=int(agent_config.get("timeout", 180)),
    )
    content = data.get("message", {}).get("content", "") if isinstance(data, dict) else ""
    return _normalize_output(content, f"Ollama result from {agent_config.get('name', 'worker')}")


def _invoke_openai(agent_config: dict[str, Any], prompt: str) -> dict[str, Any]:
    api_key = _env_secret(agent_config.get("credentials_ref", ""), agent_config.get("name", ""))
    if not api_key:
        raise RuntimeError(f"Missing env var: {agent_config.get('credentials_ref', '')}")
    base = str(agent_config.get("api_base", "") or "https://api.openai.com").rstrip("/")
    data = _json_request(
        f"{base}/v1/chat/completions",
        payload={
            "model": agent_config["model"],
            "messages": [
                {"role": "system", "content": agent_config.get("instructions", "")},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": int(agent_config.get("max_output_tokens", 4000)),
        },
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        timeout=int(agent_config.get("timeout", 180)),
    )
    content = ""
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        content = json.dumps(data)
    return _normalize_output(content, f"OpenAI result from {agent_config.get('name', 'worker')}")


def _invoke_anthropic(agent_config: dict[str, Any], prompt: str) -> dict[str, Any]:
    api_key = _env_secret(agent_config.get("credentials_ref", ""), agent_config.get("name", ""))
    if not api_key:
        raise RuntimeError(f"Missing env var: {agent_config.get('credentials_ref', '')}")
    data = _json_request(
        "https://api.anthropic.com/v1/messages",
        payload={
            "model": agent_config["model"],
            "max_tokens": int(agent_config.get("max_output_tokens", 4000)),
            "system": agent_config.get("instructions", ""),
            "messages": [{"role": "user", "content": prompt}],
            "tools": _anthropic_tools(agent_config.get("tools", [])),
        },
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout=int(agent_config.get("timeout", 180)),
    )
    text_parts = []
    for item in data.get("content", []):
        if item.get("type") == "text":
            text_parts.append(item.get("text", ""))
    return _normalize_output("\n".join(text_parts), f"Anthropic result from {agent_config.get('name', 'worker')}")


def _safe_repo_path(path_text: str) -> Path:
    raw = str(path_text or "").strip()
    if not raw:
        raise RuntimeError("path is required")
    candidate = Path(raw)
    resolved = (candidate if candidate.is_absolute() else (ROOT / candidate)).resolve()
    root = ROOT.resolve()
    if root != resolved and root not in resolved.parents:
        raise RuntimeError("path must stay within repo root")
    return resolved


def _anthropic_tools(enabled_tools: list[str]) -> list[dict[str, Any]]:
    tools = []
    enabled = set(enabled_tools or [])
    if "read_file" in enabled:
        tools.append({
            "name": "read_file",
            "description": "Read a UTF-8 text file from the repository.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        })
    if "list_directory" in enabled:
        tools.append({
            "name": "list_directory",
            "description": "List files and directories at a repository path.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        })
    if "search_files" in enabled:
        tools.append({
            "name": "search_files",
            "description": "Search repository files for a text pattern.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["pattern"],
            },
        })
    return tools


def _execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    if tool_name == "read_file":
        path = _safe_repo_path(tool_input.get("path", ""))
        if not path.is_file():
            raise RuntimeError(f"Not a file: {path}")
        return path.read_text(encoding="utf-8")
    if tool_name == "list_directory":
        path = _safe_repo_path(tool_input.get("path", "."))
        if not path.is_dir():
            raise RuntimeError(f"Not a directory: {path}")
        return "\n".join(sorted(item.name for item in path.iterdir()))
    if tool_name == "search_files":
        pattern = str(tool_input.get("pattern", "") or "").strip()
        if not pattern:
            raise RuntimeError("pattern is required")
        path = _safe_repo_path(tool_input.get("path", "."))
        if not path.exists():
            raise RuntimeError(f"Path not found: {path}")
        proc = subprocess.run(
            ["rg", "-n", pattern, str(path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        return (proc.stdout or proc.stderr or "").strip() or "No matches"
    raise RuntimeError(f"Unsupported tool: {tool_name}")


def _anthropic_text(content_blocks: list[dict[str, Any]]) -> str:
    return "\n".join(item.get("text", "") for item in content_blocks if item.get("type") == "text").strip()


def _send_anthropic_session(messages: list[dict[str, Any]], agent_config: dict[str, Any]) -> str:
    api_key = _env_secret(agent_config.get("credentials_ref", ""), agent_config.get("name", ""))
    if not api_key:
        raise RuntimeError(f"Missing env var: {agent_config.get('credentials_ref', '')}")
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    tools = _anthropic_tools(agent_config.get("tools", []))
    while True:
        data = _json_request(
            "https://api.anthropic.com/v1/messages",
            payload={
                "model": agent_config["model"],
                "max_tokens": int(agent_config.get("max_output_tokens", 4000)),
                "system": agent_config.get("instructions", ""),
                "messages": messages,
                "tools": tools,
            },
            headers=headers,
            timeout=int(agent_config.get("timeout", 180)),
        )
        content_blocks = data.get("content", []) or []
        tool_uses = [item for item in content_blocks if item.get("type") == "tool_use"]
        text = _anthropic_text(content_blocks)
        messages.append({"role": "assistant", "content": content_blocks})
        if not tool_uses:
            if not text:
                raise RuntimeError("Anthropic returned an empty response")
            return text
        tool_results = []
        for tool_use in tool_uses:
            tool_name = tool_use.get("name", "")
            tool_input = tool_use.get("input", {}) or {}
            try:
                result = _execute_tool(tool_name, tool_input)
                is_error = False
            except Exception as exc:
                result = str(exc)
                is_error = True
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.get("id", ""),
                "content": result,
                "is_error": is_error,
            })
        messages.append({"role": "user", "content": tool_results})


def _invoke_google(agent_config: dict[str, Any], prompt: str) -> dict[str, Any]:
    api_key = _env_secret(agent_config.get("credentials_ref", ""), agent_config.get("name", ""))
    if not api_key:
        raise RuntimeError(f"Missing env var: {agent_config.get('credentials_ref', '')}")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(agent_config['model'])}:generateContent?key={urllib.parse.quote(api_key)}"
    data = _json_request(
        url,
        payload={
            "system_instruction": {"parts": [{"text": agent_config.get("instructions", "")}]},
            "contents": [{"parts": [{"text": prompt}]}],
        },
        headers={"Content-Type": "application/json"},
        timeout=int(agent_config.get("timeout", 180)),
    )
    text_parts = []
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if "text" in part:
                text_parts.append(part.get("text", ""))
    return _normalize_output("\n".join(text_parts), f"Google result from {agent_config.get('name', 'worker')}")
