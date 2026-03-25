from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

import backends
import workspace as ws
from shell.connection import manager
from shell.helpers.auth import authenticate
from shell.helpers.formatting import format_item, format_thread, get_threads_summary
from shell.helpers.routing import resolve_send_target
from shell.helpers.run_state import get_latest_run_summary
from shell.helpers.works import get_works_detail

router = APIRouter()


def _request_tags(data: dict) -> list[str]:
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        return []
    return [str(tag).strip() for tag in tags if str(tag).strip()]


def _session_id(agent_name: str, framework_id: str) -> str:
    return f"{agent_name}::{framework_id}"


def _is_framework_thread(thread_id: str, framework_id: str) -> bool:
    if not thread_id:
        return False
    items = ws.get_thread(thread_id)
    if not items:
        return False
    if not framework_id:
        return True
    for item in items:
        tags = item.get("tags") or []
        if framework_id in tags:
            return True
    return False


def _thread_reply_to(thread_id: str) -> str:
    items = ws.get_thread(thread_id)
    return items[-1]["id"] if items else ""


def _blueprint_context_block(data: dict, effective_to: str) -> str:
    framework_id = str(data.get("framework_id", "") or "").strip()
    lifecycle_section = str(data.get("lifecycle_section", "") or "").strip()
    if effective_to != "blueprint-agent" or lifecycle_section != "blueprints" or not framework_id:
        return ""
    try:
        detail = get_works_detail(framework_id)
    except ValueError:
        return ""
    blueprint = detail.get("blueprint", {})
    dep_lines = (blueprint.get("dependency_details") or [])
    dependencies = "\n".join(
        f"  {dep['framework_id']}: {'passed' if dep.get('passed') else 'not passed'}"
        for dep in dep_lines
    ) or "  none"
    sawmill_ready = "Yes" if blueprint.get("task_md_exists") and blueprint.get("dependencies_met") else "No"
    reason = "ready to start" if sawmill_ready == "Yes" else ("dependencies incomplete" if not blueprint.get("dependencies_met") else "needs TASK.md")
    return (
        "[Blueprint Context]\n"
        f"Framework: {detail.get('framework_id', framework_id)}\n"
        f"Sawmill prerequisite: {'TASK.md present' if blueprint.get('task_md_exists') else 'TASK.md missing'}\n"
        f"Optional enrichment: {'SOURCE_MATERIAL.md present' if blueprint.get('source_material_exists') else 'SOURCE_MATERIAL.md missing'}\n"
        "Dependencies:\n"
        f"{dependencies}\n"
        f"Sawmill ready: {sawmill_ready} — {reason}\n"
        f"Owns: {detail.get('owns', '')}"
    )


def _blueprint_context_content(data: dict, effective_to: str) -> str:
    content = data.get("content", "")
    block = _blueprint_context_block(data, effective_to)
    if not block:
        return content
    return f"{block}\n\n{content}"


def _blueprint_agent_message(data: dict, effective_to: str) -> str:
    block = _blueprint_context_block(data, effective_to)
    content = data.get("content", "")
    if not block:
        return content
    return f"{block}\n\n{content}"


def _brain_context_block(user_message, max_results=3):
    if max_results <= 0:
        return ""
    try:
        from shell.helpers.brain import search

        results = search(user_message, limit=max_results)
    except Exception:
        return ""
    if not results:
        return ""
    lines = ["[Brain Context — relevant prior knowledge]"]
    for thought in results:
        tags = ", ".join(thought.get("tags", []))
        tag_suffix = f" [{tags}]" if tags else ""
        lines.append(f"- {thought['content']}{tag_suffix}")
    lines.append("")
    return "\n".join(lines)


