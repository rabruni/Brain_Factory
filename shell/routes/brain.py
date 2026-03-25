from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import workspace as ws
from shell.helpers import brain

router = APIRouter()


@router.get("/api/brain/stats")
async def api_brain_stats():
    return ws.thought_stats()


@router.get("/api/brain/thoughts")
async def api_brain_thoughts(limit: int = 50, tag: str = ""):
    return ws.list_thoughts(limit=limit, tag=tag or None)


@router.post("/api/brain/capture")
async def api_brain_capture(request: Request):
    body = await request.json()
    content = str(body.get("content", "") or "").strip()
    if not content:
        return JSONResponse({"error": "content is required"}, status_code=400)
    try:
        return brain.capture(
            content=content,
            tags=body.get("tags", []),
            source=str(body.get("source", "") or ""),
        )
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)


@router.post("/api/brain/search")
async def api_brain_search(request: Request):
    body = await request.json()
    query = str(body.get("query", "") or "").strip()
    if not query:
        return JSONResponse({"error": "query is required"}, status_code=400)
    try:
        return brain.search(
            query=query,
            limit=int(body.get("limit", 10) or 10),
            tag=str(body.get("tag", "") or ""),
        )
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)


@router.delete("/api/brain/thoughts/{thought_id}")
async def api_brain_delete(thought_id: str):
    result = brain.delete(thought_id)
    if not result.get("deleted"):
        return JSONResponse({"error": "Thought not found"}, status_code=404)
    return result
