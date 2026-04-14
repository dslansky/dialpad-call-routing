from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DialpadTarget:
    target_id: str
    target_type: str


class DialpadTargetMap:
    def __init__(self, raw_data: dict) -> None:
        self._salesforce_user_targets = raw_data.get("salesforce_user_targets", {})
        self._logical_targets = raw_data.get("logical_targets", {})
        self._region_aliases = raw_data.get("region_aliases", {})

    @classmethod
    def load(cls, path: str) -> "DialpadTargetMap":
        return cls(json.loads(Path(path).read_text()))

    def get_salesforce_user_target(self, user_id: str | None) -> DialpadTarget | None:
        if not user_id:
            return None
        target = self._salesforce_user_targets.get(user_id)
        if not target:
            return None
        return DialpadTarget(
            target_id=str(target["target_id"]),
            target_type=target["target_type"],
        )

    def get_logical_target(self, key: str) -> DialpadTarget | None:
        target = self._logical_targets.get(key)
        if not target:
            return None
        return DialpadTarget(
            target_id=str(target["target_id"]),
            target_type=target["target_type"],
        )

    def resolve_region_alias(self, value: str | None) -> str | None:
        if not value:
            return None
        return self._region_aliases.get(value, value)
