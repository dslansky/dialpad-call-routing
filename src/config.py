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
    routing_config_bucket: str
    client_rules_object: str
    employee_rules_object: str
    dialpad_target_map_object: str
    routing_config_cache_ttl_seconds: int
    call_context_collection: str
    call_context_ttl_seconds: int

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
            routing_config_bucket=os.getenv("ROUTING_CONFIG_BUCKET", ""),
            client_rules_object=os.getenv(
                "ROUTING_RULES_CLIENT_OBJECT",
                "routing-rules-client.json",
            ),
            employee_rules_object=os.getenv(
                "ROUTING_RULES_EMPLOYEE_OBJECT",
                "routing-rules-employee.json",
            ),
            dialpad_target_map_object=os.getenv(
                "DIALPAD_TARGET_MAP_OBJECT",
                "dialpad-target-map.json",
            ),
            routing_config_cache_ttl_seconds=int(
                os.getenv("ROUTING_CONFIG_CACHE_TTL_SECONDS", "300")
            ),
            call_context_collection=os.getenv(
                "CALL_CONTEXT_COLLECTION",
                "dialpad_call_contexts",
            ),
            call_context_ttl_seconds=int(
                os.getenv("CALL_CONTEXT_TTL_SECONDS", "3600")
            ),
        )
