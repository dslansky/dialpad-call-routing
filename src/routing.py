from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


OWNER_FIELD_MAP = {
    "assessment administrator (region)": ("region", "Assessment_Administrator__c"),
    "assessment administrartor (region)": ("region", "Assessment_Administrator__c"),
    "back end intake coordinator (region)": ("region", "Back_End_Intake_Coordinator__c"),
    "om (site)": ("site", "Operations_Manager__c"),
    "onboarding specialist (site)": ("region", "Onboarding_Specialist__c"),
    "operations training coordinator (region": ("region", "Operations_Training_Coordinator__c"),
    "operations training coordinator (region)": ("region", "Operations_Training_Coordinator__c"),
    "scheduler (region)": ("region", "Scheduler__c"),
    "technician recruiter (site)": ("site", "Technician_Recruiter__c"),
}


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


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_owner_descriptor(value: str | None) -> tuple[str | None, str | None]:
    descriptor = (value or "").strip().lower()
    if not descriptor:
        return None, None
    return OWNER_FIELD_MAP.get(descriptor, (None, None))


def _normalize_json_rule(row: Mapping[str, object], contact_type: str | None = None) -> RoutingRule:
    normalized_contact_type = _clean(str(row.get("contact_type") or contact_type or ""))
    if not normalized_contact_type:
        raise ValueError("Routing rule is missing contact_type")
    return RoutingRule(
        contact_type=normalized_contact_type,
        onboarding_step=_clean(str(row["onboarding_step"])) if row.get("onboarding_step") is not None else None,
        status=_clean(str(row["status"])) if row.get("status") is not None else None,
        step_reason=_clean(str(row["step_reason"])) if row.get("step_reason") is not None else None,
        primary_owner_scope=_clean(str(row["primary_owner_scope"])) if row.get("primary_owner_scope") is not None else None,
        primary_owner_field=_clean(str(row["primary_owner_field"])) if row.get("primary_owner_field") is not None else None,
        spillover_owner_scope=_clean(str(row["spillover_owner_scope"])) if row.get("spillover_owner_scope") is not None else None,
        spillover_owner_field=_clean(str(row["spillover_owner_field"])) if row.get("spillover_owner_field") is not None else None,
    )


def load_rules_from_data(data: list[Mapping[str, object]], contact_type: str | None = None) -> list[RoutingRule]:
    return [_normalize_json_rule(row, contact_type=contact_type) for row in data]


def _parse_json_rules(path: Path, contact_type: str | None = None) -> list[RoutingRule]:
    data = json.loads(path.read_text())
    return load_rules_from_data(data, contact_type=contact_type)


def _parse_csv_rules(path: Path, contact_type: str) -> list[RoutingRule]:
    rules: list[RoutingRule] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            primary_scope, primary_field = _normalize_owner_descriptor(row.get("Who Gets Notified"))
            spillover_scope, spillover_field = _normalize_owner_descriptor(
                row.get("addit or spillover")
            )
            rules.append(
                RoutingRule(
                    contact_type=contact_type,
                    onboarding_step=_clean(row.get("Onboarding Step")),
                    status=_clean(row.get("Status*")),
                    step_reason=_clean(row.get("Step Reason")),
                    primary_owner_scope=primary_scope,
                    primary_owner_field=primary_field,
                    spillover_owner_scope=spillover_scope,
                    spillover_owner_field=spillover_field,
                )
            )
    return rules


def load_rules(path: str, contact_type: str | None = None) -> list[RoutingRule]:
    file_path = Path(path)
    if file_path.suffix.lower() == ".json":
        return _parse_json_rules(file_path, contact_type=contact_type)
    if file_path.suffix.lower() == ".csv":
        if not contact_type:
            raise ValueError("contact_type is required when loading CSV routing rules")
        return _parse_csv_rules(file_path, contact_type)
    raise ValueError(f"Unsupported rule file type: {file_path.suffix}")


def rules_to_json_ready(rules: Iterable[RoutingRule]) -> list[dict[str, str | None]]:
    return [
        {
            "contact_type": rule.contact_type,
            "onboarding_step": rule.onboarding_step,
            "status": rule.status,
            "step_reason": rule.step_reason,
            "primary_owner_scope": rule.primary_owner_scope,
            "primary_owner_field": rule.primary_owner_field,
            "spillover_owner_scope": rule.spillover_owner_scope,
            "spillover_owner_field": rule.spillover_owner_field,
        }
        for rule in rules
    ]


def _matches(rule_value: str | None, contact_value: str | None) -> bool:
    if rule_value is None:
        return True
    return rule_value == contact_value


def _candidate_rules(contact: MatchedContact, rules: Iterable[RoutingRule]) -> list[RoutingRule]:
    candidates: list[RoutingRule] = []
    for rule in rules:
        if rule.contact_type != contact.contact_type:
            continue
        if not _matches(rule.onboarding_step, contact.onboarding_step):
            continue
        if not _matches(rule.status, contact.status):
            continue
        candidates.append(rule)
    return candidates


def determine_route(contact: MatchedContact | None, rules: list[RoutingRule]) -> RoutingDecision:
    if contact is None:
        return RoutingDecision(matched=False, route_kind="ivr")

    if contact.contact_type in {"Other", "Referring Provider"}:
        return RoutingDecision(matched=True, route_kind="ivr")

    matching_rules = _candidate_rules(contact, rules)
    if not matching_rules:
        return RoutingDecision(matched=True, route_kind="ivr")

    exact_reason = next(
        (rule for rule in matching_rules if rule.step_reason == contact.step_reason),
        None,
    )
    fallback_reason = next((rule for rule in matching_rules if rule.step_reason is None), None)
    selected_rule = exact_reason or fallback_reason

    if selected_rule:
        return RoutingDecision(
            matched=True,
            route_kind="owner",
            primary_owner_scope=selected_rule.primary_owner_scope,
            primary_owner_field=selected_rule.primary_owner_field,
            spillover_owner_scope=selected_rule.spillover_owner_scope,
            spillover_owner_field=selected_rule.spillover_owner_field,
        )

    return RoutingDecision(matched=True, route_kind="ivr")
