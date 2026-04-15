# Dialpad Call Routing

Serverless Dialpad inbound call routing that looks up callers in Salesforce and returns the right route in real time.

## Status

This repo now includes the first working implementation slice for real-time routing. It includes:

- Python Google Cloud Function entrypoints
- Matrix-driven routing and phone-normalization helpers
- Read-only Salesforce caller lookup and owner resolution
- GCS-backed managed config loading with in-memory cache fallback
- Firestore-backed durable spillover call context
- Dialpad target mapping and spillover transfer client
- Config templates
- Setup scripts for Dialpad router and call event subscriptions
- Starter tests
- Routing source CSVs for client and employee flows

## Planned Flow

1. Dialpad calls the router webhook.
2. The app normalizes the inbound phone number.
3. The app loads routing rules and target mappings from Google Cloud Storage.
4. The app looks up the caller in Salesforce.
5. The app determines the primary target from contact type, onboarding step, status, and reason.
6. The app returns a Dialpad routing action immediately.
7. A separate Dialpad call event webhook handles spillover transfers if the first target does not answer.

## Managed Config

Production routing config should live in GCS as:

- `routing-rules-client.json`
- `routing-rules-employee.json`
- `dialpad-target-map.json`

The CSV matrices remain useful as source inputs, but the runtime no longer depends on them directly.

Use `scripts/export_managed_config.py` to convert the current CSV matrices into normalized JSON ready to upload to GCS.

## Project Layout

```text
src/
  main.py
  call_events.py
  salesforce_client.py
  routing.py
  config.py
  managed_config.py
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
  export_managed_config.py
tests/
  test_phone_normalization.py
  test_routing.py
  test_call_context_store.py
  test_call_events.py
  test_managed_config.py
```

## Environment

See `.env.example` for runtime configuration placeholders. The key managed-config settings are:

- `ROUTING_CONFIG_BUCKET`
- `ROUTING_RULES_CLIENT_OBJECT`
- `ROUTING_RULES_EMPLOYEE_OBJECT`
- `DIALPAD_TARGET_MAP_OBJECT`
- `ROUTING_CONFIG_CACHE_TTL_SECONDS`
- `CALL_CONTEXT_COLLECTION`
- `CALL_CONTEXT_TTL_SECONDS`

This project currently expects a Python 3.10+ runtime for local development and deployment.

See `docs/deployment.md` for the staged rollout checklist and current non-live deployment status.

## Notes

- Do not commit real secrets.
- Do not commit PHI.
- Salesforce should remain read-only during discovery and validation unless explicitly authorized.
- Spillover state is stored in Firestore so router and call-event webhooks can coordinate across cold starts and multiple instances.
- Configure Firestore TTL cleanup on the `expires_at` field for the `dialpad_call_contexts` collection, even though the app also ignores expired records itself.
- If a GCS refresh fails, the app uses the last cached config in memory when available; otherwise it falls back to IVR behavior.
