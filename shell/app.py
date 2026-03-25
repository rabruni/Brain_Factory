from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from shell.config import ROOT
from shell.connection import manager
from shell.routes import agents, brain, manifest, runs, threads, websocket, works

app = FastAPI(title="DoPeJarMo Chat")
app.mount("/static", StaticFiles(directory=str(ROOT / "shell/static")), name="static")
app.include_router(threads.router)
app.include_router(agents.router)
app.include_router(brain.router)
app.include_router(runs.router)
app.include_router(manifest.router)
app.include_router(works.router)
app.include_router(websocket.router)


@app.get("/")
async def index():
    return FileResponse(
        ROOT / "shell/static/index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.on_event("startup")
async def startup():
    await manager.start_polling()
