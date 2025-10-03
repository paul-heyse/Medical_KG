# Hot Configuration Change Runbook

## Purpose

Guide operators through applying configuration changes without restarting services.

## Prerequisites

- Admin JWT token with `admin:*` scope
- Access to `/admin/reload` endpoint
- Monitoring dashboard access

## Procedure

### 1. Prepare Configuration Change

```bash
# Edit configuration file
vim /path/to/config.yaml

# Validate schema
python -c "
from Medical_KG.config.manager import ConfigManager
manager = ConfigManager()
manager.reload()
print('✓ Config valid')
"
```

### 2. Apply Hot Reload

```bash
# Request hot reload with JWT
curl -X POST https://api.medkg.example.com/admin/reload \
  -H "Authorization: Bearer ${ADMIN_JWT}" \
  -H "Content-Type: application/json"

# Expected response:
# {
#   "config_version": "2024-10-03T14:30:00Z",
#   "hash": "abc123def456"
# }
```

### 3. Verify Configuration Applied

```bash
# Check /version endpoint
curl https://api.medkg.example.com/version

# Verify config_version matches reload response
# Expected output includes new config_version
```

### 4. Monitor Metrics

```bash
# Check Prometheus metric
curl https://prometheus.example.com/api/v1/query?query=config_version

# Verify metric updated within 30 seconds
```

### 5. Verify Application Behavior

```bash
# Example: If you changed retrieval weights
# Run test query and verify new blend scores
curl -X POST https://api.medkg.example.com/retrieve \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{
    "query": "metformin efficacy diabetes",
    "topK": 5,
    "intent": "endpoint"
  }'

# Check component_scores in response to verify new weights applied
```

## Rollback

If configuration causes issues:

```bash
# Revert config.yaml to previous version
git checkout HEAD~1 config/config.yaml

# Apply reload again
curl -X POST https://api.medkg.example.com/admin/reload \
  -H "Authorization: Bearer ${ADMIN_JWT}"
```

## Common Issues

### Issue: 401 Unauthorized

**Cause**: Invalid or expired JWT
**Solution**: Generate new admin JWT with correct scopes

### Issue: 403 Forbidden

**Cause**: JWT lacks `admin:*` scope
**Solution**: Use JWT with admin permissions

### Issue: 400 Bad Request

**Cause**: Invalid configuration syntax
**Solution**: Validate config locally first using schema validation

### Issue: Config not applied

**Cause**: File permissions or cached values
**Solution**: Check file readable by service; verify no cached config in memory

## Related

- [Scale Retrieval Runbook](./02-scale-retrieval.md)
- [Configuration Documentation](../../docs/configuration.md)
