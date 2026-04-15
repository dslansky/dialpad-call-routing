# Deployment Notes

## Current Status

- Firestore is enabled in project `dialpad-call-routing`.
- The default Firestore database exists in `us-central1`.
- TTL has been configured on `dialpad_call_contexts.expires_at` and may take time to finish propagating.
- No Cloud Functions are currently deployed in this project.
- Because no Cloud Functions are deployed and no Dialpad router has been pointed at a webhook URL in this project, this build is not live for production calls.

## Required Runtime Settings

Set these for the deployed function runtime:

- `DIALPAD_API_KEY`
- `SF_CLIENT_ID`
- `SF_CLIENT_SECRET`
- `SF_TOKEN_URL`
- `SF_INSTANCE_URL`
- `ROUTING_CONFIG_BUCKET=dialpad-call-routing-config`
- `ROUTING_RULES_CLIENT_OBJECT=routing-rules-client.json`
- `ROUTING_RULES_EMPLOYEE_OBJECT=routing-rules-employee.json`
- `DIALPAD_TARGET_MAP_OBJECT=dialpad-target-map.json`
- `ROUTING_CONFIG_CACHE_TTL_SECONDS=300`
- `CALL_CONTEXT_COLLECTION=dialpad_call_contexts`
- `CALL_CONTEXT_TTL_SECONDS=3600`

## Safe Rollout

To keep production traffic untouched until go-live:

1. Deploy the router and call-events functions first.
2. Verify the functions can read GCS managed config and Firestore state.
3. Test with a non-production webhook path or controlled Dialpad setup.
4. Only when ready, update the Dialpad Call Router to point inbound traffic at the deployed router webhook.

## Go-Live Reminder

The live fallback target is configured in GCS to send unknown or unroutable callers into the same Dialpad office path as calling `5162068900`.
