from src.salesforce_client import SalesforceClient


def test_build_matched_contact_uses_only_status_custom_for_routing() -> None:
    client = SalesforceClient(
        client_id="client-id",
        client_secret="client-secret",
        token_url="https://example.com/token",
        instance_url="https://example.my.salesforce.com",
    )

    matched = client.build_matched_contact(
        {
            "Id": "003-test",
            "lmry__Contact_Type__c": "Client",
            "lmry__Onboarding_Step__c": "Services Disrupted",
            "Status_custom__c": None,
            "lmry__Status__c": "Current",
            "Step_Reason__c": None,
            "lmry__Primary_Site__c": "a0f-test",
            "Region__c": "NC West",
        }
    )

    assert matched.status is None
