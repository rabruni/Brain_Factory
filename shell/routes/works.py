from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from shell.helpers.works import (
    get_works_detail,
    get_works_threads,
    list_fwk,
    list_scratchpad_threads,
    list_works,
    list_works_by_lifecycle,
)

router = APIRouter()


@router.get("/api/works")
async def api_works():
    return {
        "works": list_works(),
        "scratchpad": list_scratchpad_threads(),
    }


@router.get("/api/fwk")
async def api_fwk():
    return list_fwk()


@router.get("/api/fwk/{fwk_id}/works")
async def api_fwk_works(fwk_id: str):
    try:
        return list_works_by_lifecycle(fwk_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)


@router.get("/api/works/{framework_id}")
async def api_works_detail(framework_id: str):
    try:
        return get_works_detail(framework_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)


@router.get("/api/works/{framework_id}/threads")
async def api_works_threads(framework_id: str):
    try:
        return get_works_threads(framework_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
