# Catalog Refresh Runbook

## Purpose

Safely refresh ontology and catalog data while preserving licensing compliance, index parity, and downstream availability.

## Prerequisites

- Catalog service access (`kubectl` + port-forward or CI job permissions)
- Valid license entitlements recorded in `licenses.yml`
- Access to S3 bucket `s3://medkg-catalog-artifacts`
- OpenSearch admin credentials and Neo4j admin credentials
- Monitoring dashboards: "Catalog Refresh", "OpenSearch", "Neo4j"

## Overview

1. Validate entitlements and fetch latest artifacts
2. Stage refresh in dry-run mode and diff with current release
3. Dual-write refreshed concepts to Neo4j/OpenSearch
4. Run parity checks (counts, sampled queries, SHACL)
5. Flip aliases, update analyzer assets, and monitor

## Step-by-Step Procedure

### 1. Verify Licensing & Entitlements

```bash
# Confirm all required licenses are current
python scripts/licenses/check_licenses.py --output tmp/license_report.json
jq '.expired' tmp/license_report.json

# Any expired entitlements must be renewed before proceeding
```

Update `licenses.yml` if an entitlement changed tier or expiry:

```bash
vim configs/licenses.yml
# Update expires_on / enabled flags per vendor response
```

### 2. Fetch Latest Artifacts

```bash
# Example: SNOMED CT quarterly release
aws s3 sync s3://vendor-snomed/releases/2024-09/ ./artifacts/snomed-2024-09

# ClinicalTrials.gov snapshot
python scripts/connectors/clinicaltrials.py download --date 2024-10-03 --dest ./artifacts/ctgov-2024-10-03

# Record hashes for reproducibility
find ./artifacts -type f -exec shasum -a 256 {} + | tee refresh.sha256
```

### 3. Dry-Run Catalog Refresh

```bash
export CATALOG_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
python -m Medical_KG.catalog.pipeline \
  --config configs/catalog-refresh.yaml \
  --artifacts ./artifacts \
  --run-id "$CATALOG_RUN_ID" \
  --dry-run \
  --output ./artifacts/${CATALOG_RUN_ID}/dry_run
```

Validate diff output:

```bash
python scripts/catalog/diff_releases.py \
  --previous s3://medkg-catalog-artifacts/latest \
  --candidate ./artifacts/${CATALOG_RUN_ID}/dry_run \
  --report ./artifacts/${CATALOG_RUN_ID}/diff_report.md
```

Review:
- Added/removed concepts by ontology
- Synonym count deltas
- Vector coverage deltas
- Licensing changes (restricted → public?)

### 4. Enable Dual-Write for Refresh

Update config to dual-write while still reading from previous alias:

```yaml
# configs/config-prod.yaml
catalog:
  release_id: "${CATALOG_RUN_ID}"
  opensearch_indexes:
    write: ["concepts_v1", "concepts_v2"]
    read: "concepts_v1"
```

Hot reload the API:

```bash
curl -X POST https://api.medkg.example.com/admin/reload \
  -H "Authorization: Bearer ${ADMIN_JWT}"
```

### 5. Run Full Refresh

```bash
python -m Medical_KG.catalog.pipeline \
  --config configs/catalog-refresh.yaml \
  --artifacts ./artifacts \
  --run-id "$CATALOG_RUN_ID" \
  --output ./artifacts/${CATALOG_RUN_ID}/full
```

Monitor:

```bash
watch -n 30 'python scripts/catalog/status.py --run-id "$CATALOG_RUN_ID"'
```

### 6. Parity & Integrity Checks

```bash
# Count comparison
python scripts/catalog/compare_counts.py \
  --old-index concepts_v1 \
  --new-index concepts_v2 \
  --neo4j-bolt bolt://neo4j:7687

# Sample recall check (50 queries)
python scripts/catalog/evaluate_recall.py --baseline concepts_v1 --candidate concepts_v2

# SHACL validation on sampled KG writes
python scripts/catalog/run_shacl.py --input ./artifacts/${CATALOG_RUN_ID}/full/kg_batch.jsonl
```

Ensure:
- Concept count delta < 1%
- Recall@20 delta < 2%
- SHACL violations = 0
- Analyzer synonyms regenerated (see artifacts `<run-id>/analysis/biomed_synonyms.txt`)

### 7. Flip Aliases & Reload Analyzers

```bash
# Swap alias atomically
curl -X POST https://opensearch:9200/_aliases \
  -H 'Content-Type: application/json' \
  -d '{
    "actions": [
      {"remove": {"index": "concepts_v1", "alias": "concepts"}},
      {"add": {"index": "concepts_v2", "alias": "concepts"}}
    ]
  }'

# Reload analyzers to pick up new synonyms
curl -X POST https://opensearch:9200/concepts/_reload_search_analyzers
```

Update config to read from new alias:

```yaml
catalog:
  opensearch_indexes:
    write: ["concepts_v2"]
    read: "concepts_v2"
```

Hot reload again and restart ingestion workers (they cache analyzer hashes).

### 8. Post-Refresh Monitoring (24 hours)

Track in Grafana (Catalog dashboard):
- Concept ingest throughput (target ≥ 2k/min)
- SHACL violations (must remain 0)
- Vector coverage (≥ 99.5%)
- Retrieval nDCG@10 baseline +/− 1%

### 9. Rollback Plan

If issues within 24 hours:

```bash
# Revert alias
curl -X POST https://opensearch:9200/_aliases \
  -H 'Content-Type: application/json' \
  -d '{
    "actions": [
      {"remove": {"index": "concepts_v2", "alias": "concepts"}},
      {"add": {"index": "concepts_v1", "alias": "concepts"}}
    ]
  }'

# Disable dual-write
update-config catalog.opensearch_indexes.write '["concepts_v1"]'
```

Restore previous analyzer file from `s3://medkg-catalog-artifacts/latest/analysis/` and hot reload.

### 10. Close Out

- Upload diff & validation reports to `s3://medkg-catalog-artifacts/${CATALOG_RUN_ID}`
- Update `docs/catalog_operations.md` release log
- Schedule post-refresh review in next ops sync

## Validation Checklist

- [ ] Licenses confirmed & documented
- [ ] Dry-run diff reviewed & approved
- [ ] Dual-write window observed
- [ ] Parity metrics within thresholds
- [ ] Alias flipped & analyzers reloaded
- [ ] Post-refresh monitoring signed off
- [ ] Rollback plan rehearsed quarterly

## Related

- [Data Store Failover Runbook](./07-datastore-failover.md)
- [Catalog Operations Guide](../../docs/catalog_operations.md)
- [Release Readiness Checklist](../release/checklist.md)
