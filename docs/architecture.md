# Architecture Notes

## Runtime Components

- `src/main.py`: synchronous Dialpad Call Router webhook
- `src/call_events.py`: asynchronous Dialpad call event webhook for spillover
- `src/salesforce_client.py`: Salesforce REST client with token caching
- `src/routing.py`: matrix-driven route selection
- `src/managed_config.py`: GCS-backed managed config loader with in-memory TTL caching
- `src/call_context_store.py`: Firestore-backed temporary call state for durable spillover

## Data Sources

- Salesforce `Contact` is the canonical caller record
- Google Cloud Storage holds the runtime routing rules and Dialpad target mappings
- Firestore holds short-lived per-call spillover state
- `Inbound Calling Matrix - Client.csv` and `Inbound Calling Matrix - Employee.csv` remain source matrices for bootstrap/export workflows
- site and region owner fields determine who should receive the call

## Deployment Model

- Google Cloud Function receives the initial route request
- Google Cloud Function or companion HTTP function receives call events
- runtime configuration is externalized through environment variables and JSON objects in GCS
- router and call-event webhooks coordinate spillover through a Firestore collection keyed by `call_id`

## Safety

- Salesforce discovery should stay read-only unless explicitly approved
- secrets should not be committed
- PHI should not be logged
- if GCS config refresh fails, the router should reuse the last in-memory config when possible and otherwise fall back safely
- expired call-state records should be ignored by the app and cleaned up via Firestore TTL on `expires_at`
