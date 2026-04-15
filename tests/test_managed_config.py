from __future__ import annotations

import json

from src.config import Settings
from src.managed_config import GcsManagedConfigProvider


class FakeBlob:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def download_as_text(self) -> str:
        return json.dumps(self.payload)


class FakeBucket:
    def __init__(self, payloads: dict[str, object]) -> None:
        self.payloads = payloads

    def blob(self, object_name: str) -> FakeBlob:
        payload = self.payloads.get(object_name)
        if payload is None:
            raise KeyError(object_name)
        return FakeBlob(payload)


class FakeStorageClient:
    def __init__(self, payloads: dict[str, object]) -> None:
        self.payloads = payloads
        self.bucket_calls = 0

    def bucket(self, bucket_name: str) -> FakeBucket:
        self.bucket_calls += 1
        return FakeBucket(self.payloads)


class FailingStorageClient:
    def bucket(self, bucket_name: str) -> FakeBucket:
        raise RuntimeError("gcs unavailable")


def _settings() -> Settings:
    return Settings(
        ivr_fallback_target="",
        ivr_fallback_target_type="",
        router_did="",
        dialpad_api_key="",
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
    )


def _payloads() -> dict[str, object]:
    return {
        "routing-rules-client.json": [
            {
                "contact_type": "Client",
                "onboarding_step": "New",
                "status": "Never Contacted",
                "step_reason": None,
                "primary_owner_scope": "region",
                "primary_owner_field": "Back_End_Intake_Coordinator__c",
                "spillover_owner_scope": None,
                "spillover_owner_field": None,
            }
        ],
        "routing-rules-employee.json": [
            {
                "contact_type": "Employee",
                "onboarding_step": "Candidate Found",
                "status": "Never Contacted",
                "step_reason": None,
                "primary_owner_scope": "site",
                "primary_owner_field": "Technician_Recruiter__c",
                "spillover_owner_scope": None,
                "spillover_owner_field": None,
            }
        ],
        "dialpad-target-map.json": {
            "salesforce_user_targets": {},
            "logical_targets": {
                "ivr_fallback": {"target_id": "123", "target_type": "department"}
            },
            "region_aliases": {},
        },
    }


def test_managed_config_provider_loads_json_from_gcs() -> None:
    storage_client = FakeStorageClient(_payloads())
    provider = GcsManagedConfigProvider(
        _settings(),
        storage_client=storage_client,
        time_fn=lambda: 100.0,
    )

    config = provider.get_config()

    assert len(config.client_rules) == 1
    assert config.client_rules[0].primary_owner_field == "Back_End_Intake_Coordinator__c"
    assert config.target_map.get_logical_target("ivr_fallback").target_id == "123"
    assert storage_client.bucket_calls == 1


def test_managed_config_provider_uses_cache_within_ttl() -> None:
    storage_client = FakeStorageClient(_payloads())
    current_time = [100.0]
    provider = GcsManagedConfigProvider(
        _settings(),
        storage_client=storage_client,
        time_fn=lambda: current_time[0],
    )

    provider.get_config()
    current_time[0] = 120.0
    provider.get_config()

    assert storage_client.bucket_calls == 1


def test_managed_config_provider_returns_stale_cache_on_refresh_failure() -> None:
    current_time = [100.0]
    provider = GcsManagedConfigProvider(
        _settings(),
        storage_client=FakeStorageClient(_payloads()),
        time_fn=lambda: current_time[0],
    )

    cached = provider.get_config()
    provider._storage_client = FailingStorageClient()
    current_time[0] = 500.0

    refreshed = provider.get_config()

    assert refreshed is cached
