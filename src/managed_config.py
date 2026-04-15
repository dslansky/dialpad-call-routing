from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from src.config import Settings
from src.routing import RoutingRule, load_rules_from_data
from src.target_mapping import DialpadTargetMap

try:
    from google.cloud import storage
except ImportError:  # pragma: no cover - exercised only when dependency is missing locally.
    storage = None


@dataclass(frozen=True)
class ManagedRoutingConfig:
    client_rules: list[RoutingRule]
    employee_rules: list[RoutingRule]
    target_map: DialpadTargetMap

    def rules_for_contact_type(self, contact_type: str) -> list[RoutingRule]:
        if contact_type == "Client":
            return self.client_rules
        if contact_type == "Employee":
            return self.employee_rules
        return []


@dataclass
class CachedManagedRoutingConfig:
    config: ManagedRoutingConfig
    expires_at: float


class GcsManagedConfigProvider:
    def __init__(
        self,
        settings: Settings,
        storage_client: Any | None = None,
        time_fn: Any | None = None,
    ) -> None:
        self.bucket_name = settings.routing_config_bucket
        self.client_rules_object = settings.client_rules_object
        self.employee_rules_object = settings.employee_rules_object
        self.target_map_object = settings.dialpad_target_map_object
        self.cache_ttl_seconds = settings.routing_config_cache_ttl_seconds
        self._time_fn = time_fn or time.time
        self._cached: CachedManagedRoutingConfig | None = None

        if storage_client is not None:
            self._storage_client = storage_client
        else:
            if storage is None:
                raise RuntimeError("google-cloud-storage must be installed for managed config loading")
            self._storage_client = storage.Client()

    def get_config(self) -> ManagedRoutingConfig:
        now = self._time_fn()
        if self._cached and self._cached.expires_at > now:
            return self._cached.config
        return self._refresh_config(now)

    def _refresh_config(self, now: float) -> ManagedRoutingConfig:
        try:
            config = self._load_from_gcs()
        except Exception:
            if self._cached:
                return self._cached.config
            raise

        self._cached = CachedManagedRoutingConfig(
            config=config,
            expires_at=now + max(self.cache_ttl_seconds, 1),
        )
        return config

    def _load_from_gcs(self) -> ManagedRoutingConfig:
        if not self.bucket_name:
            raise RuntimeError("ROUTING_CONFIG_BUCKET is required")
        bucket = self._storage_client.bucket(self.bucket_name)
        client_rules_data = self._download_json(bucket, self.client_rules_object)
        employee_rules_data = self._download_json(bucket, self.employee_rules_object)
        target_map_data = self._download_json(bucket, self.target_map_object)
        return ManagedRoutingConfig(
            client_rules=load_rules_from_data(client_rules_data, contact_type="Client"),
            employee_rules=load_rules_from_data(employee_rules_data, contact_type="Employee"),
            target_map=DialpadTargetMap.from_data(target_map_data),
        )

    def _download_json(self, bucket: Any, object_name: str) -> Any:
        if not object_name:
            raise RuntimeError("Managed config object name is required")
        blob = bucket.blob(object_name)
        return json.loads(blob.download_as_text())
