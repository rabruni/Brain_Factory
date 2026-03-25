from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import backends
import workspace as ws

router = APIRouter()

PROVIDER_SECRET_REFS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
}


def _looks_like_secret(value: str) -> bool:
    text = str(value or "").strip()
    return text.startswith("sk-") or text.startswith("sk-ant-") or text.startswith("AIza")


def _normalize_agent_payload(body: dict) -> dict:
    payload = dict(body)
    provider = str(payload.get("provider", "") or "").strip()
    credentials_ref = str(payload.get("credentials_ref", "") or "").strip()
    if _looks_like_secret(credentials_ref):
        raise ValueError("This looks like a raw API key. Paste it into API Key, not API Key Env.")
    if provider in PROVIDER_SECRET_REFS:
        payload["credentials_ref"] = PROVIDER_SECRET_REFS[provider]
    return payload


@router.get("/api/agents")
async def api_agents():
    return [
        {
            **agent,
            "has_secret": backends.has_secret(agent.get("name", "")),
        }
        for agent in ws.list_agent_configs()
    ]


@router.post("/api/agents")
async def api_create_agent(request: Request):
    body = _normalize_agent_payload(await request.json())
    try:
        return ws.create_agent(
            name=body.get("name", ""),
            provider=body.get("provider", ""),
            model=body.get("model", ""),
            instructions=body.get("instructions", ""),
            task_types=body.get("task_types", []),
            tools=body.get("tools", []),
            api_base=body.get("api_base", ""),
            credentials_ref=body.get("credentials_ref", ""),
            description=body.get("description", ""),
            context_mode=body.get("context_mode", "full_thread"),
            context_n=int(body.get("context_n", 0) or 0),
            timeout=int(body.get("timeout", 180) or 180),
            max_retries=int(body.get("max_retries", 2) or 2),
            agent_type=body.get("agent_type", "worker"),
            enabled=bool(body.get("enabled", True)),
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.put("/api/agents/{name}")
async def api_update_agent(name: str, request: Request):
    body = _normalize_agent_payload(await request.json())
    try:
        body.pop("name", None)
        updated = ws.update_agent(name, **body)
        if "error" in updated:
            return JSONResponse(updated, status_code=404)
        return updated
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.post("/api/agents/{name}/secret")
async def api_set_agent_secret(name: str, request: Request):
    body = await request.json()
    try:
        return backends.save_secret(name, body.get("api_key", ""))
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.delete("/api/agents/{name}")
async def api_delete_agent(name: str):
    result = ws.delete_agent(name)
    if "error" in result:
        return JSONResponse(result, status_code=404)
    return result


@router.get("/api/providers/{provider}/models")
async def api_provider_models(provider: str, api_base: str = "", credentials_ref: str = ""):
    try:
        return backends.list_models(provider, api_base=api_base, credentials_ref=credentials_ref)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.post("/api/agents/test")
async def api_test_agent(request: Request):
    body = _normalize_agent_payload(await request.json())
    result = backends.test_connection(
        provider=body.get("provider", ""),
        model=body.get("model", ""),
        api_base=body.get("api_base", ""),
        credentials_ref=body.get("credentials_ref", ""),
        instructions=body.get("instructions", ""),
        tools=body.get("tools", []),
        agent_name=body.get("name", ""),
    )
    return JSONResponse(result, status_code=200 if result.get("ok") else 400)
