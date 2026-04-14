from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ivr_fallback_target: str
    ivr_fallback_target_type: str
    router_did: str
    dialpad_api_key: str
    dialpad_office_id: str
    dialpad_routing_url: str
    dialpad_event_webhook_url: str
    sf_client_id: str
    sf_client_secret: str
    sf_token_url: str
    sf_instance_url: str
    client_matrix_path: str
    employee_matrix_path: str
    dialpad_target_map_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            ivr_fallback_target=os.getenv("IVR_FALLBACK_TARGET", ""),
            ivr_fallback_target_type=os.getenv("IVR_FALLBACK_TARGET_TYPE", ""),
            router_did=os.getenv("ROUTER_DID", ""),
            dialpad_api_key=os.getenv("DIALPAD_API_KEY", ""),
            dialpad_office_id=os.getenv("DIALPAD_OFFICE_ID", ""),
            dialpad_routing_url=os.getenv("DIALPAD_ROUTING_URL", ""),
            dialpad_event_webhook_url=os.getenv("DIALPAD_EVENT_WEBHOOK_URL", ""),
            sf_client_id=os.getenv("SF_CLIENT_ID", ""),
            sf_client_secret=os.getenv("SF_CLIENT_SECRET", ""),
            sf_token_url=os.getenv("SF_TOKEN_URL", ""),
            sf_instance_url=os.getenv("SF_INSTANCE_URL", ""),
            client_matrix_path=os.getenv(
                "ROUTING_MATRIX_CLIENT_PATH",
                "Inbound Calling Matrix - Client.csv",
            ),
            employee_matrix_path=os.getenv(
                "ROUTING_MATRIX_EMPLOYEE_PATH",
                "Inbound Calling Matrix - Employee.csv",
            ),
            dialpad_target_map_path=os.getenv(
                "DIALPAD_TARGET_MAP_PATH",
                "config/dialpad_target_map.example.json",
            ),
        )
