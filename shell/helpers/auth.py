from __future__ import annotations

import workspace as ws


def authenticate(token: str | None) -> dict | None:
    if not token:
        return {"name": "human", "cli": "human"}
    info = ws.validate_token(token)
    return info or None

