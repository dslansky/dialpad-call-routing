from __future__ import annotations

import time
from dataclasses import dataclass

import requests


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
        access_token = self._get_token()
        response = self.session.get(
            f"{self.instance_url}/services/data/v66.0/query",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"q": soql},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
