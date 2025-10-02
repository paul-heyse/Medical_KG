# Hot Reload Procedure

The `/admin/reload` endpoint applies non-breaking configuration updates without a service restart.

## Prerequisites

- Valid admin JWT containing the `admin:config` scope.
- Updated configuration files (`config.yaml`, environment overlay, and/or `config-override.yaml`).
- Successful run of `med config validate --strict`.

## Steps

1. Ensure `CONFIG_ENV` is set to the target environment on the running service.
2. Apply file changes and commit to version control (optional but recommended).
3. Issue the reload request:

```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  https://<host>/admin/reload
```

4. On success the API returns:

```json
{ "config_version": "2024-06-01T12:00:00+0000+abc123456789", "hash": "..." }
```

5. Watch the `config_info` metric for the new version/hash pair.

## Breaking Changes

The loader rejects changes to `embeddings.vllm_api_base` and `kg.neo4j_uri` during hot reload. When these fields change the endpoint returns HTTP 400 with the message `Breaking change requires restart`. Restart the service with the updated configuration to proceed.

## Safe Changes

The following settings can be applied via hot reload:

- Retrieval fusion weights and reranker toggles.
- API and source rate limits.
- Feature flags.
- Logging level and metrics push interval.

## Validation on Reload

Every reload re-runs schema validation, Pydantic model validation, and licensing checks. The payload is rejected if:

- Fusion weights do not sum to ~1.0.
- Chunking profiles use invalid token counts.
- A vocabulary requiring a license is enabled without authorization in `policy.yaml`.
