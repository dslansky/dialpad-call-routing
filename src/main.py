from __future__ import annotations

from typing import Any

from src.call_context_store import CallContext, FirestoreCallContextStore
from src.config import Settings
from src.dialpad_responses import end_response, route_response
from src.logging_utils import log_event
from src.managed_config import GcsManagedConfigProvider, ManagedRoutingConfig
from src.routing import determine_route
from src.salesforce_client import SalesforceClient


_SETTINGS: Settings | None = None
_CONFIG_PROVIDER: GcsManagedConfigProvider | None = None
_SALESFORCE_CLIENT: SalesforceClient | None = None
_CALL_CONTEXT_STORE: FirestoreCallContextStore | None = None


def _get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings.from_env()
    return _SETTINGS


def _get_config_provider() -> GcsManagedConfigProvider:
    global _CONFIG_PROVIDER
    if _CONFIG_PROVIDER is None:
        settings = _get_settings()
        _CONFIG_PROVIDER = GcsManagedConfigProvider(settings)
    return _CONFIG_PROVIDER


def _get_managed_config() -> ManagedRoutingConfig:
    return _get_config_provider().get_config()


def _get_call_context_store() -> FirestoreCallContextStore:
    global _CALL_CONTEXT_STORE
    if _CALL_CONTEXT_STORE is None:
        settings = _get_settings()
        _CALL_CONTEXT_STORE = FirestoreCallContextStore(
            collection_name=settings.call_context_collection,
            ttl_seconds=settings.call_context_ttl_seconds,
        )
    return _CALL_CONTEXT_STORE


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


def _ivr_response(settings: Settings, managed_config: ManagedRoutingConfig | None = None) -> dict:
    if managed_config is not None:
        logical_target = managed_config.target_map.get_logical_target("ivr_fallback")
        if logical_target:
            return route_response(logical_target.target_id, logical_target.target_type)
    if settings.ivr_fallback_target and settings.ivr_fallback_target_type:
        return route_response(settings.ivr_fallback_target, settings.ivr_fallback_target_type)
    return end_response("No IVR fallback target is configured.")


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
    try:
        managed_config = _get_managed_config()
    except Exception as exc:
        log_event("managed_config_load_failed", call_id=call_id, error=str(exc))
        return _ivr_response(settings)

    try:
        record = salesforce_client.find_contact_by_phone(external_number)
    except Exception as exc:
        log_event("salesforce_lookup_failed", call_id=call_id, error=str(exc))
        return _ivr_response(settings, managed_config=managed_config)

    if not record:
        log_event("router_contact_not_found", call_id=call_id)
        return _ivr_response(settings, managed_config=managed_config)

    matched_contact = salesforce_client.build_matched_contact(record)
    rules = managed_config.rules_for_contact_type(matched_contact.contact_type)
    decision = determine_route(matched_contact, rules)

    if decision.route_kind != "owner":
        log_event(
            "router_ivr_decision",
            call_id=call_id,
            contact_id=matched_contact.contact_id,
            contact_type=matched_contact.contact_type,
        )
        return _ivr_response(settings, managed_config=managed_config)

    target_map = managed_config.target_map
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
        return _ivr_response(settings, managed_config=managed_config)

    spillover_user_id = salesforce_client.resolve_owner_user_id(
        record,
        decision.spillover_owner_scope,
        decision.spillover_owner_field,
        region_name_override=region_name,
    )
    spillover_target = target_map.get_salesforce_user_target(spillover_user_id)

    if call_id:
        _get_call_context_store().put(
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
