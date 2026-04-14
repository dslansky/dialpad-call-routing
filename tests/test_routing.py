from src.routing import MatchedContact, RoutingRule, determine_route


def test_other_contact_defaults_to_ivr() -> None:
    contact = MatchedContact(
        contact_id="003x",
        contact_type="Other",
        onboarding_step=None,
        status=None,
        step_reason=None,
        primary_site_id=None,
        region_value=None,
    )

    decision = determine_route(contact, [])

    assert decision.route_kind == "ivr"


def test_matching_rule_returns_owner_decision() -> None:
    contact = MatchedContact(
        contact_id="003x",
        contact_type="Client",
        onboarding_step="New",
        status="Never Contacted",
        step_reason="",
        primary_site_id=None,
        region_value="NC West",
    )
    rules = [
        RoutingRule(
            contact_type="Client",
            onboarding_step="New",
            status="Never Contacted",
            step_reason="",
            primary_owner_scope="region",
            primary_owner_field="Back_End_Intake_Coordinator__c",
            spillover_owner_scope=None,
            spillover_owner_field=None,
        )
    ]

    decision = determine_route(contact, rules)

    assert decision.route_kind == "owner"
    assert decision.primary_owner_scope == "region"
    assert decision.primary_owner_field == "Back_End_Intake_Coordinator__c"
