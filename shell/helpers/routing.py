from __future__ import annotations

import workspace as ws


def resolve_default_route(reply_to: str, from_agent: str) -> str:
    if not reply_to:
        return "any"
    parent = ws.get_item(reply_to)
    if not parent or "error" in parent:
        return "any"
    thread = ws.get_thread(parent.get("thread_id", "") or reply_to)
    for item in reversed(thread):
        candidate = item.get("from_agent", item.get("from_cli", "")).strip()
        if candidate and candidate not in {"human", from_agent}:
            return candidate
    participants: list[str] = []
    for item in thread:
        participant = item.get("from_agent", item.get("from_cli", "")).strip()
        if participant and participant not in {"human", from_agent} and participant not in participants:
            participants.append(participant)
    return participants[0] if participants else "any"


def resolve_send_target(explicit_to: str | None, reply_to: str, from_agent: str) -> str:
    candidate = str(explicit_to or "").strip()
    valid_targets = set(ws.get_routable_targets())
    if candidate and candidate in valid_targets and candidate not in {"human", "any"}:
        return candidate
    return resolve_default_route(reply_to, from_agent)

