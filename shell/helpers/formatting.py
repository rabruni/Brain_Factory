from __future__ import annotations

import workspace as ws


def format_item(item: dict) -> dict:
    tags = item.get("tags") or []
    framework_id = ""
    if isinstance(tags, list):
        framework_id = next((tag for tag in tags if str(tag).startswith("FMWK-")), "")
    return {
        "id": item.get("id", ""),
        "type": item.get("type", ""),
        "from_agent": item.get("from_agent", item.get("from_cli", "?")),
        "from_cli": item.get("from_cli", "?"),
        "to": item.get("to", ""),
        "reply_to": item.get("reply_to", ""),
        "thread_id": item.get("thread_id", ""),
        "status": item.get("status", ""),
        "created_at": item.get("created_at", ""),
        "summary": item.get("summary", ""),
        "content": item.get("content", ""),
        "tags": tags,
        "framework_id": framework_id,
    }


def format_thread(items: list[dict]) -> list[dict]:
    return [format_item(it) for it in items]


def get_threads_summary() -> list[dict]:
    threads = ws.list_threads()
    return [
        {
            "thread_id": t["thread_id"],
            "summary": t["summary"],
            "participants": t["participants"],
            "latest": t["latest"],
            "message_count": t["message_count"],
            "has_active": any(it.get("status") in ("sent", "read") for it in t["items"]),
        }
        for t in threads
    ]
