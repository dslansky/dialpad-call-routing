from __future__ import annotations

from datetime import datetime, timezone

from src.call_context_store import CallContext, InMemoryCallContextStore
from src.config import Settings
from src import call_events


class FakeRequest:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def get_json(self, silent: bool = True) -> dict:
        return self.payload


class FakeDialpadClient:
    transfer_calls: list[tuple[str, str, str]] = []

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def transfer_call(self, call_id: str, target_id: str, target_type: str) -> dict:
        self.transfer_calls.append((call_id, target_id, target_type))
        return {"ok": True}


def _settings() -> Settings:
    return Settings(
        ivr_fallback_target="",
        ivr_fallback_target_type="",
        router_did="",
        dialpad_api_key="dialpad-key",
        dialpad_office_id="",
        dialpad_routing_url="",
        dialpad_event_webhook_url="",
        sf_client_id="",
        sf_client_secret="",
        sf_token_url="",
        sf_instance_url="",
        routing_config_bucket="dialpad-config",
        client_rules_object="routing-rules-client.json",
        employee_rules_object="routing-rules-employee.json",
        dialpad_target_map_object="dialpad-target-map.json",
        routing_config_cache_ttl_seconds=300,
        call_context_collection="dialpad_call_contexts",
        call_context_ttl_seconds=3600,
    )


def test_duplicate_no_answer_events_only_transfer_once() -> None:
    store = InMemoryCallContextStore(
        ttl_seconds=3600,
        now_fn=lambda: datetime(2026, 4, 15, 12, 0, tzinfo=timezone.utc),
    )
    store.put(
        CallContext(
            call_id="call-1",
            contact_id="003x",
            contact_type="Client",
            primary_target_id="100",
            primary_target_type="user",
            spillover_target_id="200",
            spillover_target_type="user",
        )
    )

    original_store_getter = call_events._get_call_context_store
    original_settings_getter = call_events._get_settings
    original_dialpad_client = call_events.DialpadClient
    FakeDialpadClient.transfer_calls = []
    try:
        call_events._get_call_context_store = lambda: store
        call_events._get_settings = _settings
        call_events.DialpadClient = FakeDialpadClient

        payload = {"call_id": "call-1", "state": "no_answer"}
        call_events.dialpad_call_events(FakeRequest(payload))
        call_events.dialpad_call_events(FakeRequest(payload))
    finally:
        call_events._get_call_context_store = original_store_getter
        call_events._get_settings = original_settings_getter
        call_events.DialpadClient = original_dialpad_client

    assert FakeDialpadClient.transfer_calls == [("call-1", "200", "user")]
