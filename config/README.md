# Config Files

These files are intentionally examples and placeholders.

- `contact_routing_matrix.client.example.json`: normalized client routing rules derived from the client CSV
- `contact_routing_matrix.employee.example.json`: normalized employee routing rules derived from the employee CSV
- `dialpad_target_map.example.json`: maps Salesforce users or logical owner keys to Dialpad targets

Production routing should load the real JSON files from GCS rather than from the repo.

Use `scripts/export_managed_config.py` to convert the workspace CSV matrices into the normalized JSON objects that the runtime expects to find in GCS.

Keep real environment-specific values outside git or in separately managed private config.
