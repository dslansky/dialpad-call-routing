# Architecture Notes

## Runtime Components

- `src/main.py`: synchronous Dialpad Call Router webhook
- `src/call_events.py`: asynchronous Dialpad call event webhook for spillover
- `src/salesforce_client.py`: Salesforce REST client with token caching
- `src/routing.py`: matrix-driven route selection

## Data Sources

- Salesforce `Contact` is the canonical caller record
- `Inbound Calling Matrix - Client.csv` and `Inbound Calling Matrix - Employee.csv` are the source routing matrices
- site and region owner fields determine who should receive the call

## Deployment Model

- Google Cloud Function receives the initial route request
- Google Cloud Function or companion HTTP function receives call events
- runtime configuration is externalized through environment variables and JSON mapping files

## Safety

- Salesforce discovery should stay read-only unless explicitly approved
- secrets should not be committed
- PHI should not be logged
