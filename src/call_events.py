from __future__ import annotations

from typing import Any

from logging_utils import log_event


def dialpad_call_events(request: Any):
    payload = request.get_json(silent=True) or {}
    log_event(
        "call_event_received",
        event_type=payload.get("event_type"),
        call_id=payload.get("call_id"),
    )

    # Placeholder implementation:
    # the real handler will inspect call state, load stored context,
    # and trigger a transfer when spillover criteria are met.
    return {"ok": True}, 200
