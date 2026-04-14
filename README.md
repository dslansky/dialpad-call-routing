# Dialpad Call Routing

Serverless Dialpad inbound call routing that looks up callers in Salesforce and returns the right route in real time.

## Status

This repo now includes the first working implementation slice for real-time routing. It includes:

- Python Google Cloud Function entrypoints
- Matrix-driven routing and phone-normalization helpers
- Read-only Salesforce caller lookup and owner resolution
- Dialpad target mapping and spillover transfer client
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

This project currently expects a Python 3.10+ runtime for local development and deployment.

## Notes

- Do not commit real secrets.
- Do not commit PHI.
- Salesforce should remain read-only during discovery and validation unless explicitly authorized.
- The current spillover context store is in-memory, so production should move that state to a durable store before relying on failover across cold starts.
