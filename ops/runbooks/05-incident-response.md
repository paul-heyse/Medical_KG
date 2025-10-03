# Incident Response Playbook

## Purpose

Guide on-call engineers through incident triage, escalation, communication, and resolution.

## Severity Definitions

### P1 - Critical (Service Down)

- **Impact**: Complete service outage or data loss
- **Examples**:
  - API returning 100% errors
  - Data corruption detected
  - Security breach
- **Response Time**: Immediate (page on-call)
- **Communication**: Status page + Slack #incidents
- **Escalation**: After 15 minutes, page secondary

### P2 - High (SLO Breach)

- **Impact**: Degraded performance affecting users
- **Examples**:
  - P95 latency > 900ms for 5+ minutes
  - Error rate > 5%
  - Critical component down (OpenSearch, Neo4j)
- **Response Time**: 15 minutes
- **Communication**: Slack #incidents
- **Escalation**: After 30 minutes, page secondary

### P3 - Medium (Warning Threshold)

- **Impact**: Warning signals, not yet user-facing
- **Examples**:
  - EL acceptance < 0.6 hourly
  - Disk space > 80%
  - Replica count at max
- **Response Time**: 1 hour
- **Communication**: Slack #ops-alerts
- **Escalation**: During business hours only

### P4 - Low (Maintenance)

- **Impact**: No user impact, planned work
- **Examples**:
  - Scheduled index rebuild
  - Non-critical updates
  - Documentation updates
- **Response Time**: Next business day
- **Communication**: Slack #ops
- **Escalation**: None

## Incident Response Steps

### 1. Acknowledge Alert (< 5 minutes)

```bash
# Acknowledge in PagerDuty/OpsGenie
# Post in Slack
/incident-bot ack <incident_id>

# Claim incident
echo "I'm on it" | slack-post #incidents
```

### 2. Assess Severity (< 10 minutes)

- Check monitoring dashboards
- Verify user impact (check API metrics)
- Determine affected components
- Classify severity (P1-P4)

```bash
# Quick health check
curl https://api.medkg.example.com/health

# Check recent errors
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=rate(http_requests_total{code=~"5.."}[5m])' \
  | jq '.data.result'

# Check P95 latency
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))' \
  | jq '.data.result[0].value[1]'
```

### 3. Communication

#### P1/P2 - Start Incident Thread

```
#incidents
🔴 INCIDENT - P1 - API Down
**Status**: Investigating
**Impact**: 100% error rate on /retrieve
**Started**: 2024-10-03 14:23 UTC
**Lead**: @alice
**Link**: https://status.example.com/incidents/123
```

#### Update Status Page (P1/P2 only)

- Navigate to status.example.com/admin
- Create incident
- Select affected components
- Post initial update: "Investigating elevated error rates"

### 4. Investigate Root Cause

Use relevant runbooks:

```bash
# Check recent deployments
kubectl get events -n medkg --sort-by='.lastTimestamp' | head -20

# Check pod health
kubectl get pods -n medkg

# Check logs
kubectl logs -n medkg -l app=retrieval --tail=100 --since=10m

# Check OpenSearch
curl https://opensearch:9200/_cluster/health

# Check Neo4j
curl http://neo4j:7474/db/data/
```

**Common Root Causes**:

- Recent deployment
- Configuration change
- Resource exhaustion
- Dependency failure
- Traffic spike

### 5. Mitigation

Apply immediate fixes:

```bash
# Example: Rollback deployment
kubectl rollout undo deployment/retrieval -n medkg

# Example: Scale up
kubectl scale deployment retrieval -n medkg --replicas=10

# Example: Restart service
kubectl rollout restart deployment/retrieval -n medkg

# Example: Disable feature
# Edit config, apply hot reload
curl -X POST https://api.medkg.example.com/admin/reload \
  -H "Authorization: Bearer ${ADMIN_JWT}"
```

### 6. Verify Resolution

```bash
# Check error rate
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=rate(http_requests_total{code=~"5.."}[5m])' \
  | jq '.data.result[0].value[1]'

# Should return to baseline (< 0.01)

# Check latency
curl -s 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))' \
  | jq '.data.result[0].value[1]'

# Should be < 900ms

# Test end-to-end
curl -X POST https://api.medkg.example.com/retrieve \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{"query": "diabetes treatment", "topK": 5}'
```

