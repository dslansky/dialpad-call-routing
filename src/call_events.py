from __future__ import annotations

from typing import Any

from src.dialpad_client import DialpadClient
from src.logging_utils import log_event
from src.main import CALL_CONTEXT_STORE, _get_settings


NO_ANSWER_MARKERS = {
    "missed",
    "no_answer",
    "no-answer",
    "not_answered",
    "unanswered",
}


def _extract_call_id(payload: dict[str, Any]) -> str | None:
    return payload.get("call_id") or payload.get("call", {}).get("id")


def _extract_status_values(payload: dict[str, Any]) -> set[str]:
    nested_call = payload.get("call") if isinstance(payload.get("call"), dict) else {}
    candidates = {
        payload.get("event_type"),
        payload.get("state"),
        payload.get("call_state"),
        payload.get("status"),
        payload.get("target_status"),
        payload.get("target_call_status"),
        nested_call.get("state"),
        nested_call.get("status"),
    }
    return {str(value).strip().lower() for value in candidates if value}


def _is_no_answer_event(payload: dict[str, Any]) -> bool:
    status_values = _extract_status_values(payload)
    return any(marker in value for value in status_values for marker in NO_ANSWER_MARKERS)


def dialpad_call_events(request: Any):
    settings = _get_settings()
    payload = request.get_json(silent=True) or {}
    call_id = _extract_call_id(payload)
    event_type = payload.get("event_type")
    log_event(
        "call_event_received",
        event_type=event_type,
        call_id=call_id,
    )

    if not call_id:
        return {"ok": True}, 200

    context = CALL_CONTEXT_STORE.get(call_id)
    if not context or context.spillover_attempted:
        return {"ok": True}, 200

    if not context.spillover_target_id or not context.spillover_target_type:
        return {"ok": True}, 200

    if not _is_no_answer_event(payload):
        return {"ok": True}, 200

    try:
        DialpadClient(settings.dialpad_api_key).transfer_call(
            call_id=call_id,
            target_id=context.spillover_target_id,
            target_type=context.spillover_target_type,
        )
        CALL_CONTEXT_STORE.mark_spillover_attempted(call_id)
        log_event("spillover_transfer_triggered", call_id=call_id)
    except Exception as exc:
        log_event("spillover_transfer_failed", call_id=call_id, error=str(exc))

    return {"ok": True}, 200
