from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MatchedContact:
    contact_id: str
    contact_type: str
    onboarding_step: str | None
    status: str | None
    step_reason: str | None
    primary_site_id: str | None
    region_value: str | None


@dataclass(frozen=True)
class RoutingRule:
    contact_type: str
    onboarding_step: str | None
    status: str | None
    step_reason: str | None
    primary_owner_scope: str | None
    primary_owner_field: str | None
    spillover_owner_scope: str | None
    spillover_owner_field: str | None


@dataclass(frozen=True)
class RoutingDecision:
    matched: bool
    route_kind: str
    primary_owner_scope: str | None = None
    primary_owner_field: str | None = None
    spillover_owner_scope: str | None = None
    spillover_owner_field: str | None = None


def load_rules(path: str) -> list[RoutingRule]:
    data = json.loads(Path(path).read_text())
    return [RoutingRule(**row) for row in data]


def determine_route(contact: MatchedContact | None, rules: list[RoutingRule]) -> RoutingDecision:
    if contact is None:
        return RoutingDecision(matched=False, route_kind="ivr")

    if contact.contact_type in {"Other", "Referring Provider"}:
        return RoutingDecision(matched=True, route_kind="ivr")

    for rule in rules:
        if rule.contact_type != contact.contact_type:
            continue
        if rule.onboarding_step != (contact.onboarding_step or None):
            continue
        if rule.status != (contact.status or None):
            continue
        if (rule.step_reason or "") != (contact.step_reason or ""):
            continue
        return RoutingDecision(
            matched=True,
            route_kind="owner",
            primary_owner_scope=rule.primary_owner_scope,
            primary_owner_field=rule.primary_owner_field,
            spillover_owner_scope=rule.spillover_owner_scope,
            spillover_owner_field=rule.spillover_owner_field,
        )

    return RoutingDecision(matched=True, route_kind="ivr")
