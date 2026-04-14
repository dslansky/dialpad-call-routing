from __future__ import annotations

import requests


class DialpadClient:
    def __init__(self, api_key: str, session: requests.Session | None = None) -> None:
        self.api_key = api_key
        self.session = session or requests.Session()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def transfer_call(self, call_id: str, target_id: str, target_type: str) -> dict:
        response = self.session.post(
            f"https://dialpad.com/api/v2/call/{call_id}/transfer",
            headers=self._headers(),
            json={
                "transfer_to_target_id": int(target_id),
                "transfer_to_target_type": target_type,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
