# Dialpad Call Routing

Serverless Dialpad inbound call routing that looks up callers in Salesforce and returns the right route in real time.

## Status

This repo is scaffolded for team handoff and implementation. It includes:

- Python Google Cloud Function entrypoints
- Routing and phone-normalization helpers
- Config templates
- Setup scripts for Dialpad router and call event subscriptions
- Starter tests
- Routing source CSVs for client and employee flows

## Planned Flow

1. Dialpad calls the router webhook.
2. The app normalizes the inbound phone number.
3. The app looks up the caller in Salesforce.
4. The app determines the primary target from contact type, onboarding step, status, and reason.
5. The app returns a Dialpad routing action immediately.
6. A separate Dialpad call event webhook handles spillover transfers if the first target does not answer.

## Project Layout

```text
src/
  main.py
  call_events.py
  salesforce_client.py
  routing.py
  config.py
  phone_normalization.py
  dialpad_responses.py
  call_context_store.py
  logging_utils.py
config/
  README.md
  dialpad_target_map.example.json
  contact_routing_matrix.client.example.json
  contact_routing_matrix.employee.example.json
scripts/
  setup_router.py
  setup_call_events.py
tests/
  test_phone_normalization.py
  test_routing.py
```

## Environment

See `.env.example` for runtime configuration placeholders.

## Notes

- Do not commit real secrets.
- Do not commit PHI.
- Salesforce should remain read-only during discovery and validation unless explicitly authorized.
