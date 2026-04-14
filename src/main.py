from __future__ import annotations

from typing import Any

from src.call_context_store import CallContext, InMemoryCallContextStore
from src.config import Settings
from src.dialpad_responses import end_response, route_response
from src.logging_utils import log_event
from src.routing import determine_route, load_rules
from src.salesforce_client import SalesforceClient
from src.target_mapping import DialpadTargetMap


CALL_CONTEXT_STORE = InMemoryCallContextStore()
_SETTINGS: Settings | None = None
_CLIENT_RULES = None
_EMPLOYEE_RULES = None
_TARGET_MAP: DialpadTargetMap | None = None
_SALESFORCE_CLIENT: SalesforceClient | None = None


def _get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings.from_env()
    return _SETTINGS


def _get_client_rules():
    global _CLIENT_RULES
    if _CLIENT_RULES is None:
        settings = _get_settings()
        _CLIENT_RULES = load_rules(settings.client_matrix_path, contact_type="Client")
    return _CLIENT_RULES


def _get_employee_rules():
    global _EMPLOYEE_RULES
    if _EMPLOYEE_RULES is None:
        settings = _get_settings()
        _EMPLOYEE_RULES = load_rules(settings.employee_matrix_path, contact_type="Employee")
    return _EMPLOYEE_RULES


def _get_target_map() -> DialpadTargetMap:
    global _TARGET_MAP
    if _TARGET_MAP is None:
        settings = _get_settings()
        _TARGET_MAP = DialpadTargetMap.load(settings.dialpad_target_map_path)
    return _TARGET_MAP


def _get_salesforce_client() -> SalesforceClient:
    global _SALESFORCE_CLIENT
    if _SALESFORCE_CLIENT is None:
        settings = _get_settings()
        _SALESFORCE_CLIENT = SalesforceClient(
            client_id=settings.sf_client_id,
            client_secret=settings.sf_client_secret,
            token_url=settings.sf_token_url,
            instance_url=settings.sf_instance_url,
        )
    return _SALESFORCE_CLIENT


def _ivr_response(settings: Settings) -> dict:
    target_map = _get_target_map()
    logical_target = target_map.get_logical_target("ivr_fallback")
    if logical_target:
        return route_response(logical_target.target_id, logical_target.target_type)
    if settings.ivr_fallback_target and settings.ivr_fallback_target_type:
        return route_response(settings.ivr_fallback_target, settings.ivr_fallback_target_type)
    return end_response("No IVR fallback target is configured.")


def _rules_for_contact_type(contact_type: str):
    if contact_type == "Client":
        return _get_client_rules()
    if contact_type == "Employee":
        return _get_employee_rules()
    return []


def dialpad_router(request: Any):
    settings = _get_settings()
    payload = request.get_json(silent=True) or {}
    call_id = payload.get("call_id")
    external_number = payload.get("external_number")

    log_event(
        "router_webhook_received",
        call_id=call_id,
        external_number=external_number,
    )

    if not external_number:
        log_event("router_missing_external_number", call_id=call_id)
        return _ivr_response(settings)

    salesforce_client = _get_salesforce_client()
    target_map = _get_target_map()

    try:
        record = salesforce_client.find_contact_by_phone(external_number)
    except Exception as exc:
        log_event("salesforce_lookup_failed", call_id=call_id, error=str(exc))
        return _ivr_response(settings)

    if not record:
        log_event("router_contact_not_found", call_id=call_id)
        return _ivr_response(settings)

    matched_contact = salesforce_client.build_matched_contact(record)
    rules = _rules_for_contact_type(matched_contact.contact_type)
    decision = determine_route(matched_contact, rules)

    if decision.route_kind != "owner":
        log_event(
            "router_ivr_decision",
            call_id=call_id,
            contact_id=matched_contact.contact_id,
            contact_type=matched_contact.contact_type,
        )
        return _ivr_response(settings)

    region_name = target_map.resolve_region_alias(matched_contact.region_value)
    primary_user_id = salesforce_client.resolve_owner_user_id(
        record,
        decision.primary_owner_scope,
        decision.primary_owner_field,
        region_name_override=region_name,
    )
    primary_target = target_map.get_salesforce_user_target(primary_user_id)

    if not primary_target:
        log_event(
            "router_primary_target_missing",
            call_id=call_id,
            contact_id=matched_contact.contact_id,
            owner_scope=decision.primary_owner_scope,
            owner_field=decision.primary_owner_field,
            salesforce_user_id=primary_user_id,
        )
        return _ivr_response(settings)

    spillover_user_id = salesforce_client.resolve_owner_user_id(
        record,
        decision.spillover_owner_scope,
        decision.spillover_owner_field,
        region_name_override=region_name,
    )
    spillover_target = target_map.get_salesforce_user_target(spillover_user_id)

    if call_id:
        CALL_CONTEXT_STORE.put(
            CallContext(
                call_id=call_id,
                contact_id=matched_contact.contact_id,
                contact_type=matched_contact.contact_type,
                primary_target_id=primary_target.target_id,
                primary_target_type=primary_target.target_type,
                spillover_target_id=spillover_target.target_id if spillover_target else None,
                spillover_target_type=spillover_target.target_type if spillover_target else None,
            )
        )

    log_event(
        "router_owner_decision",
        call_id=call_id,
        contact_id=matched_contact.contact_id,
        contact_type=matched_contact.contact_type,
        primary_owner_field=decision.primary_owner_field,
        primary_owner_scope=decision.primary_owner_scope,
        spillover_owner_field=decision.spillover_owner_field,
        spillover_owner_scope=decision.spillover_owner_scope,
    )
    return route_response(primary_target.target_id, primary_target.target_type)
