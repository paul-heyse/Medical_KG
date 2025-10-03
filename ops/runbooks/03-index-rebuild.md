# Index Rebuild Runbook

## Purpose

Guide operators through rebuilding OpenSearch index with zero downtime using blue-green deployment strategy.

## Prerequisites

- OpenSearch admin access
- Sufficient disk space (2x current index size)
- Monitoring dashboard access
- Estimated time: 2-6 hours depending on data volume

## Overview

This runbook uses dual-write strategy to minimize downtime:

1. Create new index with updated schema
2. Enable dual-write to both old and new indexes
3. Backfill historical data
4. Verify parity
5. Flip alias to new index
6. Drop old index

## Procedure

### 1. Create New Index

```bash
# Define new index name with version suffix
OLD_INDEX="chunks_v1"
NEW_INDEX="chunks_v2"
ALIAS="chunks"

# Create new index with updated mapping
curl -X PUT "https://opensearch:9200/${NEW_INDEX}" \
  -H 'Content-Type: application/json' \
  -d @- <<EOF
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "refresh_interval": "30s",
    "index.codec": "best_compression"
  },
  "mappings": {
    "properties": {
      "chunk_id": {"type": "keyword"},
      "text": {"type": "text"},
      "facet_json": {
        "type": "text",
        "fields": {
          "keyword": {"type": "keyword"}
        }
      },
      "facet_type": {"type": "keyword"},
      "facet_codes": {"type": "keyword"},
      "embedding_qwen": {
        "type": "knn_vector",
        "dimension": 4096
      }
    }
  }
}
EOF
```

### 2. Enable Dual-Write

Update application configuration to write to both indexes:

```yaml
# config.yaml
opensearch:
  indexes:
    - chunks_v1  # Old index
    - chunks_v2  # New index (dual-write)
  read_alias: chunks_v1  # Still reading from old
```

```bash
# Apply configuration
curl -X POST https://api.medkg.example.com/admin/reload \
  -H "Authorization: Bearer ${ADMIN_JWT}"
```

### 3. Backfill Historical Data

```python
# Run backfill script
python scripts/reindex_opensearch.py \
  --source-index chunks_v1 \
  --target-index chunks_v2 \
  --batch-size 1000 \
  --parallel-workers 4

# Monitor progress
curl "https://opensearch:9200/${NEW_INDEX}/_count"
```

### 4. Verify Parity

```bash
# Compare document counts
OLD_COUNT=$(curl -s "https://opensearch:9200/${OLD_INDEX}/_count" | jq '.count')
NEW_COUNT=$(curl -s "https://opensearch:9200/${NEW_INDEX}/_count" | jq '.count')

echo "Old index: ${OLD_COUNT} docs"
echo "New index: ${NEW_COUNT} docs"

# Expect difference < 1% (due to in-flight writes)
DIFF=$(echo "scale=4; ($OLD_COUNT - $NEW_COUNT) / $OLD_COUNT * 100" | bc)
echo "Difference: ${DIFF}%"
```

### 5. Verify Retrieval Quality

Run evaluation queries to ensure Recall@20 delta < 2%:

```python
# Run evaluation suite
python tests/evaluation/test_retrieval_parity.py \
  --old-index chunks_v1 \
  --new-index chunks_v2 \
  --gold-queries tests/fixtures/gold_queries.jsonl

# Expected output:
# Recall@20 old: 0.82
# Recall@20 new: 0.83
# Delta: +1.2% ✓
```

### 6. Flip Alias

Once parity verified, switch alias to new index:

```bash
# Atomic alias swap
curl -X POST "https://opensearch:9200/_aliases" \
  -H 'Content-Type: application/json' \
  -d '{
    "actions": [
      {"remove": {"index": "'${OLD_INDEX}'", "alias": "'${ALIAS}'"}},
      {"add": {"index": "'${NEW_INDEX}'", "alias": "'${ALIAS}'"}}
    ]
  }'

# Update config to read from new index
# config.yaml
opensearch:
  read_alias: chunks_v2
```

### 7. Monitor New Index

```bash
# Monitor for 1 hour
watch -n 60 '
  echo "=== Request Rate ==="
  curl -s "http://prometheus:9090/api/v1/query?query=rate(opensearch_query_total[5m])"

  echo "=== P95 Latency ==="
  curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95, opensearch_query_latency_ms)"

  echo "=== Error Rate ==="
  curl -s "http://prometheus:9090/api/v1/query?query=rate(opensearch_errors_total[5m])"
'
```

### 8. Disable Dual-Write

After 24 hours of stable operation:

```yaml
# config.yaml
opensearch:
  indexes:
    - chunks_v2  # Only new index
  read_alias: chunks_v2
```

### 9. Drop Old Index

After 7 days (retention for rollback):

```bash
# Create snapshot for safety
curl -X PUT "https://opensearch:9200/_snapshot/backup/chunks_v1_final" \
  -H 'Content-Type: application/json' \
  -d '{
    "indices": "'${OLD_INDEX}'",
    "ignore_unavailable": true
  }'

# Delete old index
curl -X DELETE "https://opensearch:9200/${OLD_INDEX}"
```

## Rollback

### Before Alias Flip

Simply stop dual-write and drop new index:

```bash
curl -X DELETE "https://opensearch:9200/${NEW_INDEX}"
```

### After Alias Flip

If issues detected within 7 days:

```bash
# Flip alias back
curl -X POST "https://opensearch:9200/_aliases" \
  -H 'Content-Type: application/json' \
  -d '{
    "actions": [
      {"remove": {"index": "'${NEW_INDEX}'", "alias": "'${ALIAS}'"}},
      {"add": {"index": "'${OLD_INDEX}'", "alias": "'${ALIAS}'"}}
    ]
  }'

# Update config
opensearch:
  read_alias: chunks_v1
```

## Common Issues

### Issue: Slow backfill

**Cause**: Insufficient parallelism or resources
**Solution**: Increase `parallel_workers`, disable refresh during reindex

### Issue: Disk full

**Cause**: Not enough space for both indexes
**Solution**: Add nodes, increase disk, or use remote snapshot

### Issue: Query performance degraded

**Cause**: Shard count mismatch, no warmup
**Solution**: Run warmup queries, adjust shard count

### Issue: Missing documents

**Cause**: Race condition in dual-write
**Solution**: Re-run backfill with overlap window

## Related

- [OpenSearch Tuning Guide](../../docs/opensearch-tuning.md)
- [Performance Monitoring](../../docs/monitoring.md)