def _error_text(agent_name: str, exc: Exception, agent_config: dict) -> str:
    message = str(exc)
    credentials_ref = str(agent_config.get("credentials_ref", "") or "").strip()
    timeout = int(agent_config.get("timeout", 180) or 180)
    if credentials_ref and credentials_ref in message:
        return f"{agent_name} cannot respond: {credentials_ref} not set"
    if "timed out" in message.lower() or "timeout" in message.lower():
        return f"{agent_name} timed out after {timeout}s"
    return f"{agent_name} error: {message}"


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default="")):
    auth = authenticate(token)
    if not auth:
        await websocket.close(code=4001, reason="Invalid token")
        return
    conn_id = f"{id(websocket)}-{time.time()}"
    await manager.connect(websocket, conn_id)
    await manager.start_polling()
    try:
        await websocket.send_json({"type": "thread_list", "threads": get_threads_summary()})
        await websocket.send_json({"type": "run_status", "run": get_latest_run_summary() or {}})
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "subscribe":
                tid = data.get("thread_id", "")
                if tid:
                    manager.subscribe(conn_id, tid)
                    await websocket.send_json({"type": "thread_update", "thread_id": tid, "messages": format_thread(ws.get_thread(tid))})
            elif action == "unsubscribe":
                tid = data.get("thread_id", "")
                if tid:
                    manager.unsubscribe(conn_id, tid)
            elif action == "send":
                from_agent = auth.get("name", "human")
                from_cli = auth.get("cli", "human")
                reply_to = data.get("reply_to", "")
                effective_to = resolve_send_target(data.get("to", ""), reply_to, from_agent)
                item = ws.create_item(
                    item_type=data.get("type", "prompt"),
                    from_cli=from_cli,
                    to=effective_to,
                    summary=data.get("summary", data.get("content", "")[:80]),
                    content=data.get("content", ""),
                    tags=_request_tags(data),
                    from_agent=from_agent,
                    reply_to=reply_to,
                )
                await websocket.send_json({"type": "sent", "message": format_item(item)})
            elif action == "interactive":
                from_agent = auth.get("name", "human")
                from_cli = auth.get("cli", "human")
                framework_id = str(data.get("framework_id", "") or "").strip()
                requested_thread_id = str(data.get("thread_id", "") or "").strip()
                effective_to = resolve_send_target(data.get("to", ""), "", from_agent)
                agent_config = ws.get_agent_config(effective_to)
                if not agent_config or agent_config.get("agent_type") != "interactive" or not agent_config.get("enabled"):
                    continue

                thread_id = requested_thread_id if _is_framework_thread(requested_thread_id, framework_id) else ""
                reply_to = _thread_reply_to(thread_id) if thread_id else ""
                user_item = ws.create_item(
                    item_type=data.get("type", "prompt"),
                    from_cli=from_cli,
                    to=effective_to,
                    summary=data.get("summary", data.get("content", "")[:80]),
                    content=data.get("content", ""),
                    tags=_request_tags(data),
                    from_agent=from_agent,
                    reply_to=reply_to,
                )
                thread_id = user_item["thread_id"]
                manager.subscribe(conn_id, thread_id)
                await websocket.send_json({"type": "sent", "message": format_item(user_item)})
                await manager.broadcast_thread_update(thread_id, format_thread(ws.get_thread(thread_id)))
                await manager.broadcast_thread_list()

                session_id = _session_id(effective_to, framework_id or "__scratchpad__")
                initial_context = _blueprint_context_block(data, effective_to)
                brain_context = _brain_context_block(data.get("content", ""), max_results=3)
                if brain_context:
                    initial_context = f"{brain_context}\n{initial_context}" if initial_context else brain_context
                backends.create_session(session_id, agent_config, initial_context)

                try:
                    response_text = await asyncio.to_thread(
                        backends.send_to_session,
                        session_id,
                        _blueprint_agent_message(data, effective_to),
                        agent_config,
                    )
                    ws.create_item(
                        item_type="context",
                        from_cli=agent_config.get("cli", agent_config.get("provider", "assistant")),
                        to=from_agent,
                        summary=response_text[:80],
                        content=response_text,
                        tags=_request_tags(data),
                        from_agent=effective_to,
                        reply_to=user_item["id"],
                    )
                except Exception as exc:
                    error_text = _error_text(effective_to, exc, agent_config)
                    ws.create_item(
                        item_type="context",
                        from_cli="system",
                        to=from_agent,
                        summary=error_text[:80],
                        content=error_text,
                        tags=_request_tags(data),
                        from_agent="system",
                        reply_to=user_item["id"],
                    )
                await manager.broadcast_thread_update(thread_id, format_thread(ws.get_thread(thread_id)))
                await manager.broadcast_thread_list()
    except WebSocketDisconnect:
        manager.disconnect(conn_id)
    except Exception:
        manager.disconnect(conn_id)
