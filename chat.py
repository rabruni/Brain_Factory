"""DoPeJarMo Shell — operator surface for workspace and sawmill runs."""

from __future__ import annotations

import argparse

import uvicorn

from shell.app import app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DoPeJarMo Shell")
    parser.add_argument("--port", type=int, default=8503)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
