from __future__ import annotations

import argparse
import json

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Dialpad call event subscription.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--webhook-url", required=True)
    parser.add_argument("--hook-id", required=True, help="A unique external identifier for this subscription.")
    args = parser.parse_args()

    payload = {
        "hook_id": args.hook_id,
        "target_url": args.webhook_url,
        "event_type": "call",
    }

    response = requests.post(
        "https://dialpad.com/api/v2/subscriptions",
        headers={
            "Authorization": f"Bearer {args.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