### 7. Communication - Resolution

```
#incidents
✅ RESOLVED - P1 - API Down
**Duration**: 23 minutes
**Root Cause**: OOM in retrieval pods due to memory leak
**Mitigation**: Restarted pods, increased memory limits
**Follow-up**: Post-mortem scheduled for 2024-10-04 10:00 UTC
**Link**: https://docs.example.com/incidents/2024-10-03-api-down
```

Update status page:

- Mark incident as resolved
- Post resolution message
- Thank users for patience

### 8. Post-Mortem (P1/P2 within 48 hours)

Schedule post-mortem meeting with stakeholders.

## Post-Mortem Template

Create document: `docs/incidents/YYYY-MM-DD-<title>.md`

```markdown
# Incident: <Title>

## Summary
One-line summary of incident.

## Impact
- **Duration**: X hours Y minutes
- **Users Affected**: Estimate or metrics
- **Services**: List affected services
- **Data Loss**: Yes/No, details if applicable

## Timeline (UTC)
- 14:23 - First alert received
- 14:25 - On-call engineer acknowledged
- 14:30 - Root cause identified (OOM)
- 14:35 - Mitigation applied (restart + config)
- 14:46 - Service fully recovered
- 14:50 - Incident resolved

## Root Cause
Detailed explanation of what caused the incident.

**Contributing Factors**:
- Factor 1
- Factor 2

## Resolution
What was done to resolve the incident.

## What Went Well
- Quick acknowledgment
- Effective use of runbooks
- Clear communication

## What Went Poorly
- Delayed escalation
- Monitoring gap (no memory alert)

## Action Items
- [ ] Add memory alerts for all services (@alice, 2024-10-05)
- [ ] Increase memory limits in production (@bob, 2024-10-04)
- [ ] Update runbook with OOM scenario (@alice, 2024-10-06)
- [ ] Schedule load test to reproduce (@charlie, 2024-10-10)

## Lessons Learned
- Memory monitoring critical for long-running services
- Memory leak introduced in recent release needs fix
```

## On-Call Rotation

### Schedule

- **Primary**: Week 1 - Alice, Week 2 - Bob, Week 3 - Charlie
- **Secondary**: Always one week behind primary
- **Handoff**: Fridays 4pm UTC

### Handoff Checklist

- [ ] Review open incidents
- [ ] Review recent changes/deployments
- [ ] Review upcoming maintenance windows
- [ ] Verify access to all systems
- [ ] Test paging system

### On-Call Responsibilities

- Respond to pages within 5 minutes
- Acknowledge alerts within 15 minutes
- Follow incident response playbook
- Escalate if needed
- Document all actions
- Complete post-mortem for P1/P2

## Escalation Paths

### Technical Escalation

1. **Primary On-Call** (immediate)
2. **Secondary On-Call** (15 min for P1, 30 min for P2)
3. **Engineering Manager** (30 min for P1)
4. **VP Engineering** (1 hour for P1)

### Business Escalation

1. **Product Manager** (for user communication)
2. **Head of Product** (major incidents)
3. **CEO** (security breach, data loss)

### External Escalation

- **AWS Support**: For infrastructure issues
- **OpenSearch**: For search engine issues
- **Neo4j Support**: For database issues

## Contact Information

```yaml
primary_oncall: check_pagerduty
secondary_oncall: check_pagerduty
engineering_manager: manager@example.com
vp_engineering: vp@example.com
security_team: security@example.com
aws_support: support.aws.amazon.com (Enterprise Support)
```

## Tools Access Checklist

- [ ] Kubernetes cluster access (kubectl configured)
- [ ] AWS console access
- [ ] OpenSearch dashboard access
- [ ] Neo4j browser access
- [ ] Grafana dashboard access
- [ ] Prometheus access
- [ ] Status page admin access
- [ ] Slack #incidents channel
- [ ] PagerDuty/OpsGenie login
- [ ] VPN connected (if required)

## Related

- [Hot Config Change](./01-hot-config-change.md)
- [Scale Retrieval](./02-scale-retrieval.md)
- [GPU Node Failure](./04-gpu-node-failure.md)
- [Monitoring Guide](../../docs/monitoring.md)
