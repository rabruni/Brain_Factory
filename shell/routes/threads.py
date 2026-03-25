from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import workspace as ws
from shell.helpers.auth import authenticate
from shell.helpers.formatting import format_item, format_thread, get_threads_summary
from shell.helpers.routing import resolve_send_target
from shell.helpers.works import get_works_detail

router = APIRouter()


def _request_tags(body: dict) -> list[str]:
    tags = body.get("tags", [])
    if not isinstance(tags, list):
        return []
    return [str(tag).strip() for tag in tags if str(tag).strip()]


def _blueprint_context_content(body: dict, effective_to: str) -> str:
    content = body.get("content", "")
    framework_id = str(body.get("framework_id", "") or "").strip()
    lifecycle_section = str(body.get("lifecycle_section", "") or "").strip()
    if effective_to != "blueprint-agent" or lifecycle_section != "blueprints" or not framework_id:
        return content
    try:
        detail = get_works_detail(framework_id)
    except ValueError:
        return content
    blueprint = detail.get("blueprint", {})
    dep_lines = (blueprint.get("dependency_details") or [])
    dependencies = "\n".join(
        f"  {dep['framework_id']}: {'passed' if dep.get('passed') else 'not passed'}"
        for dep in dep_lines
    ) or "  none"
    block = (
        "[Blueprint Context]\n"
        f"Framework: {detail.get('framework_id', framework_id)}\n"
        f"State: {blueprint.get('blueprint_state', 'not_started')}\n"
        f"Directory: {'present' if blueprint.get('directory_exists') else 'missing'}\n"
        f"TASK.md: {'present' if blueprint.get('task_md_exists') else 'missing'}\n"
        f"SOURCE_MATERIAL.md: {'present' if blueprint.get('source_material_exists') else 'missing'}\n"
        f"Owns: {detail.get('owns', '')}\n"
        "Dependencies:\n"
        f"{dependencies}\n"
        f"D-docs complete: {blueprint.get('complete_count', 0)}/{blueprint.get('total_count', 0)}"
    )
    return f"{block}\n\n{content}"


@router.get("/api/threads")
async def api_threads():
    return get_threads_summary()


@router.get("/api/thread/{thread_id}")
async def api_thread(thread_id: str):
    items = ws.get_thread(thread_id)
    if not items:
        return JSONResponse({"error": "Thread not found"}, status_code=404)
    return format_thread(items)


@router.post("/api/send")
async def api_send(request: Request):
    body = await request.json()
    auth = authenticate(body.get("token"))
    if not auth:
        return JSONResponse({"error": "Invalid token"}, status_code=401)
    from_agent = auth.get("name", "human")
    from_cli = auth.get("cli", "human")
    reply_to = body.get("reply_to", "")
    effective_to = resolve_send_target(body.get("to", ""), reply_to, from_agent)
    item = ws.create_item(
        item_type=body.get("type", "prompt"),
        from_cli=from_cli,
        to=effective_to,
        summary=body.get("summary", body.get("content", "")[:80]),
        content=_blueprint_context_content(body, effective_to),
        tags=_request_tags(body),
        from_agent=from_agent,
        reply_to=reply_to,
    )
    return format_item(item)


@router.get("/api/targets")
async def api_targets():
    return ws.get_routable_targets()
