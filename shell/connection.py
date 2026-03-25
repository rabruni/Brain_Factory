from __future__ import annotations

import asyncio
import json

import workspace as ws

from shell.helpers.formatting import format_thread, get_threads_summary
from shell.helpers.run_state import get_latest_run_summary


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, object] = {}
        self.subscriptions: dict[str, set[str]] = {}
        self._poll_task: asyncio.Task | None = None
        self._last_seen: dict[str, str] = {}
        self._last_run_fingerprint = ""

    async def connect(self, ws_conn, conn_id: str) -> None:
        await ws_conn.accept()
        self.active[conn_id] = ws_conn

    def disconnect(self, conn_id: str) -> None:
        self.active.pop(conn_id, None)
        self.subscriptions.pop(conn_id, None)

    def subscribe(self, conn_id: str, thread_id: str) -> None:
        self.subscriptions.setdefault(conn_id, set()).add(thread_id)

    def unsubscribe(self, conn_id: str, thread_id: str) -> None:
        if conn_id in self.subscriptions:
            self.subscriptions[conn_id].discard(thread_id)

    async def broadcast_thread_update(self, thread_id: str, messages: list[dict]) -> None:
        dead: list[str] = []
        for conn_id, subs in self.subscriptions.items():
            if thread_id in subs and conn_id in self.active:
                try:
                    await self.active[conn_id].send_json({"type": "thread_update", "thread_id": thread_id, "messages": messages})
                except Exception:
                    dead.append(conn_id)
        for conn_id in dead:
            self.disconnect(conn_id)

    async def broadcast_thread_list(self) -> None:
        threads = get_threads_summary()
        dead: list[str] = []
        for conn_id, ws_conn in self.active.items():
            try:
                await ws_conn.send_json({"type": "thread_list", "threads": threads})
            except Exception:
                dead.append(conn_id)
        for conn_id in dead:
            self.disconnect(conn_id)

    async def broadcast_run_status(self, run: dict) -> None:
        dead: list[str] = []
        for conn_id, ws_conn in self.active.items():
            try:
                await ws_conn.send_json({"type": "run_status", "run": run})
            except Exception:
                dead.append(conn_id)
        for conn_id in dead:
            self.disconnect(conn_id)

    async def start_polling(self) -> None:
        if self._poll_task is None:
            self._poll_task = asyncio.create_task(self._poll_loop())

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(2.5)
            if not self.active:
                continue
            try:
                threads = ws.list_threads()
                changed = False
                for t in threads:
                    tid = t["thread_id"]
                    latest = t["latest"]
                    if tid not in self._last_seen or self._last_seen[tid] != latest:
                        self._last_seen[tid] = latest
                        changed = True
                        await self.broadcast_thread_update(tid, format_thread(ws.get_thread(tid)))
                if changed:
                    await self.broadcast_thread_list()
                latest_run = get_latest_run_summary()
                fingerprint = json.dumps(latest_run, sort_keys=True) if latest_run else ""
                if fingerprint != self._last_run_fingerprint:
                    self._last_run_fingerprint = fingerprint
                    await self.broadcast_run_status(latest_run or {})
            except Exception:
                pass


manager = ConnectionManager()

