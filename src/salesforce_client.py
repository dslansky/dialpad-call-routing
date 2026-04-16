from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from src.phone_normalization import generate_phone_variants
from src.routing import MatchedContact


SITE_OWNER_FIELDS = [
    "Clinic_Director__c",
    "Operations_Manager__c",
    "Technician_Recruiter__c",
]

REGION_OWNER_FIELDS = [
    "Assessment_Administrator__c",
    "Back_End_Intake_Coordinator__c",
    "Onboarding_Specialist__c",
    "Operations_Leader__c",
    "Operations_Training_Coordinator__c",
    "Regional_Director__c",
    "Scheduler__c",
]

CONTACT_FIELDS = [
    "Id",
    "Name",
    "RecordType.Name",
    "lmry__Contact_Type__c",
    "lmry__Onboarding_Step__c",
    "Status_custom__c",
    "lmry__Status__c",
    "Step_Reason__c",
    "Region__c",
    "lmry__Primary_Site__c",
    "lmry__Primary_Site__r.Name",
    "lmry__Primary_Site__r.Region__c",
    "lmry__Primary_Site__r.Region__r.Name",
]
CONTACT_FIELDS.extend([f"lmry__Primary_Site__r.{field}" for field in SITE_OWNER_FIELDS])
CONTACT_FIELDS.extend([f"lmry__Primary_Site__r.Region__r.{field}" for field in REGION_OWNER_FIELDS])


@dataclass
class SalesforceToken:
    access_token: str
    expires_at: float


class SalesforceClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        instance_url: str,
        session: requests.Session | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.instance_url = instance_url.rstrip("/")
        self.session = session or requests.Session()
        self._token: SalesforceToken | None = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def _get_token(self) -> str:
        now = time.time()
        if self._token and self._token.expires_at > now + 60:
            return self._token.access_token

        response = self.session.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        access_token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 300))
        self._token = SalesforceToken(
            access_token=access_token,
            expires_at=now + expires_in,
        )
        return access_token

    def query(self, soql: str) -> dict:
        response = self.session.get(
            f"{self.instance_url}/services/data/v66.0/query",
            headers=self._headers(),
            params={"q": soql},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    def _query_all(self, soql: str) -> list[dict]:
        response = self.query(soql)
        records = list(response.get("records", []))
        next_url = response.get("nextRecordsUrl")
        while next_url:
            page = self.session.get(
                f"{self.instance_url}{next_url}",
                headers=self._headers(),
                timeout=5,
            )
            page.raise_for_status()
            payload = page.json()
            records.extend(payload.get("records", []))
            next_url = payload.get("nextRecordsUrl")
        return records

    def _escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    def _build_phone_where_clause(self, raw_phone: str) -> str:
        variants = sorted(generate_phone_variants(raw_phone))
        if not variants:
            return "Id = null"

        exact_fields = ["Phone", "MobilePhone", "HomePhone", "OtherPhone"]
        clauses: list[str] = []
        for field_name in exact_fields:
            quoted_values = ", ".join(f"'{self._escape(value)}'" for value in variants)
            clauses.append(f"{field_name} IN ({quoted_values})")

        digits_only = [value for value in variants if value.isdigit()]
        if digits_only:
            trailing_digits = max(digits_only, key=len)[-10:]
            clauses.extend(
                [
                    f"Phone LIKE '%{self._escape(trailing_digits)}'",
                    f"MobilePhone LIKE '%{self._escape(trailing_digits)}'",
                    f"HomePhone LIKE '%{self._escape(trailing_digits)}'",
                    f"OtherPhone LIKE '%{self._escape(trailing_digits)}'",
                ]
            )

        return " OR ".join(clauses)

    def find_contact_by_phone(self, raw_phone: str) -> dict | None:
        where_clause = self._build_phone_where_clause(raw_phone)
        soql = (
            f"SELECT {', '.join(CONTACT_FIELDS)} "
            f"FROM Contact WHERE {where_clause} "
            "ORDER BY LastModifiedDate DESC LIMIT 5"
        )
        records = self._query_all(soql)
        return records[0] if records else None

    def find_region_by_name(self, region_name: str) -> dict | None:
        escaped = self._escape(region_name)
        soql = (
            "SELECT Id, Name, "
            + ", ".join(REGION_OWNER_FIELDS)
            + f" FROM lmry__Region__c WHERE Name = '{escaped}' LIMIT 1"
        )
        records = self._query_all(soql)
        return records[0] if records else None

    def build_matched_contact(self, record: dict) -> MatchedContact:
        return MatchedContact(
            contact_id=record["Id"],
            contact_type=record.get("lmry__Contact_Type__c") or "Other",
            onboarding_step=record.get("lmry__Onboarding_Step__c"),
            status=record.get("Status_custom__c"),
            step_reason=record.get("Step_Reason__c"),
            primary_site_id=record.get("lmry__Primary_Site__c"),
            region_value=record.get("Region__c"),
        )

    def resolve_owner_user_id(
        self,
        record: dict,
        scope: str | None,
        field_name: str | None,
        region_name_override: str | None = None,
    ) -> str | None:
        if not scope or not field_name:
            return None
        if scope == "site":
            site = record.get("lmry__Primary_Site__r") or {}
            return site.get(field_name)
        if scope == "region":
            site = record.get("lmry__Primary_Site__r") or {}
            region = site.get("Region__r") or {}
            if region.get(field_name):
                return region.get(field_name)
            region_name = region_name_override or record.get("Region__c")
            if not region_name:
                return None
            region_record = self.find_region_by_name(region_name)
            if not region_record:
                return None
            return region_record.get(field_name)
        return None
