from __future__ import annotations


def route_response(target_id: str, target_type: str) -> dict:
    return {
        "action": "route",
        "target_id": str(target_id),
        "target_type": target_type,
    }


def forward_response(forward_to: str) -> dict:
    return {
        "action": "forward",
        "forward_to": forward_to,
    }


def ask_response(message: str, hint_name: str, num_digits: int = 1) -> dict:
    return {
        "action": "ask",
        "message": [message],
        "hint_name": hint_name,
        "num_digits": num_digits,
    }


def end_response(message: str) -> dict:
    return {
        "action": "end",
        "message": [message],
    }
