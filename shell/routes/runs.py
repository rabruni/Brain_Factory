from __future__ import annotations

import subprocess

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from shell.config import ROOT, SAWMILL_DIR
from shell.helpers.manifest import ensure_manifest, framework_has_active_run, manifest_path
from shell.helpers.run_state import run_detail, run_dirs, run_summary

router = APIRouter()


@router.get("/api/runs")
async def api_runs():
    return [run_summary(run_dir) for run_dir in run_dirs()]


@router.get("/api/run/{run_id}")
async def api_run(run_id: str):
    for run_dir in run_dirs():
        if run_dir.name == run_id:
            return run_detail(run_dir)
    return JSONResponse({"error": "Run not found"}, status_code=404)


@router.post("/api/run/launch")
async def api_run_launch(request: Request):
    body = await request.json()
    framework = str(body.get("framework", "")).strip()
    framework_dir = SAWMILL_DIR / framework
    if not framework or not framework_dir.is_dir() or not (framework_dir / "TASK.md").exists():
        return JSONResponse({"error": f"Unknown framework: {framework}"}, status_code=404)
    if framework_has_active_run(framework):
        return JSONResponse({"error": f"Framework {framework} already has an active run"}, status_code=409)
    manifest_preexisted = manifest_path(framework).exists()
    manifest = ensure_manifest(framework)
    proc = subprocess.Popen(
        ["./sawmill/run.sh", framework],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {
        "status": "launched",
        "framework": framework,
        "pid": proc.pid,
        "manifest_created": not manifest_preexisted,
        "manifest": manifest,
    }

