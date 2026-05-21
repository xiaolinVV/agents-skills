from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence


def envelope(command: str, status: str, **payload: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "command": command,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    data.update(payload)
    return data


def overall_status(results: Sequence[dict[str, Any]]) -> str:
    if not results:
        return "success"
    statuses = {item.get("status") for item in results}
    if statuses == {"success"}:
        return "success"
    if "success" in statuses or "partial_error" in statuses:
        return "partial_error"
    return "error"
