from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.routing import load_rules, rules_to_json_ready


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert routing matrices into normalized JSON for managed GCS config."
    )
    parser.add_argument(
        "--client-csv",
        default="Inbound Calling Matrix - Client.csv",
        help="Path to the client routing matrix CSV.",
    )
    parser.add_argument(
        "--employee-csv",
        default="Inbound Calling Matrix - Employee.csv",
        help="Path to the employee routing matrix CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="build/managed-config",
        help="Directory for generated JSON output.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client_rules = load_rules(args.client_csv, contact_type="Client")
    employee_rules = load_rules(args.employee_csv, contact_type="Employee")

    _write_json(output_dir / "routing-rules-client.json", rules_to_json_ready(client_rules))
    _write_json(
        output_dir / "routing-rules-employee.json",
        rules_to_json_ready(employee_rules),
    )


if __name__ == "__main__":
    main()
