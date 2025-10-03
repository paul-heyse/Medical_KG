# Data Store Failover Runbook

## Purpose

Coordinate failover and recovery for Neo4j, OpenSearch, and backup/restore services during outages or maintenance.

## Prerequisites

- Kubernetes admin access to `medkg` namespace
- Access to AWS (or cloud) console for storage snapshots
- Neo4j admin credentials (`NEO4J_BOLT_URI`, `NEO4J_PASSWORD`)
- OpenSearch admin credentials
- Access to backup bucket `s3://medkg-backups`
- Monitoring dashboards: "Neo4j Cluster", "OpenSearch", "Backups"

## Severity Mapping

| Impact                               | Severity | Response Goal |
|--------------------------------------|----------|---------------|
| Primary cluster down, no writes      | P1       | < 15 minutes  |
| Replica degraded, writes succeeding  | P2       | < 30 minutes  |
| Backup job failure (no recent copy)  | P2       | < 4 hours     |
| Maintenance rollover                 | P3       | Scheduled     |

## Neo4j Failover

### Detect

- Alert: `Neo4jCoreDown` firing
- `neo4j_core_available < 3`
- `kubectl get pods -n medkg -l app=neo4j` shows < 3 `core` pods Ready

### Immediate Actions

```bash
kubectl describe statefulset neo4j-core -n medkg
kubectl logs neo4j-core-0 -n medkg | tail
```

If pod stuck Pending:

```bash
kubectl get events -n medkg --sort-by='.lastTimestamp' | grep neo4j-core
```

### Failover Procedure

1. **Promote Read Replica (if available)**

```bash
kubectl exec -n medkg neo4j-admin-0 -- neo4j-admin server promote --database=neo4j
```

2. **Remove Failed Core**

```bash
kubectl delete pod neo4j-core-1 -n medkg --grace-period=0 --force
kubectl delete pvc data-neo4j-core-1 -n medkg
```

3. **Provision Replacement**

```bash
kubectl scale statefulset neo4j-core -n medkg --replicas=4
kubectl rollout status statefulset neo4j-core -n medkg --timeout=600s
kubectl scale statefulset neo4j-core -n medkg --replicas=3
```

4. **Rejoin Cluster**

```bash
kubectl exec -n medkg neo4j-core-2 -- neo4j-admin server unbind --database=system
kubectl exec -n medkg neo4j-core-2 -- neo4j-admin server enable --database=neo4j
```

5. **Verify**

```bash
cypher-shell -a neo4j://neo4j-core:7687 -u neo4j -p "$NEO4J_PASSWORD" <<'CYPHER'
SHOW DATABASES YIELD name, currentStatus, default, address;
CYPHER
```

### Rollback / Restore from Snapshot

```bash
# Stop writers
eksctl scale nodegroup --cluster medkg-prod --name neo4j-ng --nodes 0

# Restore snapshot
aws s3 cp s3://medkg-backups/neo4j/2024-10-03/core-0.tar.gz - | tar -xz -C /var/lib/neo4j/data

# Restart
kubectl scale statefulset neo4j-core -n medkg --replicas=3
```

## OpenSearch Failover

### Detect

- Alerts: `OpenSearchUnassignedShards`, `OpenSearchDiskSpaceHigh`
- `curl -u admin:$OS_PASSWORD https://opensearch:9200/_cluster/health?pretty`

### Reroute Shards

```bash
curl -u admin:$OS_PASSWORD -X POST https://opensearch:9200/_cluster/reroute -H 'Content-Type: application/json' -d '{
  "commands": [
    {"allocate_empty_primary": {"index": "chunks_v1", "shard": 0, "node": "opensearch-data-1", "accept_data_loss": true}}
  ]
}'
```

*(Use only if shard lost after confirming snapshot recency)*

### Replace Failed Data Node

```bash
kubectl delete pod opensearch-data-0 -n medkg
kubectl delete pvc data-opensearch-data-0 -n medkg
kubectl scale statefulset opensearch-data -n medkg --replicas=4
kubectl rollout status statefulset opensearch-data -n medkg --timeout=600s
kubectl scale statefulset opensearch-data -n medkg --replicas=3
```

### Restore Index From Snapshot

```bash
SNAPSHOT=$(aws s3 ls s3://medkg-backups/opensearch/ | tail -n1 | awk '{print $4}')

curl -u admin:$OS_PASSWORD -X POST https://opensearch:9200/_snapshot/medkg/$SNAPSHOT/_restore -H 'Content-Type: application/json' -d '{
  "indices": "chunks_v1,concepts_v1",
  "ignore_unavailable": true,
  "include_global_state": false
}'
```

### Verify

```bash
curl -u admin:$OS_PASSWORD https://opensearch:9200/_cluster/health?pretty
curl -u admin:$OS_PASSWORD https://opensearch:9200/_cat/shards | sort
```

## Backup & Restore

### Daily Verification

```bash
# Ensure last backup < 24h
aws s3 ls s3://medkg-backups/neo4j/ | tail -n1
aws s3 ls s3://medkg-backups/opensearch/ | tail -n1
```

If backup failed:

```bash
kubectl logs cronjob/backup-neo4j -n medkg --tail=200
kubectl logs cronjob/backup-opensearch -n medkg --tail=200
```

Re-run manually:

```bash
kubectl create job --from=cronjob/backup-neo4j backup-neo4j-manual -n medkg
kubectl create job --from=cronjob/backup-opensearch backup-opensearch-manual -n medkg
```

### Restore Drill (Quarterly)

1. Provision staging namespace `medkg-dr`.
2. Restore latest Neo4j snapshot to staging cluster.
3. Restore OpenSearch indices.
4. Run `python ops/e2e/run_verification.py --env staging --dry-run false` against restored stack.
5. Document timings and issues.

## Decision Tree

1. **Cluster down?**
   - Yes → Initiate failover (Neo4j or OpenSearch) → Verify → Postmortem.
2. **Degraded but serving traffic?**
   - Yes → Scale replacement nodes, reroute shards, monitor.
3. **Backup gap > 24h?**
   - Yes → Run manual backup, investigate CronJob, escalate if repeated.

## Communication Template

```
:pager: *P1 Datastore Incident*
Service: Neo4j
Impact: Writes failing, API returning 500s
Start: 2024-10-03 14:22 UTC
Lead: @oncall
Mitigation: Promoting replica, rerouting shards
ETA: 15 minutes
Runbook: ops/runbooks/07-datastore-failover.md
```

## Post-Incident Checklist

- [ ] Failover completed and validated (queries + SHACL)
- [ ] Backups intact (last snapshot verified)
- [ ] Incident comms posted + status page updated
- [ ] Post-mortem scheduled within 48 hours
- [ ] Action items tracked in Ops board

## Related

- [Catalog Refresh Runbook](./06-catalog-refresh.md)
- [Incident Response Playbook](./05-incident-response.md)
- [Release Readiness Checklist](../release/checklist.md)
