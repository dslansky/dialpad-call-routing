from __future__ import annotations

import json
import logging


logger = logging.getLogger("dialpad_call_routing")
logger.setLevel(logging.INFO)


def log_event(event_name: str, **fields: object) -> None:
    payload = {"event": event_name, **fields}
    logger.info(json.dumps(payload, sort_keys=True, default=str))
