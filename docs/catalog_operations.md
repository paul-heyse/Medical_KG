# Concept Catalog Operations

## License Acquisition

| Source      | Requirement | Notes |
|-------------|-------------|-------|
| SNOMED CT   | National release centre approval; affiliate agreement | Record affiliate ID in `licenses.yml` under `loaders.SNOMED`. |
| UMLS / RxNorm | Annual Terms of Service acceptance | Store API keys in the credential vault referenced by `LICENSES_UMLS_KEY`. |
| MedDRA      | Subscription with quarterly download rights | Flag as `restricted` in `licenses.yml` to disable ingestion when expired. |

The catalog bootstrap reads `licenses.yml` on startup. Buckets (`open`, `permissive`, `restricted`, `proprietary`) determine whether a loader executes; set `loaders.<ONTOLOGY>.enabled` to `false` to hard-disable a source.

## Refresh Runbook

1. Fetch latest artifacts or API snapshots per ontology (SNOMED quarterly, ICD-11 biannual, MONDO/HPO monthly, RxNorm weekly, GUDID six-hourly).
2. Update `licenses.yml` if entitlement status changed.
3. Execute the catalog updater service. It compares release versions, computes the release hash, and skips work if nothing changed.
4. On change, the updater writes concepts to Neo4j, refreshes `concepts_v1` in OpenSearch, regenerates `analysis/biomed_synonyms.txt`, and reloads analyzers.
5. Verify the audit log for skipped loaders and ensure vector index `concept_qwen_idx` reports the new `release_hash`.

## Synonym Analyzer Refresh

The catalog pipeline aggregates ontology-specific synonym lists and writes them into the analyzer filter. After each refresh:

- Persist the generated synonyms file to `analysis/biomed_synonyms.txt`.
- Call `ConceptIndexManager.update_synonyms(...)` to push the list to OpenSearch.
- Trigger a rolling analyzer reload (`indices.reload_search_analyzers`).
- Confirm boosted fields (`label^3`, `synonyms.value^2`, `definition^0.5`) respond correctly via a smoke query.
