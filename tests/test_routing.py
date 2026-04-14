from pathlib import Path

from src.routing import MatchedContact, RoutingRule, determine_route, load_rules


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


def test_blank_step_reason_falls_back_when_exact_match_missing() -> None:
    contact = MatchedContact(
        contact_id="003x",
        contact_type="Client",
        onboarding_step="Assessment",
        status="Pending Authorization",
        step_reason="Unexpected Value",
        primary_site_id=None,
        region_value="NC West",
    )
    rules = [
        RoutingRule(
            contact_type="Client",
            onboarding_step="Assessment",
            status="Pending Authorization",
            step_reason=None,
            primary_owner_scope="region",
            primary_owner_field="Assessment_Administrator__c",
            spillover_owner_scope=None,
            spillover_owner_field=None,
        )
    ]

    decision = determine_route(contact, rules)

    assert decision.route_kind == "owner"
    assert decision.primary_owner_field == "Assessment_Administrator__c"


def test_load_rules_parses_csv_owner_mapping(tmp_path: Path) -> None:
    csv_path = tmp_path / "matrix.csv"
    csv_path.write_text(
        "Onboarding Step,Status*,Step Reason,Who Gets Notified,addit or spillover\n"
        "Training,In Training,,Operations Training Coordinator (region,Scheduler (region)\n",
        encoding="utf-8",
    )

    rules = load_rules(str(csv_path), contact_type="Employee")

    assert len(rules) == 1
    assert rules[0].primary_owner_scope == "region"
    assert rules[0].primary_owner_field == "Operations_Training_Coordinator__c"
    assert rules[0].spillover_owner_field == "Scheduler__c"
