from __future__ import annotations

from typing import Any

from dialpad_responses import end_response
from logging_utils import log_event


def dialpad_router(request: Any):
    payload = request.get_json(silent=True) or {}
    call_id = payload.get("call_id")
    external_number = payload.get("external_number")

    log_event(
        "router_webhook_received",
        call_id=call_id,
        external_number=external_number,
    )

    # Placeholder implementation:
    # the real handler will normalize the phone, query Salesforce,
    # evaluate the routing matrix, and return a Dialpad route action.
    return end_response("Routing is not configured yet.")
