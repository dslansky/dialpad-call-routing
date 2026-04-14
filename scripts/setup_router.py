from __future__ import annotations

import argparse
import json

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Dialpad API call router.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--office-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--routing-url", required=True)
    parser.add_argument("--default-target-id", required=True)
    parser.add_argument("--default-target-type", required=True)
    args = parser.parse_args()

    payload = {
        "name": args.name,
        "office_id": int(args.office_id),
        "routing_url": args.routing_url,
        "default_target_id": int(args.default_target_id),
        "default_target_type": args.default_target_type,
    }

    response = requests.post(
        "https://dialpad.com/api/v2/callrouters",
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
