from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from shell.helpers.manifest import build_manifest_view, framework_dirs, registry_role_defaults, write_manifest

router = APIRouter()


@router.get("/api/registry")
async def api_registry():
    return {"roles": registry_role_defaults()}


@router.get("/api/frameworks")
async def api_frameworks():
    return framework_dirs()


@router.get("/api/manifest/{fmwk_id}")
async def api_manifest(fmwk_id: str):
    try:
        return build_manifest_view(fmwk_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)


@router.put("/api/manifest/{fmwk_id}")
async def api_put_manifest(fmwk_id: str, request: Request):
    try:
        body = await request.json()
        manifest = write_manifest(fmwk_id, body)
        return {"status": "saved", "framework": fmwk_id, "manifest": manifest}
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

